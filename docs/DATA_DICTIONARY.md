# Data dictionary and coverage

Footlyzer is a public analysis tool with an explicitly licensed historical archive and an optional private browser workspace. It is not an official league service or a current scouting database.

## Results

OpenFootball (CC0) supplies dates, home and away clubs, scheduled fixtures and full-time scores. Null goals mean missing results, not zero goals. Result IDs use league, season and both teams. Provider rows outside the season or containing invalid scores are quarantined with reasons. No restricted provider supplements are used.

Tables are computed from recorded results: three points per win and one per draw; sorted by points, goal difference, goals for and name. These are match points and sample ranks, not independently verified official standings. Administrative deductions, disciplinary outcomes and league-specific tie-breaks may differ. Clean sheets include only recorded matches. Form is ordered oldest to newest. Comparisons use the same filters and match-weighted league averages.

## Event archive

The Pappalardo/Wyscout research dataset covers 2017/18 in England, Spain, Italy, Germany and France: 1,826 matches and 3,071,395 source events. It is licensed CC BY 4.0. These player records are historical, including club membership and positions. They are not current squads or transfer recommendations.

Player and team IDs come from the source. A transfer creates separate player-club records. Positions use the catalogue's GK, DF, MD and FW groups; unknown remains unknown. Substitute status is never interpreted as a position.

- Non-penalty shots and goals exclude penalties. Match shot maps include penalties.
- Pass completion uses the provider's accurate tag. Key passes / assists count events with either tag once. They are provider labels, not an independently reconstructed chance chain.
- Progressive passes are completed passes that move at least 10 display units closer to the centre of the goal and finish in the attacking 40% of the pitch.
- Progressive accelerations apply the same geometry to the provider's acceleration events. These are not all ball carries.
- Interceptions and defensive duels are event counts, not success rates.
- Regulation minutes are estimated from lineups, substitutions and dismissals; stoppage time is excluded. Unknown participation is not guessed. Per-90 rates require positive minutes.
- Percentiles compare eligible player-club records in the same broad position and season. They describe activity, not skill or suitability for recruitment.

Provider xG, possession, pressures, recoveries and explicit pass recipients are unavailable in this public archive. They remain null or are omitted from the interface. Goals from own goals are not credited to a shooting player. Counts of located shots can differ from match goals.

Coordinates are normalized 0–100 in the source, with the acting team attacking right, then rescaled to 120 by 80 display units. These units are not measured metres. Missing coordinates do not become (0,0).

## Private workspace

The CSV template contains id, period, second, team, player, action, x, y, end_x, end_y and outcome. Use one match per project. Import coordinates already normalized to an attacking-right frame. Periods are 1–4; seconds start at zero within each period. Empty coordinate pairs are supported. Event IDs must be unique.

User data is not uploaded or independently verified. A SHA-256 fingerprint identifies the imported bytes but does not prove their truth or licensing. Analyst observations, interpretations and recommendations remain distinct from provider evidence.

## Downloads

The JSON manifest lists every published league-season. Snapshot JSON includes the source URL, license, source fingerprint, fetch time and quality record. The SQL warehouse contains only the two approved public sources. Source attribution and transformations are recorded in source_registry.json and the [attribution page](ASSET_CREDITS.html).
