"""
Bulk data ingestion from StatsBomb open data.

Pulls every shot from every available match across all free competitions into a
single local dataset (data/shots.parquet) plus a match catalogue
(data/matches.parquet). Resumable: already-ingested matches are skipped, so you
can run it in batches and stop/restart any time.

This is the "import as much as you can" layer. StatsBomb open data is the only
bulk source reachable from a locked-down environment (it's served from GitHub);
for live sources like Understat and FBref, see src/sources.py (run those on a
machine with open internet).

Usage:
    python src/ingest.py                 # ingest everything (resumable)
    python src/ingest.py --limit 300     # ingest up to 300 new matches then stop
    python src/ingest.py --comp 11 90    # ingest only one competition+season
    python src/ingest.py --stats         # show what's been ingested so far
"""

import os
import sys
import time
import argparse
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statsbombpy import sb
from xg_model import _shot_row  # reuse the exact feature extraction

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
SHOTS_PATH = os.path.join(DATA_DIR, "shots.parquet")
MATCHES_PATH = os.path.join(DATA_DIR, "matches.parquet")
MANIFEST_PATH = os.path.join(DATA_DIR, "ingested_match_ids.txt")


def _load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return set(int(x) for x in f.read().split() if x.strip())
    return set()


def _append_manifest(match_id):
    with open(MANIFEST_PATH, "a") as f:
        f.write(f"{match_id}\n")


def _append_parquet(path, df):
    """Append rows to a parquet file (read-concat-write; fine at this scale)."""
    if df.empty:
        return
    if os.path.exists(path):
        existing = pd.read_parquet(path)
        df = pd.concat([existing, df], ignore_index=True)
    df.to_parquet(path, index=False)


def all_competitions():
    comps = sb.competitions()
    return [(int(c["competition_id"]), int(c["season_id"]),
             c["competition_name"], c["season_name"])
            for _, c in comps.iterrows()]


def ingest(target_comps=None, limit=None):
    os.makedirs(DATA_DIR, exist_ok=True)
    done = _load_manifest()
    print(f"Already ingested: {len(done):,} matches")

    comps = all_competitions()
    if target_comps:
        comps = [c for c in comps if (c[0], c[1]) in target_comps]

    # Build the full match list (also saved as the catalogue)
    match_rows, work = [], []
    for cid, sid, cname, sname in comps:
        try:
            m = sb.matches(competition_id=cid, season_id=sid)
        except Exception:
            continue
        for _, r in m.iterrows():
            mid = int(r["match_id"])
            match_rows.append({
                "match_id": mid, "competition_id": cid, "season_id": sid,
                "competition": cname, "season": sname,
                "home_team": r["home_team"], "away_team": r["away_team"],
                "home_score": int(r["home_score"]), "away_score": int(r["away_score"]),
                "date": str(r.get("match_date", "")),
            })
            if mid not in done:
                work.append((mid, cid, sid, cname))

    # Refresh the catalogue every run (cheap, keeps it complete)
    pd.DataFrame(match_rows).drop_duplicates("match_id").to_parquet(MATCHES_PATH, index=False)
    print(f"Catalogue: {len(match_rows):,} matches across {len(comps)} competition-seasons")
    print(f"Remaining to ingest: {len(work):,}")

    if limit:
        work = work[:limit]
        print(f"This run: ingesting up to {len(work):,} matches")

    buffer, t0, n_shots = [], time.time(), 0
    for i, (mid, cid, sid, cname) in enumerate(work, 1):
        try:
            events = sb.events(match_id=mid)
        except Exception as e:
            print(f"  [{i}/{len(work)}] match {mid} failed: {e}")
            continue
        shots = events[events["type"] == "Shot"]
        for _, s in shots.iterrows():
            r = _shot_row(s, mid)
            if r:
                r["competition_id"] = cid
                r["season_id"] = sid
                r["team"] = s.get("team")
                r["player"] = s.get("player")
                buffer.append(r)
                n_shots += 1
        done.add(mid)
        _append_manifest(mid)

        # Flush every 50 matches so progress is durable
        if i % 50 == 0 or i == len(work):
            _append_parquet(SHOTS_PATH, pd.DataFrame(buffer))
            buffer = []
            rate = i / (time.time() - t0)
            eta = (len(work) - i) / rate / 60 if rate else 0
            print(f"  [{i}/{len(work)}] matches done · {n_shots:,} shots · "
                  f"{rate:.1f} matches/s · ~{eta:.1f} min left")

    print(f"\nDone this run. Total shots in dataset: "
          f"{len(pd.read_parquet(SHOTS_PATH)):,}" if os.path.exists(SHOTS_PATH) else "no shots yet")


def stats():
    if not os.path.exists(SHOTS_PATH):
        print("No data ingested yet. Run: python src/ingest.py")
        return
    shots = pd.read_parquet(SHOTS_PATH)
    print(f"Shots ingested:   {len(shots):,}")
    print(f"Goals:            {int(shots['is_goal'].sum()):,} "
          f"({shots['is_goal'].mean()*100:.1f}% conversion)")
    print(f"Matches covered:  {shots['match_id'].nunique():,}")
    if os.path.exists(MATCHES_PATH):
        m = pd.read_parquet(MATCHES_PATH)
        print(f"Matches in catalogue: {len(m):,}")
        print(f"Competitions:     {m['competition'].nunique()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--comp", nargs=2, type=int, metavar=("COMP_ID", "SEASON_ID"))
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    if args.stats:
        stats()
    elif args.comp:
        ingest(target_comps={(args.comp[0], args.comp[1])})
    else:
        ingest(limit=args.limit)
