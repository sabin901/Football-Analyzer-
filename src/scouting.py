"""
Season-long Scouting / Opponent Report.

Where the match report answers "what happened in this game?", this answers
"what is this team LIKE?" — the pre-match / recruitment flank of analysis.

For one team across one competition+season it aggregates:
  - Record: played, W-D-L, goals for/against, model xG for/against per 90
  - Shot-location heatmap (where they create chances)
  - Conceded-shot heatmap (where they're vulnerable)
  - Set-piece dependence (share of xG from corners & free kicks)
  - Attacking side bias (left / central / right)
  - Form: cumulative xG difference over the season

Outputs a dashboard PNG + JSON.

Usage:
    python src/scouting.py <competition_id> <season_id> "<Team Name>"
    python src/scouting.py 2 27 "Arsenal"
"""

import os
import sys
import json
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore")

from statsbombpy import sb
from mplsoccer import VerticalPitch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xg_model import load_model, predict_xg

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")

BG, FG, MUTED = "#12161c", "#e8edf2", "#8a97a6"
FOR_C, AGN_C, ACCENT2, LINE = "#4ea1ff", "#ff6b6b", "#ffd34e", "#3a4350"


def _xg_for_shot(model, features, s):
    loc = s.get("location")
    if not isinstance(loc, list) or len(loc) < 2:
        return 0.0, None, None
    x, y = loc[0], loc[1]
    pp = s.get("play_pattern")
    xg = predict_xg(
        model, features, x, y,
        header=1 if s.get("shot_body_part") == "Head" else 0,
        volley=1 if s.get("shot_technique") == "Volley" else 0,
        first_time=1 if s.get("shot_first_time") is True else 0,
        open_play=1 if s.get("shot_type") == "Open Play" else 0,
        from_corner=1 if pp == "From Corner" else 0,
        from_free_kick=1 if pp == "From Free Kick" else 0,
        from_counter=1 if pp == "From Counter" else 0,
        under_pressure=1 if s.get("under_pressure") is True else 0,
    )
    return xg, x, y


def gather(competition_id, season_id, team):
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    # keep only this team's matches
    mask = (matches["home_team"] == team) | (matches["away_team"] == team)
    tm = matches[mask]
    if tm.empty:
        raise ValueError(f"No matches found for '{team}' in this competition/season.")

    model, features = load_model()

    rec = {"played": 0, "W": 0, "D": 0, "L": 0, "gf": 0, "ga": 0}
    xg_for = xg_against = 0.0
    sp_xg = 0.0  # xG from set pieces (for)
    shots_for, shots_against = [], []   # (x, y, xg)
    side = {"left": 0.0, "central": 0.0, "right": 0.0}
    timeline = []  # (match_index, xg_diff) for form chart

    for i, (_, m) in enumerate(tm.iterrows()):
        mid = m["match_id"]
        try:
            events = sb.events(match_id=mid)
        except Exception:
            continue
        shots = events[events["type"] == "Shot"]

        is_home = m["home_team"] == team
        gf = m["home_score"] if is_home else m["away_score"]
        ga = m["away_score"] if is_home else m["home_score"]
        rec["played"] += 1
        rec["gf"] += int(gf); rec["ga"] += int(ga)
        if gf > ga: rec["W"] += 1
        elif gf == ga: rec["D"] += 1
        else: rec["L"] += 1

        # Build a lookup of pass end-locations so we can tell which flank a
        # chance was created from (the shot itself is almost always central,
        # so shot-y is a poor signal; the assist origin is the right one).
        passes = events[events["type"] == "Pass"]
        assist_x = {}
        for _, p in passes.iterrows():
            if p.get("pass_shot_assist") is True or p.get("pass_goal_assist") is True:
                loc = p.get("location")
                if isinstance(loc, list) and len(loc) >= 2:
                    assist_x[p.get("id")] = loc  # keyed by pass id

        match_xg_for = match_xg_against = 0.0
        for _, s in shots.iterrows():
            xg, x, y = _xg_for_shot(model, features, s)
            if x is None:
                continue
            if s["team"] == team:
                xg_for += xg; match_xg_for += xg
                shots_for.append((x, y, xg))
                pp = s.get("play_pattern")
                if pp in ("From Corner", "From Free Kick"):
                    sp_xg += xg
                # Attacking side: use the key-pass origin if we have it,
                # else fall back to the shot's own width position.
                kp = s.get("shot_key_pass_id")
                src_y = assist_x[kp][1] if kp in assist_x else y
                if src_y < 80 / 3:
                    side["left"] += xg
                elif src_y > 2 * 80 / 3:
                    side["right"] += xg
                else:
                    side["central"] += xg
            else:
                xg_against += xg; match_xg_against += xg
                shots_against.append((x, y, xg))
        timeline.append(round(match_xg_for - match_xg_against, 3))

    p90 = max(rec["played"], 1)
    summary = {
        "team": team, "competition_id": competition_id, "season_id": season_id,
        "played": rec["played"], "W": rec["W"], "D": rec["D"], "L": rec["L"],
        "goals_for": rec["gf"], "goals_against": rec["ga"],
        "xg_for_total": round(xg_for, 1), "xg_against_total": round(xg_against, 1),
        "xg_for_per90": round(xg_for / p90, 2),
        "xg_against_per90": round(xg_against / p90, 2),
        "xg_diff_per90": round((xg_for - xg_against) / p90, 2),
        "setpiece_xg_share_pct": round(100 * sp_xg / max(xg_for, 1e-9), 1),
        "attack_left_pct": round(100 * side["left"] / max(sum(side.values()), 1e-9), 1),
        "attack_central_pct": round(100 * side["central"] / max(sum(side.values()), 1e-9), 1),
        "attack_right_pct": round(100 * side["right"] / max(sum(side.values()), 1e-9), 1),
    }
    return summary, shots_for, shots_against, timeline


