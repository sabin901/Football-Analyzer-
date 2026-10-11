"""
Expected Threat (xT) — valuing ball progression, not just shots.

xG only rewards the final shot. Expected Threat (Karun Singh's model) values
*moving* the ball into dangerous areas — the progressive passes and carries that
modern scouting departments care about most.

The pitch is split into an M x N grid. For every zone we learn, from event data:
  - the chance a possession in that zone ends in a shot, and the chance that
    shot scores  (the "score here now" term)
  - the chance the ball is moved on, and where it moves to (a transition matrix)

xT(zone) is then solved by value iteration:
    xT = shoot_prob * goal_prob  +  move_prob * Σ  T(zone→z') * xT(z')
Any pass or carry is worth  xT(end_zone) − xT(start_zone)  — positive when it
raises the team's scoring threat. Summing a player's positive contributions
ranks the best ball progressors.

Usage:
    python src/xt.py "La Liga" "2015/2016" --matches 120
"""

import os
import sys
import json
import argparse
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statsbombpy import sb
from mplsoccer import Pitch

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUTPUT_DIR = os.path.join(ROOT, "output")
MODELS_DIR = os.path.join(ROOT, "models")

PITCH_X, PITCH_Y = 120.0, 80.0
GRID_W, GRID_H = 16, 12            # columns (length) x rows (width)

BG, FG, MUTED, LINE = "#12161c", "#e8edf2", "#8a97a6", "#3a4350"


def _cell(x, y):
    cx = min(int(x / PITCH_X * GRID_W), GRID_W - 1)
    cy = min(int(y / PITCH_Y * GRID_H), GRID_H - 1)
    return cx, cy


def _collect(competition, season, max_matches):
    """Pull shots + moves (passes, carries) from a sample of matches."""
    matches = sb.matches(competition_id=_cid(competition, season),
                         season_id=_sid(competition, season))
    mids = matches["match_id"].tolist()[:max_matches]
    shots, moves = [], []
    for mid in mids:
        try:
            ev = sb.events(match_id=mid)
        except Exception:
            continue
        for _, e in ev.iterrows():
            loc = e.get("location")
            if not isinstance(loc, list) or len(loc) < 2:
                continue
            t = e["type"]
            if t == "Shot":
                shots.append({"x": loc[0], "y": loc[1],
                              "goal": 1 if e.get("shot_outcome") == "Goal" else 0})
            elif t in ("Pass", "Carry"):
                end = (e.get("pass_end_location") if t == "Pass"
                       else e.get("carry_end_location"))
                if isinstance(end, list) and len(end) >= 2:
                    # only completed passes count as moves
                    if t == "Pass" and pd.notna(e.get("pass_outcome")):
                        continue
                    moves.append({"x": loc[0], "y": loc[1],
                                  "ex": end[0], "ey": end[1],
                                  "player": e.get("player"), "team": e.get("team")})
    return pd.DataFrame(shots), pd.DataFrame(moves), len(mids)


def _cid(name, season):
    c = sb.competitions()
    row = c[(c["competition_name"] == name) & (c["season_name"] == season)].iloc[0]
    return int(row["competition_id"])


def _sid(name, season):
    c = sb.competitions()
    row = c[(c["competition_name"] == name) & (c["season_name"] == season)].iloc[0]
    return int(row["season_id"])


