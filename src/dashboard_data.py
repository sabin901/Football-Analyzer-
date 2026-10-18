"""Shared five-league data contract. Current data: OpenFootball (CC0).

Fetch time is deliberately separate from the last recorded result date.
"""

from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
import argparse
import json
import math
import os
import re
import time
import unicodedata

ESPN_CODES = {"PL": "eng.1", "PD": "esp.1", "SA": "ita.1", "BL1": "ger.1", "FL1": "fra.1"}
# Explicit identity mapping; never fuzzy-match a result to a different club.
ALIASES = {
    "Levante": "Levante UD",
    "Atalanta": "Atalanta BC",
    "Atlético Madrid": "Club Atlético de Madrid",
    "Alavés": "Deportivo Alavés",
    "Celta Vigo": "RC Celta de Vigo",
    "Deportivo": "RC Deportivo La Coruña",
    "Espanyol": "RCD Espanyol de Barcelona",
    "Osasuna": "CA Osasuna",
    "Racing Santander": "Real Racing Club de Santander",
    "Rayo Vallecano": "Rayo Vallecano de Madrid",
    "Real Betis": "Real Betis Balompié",
    "Real Sociedad": "Real Sociedad de Fútbol",
    "Bologna": "Bologna FC 1909",
    "Como": "Como 1907",
    "Parma": "Parma Calcio 1913",
    "Internazionale": "FC Internazionale Milano",
    "Fiorentina": "ACF Fiorentina",
    "Lazio": "SS Lazio",
    "Napoli": "SSC Napoli",
    "Lecce": "US Lecce",
    "Sassuolo": "US Sassuolo Calcio",
    "Monza": "AC Monza",
    "Bayer Leverkusen": "Bayer 04 Leverkusen",
    "Bayern Munich": "FC Bayern München",
    "FC Cologne": "1. FC Köln",
    "Hamburg SV": "Hamburger SV",
    "Mainz": "1. FSV Mainz 05",
    "SV Elversberg": "SV 07 Elversberg",
    "TSG Hoffenheim": "TSG 1899 Hoffenheim",
    "Werder Bremen": "SV Werder Bremen",
    "Angers": "Angers SCO",
    "Brest": "Stade Brestois 29",
    "Lens": "Racing Club de Lens",
    "Lille": "Lille OSC",
    "Lyon": "Olympique Lyonnais",
    "Marseille": "Olympique de Marseille",
    "Nice": "OGC Nice",
    "Stade Rennais": "Stade Rennais FC 1901",
    "Strasbourg": "RC Strasbourg Alsace",
    "Troyes": "ES Troyes AC",
}


def normalized_name(name):
    name = "".join(
        c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c)
    ).lower()
    return " ".join(
        t
        for t in re.findall(r"[a-z0-9]+", name)
        if t not in {"fc", "cf", "afc", "ac", "as", "cfc", "calcio"}
    )


def fetch_json(url):
    with urlopen(
        Request(url, headers={"User-Agent": "FootballAnalyzer/2.0"}), timeout=25
    ) as response:
        return json.load(response)


