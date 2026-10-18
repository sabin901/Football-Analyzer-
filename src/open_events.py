"""Reproduce the CC BY 4.0 Pappalardo/Wyscout 2017/18 five-league archive.

No inferred recipients, pressure, possession, current squads or provider xG.
Coordinates are rescaled from the documented attacking-team 0..100 frame to
120x80 display units. Regulation minutes exclude stoppage time.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile
import requests
from dashboard_data import ROOT, LEAGUES, write_json, utc_now
from open_policy import OPEN, WORKBENCH, provenance, validate_public
from spatial_workbench import aggregate_spatial

FILES = {
    "events.zip": (7770599, 14464685, "7c20e8647e7eda58d7838a0c7b1ec6ab"),
    "matches.zip": (7770422, 14464622, "51d80beb17480919f69a53a0152c2d71"),
    "players.json": (7765196, 15073721, "f28ddf6326281efeda6488b2169f5609"),
    "teams.json": (7765310, 15073697, "1381ff9449f21105090729cf0e086b5b"),
}
COUNTRIES = {"PL": "England", "PD": "Spain", "SA": "Italy", "BL1": "Germany", "FL1": "France"}
METRICS = [
    "shots",
    "np_goals",
    "key_passes",
    "passes",
    "completed_passes",
    "progressive_passes",
    "progressive_carries",
    "interceptions",
    "defensive_duels",
]
ACTIONS = [
    "Pass",
    "Acceleration",
    "Shot",
    "Defensive duel",
    "Interception / clearance",
    "Touch",
    "Other action",
]
PERIODS = {"1H": 1, "2H": 2, "E1": 3, "E2": 4}


def clean_name(text):
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), text or "Unknown player")


def source_files(cache):
    registry = []
    for name, (article, fid, expected) in FILES.items():
        meta = requests.get(f"https://api.figshare.com/v2/articles/{article}", timeout=30)
        meta.raise_for_status()
        metadata = meta.json()
        if metadata.get("license", {}).get("name") != "CC BY 4.0":
            raise ValueError(f"License changed for {name}; manual review required")
        file = next(f for f in metadata["files"] if f["id"] == fid)
        path = cache / name
        if not path.exists():
            with requests.get(file["download_url"], timeout=120, stream=True) as response:
                response.raise_for_status()
                with path.open("wb") as out:
                    for chunk in response.iter_content(1024 * 1024):
                        out.write(chunk)
        if hashlib.md5(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Checksum changed for {name}; manual review required")
        registry.append(
            {
                "file": name,
                "article": article,
                "doi": metadata["doi"],
                "license": metadata["license"],
                "source_url": file["download_url"],
                "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    write_json(
        OPEN / "wyscout_sources.json",
        {"checked_at": utc_now(), "files": registry, **provenance("wyscout_research")},
    )
    return registry


def point(event):
    positions = event.get("positions", [])
    if not positions:
        return None
    p = positions[0]
    if not all(
        type(p.get(k)) in (int, float) and math.isfinite(p[k]) and 0 <= p[k] <= 100
        for k in ("x", "y")
    ):
        return None
    return p["x"] * 1.2, p["y"] * 0.8


def progress(event):
    ps = event.get("positions", [])
    if len(ps) < 2:
        return False
    a, b = ps[:2]
    return (
        b["x"] >= 60
        and math.hypot(120 - a["x"] * 1.2, 40 - a["y"] * 0.8)
        - math.hypot(120 - b["x"] * 1.2, 40 - b["y"] * 0.8)
        >= 10
    )


def summarize(events, match, people, teams, source):
    if match["status"] != "Played" or len(match["teamsData"]) != 2:
        raise ValueError("Not a completed two-team match")
    if len({e["id"] for e in events}) != len(events):
        raise ValueError("Duplicate event ID")
    sides = {v["side"]: v for v in match["teamsData"].values()}
    home, away = sides["home"], sides["away"]
    rows, starts, entered, ends = {}, set(), {}, {}

    def player(pid, tid):
        if pid not in rows:
            p = people.get(pid, {})
            role = {"GK": "GK", "DF": "DEF", "MD": "MID", "FW": "FWD"}.get(
                p.get("role", {}).get("code2"), "UNKNOWN"
            )
            rows[pid] = {
                "id": pid,
                "name": clean_name(p.get("shortName")),
                "team_id": tid,
                "team": teams[tid]["name"],
                "position": role,
                "minutes": 0,
                **{m: 0 for m in METRICS},
                "npxg": None,
                "pressures": None,
                "recoveries": None,
                "tackles": None,
            }
        if rows[pid]["team_id"] != tid:
            raise ValueError("Player appears for both teams")
        return rows[pid]

    for t in sides.values():
        tid = t["teamId"]
        for p in t.get("formation", {}).get("lineup", []):
            player(p["playerId"], tid)
            starts.add(p["playerId"])
            entered[p["playerId"]] = 0
        substitutions = t.get("formation", {}).get("substitutions") or []
        for sub in substitutions if isinstance(substitutions, list) else []:
            minute = min(90, max(0, sub["minute"]))
            player(sub["playerIn"], tid)
            entered[sub["playerIn"]] = minute
            ends[sub["playerOut"]] = minute
    shots, cells, located, missing = [], Counter(), 0, 0
    periods = Counter()
    for e in sorted(
        events, key=lambda e: (PERIODS.get(e["matchPeriod"], 9), e["eventSec"], e["id"])
    ):
        if e["matchId"] != match["wyId"]:
            raise ValueError("Wrong event match")
        period = PERIODS.get(e["matchPeriod"])
        pid, tid = e["playerId"], e["teamId"]
        if not period or not pid or str(tid) not in match["teamsData"]:
            continue
        r = player(pid, tid)
        tags = {t["id"] for t in e["tags"]}
        minute = e["eventSec"] / 60 + {1: 0, 2: 45, 3: 90, 4: 105}[period]
        if 1701 in tags or 1703 in tags:
            ends[pid] = min(ends.get(pid, 90), max(0, min(90, minute)))
        kind, sub = e["eventName"], e.get("subEventName", "")
        is_shot = kind == "Shot" or sub in ("Free kick shot", "Penalty")
        bucket = 6
        if kind == "Pass":
            bucket = 0
            r["passes"] += 1
            r["completed_passes"] += int(1801 in tags)
            r["key_passes"] += int(301 in tags or 302 in tags)
            r["progressive_passes"] += int(1801 in tags and progress(e))
        elif sub == "Acceleration":
            bucket = 1
            r["progressive_carries"] += int(progress(e))
        elif sub == "Ground defending duel":
            bucket = 3
            r["defensive_duels"] += 1
        elif sub == "Clearance" or 1401 in tags:
            bucket = 4
        elif sub == "Touch":
            bucket = 5
        r["interceptions"] += int(1401 in tags)
        p = point(e)
        if is_shot:
            bucket = 2
            penalty = sub == "Penalty"
            goal = 101 in tags and 102 not in tags
            r["shots"] += int(not penalty)
            r["np_goals"] += int(goal and not penalty)
            if p:
                shots.append(
                    {
                        "id": str(e["id"]),
                        "player_id": pid,
                        "player": r["name"],
                        "team_id": tid,
                        "minute": round(minute, 2),
                        "period": period,
                        "second": e["eventSec"],
                        "x": round(p[0], 3),
                        "y": round(p[1], 3),
                        "xg": None,
                        "goal": goal,
                        "penalty": penalty,
                        "outcome": "Goal" if goal else "Other shot",
                        "play_pattern": sub,
                        "body_part": (
                            "Head / body"
                            if 403 in tags
                            else (
                                "Left foot"
                                if 401 in tags
                                else "Right foot" if 402 in tags else "Unknown"
                            )
                        ),
                    }
                )
        if p:
            cell = min(7, int(p[1] / 10)) * 12 + min(11, int(p[0] / 10))
            cells[(pid, period, bucket, cell)] += 1
            located += 1
        else:
            missing += 1
        periods[period] += 1
    for pid, r in rows.items():
        r["minutes"] = round(max(0, ends.get(pid, 90) - entered[pid]), 2) if pid in entered else 0
    players = list(rows.values())
    indices = {p["id"]: i for i, p in enumerate(players)}
    common = {**provenance("wyscout_research"), **source, "fetched_at": utc_now()}
    summary = {
        **common,
        "id": match["wyId"],
        "date": match["dateutc"][:10],
        "home": teams[home["teamId"]]["name"],
        "away": teams[away["teamId"]]["name"],
        "home_id": home["teamId"],
        "away_id": away["teamId"],
        "hg": home["score"],
        "ag": away["score"],
        "events": len(events),
        "players": players,
        "shots": shots,
        "pass_links": [],
        "xg_available": False,
        "event_sha256": hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest(),
    }
    spatial = {
        **common,
        "schema_version": 1,
        "source_hash": summary["event_sha256"],
        "match_id": match["wyId"],
        "date": summary["date"],
        "players": [{k: p[k] for k in ("id", "name", "team_id", "team")} for p in players],
        "cols": 12,
        "rows": 8,
        "actions": ACTIONS,
        "located": located,
        "missing_location": missing,
        "invalid_location": 0,
        "edge_clamped": 0,
        "orientation": "action executing team attacks right",
        "cells": [
            [indices[pid], period, kind, cell, n]
            for (pid, period, kind, cell), n in sorted(cells.items())
        ],
    }
    report = {
        **common,
        "id": str(match["wyId"]),
        "date": match["dateutc"].replace(" ", "T") + "Z",
        "teams": [
            {
                "id": str(t["teamId"]),
                "name": teams[t["teamId"]]["name"],
                "venue": t["side"],
                "goals": t["score"],
                "stats": {"totalShots": sum(s["team_id"] == t["teamId"] for s in shots)},
            }
            for t in sides.values()
        ],
        "players": [
            {
                "id": str(p["id"]),
                "name": p["name"],
                "team_id": str(p["team_id"]),
                "position": p["position"],
                "starter": p["id"] in starts,
                "stats": {
                    "appearances": int(p["id"] in entered),
                    "totalGoals": sum(s["player_id"] == p["id"] and s["goal"] for s in shots),
                    "totalShots": sum(s["player_id"] == p["id"] for s in shots),
                },
            }
            for p in players
        ],
        "moments": [],
    }
    return summary, spatial, report


def aggregate(matches):
    rows = {}
    for m in matches:
        for p in m["players"]:
            k = (p["id"], p["team_id"])
            if k not in rows:
                rows[k] = {**p, **{metric: 0 for metric in METRICS}, "minutes": 0, "matches": 0}
            r = rows[k]
            r["minutes"] += p["minutes"]
            r["matches"] += int(p["minutes"] > 0)
            for metric in METRICS:
                r[metric] += p[metric]
    for p in rows.values():
        p["minutes"] = round(p["minutes"], 2)
        p["per90"] = {
            m: round(p[m] * 90 / p["minutes"], 3) if p["minutes"] else None for m in METRICS
        }
        p["per90"].update(npxg=None, pressures=None, recoveries=None, tackles=None)
    return sorted(rows.values(), key=lambda p: -p["minutes"])


def run(cache):
    from workbench_data import aggregate_players

    cache.mkdir(parents=True, exist_ok=True)
    registry = source_files(cache)
    source = {k: registry[0][k] for k in ("source_url", "source_sha256")}
    people = {p["wyId"]: p for p in json.loads((cache / "players.json").read_text())}
    teams = {
        p["wyId"]: {**p, "name": clean_name(p["name"])}
        for p in json.loads((cache / "teams.json").read_text())
    }
    events_zip, matches_zip = zipfile.ZipFile(cache / "events.zip"), zipfile.ZipFile(
        cache / "matches.zip"
    )
    sets = []
    for league in LEAGUES:
        country = COUNTRIES[league["id"]]
        key = f"{league['id']}_2017_18"
        catalogue = json.loads(matches_zip.read(f"matches_{country}.json"))
        grouped = defaultdict(list)
        for event in json.loads(events_zip.read(f"events_{country}.json")):
            grouped[event["matchId"]].append(event)
        summaries, spatial, reports = [], [], []
        for match in sorted(catalogue, key=lambda m: m["dateutc"]):
            if not grouped[match["wyId"]]:
                raise ValueError("Missing match events")
            m, s, r = summarize(grouped.pop(match["wyId"]), match, people, teams, source)
            validate_public(m)
            write_json(WORKBENCH / "event_matches" / f"{m['id']}.json", m)
            write_json(WORKBENCH / "spatial_matches" / f"{m['id']}.json", s)
            summaries.append(m)
            spatial.append(s)
            reports.append(r)
        players = aggregate(summaries)
        info = {
            "key": key,
            "league": league["id"],
            "season": "2017/2018",
            "competition": league["name"],
            "available_matches": len(catalogue),
            "imported_matches": len(summaries),
            "players": len(players),
            "events": sum(m["events"] for m in summaries),
            "errors": [],
            "first_date": summaries[0]["date"],
            "last_date": summaries[-1]["date"],
        }
        common = {**provenance("wyscout_research"), **source, "fetched_at": utc_now(), **info}
        write_json(
            WORKBENCH / f"events_{key}.json",
            {
                **common,
                "xg_available": False,
                "coverage_note": "2017/18 historical league archive. Not a current squad, form or recruitment assessment.",
                "minutes_note": "Regulation minutes estimated from lineups, substitutions and dismissal events. Stoppage time excluded; unknown participation is not guessed.",
                "player_rows": players,
                "matches": [
                    {k: v for k, v in m.items() if k not in ("players", "shots", "pass_links")}
                    for m in summaries
                ],
            },
        )
        grid = aggregate_spatial(spatial)
        grid["actions"] = ACTIONS
        write_json(
            WORKBENCH / f"spatial_{key}.json",
            {**common, **grid, "match_ids": [m["id"] for m in summaries]},
        )
        ids = sorted({p["team_id"] for p in players})
        current_players = aggregate_players(reports, [])
        write_json(
            WORKBENCH / f"current_{league['id']}.json",
            {
                **common,
                "schema_version": 2,
                "historical": True,
                "refresh_ok": True,
                "teams": [{"id": str(tid), "name": teams[tid]["name"]} for tid in ids],
                "players": current_players,
                "matches": reports,
                "coverage": {
                    "squads": len(ids),
                    "expected_teams": len(ids),
                    "match_summaries": len(reports),
                    "schedule_results": len(catalogue),
                    "minutes_available": False,
                    "shot_xg_available": False,
                },
                "limitations": [
                    "Historical 2017/18; no current squads",
                    "No provider xG, possession, pass recipients or continuous tracking",
                ],
            },
        )
        sets.append(info)
        print(key, len(summaries), "matches", info["events"], "events", flush=True)
    for name in ["events_manifest", "spatial_manifest"]:
        write_json(
            WORKBENCH / f"{name}.json",
            {**provenance("wyscout_research"), **source, "sets": sets, "fetched_at": utc_now()},
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=ROOT / ".artifacts/open-data")
    run(parser.parse_args().cache)
