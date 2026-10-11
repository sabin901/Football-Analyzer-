"""
Match prediction — a Dixon-Coles Poisson model.

This is the classic, genuinely strong approach to football prediction. Each team
gets an attack strength and a defence strength; goals are modelled as Poisson,
with a home-advantage term and the Dixon-Coles low-score correction. From the
fitted strengths we produce, for any fixture:
  - a full scoreline probability matrix
  - 1X2 probabilities (home win / draw / away win)
  - the most likely scorelines
  - over/under 2.5 goals

It's validated with a proper time-split (train on the earlier part of a season,
predict the later part) and scored with accuracy, log-loss, and the Ranked
Probability Score (RPS) — the standard metric for ordered football outcomes —
benchmarked against the season's base rates.

Usage:
    python src/predict.py "Premier League" "2015/2016"       # train + validate
    python src/predict.py "La Liga" "2015/2016" --fixture "Barcelona" "Sevilla"
"""

import os
import sys
import json
import argparse
import warnings
from itertools import product

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
MATCHES_PATH = os.path.join(DATA_DIR, "matches.parquet")           # StatsBomb catalogue
RESULTS_HISTORY = os.path.join(DATA_DIR, "results_history.parquet")  # top-5 leagues, many seasons
MODEL_DIR = os.path.join(HERE, "..", "models")
MAX_GOALS = 10


def load_catalogue():
    """Combined match catalogue: the big top-5-league history (many seasons)
    plus any StatsBomb competition-seasons it doesn't already cover
    (World Cups, WSL, etc.). Carries shot columns when present (for xG basis)."""
    base = ["competition", "season", "home_team", "away_team",
            "home_score", "away_score", "date"]
    shots = ["home_shots", "away_shots", "home_sot", "away_sot"]
    frames = []
    if os.path.exists(RESULTS_HISTORY):
        rh = pd.read_parquet(RESULTS_HISTORY)
        frames.append(rh[[c for c in base + shots if c in rh.columns]])
    if os.path.exists(MATCHES_PATH):
        sb = pd.read_parquet(MATCHES_PATH)[base]
        if frames:
            have = set(map(tuple, frames[0][["competition", "season"]].drop_duplicates().values))
            sb = sb[~sb.apply(lambda r: (r["competition"], r["season"]) in have, axis=1)]
        frames.append(sb)
    if not frames:
        raise FileNotFoundError("No match catalogue found.")
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Dixon-Coles
# ---------------------------------------------------------------------------
def _dc_tau(i, j, lam, mu, rho):
    """Dixon-Coles low-score dependency correction."""
    if i == 0 and j == 0:
        return 1 - lam * mu * rho
    if i == 0 and j == 1:
        return 1 + lam * rho
    if i == 1 and j == 0:
        return 1 + mu * rho
    if i == 1 and j == 1:
        return 1 - rho
    return 1.0


def _neg_log_likelihood(params, teams, hi, ai, hg, ag, w):
    """Vectorised Dixon-Coles negative log-likelihood (fast)."""
    n = len(teams)
    attack = params[:n]; defence = params[n:2 * n]
    home_adv = params[2 * n]; rho = params[2 * n + 1]

    lam = np.exp(home_adv + attack[hi] + defence[ai])   # home goals rate
    mu = np.exp(attack[ai] + defence[hi])               # away goals rate

    # Dixon-Coles low-score correction, vectorised
    tau = np.ones_like(lam)
    m00 = (hg == 0) & (ag == 0); tau[m00] = 1 - lam[m00] * mu[m00] * rho
    m01 = (hg == 0) & (ag == 1); tau[m01] = 1 + lam[m01] * rho
    m10 = (hg == 1) & (ag == 0); tau[m10] = 1 + mu[m10] * rho
    m11 = (hg == 1) & (ag == 1); tau[m11] = 1 - rho
    tau = np.maximum(tau, 1e-10)

    ll = w * (np.log(tau) + poisson.logpmf(hg, lam) + poisson.logpmf(ag, mu))
    return -ll.sum()


def _neg_poisson_deviance(params, teams, hi, ai, yh, ya, w):
    """Loss for fitting ratings to CONTINUOUS expected goals (xG basis).
    Poisson deviance Σ (λ − y·logλ), valid for non-integer targets."""
    n = len(teams)
    attack = params[:n]; defence = params[n:2 * n]; home_adv = params[2 * n]
    lam = np.exp(home_adv + attack[hi] + defence[ai])
    mu = np.exp(attack[ai] + defence[hi])
    loss = w * ((lam - yh * np.log(lam)) + (mu - ya * np.log(mu)))
    return loss.sum()


