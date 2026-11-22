"""Fetch only the explicitly CC0 OpenFootball archive; never supplement restricted feeds."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import argparse
import hashlib
import requests
from dashboard_data import (
    LEAGUES,
    current_season,
    parse_openfootball,
    utc_now,
    write_json,
    read_json,
)
from open_policy import RESULTS, OPEN, provenance, validate_public
from data_quality import results_digest


def apply_competition_context(snapshot):
    """Annotate the curtailed French season without inventing scores or dates.

    Keep the source fingerprint and acquisition time. This is a separately cited
    competition decision, applied only to the known complete 279-result archive.
    """
    if (snapshot.get("league"), snapshot.get("season")) != ("FL1", "2019-20"):
        return False
    matches = snapshot["matches"]
    played = [m for m in matches if m["hg"] is not None]
    if len(matches) != 380 or len(played) != 279 or any(m["date"] > "2020-03-08" for m in played):
        return False
    context = {
        "note": "The 2019/20 Ligue 1 season ended early after 279 matches. The 101 unplayed fixtures were cancelled, not missing results. This table shows match points, not the official points-per-game ranking.",
        "source_url": "https://www.lfp.fr/assets/20200430_PV_Conseil_Administration_LFP_e824a457fa.pdf",
        "decision_date": "2020-04-30",
    }
    changed = snapshot.get("competition_context") != context
    snapshot["competition_context"] = context
    for match in matches:
        if match["hg"] is None and match["ag"] is None and match.get("status") != "cancelled":
            match["status"] = "cancelled"
            changed = True
    return changed


def quality(snapshot):
    today = datetime.now(timezone.utc).date().isoformat()
    past_missing = [
        m
        for m in snapshot["matches"]
        if m.get("date")
        and m["date"] < today
        and m["hg"] is None
        and m.get("status") not in {"abandoned", "postponed", "cancelled"}
    ]
    return {
        "schema_version": 2,
        "checked_at": snapshot["fetched_at"],
        "results_digest": results_digest(snapshot["matches"]),
        "standings": {
            "status": "computed",
            "note": "Results-derived table; administrative deductions and official tie-breaks are not independently verified.",
        },
        "results": {
            "status": "structural_checks_passed",
            "matched": None,
            "local_results": sum(m["hg"] is not None for m in snapshot["matches"]),
            "conflicts": [],
            "unmatched": [],
            "reviewed": [],
            "past_missing": len(past_missing),
            "source_url": snapshot["source_url"],
            "note": "One community source. Schema, identity, duplicate, score and date checks; no independent provider verification.",
        },
    }


def fetch_one(league, season):
    url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{league['file']}.json"
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    raw = response.json()
    # Quarantine invalid rows; never silently change a source date or score.
    valid, rejected = [], []
    for m in raw.get("matches", []):
        try:
            # Published season opening date, not inferred from a replacement score feed.
            if (
                league["id"] == "PL"
                and season == "2019-20"
                and m.get("date")
                and m["date"] < "2019-08-09"
            ):
                raise ValueError(
                    "Before league opening date 2019-08-09; https://www.premierleague.com/en/news/1240976"
                )
            parse_openfootball({"matches": [m]}, season)
            valid.append(m)
        except (ValueError, TypeError, KeyError) as exc:
            rejected.append(
                {
                    "date": m.get("date"),
                    "home": m.get("team1"),
                    "away": m.get("team2"),
                    "reason": str(exc),
                }
            )
    matches = parse_openfootball({"matches": valid}, season)
    names = {m[t] for m in matches for t in ("home", "away")}
    expected = 20 if league["id"] == "FL1" and int(season[:4]) < 2023 else league["teams"]
    if len(names) != expected:
        raise ValueError(f"Expected {expected} teams; got {len(names)}")
    result = {
        **provenance("openfootball"),
        "league": league["id"],
        "season": season,
        "source_url": url,
        "source_sha256": hashlib.sha256(response.content).hexdigest(),
        "fetched_at": utc_now(),
        "matches": matches,
        "quarantined": rejected,
        "expected_fixtures": expected * (expected - 1),
        "raw_fixtures": len(raw["matches"]),
    }
    apply_competition_context(result)
    validate_public(result)
    report = quality(result)
    write_json(RESULTS / f"dashboard_{league['id']}_{season}.json", result)
    write_json(RESULTS / f"quality_{league['id']}_{season}.json", report)
    return {
        "league": league["id"],
        "season": season,
        "results": sum(m["hg"] is not None for m in matches),
        "quarantined": len(rejected),
        "past_missing": report["results"]["past_missing"],
        "last_result": max((m["date"] for m in matches if m["hg"] is not None), default=None),
    }


def sync(archive=False):
    # Restored snapshots may predate this documented status annotation. Migrate
    # that archive once without pretending it was fetched again today.
    path = RESULTS / "dashboard_FL1_2019-20.json"
    archived = read_json(path)
    if archived and apply_competition_context(archived):
        validate_public(archived)
        write_json(path, archived)
        write_json(RESULTS / "quality_FL1_2019-20.json", quality(archived))
    seasons = (
        [f"{y}-{str(y+1)[-2:]}" for y in range(2010, int(current_season()[:4]) + 1)]
        if archive
        else [current_season()]
    )
    jobs = [(league, s) for league in LEAGUES for s in seasons]
    status = read_json(RESULTS / "dashboard_sync.json", {"leagues": {}})
    failures = []

    def one(job):
        league, season = job
        try:
            return league, season, fetch_one(league, season), None
        except Exception as exc:
            return league, season, None, str(exc)

    with ThreadPoolExecutor(max_workers=5) as pool:
        for league, season, result, error in pool.map(one, jobs):
            key = f"{league['id']}_{season}"
            status["leagues"][key] = {"checked_at": utc_now(), "ok": error is None, "error": error}
            if error and season == current_season():
                failures.append(key)
            print(result or f"{key}: unavailable ({error})", flush=True)
            if (
                result
                and season == current_season()
                and (result["past_missing"] or result["quarantined"])
            ):
                print(
                    f"::warning::{key}: fetch succeeded, but {result['past_missing']} past fixtures have no result and {result['quarantined']} rows are quarantined. Latest recorded result: {result['last_result'] or 'none'}. A successful fetch is not complete coverage.",
                    flush=True,
                )
    write_json(RESULTS / "dashboard_sync.json", status)
    write_json(
        OPEN / "source_registry.json",
        {
            "checked_at": utc_now(),
            "policy": "Only allowlisted sources with explicit reusable licenses are packaged.",
            "sources": __import__("open_policy").SOURCES,
        },
    )
    return failures


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--archive", action="store_true")
    raise SystemExit(1 if sync(p.parse_args().archive) else 0)
