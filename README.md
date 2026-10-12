# Footlyzer — Football Analyzer

[Open the dashboard](https://sabin901.github.io/Football-Analyzer-/)

An interactive football analysis desk for the **Premier League, La Liga, Serie A, Bundesliga and Ligue 1**. The same frontend runs on GitHub Pages and FastAPI.

- 76 available league-season result snapshots, with historical coverage back to 2010/11 (coverage varies by league).
- Calculated standings, home/away splits, recent form, team search and sorting.
- Team comparisons with per-match rates, sample windows, clean sheets and head-to-heads.
- A clearly labeled experimental Poisson matchup simulator.
- CSV export and source/freshness information for every league-season.
- Current squads, searchable player appearance statistics, match lineups and box-score reports.
- Opposition briefing exports, with evidence and questions to verify on video.
- Historical event/scouting lab: every available men’s top-five StatsBomb open match, shot maps and positional profiles.
- Rolling-origin forecast validation, downloadable prediction audits, upcoming fixtures and season simulations.
- Downloadable indexed SQLite warehouse, SQL examples, model card and club-role research.
- Historical StatsBomb research reports kept separate from present-day data.

## Free data, visible provenance

OpenFootball supplies the schedule and archived results under CC0. ESPN's public scoreboard supplements recent completed results, without an API key. It is an unofficial endpoint and has no service guarantee; ESPN data is not covered by OpenFootball's CC0 license. See [DATA_SOURCES.md](DATA_SOURCES.md).

The importer validates scores, season dates, fixture counts and team identities. It retains the last verified data after a provider failure. Abandoned, postponed and missing results are distinguished. A successful fetch is not described as a live feed: the dashboard shows the fetch time, latest recorded result and coverage warnings separately.

GitHub Actions refreshes every six hours and deploys the artifact in the **same workflow**, avoiding reliance on bot commits triggering another workflow.

## Run locally

```bash
python -m venv .venv
# Activate .venv for your OS, then:
pip install -r requirements.txt -r requirements-dev.txt
python src/build_site.py
uvicorn app:app --host 127.0.0.1 --port 8000
```

Or `docker compose up --build`. The homepage is the shared dashboard; `/research` preserves the original event-analysis app. Current snapshots are committed, so normal builds need no network data calls. Historical research generation may require downloading StatsBomb data and training the research model separately.

Refresh current data explicitly:

```bash
python src/dashboard_data.py
python src/workbench_data.py
python src/forecast_lab.py
python src/build_site.py
```

The season changes automatically in July. A new season is only advertised as available once its validated schedule exists. Missing new-season data leaves the previous season explicitly labeled historical.

## Validation

```bash
python -m unittest discover -s tests -v
node --check frontend/dashboard.js
node --check frontend/workbench.js
```

Tests cover provider formats, zero scores, future/duplicate results, source failures, fixture identity, abandoned matches, standings arithmetic, probability normalization, API input validation and frontend/data packaging parity.

## Analytics boundaries

Calculated tables use points, goal difference and goals scored; they do not implement every official tie-breaker or administrative points deduction. The current simulator is a **smoothed goals-based Poisson baseline**. It has no validated accuracy claim, does not account for injuries/lineups, and does not produce shot-based xG.

The original research modules remain in `src/`: shot-based xG, expected threat, player profiles, match/scouting reports, Dixon–Coles prediction and historical backtests. Their metrics apply to their historical datasets, not to the new baseline or today's players. The shots-on-target proxy in historical experiments must not be interpreted as shot-location xG. Aggregate predicted versus observed goal totals alone do not demonstrate calibration, and retrospective team ratings do not prove early-season predictive skill.

See [REVIEW.md](REVIEW.md) for the engineering and soccer-analysis assessment, and [DEPLOYMENT.md](DEPLOYMENT.md) for operations.


## Analyst workbench and reproducible backfills

As imported on 12 October 2026: **25,745 completed results**, **2,994 current player-club records**, and **7,775,488 historical events processed from 2,169 matches in 27 provider-selected datasets**. These counts describe this snapshot, not a claim of complete worldwide or current event coverage. All five leagues have current squad and match-summary imports. No API credentials are needed.

```bash
python src/import_open_history.py  # available CC0 files; failures recorded
python src/event_workbench.py      # resumable top-five event backfill
python src/forecast_lab.py
python src/build_site.py           # includes SQLite and readable documentation pages
```

Historical imports are explicit; the six-hour workflow refreshes current results, squads and match reports, then rebuilds forecasts and the site. Response caching limits repeat requests. Large raw event files are processed into compact aggregates, shot records and pass links; every derived match retains source URL, update marker and event hash. The import does not download paid video, tracking or medical data.

Read the [data dictionary](docs/DATA_DICTIONARY.md), [model card](docs/MODEL_CARD.md), [club-role research](docs/CAREER_RESEARCH.md) and [portfolio playbook](docs/PORTFOLIO_PLAYBOOK.md). The frontend uses vanilla JavaScript, functional club imagery, responsive navigation and lazy dataset loading; it is not a React portfolio claim. Current player minutes are unavailable, so per-90 metrics are restricted to the historical event lab and labeled as clock estimates.

FastAPI also provides `/api/workbench/catalogue`, `/api/workbench/players/{league}` (bounded pagination), `/api/workbench/current/{league}`, `/api/workbench/forecast/{league}`, `/api/workbench/events/{competition_season}`, `/api/workbench/event-match/{id}` and `/api/workbench/backtest/{league}`. GitHub Pages serves equivalent static snapshots; it does not host a Python process.
