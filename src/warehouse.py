"""Rebuild an indexed SQLite research warehouse from validated snapshots."""

import json
import sqlite3
from dashboard_data import ROOT, LIVE, read_json
from open_policy import WORKBENCH as OUT


def build():
    path = ROOT / "data" / "football.sqlite"
    temp = path.with_suffix(".tmp")
    if temp.exists():
        temp.unlink()
    db = sqlite3.connect(temp)
    db.executescript("""
      CREATE TABLE results (league TEXT, season TEXT, date TEXT, home TEXT, away TEXT,
        home_goals INTEGER, away_goals INTEGER, source TEXT, fetched_at TEXT,
        status TEXT, awarded_winner TEXT, exclude_from_model INTEGER, review_json TEXT,
        PRIMARY KEY(league,season,home,away));
      CREATE INDEX results_date ON results(league,date);
      CREATE TABLE player_appearances (league TEXT, season TEXT, match_id TEXT, player_id TEXT,
        team_id TEXT, player TEXT, position TEXT, starter INTEGER, stats_json TEXT,
        PRIMARY KEY(league,match_id,player_id,team_id));
      CREATE INDEX appearances_player ON player_appearances(player_id,league);
      CREATE TABLE event_players (dataset TEXT, player_id INTEGER, team_id INTEGER, player TEXT,
        team TEXT, position TEXT, minutes REAL, matches INTEGER, npxg REAL, shots INTEGER,
        key_passes INTEGER, progressive_passes INTEGER, PRIMARY KEY(dataset,player_id,team_id));
      CREATE TABLE shots (match_id INTEGER, event_id TEXT PRIMARY KEY, player_id INTEGER,
        team_id INTEGER, minute INTEGER, x REAL, y REAL, xg REAL, goal INTEGER, penalty INTEGER);
      CREATE INDEX shots_player ON shots(player_id);
      CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
    """)
    for file in LIVE.glob("dashboard_*.json"):
        raw = read_json(file)
        if "matches" not in raw:
            continue
        db.executemany(
            "INSERT INTO results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    raw["league"],
                    raw["season"],
                    m["date"],
                    m["home"],
                    m["away"],
                    m["hg"],
                    m["ag"],
                    m.get("result_source", "OpenFootball"),
                    raw["fetched_at"],
                    m.get("status"),
                    m.get("awarded_winner"),
                    int(bool(m.get("exclude_from_model"))),
                    json.dumps(m["result_review"]) if m.get("result_review") else None,
                )
                for m in raw["matches"]
            ],
        )
    for file in OUT.glob("current_*.json"):
        raw = read_json(file)
        for m in raw["matches"]:
            db.executemany(
                "INSERT INTO player_appearances VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    (
                        raw["league"],
                        raw["season"],
                        m["id"],
                        p["id"],
                        p["team_id"],
                        p["name"],
                        p["position"],
                        p["starter"],
                        json.dumps(p["stats"]),
                    )
                    for p in m["players"]
                ],
            )
    for file in OUT.glob("events_*.json"):
        raw = read_json(file)
        if "player_rows" not in raw:
            continue
        db.executemany(
            "INSERT INTO event_players VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    raw["key"],
                    p["id"],
                    p["team_id"],
                    p["name"],
                    p["team"],
                    p["position"],
                    p["minutes"],
                    p["matches"],
                    p["npxg"],
                    p["shots"],
                    p["key_passes"],
                    p["progressive_passes"],
                )
                for p in raw["player_rows"]
            ],
        )
    for file in (OUT / "event_matches").glob("*.json"):
        raw = read_json(file)
        db.executemany(
            "INSERT INTO shots VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    raw["id"],
                    s["id"],
                    s["player_id"],
                    s["team_id"],
                    s["minute"],
                    s["x"],
                    s["y"],
                    s["xg"],
                    s["goal"],
                    s["penalty"],
                )
                for s in raw["shots"]
            ],
        )
    db.execute(
        "INSERT INTO metadata VALUES (?,?)",
        (
            "sources",
            "OpenFootball CC0-1.0; Pappalardo/Wyscout research dataset CC-BY-4.0. Attribution and transformations: source_registry.json.",
        ),
    )
    db.commit()
    db.close()
    temp.replace(path)
    return path


if __name__ == "__main__":
    print(build())
