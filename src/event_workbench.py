"""Resumable import of every available men's top-five StatsBomb open match.

Derived research outputs retain provider player/team/event IDs and xG. The open
selections are NOT representative full leagues unless coverage demonstrates it.
"""

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from datetime import date
from dashboard_data import ROOT, read_json, write_json, utc_now, fetch_json
from workbench_data import cached_fetch, OUT

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
LEAGUE_IDS = {2: "PL", 11: "PD", 12: "SA", 9: "BL1", 7: "FL1"}
METRICS = [
    "shots",
    "npxg",
    "np_goals",
    "key_passes",
    "passes",
    "completed_passes",
    "progressive_passes",
    "progressive_carries",
    "pressures",
    "recoveries",
    "interceptions",
    "tackles",
]


def position_group(name):
    if "Goalkeeper" in name:
        return "GK"
    if "Back" in name:
        return "DEF"
    if any(x in name for x in ("Forward", "Wing", "Striker")):
        return "FWD"
    return "MID"


def progressive(start, end):
    return (
        isinstance(start, list)
        and isinstance(end, list)
        and len(start) >= 2
        and len(end) >= 2
        and end[0] >= 72
        and math.hypot(120 - start[0], 40 - start[1]) - math.hypot(120 - end[0], 40 - end[1]) >= 10
    )


def summarize(events, match):
    if type(match.get("match_id")) is not int or match["match_id"] <= 0:
        raise ValueError("Invalid provider match ID")
    if date.fromisoformat(match["match_date"]) > date.today():
        raise ValueError("Future event match")
    if any(type(match.get(k)) is not int or match[k] < 0 for k in ("home_score", "away_score")):
        raise ValueError("Invalid event match score")
    if (
        not isinstance(events, list)
        or not events
        or not any(e.get("type", {}).get("name") == "Half End" for e in events)
    ):
        raise ValueError("Empty or incomplete event feed")
    if len({e["id"] for e in events}) != len(events):
        raise ValueError("Duplicate event IDs")
    players, active, minutes, positions = {}, {}, defaultdict(float), {}
    duration = 120 if any(e.get("period") in (3, 4) for e in events) else 90
    shots, connections = [], Counter()

    def player(pid, name, team):
        if pid not in players:
            players[pid] = {
                "id": pid,
                "name": name,
                "team_id": team["id"],
                "team": team["name"],
                **{m: 0 for m in METRICS},
            }
        return players[pid]

    for e in sorted(events, key=lambda e: e["index"]):
        t = e.get("type", {}).get("name")
        minute = min(duration, e.get("minute", 0) + e.get("second", 0) / 60)
        team = e.get("team", {})
        if t == "Starting XI":
            for p in e.get("tactics", {}).get("lineup", []):
                pid = p["player"]["id"]
                player(pid, p["player"]["name"], team)
                active[pid] = 0
                positions[pid] = position_group(p["position"]["name"])
        p = e.get("player")
        if not p or e.get("period", 1) > 4:
            continue  # Shootouts are not league shot performance.
        pid = p["id"]
        row = player(pid, p["name"], team)
        positions.setdefault(pid, position_group(e.get("position", {}).get("name", "")))
        if t == "Substitution":
            if pid in active:
                minutes[pid] += max(0, minute - active.pop(pid))
            replacement = e["substitution"]["replacement"]
            rid = replacement["id"]
            player(rid, replacement["name"], team)
            active[rid] = minute
            positions.setdefault(rid, positions.get(pid, "MID"))
        card = (
            e.get("bad_behaviour", {})
            .get("card", e.get("foul_committed", {}).get("card", {}))
            .get("name")
        )
        if card in ("Red Card", "Second Yellow") and pid in active:
            minutes[pid] += max(0, minute - active.pop(pid))
        loc = e.get("location")
        if t == "Shot":
            shot = e["shot"]
            penalty = shot.get("type", {}).get("name") == "Penalty"
            xg = shot.get("statsbomb_xg")
            if xg is None or not 0 <= xg <= 1:
                raise ValueError("Invalid provider shot xG")
            goal = shot.get("outcome", {}).get("name") == "Goal"
            if not penalty:
                row["shots"] += 1
                row["npxg"] += xg
                row["np_goals"] += int(goal)
            if isinstance(loc, list):
                # Provider corner locations can be 120.2; preserve the measurement.
                if (
                    len(loc) < 2
                    or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in loc[:2])
                    or not (-1 <= loc[0] <= 121 and -1 <= loc[1] <= 81)
                ):
                    raise ValueError("Invalid shot coordinates")
                shots.append(
                    {
                        "id": e["id"],
                        "player_id": pid,
                        "player": p["name"],
                        "team_id": team["id"],
                        "minute": e.get("minute"),
                        "x": loc[0],
                        "y": loc[1],
                        "xg": xg,
                        "goal": goal,
                        "outcome": shot.get("outcome", {}).get("name"),
                        "penalty": penalty,
                        "body_part": shot.get("body_part", {}).get("name"),
                        "play_pattern": e.get("play_pattern", {}).get("name"),
                    }
                )
        elif t == "Pass":
            passing = e["pass"]
            completed = "outcome" not in passing
            row["passes"] += 1
            row["completed_passes"] += int(completed)
            row["key_passes"] += int(bool(passing.get("shot_assist")))
            row["progressive_passes"] += int(
                bool(completed and progressive(loc, passing.get("end_location")))
            )
            if completed and passing.get("recipient"):
                connections[(team["id"], pid, passing["recipient"]["id"])] += 1
        elif t == "Carry":
            row["progressive_carries"] += int(
                bool(progressive(loc, e["carry"].get("end_location")))
            )
        elif t == "Pressure":
            row["pressures"] += 1
        elif t == "Ball Recovery":
            row["recoveries"] += int(not e.get("ball_recovery", {}).get("recovery_failure"))
        elif t == "Interception":
            row["interceptions"] += 1
        elif t == "Duel" and e.get("duel", {}).get("type", {}).get("name") == "Tackle":
            row["tackles"] += 1
    for pid, start in active.items():
        minutes[pid] += max(0, duration - start)
    for pid, row in players.items():
        row["minutes"] = round(minutes.get(pid, 0), 2)
        row["position"] = positions.get(pid, "MID")
        row["npxg"] = round(row["npxg"], 4)
    return {
        "id": match["match_id"],
        "date": match["match_date"],
        "home": match["home_team"]["home_team_name"],
        "away": match["away_team"]["away_team_name"],
        "home_id": match["home_team"]["home_team_id"],
        "away_id": match["away_team"]["away_team_id"],
        "hg": match["home_score"],
        "ag": match["away_score"],
        "events": len(events),
        "players": list(players.values()),
        "shots": shots,
        "pass_links": [
            {"team_id": k[0], "from": k[1], "to": k[2], "count": n}
            for k, n in connections.most_common(40)
        ],
        "source_url": f"{BASE}/events/{match['match_id']}.json",
        "source_updated": match.get("last_updated"),
        "fetched_at": utc_now(),
        "event_sha256": hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest(),
    }


