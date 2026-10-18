# Forecast model card

Version: `venue-poisson-365d-prior8-v1`. Research model, not betting advice or an elite-club performance system.

## Question and inputs

Estimate home win, draw and away win probabilities for a league fixture using recorded goals in the preceding 365 days. Home and away scoring/conceding rates are smoothed with eight pseudo-matches at that training window's league mean. The product of the attacking and conceding rates, divided by the corresponding league mean, defines each team's Poisson goal rate. A 0–19 score grid is normalized to obtain outcome probabilities. No shot-based xG enters this model.

An unseen/promoted team receives the league-mean prior for an unobserved venue. Team strings are conservatively normalized; unresolved naming changes can reduce team samples and are not silently fuzzy-matched. Minimum league training sample: 50 matches. Parameters are fixed, not selected by optimizing the displayed evaluation results.

## Validation protocol

- Evaluation fixtures start on 1 July 2024. Each fixture uses only training dates strictly before its date, within 365 days. All matches on the test date are excluded, even earlier kickoffs.
- The same fixtures and training windows are used for the rolling empirical home/draw/away frequency baseline (Laplace smoothing), and an equal-probability baseline.
- Report multiclass log loss, summed multiclass Brier score (0–2), and normalized ranked probability score (home/draw/away order). Lower is better. Accuracy is retained in JSON but is secondary to proper probability scores; uniform ties select home deterministically.
- Calibration pools the three outcome probabilities in ten bins. It is a diagnostic, not an independently fitted calibration model.
- A seeded 1,000-replicate bootstrap resamples date blocks for the model-minus-frequency log-loss difference. Dependence across dates/seasons remains; intervals are descriptive, not proof of future superiority.
- Evaluation by season and every forecast's training bounds, sample counts and probabilities are downloadable. Source files are corrected snapshots available at import time. This is a reconstructed backtest, **not a vintage-feed replay or prospective test**.

## Future outputs

Upcoming fixtures within 14 days use a single explicit exclusive cutoff date. The season simulation uses 2,000 seeded runs, fixed current strengths and independent Poisson scores for remaining dated fixtures. It sorts by points, goal difference and goals scored, then deterministic team order. Administrative deductions, league-specific head-to-head rules and sporting decisions are omitted. Top-four rank is not synonymous with Champions League qualification. If any unresolved fixture is omitted, finishing-position probabilities are withheld and the remaining points are labelled as a partial scenario. Fixtures with fewer than five home or away venue observations carry a limited-sample label; the eight-game prior weight is shown explicitly. These sample labels describe data volume, not calibrated confidence.

The 10th–90th points range expresses simulation variability, not total real-world uncertainty. Long-horizon projections have not been independently validated.

## Known weaknesses

No lineups, injuries, transfers, fatigue, travel, managerial changes, market prices, opponent-strength adjustment, continuous tracking, event quality, correlated score correction or changing team strengths. Early-season and promoted-team priors can be badly wrong. Missing source results and team-name changes affect training. Historical provider corrections may improve data relative to what was known before kickoff. Schedule dates may move; fixture kickoff times are not guaranteed.

## Reproduce

```bash
python src/import_open_history.py   # one-time CC0 backfill, cached
python src/dashboard_data.py       # refresh current schedules/results
python src/forecast_lab.py         # build evaluations and future outputs
python src/build_site.py
python -m unittest discover -s tests -v
```

Inspect `data/workbench/backtest_<league>.json`, `forecast_<league>.json` and the league-season source snapshots in `data/live/`. Raw ESPN response caches are local and excluded from Git. See DATA_DICTIONARY.md for the data boundaries.