def supplement_results(matches, league, season, previous=None, fetch=fetch_json, today=None):
    """Supplement recent results via ESPN's public, unofficial scoreboard.

    Retain per-record provenance. Only known home/away pairs within seven days
    of the schedule can be updated; mismatches remain missing, never guessed.
    """
    today = today or datetime.now(timezone.utc).date()
    previous = previous or {}
    old = {(m["home"], m["away"]): m for m in previous.get("matches", [])}
    names = {m[t] for m in matches for t in ("home", "away")}
    lookup = {normalized_name(n): n for n in names}
    for alias, canonical in ALIASES.items():
        if canonical in names:
            lookup[normalized_name(alias)] = canonical
    pairs = {(m["home"], m["away"]): m for m in matches}
    for pair, m in pairs.items():
        cached = old.get(pair)
        if m["hg"] is None and cached and cached.get("result_source") == "ESPN":
            for key in (
                "hg",
                "ag",
                "date",
                "result_source",
                "result_url",
                "result_checked_at",
                "status",
            ):
                m[key] = cached.get(key)
    days = sorted(
        {
            m["date"]
            for m in matches
            if m["date"]
            and (today - timedelta(days=14)).isoformat() <= m["date"] <= today.isoformat()
        }
    )
    errors = []
    for day in days:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{ESPN_CODES[league]}/scoreboard?dates={day.replace('-', '')}"
        try:
            payload = fetch(url)
            if not isinstance(payload.get("events"), list):
                raise ValueError("Scoreboard is missing its events array")
            for event in payload["events"]:
                event_status = event.get("status", {}).get("type", {})
                special = {
                    "STATUS_ABANDONED": "abandoned",
                    "STATUS_POSTPONED": "postponed",
                    "STATUS_CANCELED": "cancelled",
                }.get(event_status.get("name"))
                if not event_status.get("completed") and not special:
                    continue
                competition = event["competitions"][0]
                opponents = {c["homeAway"]: c for c in competition["competitors"]}
                h, a = opponents["home"], opponents["away"]
                home, away = lookup.get(normalized_name(h["team"]["displayName"])), lookup.get(
                    normalized_name(a["team"]["displayName"])
                )
                match = pairs.get((home, away))
                event_day = date.fromisoformat(event["date"][:10])
                if match is None:
                    errors.append(f"Unmapped completed fixture on {day}")
                    continue
                if (
                    event_day > today
                    or not match["date"]
                    or abs((event_day - date.fromisoformat(match["date"])).days) > 7
                ):
                    errors.append(f"Fixture date mismatch on {day}")
                    continue
                if special:
                    match.update(
                        hg=None,
                        ag=None,
                        status=special,
                        result_source="ESPN",
                        result_url=url,
                        result_checked_at=utc_now(),
                    )
                    continue
                scores = [h.get("score"), a.get("score")]
                if any(not re.fullmatch(r"\d{1,2}", str(s)) for s in scores):
                    raise ValueError("Invalid scoreboard score")
                match.update(
                    hg=int(scores[0]),
                    ag=int(scores[1]),
                    date=event_day.isoformat(),
                    status="finished",
                    result_source="ESPN",
                    result_url=url,
                    result_checked_at=utc_now(),
                )
        except Exception as exc:
            errors.append(f"{day}: {type(exc).__name__}")
    matches.sort(key=lambda m: (m["date"] or "9999", m["home"]))
    return errors


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "data" / "open" / "results"
LEAGUES = [
    {"id": "PL", "name": "Premier League", "country": "England", "file": "en.1", "teams": 20},
    {"id": "PD", "name": "La Liga", "country": "Spain", "file": "es.1", "teams": 20},
    {"id": "SA", "name": "Serie A", "country": "Italy", "file": "it.1", "teams": 20},
    {"id": "BL1", "name": "Bundesliga", "country": "Germany", "file": "de.1", "teams": 18},
    {"id": "FL1", "name": "Ligue 1", "country": "France", "file": "fr.1", "teams": 18},
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def current_season(today=None):
    today = today or datetime.now(timezone.utc).date()
    year = today.year if today.month >= 7 else today.year - 1
    return f"{year}-{str(year + 1)[-2:]}"


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        encoding="utf-8",
    )
    # Windows sync/indexing can briefly lock the destination. Preserve atomic
    # replacement and surface persistent permission failures after bounded retries.
    for attempt in range(6):
        try:
            os.replace(tmp, path)
            break
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.1 * 2**attempt)


def parse_openfootball(payload, season, today=None):
    today = today or datetime.now(timezone.utc).date()
    rows, seen = [], set()
    if not isinstance(payload.get("matches"), list) or not payload["matches"]:
        raise ValueError("Source contains no match schedule")
    for m in payload["matches"]:
        home, away, day = m.get("team1"), m.get("team2"), m.get("date")
        if (
            not isinstance(home, str)
            or not isinstance(away, str)
            or not home.strip()
            or not away.strip()
            or home == away
        ):
            raise ValueError("Invalid team identity")
        if day:
            parsed = date.fromisoformat(day)
            start = int(season[:4])
            # COVID-delayed 2019/20 league fixtures extended into summer 2020.
            end = date(2020, 9, 1) if start == 2019 else date(start + 1, 7, 1)
            if not date(start, 7, 1) <= parsed < end:
                raise ValueError("Match date outside requested season")
        raw_score = m.get("score", {})
        score = raw_score if isinstance(raw_score, list) else raw_score.get("ft")
        if score is not None:
            if (
                not isinstance(score, list)
                or len(score) != 2
                or any(type(v) is not int or v < 0 for v in score)
            ):
                raise ValueError("Invalid full-time score")
            if not day or parsed > today:
                raise ValueError("Completed result has a missing or future date")
        key = (home, away)
        if key in seen:
            raise ValueError("Duplicate league fixture")
        seen.add(key)
        rows.append(
            {
                "date": day,
                "home": home.strip(),
                "away": away.strip(),
                "hg": score[0] if score is not None else None,
                "ag": score[1] if score is not None else None,
                "round": str(m.get("round", "")),
            }
        )
    return sorted(rows, key=lambda m: (m["date"] or "9999", m["home"]))


