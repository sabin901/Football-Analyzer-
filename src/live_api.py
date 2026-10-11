"""
Live + bulk data importer — the data API for Football Analyzer.

Two free sources, no sandbox required (these run wherever the internet is open:
your machine, or a GitHub Actions runner on a schedule):

  1. football-data.org  — a free REST API for LIVE fixtures, results, standings
     and scorers across the major leagues (PL, La Liga, Serie A, Bundesliga,
     Ligue 1, Champions League, World Cup, ...). Needs a free API key:
     https://www.football-data.org/client/register  (free tier: 10 req/min).
     Set it as the environment variable FOOTBALL_DATA_API_KEY.

  2. football-data.co.uk — direct CSV downloads of historical results + BETTING
     ODDS for ~22 leagues back to the 1990s. No key. This is the odds backbone
     for turning the predictor into a true "beat-the-market" model.

Everything is saved under data/live/ as parquet + json so the predictor, the
site builder, and the web app can read it.

Usage:
    # live (needs a free key in FOOTBALL_DATA_API_KEY)
    python src/live_api.py sync            # recent + upcoming matches + standings
    python src/live_api.py standings PL
    python src/live_api.py matches PL --days 10

    # historical results + odds (no key)
    python src/live_api.py odds E0 2324    # Premier League, 2023/24
    python src/live_api.py odds SP1 2324   # La Liga, 2023/24
"""

import os
import sys
import json
import time
import argparse
import datetime as dt
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE_DIR = os.path.join(HERE, "..", "data", "live")

FD_BASE = "https://api.football-data.org/v4"
FD_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "")

# Free-tier competition codes on football-data.org
COMPETITIONS = {
    "PL": "Premier League", "PD": "La Liga", "SA": "Serie A",
    "BL1": "Bundesliga", "FL1": "Ligue 1", "DED": "Eredivisie",
    "PPL": "Primeira Liga", "ELC": "Championship", "CL": "Champions League",
    "EC": "European Championship", "WC": "World Cup", "BSA": "Brazil Série A",
}

# football-data.co.uk league codes (for odds CSVs)
#   E0 = Premier League, E1 = Championship, SP1 = La Liga, I1 = Serie A,
#   D1 = Bundesliga, F1 = Ligue 1, N1 = Eredivisie, P1 = Primeira Liga
ODDS_URL = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"


