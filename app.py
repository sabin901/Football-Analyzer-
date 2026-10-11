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