def sync(seasons=None, live_dir=LIVE, fetch=None, today=None):
    from result_corrections import apply_corrections

    today = today or datetime.now(timezone.utc).date()
    seasons = seasons or [current_season(today)]
    status_path = live_dir / "dashboard_sync.json"
    status = read_json(status_path, {"leagues": {}})
    failures = []
    for season in seasons:
        if not re.fullmatch(r"20\d{2}-\d{2}", season):
            raise ValueError("Invalid season")
        for league in LEAGUES:
            key = f"{league['id']}_{season}"
            url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{league['file']}.json"
            try:
                if fetch:
                    payload = fetch(url)
                else:
                    with urlopen(
                        Request(url, headers={"User-Agent": "FootballAnalyzer/2.0"}), timeout=30
                    ) as response:
                        payload = json.load(response)
                matches = parse_openfootball(payload, season, today)
                teams = {m[t] for m in matches for t in ("home", "away")}
                if len(teams) != league["teams"]:
                    raise ValueError(f"Expected {league['teams']} teams; received {len(teams)}")
                if len(matches) != len(teams) * (len(teams) - 1):
                    raise ValueError("Incomplete league schedule")
                fetched = utc_now()
                supplement_errors = []
                if season == current_season(today) and fetch is None:
                    previous = read_json(live_dir / f"dashboard_{key}.json", {})
                    supplement_errors = supplement_results(
                        matches, league["id"], season, previous, today=today
                    )
                supplemented = any(m.get("result_source") == "ESPN" for m in matches)
                write_json(
                    live_dir / f"dashboard_{key}.json",
                    apply_corrections(
                        {
                            "league": league["id"],
                            "season": season,
                            "source": "OpenFootball + ESPN" if supplemented else "OpenFootball",
                            "source_url": url,
                            "license": (
                                "CC0 schedule; ESPN terms for supplemented results"
                                if supplemented
                                else "CC0-1.0"
                            ),
                            "fetched_at": fetched,
                            "matches": matches,
                            "supplement_errors": supplement_errors,
                        }
                    ),
                )
                status["leagues"][key] = {"checked_at": fetched, "ok": not supplement_errors}
                if supplement_errors:
                    failures.append(key)
                    print(f"{key}: scoreboard warnings: {supplement_errors}")
                print(
                    f"{key}: {len(matches)} fixtures, {sum(m['hg'] is not None for m in matches)} results"
                )
            except Exception as exc:
                status["leagues"][key] = {"checked_at": utc_now(), "ok": False, "error": str(exc)}
                failures.append(key)
                print(f"{key}: refresh failed; preserving previous snapshot ({exc})")
    write_json(status_path, status)
    return failures


def standings(matches, venue="all", last=None):
    names = sorted({m[t] for m in matches for t in ("home", "away")})
    rows = []
    for team in names:
        games = [
            m
            for m in matches
            if m["hg"] is not None
            and ((m["home"] == team and venue != "away") or (m["away"] == team and venue != "home"))
        ]
        games.sort(key=lambda m: m["date"] or "")
        if last:
            games = games[-last:]
        row = dict(team=team, p=0, w=0, d=0, l=0, gf=0, ga=0, pts=0, cs=0, form=[])
        for m in games:
            gf, ga = (m["hg"], m["ag"]) if m["home"] == team else (m["ag"], m["hg"])
            awarded = m.get("awarded_winner")
            result = (
                ("W" if awarded == team else "L")
                if awarded
                else "W" if gf > ga else "D" if gf == ga else "L"
            )
            row["p"] += 1
            row[result.lower()] += 1
            row["gf"] += gf
            row["ga"] += ga
            row["pts"] += 3 if result == "W" else 1 if result == "D" else 0
            row["cs"] += ga == 0
            row["form"].append(result)
        row["gd"] = row["gf"] - row["ga"]
        row["ppg"] = round(row["pts"] / row["p"], 2) if row["p"] else None
        row["form"] = row["form"][-5:]
        rows.append(row)
    return sorted(rows, key=lambda r: (-r["pts"], -r["gd"], -r["gf"], r["team"]))