def _ensure_dir():
    os.makedirs(LIVE_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# football-data.org (live REST API)
# ---------------------------------------------------------------------------
def _fd_get(path, params=None):
    if not FD_KEY:
        raise RuntimeError(
            "No API key. Get a free one at football-data.org and set "
            "FOOTBALL_DATA_API_KEY. (Not needed for the 'odds' command.)")
    url = FD_BASE + path
    if params:
        q = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        url += "?" + q
    req = Request(url, headers={"X-Auth-Token": FD_KEY})
    for attempt in range(4):
        try:
            with urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except HTTPError as e:
            if e.code == 429:            # rate limited: free tier = 10/min
                time.sleep(6)
                continue
            raise
        except URLError:
            time.sleep(3)
    raise RuntimeError(f"Failed to fetch {path} after retries")


def parse_matches(payload):
    """Turn a football-data.org /matches payload into tidy rows.

    Kept separate from the HTTP call so it can be unit-tested with sample JSON.
    """
    rows = []
    for m in payload.get("matches", []):
        score = m.get("score", {}).get("fullTime", {})
        rows.append({
            "match_id": m.get("id"),
            "competition": m.get("competition", {}).get("name",
                           payload.get("competition", {}).get("name", "")),
            "utc_date": m.get("utcDate"),
            "status": m.get("status"),               # SCHEDULED/LIVE/FINISHED...
            "matchday": m.get("matchday"),
            "home_team": m.get("homeTeam", {}).get("name"),
            "away_team": m.get("awayTeam", {}).get("name"),
            "home_score": score.get("home"),
            "away_score": score.get("away"),
        })
    return rows


def parse_standings(payload):
    rows = []
    for table in payload.get("standings", []):
        if table.get("type") != "TOTAL":
            continue
        for e in table.get("table", []):
            rows.append({
                "competition": payload.get("competition", {}).get("name", ""),
                "position": e.get("position"),
                "team": e.get("team", {}).get("name"),
                "played": e.get("playedGames"),
                "won": e.get("won"), "draw": e.get("draw"), "lost": e.get("lost"),
                "points": e.get("points"),
                "goals_for": e.get("goalsFor"), "goals_against": e.get("goalsAgainst"),
                "goal_difference": e.get("goalDifference"),
            })
    return rows


def matches(code, days=10, past=True):
    """Upcoming (and optionally recent) matches for a competition."""
    import pandas as pd
    _ensure_dir()
    today = dt.date.today()
    date_from = (today - dt.timedelta(days=days if past else 0)).isoformat()
    date_to = (today + dt.timedelta(days=days)).isoformat()
    payload = _fd_get(f"/competitions/{code}/matches",
                      {"dateFrom": date_from, "dateTo": date_to})
    rows = parse_matches(payload)
    df = pd.DataFrame(rows)
    out = os.path.join(LIVE_DIR, f"matches_{code}.parquet")
    df.to_parquet(out, index=False)
    print(f"{code}: {len(df)} matches ({date_from} → {date_to}) -> {out}")
    return df


def standings(code):
    import pandas as pd
    _ensure_dir()
    payload = _fd_get(f"/competitions/{code}/standings")
    df = pd.DataFrame(parse_standings(payload))
    out = os.path.join(LIVE_DIR, f"standings_{code}.parquet")
    df.to_parquet(out, index=False)
    print(f"{code}: standings for {len(df)} teams -> {out}")
    return df


def sync(codes=None, days=10):
    """Pull recent+upcoming matches and standings for a set of leagues.

    This is what the scheduled GitHub Action calls. Respects the free-tier
    rate limit with small pauses.
    """
    codes = codes or ["PL", "PD", "SA", "BL1", "FL1"]
    manifest = {"synced_at": dt.datetime.utcnow().isoformat() + "Z", "leagues": {}}
    for code in codes:
        try:
            m = matches(code, days=days)
            time.sleep(6)
            s = standings(code)
            time.sleep(6)
            manifest["leagues"][code] = {
                "name": COMPETITIONS.get(code, code),
                "matches": int(len(m)), "teams": int(len(s))}
        except Exception as e:
            print(f"  {code} failed: {e}")
            manifest["leagues"][code] = {"error": str(e)}
    _ensure_dir()
    with open(os.path.join(LIVE_DIR, "sync_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nSync complete: {sum('matches' in v for v in manifest['leagues'].values())} leagues OK")
    return manifest


# ---------------------------------------------------------------------------
# football-data.co.uk (historical results + odds, no key)
# ---------------------------------------------------------------------------
def odds(code="E0", season="2324"):
    """Download one league-season CSV of results + betting odds."""
    import pandas as pd
    _ensure_dir()
    url = ODDS_URL.format(season=season, code=code)
    try:
        df = pd.read_csv(url, encoding="latin-1", on_bad_lines="skip")
    except Exception as e:
        raise RuntimeError(f"Could not download {url}: {e}")
    # Keep the columns that matter: results + main market odds (Bet365, avg)
    keep = [c for c in ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
                        "B365H", "B365D", "B365A", "AvgH", "AvgD", "AvgA"]
            if c in df.columns]
    df = df[keep]
    out = os.path.join(LIVE_DIR, f"odds_{code}_{season}.parquet")
    df.to_parquet(out, index=False)
    print(f"{code} {season}: {len(df)} matches with odds -> {out}")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    ap_sync = sub.add_parser("sync"); ap_sync.add_argument("--days", type=int, default=10)
    ap_m = sub.add_parser("matches"); ap_m.add_argument("code"); ap_m.add_argument("--days", type=int, default=10)
    ap_s = sub.add_parser("standings"); ap_s.add_argument("code")
    ap_o = sub.add_parser("odds"); ap_o.add_argument("code"); ap_o.add_argument("season")
    args = ap.parse_args()

    if args.cmd == "sync":
        sync(days=args.days)
    elif args.cmd == "matches":
        matches(args.code, days=args.days)
    elif args.cmd == "standings":
        standings(args.code)
    elif args.cmd == "odds":
        odds(args.code, args.season)
    else:
        print(__doc__)
