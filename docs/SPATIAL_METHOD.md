# Player and team heatmaps

Footlyzer maps actual recorded event locations from StatsBomb Open Data. It does not infer positions from results or player photographs.

## What a map measures

Each event with a player, team, period and valid location contributes one count to a 12 by 8 grid. Cells cover 10 by 10 units on the provider's 120 by 80 pitch. We use action start locations. Carries do not trace their paths through intermediate cells. Pass maps count the origin, not the receiving position.

Both teams attack right in the provider's action executing team frame. The second half is not rotated again. These are provider units, not measured metres. The top edge is y = 0. A bright area means more recorded activity, not higher quality.

All located actions include receipts and other event types. A pass and the subsequent receipt are separate events. This total is neither unique touches nor possessions. Defensive actions combine recoveries, interceptions, duels, blocks, clearances and dribbled past events; they are not necessarily successful defensive interventions.

## Filters and comparisons

Choose a historical dataset, the imported season sample or one match, a team, an optional player, an action group and a period. Periods 3 and 4 represent extra time if present. Shootouts are excluded.

Count mode shows raw events per cell. Share mode divides each cell by the number of selected events, so a nonempty map sums to 100 percent. Comparison maps use one shared maximum. Share comparisons describe spatial distributions; counts still depend on minutes, possession and sample size. The comparison selection represents a whole team and is labelled accordingly.

The matches card is the number of team matches in the imported sample, or matches where the selected player has any located action. It does not change with the action or period filter. It is not an appearance or minutes estimate.

## Missing data and boundaries

Missing and invalid coordinates are excluded and counted. Missing coordinates never become the origin. Finite points within a one unit tolerance of the pitch boundary are assigned to the nearest edge cell, with a clamped count. Coordinates further outside are excluded. Exact x = 120 and y = 80 belong to the last column and row. No smoothing creates artificial locations.

Coverage details show quality counts across the full match or dataset before filtering. A sparse or empty selection is displayed as such. Some seasons contain one club or a selected subset of fixtures. All currently available imported archive matches are eligible, but an import failure reduces the mapped sample and is disclosed.

## Reproduction and exports

Run `python src/event_workbench.py` to refresh the historical event archive, then `python src/spatial_workbench.py`. Spatial imports use three workers, atomic writes and resumable files. A SHA256 digest must match the event summary before a spatial file can be published. Changed upstream data requires refreshing the event summary first.

The sparse row schema is `[player_index, period, action_index, cell_index, count]`. Player indices refer to the enclosing players array; cell index is row times 12 plus column. Season aggregation preserves provider player and team IDs, so transfers are separate records. The schema version and source hash invalidate stale match caches.

Grid CSV exports contain counts, shares, filters, identities, sample and attribution. SVG exports retain text, legend, selected filters and source metadata. The accessible grid presents the same values without requiring colour interpretation. Public data files mirror the FastAPI spatial endpoints.

## Limits

These are historical event activity heatmaps. They cannot show distance covered, off ball movement, physical load, defensive compactness or time spent in a zone. Current ESPN summaries have no reliable event locations, so this view cannot truthfully provide current season player heatmaps. Tracking and permissioned video are separate future inputs.

Data attribution: [StatsBomb Open Data](https://github.com/statsbomb/open-data). Consult the provider's terms before additional redistribution or commercial use. Coordinate concepts are also described by [Kloppy](https://kloppy.pysport.org/user-guide/concepts/coordinates/).
