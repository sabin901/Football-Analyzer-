"""
Player analysis — percentile radars and player similarity.

The scouting layer top projects are built around: per-90 player metrics from
event data, percentile-ranked against positional peers (the StatsBomb/FBref
radar), and "find players like X" similarity. It ties the xG and xT models
together at the player level.

Metrics per 90 (minutes derived from Starting XI + substitution events):
  npxG, shots, shots on target, key passes (shot assists), goals,
  xT added (progression), progressive passes, progressive carries,
  pass completion %, ball recoveries, pressures, tackles+interceptions.

Builds a cache per competition-season:  data/players_<comp>_<season>.parquet

Usage:
    python src/players.py "La Liga" "2015/2016" --matches 380
    python src/players.py --stats
"""

import os
import sys
import glob
import argparse
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statsbombpy import sb
from xg_model import load_model, predict_xg

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA_DIR = os.path.join(ROOT, "data")

GOAL = (120.0, 40.0)

METRICS = ["np_goals", "npxg", "shots", "sot", "key_passes", "xt",
           "prog_passes", "prog_carries", "pass_pct", "recoveries", "pressures", "tkl_int"]
METRIC_LABELS = {
    "np_goals": "Non-pen goals", "npxg": "npxG", "shots": "Shots", "sot": "Shots on target",
    "key_passes": "Key passes", "xt": "xT added", "prog_passes": "Prog. passes",
    "prog_carries": "Prog. carries", "pass_pct": "Pass %", "recoveries": "Recoveries",
    "pressures": "Pressures", "tkl_int": "Tackles+int",
}
# metrics shown on the radar (general outfield profile)
RADAR = ["npxg", "shots", "key_passes", "xt", "prog_passes", "prog_carries",
         "pass_pct", "recoveries", "pressures"]


def _dist_to_goal(loc):
    return ((GOAL[0] - loc[0]) ** 2 + (GOAL[1] - loc[1]) ** 2) ** 0.5


def _progressive(start, end):
    """A pass/carry that moves the ball >=10 units closer to goal and ends in
    the attacking 60% of the pitch — a simple, defensible 'progressive' rule."""
    if not (isinstance(start, list) and isinstance(end, list)):
        return False
    return (_dist_to_goal(start) - _dist_to_goal(end) >= 10) and end[0] >= 72


def _position_group(pos):
    if not pos:
        return "MID"
    p = pos.lower()
    if "goalkeeper" in p:
        return "GK"
    if "back" in p or "defend" in p or p.startswith("right") and "wing" not in p:
        return "DEF"
    if "forward" in p or "striker" in p or "wing" in p:
        return "FWD"
    return "MID"


def _match_minutes_and_pos(events):
    """Minutes played + primary position per player in one match."""
    end_min = int(events["minute"].max()) if len(events) else 90
    on_min, off_min, pos = {}, {}, {}
    xi = events[events["type"] == "Starting XI"]
    for _, r in xi.iterrows():
        tac = r.get("tactics")
        if isinstance(tac, dict):
            for p in tac.get("lineup", []):
                name = p.get("player", {}).get("name")
                if name:
                    on_min[name] = 0
                    pos[name] = p.get("position", {}).get("name")
    subs = events[events["type"] == "Substitution"]
    for _, r in subs.iterrows():
        off = r.get("player"); m = int(r.get("minute", end_min))
        if off:
            off_min[off] = m
        rep = r.get("substitution_replacement")
        if rep:
            on_min[rep] = m
    minutes = {}
    for name, on in on_min.items():
        minutes[name] = max(0, off_min.get(name, end_min) - on)
    return minutes, pos


