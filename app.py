"""
Soccer Analytics — FastAPI backend.

Serves the analytics pipeline (xG model, match reports, scouting reports) to the
web frontend. Reports are generated on demand and cached on disk; repeat
requests return instantly.

Run:
    uvicorn app:app --reload --port 8000
Then open http://localhost:8000
"""

import os
import sys
import json
import warnings

warnings.filterwarnings("ignore")

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

from statsbombpy import sb
import report as match_report
import scouting as scout
import predict as predictor

OUTPUT_DIR = os.path.join(HERE, "output")
MODELS_DIR = os.path.join(HERE, "models")
FRONTEND_DIR = os.path.join(HERE, "frontend")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="Soccer Analytics", version="1.0")

# Serve generated images and the frontend
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.get("/api/competitions")
def competitions():
    """List available competitions+seasons from StatsBomb open data."""
    comps = sb.competitions()
    out = []
    for _, c in comps.iterrows():
        out.append({
            "competition_id": int(c["competition_id"]),
            "season_id": int(c["season_id"]),
            "competition_name": c["competition_name"],
            "season_name": c["season_name"],
            "country": c.get("country_name", ""),
            "label": f"{c['competition_name']} — {c['season_name']}",
        })
    out.sort(key=lambda r: (r["competition_name"], r["season_name"]))
    return out


@app.get("/api/matches")
def matches(competition_id: int, season_id: int):
    """List matches in a competition+season."""
    try:
        m = sb.matches(competition_id=competition_id, season_id=season_id)
    except Exception as e:
        raise HTTPException(404, f"No matches: {e}")
    out = []
    for _, r in m.iterrows():
        out.append({
            "match_id": int(r["match_id"]),
            "home_team": r["home_team"], "away_team": r["away_team"],
            "home_score": int(r["home_score"]), "away_score": int(r["away_score"]),
            "date": str(r.get("match_date", "")),
            "label": f"{r['home_team']} {int(r['home_score'])}-{int(r['away_score'])} {r['away_team']}",
        })
    out.sort(key=lambda r: r["date"])
    return out


@app.get("/api/teams")
def teams(competition_id: int, season_id: int):
    """Distinct teams in a competition+season (for the scouting picker)."""
    try:
        m = sb.matches(competition_id=competition_id, season_id=season_id)
    except Exception as e:
        raise HTTPException(404, f"No matches: {e}")
    names = sorted(set(m["home_team"]).union(set(m["away_team"])))
    return names


@app.get("/api/report/{match_id}")
def report(match_id: int):
    """Generate (or return cached) post-match report for a match."""
    cached = os.path.join(OUTPUT_DIR, f"report_{match_id}.json")
    png = os.path.join(OUTPUT_DIR, f"report_{match_id}.png")
    if os.path.exists(cached) and os.path.exists(png):
        with open(cached) as f:
            summary = json.load(f)
        summary["png"] = f"report_{match_id}.png"
        return summary
    try:
        summary = match_report.run(match_id)
    except Exception as e:
        raise HTTPException(500, f"Report failed: {e}")
    return summary


@app.get("/api/scout")
def scout_report(competition_id: int, season_id: int, team: str):
    """Generate (or return cached) season scouting report for a team."""
    safe = team.replace(" ", "_").replace("/", "-")
    png = f"scout_{competition_id}_{season_id}_{safe}.png"
    cached = os.path.join(OUTPUT_DIR, png.replace(".png", ".json"))
    if os.path.exists(cached) and os.path.exists(os.path.join(OUTPUT_DIR, png)):
        with open(cached) as f:
            summary = json.load(f)
        summary["png"] = png
        return summary
    try:
        summary = scout.run(competition_id, season_id, team)
    except Exception as e:
        raise HTTPException(500, f"Scouting failed: {e}")
    return summary


# Cache fitted prediction models per competition-season (fitting takes a few s)
_PRED_CACHE = {}


def _get_predictor(competition, season):
    key = (competition, season)
    if key not in _PRED_CACHE:
        # xG basis (chance quality) + 90-day recency weighting — the combination
        # the 115-season backtest found best.
        model, metrics = predictor.validate(competition, season,
                                            half_life_days=90, basis="xg")
        _PRED_CACHE[key] = (model, metrics)
    return _PRED_CACHE[key]


