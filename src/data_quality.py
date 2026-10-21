"""Reconcile published standings and cross-provider scores without guessing corrections."""

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen

from dashboard_data import (
    LIVE,
    ESPN_CODES,
    current_season,
    read_json,
    write_json,
    utc_now,
    standings,
)
from club_identity import resolver

DIVISIONS = {"PL": "E0", "PD": "SP1", "SA": "I1", "BL1": "D1", "FL1": "F1"}


def results_digest(matches):
    rows = sorted(
        (
            m["home"],
            m["away"],
            m.get("date"),
            m["hg"],
            m["ag"],
            m.get("status"),
            m.get("awarded_winner"),
            m.get("exclude_from_model"),
        )
        for m in matches
    )
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode()).hexdigest()


def parse_standings(raw, snapshot):
    year = int(snapshot["season"][:4])
    if raw.get("season", {}).get("year") != year:
        raise ValueError("Standings season does not match requested season")
    groups = [
        g["standings"]
        for g in raw.get("children", [])
        if g.get("standings", {}).get("name") == "overall"
    ]
    if len(groups) != 1 or groups[0].get("season") != year:
        raise ValueError("Expected one overall table for the requested season")
    calculated = {r["team"]: r for r in standings(snapshot["matches"])}
    resolve = resolver(calculated)
    rows, issues, seen = [], [], set()
    fields = {
        "p": "gamesPlayed",
        "w": "wins",
        "d": "ties",
        "l": "losses",
        "gf": "pointsFor",
        "ga": "pointsAgainst",
        "pts": "points",
        "rank": "rank",
    }
    for entry in groups[0]["entries"]:
        name = entry["team"]["displayName"]
        team = resolve(name)
        if team is None or team in seen:
            raise ValueError(f"Unknown or duplicate standings club: {name}")
        seen.add(team)
        stats = {s["name"]: s.get("value") for s in entry["stats"]}
        row = {"team": team, "provider_team_id": str(entry["team"]["id"])}
        for key, source in fields.items():
            value = stats.get(source)
            if not isinstance(value, (int, float)) or not float(value).is_integer():
                raise ValueError(f"Invalid standings {source}: {name}")
            row[key] = int(value)
        if row["p"] != row["w"] + row["d"] + row["l"] or any(
            row[k] < 0 for k in ("p", "w", "d", "l", "gf", "ga")
        ):
            raise ValueError("Invalid standings arithmetic")
        row["adjustment"] = row["pts"] - (3 * row["w"] + row["d"])
        for key in ("p", "w", "d", "l", "gf", "ga"):
            if row[key] != calculated[team][key]:
                issues.append(
                    {
                        "team": team,
                        "field": key,
                        "results": calculated[team][key],
                        "provider": row[key],
                    }
                )
        rows.append(row)
    if seen != set(calculated) or {r["rank"] for r in rows} != set(range(1, len(rows) + 1)):
        raise ValueError("Incomplete standings identities or ranking")
    return {
        "status": "matched" if not issues else "mismatch",
        "rows": sorted(rows, key=lambda r: r["rank"]),
        "issues": issues,
    }


def compare_results(text, snapshot):
    local = {(m["home"], m["away"]): m for m in snapshot["matches"] if m["hg"] is not None}
    resolve = resolver({m[k] for m in snapshot["matches"] for k in ("home", "away")})
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not {"HomeTeam", "AwayTeam", "Date", "FTHG", "FTAG"} <= set(reader.fieldnames or []):
        raise ValueError("Results source is missing required CSV columns")
    matched, issues, seen, missing, reviewed = 0, [], set(), [], []
    for row in reader:
        if not row.get("HomeTeam") or row.get("FTHG") in (None, ""):
            continue
        home, away = resolve(row["HomeTeam"]), resolve(row["AwayTeam"])
        if home is None or away is None:
            raise ValueError(f"Unmapped results club: {row['HomeTeam']} / {row['AwayTeam']}")
        pair = (home, away)
        if pair in seen:
            raise ValueError("Duplicate second-provider fixture")
        seen.add(pair)
        day = None
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                day = datetime.strptime(row["Date"], fmt).date().isoformat()
                break
            except ValueError:
                pass
        if (
            day is None
            or not f"{snapshot['season'][:4]}-07-01"
            <= day
            < f"{int(snapshot['season'][:4])+1}-09-01"
        ):
            raise ValueError("Results source date outside requested season")
        hg, ag = int(row["FTHG"]), int(row["FTAG"])
        if min(hg, ag) < 0:
            raise ValueError("Negative final score")
        original = local.get(pair)
        if original is None:
            missing.append({"home": home, "away": away, "source": "local"})
        elif (original["hg"], original["ag"], original["date"]) != (hg, ag, day):
            difference = {
                "home": home,
                "away": away,
                "local": [original["date"], original["hg"], original["ag"]],
                "reference": [day, hg, ag],
            }
            review = original.get("result_review", {})
            if review.get("reference_result") == [day, hg, ag] and review.get("sources"):
                reviewed.append({**difference, "review": review})
            else:
                issues.append(difference)
        else:
            matched += 1
    missing.extend(
        {"home": h, "away": a, "source": "reference"} for h, a in sorted(set(local) - seen)
    )
    return {
        "status": (
            "conflict"
            if issues
            else "partial" if missing else "reviewed" if reviewed else "matched"
        ),
        "matched": matched,
        "local_results": len(local),
        "reference_results": len(seen),
        "conflicts": issues,
        "unmatched": missing,
        "reviewed": reviewed,
    }