def _recency_weights(train, half_life_days):
    """exp decay so recent matches count more. half_life_days=None → all 1.0."""
    if not half_life_days:
        return np.ones(len(train))
    dates = pd.to_datetime(train["date"], errors="coerce")
    ref = dates.max()
    age = (ref - dates).dt.days.fillna(0).values
    return np.power(0.5, age / float(half_life_days))


def expected_goals_from_shots(train):
    """Per-match expected goals from shots on target, calibrated so total
    xG ≈ total goals on the training set. A shots-based ExpG proxy — teams are
    then rated by chance quality, not the goals they happened to convert."""
    need = {"home_sot", "away_sot"}
    if not need.issubset(train.columns):
        return None
    sot_h = train["home_sot"].astype("float"); sot_a = train["away_sot"].astype("float")
    if sot_h.isna().mean() > 0.2 or sot_a.isna().mean() > 0.2:
        return None
    sot_h = sot_h.fillna(sot_h.mean()); sot_a = sot_a.fillna(sot_a.mean())
    total_goals = train["home_score"].sum() + train["away_score"].sum()
    total_sot = sot_h.sum() + sot_a.sum()
    if total_sot <= 0:
        return None
    conv = total_goals / total_sot          # average SoT→goal conversion
    return sot_h.values * conv, sot_a.values * conv


def fit(train, half_life_days=None, basis="goals"):
    """Fit team attack/defence (+ home advantage) on a DataFrame of matches.

    basis="goals": classic Dixon-Coles Poisson on actual goals.
    basis="xg":    ratings fit to a shots-based expected-goals proxy, so a team
                   is judged by the chances it creates/concedes rather than the
                   goals it converted. Falls back to goals if shots are absent.
    half_life_days: recency weighting (recent matches count more).
    """
    teams = sorted(set(train["home_team"]).union(train["away_team"]))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    hi = train["home_team"].map(idx).values
    ai = train["away_team"].map(idx).values
    hg = train["home_score"].values
    ag = train["away_score"].values
    w = _recency_weights(train, half_life_days)
    cons = [{"type": "eq", "fun": lambda p: np.sum(p[:n])}]

    xg = expected_goals_from_shots(train) if basis == "xg" else None
    if basis == "xg" and xg is not None:
        yh, ya = xg
        x0 = np.concatenate([np.zeros(n), np.zeros(n), [0.25]])
        res = minimize(_neg_poisson_deviance, x0, args=(teams, hi, ai, yh, ya, w),
                       constraints=cons, method="SLSQP",
                       options={"maxiter": 200, "ftol": 1e-6})
        p = res.x
        return {"teams": teams, "idx": idx, "attack": p[:n], "defence": p[n:2 * n],
                "home_adv": float(p[2 * n]), "rho": 0.0, "basis": "xg"}

    # goals basis (Dixon-Coles)
    x0 = np.concatenate([np.zeros(n), np.zeros(n), [0.25], [-0.1]])
    res = minimize(_neg_log_likelihood, x0, args=(teams, hi, ai, hg, ag, w),
                   constraints=cons, method="SLSQP",
                   options={"maxiter": 200, "ftol": 1e-6})
    p = res.x
    return {"teams": teams, "idx": idx, "attack": p[:n], "defence": p[n:2 * n],
            "home_adv": float(p[2 * n]), "rho": float(p[2 * n + 1]), "basis": "goals"}


def score_matrix(model, home, away):
    """P(home i goals, away j goals) matrix up to MAX_GOALS."""
    idx = model["idx"]
    if home not in idx or away not in idx:
        return None
    hi, ai = idx[home], idx[away]
    lam = np.exp(model["home_adv"] + model["attack"][hi] + model["defence"][ai])
    mu = np.exp(model["attack"][ai] + model["defence"][hi])
    rho = model["rho"]

    mat = np.zeros((MAX_GOALS + 1, MAX_GOALS + 1))
    for i, j in product(range(MAX_GOALS + 1), repeat=2):
        mat[i, j] = (_dc_tau(i, j, lam, mu, rho)
                     * poisson.pmf(i, lam) * poisson.pmf(j, mu))
    mat /= mat.sum()
    return mat


