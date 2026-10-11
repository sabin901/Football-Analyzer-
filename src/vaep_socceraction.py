"""
Production VAEP via socceraction — the reference implementation.

This replaces the experimental src/vaep.py with the real thing: the
`socceraction` library's validated VAEP pipeline (Decroos et al.). It credits
every action by how much it changes the team's chance of scoring minus
conceding, so progressive passing and carrying are valued, not just shots.

WHY A SEPARATE ENVIRONMENT: socceraction pins old pandas/pandera that conflict
with this app's stack, so run it in its own venv — then the main app reads the
resulting parquet with no conflict.

    # one-time setup (Windows PowerShell)
    python -m venv .venv-vaep
    .venv-vaep\\Scripts\\activate
    pip install -r requirements-vaep.txt

    # generate VAEP for a league-season (writes data/vaep_<comp>_<season>.parquet)
    python src/vaep_socceraction.py "La Liga" "2015/2016"
    python src/vaep_socceraction.py "Premier League" "2015/2016"

Once the parquet exists, the app's Players tab automatically shows a
"VAEP leaderboard (socceraction)" card for that league-season — no code change.

Output columns (what the app expects):
    player, team, vaep_total, vaep_p90, minutes
plus models/vaep_<key>.json with model AUCs + the top-20 leaderboard.
"""

import os
import sys
import json
import argparse

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA_DIR = os.path.join(ROOT, "data")
MODELS_DIR = os.path.join(ROOT, "models")


def run(competition, season, min_minutes=450):
    # Imported here so the file can be read/linted without socceraction installed.
    import socceraction.spadl as spadl
    import socceraction.vaep.features as fs
    import socceraction.vaep.labels as lab
    import socceraction.vaep.formula as vaepformula
    from socceraction.data.statsbomb import StatsBombLoader
    from sklearn.metrics import roc_auc_score
    try:
        from xgboost import XGBClassifier
        def make_clf():
            return XGBClassifier(n_estimators=250, max_depth=4, learning_rate=0.05,
                                 use_label_encoder=False, eval_metric="logloss", n_jobs=4)
    except Exception:
        from sklearn.ensemble import HistGradientBoostingClassifier
        def make_clf():
            return HistGradientBoostingClassifier(max_iter=250, max_depth=4, learning_rate=0.05)

    SBL = StatsBombLoader(getter="remote", creds={"user": "", "passwd": ""})
    comps = SBL.competitions()
    row = comps[(comps.competition_name == competition) & (comps.season_name == season)]
    if row.empty:
        raise SystemExit(f"Not found in StatsBomb open data: {competition} {season}")
    comp_id = int(row.iloc[0].competition_id); season_id = int(row.iloc[0].season_id)
    games = SBL.games(comp_id, season_id)
    print(f"{competition} {season}: {len(games)} games")

    # feature + label functions (the standard socceraction set)
    xfns = [fs.actiontype_onehot, fs.bodypart_onehot, fs.result_onehot,
            fs.goalscore, fs.startlocation, fs.endlocation, fs.movement,
            fs.space_delta, fs.startpolar, fs.endpolar, fs.team, fs.time_delta]
    yfns = [lab.scores, lab.concedes]

    all_X, all_Ys, all_Yc = [], [], []
    actions_by_game, minutes = {}, {}

    for g in games.itertuples():
        try:
            events = SBL.events(g.game_id)
            actions = spadl.statsbomb.convert_to_actions(events, g.home_team_id)
            actions = spadl.add_names(actions)
        except Exception as e:
            print(f"  skip game {g.game_id}: {e}"); continue
        gs = fs.gamestates(actions, 3)
        gs = fs.play_left_to_right(gs, g.home_team_id)
        X = pd.concat([fn(gs) for fn in xfns], axis=1)
        Ys = lab.scores(actions); Yc = lab.concedes(actions)
        all_X.append(X); all_Ys.append(Ys); all_Yc.append(Yc)
        actions_by_game[g.game_id] = actions
        # minutes
        try:
            pl = SBL.players(g.game_id)
            for p in pl.itertuples():
                minutes[p.player_id] = minutes.get(p.player_id, 0) + int(getattr(p, "minutes_played", 0) or 0)
        except Exception:
            pass

    X = pd.concat(all_X).reset_index(drop=True)
    Ys = pd.concat(all_Ys).reset_index(drop=True).values.ravel()
    Yc = pd.concat(all_Yc).reset_index(drop=True).values.ravel()

    # train with a held-out AUC
    n = len(X); cut = int(n * 0.8)
    clf_s = make_clf().fit(X.iloc[:cut], Ys[:cut])
    clf_c = make_clf().fit(X.iloc[:cut], Yc[:cut])
    auc_s = roc_auc_score(Ys[cut:], clf_s.predict_proba(X.iloc[cut:])[:, 1])
    auc_c = roc_auc_score(Yc[cut:], clf_c.predict_proba(X.iloc[cut:])[:, 1])
    print(f"P(score) AUC {auc_s:.3f} · P(concede) AUC {auc_c:.3f}")

    # value every action, aggregate per player
    vaep_tot, team_of, name_of = {}, {}, {}
    off = 0
    for gid, actions in actions_by_game.items():
        m = len(actions)
        gs = fs.gamestates(actions, 3)
        gs = fs.play_left_to_right(gs, games[games.game_id == gid].iloc[0].home_team_id)
        Xg = pd.concat([fn(gs) for fn in xfns], axis=1)
        ps = clf_s.predict_proba(Xg)[:, 1]
        pc = clf_c.predict_proba(Xg)[:, 1]
        vals = vaepformula.value(actions, pd.Series(ps), pd.Series(pc))
        v = vals["vaep_value"].values
        for i, a in actions.iterrows():
            pid = a.get("player_id")
            if pd.isna(pid):
                continue
            vaep_tot[pid] = vaep_tot.get(pid, 0.0) + float(v[i])
            name_of[pid] = a.get("player_name", pid)
            team_of[pid] = a.get("team_name", "")

    rows = []
    for pid, v in vaep_tot.items():
        mn = minutes.get(pid, 0)
        if mn < min_minutes:
            continue
        rows.append({"player": name_of.get(pid, str(pid)), "team": team_of.get(pid, ""),
                     "vaep_total": round(v, 1), "vaep_p90": round(v / mn * 90, 3),
                     "minutes": int(mn)})
    df = pd.DataFrame(rows).sort_values("vaep_p90", ascending=False).reset_index(drop=True)

    os.makedirs(DATA_DIR, exist_ok=True); os.makedirs(MODELS_DIR, exist_ok=True)
    key = f"{competition}_{season}".replace(" ", "_").replace("/", "-")
    df.to_parquet(os.path.join(DATA_DIR, f"vaep_{key}.parquet"), index=False)
    meta = {"competition": competition, "season": season, "key": key,
            "games": int(len(games)), "auc_score": round(float(auc_s), 3),
            "auc_concede": round(float(auc_c), 3), "library": "socceraction",
            "top": df.head(20).to_dict("records")}
    with open(os.path.join(MODELS_DIR, f"vaep_{key}.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print("\nTop players by VAEP per 90:")
    for _, r in df.head(12).iterrows():
        print(f"  {r['player']:<28} {r['team']:<18} {r['vaep_p90']:+.2f}")
    print(f"\nSaved data/vaep_{key}.parquet — the app will now show it.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("competition"); ap.add_argument("season")
    ap.add_argument("--min-minutes", type=int, default=450)
    args = ap.parse_args()
    run(args.competition, args.season, args.min_minutes)
