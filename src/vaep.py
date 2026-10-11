"""
VAEP — Valuing Actions by Estimating Probabilities.  [EXPERIMENTAL]

NOTE ON STATUS: this is a from-scratch, simplified VAEP and it is NOT yet good
enough to use. On La Liga 2015/16 it ranks poachers above elite progressors
(Modrić/Kroos land near the bottom), because with such sparse goal labels the
P(score) model collapses to a near-step-function at the goalmouth — so it credits
the shot, not the buildup VAEP is meant to reward (and the AUC looks implausibly
high as a result). A production VAEP needs the SPADL representation, richer
features and far more data; use the reference library `socceraction` for that.
Kept here as a documented, honest attempt — deliberately NOT surfaced in the app.

The state-of-the-art action-valuation technique (Decroos et al.). Every action
is worth how much it changes the team's chance of scoring minus its chance of
conceding in the near future:

    VAEP(action) = ΔP(score soon) − ΔP(concede soon)

So a progressive pass into the box is rewarded, a sloppy one that invites a
counter is penalised — not just shots. We:
  1. turn events into an ordered action stream (StatsBomb orients every action
     toward the attacking goal at x=120, so distance-to-goal is direct),
  2. label each action: does the acting team score / concede within the next
     K=10 actions,
  3. train two gradient-boosted classifiers (P_score, P_concede), reporting AUC,
  4. value each action and sum per player → a VAEP-per-90 leaderboard.

Usage:
    python src/vaep.py "La Liga" "2015/2016" --matches 180
    python src/vaep.py --stats
"""

import os
import sys
import json
import glob
import argparse
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statsbombpy import sb
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

import players as P

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA_DIR = os.path.join(ROOT, "data")
MODELS_DIR = os.path.join(ROOT, "models")
GOAL = (120.0, 40.0)
K = 10  # look-ahead window (actions)

ACTION_TYPES = ["Pass", "Carry", "Shot", "Dribble", "Clearance",
                "Interception", "Ball Recovery", "Foul Won", "Shot_Other"]
TYPE_IDX = {t: i for i, t in enumerate(ACTION_TYPES)}


def _dist(x, y):
    return ((GOAL[0] - x) ** 2 + (GOAL[1] - y) ** 2) ** 0.5


def match_actions(events):
    """Ordered list of actions with acting team, player, start/end, success, goal."""
    acts = []
    for _, e in events.iterrows():
        t = e["type"]
        loc = e.get("location")
        if not isinstance(loc, list) or len(loc) < 2:
            continue
        if t == "Pass":
            end = e.get("pass_end_location"); succ = pd.isna(e.get("pass_outcome"))
            atype = "Pass"
        elif t == "Carry":
            end = e.get("carry_end_location"); succ = True; atype = "Carry"
        elif t == "Shot":
            end = [GOAL[0], GOAL[1]]; succ = e.get("shot_outcome") == "Goal"; atype = "Shot"
        elif t in ("Clearance", "Interception", "Ball Recovery", "Foul Won"):
            end = loc; succ = True; atype = t
        elif t == "Dribble":
            end = loc; succ = e.get("dribble_outcome") == "Complete"; atype = "Dribble"
        else:
            continue
        if not isinstance(end, list) or len(end) < 2:
            end = loc
        acts.append({
            "type": atype, "team": e.get("team"), "player": e.get("player"),
            "x": loc[0], "y": loc[1], "ex": end[0], "ey": end[1],
            "success": 1 if succ else 0, "minute": int(e.get("minute", 0)),
            "is_goal": 1 if (t == "Shot" and e.get("shot_outcome") == "Goal") else 0,
        })
    return acts


def _features(a):
    return [a["ex"], a["ey"], _dist(a["ex"], a["ey"]), a["x"],
            a["ex"] - a["x"], a["ey"] - a["y"], a["success"], a["minute"],
            TYPE_IDX.get(a["type"], len(ACTION_TYPES))]


def _label(acts, i):
    """Does the acting team score / concede within the next K actions *after*
    this one? Excluding the current action avoids the trivial shot→its-own-goal
    leak, so the model must learn which states precede goals."""
    team = acts[i]["team"]; scores = concedes = 0
    for j in range(i + 1, min(i + 1 + K, len(acts))):
        if acts[j]["is_goal"]:
            if acts[j]["team"] == team:
                scores = 1
            else:
                concedes = 1
    return scores, concedes


