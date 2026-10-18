# Spatial analysis method

Historical activity maps use the CC BY 4.0 Pappalardo/Wyscout 2017/18 event archive. The source uses 0–100 coordinates in the acting team's attacking-right frame. We rescale to 120 by 80 display units, not measured metres. Halves are not rotated a second time.

Each valid event start location enters exactly one of 96 cells (12 columns by 8 rows). Boundary coordinates remain in the outermost cell. Missing or invalid locations are excluded and counted; they are never replaced with zero. There is no interpolation or smoothing. The displayed grid conserves the selected event count.

Choose season or match, team, player, action and period. Action categories are mutually exclusive: pass, acceleration, shot, defensive duel, interception/clearance, touch and other action. The provider can record multiple actions in a possession; all actions are not unique touches. Penalty shootouts are excluded.

Count mode shows recorded events per cell. Share mode divides by all selected located events. Comparisons share the same color scale. Different match counts, minutes, roles or team possession can still confound comparisons; equal percentages do not imply equal involvement. Numeric cells and downloadable CSV/SVG supplement the visual colors.

These are action locations, not continuous tracking, time spent in a zone, distance covered or off-ball positioning. The archive is historical and cannot establish current player suitability. The private workspace uses the same exact-bin approach on user-supplied 0–100 coordinates and requires the importer to normalize direction.

Data attribution: Pappalardo and colleagues (2019), Wyscout research data, CC BY 4.0. See [full attribution and transformations](ASSET_CREDITS.html).
