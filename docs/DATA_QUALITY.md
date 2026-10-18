# Data verification and corrections

Footlyzer separates recorded results, provider standings, historical event data and experimental forecasts. No prediction is a fact, and agreement between providers does not guarantee an error-free source.

## Standings

The overall table uses ESPN's published points and rank only after team identities, games played, wins, draws, losses, goals for and goals against reconcile with the result archive. This preserves deductions and the provider's competition ordering. A points adjustment appears beside the total. This is an attributed provider table, not an independently certified league feed.

If the table does not reconcile, Footlyzer withholds competition rank and the table-leader claim. It shows a results summary with match points instead. Home/away splits and team comparisons always show match points; they do not distribute administrative deductions across individual fixtures. Their sample rank is not a league position.

## Results

Scores and dates are checked against Football-Data.co.uk. Unknown team identities, duplicate fixtures, changed scores and changed dates are not silently guessed or overwritten. The data page shows how many records agree, how many have reviewed administrative differences, and where source coverage is incomplete. Recent results can precede the second provider's update.

Verification is tied to a digest of the exact fixtures, dates, scores and administrative outcomes. Changing those inputs invalidates the previous verification. An unresolved score conflict fails publication checks. Missing source responses are labelled unavailable rather than successful.

## Reviewed archive corrections

The October 2026 release records 89 reviewed changes or annotations: 66 wrongly dated July 2020 fixtures; 20 missing Spanish and Italian final-round results from 2024/25; and three administrative-result cases. The record in `data/live/result_corrections.json` retains the previous values, replacements, evidence URLs and review timestamps. The importer refuses to reapply a correction if upstream values change unexpectedly.

- Everton 2023/24: 40 competition points, including an eight-point deduction; 48 match points. [Premier League decision](https://www.premierleague.com/ar/news/4001861).
- Bastia–Lyon, April 2017: awarded Lyon win with no goals added to the table. The 0–0 goals must not be interpreted as a draw. [Contemporary disciplinary report](https://www.lequipe.fr/Football/Actualites/Discipline-defaite-sur-tapis-vert-pour-bastia-contre-lyon-et-trois-matches-a-huis-clos/798557).
- Verona–Roma, September 2020: official awarded 3–0 retained, although the on-field result was 0–0. [FIGC appeal decision](https://www.figc.it/it/federazione/news/respinto-il-ricorso-della-roma-confermata-la-sconfitta-per-3-0-a-tavolino-con-il-verona-ha0usqwf).
- Nantes–Toulouse, May 2026: 0–0 ratified after abandonment. ESPN's archived table had not incorporated the result when checked, so that season's competition ranking is withheld. [Club statement on the LFP decision](https://www.fcnantes.com/articles/article2809.php?num=49229).

Awarded or ratified abandoned matches remain in the result record and are excluded from goal-model training and evaluation. Source notes are available in match rows and CSV exports.

## Forecast release policy

Upcoming experimental probabilities require reconciled current standings, no unresolved score conflicts, no completed result known only to the reference provider, and result and verification snapshots no older than 36 hours. The browser also suppresses expired probabilities. Only fixtures after the current UTC date are shown, because the schedule cannot reliably establish whether a same-day kickoff has already happened.

The first eligible prediction for a fixture date and model version is stored before match day. Its probabilities are not overwritten by later runs. Rescheduled fixtures and administrative results are excluded from scoring. Historical reconstructions and this prospective record remain separate. The record is versioned in Git; it is not an external notarization service.

The separate match simulator and unvalidated season finishing projections are not part of the public product. The research code remains in the repository.

## Event and player data

Historical StatsBomb heatmaps retain exact event counts and provider coordinates. They show action locations, not continuous tracking. Current player totals depend on imported reports and field-level availability; no minutes or per-90 values are invented. See the data dictionary and spatial method for coverage and definitions.

## Source availability

Automated current-source reconciliation runs with each scheduled refresh. Historical checks are rerun explicitly. Errors and stale inputs must stay visible. Public provider endpoints can change; this release does not promise continuous live coverage or access to paid club feeds.

Sources: [ESPN](https://www.espn.com/soccer/), [Football-Data.co.uk](https://www.football-data.co.uk/data), [OpenFootball](https://github.com/openfootball/football.json), [StatsBomb Open Data](https://github.com/hudl/open-data).