def fetch_text(url):
    with urlopen(Request(url, headers={"User-Agent": "Footlyzer/3.0"}), timeout=30) as response:
        return response.read().decode("utf-8-sig")


def refresh(path, source_dir=None):
    snapshot = read_json(path)
    league, season = snapshot["league"], snapshot["season"]
    key = f"{league}_{season}"
    urls = {
        "standings": f"https://site.api.espn.com/apis/v2/sports/soccer/{ESPN_CODES[league]}/standings?season={season[:4]}",
        "results": f"https://www.football-data.co.uk/mmz4281/{season[2:4]+season[-2:]}/{DIVISIONS[league]}.csv",
    }
    output = {
        "schema_version": 1,
        "league": league,
        "season": season,
        "checked_at": utc_now(),
        "results_digest": results_digest(snapshot["matches"]),
    }
    for kind, url in urls.items():
        try:
            text = (
                (Path(source_dir) / f"{kind}_{key}.txt").read_text()
                if source_dir
                else fetch_text(url)
            )
            result = (
                parse_standings(json.loads(text), snapshot)
                if kind == "standings"
                else compare_results(text, snapshot)
            )
            output[kind] = {
                **result,
                "source_url": url,
                "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
        except Exception as exc:
            output[kind] = {"status": "unavailable", "source_url": url, "error": str(exc)}
    write_json(LIVE / f"quality_{key}.json", output)
    print(key, output["standings"]["status"], output["results"]["status"], flush=True)
    return output


def quality_for(snapshot, live_dir=LIVE):
    if snapshot.get("source_id") == "football_data_org":
        quality = snapshot.get("quality", {})
        if quality.get("results_digest") == results_digest(snapshot["matches"]):
            return quality
        return {}
    quality = read_json(
        live_dir / f"quality_{snapshot.get('league')}_{snapshot.get('season')}.json", {}
    )
    if not quality or quality.get("results_digest") != results_digest(snapshot["matches"]):
        return {"standings": {"status": "unavailable"}, "results": {"status": "unchecked"}}
    return quality


def apply_standings(snapshot, quality):
    rows = standings(snapshot["matches"])
    reference = quality.get("standings", {})
    if reference.get("status") != "matched":
        return rows
    by_team = {r["team"]: r for r in reference["rows"]}
    return sorted(
        [
            {
                **r,
                "match_points": r["pts"],
                "pts": by_team[r["team"]]["pts"],
                "adjustment": by_team[r["team"]]["adjustment"],
                "rank": by_team[r["team"]]["rank"],
            }
            for r in rows
        ],
        key=lambda r: r["rank"],
    )


if __name__ == "__main__":
    import os

    if os.environ.get("FOOTLYZER_LICENSED_RESEARCH") != "1":
        raise SystemExit(
            "Legacy restricted feed disabled. Public workflows use src/open_results.py and src/open_events.py. Local research requires your own provider authorization."
        )
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--source-dir")
    args = parser.parse_args()
    paths = sorted(
        LIVE.glob("dashboard_*_20*.json" if args.all else f"dashboard_*_{current_season()}.json")
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda p: refresh(p, args.source_dir), paths))
