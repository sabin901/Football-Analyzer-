# ⚽ Football Analyzer

> **An automated opposition-scouting and match-prediction engine that surfaces
> underlying performance — expected goals, expected threat, team strength and
> win probabilities — from raw event data.** It turns StatsBomb's open data into
> the three things a football department actually uses: post-match reviews,
> season scouting profiles, and forward-looking match predictions. Everything is
> built from scratch, validated with professional metrics, and runs with one
> command.

**Live dashboard:** https://sabin901.github.io/Football-Analyzer-/ · **Repo:** https://github.com/sabin901/Football-Analyzer-

---

## Key results (held-out validation)

| Model | Metric | Result | Benchmark | Why it matters |
|---|---|---|---|---|
| **xG** (expected goals) | ROC-AUC | **0.79** | pro models 0.78–0.82 | Separates good chances from bad ones |
| **xG** calibration | pred vs actual goals | **2778 vs 2807** | — | A "0.3 xG" chance really scores ~30% |
| **Predictor** (Dixon-Coles + recency) | Accuracy | **51.9%** | base rate 44.4% | 1X2 outcome, Premier League 2015/16 |
| **Predictor** | RPS | **0.2005** | base rate 0.226 | Lower is better; pro range ~0.19–0.21 |

### Backtested across **120 league-seasons** (not cherry-picked)

The predictor is validated on every top-5-league season from 2002/03 to
2025/26 — a time-split per season, scored by RPS, against the base-rate baseline:

| Rating basis | Mean RPS | Mean accuracy | Seasons beating baseline |
|---|---|---|---|
| Baseline (base rates) | 0.2275 | 45.9% | — |
| Goals (Dixon-Coles) | 0.2095 | 50.1% | 106 / 120 |
| **xG (chance quality)** | **0.2063** | **50.9%** | — |

Two findings, both honest: the model beats the baseline in **106 of 120**
seasons, and rating teams by **expected goals (chance quality) rather than goals
scored** lowers mean RPS (0.2095 → **0.2063**) and wins in **70 of 120** seasons —
so the xG basis is the default. The improvement is modest because the xG proxy
here is shots-on-target; true shot-location xG would widen it. Recency weighting
(90-day half-life) is applied throughout. Run it yourself: `python src/backtest.py`.

The remaining benchmark is **bookmaker closing odds** (RPS ~0.19); `src/benchmark.py`
runs that comparison once the odds are pulled (`python src/live_api.py odds E0 2324`).

---

## What it does

| Capability | What you get |
|---|---|
| **xG model** | Gradient-boosted expected-goals model, 100k+ shots, calibrated, with reliability + feature-importance plots |
| **Player profiles** | Per-90 metrics percentile-ranked vs positional peers (radar) + statistical player similarity — the scouting view |
| **Expected Threat (xT)** | Values ball *progression*, not just shots — an xT surface + ranked ball progressors (Koke, Kroos top La Liga 15/16) |
| **Post-match report** | Score, shot maps, cumulative-xG race, pass networks — the club review in one dashboard |
| **Scouting report** | Season opponent profile: xG for/against, chance-creation & vulnerability heatmaps, set-piece reliance, form |
| **Match predictor** | Dixon-Coles Poisson with recency weighting → 1X2, expected goals, scorelines, over/under, fitted team strengths |
| **Web app** | FastAPI + Preact, four tabs, on-demand generation, cached |
| **Live-data pipeline** | Scheduled GitHub Action pulls fresh fixtures/results/standings and republishes the dashboard |

---

## ⚡ Quickstart — one command

```bash
docker compose up          # → http://localhost:8000
```

or without Docker:

```bash
bash run.sh                # installs deps, trains the model, starts the app
```

---

## 📊 Case study — Leicester City's title, seen in the data

*A 250-word read for a sporting director, written from this tool's own output.*

In 2015/16 Leicester City won the Premier League at 5000-to-1. Traditional
tables called it a fluke. The underlying numbers did not. When this model fits
attack and defence coefficients to that season's results, **Leicester emerge
with the strongest attack rating in the division (+0.41)** — ahead of Manchester
City and Arsenal — paired with a solid, unspectacular defence (−0.04). This is
not hindsight: attack/defence strengths are estimated purely from goals for and
against, and they rated Leicester a genuinely elite scoring side, not an
over-achieving one.

The scouting view sharpens the picture. Leicester's chance-creation heatmap
concentrates in direct, central, high-value zones — consistent with their
fast-transition, Vardy-led approach — while their xG-conceded profile stays low,
the signature of a compact, disciplined block. The predictor, in turn, gives
them high home-win probabilities against mid-table sides and competitive numbers
against the traditional top six: the model saw a team that *deserved* to win
most weeks, not one riding variance.

