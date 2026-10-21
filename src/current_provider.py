"""Optional application-only current data. Never add API responses to the CC0 archive.

Activated with FOOTBALL_DATA_API_KEY in GitHub Actions. The free plan is delayed.
Only normalized display fields are retained; credentials and provider graphics are not.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import json
import os
import time
import requests
from dashboard_data import (
    LEAGUES,
    current_season,
    parse_openfootball,
    standings,
    utc_now,
    write_json,
    read_json,
)
from club_identity import club_key, resolver
from data_quality import results_digest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".artifacts/current-provider"
API = "https://api.football-data.org/v4"
TERMS = "https://www.football-data.org/client/register"
ATTRIBUTION = "Football data provided by the Football-Data.org API"


def normalize(fixtures, table, league, season, fetched_at, aliases=()):
    """Reject cross-season payloads, partial scores, identity collisions and table drift."""
    year = int(season[:4])
    for raw in (fixtures, table):
        if raw.get("competition", {}).get("code") != league["id"]:
            raise ValueError("Provider competition mismatch")
    if table.get("season", {}).get("startDate", "")[:4] != str(year):
        raise ValueError("Provider standings season mismatch")
    groups = [g for g in table.get("standings", []) if g.get("type") == "TOTAL"]
    if len(groups) != 1:
        raise ValueError("Expected one overall provider table")
    entries = groups[0]["table"]
    if len(entries) != league["teams"]:
        raise ValueError("Incomplete provider table")
    resolve = resolver(aliases)
    identities = {}
    names = set()
    for row in entries:
        team = row["team"]
        name = resolve(team["name"]) or team["name"]
        if (
            not isinstance(name, str)
            or not name.strip()
            or team["id"] in identities
            or club_key(name) in names
        ):
            raise ValueError("Ambiguous provider team identity")
        names.add(club_key(name))
        identities[team["id"]] = name
    rows = []
    for match in fixtures.get("matches", []):
        if match.get("season", {}).get("startDate", "")[:4] != str(year):
            raise ValueError("Provider fixture season mismatch")
        if match.get("competition", {}).get("code") != league["id"]:
            raise ValueError("Provider fixture competition mismatch")
        home, away = (identities.get(match[t]["id"]) for t in ("homeTeam", "awayTeam"))
        if not home or not away or home == away:
            raise ValueError("Unknown fixture team")
        if type(match.get("id")) is not int or match["id"] <= 0:
            raise ValueError("Invalid fixture ID")
        kickoff = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
        if kickoff.tzinfo is None:
            raise ValueError("Missing kickoff timezone")
        status = match["status"]
        if status not in {
            "SCHEDULED",
            "TIMED",
            "IN_PLAY",
            "PAUSED",
            "FINISHED",
            "POSTPONED",
            "SUSPENDED",
            "CANCELLED",
            "AWARDED",
        }:
            raise ValueError("Unknown match status")
        full = match.get("score", {}).get("fullTime", {})
        score = [full.get("home"), full.get("away")] if status == "FINISHED" else None
        if status == "FINISHED" and (
            any(type(v) is not int or v < 0 for v in score)
            or kickoff > datetime.fromisoformat(fetched_at)
        ):
            raise ValueError("Invalid completed provider score")
        parsed = parse_openfootball(
            {
                "matches": [
                    {
                        "team1": home,
                        "team2": away,
                        "date": kickoff.date().isoformat(),
                        "round": str(match.get("matchday") or ""),
                        "score": {"ft": score},
                    }
                ]
            },
            season,
        )[0]
        rows.append(
            {
                **parsed,
                "kickoff": kickoff.isoformat(),
                "provider_id": match["id"],
                "status": {
                    "FINISHED": "finished",
                    "TIMED": "scheduled",
                    "SCHEDULED": "scheduled",
                    "IN_PLAY": "in_play",
                    "PAUSED": "in_play",
                    "SUSPENDED": "postponed",
                    "POSTPONED": "postponed",
                    "CANCELLED": "cancelled",
                    "AWARDED": "awarded_pending",
                }[status],
                "result_source": "Football-Data.org",
            }
        )
    if len({r["provider_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate provider fixture ID")
    if len({(r["home"], r["away"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate provider fixture")
    if {r[t] for r in rows for t in ("home", "away")} != set(identities.values()):
        raise ValueError("Provider schedule missing teams")
    rows.sort(key=lambda r: (r["date"], r["kickoff"], r["home"]))
    calculated = {r["team"]: r for r in standings(rows)}
    official, issues = [], []
    fields = {
        "p": "playedGames",
        "w": "won",
        "d": "draw",
        "l": "lost",
        "gf": "goalsFor",
        "ga": "goalsAgainst",
        "pts": "points",
        "rank": "position",
    }
    for entry in entries:
        name = identities[entry["team"]["id"]]
        row = {"team": name}
        for target, source in fields.items():
            value = entry[source]
            if type(value) is not int or (target != "pts" and value < 0):
                raise ValueError("Invalid provider standings arithmetic")
            row[target] = value
        if row["p"] != row["w"] + row["d"] + row["l"]:
            raise ValueError("Provider played total mismatch")
        row["adjustment"] = row["pts"] - (3 * row["w"] + row["d"])
        issues.extend(
            {"team": name, "field": k}
            for k in ("p", "w", "d", "l", "gf", "ga")
            if row[k] != calculated[name][k]
        )
        official.append(row)
    if {r["rank"] for r in official} != set(range(1, len(entries) + 1)):
        raise ValueError("Invalid provider ranks")
    missing = sum(
        r["hg"] is None
        and r["date"] < fetched_at[:10]
        and r["status"] not in {"cancelled", "postponed"}
        for r in rows
    )
    q = {
        "checked_at": fetched_at,
        "results_digest": results_digest(rows),
        "standings": {
            "status": "matched" if not issues else "mismatch",
            "rows": official,
            "issues": issues,
        },
        "results": {
            "status": "provider_reconciled" if not issues else "provider_mismatch",
            "past_missing": missing,
            "note": "Fixtures reconciled against the same provider’s table; not independent second-source verification.",
        },
    }
    return {
        "source_id": "football_data_org",
        "source": "Football-Data.org",
        "license": "provider-terms",
        "license_url": TERMS,
        "attribution": ATTRIBUTION,
        "source_url": f'{API}/competitions/{league["id"]}/matches?season={year}',
        "source_sha256": hashlib.sha256(
            json.dumps([fixtures, table], sort_keys=True).encode()
        ).hexdigest(),
        "league": league["id"],
        "season": season,
        "fetched_at": fetched_at,
        "matches": rows,
        "quality": q,
        "quarantined": [],
        "expected_fixtures": league["teams"] * (league["teams"] - 1),
        "delayed": True,
    }


def load_current(league, season, now=None):
    value = read_json(OUT / f"{league}.json")
    if not value or value.get("season") != season or value.get("league") != league:
        return None
    now = now or datetime.now(timezone.utc)
    try:
        age = (now - datetime.fromisoformat(value["fetched_at"])).total_seconds()
        if not 0 <= age <= 36 * 3600 or value["quality"]["results_digest"] != results_digest(
            value["matches"]
        ):
            return None
        if value["source_id"] != "football_data_org" or value["license"] != "provider-terms":
            return None
    except (KeyError, ValueError, TypeError):
        return None
    return value


def display_snapshot(raw):
    from dashboard_data import enrich

    return enrich(raw, {"ok": True})


def upcoming_overlay(base, raw, history):
    """Keep the CC0 historical evaluation separate from new provider-fed predictions."""
    from forecast_lab import forecast

    now = datetime.now(timezone.utc)
    cutoff = now.date().isoformat()
    q = raw["quality"]
    reasons = []
    if q["standings"]["status"] != "matched":
        reasons.append("Provider results and table do not reconcile")
    if q["results"]["past_missing"]:
        reasons.append("Past fixtures have missing results")
    if len(raw["matches"]) != raw["expected_fixtures"]:
        reasons.append("Provider schedule is incomplete")
    if not raw["matches"] or not any(r["hg"] is not None for r in raw["matches"]):
        reasons.append("No completed provider results")
    # Replace, never concatenate, the overlapping current-season community rows.
    training = [m for m in history if m["season"] != raw["season"]] + raw["matches"]
    upcoming = []
    if not reasons:
        for m in raw["matches"]:
            if (
                m["hg"] is None
                and m["status"] == "scheduled"
                and cutoff < m["date"] <= (now.date() + timedelta(days=14)).isoformat()
            ):
                p = forecast(training, m, cutoff)
                if p:
                    upcoming.append(p)
    return {
        **base,
        "upcoming": upcoming,
        "as_of": cutoff,
        "built_at": utc_now(),
        "current_provider": {
            "source": raw["source"],
            "attribution": ATTRIBUTION,
            "terms": TERMS,
            "fetched_at": raw["fetched_at"],
            "delayed": True,
        },
        "publication": {
            "allowed": not reasons,
            "reason": "; ".join(reasons)
            or "Delayed provider feed; table reconciled within the same source. Experimental model.",
            "valid_until": (
                datetime.fromisoformat(raw["fetched_at"]) + timedelta(hours=36)
            ).isoformat(),
        },
        "prospective": {"recorded": 0, "settled": 0, "metrics": None, "accuracy": None},
        "source_quality": {"checked_at": q["checked_at"], "result_status": q["results"]["status"]},
    }


def sync():
    key = os.environ.get("FOOTBALL_DATA_API_KEY", "").strip()
    if not key:
        print("Football-Data.org not configured; using the labelled community source.")
        return
    season = current_season()
    session = requests.Session()
    session.headers.update({"X-Auth-Token": key, "User-Agent": "Footlyzer/1.1"})
    failures = []
    last = 0.0

    def fetch(path):
        nonlocal last
        # Below the free tier's 10 requests/minute, including league boundaries.
        time.sleep(max(0, 6.2 - (time.monotonic() - last)))
        last = time.monotonic()
        response = session.get(API + path, timeout=30)
        if response.status_code != 200:
            # Never echo response headers, request configuration or credential values.
            raise ValueError(f"Provider HTTP {response.status_code}")
        return response.json()

    for league in LEAGUES:
        target = OUT / f'{league["id"]}.json'
        try:
            fixtures = fetch(f'/competitions/{league["id"]}/matches?season={season[:4]}')
            table = fetch(f'/competitions/{league["id"]}/standings?season={season[:4]}')
            archive = read_json(
                ROOT / f'data/open/results/dashboard_{league["id"]}_{season}.json', {}
            )
            aliases = sorted({m[t] for m in archive.get("matches", []) for t in ("home", "away")})
            result = normalize(fixtures, table, league, season, utc_now(), aliases)
            write_json(target, result)
            print(league["id"], "provider snapshot validated", flush=True)
        except Exception:
            target.unlink(missing_ok=True)
            failures.append(league["id"])
            print(
                league["id"],
                "provider unavailable or failed validation; community fallback retained",
                flush=True,
            )
    write_json(
        OUT / "status.json",
        {"configured": True, "checked_at": utc_now(), "failed_leagues": failures},
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    sync()
