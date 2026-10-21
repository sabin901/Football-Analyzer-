# Footlyzer

A football analysis workspace with an explicitly licensed public archive and private, browser-local evidence briefs.

[Open the website](https://sabin901.github.io/Football-Analyzer-/) · [Data policy](docs/DATA_QUALITY.md) · [Analyst guide](docs/ANALYST_GUIDE.md) · [Forecast method](docs/MODEL_CARD.md)

## What it does

- Explore five European leagues: recorded results, form and comparable per-match rates.
- Analyze 1,826 historical 2017/18 matches and 3.07 million events from the CC BY 4.0 Pappalardo/Wyscout research archive. View exact action grids, shots and player tendencies.
- Inspect experimental venue Poisson forecasts against frequency, equal-probability, Elo and fitted Poisson challengers. Earlier-data-only backtests, calibration and prospective logs are downloadable.
- Import your own permitted CSV, attach local video, record evidence and export a decision brief. Files are not uploaded. Optional local storage is unencrypted; read the [privacy policy](docs/PRIVACY.md).

The public result feed is a community source and can lag. Computed tables do not claim independently verified official standings or deductions. Upcoming probabilities are withheld when coverage or freshness checks fail. Current player events, provider xG, injuries and continuous tracking are unavailable. Historical player records must not be presented as current recruitment evidence.

## Reproduce the public website

Use Python 3.13 and Node.js 22. All public datasets included under data/open have explicit reuse licenses. Historical event files are stored in a compact checksum-pinned bundle and expanded by the build. No API key or paid service is needed for the open archive. An optional free delayed current-season feed can be activated with a GitHub Actions secret; see [API setup](docs/API_SETUP.md).

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
npm ci
.venv/bin/python src/build_site.py
.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory site
```

Open http://127.0.0.1:8765. The public app is static. The older FastAPI research service is optional and is not the public deployment.

## Refresh and validate

```sh
.venv/bin/python src/open_results.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python src/forecast_lab.py
.venv/bin/python src/build_site.py
.venv/bin/python -m unittest discover -s tests -v
npm test
npm run format:check
.venv/bin/python -m black --check .
```

To reproduce the historical event import, run `.venv/bin/python src/open_events.py`. It downloads approximately 80 MB of pinned Figshare files, verifies their licenses and checksums, and uses substantially more memory while reading expanded JSON. `src/open_results.py --archive` refreshes all available seasons. Failures retain the last available snapshot. Historical input changes require a forecast rebuild. Run `src/bundle_data.py pack` after an intentional archive rebuild to update the versioned bundle.

Browser CI uses Playwright Chromium for desktop/mobile view coverage, file-validation errors, safe rendering, local save/restore and export journeys. `npm run test:browser` runs those journeys with a temporary localhost server. Tests do not contact external analytics or upload user data.

## Release pipeline

Pull requests build and validate without deployment. On main and the hourly schedule, Actions restores approved snapshots, attempts a results refresh and optional delayed-provider refresh, rebuilds forecasts, validates contracts and browser journeys, and deploys a clean Pages artifact. Refresh snapshots and first-publication logs are versioned separately in `codex/data-snapshots`; the scheduler never commits generated site files or data refreshes to main. Normal fast-forward Git pushes protect concurrent data updates.

The published manifest records code revision, data revision and build time. `site/` is disposable generated output. The public build fails on missing or disallowed provenance; it never copies arbitrary legacy research outputs.

## Rights and remaining evidence

OpenFootball results are CC0. The specific Pappalardo/Wyscout research release is CC BY 4.0 with full attribution and transformation notes. This does not grant access to commercial Wyscout services or match video. See [source credits](docs/ASSET_CREDITS.md) and `data/open/source_registry.json`.

Legacy research scripts remain for separate, authorized local work. Their automatic restricted-feed entry points are disabled unless the operator explicitly configures licensed research. Legacy data and model files are not tracked in the current release or included in Pages. Previous Git history may still contain them; it has not been rewritten. No new blanket code license is granted by this change.

This release does not establish customer demand, paid pilots, reliable live predictive advantage, security certification or club adoption. Those require independently observed evidence, not more interface features.

## Responsive explorer

All ten workspaces include contextual quick starts. Layouts reflow from narrow tabs to wide displays; dense tables scroll within their own region. Historical forecast replays expose scoreline probabilities and disagreement between models. Club badges are original Footlyzer identifiers, not official crests. A publication notification lets returning visitors load an updated snapshot without silently replacing their filters or private work.
