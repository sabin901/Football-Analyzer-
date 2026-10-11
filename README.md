# ⚽ Soccer Analytics

A complete, end-to-end football analytics product: an **Expected Goals (xG)
model** trained from scratch on real data, two kinds of **automated analysis
reports**, and a **web app** that ties it all together. Built entirely on
[StatsBomb open data](https://github.com/statsbomb/open-data).

This mirrors what a professional club's analysis department produces — the
post-match review (within 24 hours of a game) and the pre-match / recruitment
scouting view — in one self-contained app.

---

## ✨ What it does

**1. Trains an xG model** — gradient-boosted trees on ~15,600 real shots.
Validated on held-out data at **ROC-AUC ≈ 0.77**, well-calibrated (predicted
421 goals vs 419 actual), with a reliability curve and feature-importance chart.

**2. Generates post-match reports** — pick any match, get a full dashboard:
score, key-stats bars, shot maps (dot size = xG), an xG race chart, and a pass
network. The classic "who deserved to win" picture.

**3. Generates season scouting reports** — pick a team and season, get an
opponent profile: record, xG for/against per 90, chance-creation and
vulnerability heatmaps, set-piece dependence, attacking-side bias, and a form
timeline.

**4. Serves it all in a web app** — a clean single-page UI (FastAPI + Preact)
with three tabs: Match report, Scouting report, and The model. Reports are
generated on demand and cached, so repeat views are instant.

---

## 🚀 Quick start

```bash
# one command: installs deps, trains the model if needed, starts the app
bash run.sh
```

Then open **http://localhost:8000**.

First run trains the model (~2–4 min). After that it starts in seconds.

### Manual steps (if you prefer)

```bash
pip install -r requirements.txt
python src/xg_model.py          # train the model (one time)
uvicorn app:app --port 8000     # start the web app
```

### Command-line use (no web app needed)

```bash
python src/report.py 8658                 # post-match report for one match
python src/scouting.py 2 27 "Arsenal"     # season scouting report for a team
```

Outputs land in `output/`.

---

## 🧠 The xG model

| | |
|---|---|
| **Data** | ~15,600 shots: 2018 World Cup, La Liga 20/21, Premier League 15/16, FA WSL 20/21 |
| **Features** | distance, shot angle, header, volley, first-time, open play, from corner / free kick / counter, under pressure |
| **Model** | `HistGradientBoostingClassifier` (gradient-boosted trees) |
| **ROC-AUC** | ≈ 0.77 (pro xG models land ~0.78–0.82) |
| **Calibration** | predicted 421 goals vs 419 actual on the held-out set |

The model's own xG tracks StatsBomb's proprietary xG closely on real matches —
the standard sanity check. Shot **angle** and **distance** dominate the feature
importance, exactly as the football intuition says they should.

---

## 🌐 API reference

The web app is backed by a small JSON API you can also call directly:

| Endpoint | What it returns |
|---|---|
| `GET /api/competitions` | all available competitions + seasons |
| `GET /api/matches?competition_id=&season_id=` | matches in a season |
| `GET /api/teams?competition_id=&season_id=` | teams in a season |
| `GET /api/report/{match_id}` | post-match report (JSON + PNG path) |
| `GET /api/scout?competition_id=&season_id=&team=` | scouting report |
| `GET /api/model` | model validation metrics + plot paths |

Generated images are served from `/output/<name>.png`.

---

## 📁 Project structure

```
soccer-analytics/
├── run.sh                 # one-command launcher
├── requirements.txt
├── app.py                 # FastAPI backend + API
├── src/
│   ├── xg_model.py        # feature engineering, training, validation plots
│   ├── report.py          # post-match report generator
│   └── scouting.py        # season scouting report generator
├── frontend/
│   ├── index.html         # single-page app (Preact, no build step)
│   └── vendor/            # vendored Preact + htm (no CDN needed, works offline)
├── models/
│   ├── xg_model.pkl       # trained model
│   └── metrics.json       # validation metrics for the UI
└── output/                # generated reports (PNG + JSON), created on demand
```

No build step, no bundler, no node_modules — the frontend libraries are
vendored, so the app runs anywhere Python does, offline included.

---

## ⚠️ Honest limitations

- **Possession** is a pass-share proxy, not the official on-ball clock
  (StatsBomb free data doesn't include it). Good approximation; labelled as such.
- **xG** has no defender/goalkeeper positions. Adding StatsBomb's 360
  freeze-frame data is the single biggest accuracy gain available next.
- Only the competitions in StatsBomb's **free** open-data set are available.

---

## 🔭 Where to take it next

- Add **360 freeze-frame** features (defender/keeper positions) to the xG model.
- **Player-level** reports (shot/pass maps and radars per player).
- **Head-to-head** mode comparing two teams' scouting profiles side by side.
- Swap the StatsBomb feed for a **computer-vision pipeline** (YOLO + ByteTrack)
  to run the whole thing on footage you record yourself.

---

*Data: StatsBomb open data. All xG figures come from the model in this repo, not
StatsBomb's proprietary model. Built as a portfolio project.*