def baseline_prediction(matches, home, away):
    """Smoothed Poisson baseline, not shot-based xG or calibrated probabilities.

    Five prior venue games at the league mean temper small samples.
    Only completed results in the selected season enter the calculation.
    """
    teams = {m[t] for m in matches for t in ("home", "away")}
    if home == away or home not in teams or away not in teams:
        raise ValueError("Select two different teams from this league-season")
    done = [m for m in matches if m["hg"] is not None]
    if len(done) < 30:
        return None
    hg, ag = (sum(m[k] for m in done) / len(done) for k in ("hg", "ag"))
    if hg <= 0 or ag <= 0:
        return None
    h = [m for m in done if m["home"] == home]
    a = [m for m in done if m["away"] == away]
    if len(h) < 2 or len(a) < 2:
        return None

    def rate(games, field, mean):
        return (sum(m[field] for m in games) + 5 * mean) / (len(games) + 5)

    lam = rate(h, "hg", hg) * rate(a, "hg", hg) / hg
    mu = rate(a, "ag", ag) * rate(h, "ag", ag) / ag
    cells = [
        (i, j, math.exp(-lam - mu) * lam**i * mu**j / (math.factorial(i) * math.factorial(j)))
        for i in range(16)
        for j in range(16)
    ]
    total = sum(p for _, _, p in cells)
    probs = [
        sum(p for i, j, p in cells if condition(i, j)) / total
        for condition in (lambda i, j: i > j, lambda i, j: i == j, lambda i, j: i < j)
    ]
    return {
        "home": home,
        "away": away,
        "p_home": probs[0],
        "p_draw": probs[1],
        "p_away": probs[2],
        "home_goals": round(lam, 2),
        "away_goals": round(mu, 2),
        "sample": len(done),
        "home_sample": len(h),
        "away_sample": len(a),
        "scorelines": [
            {"score": f"{i}–{j}", "p": p / total}
            for i, j, p in sorted(cells, key=lambda c: -c[2])[:5]
        ],
    }


def enrich(payload, status=None, today=None):
    from data_quality import quality_for, apply_standings

    today = today or datetime.now(timezone.utc).date()
    matches = payload["matches"]
    done = [m for m in matches if m["hg"] is not None]
    overdue = sum(
        m["hg"] is None
        and m.get("status") not in {"abandoned", "postponed", "cancelled"}
        and bool(m["date"])
        and m["date"] < today.isoformat()
        for m in matches
    )
    last = max((m["date"] for m in done), default=None)
    quality = quality_for(payload)
    return {
        **payload,
        "table": apply_standings(payload, quality),
        "quality": quality,
        "last_result": last,
        "completed": len(done),
        "overdue": overdue,
        "refresh_ok": (status or {}).get("ok"),
        "coverage": "partial" if overdue else "available" if done else "schedule only",
    }


def snapshot(league, season, live_dir=LIVE):
    if league not in {l["id"] for l in LEAGUES} or not re.fullmatch(r"20\d{2}-\d{2}", season):
        raise ValueError("Unknown league or invalid season")
    payload = read_json(live_dir / f"dashboard_{league}_{season}.json")
    if payload is None:
        raise FileNotFoundError("No snapshot for this league-season")
    status = read_json(live_dir / "dashboard_sync.json", {"leagues": {}})
    return enrich(payload, status["leagues"].get(f"{league}_{season}"))


if __name__ == "__main__":
    from open_results import sync as sync_open

    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", action="store_true")
    raise SystemExit(bool(sync_open(parser.parse_args().archive)))