def build_grid(shots, moves, n_iter=60):
    """Learn the xT surface by value iteration."""
    shoot = np.zeros((GRID_W, GRID_H))
    goals = np.zeros((GRID_W, GRID_H))
    move = np.zeros((GRID_W, GRID_H))
    action = np.zeros((GRID_W, GRID_H))          # shots + moves per cell
    T = np.zeros((GRID_W, GRID_H, GRID_W, GRID_H))  # transition counts

    for _, s in shots.iterrows():
        cx, cy = _cell(s["x"], s["y"])
        shoot[cx, cy] += 1
        goals[cx, cy] += s["goal"]
        action[cx, cy] += 1
    for _, m in moves.iterrows():
        cx, cy = _cell(m["x"], m["y"])
        ex, ey = _cell(m["ex"], m["ey"])
        move[cx, cy] += 1
        action[cx, cy] += 1
        T[cx, cy, ex, ey] += 1

    with np.errstate(divide="ignore", invalid="ignore"):
        shoot_prob = np.where(action > 0, shoot / action, 0)
        move_prob = np.where(action > 0, move / action, 0)
        goal_prob = np.where(shoot > 0, goals / shoot, 0)   # P(goal | shot here)
        # normalise transition matrix per origin cell
        Tn = np.zeros_like(T)
        for i in range(GRID_W):
            for j in range(GRID_H):
                tot = T[i, j].sum()
                if tot > 0:
                    Tn[i, j] = T[i, j] / tot

    xT = np.zeros((GRID_W, GRID_H))
    score_term = shoot_prob * goal_prob
    for _ in range(n_iter):
        move_value = np.tensordot(Tn, xT, axes=([2, 3], [0, 1]))
        xT = score_term + move_prob * move_value
    return xT, {"shoot_prob": shoot_prob, "move_prob": move_prob,
                "goal_prob": goal_prob, "Tn": Tn}


def value_moves(moves, xT):
    """xT added by each move = xT(end) − xT(start), keep positive progressions."""
    vals = []
    for _, m in moves.iterrows():
        cx, cy = _cell(m["x"], m["y"])
        ex, ey = _cell(m["ex"], m["ey"])
        d = xT[ex, ey] - xT[cx, cy]
        vals.append(d)
    moves = moves.copy()
    moves["xt"] = vals
    return moves


def top_progressors(moves_valued, n=12):
    pos = moves_valued[moves_valued["xt"] > 0]
    g = (pos.groupby(["player", "team"])["xt"].sum()
         .reset_index().sort_values("xt", ascending=False).head(n))
    return g


def plot_surface(xT, out_path, title):
    fig, ax = plt.subplots(figsize=(11, 7), facecolor=BG)
    pitch = Pitch(pitch_type="statsbomb", pitch_color=BG, line_color=LINE, linewidth=1.2)
    pitch.draw(ax=ax)
    # xT is (GRID_W,GRID_H) over (x,y); imshow wants rows=y, cols=x
    grid = xT.T
    im = ax.imshow(grid, extent=[0, PITCH_X, 0, PITCH_Y], origin="lower",
                   cmap="inferno", alpha=0.85, aspect="auto", zorder=0.5)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Expected Threat", color=FG)
    cb.ax.yaxis.set_tick_params(color=MUTED)
    plt.setp(plt.getp(cb.ax.axes, "yticklabels"), color=MUTED)
    ax.set_title(title, color=FG, fontsize=14, pad=10)
    fig.savefig(out_path, dpi=130, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def run(competition, season, max_matches=120):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    print(f"Collecting events: {competition} {season} (up to {max_matches} matches)...")
    shots, moves, n = _collect(competition, season, max_matches)
    print(f"  {n} matches · {len(shots):,} shots · {len(moves):,} moves")

    xT, _ = build_grid(shots, moves)
    print(f"  xT surface built ({GRID_W}x{GRID_H}); peak xT = {xT.max():.3f}")

    moves_valued = value_moves(moves, xT)
    tops = top_progressors(moves_valued)

    # save grid + leaders
    np.save(os.path.join(MODELS_DIR, "xt_grid.npy"), xT)
    safe = f"{competition}_{season}".replace(" ", "_").replace("/", "-")
    surf = os.path.join(OUTPUT_DIR, f"xt_surface_{safe}.png")
    plot_surface(xT, surf, f"Expected Threat surface — {competition} {season}")

    leaders = [{"player": r["player"], "team": r["team"], "xt_added": round(float(r["xt"]), 2)}
               for _, r in tops.iterrows()]
    with open(os.path.join(OUTPUT_DIR, f"xt_leaders_{safe}.json"), "w") as f:
        json.dump(leaders, f, indent=2)

    print(f"\nTop ball progressors (total xT added):")
    for l in leaders[:8]:
        print(f"  {l['player']:<26} {l['team']:<18} {l['xt_added']:+.2f}")
    print(f"\nSaved surface -> {surf}")
    return xT, leaders


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("competition")
    ap.add_argument("season")
    ap.add_argument("--matches", type=int, default=120)
    args = ap.parse_args()
    run(args.competition, args.season, args.matches)
