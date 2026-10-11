"""
Post-Match Report Generator.

Given a single StatsBomb match_id, this builds the kind of report an analyst
assembles within 12-24 hours of a match:

  - Headline score + key-stats table (xG, shots, possession, passes, etc.)
  - Shot map for both teams, dot size = xG, colour = goal/no-goal
  - xG race chart (cumulative xG over time — the "who deserved to win" story)
  - Pass network for each team (average position + most frequent connections)

Outputs a single PNG dashboard to output/ plus a JSON of the key numbers.

Usage:
    python src/report.py <match_id>
    python src/report.py              # uses a default sample match
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
from mplsoccer import Pitch, VerticalPitch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xg_model import load_model, predict_xg, shot_features

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

# Visual theme
BG = "#12161c"
FG = "#e8edf2"
MUTED = "#8a97a6"
HOME_C = "#4ea1ff"
AWAY_C = "#ff6b6b"
GOAL_C = "#ffd34e"
PITCH_LINE = "#3a4350"


def _apply_model_xg(shots, model, features):
    """Recompute xG for each shot with OUR model (not StatsBomb's)."""
    vals = []
    for _, s in shots.iterrows():
        loc = s.get("location")
        if not isinstance(loc, list) or len(loc) < 2:
            vals.append(0.0)
            continue
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
        vals.append(xg)
    shots = shots.copy()
    shots["model_xg"] = vals
    return shots


def _minute(row):
    return row["minute"] + row["second"] / 60.0


def gather(match_id):
    """Pull events and compute everything the report needs."""
    events = sb.events(match_id=match_id)
    teams = list(events["team"].dropna().unique())
    home, away = teams[0], teams[1]

    model, features = load_model()

    shots = events[events["type"] == "Shot"].copy()
    shots = _apply_model_xg(shots, model, features)

    goals = shots[shots["shot_outcome"] == "Goal"]
    score = {
        home: int((goals["team"] == home).sum()),
        away: int((goals["team"] == away).sum()),
    }
    # Own goals are logged as their own event type, not as Shots, so add them
    # to the OPPOSING team's score to get the true scoreline.
    og = events[events["type"] == "Own Goal Against"]
    for _, o in og.iterrows():
        scorer_team = o["team"]
        other = away if scorer_team == home else home
        score[other] += 1

    # Key stats per team
    def team_stats(team):
        te = events[events["team"] == team]
        ts = shots[shots["team"] == team]
        passes = te[te["type"] == "Pass"]
        completed = passes[passes["pass_outcome"].isna()]
        return {
            "goals": score[team],
            "xg_model": round(float(ts["model_xg"].sum()), 2),
            "xg_statsbomb": round(float(ts["shot_statsbomb_xg"].sum()), 2),
            "shots": int(len(ts)),
            "shots_on_target": int((ts["shot_outcome"].isin(["Goal", "Saved"])).sum()),
            "passes": int(len(passes)),
            "pass_accuracy": round(100 * len(completed) / max(len(passes), 1), 1),
        }

    stats = {home: team_stats(home), away: team_stats(away)}

    # Possession proxy: share of completed passes
    tp = stats[home]["passes"] + stats[away]["passes"]
    stats[home]["possession"] = round(100 * stats[home]["passes"] / max(tp, 1), 1)
    stats[away]["possession"] = round(100 * stats[away]["passes"] / max(tp, 1), 1)

    return {
        "match_id": match_id,
        "home": home, "away": away,
        "score": score, "stats": stats,
        "events": events, "shots": shots, "goals": goals,
        "model": model, "features": features,
    }


# ---------------------------------------------------------------------------
# Pass network
# ---------------------------------------------------------------------------
def pass_network(events, team):
    """Average positions and most frequent passing links for a team,
    up to its first substitution (standard convention for a clean network)."""
    te = events[events["team"] == team].copy()
    passes = te[te["type"] == "Pass"].copy()
    passes = passes[passes["pass_outcome"].isna()]  # completed only

    # Cut at first substitution so the XI is stable
    subs = te[te["type"] == "Substitution"]
    if not subs.empty:
        first_sub = subs["minute"].min()
        passes = passes[passes["minute"] < first_sub]

    passes = passes.dropna(subset=["player", "pass_recipient", "location"])
    if passes.empty:
        return None, None

    passes["x"] = passes["location"].apply(lambda l: l[0])
    passes["y"] = passes["location"].apply(lambda l: l[1])

    avg = passes.groupby("player").agg(
        x=("x", "mean"), y=("y", "mean"), count=("x", "size")
    ).reset_index()

    pair = passes.groupby(["player", "pass_recipient"]).size().reset_index(name="n")
    pair = pair[pair["n"] >= 3]  # only show links used 3+ times

    return avg, pair


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def build_report(data, out_path):
    home, away = data["home"], data["away"]
    stats, shots = data["stats"], data["shots"]
    events = data["events"]

    fig = plt.figure(figsize=(16, 20), facecolor=BG)
    gs = GridSpec(4, 2, figure=fig, height_ratios=[0.8, 1.2, 1.1, 1.3],
                  hspace=0.28, wspace=0.12)

    # ---- Header ----
    ax_h = fig.add_subplot(gs[0, :])
    ax_h.axis("off")
    ax_h.set_facecolor(BG)
    sc = data["score"]
    ax_h.text(0.5, 0.78, f"{home}  {sc[home]} – {sc[away]}  {away}",
              ha="center", va="center", color=FG, fontsize=30, fontweight="bold",
              transform=ax_h.transAxes)
    ax_h.text(0.5, 0.45, "P O S T - M A T C H   R E P O R T", ha="center",
              color=MUTED, fontsize=13, transform=ax_h.transAxes)
    ax_h.text(0.5, 0.28,
              f"Model xG:  {stats[home]['xg_model']}  –  {stats[away]['xg_model']}",
              ha="center", color=GOAL_C, fontsize=15, transform=ax_h.transAxes)

    # ---- Key stats bars ----
    ax_s = fig.add_subplot(gs[1, :])
    ax_s.set_facecolor(BG)
    metrics = [
        ("Model xG", "xg_model"),
        ("Shots", "shots"),
        ("On target", "shots_on_target"),
        ("Possession %", "possession"),
        ("Passes", "passes"),
        ("Pass acc. %", "pass_accuracy"),
    ]
    ypos = np.arange(len(metrics))[::-1]
    for i, (label, key) in enumerate(metrics):
        hv, av = stats[home][key], stats[away][key]
        total = hv + av if (hv + av) > 0 else 1
        hw, aw = hv / total, av / total
        yy = ypos[i]
        ax_s.barh(yy, hw, color=HOME_C, height=0.6, left=0)
        ax_s.barh(yy, aw, color=AWAY_C, height=0.6, left=hw)
        ax_s.text(-0.01, yy, f"{hv}", ha="right", va="center", color=HOME_C,
                  fontsize=13, fontweight="bold")
        ax_s.text(1.01, yy, f"{av}", ha="left", va="center", color=AWAY_C,
                  fontsize=13, fontweight="bold")
        ax_s.text(0.5, yy + 0.42, label, ha="center", va="bottom", color=MUTED,
                  fontsize=11)
    ax_s.set_xlim(-0.12, 1.12)
    ax_s.set_ylim(-0.6, len(metrics) - 0.2)
    ax_s.axis("off")

    # ---- Shot maps (one attacking half-pitch per team, goal at top) ----
    for col, (team, colour) in enumerate([(home, HOME_C), (away, AWAY_C)]):
        ax = fig.add_subplot(gs[2, col])
        pitch = VerticalPitch(pitch_type="statsbomb", half=True, pad_bottom=-18,
                              pitch_color=BG, line_color=PITCH_LINE, linewidth=1.2)
        pitch.draw(ax=ax)
        ts = shots[shots["team"] == team]
        # Draw non-goals first, goals on top so they're never hidden
        for is_goal_pass in (False, True):
            for _, s in ts.iterrows():
                loc = s.get("location")
                if not isinstance(loc, list):
                    continue
                is_goal = s["shot_outcome"] == "Goal"
                if is_goal != is_goal_pass:
                    continue
                x, y = loc
                xg = s["model_xg"]
                pitch.scatter(x, y, s=140 + xg * 1100,
                              color=GOAL_C if is_goal else colour,
                              edgecolors="white" if is_goal else "#1b2027",
                              linewidth=1.6 if is_goal else 0.8,
                              alpha=0.9, ax=ax, zorder=4 if is_goal else 3)
        tg = int((ts["shot_outcome"] == "Goal").sum())
        ax.set_title(f"{team}\n{len(ts)} shots · {tg} goals · size = xG",
                     color=colour, fontsize=12, pad=8, fontweight="bold")

    # ---- xG race chart ----
    ax_r = fig.add_subplot(gs[3, 0])
    ax_r.set_facecolor(BG)
    for team, colour in [(home, HOME_C), (away, AWAY_C)]:
        ts = shots[shots["team"] == team].copy()
        ts["t"] = ts.apply(_minute, axis=1)
        ts = ts.sort_values("t")
        t = [0] + ts["t"].tolist() + [95]
        cum = [0] + ts["model_xg"].cumsum().tolist()
        cum = cum + [cum[-1]]
        ax_r.step(t, cum, where="post", color=colour, linewidth=2.4, label=team)
        # mark goals
        for _, g in ts[ts["shot_outcome"] == "Goal"].iterrows():
            ax_r.scatter(g["t"], ts[ts["t"] <= g["t"]]["model_xg"].sum(),
                         color=GOAL_C, s=90, zorder=5, edgecolors="white", linewidth=1)
    ax_r.set_title("Cumulative xG (the flow of the game)", color=FG, fontsize=12, pad=8)
    ax_r.set_xlabel("Minute", color=MUTED, fontsize=10)
    ax_r.set_ylabel("Cumulative xG", color=MUTED, fontsize=10)
    ax_r.tick_params(colors=MUTED)
    for spine in ax_r.spines.values():
        spine.set_color(PITCH_LINE)
    ax_r.legend(facecolor=BG, edgecolor=PITCH_LINE, labelcolor=FG, fontsize=10)
    ax_r.grid(alpha=0.12)

    # ---- Pass network (home team) ----
    ax_p = fig.add_subplot(gs[3, 1])
    pitch = Pitch(pitch_type="statsbomb", pitch_color=BG,
                  line_color=PITCH_LINE, linewidth=1)
    pitch.draw(ax=ax_p)
    avg, pair = pass_network(events, home)
    if avg is not None:
        pos = {r["player"]: (r["x"], r["y"]) for _, r in avg.iterrows()}
        for _, p in pair.iterrows():
            a, b = p["player"], p["pass_recipient"]
            if a in pos and b in pos:
                x1, y1 = pos[a]; x2, y2 = pos[b]
                pitch.lines(x1, y1, x2, y2, lw=p["n"] * 0.5,
                            color=HOME_C, alpha=0.35, ax=ax_p, zorder=1)
        pitch.scatter(avg["x"], avg["y"], s=avg["count"] * 12 + 120,
                      color=HOME_C, edgecolors="white", linewidth=1.2,
                      alpha=0.9, ax=ax_p, zorder=3)
        for _, r in avg.iterrows():
            name = r["player"].split()[-1]
            pitch.annotate(name, (r["x"], r["y"]), ax=ax_p, color=FG,
                           fontsize=7.5, ha="center", va="center", zorder=4,
                           xytext=(0, -14), textcoords="offset points")
    ax_p.set_title(f"{home} — pass network (to 1st sub)", color=FG, fontsize=12, pad=8)

    fig.text(0.5, 0.012, "Generated by soccer-analytics  ·  xG = own model (ROC-AUC ~0.79)  ·  data: StatsBomb open data",
             ha="center", color=MUTED, fontsize=9)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fig.savefig(out_path, dpi=130, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved report -> {os.path.abspath(out_path)}")


def run(match_id):
    print(f"Gathering match {match_id}...")
    data = gather(match_id)
    out_png = os.path.join(OUTPUT_DIR, f"report_{match_id}.png")
    build_report(data, out_png)

    # dump the numbers too
    summary = {
        "match_id": match_id,
        "home": data["home"], "away": data["away"],
        "score": data["score"], "stats": data["stats"],
    }
    out_json = os.path.join(OUTPUT_DIR, f"report_{match_id}.json")
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary -> {os.path.abspath(out_json)}")
    print("\n" + json.dumps(summary["stats"], indent=2))
    # Return a dict the web API can hand straight to the frontend
    summary["png"] = f"report_{match_id}.png"
    return summary


if __name__ == "__main__":
    # Default sample: 2018 World Cup Final (France vs Croatia), match_id 8658
    match_id = int(sys.argv[1]) if len(sys.argv) > 1 else 8658
    run(match_id)