def build(competition, season, max_matches=380):
    model, feats = load_model()
    matches = sb.matches(competition_id=_cid(competition, season),
                         season_id=_sid(competition, season))
    mids = matches["match_id"].tolist()[:max_matches]

    agg = {}  # player -> metric totals
    mins = {}
    team = {}
    posg = {}

    def _p(name):
        if name not in agg:
            agg[name] = {m: 0.0 for m in METRICS}
            agg[name]["passes"] = 0.0; agg[name]["passes_cmp"] = 0.0
        return agg[name]

    for k, mid in enumerate(mids, 1):
        try:
            ev = sb.events(match_id=mid)
        except Exception:
            continue
        mm, pp = _match_minutes_and_pos(ev)
        for name, m in mm.items():
            mins[name] = mins.get(name, 0) + m
        for name, p in pp.items():
            posg.setdefault(name, _position_group(p))

        for _, e in ev.iterrows():
            name = e.get("player"); t = e["type"]
            if not name:
                continue
            team[name] = e.get("team")
            loc = e.get("location")
            if t == "Shot":
                stype = e.get("shot_type")
                if stype == "Penalty":
                    continue
                d = _p(name); d["shots"] += 1
                if e.get("shot_outcome") in ("Goal", "Saved"):
                    d["sot"] += 1
                if e.get("shot_outcome") == "Goal":
                    d["np_goals"] += 1
                if isinstance(loc, list):
                    pp2 = e.get("play_pattern")
                    d["npxg"] += predict_xg(model, feats, loc[0], loc[1],
                        header=1 if e.get("shot_body_part") == "Head" else 0,
                        open_play=1 if stype == "Open Play" else 0,
                        from_corner=1 if pp2 == "From Corner" else 0,
                        from_free_kick=1 if pp2 == "From Free Kick" else 0,
                        from_counter=1 if pp2 == "From Counter" else 0,
                        under_pressure=1 if e.get("under_pressure") is True else 0)
            elif t == "Pass":
                d = _p(name); d["passes"] += 1
                completed = pd.isna(e.get("pass_outcome"))
                if completed:
                    d["passes_cmp"] += 1
                if e.get("pass_shot_assist") is True or e.get("pass_goal_assist") is True:
                    d["key_passes"] += 1
                end = e.get("pass_end_location")
                if completed and _progressive(loc, end):
                    d["prog_passes"] += 1
                    if isinstance(loc, list) and isinstance(end, list):
                        d["xt"] += max(0, _prog_xt(loc, end))
            elif t == "Carry":
                d = _p(name); end = e.get("carry_end_location")
                if _progressive(loc, end):
                    d["prog_carries"] += 1
                    if isinstance(loc, list) and isinstance(end, list):
                        d["xt"] += max(0, _prog_xt(loc, end))
            elif t == "Ball Recovery":
                _p(name)["recoveries"] += 1
            elif t == "Pressure":
                _p(name)["pressures"] += 1
            elif t in ("Duel", "Interception", "Tackle"):
                _p(name)["tkl_int"] += 1

    # assemble per-90 table
    rows = []
    for name, d in agg.items():
        m = mins.get(name, 0)
        if m < 450:          # ~5 full matches minimum
            continue
        per90 = {k: round(d[k] / m * 90, 3) for k in METRICS}
        per90["pass_pct"] = round(100 * d["passes_cmp"] / d["passes"], 1) if d["passes"] else 0.0
        per90["player"] = name; per90["team"] = team.get(name, "")
        per90["minutes"] = int(m); per90["pos"] = posg.get(name, "MID")
        rows.append(per90)
    df = pd.DataFrame(rows)
    os.makedirs(DATA_DIR, exist_ok=True)
    safe = f"{competition}_{season}".replace(" ", "_").replace("/", "-")
    out = os.path.join(DATA_DIR, f"players_{safe}.parquet")
    df.to_parquet(out, index=False)
    print(f"Saved {len(df)} players ({len(mids)} matches) -> {out}")
    print("\nTop npxG/90:")
    for _, r in df.sort_values("npxg", ascending=False).head(6).iterrows():
        print(f"  {r['player']:<28} {r['team']:<16} npxG/90 {r['npxg']:.2f}")
    return df


def _prog_xt(start, end):
    """Tiny xT-style value for a progression: normalised distance gained to goal."""
    return (_dist_to_goal(start) - _dist_to_goal(end)) / 120.0 * 0.05


def _cid(name, season):
    c = sb.competitions()
    return int(c[(c["competition_name"] == name) & (c["season_name"] == season)].iloc[0]["competition_id"])


def _sid(name, season):
    c = sb.competitions()
    return int(c[(c["competition_name"] == name) & (c["season_name"] == season)].iloc[0]["season_id"])


# ---- analysis on a cached table ----
def _load(path):
    return pd.read_parquet(path)


def percentile_profile(df, player):
    """Percentile of each radar metric vs peers in the same position group."""
    row = df[df["player"] == player]
    if row.empty:
        return None
    row = row.iloc[0]
    peers = df[df["pos"] == row["pos"]]
    prof = []
    for m in RADAR:
        pct = round(100 * (peers[m] < row[m]).mean(), 0)
        prof.append({"metric": METRIC_LABELS[m], "value": float(row[m]), "pct": int(pct)})
    return {"player": player, "team": row["team"], "pos": row["pos"],
            "minutes": int(row["minutes"]), "radar": prof}


def similar_players(df, player, n=8):
    """Nearest neighbours in z-scored metric space."""
    feats = [m for m in METRICS if m != "np_goals"]
    X = df[feats].astype(float).values
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    names = df["player"].tolist()
    if player not in names:
        return []
    i = names.index(player)
    d = np.linalg.norm(Z - Z[i], axis=1)
    order = np.argsort(d)
    out = []
    for j in order:
        if j == i:
            continue
        out.append({"player": names[j], "team": df.iloc[j]["team"],
                    "pos": df.iloc[j]["pos"], "distance": round(float(d[j]), 2)})
        if len(out) >= n:
            break
    return out


def cached():
    out = []
    for f in sorted(glob.glob(os.path.join(DATA_DIR, "players_*.parquet"))):
        key = os.path.basename(f).replace("players_", "").replace(".parquet", "")
        out.append({"key": key, "title": key.replace("_", " ").replace("-", "/"), "path": f})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("competition", nargs="?")
    ap.add_argument("season", nargs="?")
    ap.add_argument("--matches", type=int, default=380)
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    if args.stats or not args.competition:
        for c in cached():
            print(c["title"], "->", c["path"])
    else:
        build(args.competition, args.season, args.matches)
