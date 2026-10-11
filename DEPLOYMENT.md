# Deployment guide

Football Analyzer has a Python/FastAPI backend, so it deploys in **two layers**.
GitHub Pages can only serve static files — it can't run the backend — so the
plan splits the project cleanly:

| Layer | What it is | Where it runs | Cost |
|---|---|---|---|
| **Public dashboard** | Static site (standings, predictions, model stats) | **GitHub Pages** | Free |
| **Live-data engine** | Scheduled importer that refreshes the data | **GitHub Actions** (cron) | Free |
| **Full interactive app** | FastAPI + the 4-tab UI, live report generation | **Local** (or a free host) | Free |

The first two are 100% GitHub. The third runs locally with one command, or on a
free backend host if you want it public (see the last section).

---

## 1. Public dashboard on GitHub Pages (one-time setup)

1. Push the repo (already done).
2. In the repo: **Settings → Pages → Build and deployment → Source = GitHub
   Actions**.
3. That's it. The `deploy.yml` workflow builds `site/` and publishes it on every
   push to `main`. Your page appears at:
   **https://sabin901.github.io/Football-Analyzer-/**

The site is built by `src/build_site.py` from committed data (the match
catalogue + trained models), so it always renders even with no live feed.

---

## 2. Live data on a schedule (GitHub Actions)

This is the "real-time, even if slightly late" engine. `refresh-data.yml` runs
**every 6 hours**, pulls fresh fixtures / results / standings, rebuilds the site,
and commits — which re-triggers the deploy.

**One-time setup — add your free API key as a secret:**

1. Get a free key: https://www.football-data.org/client/register (free tier: 10
   requests/min, the major leagues).
2. In the repo: **Settings → Secrets and variables → Actions → New repository
   secret**. Name it **`FOOTBALL_DATA_API_KEY`**, paste the key.
3. Done. The scheduled job now refreshes live data automatically. Without the
   secret, the job still runs and just rebuilds the site from existing data.

Change the cadence by editing the `cron:` line in
`.github/workflows/refresh-data.yml` (e.g. `0 * * * *` for hourly).

---

## 3. Importing data — what runs where

| Source | Command | Needs | Where |
|---|---|---|---|
| **StatsBomb** (bulk events/xG) | `python src/ingest.py` | nothing | anywhere incl. this repo |
| **football-data.org** (live fixtures/results/standings) | `python src/live_api.py sync` | free API key | your machine / Actions |
| **football-data.co.uk** (results + **odds**, decades) | `python src/live_api.py odds E0 2324` | nothing | your machine / Actions |
| **Understat / FBref** (xG, deep stats) | `python src/sources.py understat ENG 2023` | `pip install soccerdata` | your machine |

> The live sources are blocked only inside restricted sandboxes. On your laptop
> and on GitHub's runners, they work directly.

---

## 4. Running the full interactive app locally

```bash
bash run.sh          # installs deps, trains the model if needed, starts the app
# open http://localhost:8000
```

Four tabs: **Match report**, **Scouting report**, **Predictor**, **The model**.

---

## 5. (Optional) Host the full app publicly for free

The FastAPI app can go on a free backend host so the interactive version is
public too. Easiest options:

- **Render** (free web service): connect the repo, build `pip install -r
  requirements.txt`, start `uvicorn app:app --host 0.0.0.0 --port $PORT`.
- **Hugging Face Spaces** (free, Docker or Python): add a `Dockerfile` or a
  Spaces config that runs the same uvicorn command.
- **Railway / Fly.io**: similar one-service deploy.

Point the Pages dashboard's links at that URL and you have: a fast public
static dashboard (Pages) **plus** the full live app (host) — all free.
