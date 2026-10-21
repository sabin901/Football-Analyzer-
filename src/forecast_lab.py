"""Auditable, date-blocked rolling-origin validation and future scenarios.

Fixed a priori model: 365-day venue goals, eight league-average prior matches.
No tuning on reported evaluation results. Reconstructed backtests use today's
corrected historical results, not a vintage data feed; they are not live trials.
"""

from collections import defaultdict
from datetime import date, datetime, timezone, timedelta
import math
import os
import numpy as np
from dashboard_data import (
    LEAGUES,
    LIVE,
    read_json,
    write_json,
    current_season,
    standings,
    utc_now,
)
from open_policy import WORKBENCH as OUT, provenance, validate_public
from forecast_benchmarks import Challengers, SPECIFICATIONS
import hashlib
import json
from club_identity import club_key
from data_quality import quality_for

MODEL = "venue-poisson-365d-prior8-open-v3"


def score_grid(lam, mu):
    if not all(math.isfinite(v) and 0 < v <= 20 for v in (lam, mu)):
        raise ValueError("Goal rates must be finite and within (0, 20]")
    # Adaptive tail supports extreme stress tests as well as football-sized rates.
    size = max(20, int(max(lam, mu) + 12 * math.sqrt(max(lam, mu)) + 1))
    a = np.array([math.exp(-lam) * lam**i / math.factorial(i) for i in range(size)])
    b = np.array([math.exp(-mu) * mu**i / math.factorial(i) for i in range(size)])
    grid = np.outer(a, b)
    return grid / grid.sum()


def probabilities(lam, mu):
    grid = score_grid(lam, mu)
    return [float(np.tril(grid, -1).sum()), float(np.trace(grid)), float(np.triu(grid, 1).sum())]


def score_summary(lam, mu):
    grid = score_grid(lam, mu)
    cells = sorted(((i, j, float(p)) for (i, j), p in np.ndenumerate(grid)), key=lambda c: -c[2])
    top = [{"home": i, "away": j, "probability": p} for i, j, p in cells[:5]]
    return {
        "scorelines": top,
        "other_scorelines": 1 - sum(c["probability"] for c in top),
        "both_score": float(grid[1:, 1:].sum()),
        "over_2_5": sum(p for i, j, p in cells if i + j >= 3),
    }


def forecast(history, fixture, cutoff):
    start = (date.fromisoformat(cutoff) - timedelta(days=365)).isoformat()
    train = [
        m
        for m in history
        if start <= m["date"] < cutoff and m["hg"] is not None and not m.get("exclude_from_model")
    ]
    if len(train) < 50:
        return None
    hg = sum(m["hg"] for m in train) / len(train)
    ag = sum(m["ag"] for m in train) / len(train)
    if hg <= 0 or ag <= 0:
        return None
    h = [m for m in train if club_key(m["home"]) == club_key(fixture["home"])]
    a = [m for m in train if club_key(m["away"]) == club_key(fixture["away"])]
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
        "sample_status": "limited" if min(len(h), len(a)) < 5 else "established",
        "prior_weight_home": 8 / (len(h) + 8),
        "prior_weight_away": 8 / (len(a) + 8),
        "home_rate": lam,
        "away_rate": mu,
        "probabilities": probabilities(lam, mu),
        "score_summary": score_summary(lam, mu),
        "baseline": [(n + 1) / (len(train) + 3) for n in counts],
    }


def losses(p, actual):
    return {
        "log_loss": -math.log(max(1e-15, p[actual])),
        "brier": sum((v - int(i == actual)) ** 2 for i, v in enumerate(p)),
        "rps": sum((sum(p[: i + 1]) - int(actual <= i)) ** 2 for i in (0, 1)) / 2,
        "accuracy": (
            (1 / sum(abs(v - max(p)) < 1e-12 for v in p)) if abs(p[actual] - max(p)) < 1e-12 else 0
        ),
    }


def comparison_intervals(records, scores):
    output = {}
    for name, competitor in scores.items():
        if name == "probabilities":
            continue
        groups = defaultdict(list)
        for r, model, challenger in zip(records, scores["probabilities"], competitor):
            groups[r["date"]].append(model["log_loss"] - challenger["log_loss"])
        totals = np.array([sum(v) for v in groups.values()])
        sizes = np.array([len(v) for v in groups.values()])
        idx = np.random.default_rng(901).integers(0, len(totals), size=(1000, len(totals)))
        output[name] = np.quantile(
            totals[idx].sum(axis=1) / sizes[idx].sum(axis=1), [0.025, 0.975]
        ).tolist()
    return output


