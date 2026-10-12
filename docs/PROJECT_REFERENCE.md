# Project reference

Maintainer reference for the Footlyzer release reviewed on 12 October 2026. This records delivered work, implementation choices and possible next steps. The README is the user introduction; setup and maintenance instructions live in the [developer guide](DEVELOPMENT.md).

## Delivered work

- Five league result workspaces with season selection, calculated tables, recent form, venue splits, match filters and team comparisons.
- Current squads, imported player appearances, available lineups, match statistics and exportable opposition briefings.
- Historical event imports with shot maps, cumulative expected goals, player profiles and positional comparisons. Provider identities and historical seasons remain separate from current summaries.
- Player and team heatmaps built from recorded event coordinates, with count and event share modes, common comparison scales, numeric grids and CSV or SVG exports.
- A goals based Poisson forecast pipeline with strict date cutoffs, rolling evaluation, baseline comparisons, probability scores, uncertainty analysis and downloadable prediction audits. The matchup simulator and older research models remain separate.
- A queryable SQLite warehouse, data dictionary, source provenance, coverage indicators and explicit missing values.
- Twelve responsive workspaces, local league logos, consistent Lucide icons, keyboard focus states and reduced motion support.
- A dedicated historical research library for France versus Croatia in 2018 and Arsenal in 2015/16, with report previews, downloads and links into the archive.
- Shared frontend formatting and export helpers, a request cache that rejects stale responses after refresh, and content hashed assets that prevent mismatched browser bundles after deployment.
- Automated checks, scheduled data refresh, preservation of usable snapshots on source failure and GitHub Pages deployment.
- Documentation of data contracts, statistical assumptions, spatial methods, source rights, asset credits and portfolio development.

## What the project uses

| Area | Current choice | Where to verify it |
| --- | --- | --- |
| Browser interface | Plain JavaScript, HTML, CSS and SVG; no frontend framework or npm runtime dependencies | `frontend/`, `package.json` |
| Data and analysis | Python, pandas, NumPy and StatsBomb tooling; additional modelling and plotting dependencies support research modules | `requirements.txt`, `src/` |
| Local service | FastAPI and Uvicorn; research endpoints are distinct from the public static site | `app.py` |
| Queryable export | SQLite warehouse built from the imported snapshots | `src/warehouse.py` |
| Public hosting | Static GitHub Pages artifact built in GitHub Actions | `.github/workflows/deploy.yml` |
| Release checks | Python unittest, Node's test runner, Prettier and Black | `tests/`, `package.json`, `requirements-dev.txt`, `pyproject.toml` |
| CI runtimes | Python 3.12 and Node 22 | `.github/workflows/deploy.yml` |
| Branding | Locally bundled league assets and Lucide icons with provenance | [Asset credits](ASSET_CREDITS.md) |

The dependency manifests are authoritative for versions. GitHub Pages does not execute Python or expose a public FastAPI server. No paid provider or API credential is required for the current ingestion sources; this does not remove their individual usage terms.

## Verification record

The release checks recorded 42 passing Python tests and 10 passing frontend tests. Desktop and mobile review covered all twelve workspaces, five league selections, navigation, historical heatmaps, research reports and exports. The deployed page was checked after the asset versioning fix. These are release observations, not a promise that every future provider response will be complete.

Use the developer guide's commands to establish the current test results. Dataset counts are intentionally omitted here because scheduled refreshes change them; inspect the published coverage and manifests instead.

## What to use next, and why

Keep the existing architecture for the current public dashboard. New dependencies or providers should solve a demonstrated limitation rather than add a technology badge.

| Priority | Next step | Required evidence |
| --- | --- | --- |
| Football interpretation | Write original match and opposition analyses using the existing exports | A clear decision, limitations, permitted video references and feedback from an analyst or coach |
| Current spatial coverage | Evaluate an authorized event or tracking source before connecting one | Verified coverage, rights, latency, provider identity mapping and coordinate tests |
| Prediction quality | Log predictions before matches and review performance over time | Untouched outcomes, calibration, comparison with baselines and a reproducible audit |
| Player comparisons | Add role, possession, game state and opponent context where supported | Defensible peer groups, reliable denominators and documented missing values |
| Reporting workflow | Produce a stakeholder report in Excel or Power BI from the same warehouse | Reproducible calculations and feedback from the intended reader |
| Private club use | Assess a hosted service only if private data or multiple user roles are needed | Access controls, monitoring, recovery, rights review and measured workload needs |

These are future options, not delivered features or promises of professional club equivalence. Free sources do not currently provide comprehensive current events, reliable current minutes, injuries or continuous tracking.

## Reference library

- [Developer guide](DEVELOPMENT.md): local setup, code map, data flow, editing, checks and refresh commands.
- [Deployment](https://github.com/sabin901/Football-Analyzer-/blob/main/DEPLOYMENT.md): production workflow, backend routes, rollback and browser cache consistency.
- [Data sources](https://github.com/sabin901/Football-Analyzer-/blob/main/DATA_SOURCES.md): active providers, attribution and alternatives previously assessed.
- [Data dictionary](DATA_DICTIONARY.md): record grain, field definitions, joins and coverage.
- [Forecast model card](MODEL_CARD.md): training assumptions, evaluation and known weaknesses.
- [Spatial method](SPATIAL_METHOD.md): coordinates, aggregation, denominators and interpretation.
- [Project comparison](PROJECT_REVIEW.md): comparison with other public work and remaining gaps.
- [Application guide](APPLICATION_GUIDE.md) and [career research](CAREER_RESEARCH.md): relevant roles and skill expectations at the time of research.
- [Portfolio playbook](PORTFOLIO_PLAYBOOK.md): original case studies and reproducible evidence for interviews.

## Portfolio review route

1. Demonstrate a league comparison and explain the venue split and sample size.
2. Compare historical heatmaps with a common scale, export the map and inspect its numeric grid.
3. Explain the forecast baseline, date cutoff and evaluation before showing future scenarios.
4. Reproduce a finding from the warehouse using SQL.
5. Connect an original football conclusion to the evidence, its limitations and the implementation you can explain unaided.

The project provides evidence of data engineering, statistical evaluation, visual communication and frontend development. Hiring decisions still depend on analytical judgement, communication and the requirements of the role.