The lesson for recruitment and matchday planning is the one clubs live by:
**the league table lags; underlying performance leads.** A sporting director
watching these coefficients in September would have seen Leicester's title bid
as credible months before the table confirmed it. That is precisely the edge
this engine is built to provide — turning raw events into an early, honest read
on who is genuinely good.

---

## 🔮 The models, briefly

**xG** — a gradient-boosted classifier on shot distance, angle, body part, and
situation (open play, set piece, counter, under pressure). Validated by
ROC-AUC *and* a calibration curve, because a usable xG must be probabilistically
honest, not just rank-ordered.

**xT (Expected Threat)** — the pitch is a 16×12 grid; each zone's value is solved
by value iteration from the data: `xT = P(shoot)·P(goal) + P(move)·Σ T·xT`. Any
pass or carry is worth `xT(end) − xT(start)`. This rewards the players who move
the ball into danger, not only the finishers — the modern scouting lens.

**Predictor** — a Dixon-Coles Poisson model with the low-score correction and
**recency weighting**, fitting each team's attack/defence + home advantage,
validated by a time-split and the Ranked Probability Score.

---

## 📥 Data pipeline & importing

```
StatsBomb open data ──► src/ingest.py ──► data/shots.parquet (xG training)
                    └─► src/xt.py      ──► xT surface + progressors
football-data.org ──► src/live_api.py  ──► data/live/ (fixtures, standings)   [free key]
football-data.co.uk ─► src/live_api.py ──► odds CSVs (vs-market benchmark)    [no key]
Understat / FBref ──► src/sources.py   ──► deeper xG + stats                  [your machine]
```

- `python src/import_results.py` — top-5 leagues × 23 seasons of results (**41,601 matches, 116 league-seasons** — 2002–2025) for broad predictor testing
- `python src/ingest.py` — bulk import every shot from ~3,960 matches (resumable)
- `python src/live_api.py sync` — live fixtures/results/standings (free key)
- `python src/live_api.py odds E0 2324` — results + betting odds, no key
- See **[DEPLOYMENT.md](DEPLOYMENT.md)** for the full GitHub Pages + Actions setup

---

## 🏗️ Architecture

```
src/
  xg_model.py   xG model: features, training, calibration & importance plots
  xt.py         Expected Threat grid + ball-progressor rankings
  report.py     post-match report generator
  scouting.py   season scouting report generator
  predict.py    Dixon-Coles predictor with recency weighting
  ingest.py     bulk StatsBomb importer (resumable)
  live_api.py   live + odds data importer (football-data.org / .co.uk)
  sources.py    Understat / FBref importers
  build_site.py static site generator for GitHub Pages
app.py          FastAPI backend + JSON API
frontend/       Preact single-page app (no build step; libs vendored)
.github/        Actions: build+deploy Pages, scheduled live-data refresh
Dockerfile      one-command container
```

**Tech:** Python · scikit-learn · scipy · pandas · matplotlib · mplsoccer ·
FastAPI · Preact · StatsBomb open data.

---

## 🔬 VAEP — possession value (reference implementation)

The player tab shows a **VAEP leaderboard** (Valuing Actions by Estimating
Probabilities — Decroos et al.) when you generate it. VAEP values every action by
how much it changes the chance of scoring minus conceding, so progression is
credited, not just shots. It runs via the reference **`socceraction`** library,
which pins an older pandas/pandera than the app, so it lives in its own venv:

```bash
python -m venv .venv-vaep && source .venv-vaep/bin/activate   # Windows: .venv-vaep\Scripts\activate
pip install -r requirements-vaep.txt
python src/vaep_socceraction.py "La Liga" "2015/2016"
```

That writes `data/vaep_<league>_<season>.parquet` and the app's Players tab
auto-detects it — no code change. (A from-scratch VAEP was attempted first and
*not shipped*: with sparse goal labels it collapsed to shot proximity and ranked
elite progressors poorly — a reminder that VAEP needs the full SPADL pipeline.)

## 🛣️ Roadmap

- **Odds benchmark** — score the predictor against bookmaker closing odds (RPS)
- **xG-based dynamic ratings** — feed rolling team xG (not goals) into the predictor
- **StatsBomb 360** — add defender/keeper positions to xG (freeze-frame shot quality)
- **Pressing metrics** — PPDA and defensive-pressure maps for out-of-possession profiles

---

*Built by [Sabin Raut](https://github.com/sabin901). Data: StatsBomb open data.
All xG, xT and prediction figures come from the models in this repository.*