def build(competition, season, max_matches=180):
    matches = sb.matches(competition_id=P._cid(competition, season),
                         season_id=P._sid(competition, season))
    mids = matches["match_id"].tolist()[:max_matches]

    all_feats, y_s, y_c = [], [], []
    match_streams = []           # (actions, features) per match, to value later
    minutes = {}

    for k, mid in enumerate(mids, 1):
        try:
            ev = sb.events(match_id=mid)
        except Exception:
            continue
        mm, _ = P._match_minutes_and_pos(ev)
        for nm, mn in mm.items():
            minutes[nm] = minutes.get(nm, 0) + mn
        acts = match_actions(ev)
        if len(acts) < 20:
            continue
        feats = [_features(a) for a in acts]
        for i in range(len(acts)):
            s, c = _label(acts, i)
            all_feats.append(feats[i]); y_s.append(s); y_c.append(c)
        match_streams.append((acts, feats))

    X = np.array(all_feats); ys = np.array(y_s); yc = np.array(y_c)
    print(f"{len(mids)} matches · {len(X):,} actions · "
          f"{ys.sum():,} score-labels · {yc.sum():,} concede-labels")

    # train two models with a held-out AUC
    Xtr, Xte, ys_tr, ys_te, yc_tr, yc_te = train_test_split(
        X, ys, yc, test_size=0.25, random_state=42)
    m_s = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06,
                                         max_depth=4, random_state=42).fit(Xtr, ys_tr)
    m_c = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06,
                                         max_depth=4, random_state=42).fit(Xtr, yc_tr)
    auc_s = roc_auc_score(ys_te, m_s.predict_proba(Xte)[:, 1])
    auc_c = roc_auc_score(yc_te, m_c.predict_proba(Xte)[:, 1])
    print(f"P(score) AUC {auc_s:.3f} · P(concede) AUC {auc_c:.3f}")

    # value every action and sum per player
    vaep = {}
    for acts, feats in match_streams:
        F = np.array(feats)
        ps = m_s.predict_proba(F)[:, 1]
        pc = m_c.predict_proba(F)[:, 1]
        prev_s = prev_c = 0.0; prev_team = None
        for i, a in enumerate(acts):
            if prev_team is None or a["team"] == prev_team:
                base_s, base_c = prev_s, prev_c
            else:                 # possession switched: flip perspective
                base_s, base_c = prev_c, prev_s
            val = (ps[i] - base_s) - (pc[i] - base_c)
            if a["player"]:
                vaep[a["player"]] = vaep.get(a["player"], 0.0) + val
            prev_s, prev_c, prev_team = ps[i], pc[i], a["team"]

    rows = []
    for name, v in vaep.items():
        mn = minutes.get(name, 0)
        if mn < 450:
            continue
        rows.append({"player": name, "vaep_total": round(v, 1),
                     "vaep_p90": round(v / mn * 90, 3), "minutes": int(mn)})
    df = pd.DataFrame(rows).sort_values("vaep_p90", ascending=False)

    os.makedirs(DATA_DIR, exist_ok=True); os.makedirs(MODELS_DIR, exist_ok=True)
    safe = f"{competition}_{season}".replace(" ", "_").replace("/", "-")
    df.to_parquet(os.path.join(DATA_DIR, f"vaep_{safe}.parquet"), index=False)
    meta = {"competition": competition, "season": season, "key": safe,
            "matches": len(mids), "actions": int(len(X)),
            "auc_score": round(float(auc_s), 3), "auc_concede": round(float(auc_c), 3),
            "top": [{"player": r["player"], "vaep_p90": r["vaep_p90"],
                     "minutes": r["minutes"]} for _, r in df.head(20).iterrows()]}
    with open(os.path.join(MODELS_DIR, f"vaep_{safe}.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print("\nTop players by VAEP per 90:")
    for _, r in df.head(10).iterrows():
        print(f"  {r['player']:<30} {r['vaep_p90']:+.2f}")
    return df, meta


def cached():
    out = []
    for f in sorted(glob.glob(os.path.join(MODELS_DIR, "vaep_*.json"))):
        out.append(json.load(open(f)))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("competition", nargs="?"); ap.add_argument("season", nargs="?")
    ap.add_argument("--matches", type=int, default=180)
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    if args.stats or not args.competition:
        for c in cached():
            print(c["competition"], c["season"], "AUC_score", c["auc_score"])
    else:
        build(args.competition, args.season, args.matches)
