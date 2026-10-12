# Data sources and attribution

## OpenFootball

https://github.com/openfootball/football.json

CC0-1.0. Provides season schedules and historical full-time results. A community dataset with variable update latency. Each snapshot contains its exact source URL. Schedule dates are day-level; the dashboard does not infer a timezone for unzoned kickoff times.

## ESPN public scoreboard

https://www.espn.com/soccer/scoreboard

Public endpoint used: `https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates=YYYYMMDD`.

No key is currently required. This is an unofficial endpoint without a documented stability or availability guarantee. ESPN terms apply to supplemented records; they are **not** relabeled CC0. We retain factual score/status fields, the precise source URL, and verification time in each supplemented record. Requests are server-side, limited to relevant scheduled dates over the last 14 days, on a six-hour cadence. Failures retain verified cached results.

Team aliases are explicitly mapped. Unknown teams are not fuzzy-matched. Home/away identity and scheduled-date proximity must agree. In-progress scores never enter the finished-results table or prediction model. Abandoned and postponed fixtures remain scoreless.

## Other free sources assessed on 12 October 2026

OpenLigaDB: https://www.openligadb.de/ — documented, no authentication, ODbL. Its Bundesliga and La Liga data had recent results; the Premier League feed was older, and no equivalent current Serie A/Ligue 1 coverage was established. It is not mixed into the current dataset.

football-data.org: https://www.football-data.org/coverage — free access exists but requires registration/key. The old optional importer is retained; no account or secret has been created.

football-data.co.uk: https://www.football-data.co.uk/data.php — the source's published use restrictions exclude automated commercial/data-training products. The new scheduled pipeline does not fetch it. Legacy imported research files remain in the repository and need separate use-rights review before commercial reuse.

## Historical research

StatsBomb open data: https://github.com/statsbomb/open-data . Historical event reports retain their competition/season context. Follow StatsBomb's attribution and use terms for those assets. Current event-level xG, tracking, injuries and player scouting are not supplied by the results feed.


## Expanded analyst workbench (12 October 2026)

See [the full dictionary](docs/DATA_DICTIONARY.md) for grains, sources, caching, missing values and metric definitions. ESPN public API squad/summary endpoints now support current player appearance totals, lineups, team box scores and goal/dismissal moments. These do not include reliable minutes or current shot-based xG. Provider terms remain distinct from OpenFootball's CC0 license.

The historical event importer processes all available men's top-five league match selections in StatsBomb's open catalogue, including the provider's own shot xG. Historical datasets may follow one team or player; an imported match count is not evidence of representative league coverage. Attribution and the provider logo are displayed in the event lab. API player IDs are never joined across providers by name.