def evaluate(records):
    if not records:
        return {"n": 0}
    scores = {
        name: [losses(r[name], r["actual"]) for r in records]
        for name in ("probabilities", "baseline", "uniform", "elo", "fitted_poisson")
        if all(name in r for r in records)
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
        "calibration_by_outcome": {
            label: [
                {
                    "bin": i,
                    "n": len(pairs),
                    "predicted": sum(p for p, y in pairs) / len(pairs),
                    "observed": sum(y for p, y in pairs) / len(pairs),
                }
                for i in range(10)
                if (
                    pairs := [
                        (r["probabilities"][j], int(r["actual"] == j))
                        for r in records
                        if min(9, int(r["probabilities"][j] * 10)) == i
                    ]
                )
            ]
            for j, label in enumerate(["home", "draw", "away"])
        },
        "comparison_95ci": comparison_intervals(records, scores),
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
        "complete_schedule": omitted == 0,
        "seed": 901,
        "limitations": "Fixed team strengths, independent games. Points/GD/GF ordering; competition-specific head-to-head, deductions and disciplinary decisions not modeled. Top four is a rank, not guaranteed Champions League qualification.",
        "teams": [
            {
                "team": name,
                "mean_points": round(float(points[:, i].mean()), 1),
                "points_10": float(np.quantile(points[:, i], 0.1)),
                "points_90": float(np.quantile(points[:, i], 0.9)),
                "first": float((order[:, 0] == i).mean()) if omitted == 0 else None,
                "top_four": float((order[:, :4] == i).any(axis=1).mean()) if omitted == 0 else None,
            }
            for i, name in enumerate(names)
        ],
    }


def publication_gate(snapshot, quality, now=None):
    now = now or datetime.now(timezone.utc)
    if snapshot.get("source_id") == "openfootball":
        try:
            validate_public(snapshot)
            times = [
                datetime.fromisoformat(snapshot["fetched_at"]),
                datetime.fromisoformat(quality["checked_at"]),
            ]
            from data_quality import results_digest

            if quality.get("results_digest") != results_digest(snapshot["matches"]):
                raise ValueError("Quality record does not match results")
            if any(not 0 <= (now - t).total_seconds() <= 36 * 3600 for t in times):
                raise ValueError("Snapshot older than 36 hours")
            if snapshot.get("quarantined"):
                raise ValueError("Source contains quarantined records")
            if len(snapshot["matches"]) != snapshot.get("expected_fixtures"):
                raise ValueError("Source schedule is incomplete")
            if quality.get("results", {}).get("past_missing"):
                raise ValueError("Past fixtures have missing results")
            if quality.get("results", {}).get("status") != "structural_checks_passed":
                raise ValueError("Structural checks unavailable")
        except (ValueError, KeyError, TypeError) as exc:
            return {"allowed": False, "reason": str(exc)}
        return {
            "allowed": True,
            "valid_until": (min(times) + timedelta(hours=36)).isoformat(),
            "reason": "Structurally checked community source; not independently verified or suitable for betting decisions.",
        }
    if quality.get("standings", {}).get("status") != "matched":
        return {
            "allowed": False,
            "reason": "The current results and provider standings have not reconciled.",
        }
    result = quality.get("results", {})
    if result.get("status") not in {"matched", "reviewed", "partial"} or any(
        x["source"] == "local" for x in result.get("unmatched", [])
    ):
        return {
            "allowed": False,
            "reason": "Result verification is incomplete or contains unresolved discrepancies.",
        }
    try:
        times = [
            datetime.fromisoformat(snapshot["fetched_at"]),
            datetime.fromisoformat(quality["checked_at"]),
        ]
        if any(not 0 <= (now - t).total_seconds() <= 36 * 3600 for t in times):
            raise ValueError("Expired data")
    except (KeyError, ValueError, TypeError):
        return {
            "allowed": False,
            "reason": "A fresh result snapshot and verification record are required.",
        }
    return {
        "allowed": True,
        "valid_until": (min(times) + timedelta(hours=36)).isoformat(),
        "reason": "Standings reconciled; no unresolved score conflicts. Second-source coverage may lag recent results.",
    }


