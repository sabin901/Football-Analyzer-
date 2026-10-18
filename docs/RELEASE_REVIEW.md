# Public interface and data review — 18 October 2026

This review is retained in the repository and excluded from the website's documentation allowlist.

## Codebase

The product uses a static HTML/CSS/JavaScript dashboard with a FastAPI research backend. `frontend/dashboard.html` is the public entry point; `dashboard.js`, `workbench-views.js` and `spatial.js` render the result, player, forecast and event views. `src/build_site.py` packages content-addressed browser assets, league-season snapshots, the event archive and a SQLite warehouse into `site/`. GitHub Actions refreshes sources, runs validation and deploys that directory on main.

`src/dashboard_data.py` imports OpenFootball schedules and explicitly maps ESPN results. `workbench_data.py` imports current squads and match summaries. `event_workbench.py` and `spatial_workbench.py` maintain the separate historical StatsBomb event archive. `forecast_lab.py` performs date-blocked rolling evaluations and season scenarios.

## Changes

- Removed the portfolio/careers destination and its promotional content. Removed static research examples from primary navigation and the mobile selector. Personal documents remain in the repository but are neither copied to the website nor added to its sitemap. Old bundles containing personal-page references are removed during packaging.
- Added compact team identity cards, consistent circle/square team markers, one labelled axis per comparison metric, match-weighted league averages, explicit lower-is-better defence labels, and responsive layouts.
- Redesigned historical heatmaps with a continuous teal-to-yellow scale on the original exact 12 × 8 grid, clearer pitch markings, high-value cell labels, shared comparison scales, territory shares, accessible numerical tables and source attribution. No smoothing or invented tracking was introduced.
- Simplified forecast presentation, capped the initially expanded fixture list at six, exposed training samples and prior contributions, handled unavailable evaluations, and withheld finishing-position probabilities when unresolved fixtures are omitted.
- Fixed explicit source-name mappings for Levante / Levante UD and Atalanta / Atalanta BC. Refreshed current results, squads and match summaries, then rebuilt forecasts and published data.

## Data refresh

| League | Recorded results before | After |
| --- | ---: | ---: |
| Premier League | 68 | 69 |
| La Liga | 82 | 86 |
| Serie A | 65 | 67 |
| Bundesliga | 53 | 54 |
| Ligue 1 | 59 | 62 |

All five result and squad refreshes completed without importer errors. The refreshed files contain 338 current-season match summaries and 3,018 player-club records. The current StatsBomb competition catalogue was checked: all available top-five competition/season selections are already represented, so no unsupported event coverage is claimed.

The existing 365-day venue-Poisson formula was retained. Better source completeness and safer presentation do not establish a new predictive-accuracy claim. La Liga still has an abandoned fixture; its season scenario is explicitly partial and rank probabilities are withheld.

## Verification

- 49 Python tests and 10 JavaScript tests passed, including source identity, temporal leakage, incomplete-schedule safety, public-document exclusion and packaged data contracts.
- Full static build, JavaScript syntax, Prettier check, Black check and Git whitespace checks passed.
- Browser checks at 1440 × 1000 and 390 × 844: all primary workspaces load; comparison filters and individual player/action filters update; no document overflow in tested views; no browser console errors observed.
- CSV/SVG generation was exercised with Messi's 2015/16 Barcelona passes: 96 grid cells sum to 1,926 passes, selected identity and attribution are retained, and the exported SVG parses as XML. The embedded browser's download-event check timed out, so operating-system download completion was not confirmed.
- Local screenshots: `.artifacts/team-comparison-desktop.jpg` and `.artifacts/heatmap-desktop.jpg`.

## Reference sources

- [Hudl StatsBomb analysis platform](https://www.hudl.com/products/statsbomb/platform): functional analysis and readable event visualisations.
- [Hudl StatsBomb Open Data](https://github.com/hudl/open-data): event coverage, schema and attribution requirements.
- [OpenFootball JSON](https://github.com/openfootball/football.json): CC0 results and schedules.
- [Dixon and Coles, 1997](https://academic.oup.com/jrsssc/article-abstract/46/2/265/6990546): reviewed as a modelling reference; this release does not claim to implement that model or reproduce club forecasting systems.

Current player event feeds, continuous tracking, injuries and confirmed future lineups remain outside the available data. The historical heatmaps must not be presented as current player movement.

## Public data-quality release

The follow-up release adds a separate verification layer for every one of the 76 league-season snapshots. At review, 25,768 scores and dates agree with Football-Data.co.uk, two administrative differences have explicit evidence, and 44 recent results await that provider's update. There are no unresolved score/date conflicts. ESPN's W/D/L and goals reconcile for 75 tables; the 2025/26 Ligue 1 ranking is withheld because the archived provider table omits the ratified Nantes–Toulouse draw.

The correction registry records 89 changes or annotations: 66 July 2020 Premier League dates, 20 missing 2024/25 final-round results, and three administrative outcomes. Overall tables retain provider points, deductions and ordering; comparison samples use match points. The downloadable JSON, CSV and SQL retain administrative outcome semantics and source notes.

The unvalidated simulator and season-finishing projections are removed from the public product. Experimental upcoming probabilities require fresh, reconciled inputs. Their browser expiry is tied to the oldest input timestamp, so rebuilding cannot extend stale data's life. Production builds freeze the first eligible prediction before its fixture date; local and PR builds do not backfill this prospective record. Historical evaluations remain explicitly reconstructed.

Validation: 63 Python tests and 11 JavaScript tests, including publication contracts, administrative SQL exports, corrections, identity mapping, stale-input gating and prospective-log immutability. Format and whitespace checks run with the release. Desktop and mobile browser verification covers corrected standings, disclosed table discrepancies, forecast presentation and responsive layout.
