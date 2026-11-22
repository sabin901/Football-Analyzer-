# Data refresh and presentation audit

Reviewed 22 November 2026. This is an audit record, not a live status page.

## Finding

The refresh and deployment pipeline runs successfully, but the active community source does not provide current results. All five 2026/27 feeds stop at 20 September 2026. Repeated downloads update acquisition timestamps without adding missing scores. The live interface correctly labels the results as out of date and withholds upcoming forecast probabilities.

The initial inspected deployment was [run 44979340042](https://github.com/sabin901/Football-Analyzer-/actions/runs/44979340042), built at 03:12 UTC on 22 November (21:12 CST on 21 November). Its manifest identifies code revision `215387bbd8a4eb7da2af1ffeff5ebbc3d753366f` and data revision `d883fcbefeb3819817591b3c8ea299e63174e9b6`. All twelve recent scheduled runs inspected succeeded. The workflow requests hourly execution, but observed starts were several hours apart; scheduled execution is not a guaranteed hourly service.

## Current season coverage

| League | Recorded results | Past fixtures without results | Latest recorded result |
| --- | --- | --- | --- |
| Premier League | 50 | 60 | 20 September 2026 |
| La Liga | 69 | 51 | 20 September 2026 |
| Serie A | 50 | 64 | 20 September 2026 |
| Bundesliga | 36 | 52 | 20 September 2026 |
| Ligue 1 | 45 | 51 | 20 September 2026 |

These 278 gaps are missing scores in the published schedule, not independently verified assertions that each fixture took place. Current source responses exactly matched the published normalized fixtures and SHA256 fingerprints. This rules out a failed copy or stale browser bundle as the cause of the missing scores; it does not independently establish the truth of every community score or schedule date.

The optional delayed provider is inactive: the public manifest has no active provider leagues, and the workflow logs say Football-Data.org is not configured. No provider credential was added during this audit.

## Checks completed

- Downloaded all 76 published league-season snapshots. Verified league and season identity, unique fixture pairs, score nullability, result counts, latest result dates, quality digests, manifest parity and standings recalculated from the fixtures. Goal totals balance and appearances equal twice the recorded match count.
- Checked all five historical archive summaries: 1,826 matches, 3,071,395 events and 2,698 player-club records. Verified player totals, unique match IDs, heatmap coordinate bins and conservation of located event counts. Inspected first and last match detail pairs for each league against their event fingerprints. The local suite additionally checks all archive match spatial totals.
- Audited all 3,733 published backtest rows: venue and challenger training end before the fixture date; every model probability vector is finite, bounded and sums to one. All five current forecast files withhold upcoming probabilities because of missing past results. This checks temporal and numerical contracts, not independent model performance or source accuracy.
- Downloaded the published SQLite warehouse. SQLite integrity check passed; no invented shot xG values were populated.
- Reviewed all ten workspaces in the public browser at desktop and mobile widths. No JavaScript errors, blank workspaces, broken images or page-level horizontal overflow were observed. Current result warnings and historical archive labels are visible. New visitors default to a more complete historical season rather than silently treating incomplete current results as complete.
- Checked league selection, workspace navigation and source context. Verified the corrected historical missing-result and cancellation filters locally. A browser-generated results CSV contained the 279 played matches without turning cancellations into scores.
- Local validation: 81 Python tests and 20 frontend tests passed. Formatting checks passed. Python tests used UTF8 mode on Windows to match CI's text encoding. A browser regression journey covers the cancelled-season presentation.

## Corrections made

Ligue 1's curtailed 2019/20 season previously showed 101 unplayed fixtures as missing results. The [LFP decision of 30 April 2020](https://www.lfp.fr/assets/20200430_PV_Conseil_Administration_LFP_e824a457fa.pdf) ended that season. The known archive with 279 results now labels its 101 remaining fixtures as cancelled, with an explicit competition note and source link. Dates, scores, original source fingerprint and acquisition time are preserved. The calculation remains match points, not the official points per game ranking.

The importer applies the annotation to restored snapshots and subsequent archive imports. Quality records exclude cancelled, postponed and abandoned fixtures from missing-result counts, consistently with the dashboard. The match filter now explicitly includes cancellations.

Successful current-season fetches with missing past results or quarantined rows now emit GitHub Actions warnings containing the gap count and latest result date. A green deployment can still publish useful historical data, while its logs clearly expose incomplete current coverage.

## Remaining source limitations

- Current results: all five leagues still have the gaps listed above. The audit and status correction do not acquire the absent scores. A working authorized current source is needed to close these gaps; page refresh cannot do so.
- La Liga 2024/25 and Serie A 2024/25 each have ten missing scheduled results in the archive. Ligue 1 2025/26 has one. The scheduled refresh currently targets the current season, so historical corrections require an archive refresh.
- Premier League 2019/20 has 66 quarantined rows with invalid source dates; 314 recorded results remain. No dates were guessed or silently repaired.
- Historical events and player profiles describe 2017/18. They are fixed research data and should not refresh into current squads. Current player events, injuries, tracking and provider shot xG remain unavailable.
- No second provider or official table was used to verify every score. Passing internal checks is not independent football verification.

Recheck the live Data & methodology view and workflow logs for later changes. The README was not changed by this audit.