def build_report(summary, shots_for, shots_against, timeline, out_path):
    team = summary["team"]
    fig = plt.figure(figsize=(16, 13), facecolor=BG)
    gs = GridSpec(3, 3, figure=fig, height_ratios=[0.5, 1.3, 1.0],
                  hspace=0.35, wspace=0.25)

    # ---- Header + record ----
    ax = fig.add_subplot(gs[0, :]); ax.axis("off")
    ax.text(0.5, 0.8, f"{team}", ha="center", color=FG, fontsize=28,
            fontweight="bold", transform=ax.transAxes)
    ax.text(0.5, 0.42, "S E A S O N   S C O U T I N G   R E P O R T", ha="center",
            color=MUTED, fontsize=12, transform=ax.transAxes)
    rec = (f"Played {summary['played']}   ·   {summary['W']}W {summary['D']}D {summary['L']}L"
           f"   ·   GF {summary['goals_for']}  GA {summary['goals_against']}"
           f"   ·   xG {summary['xg_for_per90']} / {summary['xg_against_per90']} per 90")
    ax.text(0.5, 0.05, rec, ha="center", color=ACCENT2, fontsize=14,
            transform=ax.transAxes)

    # ---- Chance-creation heatmap (for) ----
    ax1 = fig.add_subplot(gs[1, 0])
    pitch = VerticalPitch(pitch_type="statsbomb", half=True, pad_bottom=-10,
                          pitch_color=BG, line_color=LINE, linewidth=1.2)
    pitch.draw(ax=ax1)
    if shots_for:
        xs = [s[0] for s in shots_for]; ys = [s[1] for s in shots_for]
        pitch.kdeplot(xs, ys, ax=ax1, fill=True, levels=50, thresh=0.05,
                      cmap="Blues", alpha=0.75)
    ax1.set_title("Where they create\n(shot density, for)", color=FOR_C,
                  fontsize=12, fontweight="bold", pad=8)

    # ---- Vulnerability heatmap (against) ----
    ax2 = fig.add_subplot(gs[1, 1])
    pitch = VerticalPitch(pitch_type="statsbomb", half=True, pad_bottom=-10,
                          pitch_color=BG, line_color=LINE, linewidth=1.2)
    pitch.draw(ax=ax2)
    if shots_against:
        xs = [s[0] for s in shots_against]; ys = [s[1] for s in shots_against]
        pitch.kdeplot(xs, ys, ax=ax2, fill=True, levels=50, thresh=0.05,
                      cmap="Reds", alpha=0.75)
    ax2.set_title("Where they concede\n(shot density, against)", color=AGN_C,
                  fontsize=12, fontweight="bold", pad=8)

    # ---- Profile bars (set-piece share + attacking sides) ----
    ax3 = fig.add_subplot(gs[1, 2]); ax3.set_facecolor(BG)
    profile = [
        ("Set-piece xG share", summary["setpiece_xg_share_pct"], ACCENT2),
        ("Attack left", summary["attack_left_pct"], FOR_C),
        ("Attack central", summary["attack_central_pct"], FOR_C),
        ("Attack right", summary["attack_right_pct"], FOR_C),
    ]
    labels = [p[0] for p in profile][::-1]
    vals = [p[1] for p in profile][::-1]
    cols = [p[2] for p in profile][::-1]
    ax3.barh(labels, vals, color=cols)
    for i, v in enumerate(vals):
        ax3.text(v + 1, i, f"{v}%", va="center", color=FG, fontsize=11)
    ax3.set_xlim(0, max(vals) * 1.25 + 5)
    ax3.set_title("Tactical profile", color=FG, fontsize=12, fontweight="bold", pad=8)
    ax3.tick_params(colors=FG)
    for sp in ax3.spines.values():
        sp.set_color(LINE)
    ax3.grid(alpha=0.12, axis="x")

    # ---- Form: per-match xG difference ----
    ax4 = fig.add_subplot(gs[2, :]); ax4.set_facecolor(BG)
    x = np.arange(1, len(timeline) + 1)
    colors = [FOR_C if v >= 0 else AGN_C for v in timeline]
    ax4.bar(x, timeline, color=colors, alpha=0.9)
    ax4.axhline(0, color=MUTED, lw=1)
    # rolling average line
    if len(timeline) >= 3:
        roll = pd.Series(timeline).rolling(3, min_periods=1).mean()
        ax4.plot(x, roll, color=ACCENT2, lw=2.2, label="3-match rolling avg")
        ax4.legend(facecolor=BG, edgecolor=LINE, labelcolor=FG, fontsize=10)
    ax4.set_title("Form — model xG difference per match (blue = outplayed opponent)",
                  color=FG, fontsize=12, fontweight="bold", pad=8)
    ax4.set_xlabel("Match number", color=MUTED, fontsize=10)
    ax4.set_ylabel("xG for − against", color=MUTED, fontsize=10)
    ax4.tick_params(colors=MUTED)
    for sp in ax4.spines.values():
        sp.set_color(LINE)
    ax4.grid(alpha=0.12, axis="y")

    fig.text(0.5, 0.01,
             "Generated by soccer-analytics  ·  xG = own model  ·  data: StatsBomb open data",
             ha="center", color=MUTED, fontsize=9)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fig.savefig(out_path, dpi=130, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved scouting report -> {os.path.abspath(out_path)}")


def run(competition_id, season_id, team):
    print(f"Scouting {team} (comp {competition_id}, season {season_id})...")
    summary, sf, sa, tl = gather(competition_id, season_id, team)
    safe = team.replace(" ", "_").replace("/", "-")
    png = f"scout_{competition_id}_{season_id}_{safe}.png"
    out_png = os.path.join(OUTPUT_DIR, png)
    build_report(summary, sf, sa, tl, out_png)

    out_json = os.path.join(OUTPUT_DIR, png.replace(".png", ".json"))
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)
    print("\n" + json.dumps(summary, indent=2))
    summary["png"] = png
    return summary


if __name__ == "__main__":
    if len(sys.argv) >= 4:
        run(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
    else:
        # Default sample: Arsenal, Premier League 2015/2016
        run(2, 27, "Arsenal")