def predict(model, home, away):
    mat = score_matrix(model, home, away)
    if mat is None:
        return None
    p_home = float(np.tril(mat, -1).sum())   # home goals > away goals
    p_away = float(np.triu(mat, 1).sum())    # away goals > home goals
    p_draw = float(np.trace(mat))
    # most likely scorelines
    flat = [((i, j), mat[i, j]) for i in range(MAX_GOALS + 1) for j in range(MAX_GOALS + 1)]
    flat.sort(key=lambda z: -z[1])
    top = [{"score": f"{i}-{j}", "p": round(p, 3)} for (i, j), p in flat[:5]]
    over25 = float(sum(mat[i, j] for i in range(MAX_GOALS + 1)
                       for j in range(MAX_GOALS + 1) if i + j > 2.5))
    return {
        "home": home, "away": away,
        "p_home": round(p_home, 3), "p_draw": round(p_draw, 3),
        "p_away": round(p_away, 3),
        "most_likely": top,
        "expected_home_goals": round(float((mat.sum(axis=1) * np.arange(MAX_GOALS + 1)).sum()), 2),
        "expected_away_goals": round(float((mat.sum(axis=0) * np.arange(MAX_GOALS + 1)).sum()), 2),
        "over_2_5": round(over25, 3), "under_2_5": round(1 - over25, 3),
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _outcome(h, a):
    return 0 if h > a else (1 if h == a else 2)   # H, D, A


def _rps(probs, outcome):
    """Ranked Probability Score for ordered [H, D, A]. Lower is better."""
    cum_p, cum_o, s = 0.0, 0.0, 0.0
    for k in range(3):
        cum_p += probs[k]
        cum_o += 1.0 if k == outcome else 0.0
        s += (cum_p - cum_o) ** 2
    return s / 2.0


def validate(competition, season, train_frac=0.65, half_life_days=None, basis="goals"):
    m = load_catalogue()
    df = m[(m["competition"] == competition) & (m["season"] == season)].copy()
    if df.empty:
        raise ValueError(f"No matches for {competition} {season}")
    df = df.sort_values("date").reset_index(drop=True)
    split = int(len(df) * train_frac)
    train, test = df.iloc[:split], df.iloc[split:]

    model = fit(train, half_life_days=half_life_days, basis=basis)

    # Base-rate baseline from the training set
    base = np.array([
        (train.apply(lambda r: _outcome(r.home_score, r.away_score), axis=1) == k).mean()
        for k in range(3)])

    rows = []
    acc = base_acc = 0
    ll = base_ll = 0.0
    rps = base_rps = 0.0
    n = 0
    for _, r in test.iterrows():
        pred = predict(model, r["home_team"], r["away_team"])
        if pred is None:
            continue
        probs = [pred["p_home"], pred["p_draw"], pred["p_away"]]
        o = _outcome(r["home_score"], r["away_score"])
        n += 1
        acc += (int(np.argmax(probs)) == o)
        base_acc += (int(np.argmax(base)) == o)
        ll += -np.log(max(probs[o], 1e-12))
        base_ll += -np.log(max(base[o], 1e-12))
        rps += _rps(probs, o)
        base_rps += _rps(base, o)

    metrics = {
        "competition": competition, "season": season,
        "train_matches": len(train), "test_matches": n,
        "accuracy": round(acc / n, 3),
        "baseline_accuracy": round(base_acc / n, 3),
        "log_loss": round(ll / n, 4),
        "baseline_log_loss": round(base_ll / n, 4),
        "rps": round(rps / n, 4),
        "baseline_rps": round(base_rps / n, 4),
        "home_advantage": round(model["home_adv"], 3),
        "half_life_days": half_life_days,
    }
    return model, metrics


def team_ratings(model, top=10):
    """Readable attack/defence table."""
    rows = []
    for t in model["teams"]:
        i = model["idx"][t]
        rows.append((t, model["attack"][i], model["defence"][i]))
    rows.sort(key=lambda z: -z[1])
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("competition")
    ap.add_argument("season")
    ap.add_argument("--fixture", nargs=2, metavar=("HOME", "AWAY"))
    args = ap.parse_args()

    model, metrics = validate(args.competition, args.season)
    print("=== Validation (time-split) ===")
    print(json.dumps(metrics, indent=2))
    print(f"\nModel beats baseline on RPS: "
          f"{metrics['rps'] < metrics['baseline_rps']} "
          f"({metrics['rps']} vs {metrics['baseline_rps']})")

    print("\n=== Strongest attacks (fitted) ===")
    for t, a, d in team_ratings(model)[:6]:
        print(f"  {t:<24} attack {a:+.2f}  defence {d:+.2f}")

    if args.fixture:
        print(f"\n=== Prediction: {args.fixture[0]} vs {args.fixture[1]} ===")
        pr = predict(model, args.fixture[0], args.fixture[1])
        print(json.dumps(pr, indent=2))
