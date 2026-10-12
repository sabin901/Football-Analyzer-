"""Auditable, date-blocked rolling-origin validation and future scenarios.

Fixed a priori model: 365-day venue goals, eight league-average prior matches.
No tuning on reported evaluation results. Reconstructed backtests use today's
corrected historical results, not a vintage data feed; they are not live trials.
"""

from collections import defaultdict
from datetime import date, datetime, timezone, timedelta
import math
import numpy as np
from dashboard_data import (
    LEAGUES,
    LIVE,
    read_json,
    write_json,
    current_season,
    normalized_name,
    standings,
    utc_now,
)
from workbench_data import OUT

MODEL = "venue-poisson-365d-prior8-v1"


def probabilities(lam, mu):
    a = np.array([math.exp(-lam) * lam**i / math.factorial(i) for i in range(20)])
    b = np.array([math.exp(-mu) * mu**i / math.factorial(i) for i in range(20)])
    grid = np.outer(a, b)
    grid /= grid.sum()
    return [float(np.tril(grid, -1).sum()), float(np.trace(grid)), float(np.triu(grid, 1).sum())]


def forecast(history, fixture, cutoff):
    start = (date.fromisoformat(cutoff) - timedelta(days=365)).isoformat()
    train = [m for m in history if start <= m["date"] < cutoff and m["hg"] is not None]
    if len(train) < 50:
        return None
    hg = sum(m["hg"] for m in train) / len(train)
    ag = sum(m["ag"] for m in train) / len(train)
    if hg <= 0 or ag <= 0:
        return None
    h = [m for m in train if normalized_name(m["home"]) == normalized_name(fixture["home"])]
    a = [m for m in train if normalized_name(m["away"]) == normalized_name(fixture["away"])]
    rate = lambda rows, k, mean: (sum(m[k] for m in rows) + 8 * mean) / (len(rows) + 8)
    lam = rate(h, "hg", hg) * rate(a, "hg", hg) / hg
    mu = rate(a, "ag", ag) * rate(h, "ag", ag) / ag
    counts = [
        sum(m["hg"] > m["ag"] for m in train),
        sum(m["hg"] == m["ag"] for m in train),
        sum(m["hg"] < m["ag"] for m in train),
    ]
    return {
        "home": fixture["home"],
        "away": fixture["away"],
        "date": fixture["date"],
        "cutoff_exclusive": cutoff,
        "training_start": min(m["date"] for m in train),
        "training_end": max(m["date"] for m in train),
        "sample": len(train),
        "home_sample": len(h),
        "away_sample": len(a),
        "home_rate": lam,
        "away_rate": mu,
        "probabilities": probabilities(lam, mu),
        "baseline": [(n + 1) / (len(train) + 3) for n in counts],
    }


def losses(p, actual):
    return {
        "log_loss": -math.log(max(1e-15, p[actual])),
        "brier": sum((v - int(i == actual)) ** 2 for i, v in enumerate(p)),
        "rps": sum((sum(p[: i + 1]) - int(actual <= i)) ** 2 for i in (0, 1)) / 2,
        "accuracy": int(max(range(3), key=lambda i: p[i]) == actual),
    }


def evaluate(records):
    if not records:
        return {"n": 0}
    scores = {
        name: [losses(r[name], r["actual"]) for r in records]
        for name in ("probabilities", "baseline", "uniform")
    }
    metrics = {
        name: {k: round(sum(s[k] for s in rows) / len(rows), 5) for k in rows[0]}
        for name, rows in scores.items()
    }
    bins = []
    for i in range(10):
        pairs = [
            (p, int(r["actual"] == j))
            for r in records
            for j, p in enumerate(r["probabilities"])
            if min(9, int(p * 10)) == i
        ]
        if pairs:
            bins.append(
                {
                    "bin": i,
                    "n": len(pairs),
                    "predicted": sum(p for p, y in pairs) / len(pairs),
                    "observed": sum(y for p, y in pairs) / len(pairs),
                }
            )
    # Resample date blocks to preserve within-matchday dependence.
    groups = defaultdict(list)
    for r, m, b in zip(records, scores["probabilities"], scores["baseline"]):
        groups[r["date"]].append(m["log_loss"] - b["log_loss"])
    totals = np.array([sum(v) for v in groups.values()])
    sizes = np.array([len(v) for v in groups.values()])
    rng = np.random.default_rng(901)
    idx = rng.integers(0, len(totals), size=(1000, len(totals)))
    delta = totals[idx].sum(axis=1) / sizes[idx].sum(axis=1)
    return {
        "n": len(records),
        "first_date": records[0]["date"],
        "last_date": records[-1]["date"],
        "metrics": metrics,
        "calibration": bins,
        "log_loss_delta_95ci": [float(x) for x in np.quantile(delta, [0.025, 0.975])],
        "note": "Negative model-minus-frequency log-loss difference is better. Date-block bootstrap, 1,000 replicates; descriptive interval only.",
    }


