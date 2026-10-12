'use strict';

// These reports have fixed source datasets. They never inherit a current league filter.
function researchView() {
  return /* HTML */ `
    <section class="research-intro panel">
      <div>
        <p class="eyebrow">HISTORICAL CASE STUDIES</p>
        <h2>See the evidence. Develop the argument.</h2>
        <p>
          Two worked examples of match analysis and team profiling. Inspect the charts, question the
          assumptions, then continue with the interactive historical archive.
        </p>
      </div>
      <a class="secondary" href="docs/PORTFOLIO_PLAYBOOK.html"
        >Build your own case study ${icon('arrow-up-right')}</a
      >
    </section>
    <div class="research-library">
      <article class="panel research-case">
        <div class="research-case-copy">
          <p class="eyebrow">01 / MATCH REVIEW</p>
          <h2>France vs Croatia</h2>
          <p class="research-meta">World Cup final · 15 July 2018 · Single match</p>
          <p>
            Read the shot map, cumulative expected goals and passing networks together. Use them to
            ask how chance quality and ball circulation shaped the match.
          </p>
        </div>
        <a
          class="research-preview"
          href="assets/report_8658.png"
          aria-label="Open full size France versus Croatia report"
        >
          <img
            src="assets/report_8658.png"
            alt="Historical France versus Croatia report with shot locations, cumulative xG and passing networks"
            loading="lazy"
          />
        </a>
        <div class="research-case-copy">
          <h3>Questions to investigate</h3>
          <ul>
            <li>When did chance quality accumulate, and how did score state change the match?</li>
            <li>Which passing connections are worth checking against video?</li>
          </ul>
          <p class="muted">
            A single match cannot establish a repeatable team identity. Network edges describe
            recorded passes, not off ball positioning.
          </p>
          <div class="toolbar">
            <a class="secondary" href="assets/report_8658.png" download
              >Download match report ${icon('download')}</a
            >
          </div>
        </div>
      </article>
      <article class="panel research-case">
        <div class="research-case-copy">
          <p class="eyebrow">02 / TEAM PROFILE</p>
          <h2>Arsenal</h2>
          <p class="research-meta">Premier League · 2015/16 · Historical season</p>
          <p>
            Explore a team scouting example, then test your interpretation against player profiles,
            shot locations and event activity in the interactive archive.
          </p>
        </div>
        <a
          class="research-preview"
          href="assets/scout_2_27_Arsenal.png"
          aria-label="Open full size Arsenal 2015/16 report"
        >
          <img
            src="assets/scout_2_27_Arsenal.png"
            alt="Historical Arsenal scouting report from the 2015/16 Premier League season"
            loading="lazy"
          />
        </a>
        <div class="research-case-copy">
          <h3>Continue the investigation</h3>
          <ul>
            <li>Compare players in the same role and inspect the minutes denominator.</li>
            <li>Check where actions originate and whether the pattern persists across matches.</li>
          </ul>
          <p class="muted">
            This describes the 2015/16 archive, not the current Arsenal squad. Historical playing
            time is estimated from the event record.
          </p>
          <div class="toolbar">
            <button class="secondary" data-research-view="events">
              Explore 2015/16 events ${icon('arrow-up-right')}
            </button>
            <button class="secondary" data-research-view="heatmap">
              Explore 2015/16 heatmaps ${icon('scan-line')}
            </button>
            <a href="assets/scout_2_27_Arsenal.png" download
              >Download team report ${icon('download')}</a
            >
          </div>
        </div>
      </article>
    </div>
    <section class="panel prose">
      <div class="panel-body">
        <h2>Turn a chart into a defensible recommendation</h2>
        <ol>
          <li>
            <strong>State the question.</strong> Define the opponent, phase of play and decision the
            analysis should support.
          </li>
          <li>
            <strong>Show the evidence.</strong> Record the dataset, sample, method and alternative
            explanations. Use video to verify tactical claims.
          </li>
          <li>
            <strong>Explain the decision.</strong> Separate observations from interpretation, and
            say what additional evidence could change your conclusion.
          </li>
        </ol>
        <p>
          These are static research artifacts from StatsBomb Open Data. They do not update with
          current results. The research models and retrospective outputs are not validated forecasts
          of today's players or teams.
        </p>
        <div class="toolbar">
          <a href="docs/MODEL_CARD.html">Model assumptions ${icon('arrow-up-right')}</a>
          <a href="docs/SPATIAL_METHOD.html">Spatial method ${icon('arrow-up-right')}</a>
          <a href="https://github.com/sabin901/Football-Analyzer-"
            >Code and reproduction guide ${icon('arrow-up-right')}</a
          >
        </div>
      </div>
    </section>
  `;
}

document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-research-view]');
  if (!button) return;
  // An explicit jump sets the historical dataset, including when arriving from another league.
  leagueId = 'PL';
  view = button.dataset.researchView;
  wb.set = '2_27';
  wb.eventPlayer = '';
  wb.eventMatch = '';
  Object.assign(hs, { set: '2_27', scope: 'season', team: '1', player: '', compare: '' });
  loadLeague(true);
  window.scrollTo(0, 0);
});
