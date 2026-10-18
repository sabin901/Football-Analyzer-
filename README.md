# Footlyzer

Explore football results, compare teams and players, and build an analysis with the evidence in view.

Footlyzer brings together **Premier League, La Liga, Serie A, Bundesliga and Ligue 1** results with current squad summaries and a separate archive of historical match events.

**[Open Footlyzer](https://sabin901.github.io/Football-Analyzer-/)** · [Report an issue](https://github.com/sabin901/Football-Analyzer-/issues)

Use it in your browser on desktop or mobile. No installation, account or API key is required.

## What you can explore

- **Leagues and matches:** recorded results, schedules, calculated standings, recent form and home or away performance.
- **Teams and players:** team comparisons, current squads, imported appearances, available lineups and match statistics.
- **Match analysis:** opposition briefings, historical shot maps, expected goals charts and player profiles.
- **Heatmaps:** historical player and team action locations, with match, period and action filters and a shared comparison scale.
- **Forecasts:** experimental match probabilities with historical evaluation, baseline comparisons and a prospective prediction record.
- **Exports:** tables, heatmaps, reports and prediction records for your own analysis.

## Get started

1. Open **League overview** and choose a league and season.
2. Use **Matches & results**, **Team comparison** or **Players & squads** to explore your question.
3. For spatial analysis, open **Player & team heatmaps** or **Event & scouting lab** and select a historical dataset. These have their own competition and season coverage.
4. Check **Data & methodology** for sources, sample sizes, missing data and freshness before drawing conclusions.
5. Use the export controls in each workspace to save the available results.

Personal project reviews, career research and application notes stay in the repository; the public build publishes only product data, attribution and methodology documents. The legacy research interface is available locally at `/research` when running the API.

## Where the data comes from

| Source | What it provides |
| --- | --- |
| OpenFootball | Schedules and archived results |
| ESPN public endpoints | Current results, squads and available match summaries |
| StatsBomb Open Data | Historical match events, shot locations and expected goals |

Coverage varies by league, season and provider. Some historical datasets cover selected teams rather than a full league. OpenFootball data is CC0; ESPN and StatsBomb have separate terms. See [data sources and attribution](DATA_SOURCES.md) and [asset credits](docs/ASSET_CREDITS.md).

Current data is scheduled to refresh every six hours. The dashboard's **Refresh** button reloads the latest published snapshot. Check the latest recorded result as well as the fetch time: a recent fetch does not guarantee complete results. If a source fails, the last available snapshot is retained with a warning.

## Reading the analysis

Heatmaps show recorded historical actions, not continuous player movement or time spent in an area. Comprehensive current match events, reliable current player minutes, injuries and tracking data are not available.

Calculated standings may differ from official tables because administrative deductions and some competition tie breakers are omitted. Forecasts use recorded goals and express uncertain outcomes; they do not account for every factor affecting a match.

For metric definitions and assumptions, read the [data dictionary](docs/DATA_DICTIONARY.md), [heatmap method](docs/SPATIAL_METHOD.md) and [forecast model card](docs/MODEL_CARD.md).

## Feedback

Found a missing result, an unexpected calculation or a display problem? [Open an issue](https://github.com/sabin901/Football-Analyzer-/issues) with the workspace, league, season and steps needed to reproduce it. Include the source or fixture when reporting a data discrepancy.

## Public release quality

Overall league tables preserve reconciled provider ranking and administrative points adjustments. Results are cross-checked against Football-Data.co.uk, with reviewed source corrections and visible coverage. Forecasts are experimental, gated on current reconciled inputs and recorded prospectively before match day. Unvalidated finishing projections and the separate simulator are not published. See [data quality](docs/DATA_QUALITY.md).

To refresh verification, run `python src/data_quality.py` for the current season or add `--all` for the historical archive. Rebuild forecasts and the site afterward.
