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

**4. Predicts matches** — a Dixon-Coles Poisson model fits every team's attack
and defence strength (plus home advantage) from results, then predicts any
fixture: 1X2 probabilities, expected goals, most-likely scorelines, and
over/under 2.5. Validated with a proper time-split and scored against the
base-rate baseline (see numbers below).

**5. Serves it all in a web app** — a clean single-page UI (FastAPI + Preact)
with four tabs: Match report, Scouting report, Predictor, and The model. Reports
are generated on demand and cached, so repeat views are instant.

---

## 🔮 The match predictor

A **Dixon-Coles Poisson model** — the classic, genuinely strong approach to
football prediction. Each team gets an attack and a defence rating fitted by
maximum likelihood from match results; goals are Poisson with a home-advantage
term and the Dixon-Coles low-score correction.

Validated with a **time-split** (train on the earlier matches of a season,
predict the later ones) and scored with the **Ranked Probability Score (RPS)** —
the standard metric for ordered 1X2 outcomes:

| League 2015/16 | Accuracy | Baseline | RPS | Baseline RPS |
|---|---|---|---|---|
| Premier League | **48.9%** | 44.4% | **0.203** | 0.226 |
| La Liga | **49.6%** | 46.6% | **0.215** | 0.233 |

It beats the base-rate baseline on every metric, and an RPS near 0.19–0.21 is
the professional range for 1X2 prediction. A sanity check that it's learning
real football: it rated **Leicester City** the strongest attack of 2015/16 —
the season they won the title — and recovered La Liga's higher home advantage
(0.39) vs the Premier League's (0.19).

```bash
python src/predict.py "Premier League" "2015/2016"                       # validate
python src/predict.py "La Liga" "2015/2016" --fixture "Barcelona" "Sevilla"
```

> **Making it a true "prediction champion."** The ceiling for this kind of model
> is set by **betting odds** — the market is the hardest baseline to beat. To go
> further, train on **football-data.co.uk** (free results + odds, ~22 leagues,
> decades of history), add **Understat** xG form and **API-Football** player/
> injury/lineup data, and benchmark the model's RPS against the bookmakers'
> closing odds. See *Importing data* below for how to pull those.

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

## 📥 Importing data

### StatsBomb (bulk, built in)

`src/ingest.py` pulls **every shot from every available match** — ~3,960
matches across 80 competition-seasons (La Liga, Premier League, Serie A, Ligue
1, Bundesliga, multiple World Cups and Euros, NWSL, WSL, and more) — into one
local dataset. It's **resumable**: already-ingested matches are skipped, so you
can stop and restart any time.

```bash
python src/ingest.py              # ingest everything (resumable; ~1 hour)
python src/ingest.py --limit 300  # just the next 300 matches
python src/ingest.py --comp 11 90 # one competition+season (La Liga 20/21)
python src/ingest.py --stats      # how much is ingested so far
```

The result (`data/shots.parquet`) becomes the xG model's training set
automatically — `python src/xg_model.py` trains on the full ingested corpus
when it's present, which is far larger than the default 4-competition pull.

### Live sources (Understat, FBref, football-data.co.uk)

These are live websites — reachable from any normal machine (but blocked by
restrictive firewalls). `src/sources.py` imports them via the
[`soccerdata`](https://soccerdata.readthedocs.io) package:

```bash
pip install soccerdata
python src/sources.py understat ENG 2023     # shot data + xG, top-5 leagues
python src/sources.py fbref ENG 2023         # Opta-derived season stats
python src/sources.py matchhistory ENG 2023  # results + odds, deep history
```

### A note on SofaScore

SofaScore has **no official/public API**. Its internal endpoints are
undocumented, against its terms of service, and protected by bot-detection, so
they're not a sound base for a project. The sources above are free, legitimate,
and far more complete.

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