def season_scenarios(snapshot, history, cutoff):
    table = standings(snapshot["matches"])
    names = [r["team"] for r in table]
    index = {n: i for i, n in enumerate(names)}
    points = np.tile([r["pts"] for r in table], (2000, 1))
    gf = np.tile([r["gf"] for r in table], (2000, 1))
    ga = np.tile([r["ga"] for r in table], (2000, 1))
    rng = np.random.default_rng(901)
    simulated = 0
    omitted = 0
    for m in snapshot["matches"]:
        if m["hg"] is not None:
            continue
        if (
            not m.get("date")
            or m["date"] < cutoff
            or m.get("status") in ("abandoned", "cancelled", "postponed")
        ):
            omitted += 1
            continue
        p = forecast(history, m, cutoff)
        if not p:
            omitted += 1
            continue
        h = index[m["home"]]
        a = index[m["away"]]
        hs = rng.poisson(p["home_rate"], 2000)
        aws = rng.poisson(p["away_rate"], 2000)
        points[:, h] += 3 * (hs > aws) + (hs == aws)
        points[:, a] += 3 * (aws > hs) + (hs == aws)
        gf[:, h] += hs
        ga[:, h] += aws
        gf[:, a] += aws
        ga[:, a] += hs
        simulated += 1
    order = np.lexsort(
        (np.broadcast_to(np.arange(len(names)), points.shape), -gf, -(gf - ga), -points), axis=1
    )
    return {
        "runs": 2000,
        "simulated_fixtures": simulated,
        "omitted_fixtures": omitted,
        "seed": 901,
        "limitations": "Fixed team strengths, independent games. Points/GD/GF ordering; competition-specific head-to-head, deductions and disciplinary decisions not modeled. Top four is a rank, not guaranteed Champions League qualification.",
        "teams": [
            {
                "team": name,
                "mean_points": round(float(points[:, i].mean()), 1),
                "points_10": float(np.quantile(points[:, i], 0.1)),
                "points_90": float(np.quantile(points[:, i], 0.9)),
                "first": float((order[:, 0] == i).mean()),
                "top_four": float((order[:, :4] == i).any(axis=1).mean()),
            }
            for i, name in enumerate(names)
        ],
    }


def run():
    cutoff = datetime.now(timezone.utc).date().isoformat()
    for league in LEAGUES:
        history = []
        for path in sorted(LIVE.glob(f"dashboard_{league['id']}_*.json")):
            raw = read_json(path)
            history.extend(
                {**m, "season": raw["season"]} for m in raw["matches"] if m["hg"] is not None
            )
        history.sort(key=lambda m: m["date"])
        records = []
        for m in history:
            if m["date"] < "2024-07-01" or m["date"] >= cutoff:
                continue
            p = forecast(history, m, m["date"])
            if p:
                p.update(
                    actual=0 if m["hg"] > m["ag"] else 1 if m["hg"] == m["ag"] else 2,
                    uniform=[1 / 3] * 3,
                    season=m["season"],
                )
                records.append(p)
        snapshot = read_json(LIVE / f"dashboard_{league['id']}_{current_season()}.json")
        upcoming = []
        for m in snapshot["matches"]:
            if (
                m["hg"] is None
                and m.get("date")
                and cutoff
                <= m["date"]
                <= (date.fromisoformat(cutoff) + timedelta(days=14)).isoformat()
                and m.get("status") not in ("abandoned", "cancelled", "postponed")
            ):
                p = forecast(history, m, cutoff)
                if p:
                    upcoming.append(p)
        payload = {
            "model": MODEL,
            "league": league["id"],
            "season": current_season(),
            "as_of": cutoff,
            "built_at": utc_now(),
            "history_matches": len(history),
            "evaluation": evaluate(records),
            "by_season": {
                s: evaluate([r for r in records if r["season"] == s])
                for s in sorted({r["season"] for r in records})
            },
            "upcoming": upcoming,
            "scenarios": season_scenarios(snapshot, history, cutoff),
            "methodology": "365 preceding days; eight league-average prior venue games. Every evaluation date excludes all results on that date and later. Fixed parameters; no optimization on evaluation seasons. Current corrected results, not archived as-known-at-time feeds. No lineup, injury, tracking or market inputs.",
        }
        write_json(OUT / f"forecast_{league['id']}.json", payload)
        write_json(OUT / f"backtest_{league['id']}.json", {"model": MODEL, "records": records})
        print(
            league["id"],
            len(history),
            "historical results;",
            len(records),
            "evaluations;",
            len(upcoming),
            "upcoming",
            flush=True,
        )


if __name__ == "__main__":
    run()
