# Data quality and publication policy

The public build allows OpenFootball CC0 results and the CC BY 4.0 Pappalardo/Wyscout research archive. A reachable endpoint is not treated as permission to republish. ESPN, Football-Data.co.uk and the restricted StatsBomb archive are excluded from this release's public package.

## Checks and limits

Results are checked for season membership, valid dates and integer scores, team count, duplicate fixtures and future completed matches. Invalid rows are quarantined without silently rewriting their dates. The quality record is tied to a digest of the normalized results. These checks detect structural problems; they do not independently confirm that a score is true.

The free community source can lag. The latest recorded result date and missing past fixtures are shown separately from the fetch time. Refreshes are attempted every six hours; failures retain the last available snapshot and display its age. A recent download is not a live feed.

Official standings are not independently verified. Tables show computed match points, without claiming official disciplinary deductions or competition tie-break rules. The 2019/20 Premier League source contains out-of-season dates; rejected rows remain visible in the quarantine report rather than being silently repaired from a restricted feed.

## Event checks

Archive files are pinned by checksum; their Figshare records must retain the approved license. Match and event IDs, team membership, unique events, finite coordinate ranges and heatmap mass are validated. Event IDs are retained in shot tables. Grid counts must sum exactly to the number of located events; player transfers remain separate records.

No current squad, tracking data, possession or provider xG is inferred from these historical events. Regulation minutes have documented limitations. Historical per-90 profiles should be interpreted alongside sample size, role, possession and opponent context.

## Forecast gate

Upcoming probabilities require a source snapshot and quality record at most 36 hours old, an intact result digest, a complete round-robin schedule, no quarantined rows and no past fixture missing a result. Otherwise probabilities are withheld. Historical evaluations may remain available with their source limitations. These gates do not establish a betting edge.

## Publication and reproducibility

The build uses a fresh staging directory and validates provenance before copying data. Retired assets cannot leak through a directory overlay. Generated site files are not maintained as source code. The manifest records the code revision, data revision and build time. Automated checks cover import boundaries, temporal leakage, probability scores, source contracts and public packaging.

The current public package excludes restricted legacy datasets. Historical Git commits may still contain prior data; this release does not rewrite repository history or certify removal from third-party caches.
