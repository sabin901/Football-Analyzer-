"""
Importers for live free data sources — RUN THESE ON YOUR OWN MACHINE.

StatsBomb open data (see src/ingest.py) is the only bulk source reachable from a
locked-down/sandboxed environment, because it's served from GitHub. The sources
below are live websites — fully accessible from a normal machine with open
internet, but blocked by restrictive firewalls.

They use the excellent `soccerdata` package, which wraps several public sources
behind one tidy API and caches locally:
    pip install soccerdata

Coverage you unlock:
  - Understat  — shot-level data + xG for the top-5 European leagues, many seasons
  - FBref      — huge stats coverage (Opta-derived) across dozens of competitions
  - MatchHistory (football-data.co.uk) — results + betting odds, decades of history

Docs: https://soccerdata.readthedocs.io

Usage (examples):
    python src/sources.py understat ENG 2023
    python src/sources.py fbref ENG 2023
    python src/sources.py matchhistory ENG 2023
"""

import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def _save(df, name):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{name}.parquet")
    try:
        df.to_parquet(path)
    except Exception:
        path = os.path.join(DATA_DIR, f"{name}.csv")
        df.to_csv(path)
    print(f"Saved {len(df):,} rows -> {os.path.abspath(path)}")


def understat(league="ENG-Premier League", season="2023"):
    """Shot-level data with xG from Understat (top-5 leagues)."""
    import soccerdata as sd
    us = sd.Understat(leagues=league, seasons=season)
    shots = us.read_shot_events()
    _save(shots.reset_index(), f"understat_shots_{league}_{season}".replace(" ", "_"))
    return shots


def fbref(league="ENG-Premier League", season="2023", stat="standard"):
    """Team/player season stats from FBref (Opta-derived)."""
    import soccerdata as sd
    fb = sd.FBref(leagues=league, seasons=season)
    team = fb.read_team_season_stats(stat_type=stat)
    _save(team.reset_index(), f"fbref_team_{stat}_{league}_{season}".replace(" ", "_"))
    return team


def matchhistory(league="ENG-Premier League", season="2023"):
    """Results + betting odds from football-data.co.uk (deep history)."""
    import soccerdata as sd
    mh = sd.MatchHistory(leagues=league, seasons=season)
    games = mh.read_games()
    _save(games.reset_index(), f"matchhistory_{league}_{season}".replace(" ", "_"))
    return games


# Convenience league codes soccerdata understands:
#   ENG-Premier League, ESP-La Liga, ITA-Serie A, GER-Bundesliga, FRA-Ligue 1
LEAGUE_ALIASES = {
    "ENG": "ENG-Premier League", "ESP": "ESP-La Liga", "ITA": "ITA-Serie A",
    "GER": "GER-Bundesliga", "FRA": "FRA-Ligue 1",
}

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(0)
    source, league, season = sys.argv[1], sys.argv[2], sys.argv[3]
    league = LEAGUE_ALIASES.get(league, league)
    try:
        {"understat": understat, "fbref": fbref,
         "matchhistory": matchhistory}[source](league, season)
    except KeyError:
        print(f"Unknown source '{source}'. Use: understat | fbref | matchhistory")
    except ImportError:
        print("This importer needs `soccerdata`. Install it with:\n    pip install soccerdata")