def aggregate(matches):
    rows = {}
    for match in matches:
        for p in match["players"]:
            key = (p["id"], p["team_id"])
            if key not in rows:
                rows[key] = {k: p[k] for k in ("id", "name", "team", "team_id")}
                rows[key].update({m: 0 for m in METRICS})
                rows[key].update(minutes=0, matches=0, positions={})
            r = rows[key]
            r["minutes"] += p["minutes"]
            r["matches"] += int(p["minutes"] > 0)
            r["positions"][p["position"]] = r["positions"].get(p["position"], 0) + p["minutes"]
            for m in METRICS:
                r[m] += p[m]
    for r in rows.values():
        r["position"] = max(r.pop("positions").items(), key=lambda kv: kv[1])[0]
        r["minutes"] = round(r["minutes"], 1)
        r["npxg"] = round(r["npxg"], 3)
        r["per90"] = {
            m: round(r[m] * 90 / r["minutes"], 3) if r["minutes"] > 0 else None for m in METRICS
        }
        r["pass_pct"] = round(100 * r["completed_passes"] / r["passes"], 1) if r["passes"] else None
    return sorted(rows.values(), key=lambda p: -p["minutes"])


def run():
    competitions = cached_fetch(BASE + "/competitions.json", 24)
    write_json(OUT / "event_catalogue.json", competitions)
    sets = []
    for c in competitions:
        if c["competition_id"] not in LEAGUE_IDS or c.get("competition_gender") != "male":
            continue
        key = f"{c['competition_id']}_{c['season_id']}"
        catalogue = cached_fetch(f"{BASE}/matches/{c['competition_id']}/{c['season_id']}.json", 24)
        errors = []
        matches = []

        def one(match):
            if type(match.get("match_id")) is not int or match["match_id"] <= 0:
                return None, {
                    "match_id": str(match.get("match_id")),
                    "error": "Invalid provider match ID",
                }
            path = OUT / "event_matches" / f"{match['match_id']}.json"
            old = read_json(path, {})
            if (
                old.get("source_updated") == match.get("last_updated")
                and old.get("parser_version") == 1
            ):
                return old, None
            try:
                result = summarize(fetch_json(f"{BASE}/events/{match['match_id']}.json"), match)
                result["parser_version"] = 1
                write_json(path, result)
                return result, None
            except Exception as exc:
                return old or None, {"match_id": match["match_id"], "error": str(exc)}

        with ThreadPoolExecutor(max_workers=3) as pool:
            for row, error in pool.map(one, catalogue):
                if row:
                    matches.append(row)
                if error:
                    errors.append(error)
        matches.sort(key=lambda m: m["date"])
        players = aggregate(matches)
        info = {
            "key": key,
            "league": LEAGUE_IDS[c["competition_id"]],
            "competition": c["competition_name"],
            "season": c["season_name"],
            "available_matches": len(catalogue),
            "imported_matches": len(matches),
            "players": len(players),
            "events": sum(m["events"] for m in matches),
            "errors": errors,
            "first_date": matches[0]["date"] if matches else None,
            "last_date": matches[-1]["date"] if matches else None,
        }
        write_json(
            OUT / f"events_{key}.json",
            {
                **info,
                "source": "StatsBomb Open Data",
                "fetched_at": utc_now(),
                "source_url": f'https://github.com/statsbomb/open-data/tree/master/data/matches/{c["competition_id"]}',
                "coverage_note": "Provider-selected historical matches; not assumed to be a full league or representative sample.",
                "minutes_note": "Regulation/extra-time clock estimate from starting XI, substitutions and dismissals; stoppage time excluded.",
                "player_rows": players,
                "matches": [
                    {k: v for k, v in m.items() if k not in ("players", "shots", "pass_links")}
                    for m in matches
                ],
            },
        )
        sets.append(info)
        write_json(
            OUT / "events_manifest.json",
            {"fetched_at": utc_now(), "sets": sets, "source": "StatsBomb Open Data"},
        )
        print(
            f"{c['competition_name']} {c['season_name']}: {len(matches)}/{len(catalogue)} matches, {len(players)} players, {len(errors)} failures",
            flush=True,
        )


if __name__ == "__main__":
    run()