@app.get("/api/backtest")
def backtest_summary():
    """Aggregated backtest across all 115 league-seasons (goals vs xG basis)."""
    import os as _os
    p = _os.path.join(MODELS_DIR, "backtest.json")
    if not _os.path.exists(p):
        raise HTTPException(404, "No backtest yet. Run: python src/backtest.py")
    with open(p) as f:
        data = json.load(f)
    data["plot"] = "backtest.png"
    return data


# The five major European top leagues — the predictor's scope.
MAJOR_LEAGUES = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]


@app.get("/api/predict/seasons")
def predict_seasons():
    """Season options for the predictor — the five major top leagues only."""
    m = predictor.load_catalogue()
    m = m[m["competition"].isin(MAJOR_LEAGUES)]
    g = m.groupby(["competition", "season"]).size().reset_index(name="n")
    g = g[g["n"] >= 180].sort_values(["competition", "season"], ascending=[True, False])
    return [{"competition": r["competition"], "season": r["season"],
             "matches": int(r["n"]),
             "label": f"{r['competition']} — {r['season']}"} for _, r in g.iterrows()]


@app.get("/api/predict/overview")
def predict_overview(competition: str, season: str):
    """Validation metrics + fitted team strengths + the season's teams."""
    try:
        model, metrics = _get_predictor(competition, season)
    except Exception as e:
        raise HTTPException(500, f"Fit failed: {e}")
    ratings = [{"team": t, "attack": round(float(a), 3), "defence": round(float(d), 3)}
               for t, a, d in predictor.team_ratings(model)]
    return {"metrics": metrics, "ratings": ratings,
            "teams": model["teams"]}


_TABLE_CACHE = {}


@app.get("/api/table")
def league_table(competition: str, season: str):
    """League table: actual standings + the model's expected points (xPts),
    over/under-performance, and last-5 form — the analytics league view."""
    key = (competition, season)
    if key in _TABLE_CACHE:
        return _TABLE_CACHE[key]
    import pandas as pd
    cat = predictor.load_catalogue()
    df = cat[(cat["competition"] == competition) & (cat["season"] == season)].copy()
    if df.empty:
        raise HTTPException(404, "No matches for that competition/season.")
    df = df.sort_values("date").reset_index(drop=True)

    teams = sorted(set(df["home_team"]).union(df["away_team"]))
    rec = {t: {"team": t, "played": 0, "won": 0, "draw": 0, "lost": 0,
               "gf": 0, "ga": 0, "pts": 0, "xpts": 0.0, "form": []} for t in teams}

    # fitted model (cached) for expected points
    model = None
    try:
        model, _ = _get_predictor(competition, season)
    except Exception:
        model = None

    for _, r in df.iterrows():
        h, a = r["home_team"], r["away_team"]
        hs, as_ = int(r["home_score"]), int(r["away_score"])
        for t, gf, ga in ((h, hs, as_), (a, as_, hs)):
            rec[t]["played"] += 1
            rec[t]["gf"] += gf; rec[t]["ga"] += ga
            if gf > ga:
                rec[t]["pts"] += 3; rec[t]["won"] += 1; rec[t]["form"].append("W")
            elif gf == ga:
                rec[t]["pts"] += 1; rec[t]["draw"] += 1; rec[t]["form"].append("D")
            else:
                rec[t]["lost"] += 1; rec[t]["form"].append("L")
        if model is not None:
            pr = predictor.predict(model, h, a)
            if pr:
                rec[h]["xpts"] += 3 * pr["p_home"] + pr["p_draw"]
                rec[a]["xpts"] += 3 * pr["p_away"] + pr["p_draw"]

    table = []
    for t in teams:
        d = rec[t]
        d["gd"] = d["gf"] - d["ga"]
        d["xpts"] = round(d["xpts"], 1)
        d["xpts_diff"] = round(d["pts"] - d["xpts"], 1)   # + = overperforming
        d["form"] = d["form"][-5:]
        table.append(d)
    table.sort(key=lambda z: (-z["pts"], -z["gd"], -z["gf"]))
    for i, d in enumerate(table, 1):
        d["position"] = i

    out = {"competition": competition, "season": season,
           "has_xpts": model is not None, "table": table}
    _TABLE_CACHE[key] = out
    return out


