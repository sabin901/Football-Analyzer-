# Football analyst and developer role research

Reviewed 12 October 2026. These are published examples of role requirements, **not a list of currently open vacancies**. The Manchester City description is dated July 2019; Leeds' deadline was 25 June 2025; Swansea's document is hosted in its October 2025 archive. Club needs and technology choices vary. These UK examples do not establish a universal hiring standard for all five leagues.

## What the primary sources say

**Manchester City — Data & Development First Team Performance Analyst (2019).** The role connects quantitative work with coaching decisions. It asks for tactical knowledge, useful visual communication, database concepts and analytical tools; coding and statistical modelling are desirable. The emphasis is on tailoring insight to players and staff and working within the analysis department, including data and video workflows. [Club job description](https://mediacdn.mancity.com/-/media/vacancies/2019/june/data-and-development-1st-team-performance-analyst-jd.ashx?la=en).

**Swansea City — First Team Data Scientist (2025 archive).** The work spans opposition preparation, match review and player/team monitoring, with support for other football departments. Requirements include event-data experience, SQL, Python/data visualisation and explaining findings to nontechnical audiences. API and tracking-data experience are desirable; the document also names BI tools and football-analysis software. [Club job description](https://cdn.swanseacity.com/sites/default/files/2025-10/First%20Team%20Data%20Scientist%20%281%29.pdf).

**Leeds United — Senior Full Stack Developer (2025).** A football intelligence platform should improve staff workflows across analysis, recruitment and performance. The description asks for production delivery and maintainability, React/TypeScript, cloud experience, Python services/data workflows and CI/CD. It specifies four or more years of professional engineering experience. [Club/EFL-hosted job description](https://s3.eu-west-1.amazonaws.com/gc-media-assets.gc.eflservices.co.uk/1388ad30-4860-11f0-ad51-a905242fadd2.pdf).

**Liverpool — research perspective (2021).** The club's interview with William Spearman illustrates a broader research problem: understanding the actions and interactions that create scoring opportunities, beyond counting goals. This is context, not a current job specification. [Club interview](https://www.liverpoolfc.com/news/first-team/450917-the-weird-journey-of-william-spearman-liverpool-s-lead-data-scientist).

## Evidence matrix for this project

### Context outside England and Wales

**Barcelona / La Liga.** The club's Innovation Hub argues for understanding the football question, programming and statistical modelling, while recognizing how much off-ball context is absent from event counts. Its practical account of a data scientist's work emphasizes learning from staff and answering specific questions before building an automated system. These are professional perspectives, not current vacancy requirements. [Skills discussion, 2019](https://barcainnovationhub.fcbarcelona.com/blog/what-do-you-need-to-learn-to-work-in-football-analytics/) · [Workplace perspective, 2022](https://barcainnovationhub.fcbarcelona.com/blog/what-does-a-football-data-scientist-do/).

**Bayer Leverkusen / Bundesliga.** The club describes its analysis coach's close work with coaching staff and the need to respond to tactical changes. That reinforces the importance of football interpretation and timely communication; it does not establish a required programming stack. [Club staff profile](https://www.bayer04.de/de-de/page/werkself/marcel-daum).

**Juventus / Serie A.** The official careers page is the place to verify current specifications. At this review it listed a stadium-steward opportunity; no football analyst vacancy was verified there. Do not manufacture Italian club requirements from unrelated commercial roles. [Official opportunities](https://careers.juventus.com/jobs).

**PSG / Ligue 1.** An official July 2026 junior content-analyst listing concerns digital content and audiences, not first-team tactical analysis. This is a useful warning about job titles: a club's “data analyst” role may be commercial rather than sporting. A football-data-scientist listing appeared on a third-party board, but an official live version was not verified in this review, so its requirements are not treated as primary evidence. [Official content-analyst listing](https://parissaintgermain.wd3.myworkdayjobs.com/en-US/rejoigneznous/job/BOULOGNE-BILLANCOURT/STAGIAIRE-ASSISTANT-E--JUNIOR-CONTENT-ANALYST--H-F----JUILLET-2026_014376).

### Project evidence

| Capability | Evidence you can demonstrate | Gap or next exercise |
|---|---|---|
| Data engineering | Cached API ingestion; IDs; provenance; last-good retention; SQLite indexes; scheduled CI | Add contract monitoring and incident history over several weeks; explain provider rights |
| SQL | Relational results, appearances, event-player and shot tables; executable example queries | Explain joins, grains, nulls and query plans without assistance |
| Football analysis | Match reports, shot maps, progression definition, contextual opposition checklist | Write your own tactical interpretation and verify it against licensed/full-match video |
| Player recruitment | Position-group profiles, minutes threshold, sample disclosure | Define a role with a coach; account for possession, competition strength, age and feasibility |
| Statistical modelling | Same-date exclusion; simple baselines; log loss/Brier/RPS; calibration; audit records | Run a prospective forecasting journal; test drift, strength changes and stronger models without test-set tuning |
| Communication | Downloadable briefing notes; data limitations next to the outputs | Deliver a five-minute presentation and a one-page recommendation to a coach; record feedback |
| Software engineering | FastAPI, a responsive static frontend, integration tests and deployment | This vanilla-JS project does not demonstrate React/TypeScript or AWS infrastructure; build those skills separately if targeting the Leeds role |
| Tracking / video | Clear statement of unavailable inputs | Learn event/tracking alignment and video coding with permissioned material; do not claim those skills from shot coordinates |
| Professional judgement | No fake current xG, no invented minutes, explicit uncertainty | Demonstrate how you change an opinion when video or data contradicts it |

## A realistic hiring strategy

Choose a primary direction: performance analysis, recruitment analysis, football data science, or football software engineering. They overlap, but employers do not assess them identically. Tailor the project demonstration to that role rather than presenting every chart.

Prepare three original case studies: an opposition briefing, a role-specific player comparison, and a prediction validation investigation. Each needs a question, the data/sample, a defensible method, evidence, an interpretation, a proposed next action and limits. Keep code reproducible and make your own contribution explicit, including AI assistance. Do not claim experience working inside a club, production cloud experience or model accuracy beyond what you can demonstrate.

Seek feedback from a local coach, academy or university team and practice working to a match deadline. A smaller real stakeholder project can test whether your analysis changes a decision. Follow each club's official careers pages for current eligibility, location, qualification and work-authorisation requirements. This research and software improve portfolio evidence; they do not guarantee an interview or job.
