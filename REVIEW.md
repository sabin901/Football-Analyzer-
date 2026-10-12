# Engineering and soccer-analysis review — 12 October 2026

The original project is a promising research prototype. Its strongest feature is the breadth of analytical experiments: xG, xT, player comparisons and Dixon–Coles prediction. The public product fell short of that code because it deployed a different, mostly static page and mixed unrelated datasets without enough context.

## Findings and changes

| Finding | Impact | Resolution in this release |
|---|---|---|
| Pages built one hardcoded league-season; interactive app was local only | Users could not explore the five leagues | Shared interactive dashboard and data contract on Pages and FastAPI |
| 2025/26 default, with no current-season selection | Historical data looked like present-day coverage | Calendar-based 2026/27 selection, three seasons and five leagues |
| Open data had stale results and no freshness distinction | Fresh build timestamps implied fresh football data | ESPN supplementation, per-record provenance, latest-result date and fetch/failure warnings |
| Hypothetical round-robin predictions labeled as fixtures | Confused scenarios with scheduled matches | Separate real schedules and clearly labeled experimental simulator |
| Historical Spanish player data shown beside English standings | Invalid cross-season/competition interpretation | Historical event reports have explicit dates and their own archive |
| Shots-on-target proxy labeled as xG, with overconfident model claims | Users could infer unmeasured chance quality | Current metrics use actual goals; simulator method and limitations are stated; README claims corrected |
| Scheduled bot commit expected to trigger Pages workflow | Refresh could complete without publishing | Refresh, build, verification and deployment in one run |
| No automated data/API contract coverage | Silent corruption and regression risk | Provider, standings, probability, API and packaging tests |
| Dataset keys were inserted into filesystem paths | Invalid paths could reach unintended files | Strict allowlist validation for research dataset keys |

## Soccer analyst assessment

The new version is suitable for exploring results, form and basic team output. Home/away splits, recent windows and per-match rates help make comparisons meaningful, and sample sizes remain visible. It deliberately separates missing results from abandoned matches and real fixtures from simulations.

It is not yet a professional recruitment or opposition-analysis platform. Goals describe output, not the quality or repeatability of chance creation. Serious next steps are event-level data with consistent coverage, position-specific player minutes and per-90 metrics, lineup/injury context, opponent-adjusted form, and calibrated walk-forward forecasts benchmarked on the exact deployment data. These should only be added when a suitable free/licensed source is verified.

The experimental simulator is a deliberately simple, auditable goals baseline. Its percentages have not been validated as calibrated pre-match forecasts. Historical research benchmarks cannot be transferred to it. Do not interpret retrospective points differences as luck or causal evidence.

## Senior engineer assessment

The deployed architecture is appropriate for a small public analytics dashboard: static UI, lightweight precomputed JSON, scheduled server-side ingestion, no exposed credentials, and preserved snapshots. FastAPI uses the same packaged assets and exposes normalized snapshot/prediction endpoints locally. A separate paid backend is unnecessary for these features.

Remaining constraints are explicit: ESPN's public endpoint is unofficial; schedule updates depend on OpenFootball; recent supplementation covers 14 days; calculated standings do not implement league-specific tie-breakers or deductions; and event research remains dependent on historical datasets and optional model training. Source schema changes should fail visibly and retain known-good data.

## Verification

Automated tests exercise zero/missing/future/duplicate scores, season rollover, atomic snapshot preservation, scorer identity, abandoned fixtures, venue/form arithmetic, probability normalization, invalid API input, all five league snapshots and frontend packaging parity. Browser checks cover league and season switches, search/filter controls, comparisons, same-team simulator rejection, and responsive layouts. The final deployment must also pass the GitHub workflow and a live-site smoke test.
