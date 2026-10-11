"""
Benchmark the predictor against the betting market.

The bookmakers' closing odds are the single hardest baseline in football
prediction — a model is only credible once it's compared to them. This script
does exactly that, self-contained on one odds file:

  1. load a league-season of results + odds (from `python src/live_api.py odds`)
  2. time-split: fit the Dixon-Coles model on the earlier matches
  3. for each later match, compute BOTH the model's 1X2 probabilities and the
     market's implied probabilities (de-vigged from the bookmaker odds)
  4. score both with the Ranked Probability Score (RPS) and log-loss

Output tells you how close the model gets to the market — the honest measure of
whether it's any good.

Usage:
    # first pull odds (needs open internet — your machine or a GitHub runner):
    python src/live_api.py odds E0 2324
    # then benchmark:
    python src/benchmark.py data/live/odds_E0_2324.parquet
"""

import os
import sys
import json
import argparse
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import predict as predictor


def devig(oh, od, oa):
    """Decimal odds -> normalised (vig-removed) implied probabilities [H,D,A]."""
    inv = np.array([1.0 / oh, 1.0 / od, 1.0 / oa])
    return inv / inv.sum()


def _rps(p, outcome):
    cum_p = cum_o = s = 0.0
    for k in range(3):
        cum_p += p[k]
        cum_o += 1.0 if k == outcome else 0.0
        s += (cum_p - cum_o) ** 2
    return s / 2.0


def _outcome(h, a):
    return 0 if h > a else (1 if h == a else 2)


def load_odds(path):
    """Normalise an odds file into the columns the predictor expects."""
    df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    # prefer Bet365, fall back to market average
    oh = "B365H" if "B365H" in df.columns else "AvgH"
    od = "B365D" if "B365D" in df.columns else "AvgD"
    oa = "B365A" if "B365A" in df.columns else "AvgA"
    need = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", oh, od, oa]
    df = df[[c for c in need if c in df.columns]].dropna()
    df = df.rename(columns={"HomeTeam": "home_team", "AwayTeam": "away_team",
                            "FTHG": "home_score", "FTAG": "away_score",
                            "Date": "date", oh: "oh", od: "od", oa: "oa"})
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    for c in ("home_score", "away_score"):
        df[c] = df[c].astype(int)
    return df


def benchmark(path, train_frac=0.5, half_life_days=90):
    df = load_odds(path)
    if len(df) < 60:
        raise ValueError("Not enough matches with odds to benchmark.")
    split = int(len(df) * train_frac)
    train, test = df.iloc[:split], df.iloc[split:]

    model = predictor.fit(train, half_life_days=half_life_days)

    m_rps = k_rps = 0.0
    m_ll = k_ll = 0.0
    closer = n = 0
    for _, r in test.iterrows():
        pred = predictor.predict(model, r["home_team"], r["away_team"])
        if not pred:
            continue
        model_p = [pred["p_home"], pred["p_draw"], pred["p_away"]]
        market_p = devig(r["oh"], r["od"], r["oa"]).tolist()
        o = _outcome(r["home_score"], r["away_score"])
        n += 1
        mr, kr = _rps(model_p, o), _rps(market_p, o)
        m_rps += mr; k_rps += kr
        m_ll += -np.log(max(model_p[o], 1e-12))
        k_ll += -np.log(max(market_p[o], 1e-12))
        closer += (mr <= kr)

    res = {
        "file": os.path.basename(path),
        "test_matches": n,
        "model_rps": round(m_rps / n, 4),
        "market_rps": round(k_rps / n, 4),
        "model_log_loss": round(m_ll / n, 4),
        "market_log_loss": round(k_ll / n, 4),
        "pct_matches_model_at_least_as_good": round(100 * closer / n, 1),
        "gap_to_market_rps": round((m_rps - k_rps) / n, 4),
    }
    return res


def _self_test():
    """Verify the RPS + de-vig math on known values (runs with no data)."""
    # de-vig: fair 2.0/3.5/4.0 odds should normalise to sum 1
    p = devig(2.0, 3.5, 4.0)
    assert abs(p.sum() - 1.0) < 1e-9, "de-vig must normalise"
    # perfect forecast has RPS 0; worst (all mass on wrong end) has RPS 1
    assert _rps([1, 0, 0], 0) == 0.0
    assert abs(_rps([0, 0, 1], 0) - 1.0) < 1e-9
    # a 50/30/20 forecast when home wins
    r = _rps([0.5, 0.3, 0.2], 0)
    assert 0 < r < 0.2
    print("self-test OK: de-vig normalises, RPS bounds correct, "
          f"sample RPS([.5,.3,.2]|home win) = {r:.4f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("odds_file", nargs="?", help="odds parquet/csv from live_api.py odds")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test or not args.odds_file:
        _self_test()
        if not args.odds_file:
            print("\nNo odds file given. Pull one first on a machine with internet:")
            print("  python src/live_api.py odds E0 2324")
            print("  python src/benchmark.py data/live/odds_E0_2324.parquet")
            sys.exit(0)

    res = benchmark(args.odds_file)
    print(json.dumps(res, indent=2))
    verdict = ("MATCHES/BEATS the market" if res["model_rps"] <= res["market_rps"]
               else "trails the market")
    print(f"\nModel {verdict}: RPS {res['model_rps']} vs market {res['market_rps']} "
          f"(market is the hardest baseline; close is good).")
