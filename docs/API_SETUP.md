# Optional current-season feed

Footlyzer remains hosted exclusively on GitHub Pages. GitHub Actions fetches and validates data; the browser only reads same-origin published files. No API key is sent to visitors.

## Activate the free delayed feed

1. Register the Footlyzer application at https://www.football-data.org/client/register and review the provider terms. Use the free plan; no paid upgrade is required.
2. In this repository, open Settings → Secrets and variables → Actions → New repository secret.
3. Name the secret `FOOTBALL_DATA_API_KEY` and paste the token as its value. Never commit it or put it in browser code.
4. Run “Validate, refresh and deploy” from the Actions tab, or wait for the next hourly schedule.
5. Check the “Refresh optional delayed provider” step. The public manifest's `current_provider.active_leagues` lists successfully activated competitions. The current-season source label changes to Football-Data.org only for validated leagues.

Requests are separated by at least 6.2 seconds to respect the free plan's ten calls per minute. Scores and schedules are delayed. Hourly Actions jobs may start late; this is not a live scoreboard. Current events, tracking, injuries and shot xG are not supplied by this integration.

## Publication and failure handling

The adapter checks competition and season identity, final scores, duplicate fixtures, team membership and table arithmetic. Only `FINISHED` scores count as results. In-progress scores are never converted to completed results. Upcoming model output is withheld if the schedule is incomplete, past results are missing or the provider table does not reconcile.

Application-specific provider snapshots are generated under ignored `.artifacts/current-provider/`. They are not committed to the open archive or the separately versioned CC0 data branch. Provider data is governed by the subscription terms, not CC0. The published interface displays the required attribution. A provider failure falls back to the labelled community snapshot; it does not claim a successful live refresh.

Historical evaluations and the downloadable SQL warehouse remain based on the openly licensed archives. When enabled, current provider results replace overlapping current-season rows for upcoming forecasts. They do not rewrite the historical evaluation. Provider-fed forecasts do not yet have a persistent prospective record; the UI explicitly identifies that limitation.

The token has not been tested against a real account until it is configured and a production run succeeds. Synthetic contract tests verify the parser and failure behavior, not provider availability or account entitlement.

## Disable or cancel

Remove the repository secret and rerun the deployment workflow to remove the provider overlay from the published site. Do this before cancelling the provider subscription: the provider terms require discontinuing use after cancellation. Historical open archives remain available. Team graphics need separate permission and are not fetched by this adapter.
