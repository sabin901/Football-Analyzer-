# Footlyzer

A football analysis workspace for the Premier League, La Liga, Serie A, Bundesliga and Ligue 1. Built with Python, SQL and plain JavaScript, with a public dashboard that needs no API credentials.

[Open the dashboard](https://sabin901.github.io/Football-Analyzer-/) · [Data dictionary](docs/DATA_DICTIONARY.md) · [Developer guide](docs/DEVELOPMENT.md) · [Model card](docs/MODEL_CARD.md)

## What you can do

- Compare teams using results, venue splits, recent form and sample sizes.
- Explore current squads, imported player appearances, lineups and match statistics.
- Export an opposition briefing with source evidence and questions to verify on video.
- Inspect historical player and team heatmaps, shot maps, cumulative xG and positional profiles.
- Evaluate a goals model against simple baselines using chronological backtests and downloadable prediction audits.
- Export CSV tables, SVG maps and an indexed SQLite warehouse for independent analysis.

There are 12 workspaces. Current match summaries and historical events stay separate throughout the interface. Data & methodology shows coverage and freshness; a fetch timestamp does not guarantee that all results are present.

## A five minute review

1. Open **League overview**, change league and inspect a team's venue splits.
2. In **Player & team heatmaps**, choose a historical dataset, player and action. Compare distributions using the shared colour scale, export the map and inspect its numeric grid.
3. Open **Forecast lab** and compare the rolling evaluation with its baselines before looking at future scenarios.
4. Download the SQL warehouse from **Data & methodology**. Reproduce a finding using the [portfolio playbook](docs/PORTFOLIO_PLAYBOOK.md).
5. Read the [spatial method](docs/SPATIAL_METHOD.md) and [model card](docs/MODEL_CARD.md), then inspect the corresponding tests.

These demonstrate data engineering, statistical evaluation, visual communication and frontend development. This is a portfolio application; it does not claim professional club deployment or proven recruitment outcomes.

## Run locally

Python 3.12 is used in CI. Node 22 is needed only for frontend tests and formatting. The browser has no npm runtime dependencies.

```bash
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in PowerShell, or `source .venv/bin/activate` on macOS/Linux. Then:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
npm ci
python src/build_site.py
uvicorn app:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. The shared dashboard is at `/`, the older experimental app at `/research`, and API documentation at `/docs`. `docker compose up --build` is also available. Existing snapshots are committed, so building the dashboard does not fetch new football data. The checkout contains a substantial historical archive.

For a static preview after building, run `python -m http.server 8000 --directory site` instead of Uvicorn. Historical research endpoints may require their own data downloads and trained models.

## Data and limits

| Source | Used for | Important boundary |
| --- | --- | --- |
| OpenFootball | Schedules and archived results | CC0; coverage varies by season and league |
| ESPN public endpoints | Current results, squads and match summaries | Unofficial, no service guarantee; not covered by OpenFootball's license |
| StatsBomb Open Data | Historical event locations, shots and player profiles | Selected competitions and seasons; attribution and source terms apply |

Current reliable player minutes, shot xG, injuries and continuous tracking are unavailable. Heatmaps show historical action locations, not distance covered or time spent in a zone. Some event seasons include only selected teams. Missing values stay missing.

Calculated standings omit administrative deductions and some competition specific tie breakers. Forecasts are experimental probabilities from goals data, with documented assumptions. The matchup simulator and older research models are separate from the evaluated forecast pipeline. See [data sources](DATA_SOURCES.md) and [asset credits](docs/ASSET_CREDITS.md).

## Code map

| Location | Responsibility |
| --- | --- |
| `frontend/dashboard.js` | Navigation, league loading and result views |
| `frontend/workbench.js` | Analyst controls and snapshot loading |
| `frontend/workbench-views.js` | Player, match, event, forecast and portfolio views |
| `frontend/research.js` | Fixed historical reports and explicit archive links |
| `frontend/spatial.js` | Heatmap filters, SVG rendering and spatial exports |
| `frontend/ui.js`, `snapshot-store.js` | Shared formatting, safe CSV exports and request caching |
| `src/dashboard_data.py`, `workbench_data.py` | Current data ingestion and validation |
| `src/event_workbench.py`, `spatial_workbench.py` | Historical event processing and aggregation |
| `src/forecast_lab.py`, `warehouse.py` | Forecast evaluation and SQL warehouse |
| `src/build_site.py`, `build_docs.py` | Static deployment and documentation pages |
| `app.py` | FastAPI endpoints and local hosting |
| `tests/` | Data contracts, API validation and frontend calculation tests |

Edit `frontend/` and `src/`, then rebuild. `site/` is generated output. The [developer guide](docs/DEVELOPMENT.md) explains the data flow and design choices.

## Checks

```bash
python src/build_site.py
python -m unittest discover -s tests -v
npm test
npm run format:check
python -m black --check .
```

Use `npm run format` and `python -m black .` to format the maintained frontend and pipeline. Tests cover source failures, fixture identity, standings arithmetic, strict prediction cutoffs, spatial coordinates, API inputs, published files, stale requests and exports. Browser release checks also cover all workspaces, the five leagues and mobile layouts.

## Refresh and deploy

```bash
python src/dashboard_data.py
python src/workbench_data.py
python src/forecast_lab.py
python src/build_site.py
```

GitHub Actions runs checks, refreshes current data every six hours, builds the site and deploys that same artifact. Failed source requests retain the last good snapshot with a visible warning. Historical imports are explicit operations rather than repeated scheduled downloads. See [deployment](DEPLOYMENT.md) for the full procedure.

For portfolio presentation and relevant roles, see the [application guide](docs/APPLICATION_GUIDE.md). Pair the software with an original match analysis and a reproducible notebook or SQL investigation that you can explain in an interview.
