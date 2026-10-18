'use strict';
const interrupted = (m) => ['abandoned', 'postponed', 'cancelled'].includes(m.status);
const today = () => new Date().toISOString().slice(0, 10);
const titles = {
  overview: [
    'League overview',
    'The season at a glance',
    'Follow the table, read the form, and find the story behind the score.',
  ],
  matches: [
    'Matches & results',
    'Matches & results',
    'Explore recorded results and the published schedule.',
  ],
  compare: [
    'Team comparison',
    'Team comparison',
    'Compare like for like: the same league, season, venue and sample window.',
  ],
  coverage: [
    'Data & methodology',
    'Data & methodology',
    'See exactly what is available, what is missing, and how we calculate it.',
  ],
};
let manifest,
  data,
  leagueId = 'PL',
  seasonId = '',
  view = 'overview',
  venue = 'all',
  windowSize = 'all',
  query = '',
  sort = 'points',
  matchFilter = 'results',
  matchTeam = '',
  page = 1,
  home = '',
  away = '',
  requestId = 0;
Object.assign(titles, {
  analyst: [
    'Analyst workspace',
    'Build the evidence. Make the decision.',
    'A private workspace for your match data, local video and decision brief.',
  ],
  heatmap: [
    'Player & team heatmaps',
    'The game, mapped',
    'Player and team activity maps from real historical event locations.',
  ],
  players: [
    'Player archive',
    'Player archive',
    'Explore the 2017/18 research archive. These are historical player records.',
  ],
  matchlab: [
    'Match archive',
    'Match archive',
    'Inspect historical 2017/18 match events and lineups.',
  ],
  events: [
    'Event & scouting lab',
    'Historical event analysis',
    'Historical shot maps, player profiles and positional comparisons.',
  ],
  forecast: [
    'Forecast lab',
    'Match forecasts',
    'Experimental probabilities, measured performance and a published forecast record.',
  ],
});
const content = $('#content');
const form = (letters) =>
  `<span class="form" aria-label="Last ${letters.length} results, oldest first: ${letters.join(', ')}">${letters.map((x) => `<i class="${x}">${x}</i>`).join('')}</span>`;
const badge = (name) =>
  manifest?.crests?.[leagueId]?.[name]
    ? crest({ name, logo: manifest.crests[leagueId][name] })
    : `<span class="team-badge" aria-hidden="true">${esc(
        short(name)
          .split(' ')
          .map((n) => n[0])
          .join('')
          .slice(0, 3),
      )}</span>`;
const metric = (label, value, note, team = false) =>
  `<div class="metric"><div class="metric-label">${label}</div><div class="metric-value ${team ? 'team-value' : ''}">${value}</div><div class="metric-note">${note}</div></div>`;
const empty = (message) => `<div class="empty">${message}</div>`;
const teamOptions = (selected, all = false) =>
  `${all ? '<option value="">All teams</option>' : ''}${data.table.map((r) => `<option value="${esc(r.team)}" ${r.team === selected ? 'selected' : ''}>${esc(short(r.team))}</option>`).join('')}`;
