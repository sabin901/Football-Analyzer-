"""
Bulk results importer — many leagues, many seasons (for the predictor).

StatsBomb open data is deep but a fixed set. To stress-test the match predictor
across *breadth* — top-5 leagues over ~15 seasons — this pulls clean results
from the GitHub-hosted `datasets/football-datasets` archive (football-data.co.uk
data, reachable anywhere GitHub is). ~75 league-seasons, ~27,000 matches.

Output `data/results_history.parquet` is merged automatically into the
predictor's catalogue, so every season below appears in the Predictor.

Usage:
    python src/import_results.py              # pull everything
    python src/import_results.py --stats      # summarise what's imported
"""

import os
import sys
import argparse
import warnings
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from io import StringIO

import pandas as pd

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA_DIR, "results_history.parquet")

BASE = "https://raw.githubusercontent.com/datasets/football-datasets/main/datasets/{lg}/season-{sc}.csv"

LEAGUES = {
    "premier-league": "Premier League",
    "la-liga": "La Liga",
    "serie-a": "Serie A",
    "bundesliga": "Bundesliga",
    "ligue-1": "Ligue 1",
}

# season codes: 0203 … latest available (start/end two-digit years).
# Range runs ahead of "now" so a re-run auto-picks up each new season the
# source publishes; missing ones 404 and are skipped.
def _season_codes():
    codes = []
    for start in range(2, 28):            # 2002/03 … 2027/28 (skips any not yet published)
        codes.append(f"{start:02d}{(start + 1) % 100:02d}")
    return codes


def _label(sc):
    a, b = int(sc[:2]), int(sc[2:])
    ya = 2000 + a if a < 90 else 1900 + a
    yb = 2000 + b if b < 90 else 1900 + b
    return f"{ya}/{yb}"


def _fetch_csv(url):
    try:
        with urlopen(url, timeout=25) as r:
            return pd.read_csv(StringIO(r.read().decode("utf-8", "ignore")))
    except (HTTPError, URLError):
        return None


def import_all():
    os.makedirs(DATA_DIR, exist_ok=True)
    rows = []
    for lg, name in LEAGUES.items():
        got = 0
        for sc in _season_codes():
            df = _fetch_csv(BASE.format(lg=lg, sc=sc))
            if df is None or "HomeTeam" not in df.columns:
                continue
            need = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"}
            if not need.issubset(df.columns):
                continue
            df = df.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
            # shots / shots-on-target when present (enables xG-based ratings)
            def _opt(r, col):
                try:
                    return int(r[col]) if col in df.columns and pd.notna(r[col]) else None
                except (ValueError, TypeError):
                    return None
            for _, r in df.iterrows():
                try:
                    hs, as_ = int(r["FTHG"]), int(r["FTAG"])
                except (ValueError, TypeError):
                    continue
                rows.append({
                    "competition": name, "season": _label(sc),
                    "home_team": str(r["HomeTeam"]).strip(),
                    "away_team": str(r["AwayTeam"]).strip(),
                    "home_score": hs, "away_score": as_,
                    "home_shots": _opt(r, "HS"), "away_shots": _opt(r, "AS"),
                    "home_sot": _opt(r, "HST"), "away_sot": _opt(r, "AST"),
                    "date": str(r["Date"]),
                    "source": "football-datasets",
                })
            got += 1
        print(f"  {name}: {got} seasons")
    out = pd.DataFrame(rows)
    # normalise dates (football-data.co.uk is dd/mm/yy or dd/mm/yyyy)
    out["date"] = pd.to_datetime(out["date"], dayfirst=True, errors="coerce").astype(str)
    out.to_parquet(OUT, index=False)
    print(f"\nSaved {len(out):,} matches across "
          f"{out.groupby(['competition','season']).ngroups} league-seasons -> {OUT}")
    return out


def stats():
    if not os.path.exists(OUT):
        print("Nothing imported yet. Run: python src/import_results.py")
        return
    df = pd.read_parquet(OUT)
    print(f"{len(df):,} matches · "
          f"{df.groupby(['competition','season']).ngroups} league-seasons")
    print(df.groupby("competition")["season"].nunique().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    if args.stats:
        stats()
    else:
        print("Importing top-5 league results from football-datasets...")
        import_all()
