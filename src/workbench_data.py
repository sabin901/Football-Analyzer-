"""Free current-season squads and match box scores, with explicit coverage.

No credentials; ESPN's public, undocumented API has no availability guarantee.
Keep provider IDs and missing values. Never infer minutes or shot xG.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from dashboard_data import (
    ROOT,
    LIVE,
    LEAGUES,
    ESPN_CODES,
    current_season,
    fetch_json,
    read_json,
    write_json,
    utc_now,
)

CACHE = ROOT / "data" / "api_cache"
OUT = ROOT / "data" / "workbench"


def cached_fetch(url, ttl_hours=24):
    path = CACHE / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    old = read_json(path, {})
    if old and time.time() - path.stat().st_mtime < ttl_hours * 3600:
        return old["data"]
    for attempt in range(3):
        try:
            result = fetch_json(url)
            write_json(path, {"url": url, "fetched_at": utc_now(), "data": result})
            return result
        except Exception as exc:
            if isinstance(exc, HTTPError) and exc.code in (400, 404):
                raise
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def acquisition_time(url):
    """Timestamp of the actual HTTP response, not a cache read or rebuild."""
    return read_json(CACHE / (hashlib.sha256(url.encode()).hexdigest() + ".json"), {}).get(
        "fetched_at"
    )


def number(value):
    try:
        n = float(str(value).replace("%", ""))
        return n if n >= 0 and n < float("inf") else None
    except (TypeError, ValueError):
        return None


def stat_map(items):
    return {
        x["name"]: number(x.get("value", x.get("displayValue"))) for x in items if x.get("name")
    }


def parse_summary(raw, event_id, season):
    header = raw.get("header", {})
    if str(header.get("id")) != str(event_id) or header.get("season", {}).get("year") != int(
        season[:4]
    ):
        raise ValueError("Summary identity or season mismatch")
    comp = header["competitions"][0]
    if not str(event_id).isdigit():
        raise ValueError("Invalid provider match ID")
    played = datetime.fromisoformat(comp["date"].replace("Z", "+00:00"))
    if played > datetime.now(timezone.utc):
        raise ValueError("Completed match has a future timestamp")
    if not comp.get("status", {}).get("type", {}).get("completed"):
        raise ValueError("Match is not completed")
    teams = []
    for c in comp["competitors"]:
        team = c["team"]
        stats = next(
            (
                t.get("statistics", [])
                for t in raw.get("boxscore", {}).get("teams", [])
                if str(t["team"]["id"]) == str(team["id"])
            ),
            [],
        )
        teams.append(
            {
                "id": str(team["id"]),
                "name": team["displayName"],
                "venue": c["homeAway"],
                "goals": number(c.get("score")),
                "stats": stat_map(stats),
            }
        )
    if (
        len(teams) != 2
        or {t["venue"] for t in teams} != {"home", "away"}
        or any(t["goals"] is None for t in teams)
    ):
        raise ValueError("Invalid match participants or scores")
    if any(not t["goals"].is_integer() for t in teams):
        raise ValueError("Non-integer final score")
    players = []
    for roster in raw.get("rosters", []):
        for r in roster.get("roster", []):
            a = r.get("athlete", {})
            if not a.get("id"):
                continue
            players.append(
                {
                    "id": str(a["id"]),
                    "name": a.get("displayName"),
                    "team_id": str(roster["team"]["id"]),
                    "position": playing_position(a.get("position", {}).get("displayName"))
                    or playing_position(r.get("position", {}).get("displayName")),
                    "starter": bool(r.get("starter")),
                    "stats": stat_map(r.get("stats", [])),
                }
            )
    moments = []
    for e in comp.get("details", []):
        if e.get("scoringPlay") or e.get("redCard"):
            moments.append(
                {
                    "clock": e.get("clock", {}).get("displayValue"),
                    "goal": bool(e.get("scoringPlay")),
                    "red_card": bool(e.get("redCard")),
                    "own_goal": bool(e.get("ownGoal")),
                    "team_id": str(e.get("team", {}).get("id", "")),
                    "players": [
                        p.get("athlete", {}).get("displayName") for p in e.get("participants", [])
                    ],
                }
            )
    return {
        "id": str(event_id),
        "date": comp["date"],
        "teams": teams,
        "players": players,
        "moments": moments,
        "source_url": f"https://www.espn.com/soccer/match/_/gameId/{event_id}",
        "fetched_at": utc_now(),
    }


def playing_position(value):
    """Roster participation labels must never become playing positions."""
    if not isinstance(value, str) or value.strip().lower() in {
        "substitute",
        "sub",
        "bench",
        "reserve",
        "unknown",
        "",
    }:
        return None
    return value.strip()


def aggregate_players(matches, squads):
    players = {}
    for squad in squads:
        for p in squad["players"]:
            key = (p["id"], squad["id"])
            players[key] = {
                **p,
                "team_id": squad["id"],
                "team": squad["name"],
                "matches": 0,
                "starts": 0,
                "stats": {},
                "stat_samples": {},
            }
    for m in matches:
        team_names = {t["id"]: t["name"] for t in m["teams"]}
        for p in m["players"]:
            key = (p["id"], p["team_id"])
            row = players.setdefault(
                key,
                {
                    **p,
                    "team": team_names.get(p["team_id"], ""),
                    "matches": 0,
                    "starts": 0,
                    "stats": {},
                    "stat_samples": {},
                },
            )
            row["position"] = playing_position(row.get("position")) or playing_position(
                p.get("position")
            )
            appearance = p["stats"].get("appearances")
            if appearance is None or appearance <= 0:
                continue
            row["matches"] += 1
            row["starts"] += p["starter"]
            for stat, value in p["stats"].items():
                if value is not None:
                    row["stats"][stat] = row["stats"].get(stat, 0) + value
                    row["stat_samples"][stat] = row["stat_samples"].get(stat, 0) + 1
    return sorted(
        players.values(), key=lambda p: (-p["stats"].get("totalGoals", 0), p["name"] or "")
    )


def sync_league(league):
    season = current_season()
    code = ESPN_CODES[league["id"]]
    base = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}"
    path = OUT / f"current_{league['id']}.json"
    previous = read_json(path, {})
    errors = []
    raw = cached_fetch(base + "/teams?limit=100", 24)
    team_list = raw["sports"][0]["leagues"][0]["teams"]
    squads = []
    for item in team_list:
        t = item["team"]
        try:
            roster = cached_fetch(base + f"/teams/{t['id']}/roster?season={season[:4]}", 24)
            if roster.get("season", {}).get("year") != int(season[:4]):
                raise ValueError("Roster season mismatch")
            squads.append(
                {
                    "id": str(t["id"]),
                    "name": t["displayName"],
                    "fetched_at": acquisition_time(
                        base + f"/teams/{t['id']}/roster?season={season[:4]}"
                    ),
                    "logo": next((l["href"] for l in t.get("logos", []) if l.get("href")), None),
                    "players": [
                        {
                            "id": str(a["id"]),
                            "name": a["displayName"],
                            "position": a.get("position", {}).get("displayName"),
                            "age": a.get("age"),
                            "jersey": a.get("jersey"),
                            "photo": a.get("headshot", {}).get("href"),
                        }
                        for a in roster.get("athletes", [])
                    ],
                }
            )
        except Exception as exc:
            errors.append(f"Roster {t['id']}: {exc}")
            if previous.get("season") == season:
                old_squad = next(
                    (s for s in previous.get("teams", []) if s["id"] == str(t["id"])), None
                )
                if old_squad:
                    squads.append(old_squad)
    snapshot = read_json(LIVE / f"dashboard_{league['id']}_{season}.json", {})
    dates = {
        m["date"]
        for m in snapshot.get("matches", [])
        if m.get("date") and m["date"] <= datetime.now(timezone.utc).date().isoformat()
    }
    # Last two weeks cover moved dates missing from the original schedule.
    dates.update(
        (datetime.now(timezone.utc).date() - timedelta(days=i)).isoformat() for i in range(14)
    )
    events = {}

    def board(date):
        try:
            result = cached_fetch(
                base + "/scoreboard?dates=" + date.replace("-", ""),
                (
                    6
                    if date >= (datetime.now(timezone.utc).date() - timedelta(days=3)).isoformat()
                    else 24 * 30
                ),
            )
            return result.get("events", []), None
        except Exception as exc:
            return [], f"Scoreboard {date}: {exc}"

    with ThreadPoolExecutor(max_workers=3) as pool:
        for rows, error in pool.map(board, sorted(dates)):
            if error:
                errors.append(error)
            for e in rows:
                if e.get("status", {}).get("type", {}).get("completed"):
                    events[str(e["id"])] = e
    old_matches = (
        {m["id"]: m for m in previous.get("matches", [])}
        if previous.get("season") == season
        else {}
    )
    matches = []

    def summary(eid):
        try:
            # Recheck recent finals for provider corrections; older finals cached for 30 days.
            ttl = (
                6
                if events[eid]["date"][:10]
                >= (datetime.now(timezone.utc).date() - timedelta(days=3)).isoformat()
                else 24 * 30
            )
            url = base + "/summary?event=" + eid
            result = parse_summary(cached_fetch(url, ttl), eid, season)
            result["fetched_at"] = acquisition_time(url)
            return result, None
        except Exception as exc:
            return old_matches.get(eid), f"Summary {eid}: {exc}"

    with ThreadPoolExecutor(max_workers=3) as pool:
        for row, error in pool.map(summary, sorted(events)):
            if row:
                matches.append(row)
            if error:
                errors.append(error)
    # A scoreboard outage must not silently delete previously recorded matches.
    present = {m["id"] for m in matches}
    matches.extend(m for eid, m in old_matches.items() if eid not in present)
    matches.sort(key=lambda m: m["date"])
    players = aggregate_players(matches, squads)
    payload = {
        "schema_version": 1,
        "league": league["id"],
        "season": season,
        "source": "ESPN public API",
        "source_url": base,
        "fetched_at": utc_now(),
        "refresh_ok": not errors,
        "errors": errors,
        "teams": squads,
        "players": players,
        "matches": matches,
        "coverage": {
            "expected_teams": league["teams"],
            "squads": len(squads),
            "discovered_finals": len(events),
            "match_summaries": len(matches),
            "schedule_results": sum(m["hg"] is not None for m in snapshot.get("matches", [])),
            "players": len(players),
            "minutes_available": False,
            "shot_xg_available": False,
        },
        "limitations": [
            "Undocumented public feed; no SLA or open-data redistribution license.",
            "Totals cover imported appearances only. Missing statistics remain missing.",
            "Minutes unavailable: no current-player per-90 or peer percentiles are computed.",
        ],
    }
    if not matches or not squads:
        raise ValueError("No usable match or squad data; retaining prior published file")
    write_json(path, payload)
    print(
        f"{league['id']}: {len(squads)} squads, {len(players)} players, {len(matches)} summaries, {len(errors)} errors",
        flush=True,
    )
    return bool(errors)


if __name__ == "__main__":
    import os

    if os.environ.get("FOOTLYZER_LICENSED_RESEARCH") != "1":
        raise SystemExit(
            "Legacy restricted feed disabled. Public workflows use src/open_results.py and src/open_events.py. Local research requires your own provider authorization."
        )
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", choices=[l["id"] for l in LEAGUES])
    args = parser.parse_args()
    failed = []
    for league in LEAGUES:
        if args.league and league["id"] != args.league:
            continue
        try:
            if sync_league(league):
                failed.append(league["id"])
        except Exception as exc:
            failed.append(league["id"])
            print(f"{league['id']}: {exc}", flush=True)
            path = OUT / f"current_{league['id']}.json"
            previous = read_json(path, {})
            if previous:
                previous.update(refresh_ok=False, errors=[str(exc)], last_attempt_at=utc_now())
                write_json(path, previous)
    raise SystemExit(bool(failed))
