# Deployment

Production: https://sabin901.github.io/Football-Analyzer-/

## Architecture

The public application is a static interactive dashboard, with a Python ingestion and analytics pipeline running in GitHub Actions. This is the deployed backend for the Pages site; GitHub Pages itself cannot execute FastAPI. No paid host, API key, database, or browser credential is needed.

FastAPI additionally serves the identical built dashboard and JSON snapshots, exposes live backend calculation endpoints, and retains the historical research app. It can be run locally or with the existing Docker configuration. This release does not create a separate public FastAPI host.

## CI and refresh

`.github/workflows/deploy.yml` runs for pull requests, main pushes, manual dispatches and every six hours at minute 17 UTC. Pull requests test and build only. Production runs test, fetch the current season, preserve last-good data on errors, build, validate, save snapshots and deploy the resulting Pages artifact directly.

GitHub's GITHUB_TOKEN commits do not normally trigger another push workflow. Deployment therefore never depends on the data commit triggering a separate run. Pages must use **GitHub Actions** as its build source.

Source failures appear as workflow warnings and snapshot status. Failed HTTP requests do not overwrite verified scores or move their individual verification timestamps. Current results are supplemented from ESPN for scheduled dates in the last 14 days. An older source gap remains visible rather than silently fabricated. League and season source files are independently validated.

The public Refresh button reloads the published snapshot; it does not trigger provider ingestion. To request immediate ingestion, run the workflow manually or run the complete refresh sequence in the README locally (results, squads, forecasts, then the build).

## Backend endpoints

- `/api/health`: backend health and whether the dashboard was built.
- `/api/dashboard/{league}/{season}`: normalized snapshot and calculated table.
- `/api/dashboard/{league}/{season}/predict?home=...&away=...`: experimental scenario, validated against that league-season.
- `/research`: existing historical research UI, with original API routes retained.

League IDs: PL, PD, SA, BL1, FL1. Season IDs: `2026-27` etc. Invalid IDs return 400, missing snapshots 404, and insufficient prediction samples 422.

## Verification and rollback

Build with `python src/build_site.py`; run `python -m unittest discover -s tests -v` followed by `npm test`, `npm run format:check` and `python -m black --check .`. Check all five league logos, all 12 workspaces, mobile layouts, browser history and downloads after deployment. Publication tests verify every entry point script and bundled league asset.

To roll back code, revert the release commit and run the deployment workflow. Snapshots and their provenance are versioned in Git. For an upstream outage, keep the last successful snapshots and inspect the coverage warnings; do not reset freshness timestamps to conceal the outage.
