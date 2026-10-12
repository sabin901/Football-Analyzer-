"""Compact, reproducible event activity grids. No inferred player tracking.

Coordinates stay in StatsBomb's action executing team frame (attacking right).
Each sparse row is [player_index, period, action_index, cell_index, count].
"""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from dashboard_data import read_json, write_json, fetch_json, utc_now
from workbench_data import OUT

VERSION = 1
COLS, ROWS = 12, 8
ACTIONS = ["Pass", "Carry", "Shot", "Pressure", "Defensive action", "Ball receipt", "Other action"]
DEFENSIVE = {"Ball Recovery", "Interception", "Duel", "Block", "Clearance", "Dribbled Past"}


def summarize_spatial(events, match):
    players = [{k: p[k] for k in ("id", "name", "team_id", "team")} for p in match["players"]]
    indices = {(p["id"], p["team_id"]): i for i, p in enumerate(players)}
    cells = Counter()
    missing = invalid = clipped = located = 0
    for event in events:
        period = event.get("period")
        if period not in (1, 2, 3, 4) or not event.get("player"):
            continue
        idx = indices.get((event["player"]["id"], event.get("team", {}).get("id")))
        if idx is None:
            raise ValueError("Spatial player identity absent from event summary")
        loc = event.get("location")
        if loc is None:
            missing += 1
            continue
        if (
            not isinstance(loc, list)
            or len(loc) < 2
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in loc[:2])
            or not (-1 <= loc[0] <= 121 and -1 <= loc[1] <= 81)
        ):
            invalid += 1
            continue
        x, y = loc[:2]
        clipped += int(not (0 <= x <= 120 and 0 <= y <= 80))
        column = max(0, min(COLS - 1, int(x / 10)))
        row = max(0, min(ROWS - 1, int(y / 10)))
        name = event.get("type", {}).get("name")
        kind = (
            ACTIONS.index(name)
            if name in ACTIONS[:4]
            else 4 if name in DEFENSIVE else 5 if name == "Ball Receipt*" else 6
        )
        cells[(idx, period, kind, row * COLS + column)] += 1
        located += 1
    return {
        "schema_version": VERSION,
        "match_id": match["id"],
        "date": match["date"],
        "source_url": match["source_url"],
        "source_hash": match["event_sha256"],
        "fetched_at": utc_now(),
        "players": players,
        "cols": COLS,
        "rows": ROWS,
        "actions": ACTIONS,
        "cells": [list(key) + [n] for key, n in sorted(cells.items())],
        "located": located,
        "missing_location": missing,
        "invalid_location": invalid,
        "edge_clamped": clipped,
        "orientation": "action executing team attacks right",
    }


def aggregate_spatial(matches):
    players, indices, cells = [], {}, Counter()
    for match in matches:
        remap = {}
        for i, p in enumerate(match["players"]):
            key = (p["id"], p["team_id"])
            if key not in indices:
                indices[key] = len(players)
                players.append({**p, "matches": 0})
            remap[i] = indices[key]
        participating = {row[0] for row in match["cells"]}
        for i in participating:
            players[remap[i]]["matches"] += 1
        for i, period, kind, cell, n in match["cells"]:
            cells[(remap[i], period, kind, cell)] += n
    return {
        "schema_version": VERSION,
        "players": players,
        "cols": COLS,
        "rows": ROWS,
        "actions": ACTIONS,
        "cells": [list(k) + [n] for k, n in sorted(cells.items())],
        **{
            key: sum(m[key] for m in matches)
            for key in ("located", "missing_location", "invalid_location", "edge_clamped")
        },
    }


def run():
    manifest = read_json(OUT / "events_manifest.json")
    report = []
    for dataset in manifest["sets"]:
        event_set = read_json(OUT / f"events_{dataset['key']}.json")

        def one(meta):
            match = read_json(OUT / "event_matches" / f"{meta['id']}.json")
            path = OUT / "spatial_matches" / f"{meta['id']}.json"
            old = read_json(path, {})
            if (
                old.get("schema_version") == VERSION
                and old.get("source_hash") == match["event_sha256"]
            ):
                return old, None
            try:
                events = fetch_json(match["source_url"])
                digest = hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest()
                if digest != match["event_sha256"]:
                    raise ValueError(
                        "Provider events changed; refresh event_workbench before spatial import"
                    )
                result = summarize_spatial(events, match)
                write_json(path, result)
                return result, None
            except Exception as exc:
                return None, {"match_id": meta["id"], "error": str(exc)}

        matches, errors = [], []
        with ThreadPoolExecutor(max_workers=3) as pool:
            for result, error in pool.map(one, event_set["matches"]):
                if result:
                    matches.append(result)
                if error:
                    errors.append(error)
        info = {
            "key": dataset["key"],
            "league": dataset["league"],
            "season": dataset["season"],
            "competition": dataset["competition"],
            "available_matches": len(event_set["matches"]),
            "imported_matches": len(matches),
            "errors": errors,
        }
        write_json(
            OUT / f"spatial_{dataset['key']}.json",
            {
                **aggregate_spatial(matches),
                **info,
                "fetched_at": utc_now(),
                "match_ids": [m["match_id"] for m in matches],
                "first_date": min((m["date"] for m in matches), default=None),
                "last_date": max((m["date"] for m in matches), default=None),
            },
        )
        report.append(info)
        print(
            f"{dataset['key']}: {len(matches)}/{len(event_set['matches'])} spatial matches; {len(errors)} errors",
            flush=True,
        )
    write_json(
        OUT / "spatial_manifest.json",
        {"sets": report, "built_at": utc_now(), "schema_version": VERSION},
    )
    return not any(s["errors"] for s in report)


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
