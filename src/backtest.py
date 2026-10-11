"""
Full backtest of the predictor across every league-season.

One time-split per season is a demo. This runs the predictor over all 115
top-5-league seasons (2002/03–2024/25), both rating bases:
  - goals: classic Dixon-Coles on actual goals
  - xg:    ratings from a shots-based expected-goals proxy (chance quality)

For each season it time-splits (train early, predict late), scores with the
Ranked Probability Score, accuracy and log-loss, and compares every model to
the base-rate baseline. Aggregated results + a comparison plot go to output/.

Usage:
    python src/backtest.py
    python src/backtest.py --stats     # print the saved summary
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
import predict as predictor

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUTPUT_DIR = os.path.join(ROOT, "output")
MODELS_DIR = os.path.join(ROOT, "models")
RESULTS_CSV = os.path.join(OUTPUT_DIR, "backtest_results.csv")
SUMMARY_JSON = os.path.join(MODELS_DIR, "backtest.json")

MAJOR = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
BG, FG, MUTED, LINE = "#0f141b", "#eef2f7", "#93a0b1", "#242d39"


def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    cat = predictor.load_catalogue()
    cat = cat[cat["competition"].isin(MAJOR)]
    pairs = (cat.groupby(["competition", "season"]).size()
             .reset_index(name="n"))
    pairs = pairs[pairs["n"] >= 180].sort_values(["competition", "season"])

    rows = []
    print(f"Backtesting {len(pairs)} league-seasons (goals vs xG basis)…")
    for k, (_, r) in enumerate(pairs.iterrows(), 1):
        comp, se = r["competition"], r["season"]
        rec = {"competition": comp, "season": se, "matches": int(r["n"])}
        for basis in ("goals", "xg"):
            try:
                _, m = predictor.validate(comp, se, half_life_days=90, basis=basis)
                rec[f"{basis}_rps"] = m["rps"]
                rec[f"{basis}_acc"] = m["accuracy"]
                rec[f"{basis}_ll"] = m["log_loss"]
                rec["base_rps"] = m["baseline_rps"]
                rec["base_acc"] = m["baseline_accuracy"]
            except Exception:
                rec[f"{basis}_rps"] = None
        rows.append(rec)
        if k % 15 == 0 or k == len(pairs):
            print(f"  {k}/{len(pairs)} done")

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_CSV, index=False)

    def agg(col):
        v = df[col].dropna()
        return round(float(v.mean()), 4), len(v)

    g_rps, ng = agg("goals_rps"); x_rps, nx = agg("xg_rps")
    g_acc, _ = agg("goals_acc"); x_acc, _ = agg("xg_acc")
    b_rps, _ = agg("base_rps"); b_acc, _ = agg("base_acc")
    both = df.dropna(subset=["goals_rps", "xg_rps"])
    xg_wins = int((both["xg_rps"] < both["goals_rps"]).sum())
    beat_base = int((df["goals_rps"].dropna() < df.loc[df["goals_rps"].notna(), "base_rps"]).sum())

    summary = {
        "league_seasons": int(len(df)),
        "goals_basis": {"mean_rps": g_rps, "mean_accuracy": g_acc, "seasons": ng},
        "xg_basis": {"mean_rps": x_rps, "mean_accuracy": x_acc, "seasons": nx},
        "baseline": {"mean_rps": b_rps, "mean_accuracy": b_acc},
        "seasons_goals_beats_baseline": beat_base,
        "seasons_xg_beats_goals": xg_wins,
        "xg_vs_goals_seasons_compared": int(len(both)),
        "best_basis": "xg" if x_rps < g_rps else "goals",
    }
    with open(SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    _plot(df, both)
    print("\n=== BACKTEST SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"\nSaved: {RESULTS_CSV}\n       {SUMMARY_JSON}")
    return summary


def _plot(df, both):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2), facecolor=BG)
    for ax in (ax1, ax2):
        ax.set_facecolor(BG); ax.tick_params(colors=MUTED)
        for sp in ax.spines.values(): sp.set_color(LINE)
        ax.grid(alpha=.12)
    # 1) RPS distribution vs baseline
    g = df["goals_rps"].dropna(); b = df["base_rps"].dropna()
    ax1.hist(b, bins=20, color="#5b6775", alpha=.7, label=f"baseline (μ={b.mean():.3f})")
    ax1.hist(g, bins=20, color="#4ea1ff", alpha=.8, label=f"model (μ={g.mean():.3f})")
    ax1.axvline(g.mean(), color="#4ea1ff", lw=2); ax1.axvline(b.mean(), color="#5b6775", lw=2)
    ax1.set_title("Model RPS vs baseline — 115 league-seasons", color=FG, fontsize=12)
    ax1.set_xlabel("RPS (lower is better)", color=MUTED)
    ax1.legend(facecolor=BG, edgecolor=LINE, labelcolor=FG, fontsize=9)
    # 2) goals vs xG basis per season
    ax2.scatter(both["goals_rps"], both["xg_rps"], s=28, color="#46d19e", alpha=.75, edgecolors=BG)
    lo = min(both["goals_rps"].min(), both["xg_rps"].min()) - .005
    hi = max(both["goals_rps"].max(), both["xg_rps"].max()) + .005
    ax2.plot([lo, hi], [lo, hi], "--", color=MUTED)
    ax2.set_title("xG-basis vs goals-basis RPS (per season)", color=FG, fontsize=12)
    ax2.set_xlabel("goals-basis RPS", color=MUTED); ax2.set_ylabel("xG-basis RPS", color=MUTED)
    ax2.annotate("below line = xG basis better", (hi, lo), color=MUTED, fontsize=9,
                 ha="right", va="bottom")
    fig.savefig(os.path.join(OUTPUT_DIR, "backtest.png"), dpi=130, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    if args.stats and os.path.exists(SUMMARY_JSON):
        print(json.dumps(json.load(open(SUMMARY_JSON)), indent=2))
    else:
        run()
