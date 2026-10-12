# Project comparison and remaining gaps

Reviewed on 12 October 2026. This is a feature and method comparison against public documentation, not a claim that we audited other projects' code or measured their accuracy. Libraries and research dashboards have different purposes.

## Where Footlyzer stands

Footlyzer combines current results and squad summaries across five leagues, a historical event archive, spatial exploration, player profiles, forecast validation, exports and a deployed interface. That breadth is useful portfolio evidence. It is not equivalent to a club's operational platform or proof of professional analytical judgement.

| Reference | What its authors demonstrate | Footlyzer comparison |
|---|---|---|
| [Oseko Ashpe football match dashboard](https://github.com/ashpe-osk/football-match-dashboard) | A focused AFCON final report with passing networks, shot maps, statistics and cumulative xG | Footlyzer covers many selectable matches and leagues. We added cumulative xG and spatial maps. The public event lab still presents pass connections as a table rather than a contextual network visualization. |
| [mplsoccer gallery](https://mplsoccer.readthedocs.io/en/latest/gallery/pitch_plots/index.html) | A plotting toolkit with heatmaps, pass networks, positional charts and pitch visualizations | Footlyzer uses interactive SVG grids with accessible tables and exports. The gallery has greater visualization breadth; adding every chart would not by itself improve analysis. |
| [Kloppy](https://github.com/PySport/kloppy) | Standardized event and tracking data across providers | Footlyzer preserves StatsBomb's coordinate frame and separates provider identities. It lacks a general tracking adapter and event to tracking alignment. |
| [socceraction](https://socceraction.readthedocs.io/en/latest/) | Standard action representations and xT, VAEP and Atomic VAEP implementations | This repository contains earlier experimental valuation scripts, but the deployed scouting workspace does not have a validated, integrated possession value model. Event counts and progressive actions must not be described as action value. |

## What this release addresses

- Player and team event activity maps across the imported historical archive, with sample, half and action controls.
- Shared comparison scales, count and percentage modes, numeric grids and portable exports.
- Match xG flow charts with distinct line styles and goal markers.
- One locally bundled Lucide icon family, responsive controls and restrained motion that respects reduced motion preferences.
- Clear page titles, descriptions, canonical URLs, a sitemap and discoverable documentation. SEO titles and descriptions use no hyphens. Hash workspaces remain one main document, so they are not presented as separately indexed pages.

## The most important remaining work

| Priority | Gap | Evidence that would close it |
|---|---|---|
| 1 | Original football interpretation | Three authored case studies with a decision, counterargument, video references where permitted, and feedback from a coach or scout |
| 2 | Current detailed events and tracking | An authorized source with coverage, latency and rights verified; a tested spatial adapter and explicit acquisition timestamps |
| 3 | Role and context adjustments | Role definitions, possession and game state adjustments, opponent strength, age context and carefully chosen peer groups |
| 4 | Prediction validity beyond reconstructed history | Prospective prediction logs, drift review and comparison with stronger preregistered baselines using untouched evaluation periods |
| 5 | A club reporting workflow | A Power BI or Excel report built from the same warehouse and tested with an actual stakeholder |
| 6 | Production engineering at club scale | Authentication and access rules for private data, deployment monitoring, documented recovery, security review and measured concurrent workloads |

The most useful next step for employability is to answer a real football question convincingly and explain the work unaided. More data and more charts cannot substitute for that. No ranking claim or hiring guarantee is justified by a personal project alone.

Read the [application guide](APPLICATION_GUIDE.md), [case study playbook](PORTFOLIO_PLAYBOOK.md) and [spatial method](SPATIAL_METHOD.md).