function filteredTable() {
  return data.table
    .map((base) => {
      let games = data.matches.filter(
        (m) =>
          m.hg !== null &&
          ((m.home === base.team && venue !== 'away') ||
            (m.away === base.team && venue !== 'home')),
      );
      if (windowSize !== 'all') games = games.slice(-Number(windowSize));
      const r = {
        team: base.team,
        p: games.length,
        w: 0,
        d: 0,
        l: 0,
        gf: 0,
        ga: 0,
        pts: 0,
        cs: 0,
        form: [],
      };
      for (const m of games) {
        const [gf, ga] = m.home === base.team ? [m.hg, m.ag] : [m.ag, m.hg];
        const x = matchOutcome(m, base.team);
        r[x.toLowerCase()]++;
        r.gf += gf;
        r.ga += ga;
        r.pts += x === 'W' ? 3 : x === 'D' ? 1 : 0;
        r.cs += ga === 0;
        r.form.push(x);
      }
      r.gd = r.gf - r.ga;
      r.ppg = r.p ? r.pts / r.p : null;
      r.form = r.form.slice(-5);
      return r;
    })
    .sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf || a.team.localeCompare(b.team));
}
function selectorToolbar(includeTeams = false) {
  return /* HTML */ `<div class="toolbar">
    ${includeTeams ? `<label for="home">${view === 'predict' ? 'Home team' : 'First team'}<select id="home">${teamOptions(home)}</select></label><label for="away">${view === 'predict' ? 'Away team' : 'Second team'}<select id="away">${teamOptions(away)}</select></label>` : ''}${view !== 'predict' ? `<label for="venue">Venue<select id="venue"><option value="all" ${venue === 'all' ? 'selected' : ''}>All matches</option><option value="home" ${venue === 'home' ? 'selected' : ''}>Home only</option><option value="away" ${venue === 'away' ? 'selected' : ''}>Away only</option></select></label><label for="window">Sample window<select id="window"><option value="all" ${windowSize === 'all' ? 'selected' : ''}>Full season</option><option value="5" ${windowSize === '5' ? 'selected' : ''}>Last 5 matches</option><option value="10" ${windowSize === '10' ? 'selected' : ''}>Last 10 matches</option></select></label>` : ''}
  </div>`;
}
function standingsRows() {
  const overall = venue === 'all' && windowSize === 'all';
  const reconciled = data.quality?.standings?.status === 'matched';
  const all = overall && reconciled ? data.table : filteredTable();
  const rows = all
    .map((r, i) => ({ ...r, rank: r.rank || i + 1 }))
    .filter((r) => r.team.toLowerCase().includes(query.toLowerCase()));
  if (sort === 'attack') rows.sort((a, b) => (b.p ? b.gf / b.p : -1) - (a.p ? a.gf / a.p : -1));
  if (sort === 'defence')
    rows.sort((a, b) => (a.p ? a.ga / a.p : Infinity) - (b.p ? b.ga / b.p : Infinity));
  if (sort === 'form')
    rows.sort(
      (a, b) =>
        b.form.reduce((s, x) => s + (x === 'W' ? 3 : x === 'D' ? 1 : 0), 0) -
        a.form.reduce((s, x) => s + (x === 'W' ? 3 : x === 'D' ? 1 : 0), 0),
    );
  return (
    rows
      .map(
        (r) =>
          `<tr><td>${r.rank}</td><td><button class="team-link" data-team="${esc(r.team)}" title="Compare ${esc(short(r.team))}">${badge(r.team)}${esc(short(r.team))}</button></td><td>${r.p}</td><td>${r.w}</td><td>${r.d}</td><td>${r.l}</td><td>${r.gf}:${r.ga}</td><td>${r.gd > 0 ? '+' : ''}${r.gd}</td><td class="points">${r.pts}${r.adjustment ? `<small title="${r.adjustment} administrative points adjustment"> (${r.adjustment > 0 ? '+' : ''}${r.adjustment})</small>` : ''}</td><td>${form(r.form)}</td></tr>`,
      )
      .join('') || '<tr><td colspan="10">No teams match your search.</td></tr>'
  );
}
function matchRow(m) {
  const state =
    m.status === 'awarded'
      ? 'Awarded result'
      : m.status === 'ratified'
        ? 'Ratified result'
        : m.hg !== null
          ? 'Full time'
          : interrupted(m)
            ? m.status[0].toUpperCase() + m.status.slice(1)
            : m.date && m.date < today()
              ? 'Result missing'
              : 'Scheduled';
  return /* HTML */ `<div class="match-row">
    <span class="match-date">${day(m.date)}</span><span class="home">${esc(short(m.home))}</span
    ><span class="score">${m.hg !== null ? `${m.hg}–${m.ag}` : 'vs'}</span
    ><span class="away">${esc(short(m.away))}</span
    ><span class="match-state"
      >${m.result_review ? `<details><summary>${state} · source note</summary><p>${esc(m.result_review.reason)}</p>${m.result_review.sources.map((url, i) => `<a href="${esc(url)}" target="_blank" rel="noopener">Source ${i + 1}</a>`).join(' · ')}</details>` : state}</span
    >
  </div>`;
}
function overview() {
  const done = data.matches.filter((m) => m.hg !== null),
    goals = done.reduce((s, m) => s + m.hg + m.ag, 0),
    leader = data.table.find((r) => r.p) || null;
  const scored = [...data.table]
    .filter((r) => r.p)
    .sort((a, b) => b.gf / b.p - a.gf / a.p)
    .slice(0, 5);
  const recent = done.slice(-3).reverse();
  const formLeader = [...data.table]
    .filter((r) => r.p)
    .sort(
      (a, b) =>
        b.form.reduce((s, x) => s + (x === 'W' ? 3 : x === 'D' ? 1 : 0), 0) -
        a.form.reduce((s, x) => s + (x === 'W' ? 3 : x === 'D' ? 1 : 0), 0),
    )[0];
  return /* HTML */ ` ${data.archive_note ? `<div class="notice">${esc(data.archive_note)}</div>` : ''}
    <div class="metrics">
      ${metric('RECORDED MATCHES', data.completed, `of ${data.matches.length} scheduled fixtures`)}${metric('GOALS PER MATCH', done.length ? (goals / done.length).toFixed(2) : '—', `${goals} goals in recorded results`)}${metric('MOST MATCH POINTS', esc(short(leader?.team || '—')), leader ? `${leader.pts} points · ${leader.p} matches played` : 'No completed matches', true)}${metric('TEAMS IN FOCUS', data.table.length, `${esc(manifest.leagues.find((l) => l.id === leagueId).country)} · ${seasonId.replace('-', '/')}`)}
    </div>
    <div class="dashboard-grid">
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>
              ${venue === 'all' && data.quality?.standings?.status === 'matched' ? 'League standings' : 'Results summary'}
            </h2>
            <p>
              ${venue === 'all' && data.quality?.standings?.status === 'matched' ? 'Provider supplied standings' : venue === 'all' ? 'Computed match points · excludes deductions and official tie-breaks' : 'Match points · rank within this venue only'}
            </p>
          </div>
          <div class="segmented" role="group" aria-label="Standings venue">
            ${['all', 'home', 'away'].map((v) => `<button data-venue="${v}" class="${venue === v ? 'selected' : ''}" aria-pressed="${venue === v}">${v === 'all' ? 'Overall' : v[0].toUpperCase() + v.slice(1)}</button>`).join('')}
          </div>
        </div>
        <div class="table-tools">
          <label class="sr-label" for="team-search"
            ><span>Find a team</span
            ><input
              id="team-search"
              type="search"
              placeholder="Search teams…"
              value="${esc(query)}" /></label
          ><label for="table-sort"
            >Sort by<select id="table-sort">
              <option value="points" ${sort === 'points' ? 'selected' : ''}>Points</option>
              <option value="attack" ${sort === 'attack' ? 'selected' : ''}>Goals / match</option>
              <option value="defence" ${sort === 'defence' ? 'selected' : ''}>
                Fewest conceded / match
              </option>
              <option value="form" ${sort === 'form' ? 'selected' : ''}>Last 5 form</option>
            </select></label
          >
        </div>
        <div class="table-scroll">
          <table aria-label="${esc(venue)} standings for ${esc(leagueId)} ${esc(seasonId)}">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Club</th>
                <th scope="col" title="Played">P</th>
                <th scope="col">W</th>
                <th scope="col">D</th>
                <th scope="col">L</th>
                <th scope="col">GF:GA</th>
                <th scope="col">GD</th>
                <th scope="col">Pts</th>
                <th scope="col">Last 5 →</th>
              </tr>
            </thead>
            <tbody id="standings-body">
              ${standingsRows()}
            </tbody>
          </table>
        </div>
        <p class="table-note">
          ${venue === 'all' && data.quality?.standings?.status === 'matched' ? `Points and rank follow the <a href="${esc(data.quality.standings.source_url)}">provider table</a>, including administrative adjustments and provider tie-break ordering. Played, W/D/L and goals reconcile with the recorded results. Checked ${stamp(data.quality.checked_at)}.` : 'These are points earned from recorded results. Administrative deductions are not allocated to home/away splits. Ranks here order the sample by match points, goal difference and goals for; official competition rankings may differ.'}
          Form runs oldest to newest.
        </p>
      </section>
      <aside class="side-panels">
        <section class="panel editorial">
          <p class="eyebrow">THE ANALYST'S NOTE</p>
          <h2>
            ${formLeader ? `${esc(short(formLeader.team))} in focus.` : 'A season taking shape.'}
          </h2>
          <p>
            ${formLeader ? `${esc(short(formLeader.team))} have taken ${formLeader.form.reduce((s, x) => s + (x === 'W' ? 3 : x === 'D' ? 1 : 0), 0)} points from their last ${formLeader.form.length} recorded matches. Check the home and away splits before calling it a trend.` : 'Use the league filters to explore the available results.'}
          </p>
          <button data-view="compare">Explore team comparison ↗</button>
        </section>
        <section class="panel">
          <div class="panel-head">
            <h2>Attacking output</h2>
            <span class="mini">Goals / match</span>
          </div>
          <div class="panel-body">
            ${scored.map((r) => `<div class="ranking"><div class="ranking-top"><span>${esc(short(r.team))}</span><strong>${(r.gf / r.p).toFixed(2)}</strong></div><div class="ranking-track"><div class="ranking-fill" style="width:${(100 * (r.gf / r.p)) / (scored[0].gf / scored[0].p || 1)}%"></div></div></div>`).join('')}
            <p class="muted">Actual scoring output, not chance quality.</p>
          </div>
        </section>
        <section class="panel">
          <div class="panel-head">
            <h2>Latest recorded</h2>
            <button class="secondary" data-view="matches">View all ↗</button>
          </div>
          <div class="panel-body">
            ${recent.map((m) => `<div class="compact-match"><div class="match-date">${day(m.date)}</div><div class="sides"><span>${esc(short(m.home))}</span><strong>${m.hg}</strong></div><div class="sides"><span>${esc(short(m.away))}</span><strong>${m.ag}</strong></div></div>`).join('') || '<p class="muted">No results recorded.</p>'}
          </div>
        </section>
      </aside>
    </div>`;
}
function matchesView() {
  let rows = data.matches.filter(
    (m) =>
      (!matchTeam || m.home === matchTeam || m.away === matchTeam) &&
      `${m.home} ${m.away}`.toLowerCase().includes(query.toLowerCase()),
  );
  if (matchFilter === 'results') rows = rows.filter((m) => m.hg !== null).reverse();
  if (matchFilter === 'upcoming')
    rows = rows.filter((m) => m.hg === null && !interrupted(m) && (!m.date || m.date >= today()));
  if (matchFilter === 'interrupted') rows = rows.filter(interrupted);
  if (matchFilter === 'missing')
    rows = rows.filter((m) => m.hg === null && !interrupted(m) && m.date && m.date < today());
  const pages = Math.max(1, Math.ceil(rows.length / 20));
  page = Math.min(page, pages);
  return /* HTML */ `<div class="toolbar">
      <label for="match-filter"
        >Match status<select id="match-filter">
          ${[
            ['results', 'Recorded results'],
            ['upcoming', 'Upcoming schedule'],
            ['missing', 'Missing past results'],
            ['interrupted', 'Postponed / abandoned'],
            ['all', 'Full schedule'],
          ]
            .map(
              ([v, l]) =>
                `<option value="${v}" ${v === matchFilter ? 'selected' : ''}>${l}</option>`,
            )
            .join('')}
        </select></label
      ><label for="match-team"
        >Club<select id="match-team">
          ${teamOptions(matchTeam, true)}
        </select></label
      ><label for="match-search"
        >Search matches<input
          id="match-search"
          type="search"
          value="${esc(query)}"
          placeholder="Team name"
      /></label>
    </div>
    <section class="panel">
      <div class="panel-head">
        <h2>${rows.length} matches</h2>
        <span class="muted">Dates as published · kickoff times unavailable</span>
      </div>
      ${
        rows
          .slice((page - 1) * 20, page * 20)
          .map(matchRow)
          .join('') || empty('No matches in this selection. Try another status or club.')
      }
      <div class="pagination">
        <button class="secondary" data-page="${page - 1}" ${page <= 1 ? 'disabled' : ''}>
          ← Previous</button
        ><span>Page ${page} of ${pages}</span
        ><button class="secondary" data-page="${page + 1}" ${page >= pages ? 'disabled' : ''}>
          Next →
        </button>
      </div>
    </section>`;
}
function comparisonMetric(label, fn, a, b, table, options = {}) {
  const x = fn(a),
    y = fn(b);
  const eligible = table.filter((r) => r.p);
  const average = eligible.length
    ? eligible.reduce((sum, r) => sum + fn(r) * r.p, 0) / eligible.reduce((sum, r) => sum + r.p, 0)
    : null;
  // Each metric has one common axis for both teams and the league benchmark.
  const maximum =
    options.maximum || Math.max(1, Math.ceil(Math.max(...eligible.map(fn), 0) * 2) / 2);
  const value = (v) => (v === null ? '—' : options.percent ? `${v.toFixed(1)}%` : v.toFixed(2));
  const pos = (v) => (100 * (v || 0)) / maximum;
  return `<div class="comparison-row"><div class="comparison-label"><h3>${label}</h3><span>${options.lower ? 'Lower is better' : 'Higher is better'}</span></div><strong class="comparison-number team-a-color">${value(x)}</strong><div class="comparison-plot" role="img" aria-label="${esc(short(a.team))}: ${value(x)}; ${esc(short(b.team))}: ${value(y)}; league average: ${value(average)}; axis 0 to ${maximum}${options.percent ? '%' : ''}"><div class="comparison-axis"></div>${average !== null ? `<span class="comparison-average" style="left:${pos(average)}%" title="League average: ${value(average)}"></span>` : ''}${x !== null && y !== null ? `<span class="comparison-connector" style="left:${Math.min(pos(x), pos(y))}%;width:${Math.abs(pos(x) - pos(y))}%"></span>` : ''}${x !== null ? `<span class="comparison-dot dot-a" style="left:${pos(x)}%" title="${esc(short(a.team))}: ${value(x)}"></span>` : ''}${y !== null ? `<span class="comparison-dot dot-b" style="left:${pos(y)}%" title="${esc(short(b.team))}: ${value(y)}"></span>` : ''}<div class="comparison-ticks"><span>0</span><span>${maximum}${options.percent ? '%' : ''}</span></div></div><strong class="comparison-number team-b-color">${value(y)}</strong><span class="comparison-benchmark">${value(average)}<small>League avg.</small></span></div>`;
}
function compareView() {
  const table = filteredTable(),
    a = table.find((t) => t.team === home),
    b = table.find((t) => t.team === away);
  if (!a || !b) return empty('Choose a season with teams to compare.');
  const cards = [a, b]
    .map(
      (r, i) =>
        `<section class="panel comparison-team ${i ? 'team-b' : 'team-a'}"><div class="comparison-identity">${badge(r.team)}<div><span class="eyebrow">TEAM ${i ? 'B' : 'A'} · ${venue === 'all' ? 'ALL VENUES' : venue.toUpperCase()}</span><h2>${esc(short(r.team))}</h2></div><span class="comparison-rank" title="Rank within the selected filters">#${table.findIndex((t) => t.team === r.team) + 1}</span></div><div class="comparison-stats"><div><strong>${r.p}</strong><span>Played</span></div><div><strong>${r.pts}</strong><span>Match points</span></div><div><strong>${decimal(r.ppg)}</strong><span>Points / match</span></div><div><strong>${r.gd > 0 ? '+' : ''}${r.gd}</strong><span>Goal difference</span></div></div><div class="comparison-form"><span>Recent form</span>${form(r.form)}<small>Oldest → latest</small></div></section>`,
    )
    .join('');
  const measures = [
    ['Goals scored / match', (r) => (r.p ? r.gf / r.p : null), {}],
    ['Goals conceded / match', (r) => (r.p ? r.ga / r.p : null), { lower: true }],
    ['Points / match', (r) => r.ppg, { maximum: 3 }],
    ['Clean-sheet rate', (r) => (r.p ? (100 * r.cs) / r.p : null), { maximum: 100, percent: true }],
    ['Win rate', (r) => (r.p ? (100 * r.w) / r.p : null), { maximum: 100, percent: true }],
  ];
  const h2h = data.matches.filter(
    (m) =>
      m.hg !== null &&
      ((m.home === home && m.away === away) || (m.home === away && m.away === home)),
  );
  return `${selectorToolbar(true)}${home === away ? '<div class="notice">Choose different teams for a meaningful comparison.</div>' : ''}<div class="compare-grid">${cards}</div><section class="panel comparison-panel"><div class="panel-head"><div><p class="eyebrow">TEAM METRICS</p><h2>Performance comparison</h2></div><span class="muted">${windowSize === 'all' ? 'Full season' : 'Last ' + windowSize + ' matches'} · ${venue === 'all' ? 'All venues' : venue + ' only'}</span></div><div class="comparison-legend"><span><i class="dot-a"></i>${esc(short(a.team))}</span><span><i class="dot-b"></i>${esc(short(b.team))}</span><span><i class="average-key"></i>League average</span></div><div class="comparison-chart">${measures.map(([label, fn, options]) => comparisonMetric(label, fn, a, b, table, options)).join('')}</div><p class="table-note">League average is weighted by matches in the same filters. Each row has its own labelled scale. Match points exclude administrative deductions; sample rank is not league position. Rates are not adjusted for opponent strength. ${a.p < 5 || b.p < 5 ? '<strong>Small sample: fewer than five matches for at least one team.</strong>' : ''}</p></section><section class="panel"><div class="panel-head"><h2>Head to head</h2><span class="muted">Selected season · all venues</span></div>${h2h.length ? h2h.map(matchRow).join('') : '<div class="h2h-empty"><span aria-hidden="true">↔</span><div><strong>No meeting recorded this season</strong><p>Use the season selector to explore previous encounters.</p></div></div>'}</section>`;
}
function qualityPanel() {
  const q = data.quality || {},
    r = q.results || {};
  return wbPanel(
    'Source quality and coverage',
    `<p><strong>${esc(leagueId)} · ${esc(seasonId)}</strong> · Checked ${stamp(q.checked_at)}</p><div class="metrics">${metric('Recorded results', data.completed, 'OpenFootball community source')}${metric('Missing past results', data.overdue, 'Before today; not assumed to be draws')}${metric('Quarantined rows', data.quarantined?.length || 0, 'Invalid source rows are excluded')}${metric('Independent verification', 'Unavailable', 'Structural checks are not a second provider')}</div><p>${esc(r.note || '')} The table is computed from recorded results. Official deductions, disciplinary outcomes and competition tie-breaks are not independently verified.</p>${data.quarantined?.length ? `<details><summary>Excluded source records</summary><ul>${data.quarantined.map((m) => `<li>${esc(m.date)} · ${esc(m.home)} / ${esc(m.away)}: ${esc(m.reason)}</li>`).join('')}</ul></details>` : ''}<p><a href="${esc(data.source_url)}">Original source</a> · <a href="data/${leagueId}_${seasonId}.json">Download snapshot and quality record</a> · <a href="docs/DATA_QUALITY.html">Quality policy</a></p>`,
  );
}
function coverageView() {
  return `${qualityPanel()}<section class="panel"><div class="panel-head"><h2>Current result coverage</h2><span class="pill">${esc(manifest.current_season)}</span></div>${manifest.leagues
    .map((l) => {
      const s = l.seasons.find((s) => s.id === manifest.current_season);
      return `<div class="coverage-card"><div class="coverage-identity">${leagueLogo(l.id)}<div><h3>${esc(l.name)}</h3><p>${s ? `${s.completed} recorded results · Latest ${day(s.last_result)}<br>Fetched ${stamp(s.fetched_at)}` : 'Current season unavailable'}</p></div></div><div><span class="status-tag">${s ? `${s.overdue} past results missing` : 'Unavailable'}</span><p>${l.seasons.length} seasons</p></div></div>`;
    })
    .join(
      '',
    )}</section><div class="method-grid">${wbPanel('What is available', `<p><strong>Results:</strong> OpenFootball schedules, scores, form and comparisons across five European leagues. A fresh fetch does not mean every recent match has been entered by the community.</p><p><strong>Historical events:</strong> the complete 2017/18 five-league Pappalardo/Wyscout research archive: action locations, shots, pass counts, lineups and estimated regulation minutes. This is not current squad or recruitment data.</p><p><strong>Your analyst workspace:</strong> import permitted events, attach a local video, record evidence and export a decision brief. Your files are not uploaded.</p><p><strong>Unavailable:</strong> current granular events, provider xG, injuries, reliable possession, continuous tracking, independent official standings verification and verified betting odds. These are never substituted with invented values.</p><p><a href="docs/DATA_DICTIONARY.html">Data dictionary</a> · <a href="data/football.sqlite" download>SQL warehouse</a> · <a href="docs/ANALYST_GUIDE.html">Analyst guide</a></p>`)}${wbPanel('Sources, rights and uncertainty', `<p><a href="https://github.com/openfootball/football.json">OpenFootball</a> publishes under CC0. <a href="https://doi.org/10.6084/m9.figshare.c.4415000">Pappalardo and colleagues (2019)</a> publish the Wyscout research dataset under CC BY 4.0. Names and coordinates are normalized; counts and grids are derived. No endorsement is implied.</p><p>Only these allowlisted sources enter the public build. ESPN, Football-Data.co.uk, and the restricted StatsBomb archive are excluded from the public package.</p><p>Results refresh attempts run every six hours. Invalid rows are quarantined; a failed fetch retains the last available snapshot. Forecasts are withheld on incomplete schedules, missing past results, quarantine or stale inputs.</p><p>Historical model comparisons include league frequency, equal probabilities, Elo and a fitted Poisson challenger. The model is experimental, has no demonstrated live edge, and does not include injury or lineup information.</p><p><a href="data/source_registry.json">License registry</a> · <a href="data/wyscout_sources.json">Archive fingerprints</a> · <a href="docs/ASSET_CREDITS.html">Full attribution</a> · <a href="docs/PRIVACY.html">Privacy</a></p>`)}</div>`;
}
function render() {
  const [label, title, desc] = titles[view];
  document.title = `${label.replace(/[–—-]/g, ' ')} | Footlyzer Football Analytics`;
  $('#breadcrumb').textContent = label;
  $('#page-title').textContent = title;
  $('#page-description').textContent = desc;
  $('#view-select').innerHTML = [...document.querySelectorAll('#navigation button')]
    .map((b) => b.dataset.view)
    .map((id) => `<option value="${id}" ${id === view ? 'selected' : ''}>${titles[id][0]}</option>`)
    .join('');
  const workbench = WORKBENCH_VIEWS.has(view);
  const archive = view === 'analyst';
  $('.context-bar').hidden = archive;
  $('#league-tabs').hidden = archive;
  $('.context-controls').hidden = archive;
  $('.heading .eyebrow').textContent =
    {
      overview: 'SEASON INTELLIGENCE',
      compare: 'SIDE BY SIDE',
      heatmap: 'SPATIAL ANALYSIS',
      forecast: 'PROBABILITY & EVIDENCE',
      events: 'EVENT ANALYSIS',
    }[view] || 'FOOTBALL ANALYTICS';
  $('#league-title').textContent = archive
    ? 'Historical research library'
    : manifest?.leagues.find((l) => l.id === leagueId)?.name || '';
  $('#league-symbol').innerHTML = archive ? icon('book-open') : leagueLogo(leagueId);
  $('#season').closest('label').hidden = workbench || archive;
  $('#data-status').hidden = workbench || archive;
  $('#export').hidden = workbench || archive;
  $('#season-caption').textContent = archive
    ? 'Fixed case studies · 2018 and 2015/16'
    : workbench
      ? ['events', 'heatmap'].includes(view)
        ? 'Historical event datasets'
        : view === 'forecast'
          ? 'Experimental forecast evaluation'
          : 'Historical 2017/18 archive'
      : `${seasonId === manifest?.current_season ? 'Current season' : 'Historical season'}`;
  document.querySelectorAll('#navigation button').forEach((b) => {
    b.classList.toggle('active', b.dataset.view === view);
    b.setAttribute('aria-current', b.dataset.view === view ? 'page' : 'false');
  });
  if (archive) {
    content.innerHTML = analystView();
    decorateIcons(content);
    content.setAttribute('aria-busy', 'false');
    analystMount();
    return;
  }
  if (!data) return;
  content.innerHTML = workbench
    ? workbenchView(view)
    : {
        overview,
        matches: matchesView,
        compare: compareView,

        coverage: coverageView,
      }[view]();
  decorateIcons(content);
  content.setAttribute('aria-busy', String(workbench && snapshotStore.isLoading()));
}
function updateUrl(push = false) {
  const params = new URLSearchParams({ view, league: leagueId, season: seasonId });
  const hash = `#${params}`;
  if (location.hash !== hash) history[push ? 'pushState' : 'replaceState'](null, '', hash);
}
function showView(next) {
  view = titles[next] ? next : 'overview';
  query = '';
  page = 1;
  windowSize = 'all';
  updateUrl(true);
  render();
  window.scrollTo(0, 0);
}
async function fetchJson(url) {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`Data request failed (${response.status})`);
  return response.json();
}
async function loadLeague(push = false) {
  const token = ++requestId;
  data = null;
  content.setAttribute('aria-busy', 'true');
  content.innerHTML = empty('Loading league snapshot…');
  $('#export').disabled = true;
  const league = manifest.leagues.find((l) => l.id === leagueId) || manifest.leagues[0];
  leagueId = league.id;
  if (!league.seasons.some((s) => s.id === seasonId))
    seasonId =
      league.seasons.find((s) => s.id === manifest.current_season)?.id ||
      league.seasons[0]?.id ||
      '';
  $('#league-tabs').innerHTML = manifest.leagues
    .map(
      (l) =>
        `<button class="league-tab ${l.id === leagueId ? 'active' : ''}" data-league="${l.id}" aria-pressed="${l.id === leagueId}">${leagueLogo(l.id)}${esc(l.name)}</button>`,
    )
    .join('');
  $('#league-title').textContent = league.name;
  $('#league-symbol').innerHTML = leagueLogo(league.id);
  $('#season').innerHTML = league.seasons
    .map(
      (s) =>
        `<option value="${s.id}" ${s.id === seasonId ? 'selected' : ''}>${s.id.replace('-', '/')}</option>`,
    )
    .join('');
  $('#season').disabled = false;
  $('#season-caption').textContent =
    `${league.country} · ${seasonId === manifest.current_season ? 'Current season' : 'Historical season'}`;
  $('#data-status').textContent = 'Checking snapshot coverage…';
  updateUrl(push);
  try {
    const selected = league.seasons.find((s) => s.id === seasonId);
    if (!selected) throw new Error('No snapshot available for this league.');
    const snapshot = await fetchJson(selected.file);
    if (token !== requestId) return;
    if (
      snapshot.league !== leagueId ||
      snapshot.season !== seasonId ||
      !Array.isArray(snapshot.matches) ||
      !Array.isArray(snapshot.table)
    )
      throw new Error('The snapshot does not match the selected league and season.');
    data = snapshot;
    data.predictions = data.predictions || [];
    home = data.table[0]?.team || '';
    away = data.table[1]?.team || '';
    venue = 'all';
    windowSize = 'all';
    query = '';
    matchTeam = '';
    page = 1;
    const overdue = data.matches.filter(
      (m) => m.hg === null && !interrupted(m) && m.date && m.date < today(),
    ).length;
    const oldFetch =
      seasonId === manifest.current_season &&
      Date.now() - Date.parse(data.fetched_at) > 36 * 3600000;
    const warning =
      overdue || oldFetch || data.refresh_ok === false || seasonId !== manifest.current_season;
    $('#data-status').innerHTML =
      `<span class="status-tag ${warning ? '' : 'good'}">${seasonId !== manifest.current_season ? 'HISTORICAL SNAPSHOT' : overdue ? 'PARTIAL RESULTS' : oldFetch ? 'STALE SNAPSHOT' : data.refresh_ok === false ? 'REFRESH FAILED' : 'CURRENT-SEASON SNAPSHOT'}</span> Latest recorded result <strong>${day(data.last_result)}</strong> <span aria-hidden="true">·</span> Fetched ${stamp(data.fetched_at)}${overdue ? ` <span aria-hidden="true">·</span> <strong>${overdue} past fixtures have no recorded result.</strong>` : ''}${data.refresh_ok === false ? ' · Last refresh failed; showing the last successful snapshot.' : ''}${oldFetch ? ' · Fetch is older than 36 hours.' : ''}`;
    $('#data-status').innerHTML +=
      `<br><a href="#view=coverage&league=${leagueId}&season=${seasonId}">Computed table · community source · independent verification unavailable${data.quarantined?.length ? ' · ' + data.quarantined.length + ' quarantined rows' : ''}</a>`;
    $('#export').disabled = false;
    render();
  } catch (error) {
    if (token !== requestId) return;
    $('#data-status').textContent = 'Snapshot unavailable';
    content.setAttribute('aria-busy', 'false');
    content.innerHTML = empty(
      `<p class="error">${esc(error.message)}</p><button class="secondary" data-retry>Try again</button>`,
    );
  }
}
async function start() {
  try {
    data = null;
    manifest = await fetchJson('data/manifest.json');
    const params = new URLSearchParams(location.hash.slice(1));
    leagueId = params.get('league') || 'PL';
    seasonId = params.get('season') || manifest.current_season;
    view = titles[params.get('view')] ? params.get('view') : 'overview';
    render();
    await loadLeague();
  } catch (error) {
    content.setAttribute('aria-busy', 'false');
    if (new URLSearchParams(location.hash.slice(1)).get('view') === 'analyst') {
      view = 'analyst';
      render();
      return;
    }
    $('#data-status').textContent = 'Could not load the league catalogue.';
    content.innerHTML = empty(
      `<p class="error">${esc(error.message)}</p><button class="secondary" data-retry>Try again</button>`,
    );
  }
}
document.addEventListener('click', (event) => {
  const b = event.target.closest('button');
  if (!b) return;
  if (b.dataset.view) showView(b.dataset.view);
  if (b.dataset.league) {
    leagueId = b.dataset.league;
    Object.assign(wb, {
      team: '',
      position: '',
      search: '',
      player: '',
      page: 1,
      match: '',
      briefTeam: '',
      eventPlayer: '',
      set: '',
      eventMatch: '',
    });
    loadLeague(true);
  }
  if (b.dataset.venue) {
    venue = b.dataset.venue;
    windowSize = 'all';
    render();
  }
  if (b.dataset.team) {
    home = b.dataset.team;
    if (away === home) away = data.table.find((r) => r.team !== home)?.team || '';
    showView('compare');
  }
  if (b.dataset.page) {
    page = Number(b.dataset.page);
    render();
  }
  if (b.hasAttribute('data-retry')) start();
});
document.addEventListener('change', (event) => {
  const { id, value } = event.target;
  if (id === 'view-select') {
    showView(value);
    return;
  }
  if (id === 'season') {
    seasonId = value;
    loadLeague(true);
    return;
  }
  if (id === 'home') home = value;
  if (id === 'away') away = value;
  if (id === 'venue') venue = value;
  if (id === 'window') windowSize = value;
  if (id === 'table-sort') sort = value;
  if (id === 'match-filter') {
    matchFilter = value;
    page = 1;
  }
  if (id === 'match-team') {
    matchTeam = value;
    page = 1;
  }
  if (['home', 'away', 'venue', 'window', 'table-sort', 'match-filter', 'match-team'].includes(id))
    render();
});
document.addEventListener('input', (event) => {
  if (event.target.id === 'team-search') {
    query = event.target.value;
    $('#standings-body').innerHTML = standingsRows();
  }
  if (event.target.id === 'match-search') {
    query = event.target.value;
    page = 1;
    const pos = event.target.selectionStart;
    render();
    $('#match-search').focus();
    $('#match-search').setSelectionRange(pos, pos);
  }
});
$('#refresh').addEventListener('click', async () => {
  const b = $('#refresh');
  b.disabled = true;
  snapshotStore.clear();
  try {
    await start();
  } finally {
    b.disabled = false;
  }
});
$('#export').addEventListener('click', () => {
  if (!data) return;
  const rows = [
    [
      'league',
      'season',
      'date',
      'home',
      'away',
      'home_goals',
      'away_goals',
      'source',
      'fetched_at',
      'result_status',
      'awarded_winner',
      'source_note',
      'review_sources',
    ],
    ...data.matches
      .filter((m) => m.hg !== null)
      .map((m) => [
        leagueId,
        seasonId,
        m.date,
        m.home,
        m.away,
        m.hg,
        m.ag,
        m.result_review ? 'Reviewed correction' : m.result_source || 'OpenFootball',
        m.result_checked_at || data.fetched_at,
        m.status || 'finished',
        m.awarded_winner || '',
        m.result_review?.reason || '',
        m.result_review?.sources.join(' | ') || '',
      ]),
  ];
  downloadFile(
    `footlyzer-${leagueId}-${seasonId}-results.csv`,
    toCsv(rows),
    'text/csv;charset=utf-8',
  );
});
window.addEventListener('hashchange', () => {
  if (location.hash !== '#main') start();
});
start();
