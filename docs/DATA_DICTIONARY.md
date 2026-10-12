# Data dictionary and import scope

This project imports the available data needed for the five-league analysis workflows. It does **not** claim every football API field, every world competition, complete current events, or unlimited free access.

| Layer | Grain / identity | Fields and null policy | Coverage |
|---|---|---|---|
| OpenFootball results | league + season + ordered home/away pair | Date, final goals, round; absent score remains null | Available top-five files from 2010/11 onward; 404s recorded in `history_import.json` |
| Current squads | ESPN player ID + club ID + season | Name, supplied position, age, jersey, optional photo; no invented values | Current-season rosters from returned team lists; expected club count displayed |
| Current appearances | ESPN match ID + player ID + club ID | Starter and every supplied numeric player box-score statistic | Completed imported summaries only; no reliable minutes; no per-90 |
| Current match reports | ESPN match ID | Teams, score, supplied team box-score fields, lineups, goal/red-card moments | Discovered completed fixtures on schedule dates plus the last 14 calendar days |
| Historical events | StatsBomb match ID / event UUID | Entire event file processed; source SHA-256, source update marker, event count | All available men's Premier League, La Liga, Serie A, Bundesliga and Ligue 1 match selections in the provider catalogue |
| Event player totals | dataset + player ID + team ID | Estimated minutes, position group, non-penalty shots/goals/xG, key passes, pass counts, progression, pressures, recoveries, interception/tackle attempts | Imported event matches only; not assumed to represent a whole league |
| Shot detail | StatsBomb event UUID | Provider x/y, provider xG, outcome, minute, player/team, penalty/body part/play pattern | Historical imported shots; shootouts excluded |
| Forecast audit | league + date + home + away | Probabilities, actual outcome, training cutoff and samples | Rolling tests from July 2024; corrected source snapshots |

### Definitions that matter

- Historical player **npxG** uses the provider's shot xG and excludes penalties. It is not the legacy project-trained xG model. Match shot-map totals include penalties.
- Shot coordinates retain the original provider values. Two imported corner shots have x=120.2, just beyond the nominal 120-unit touchline; they are not clamped or discarded. Import validation permits a one-unit boundary tolerance and rejects nonfinite or grossly out-of-range coordinates.
- Historical minutes are estimated from Starting XI, substitution and dismissal events. Regulation clock is capped at 90; extra-time clock at 120. Stoppage time is excluded. A player's position group is the group accumulating most estimated minutes across appearances, not a precise tactical role.
- Progressive passes/carries move at least 10 units closer to the goal at (120,40), finishing at x ≥72. Passes must be completed. This is a project definition, not an industry standard.
- Key passes count `shot_assist`. Pressure counts do not measure successful pressures. Interceptions and tackles count tagged attempts, not a guaranteed successful regain. Recoveries exclude explicitly failed recoveries.
- Per-90 values require positive estimated minutes. Percentiles compare the same position group in one dataset above the selected threshold; at least five eligible peers are required. Higher event activity is not universally better. Provider-selected matches create substantial selection bias.
- Player identities are **not** joined across ESPN and StatsBomb. Different IDs, dates and samples remain separate. Multiple clubs create multiple player records.
- Results tables use points/GD/GF ordering and omit deductions; they are calculated tables. The curtailed French 2019/20 season's unplayed fixtures are marked cancelled.

### Sources, rights and update policy

[OpenFootball](https://github.com/openfootball/football.json) provides CC0 schedules/results. [ESPN](https://www.espn.com/soccer/) provides the public unofficial current feed without credentials; public access is not an open redistribution/commercial license. Provider terms apply and availability can change. This repository is a research portfolio; review rights before commercial distribution. No videos or media articles are copied into the data warehouse.

[StatsBomb Open Data](https://github.com/statsbomb/open-data) is made available for research and football analytics interest. The repository requests source attribution and its logo on published analyses. The event lab identifies StatsBomb and displays its supplied logo. Review the provider's LICENSE.pdf before using the data outside that scope. The data's license is independent of the code license. We do not ingest paid feeds or claim free tracking coverage.

Current data refreshes with the six-hour deployment schedule. Cached older summaries are rechecked after 30 days, recent finals every six hours, squads daily. Import errors are surfaced; last-good match summaries remain available. Historical imports are explicit, resumable backfills: rerun them to discover new releases or source corrections. Large raw event files are processed into compact research aggregates rather than committed wholesale. The complete competition catalogue is recorded; only the five requested men's leagues are imported into the event workspace.

### Rebuildable SQL warehouse

`python src/warehouse.py` rebuilds `data/football.sqlite`; deployment copies it into `site/data/football.sqlite`. Tables: `results`, `player_appearances`, `event_players`, `shots`, `metadata`. Provider IDs remain strings for ESPN and integers for StatsBomb. `stats_json` retains variable player box-score fields; missing keys are not zero. Use SQLite's JSON functions carefully and never divide current player totals by invented minutes.

The current-workbench envelope timestamp records a pipeline build. Each squad and match summary separately retains its actual HTTP acquisition timestamp, including across cache reads; the Match centre shows the selected summary timestamp. Cached records are not described as newly acquired merely because the page was rebuilt.