@app.get("/api/team")
def team_profile(competition: str, season: str, team: str):
    """A team's season: match log with running points & expected points,
    home/away splits, and a summary — the drill-down from the league table."""
    cat = predictor.load_catalogue()
    df = cat[(cat["competition"] == competition) & (cat["season"] == season)].copy()
    df = df[(df["home_team"] == team) | (df["away_team"] == team)]
    if df.empty:
        raise HTTPException(404, "No matches for that team/season.")
    df = df.sort_values("date").reset_index(drop=True)

    model = None
    try:
        model, _ = _get_predictor(competition, season)
    except Exception:
        model = None

    log, cum_pts, cum_xpts = [], 0, 0.0
    splits = {"home": {"p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0},
              "away": {"p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}}
    for i, r in df.iterrows():
        home_game = r["home_team"] == team
        venue = "home" if home_game else "away"
        opp = r["away_team"] if home_game else r["home_team"]
        gf = int(r["home_score"] if home_game else r["away_score"])
        ga = int(r["away_score"] if home_game else r["home_score"])
        res = "W" if gf > ga else ("D" if gf == ga else "L")
        pts = 3 if res == "W" else (1 if res == "D" else 0)
        cum_pts += pts
        xp = None
        if model is not None:
            pr = predictor.predict(model, r["home_team"], r["away_team"])
            if pr:
                xp = (3 * pr["p_home"] + pr["p_draw"]) if home_game else (3 * pr["p_away"] + pr["p_draw"])
                cum_xpts += xp
        s = splits[venue]
        s["p"] += 1; s["gf"] += gf; s["ga"] += ga; s["pts"] += pts
        s["w"] += res == "W"; s["d"] += res == "D"; s["l"] += res == "L"
        log.append({"md": i + 1, "date": str(r["date"])[:10], "venue": venue[0].upper(),
                    "opponent": opp, "gf": gf, "ga": ga, "result": res, "pts": pts,
                    "cum_pts": cum_pts, "cum_xpts": round(cum_xpts, 1) if xp is not None else None})

    summary = {"team": team, "competition": competition, "season": season,
               "played": len(df), "points": cum_pts,
               "xpts": round(cum_xpts, 1) if model is not None else None,
               "goals_for": sum(l["gf"] for l in log),
               "goals_against": sum(l["ga"] for l in log),
               "has_xpts": model is not None}
    return {"summary": summary, "splits": splits, "log": log}


@app.get("/api/predict/fixture")
def predict_fixture(competition: str, season: str, home: str, away: str):
    """Predict a single fixture."""
    try:
        model, _ = _get_predictor(competition, season)
    except Exception as e:
        raise HTTPException(500, f"Fit failed: {e}")
    pred = predictor.predict(model, home, away)
    if pred is None:
        raise HTTPException(400, "One of the teams isn't in this competition/season.")
    return pred


@app.get("/api/xt")
def xt_output():
    """Serve every generated Expected Threat set (one per league-season)."""
    import glob
    surfaces = sorted(glob.glob(os.path.join(OUTPUT_DIR, "xt_surface_*.png")))
    if not surfaces:
        raise HTTPException(404, "No xT output yet. Run: python src/xt.py \"La Liga\" \"2015/2016\"")
    sets = []
    for surf in surfaces:
        key = os.path.basename(surf).replace("xt_surface_", "").replace(".png", "")
        title = key.replace("_", " ").replace("-", "/")
        leaders = []
        lf = os.path.join(OUTPUT_DIR, f"xt_leaders_{key}.json")
        if os.path.exists(lf):
            with open(lf) as f:
                leaders = json.load(f)
        sets.append({"key": key, "title": title,
                     "surface": os.path.basename(surf), "leaders": leaders})
    return {"sets": sets}


@app.get("/api/model")
def model_metrics():
    """Return the trained model's validation metrics + plot URLs."""
    mp = os.path.join(MODELS_DIR, "metrics.json")
    if not os.path.exists(mp):
        raise HTTPException(404, "Model not trained yet. Run: python src/xg_model.py")
    with open(mp) as f:
        metrics = json.load(f)
    metrics["calibration_png"] = "model_calibration.png"
    metrics["importance_png"] = "model_importance.png"
    return metrics


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# Mount the rest of the frontend (css/js) if present
if os.path.isdir(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
