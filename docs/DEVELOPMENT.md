# Developer guide

## Follow one request

The public dashboard is static. Python fetches, checks and summarizes data before deployment. The browser reads the resulting JSON. FastAPI offers the same dashboard locally plus queryable endpoints and research tools; GitHub Pages does not run Python.

1. `src/dashboard_data.py` validates fixtures and writes result snapshots in `data/live/`.
2. `src/workbench_data.py` produces current squads and match summaries in `data/workbench/`.
3. Event and spatial importers produce historical files there. The forecast pipeline reads recorded results and writes probabilities and evaluation audits.
4. `src/build_site.py` packages the frontend, JSON, SQLite warehouse and documentation into `site/`.
5. `frontend/dashboard.js` reads `data/manifest.json`, chooses a league and season, then renders a workspace. Analyst views load larger datasets only when needed.

## Read the frontend

This is ordinary browser JavaScript, without a framework or transpiler. Scripts load with `defer` in the order declared in `frontend/dashboard.html`.

`ui.js` contains formatting, HTML escaping and export helpers. `snapshot-store.js` defines the request cache. Branding and icons follow, then spatial functions, workbench controls and view renderers. `dashboard.js` loads last and starts the application. Files share a page scope: changing script order or adding duplicate top level names can break initialization.

Result state lives in `dashboard.js`. Analyst controls live in `wb` in `workbench.js`; heatmap controls live in `hs` in `spatial.js`. View functions return HTML strings. Rendering replaces the content area and applies shared icons. Delegated document listeners keep controls working after replacement. Search handlers restore focus after rerendering.

Provider text must pass through `esc()` before HTML insertion. Missing numbers use `decimal()` and display a dash. CSV exports use `toCsv()`, which preserves accented names and prevents text from becoming a spreadsheet formula. Numeric negatives remain numeric.

## Why the cache has a generation counter

`snapshotStore.load(file)` returns cached data immediately. Otherwise it returns `null`, starts one request and rerenders when it finishes. Concurrent requests for the same file share that fetch.

Refresh clears the cache and increments its generation. A response from an old generation is ignored, even if it finishes after the new response. Failures become readable error states and can be retried with Refresh. Tests deliberately complete requests in the wrong order to check this behavior.

## Add a metric

Start with the source contract. Establish whether a value describes a match, player appearance, player and club record, or event. Keep source, season and sample size alongside it. Add ingestion and validation in the responsible Python module, then rebuild its snapshot.

Add the metric to its view and export. Use a missing value when the provider does not report it; do not infer zero. For a rate, display the denominator and document filters. Test a failure that would mislead an analyst, such as confusing missing minutes with zero minutes or leaking future results into a forecast. Update the data dictionary.

## Decisions worth understanding

- Forecast training excludes the prediction date and later dates. Dates without reliable kickoff times cannot safely establish within day ordering.
- Spatial cells use StatsBomb's 120 by 80 coordinates. Both teams already attack right; rotating the second half again would corrupt the map.
- Compared heatmaps share a colour scale. Event share compares distributions; counts depend on possession and sample size.
- Player participation is independent of the action filter. Selecting shots must not remove a match from the denominator merely because the player took no shots.
- Current summaries and historical profiles have different coverage. They are never silently joined into a current scouting rating.
- Atomic writes and validation preserve the previous usable snapshot when a provider or write fails.

Read the spatial method and model card for complete assumptions. Source comments explain decisions that are easy to get wrong; they do not disable working code.

## Edit and verify

Edit `frontend/`, run `npm run format`, then `python src/build_site.py`. Preview with `python -m http.server 8000 --directory site`, or use FastAPI as described in the README. Refresh the browser after rebuilding.

`dashboard.css` styles the shell and result views; `workbench.css` styles analyst views and charts. Reuse CSS variables, Lucide icons, visible labels, focus states and reduced motion rules. League assets and their source manifest live in `frontend/assets/leagues/`.

Check a narrow viewport, keyboard controls, empty filters, historical seasons and missing data. A chart working only for the default selection is incomplete.

Run the README checks. Python tests verify pipeline and API contracts; Node tests cover calculations, cache races and export helpers. Black is scoped in `pyproject.toml` to the maintained pipeline, API and tests. Older research experiments remain separate.

Build before publication tests: they compare source and packaged files. Commit source and tracked `site/` output together. Large generated artifacts, including the warehouse and rendered documentation, are ignored and recreated by CI.

If a new script returns 404, inspect its relative URL and rebuild. If a workspace stays on Loading, inspect the browser console and matching JSON request. If data looks old, compare source fetch time, latest recorded match and import failures before assuming a UI error.

The research archive is historical. Experimental xG, expected threat, valuation and Dixon–Coles modules are not substitutes for maintained forecast evaluation. Promote output to a validated claim only after a separate reproducible evaluation.

## Versioned browser assets

`package_frontend()` in `src/build_site.py` gives every script and stylesheet a filename containing a hash of its content. The generated entry point references those files. This prevents a returning visitor from combining new HTML with old cached JavaScript. Unchanged content retains its URL; earlier fingerprints remain available for older cached pages. Source HTML stays readable, and publication tests verify the generated URLs and file contents.
