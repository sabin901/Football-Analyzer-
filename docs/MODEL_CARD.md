# Forecast model card

## Intended use

Experimental football outcome probabilities for learning and analysis. No reliable live prediction edge, betting profitability or club decision benefit has been demonstrated. Forecasts exclude injuries, lineups, player quality, tracking, weather and market odds.

## Primary model

The venue Poisson model uses results from the preceding 365 days, strictly before each prediction date. Eight league-average pseudo-matches shrink each venue rate. Home and away goal counts are independently Poisson distributed. The score grid includes 0–19 goals and is normalized. Promoted teams with little history receive strong prior influence; team sample sizes and prior weights are exposed.

The public model version is venue-poisson-365d-prior8-open-v3. The version change marks the move to exclusively CC0 result inputs. Old restricted-source forecast logs are not represented as evidence for this model.

## Fixed challengers

- League frequency: smoothed home/draw/away frequencies from the same 365-day training sample.
- Equal probabilities: one third per outcome. Tied classification scores use fractional credit, not an arbitrary home-win tie-break.
- Elo / Davidson: initial rating 1500, K=20, home advantage 70, draw parameter 0.7. Results on the same calendar date update ratings simultaneously; all prediction-date results are excluded.
- Fitted attack/defence Poisson: a 730-day training window, exponential half-life 180 days, ridge penalty 2 on team parameters, monthly fits using dates strictly before month start. Unknown teams use zero team effect. Fitting failure stops the build rather than substituting a successful-looking estimate.

Parameters are fixed in code before reporting this comparison. They are not optimized against the reported evaluation seasons. A challenger is not automatically promoted when it wins a retrospective comparison. No licensed odds benchmark is available in this free release; outperforming simple baselines is not outperforming betting markets or commercial systems.

## Evaluation

Rolling-origin evaluations start in July 2024. Each match excludes all same-day and future results. All available model probabilities are evaluated on the same fixtures. Downloadable rows include dates, training cutoffs and the fitted challenger's training end.

Log loss, three-outcome Brier score (range 0–2) and ranked probability score (outcome order home, draw, away) are reported. Lower is better. Pooled and outcome-specific calibration show predicted and observed frequencies. Season and limited-sample cohorts are available in JSON.

Model-minus-comparator log-loss differences have descriptive 95% intervals from 1,000 date-block bootstrap replicates, seed 901. Within-date dependence is preserved. Intervals are not adjusted for trying multiple comparisons, do not represent all sources of uncertainty and do not establish future superiority.

Backtests use corrected community results available now. Historical source delays and corrections cannot be reconstructed; this is not an as-known-at-the-time dataset.

## Prospective record

The first forecast for a model, fixture and date is frozen before the fixture date. Rescheduled and administrative results are excluded from settlement. Settled results receive accuracy, log loss, Brier and RPS. With no settled sample, scores remain null. A new source/model version starts its own record. Publishing timestamps alone are not independent third-party certification.

## Publication conditions

A complete schedule, no missing past results, no quarantined rows, a matching quality digest and fresh inputs are required. The current open source may fail these checks; withheld forecasts are intentional. See the [quality policy](DATA_QUALITY.html). Official standings and league disciplinary decisions are not independently verified.