def update_forecast_log(previous, upcoming, snapshot, recorded_at):
    """Freeze the first pre-date forecast; never reconstruct one after the outcome."""
    import copy

    rows = copy.deepcopy([r for r in previous.get("records", []) if r.get("model") == MODEL])
    known = {(r["model"], r["date"], r["home"], r["away"]) for r in rows}
    for p in upcoming:
        key = (MODEL, p["date"], p["home"], p["away"])
        if p["date"] <= recorded_at[:10] or key in known:
            continue
        rows.append({**p, "model": MODEL, "recorded_at": recorded_at, "season": snapshot["season"]})
        known.add(key)
    matches = {(m["home"], m["away"]): m for m in snapshot["matches"]}
    for r in rows:
        m = matches.get((r["home"], r["away"])) if r["season"] == snapshot["season"] else None
        if m is None:
            continue
        r.pop("actual", None)
        if r["recorded_at"][:10] >= r["date"]:
            r["status"] = "ineligible"
        elif m["date"] != r["date"]:
            r["status"] = "rescheduled"
        elif m.get("exclude_from_model"):
            r["status"] = "administrative result"
        elif m["hg"] is not None:
            r["status"] = "settled"
            r["actual"] = 0 if m["hg"] > m["ag"] else 1 if m["hg"] == m["ag"] else 2
        else:
            r["status"] = "pending"
    settled = [r for r in rows if r.get("status") == "settled"]
    return {"schema_version": 1, "records": rows}, {
        "recorded": len(rows),
        "settled": len(settled),
        "metrics": (
            {
                k: sum(losses(r["probabilities"], r["actual"])[k] for r in settled) / len(settled)
                for k in ("log_loss", "brier", "rps")
            }
            if settled
            else None
        ),
        "accuracy": (
            sum(losses(r["probabilities"], r["actual"])["accuracy"] for r in settled) / len(settled)
            if settled
            else None
        ),
    }


def run():
    cutoff = datetime.now(timezone.utc).date().isoformat()
    for league in LEAGUES:
        history = []
        for path in sorted(LIVE.glob(f"dashboard_{league['id']}_*.json")):
            raw = validate_public(read_json(path))
            history.extend(
                {**m, "season": raw["season"]}
                for m in raw["matches"]
                if m["hg"] is not None and not m.get("exclude_from_model")
            )
        history.sort(key=lambda m: m["date"])
        records = []
        challengers = Challengers(history)
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
                p.update(challengers.predict(m, m["date"]))
                records.append(p)
        snapshot = read_json(LIVE / f"dashboard_{league['id']}_{current_season()}.json")
        quality = quality_for(snapshot)
        publication = publication_gate(snapshot, quality)
        upcoming = []
        for m in snapshot["matches"]:
            if (
                publication["allowed"]
                and m["hg"] is None
                and m.get("date")
                and cutoff
                < m["date"]
                <= (date.fromisoformat(cutoff) + timedelta(days=14)).isoformat()
                and m.get("status") not in ("abandoned", "cancelled", "postponed")
            ):
                p = forecast(history, m, cutoff)
                if p:
                    p.update(challengers.predict(m, cutoff))
                    upcoming.append(p)
        built_at = utc_now()
        log_path = OUT / f"forecast_log_{league['id']}.json"
        log, prospective = update_forecast_log(
            read_json(log_path, {}),
            upcoming if os.environ.get("FOOTLYZER_RECORD_FORECASTS") == "1" else [],
            snapshot,
            built_at,
        )
        write_json(
            log_path,
            {
                **provenance("openfootball"),
                "source_url": snapshot["source_url"],
                "source_sha256": snapshot["source_sha256"],
                **log,
            },
        )
        provenance_record = {
            **provenance("openfootball"),
            "source_url": "https://github.com/openfootball/football.json",
            "source_sha256": hashlib.sha256(
                json.dumps(history, sort_keys=True).encode()
            ).hexdigest(),
            "source_hash_scope": "normalized historical training rows",
            "benchmark_specs": SPECIFICATIONS,
        }
        payload = {
            **provenance_record,
            "model": MODEL,
            "league": league["id"],
            "season": current_season(),
            "as_of": cutoff,
            "built_at": built_at,
            "publication": publication,
            "prospective": prospective,
            "history_matches": len(history),
            "evaluation": evaluate(records),
            "by_sample": {
                label: evaluate([r for r in records if r["sample_status"] == label])
                for label in ("limited", "established")
            },
            "by_season": {
                s: evaluate([r for r in records if r["season"] == s])
                for s in sorted({r["season"] for r in records})
            },
            "upcoming": upcoming,
            "source_quality": {
                "checked_at": quality.get("checked_at"),
                "result_status": quality.get("results", {}).get("status"),
            },
            "methodology": "365 preceding days; eight league-average prior venue games. Every evaluation date excludes all results on that date and later. Fixed parameters; no optimization on evaluation seasons. Current corrected results, not archived as-known-at-time feeds. No lineup, injury, tracking or market inputs.",
        }
        write_json(OUT / f"forecast_{league['id']}.json", payload)
        write_json(
            OUT / f"backtest_{league['id']}.json",
            {**provenance_record, "model": MODEL, "records": records},
        )
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
