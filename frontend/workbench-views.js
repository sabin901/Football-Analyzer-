'use strict';
// View functions return HTML from validated snapshots and the current filters.
// Historical player summaries and event profiles retain their documented definitions.
function currentPlayerCard(d) {
  const p = d.players.find((p) => `${p.id}:${p.team_id}` === wb.player);
  if (!p) return '';
  const games = d.matches
    .filter((m) =>
      m.players.some((r) => r.id === p.id && r.team_id === p.team_id && r.stats.appearances > 0),
    )
    .slice(-5)
    .reverse();
  return wbPanel(
    `${esc(p.name)} <span class="muted">${esc(p.team)} · ${esc(p.position || 'Position unavailable')}</span>`,
    `<div class="profile-head">${portrait(p, d)}<p>${p.matches} imported appearances · ${p.starts} starts. Provider ID ${esc(p.id)}.</p></div><div class="mini-stats">${[
      ['Goals', 'totalGoals'],
      ['Shots', 'totalShots'],
    ]
      .map(
        ([label, key]) =>
          `<div><strong>${p.stats[key] ?? '—'}</strong><span>${label}</span><small>${p.stat_samples[key] || 0} matches with this field</small></div>`,
      )
      .join(
        '',
      )}</div><h3>Recent imported appearances</h3>${games.map((m) => `<button class="fixture-button" data-current-match="${m.id}">${day(m.date.slice(0, 10))}<span>${esc(m.teams.find((t) => t.venue === 'home').name)} vs ${esc(m.teams.find((t) => t.venue === 'away').name)}</span>Open report ↗</button>`).join('') || '<p>No recorded appearance yet.</p>'}<p class="muted">These are appearance totals. Estimated regulation-minute rates are available in Event & scouting lab; neither view adjusts for opposition or team style.</p>`,
  );
}
function playersView(d) {
  let rows = d.players.filter(
    (p) =>
      (!wb.search || wbFold(p.name).includes(wbFold(wb.search))) &&
      (!wb.team || p.team_id === wb.team) &&
      (!wb.position || p.position === wb.position) &&
      p.matches >= wb.min,
  );
  rows.sort(
    (a, b) =>
      (b.stats[wb.sort] ?? -1) - (a.stats[wb.sort] ?? -1) ||
      b.matches - a.matches ||
      a.name.localeCompare(b.name),
  );
  const pages = Math.max(1, Math.ceil(rows.length / 40));
  wb.page = Math.min(wb.page, pages);
  return /* HTML */ `${wbSource(d)}
    <div class="metrics">
      ${metric('Squads', d.coverage.squads, `${d.coverage.expected_teams} expected clubs`)}${metric('Player records', d.players.length, 'One row per player and club')}${metric('Match reports', d.matches.length, 'Lineups, results and box scores')}${metric('Players used', d.players.filter((p) => p.matches > 0).length, 'With imported league appearances')}
    </div>
    ${currentPlayerCard(d)}
    <section class="panel">
      <div class="panel-head">
        <h2>Squad & player explorer</h2>
        <button class="secondary" data-export-players>Export this selection ↓</button>
      </div>
      <div class="toolbar wb-toolbar">
        <label for="wb-search"
          >Player name<input
            id="wb-search"
            value="${esc(wb.search)}"
            placeholder="Find a player…"
            type="search" /></label
        >${wbSelect('wb-team', 'Club', [['', 'All clubs'], ...d.teams.map((t) => [t.id, t.name])], wb.team)}${wbSelect('wb-position', 'Position', [['', 'All positions'], ...[...new Set(d.players.map((p) => p.position).filter(Boolean))].sort().map((p) => [p, p])], wb.position)}${wbSelect(
          'wb-min',
          'Appearances',
          [
            [0, 'Include unused squad players'],
            [1, '1+ imported appearances'],
            [3, '3+ imported appearances'],
            [5, '5+ imported appearances'],
          ],
          wb.min,
        )}${wbSelect(
          'wb-sort',
          'Sort by totals',
          [
            ['totalGoals', 'Goals'],

            ['totalShots', 'Shots'],
          ],
          wb.sort,
        )}
      </div>
      ${wbTable(
        ['Player / club', 'Position', 'Apps', 'Starts', 'Goals', 'Shots'],
        rows
          .slice((wb.page - 1) * 40, wb.page * 40)
          .map(
            (p) =>
              `<tr><td><button class="player-link" data-player="${p.id}:${p.team_id}">${portrait(p, d)}<span>${esc(p.name)}<small>${esc(p.team)}</small></span></button></td><td>${esc(p.position || '—')}</td><td>${p.matches}</td><td>${p.starts}</td><td>${p.stats.totalGoals ?? '—'}</td><td>${p.stats.totalShots ?? '—'}</td></tr>`,
          ),
        'Historical player statistics',
      )}
      <div class="pagination">
        <button class="secondary" data-wb-page="${wb.page - 1}" ${wb.page <= 1 ? 'disabled' : ''}>
          ← Previous</button
        ><span>${rows.length} players · ${wb.page} / ${pages}</span
        ><button
          class="secondary"
          data-wb-page="${wb.page + 1}"
          ${wb.page >= pages ? 'disabled' : ''}
        >
          Next →
        </button>
      </div>
      ${rows.length ? '' : empty('No players match these filters. Try a lower appearance threshold.')}
      <p class="table-note">
        A dash means unavailable. Totals cover imported historical appearances. For estimated per-90
        rates, open Event & scouting lab. This source has no shot xG. Select a player for
        field-level coverage.
      </p>
    </section>`;
}
function oppositionBrief(d, id) {
  const team = d.teams.find((t) => t.id === id);
  if (!team) return '';
  const games = d.matches.filter((m) => m.teams.some((t) => t.id === id)).slice(-5);
  const average = (key, opponent = false) => {
    const values = games
      .map((m) => m.teams.find((t) => (opponent ? t.id !== id : t.id === id))?.stats[key])
      .filter((v) => v != null);
    return {
      value: values.length ? values.reduce((a, b) => a + b, 0) / values.length : null,
      n: values.length,
    };
  };
  const sf = average('totalShots'),
    sa = average('totalShots', true);
  return wbPanel(
    'Opposition briefing',
    `<div class="profile-head">${crest(team)}<div><h3>${esc(team.name)}</h3><p class="muted">Last ${games.length} imported completed matches · descriptive evidence</p></div></div><div class="mini-stats">${[
      ['Shots for / match', sf],
      ['Shots against / match', sa],
    ]
      .map(
        ([l, v]) =>
          `<div><strong>${decimal(v.value)}</strong><span>${l}</span><small>${v.n} matches with data</small></div>`,
      )
      .join(
        '',
      )}</div><div class="brief-grid"><div><h3>Observation</h3><p>${sf.value !== null && sa.value !== null ? `Shot balance is ${(sf.value - sa.value).toFixed(1)} per match across the available sample. Shot volume does not describe chance quality.` : 'Not enough shot data to describe the balance.'}</p></div><div><h3>Video questions</h3><p>Where do those shots come from? Separate settled attacks, transitions and set pieces. Check the score state and opposition before inferring a repeatable weakness.</p></div><div><h3>Next decision</h3><p>Use this as a preparation checklist. Confirm patterns in full-match video before recommending pressing triggers, marking assignments or a recruitment decision.</p></div></div><p class="muted">Sample dates: ${games.map((m) => day(m.date.slice(0, 10))).join(' · ')}. No tracking data or automated tactical diagnosis.</p><button class="secondary" data-export-brief="${esc(id)}">Download briefing notes ↓</button>`,
  );
}
function matchLabView(d) {
  const matches = [...d.matches].reverse();
  if (!matches.length) return empty('No completed match reports available.');
  if (!matches.some((m) => m.id === wb.match)) wb.match = matches[0].id;
  if (!d.teams.some((t) => t.id === wb.briefTeam)) wb.briefTeam = d.teams[0]?.id;
  const m = matches.find((m) => m.id === wb.match),
    h = m.teams.find((t) => t.venue === 'home'),
    a = m.teams.find((t) => t.venue === 'away');
  const metrics = [
    ['Possession %', 'possessionPct'],
    ['Shots', 'totalShots'],
    ['Shots on target', 'shotsOnTarget'],
    ['Corners', 'wonCorners'],
    ['Completed passes', 'accuratePasses'],
    ['Pass attempts', 'totalPasses'],
    ['Interceptions', 'interceptions'],
    ['Tackles', 'totalTackles'],
    ['Fouls', 'foulsCommitted'],
    ['Yellow cards', 'yellowCards'],
    ['Red cards', 'redCards'],
  ];
  return /* HTML */ `${wbSource(d)}
    <div class="toolbar">
      ${wbSelect(
        'wb-match',
        'Completed match',
        matches.map((m) => [
          m.id,
          `${m.date.slice(0, 10)} · ${m.teams.find((t) => t.venue === 'home').name} vs ${m.teams.find((t) => t.venue === 'away').name}`,
        ]),
        wb.match,
      )}
    </div>
    <section class="panel match-hero">
      <p class="eyebrow">MATCH REPORT · ${day(m.date.slice(0, 10))}</p>
      <div class="scoreboard">
        <div>
          ${crest(d.teams.find((t) => t.id === h.id))}
          <h2>${esc(h.name)}</h2>
        </div>
        <strong>${h.goals}<span>:</span>${a.goals}</strong>
        <div>
          ${crest(d.teams.find((t) => t.id === a.id))}
          <h2>${esc(a.name)}</h2>
        </div>
      </div>
      <p>
        Final result · Summary acquired ${stamp(m.fetched_at)} ·
        <a href="${esc(m.source_url)}" target="_blank" rel="noopener">Check source ↗</a>
      </p>
    </section>
    <div class="method-grid">
      ${wbPanel(
        'The game in numbers',
        wbTable(
          [esc(h.name), 'Metric', esc(a.name)],
          metrics
            .filter(([, key]) => h.stats[key] != null || a.stats[key] != null)
            .map(
              ([name, key]) =>
                `<tr><td>${h.stats[key] ?? '—'}</td><td>${name}</td><td>${a.stats[key] ?? '—'}</td></tr>`,
            ),
          'Team match statistics',
        ),
      )}${wbPanel('Decisive moments', m.moments.map((e) => `<div class="timeline-row"><strong>${esc(e.clock)}</strong><span class="moment-dot ${e.red_card ? 'red' : ''}"></span><div><strong>${e.red_card ? 'Red card' : e.own_goal ? 'Own goal' : 'Goal'}</strong><p>${esc(e.players.filter(Boolean).join(' · '))}</p></div></div>`).join('') || '<p>Timeline detail is not imported in this summary. The final score above comes from the match record; inspect the event shot maps for located shots.</p>', 'Goals and dismissals only')}
    </div>
    ${wbPanel(
      'Lineups & appearances',
      wbTable(
        ['Player', 'Team', 'Role', 'Start', 'Goals', 'Shots'],
        m.players.map(
          (p) =>
            `<tr><td>${esc(p.name)}</td><td>${esc(m.teams.find((t) => t.id === p.team_id)?.name)}</td><td>${esc(p.position || '—')}</td><td>${p.starter ? 'Yes' : 'No'}</td><td>${p.stats.totalGoals ?? '—'}</td><td>${p.stats.totalShots ?? '—'}</td></tr>`,
        ),
        'Match lineups',
      ),
      'Unused substitutes may appear; missing is not zero',
    )}
    <div class="toolbar">
      ${wbSelect(
        'wb-brief',
        'Prepare opposition notes',
        d.teams.map((t) => [t.id, t.name]),
        wb.briefTeam,
      )}
    </div>
    ${oppositionBrief(d, wb.briefTeam)}`;
}
const eventMetrics = [
  ['shots', 'Non-penalty shots'],
  ['key_passes', 'Key passes / assists'],
  ['progressive_passes', 'Progressive passes'],
  ['progressive_carries', 'Progressive accelerations'],
  ['interceptions', 'Interception attempts'],
];
function eventProfile(d) {
  const p = d.player_rows.find((p) => `${p.id}:${p.team_id}` === wb.eventPlayer);
  if (!p) return '';
  const peers = d.player_rows.filter((r) => r.position === p.position && r.minutes >= wb.minutes);
  const eligible = p.minutes >= wb.minutes && peers.length >= 5;
  const percentile = (key) => {
    const values = peers.map((r) => r.per90[key]);
    const x = p.per90[key];
    return (
      (100 *
        (values.filter((v) => v < x).length + 0.5 * (values.filter((v) => v === x).length - 1))) /
      (values.length - 1)
    );
  };
  const profile = eventMetrics
    .map(
      ([key, name]) =>
        `<div class="percentile-row"><span>${name}</span><strong>${decimal(p.per90[key])}</strong><div class="percentile-track"><i style="width:${eligible ? percentile(key) : 0}%"></i></div><span>${eligible ? Math.round(percentile(key)) + 'th' : '—'}</span></div>`,
    )
    .join('');
  return wbPanel(
    `${esc(p.name)} · player profile`,
    `<p>${esc(p.team)} · ${p.position} · ${p.minutes.toFixed(0)} estimated minutes / ${p.matches} matches.</p><p class="muted">Per 90 and same-position percentiles. ${peers.length} eligible player-club records with ≥${wb.minutes} minutes in this dataset. More activity is not necessarily better performance.</p>${profile}${eligible ? '' : '<div class="notice">Percentiles need at least five eligible peers and the selected player must meet the minutes threshold.</div>'}<p class="muted">Historical, provider-selected matches. Team role, possession share and opposition can dominate these differences; do not treat this profile as a transfer recommendation.</p><button class="secondary" data-open-player-map="${p.id}:${p.team_id}">Explore this player’s heatmap ↗</button>`,
  );
}
function shotMap(m, teamId) {
  const shots = m.shots.filter((s) => s.team_id === teamId);
  return /* HTML */ `<svg
      class="shot-pitch"
      viewBox="-4 -4 128 88"
      role="img"
      aria-label="Shot locations; all teams attack toward the right. Equal circle sizes; lime indicates a goal."
    >
      <rect
        x="0"
        y="0"
        width="120"
        height="80"
        rx="1"
        fill="#153b2d"
        stroke="#89ac91"
        stroke-width=".5"
      />
      <path
        d="M60 0V80M0 18H18V62H0M120 18H102V62H120M0 30H6V50H0M120 30H114V50H120"
        fill="none"
        stroke="#89ac91"
        stroke-width=".5"
      />
      <circle cx="60" cy="40" r="10" fill="none" stroke="#89ac91" stroke-width=".5" />
      ${shots.map((s) => `<circle cx="${s.x}" cy="${s.y}" r="2" fill="${s.goal ? '#c6f36b' : '#fff'}" fill-opacity=".8" stroke="#101e18" stroke-width=".4"><title>${esc(s.player)} · ${s.minute}′ · ${esc(s.outcome)}</title></circle>`).join('')}
    </svg>
    <p class="muted">
      Attack → · Equal marker sizes · Lime = goal · White = other outcome. Coordinates are rescaled
      from 0–100 to 120 × 80 display units. This dataset has no xG.
    </p>`;
}
function eventMatchView(m) {
  if (!m) return empty('Loading event detail…');
  if (m.error) return empty(esc(m.error));
  return wbPanel(
    `${esc(m.home)} ${m.hg}–${m.ag} ${esc(m.away)}`,
    `<p class="muted">${day(m.date)} · ${m.events.toLocaleString()} historical events · Pappalardo / Wyscout · CC BY 4.0</p><div class="method-grid">${[
      [m.home_id, m.home],
      [m.away_id, m.away],
    ]
      .map(
        ([id, name]) =>
          `<div><h3>${esc(name)} · ${m.shots.filter((s) => s.team_id === id).length} located shots</h3>${shotMap(m, id)}</div>`,
      )
      .join(
        '',
      )}</div><details><summary>Accessible shot table · ${m.shots.length} shots</summary>${wbTable(
      ['Minute', 'Player', 'Outcome', 'Body part', 'Type'],
      m.shots.map(
        (s) =>
          `<tr><td>${s.minute.toFixed(1)}′</td><td>${esc(s.player)}</td><td>${esc(s.outcome)}</td><td>${esc(s.body_part)}</td><td>${s.penalty ? 'Penalty' : esc(s.play_pattern)}</td></tr>`,
      ),
      'Historical shots',
    )}</details><p class="muted">This archive does not provide xG or explicit pass recipients. Shot counts do not measure chance quality. Coordinates describe recorded actions, not off-ball positions.</p><a href="${esc(m.source_url)}">Original licensed event archive</a>`,
  );
}
function eventView() {
  const manifest = wbLoad('events_manifest.json');
  if (!manifest) return empty('Loading historical event catalogue…');
  if (manifest.error) return empty(esc(manifest.error));
  const sets = manifest.sets.filter((s) => s.league === leagueId);
  if (!sets.length) return empty('No event datasets imported for this league.');
  if (!sets.some((s) => s.key === wb.set))
    wb.set = sets.find((s) => s.imported_matches >= 300)?.key || sets[0].key;
  const d = wbLoad(`events_${wb.set}.json`);
  if (!d) return empty('Loading player event data…');
  if (d.error) return empty(esc(d.error));
  if (!d.matches.some((m) => String(m.id) === wb.eventMatch))
    wb.eventMatch = String(d.matches.at(-1)?.id || '');
  const match = wb.eventMatch ? wbLoad(`event_matches/${wb.eventMatch}.json`) : null;
  const players = d.player_rows
    .filter(
      (p) =>
        p.minutes >= wb.minutes &&
        (!wb.eventPosition || p.position === wb.eventPosition) &&
        (!wb.eventSearch || wbFold(p.name + ' ' + p.team).includes(wbFold(wb.eventSearch))),
    )
    .sort((a, b) => (b.per90[wb.eventSort] || 0) - (a.per90[wb.eventSort] || 0));
  const eventPages = Math.max(1, Math.ceil(players.length / 30));
  wb.eventPage = Math.min(wb.eventPage, eventPages);
  return /* HTML */ `<div class="event-banner">
      <div>
        <p class="eyebrow">HISTORICAL EVENT LAB</p>
        <h2>See the actions behind the result.</h2>
        <p>${esc(d.coverage_note)}</p>
      </div>
      <span class="pill">2017/18 · CC BY 4.0</span>
    </div>
    <div class="toolbar">
      ${wbSelect(
        'wb-set',
        'Historical dataset',
        sets.map((s) => [s.key, `${s.competition} ${s.season} · ${s.imported_matches} matches`]),
        wb.set,
      )}
    </div>
    <div class="metrics">
      ${metric('Imported matches', d.imported_matches, `${d.available_matches} available from provider`)}${metric('Recorded events', d.events.toLocaleString(), 'Passes, duels, shots and more')}${metric('Player-club records', d.players, 'Stable provider IDs')}${metric('Season', esc(d.season), 'Historical research, not current')}
    </div>
    <div class="notice">
      ${esc(d.minutes_note)} Progression: ≥10 display units closer to goal, ending in the attacking
      40%; only completed progressive passes. Accelerations are a provider event type, not all
      carries.
    </div>
    ${scoutingPlot(d)} ${eventProfile(d)}
    <section class="panel">
      <div class="panel-head">
        <h2>Player scouting workspace</h2>
        <button class="secondary" data-view="heatmap">Explore heatmaps ↗</button
        ><a href="data/workbench/events_${esc(wb.set)}.json" download>Download dataset ↓</a>
      </div>
      <div class="toolbar wb-toolbar">
        <label for="wb-event-search"
          >Player or club<input
            id="wb-event-search"
            type="search"
            placeholder="Search historical players…"
            value="${esc(wb.eventSearch)}" /></label
        >${wbSelect(
          'wb-minutes',
          'Minimum minutes',
          [
            [90, '90 minutes'],
            [450, '450 minutes'],
            [900, '900 minutes'],
            [1800, '1,800 minutes'],
          ],
          wb.minutes,
        )}${wbSelect(
          'wb-event-position',
          'Position group',
          [
            ['', 'All positions'],
            ['GK', 'Goalkeepers'],
            ['DEF', 'Defenders'],
            ['MID', 'Midfielders'],
            ['FWD', 'Forwards'],
          ],
          wb.eventPosition,
        )}${wbSelect('wb-event-sort', 'Per-90 ranking', eventMetrics, wb.eventSort)}
      </div>
      ${wbTable(
        ['Player / club', 'Role', 'Min.', 'Shots/90', 'Key passes/90', 'Prog. passes/90'],
        players
          .slice((wb.eventPage - 1) * 30, wb.eventPage * 30)
          .map(
            (p) =>
              `<tr><td><button class="player-link" data-event-player="${p.id}:${p.team_id}"><span>${esc(p.name)}<small>${esc(p.team)}</small></span></button></td><td>${p.position}</td><td>${p.minutes.toFixed(0)}</td><td>${decimal(p.per90.shots)}</td><td>${decimal(p.per90.key_passes)}</td><td>${decimal(p.per90.progressive_passes)}</td></tr>`,
          ),
        'Historical scouting players',
      )}
      <div class="pagination">
        <button
          class="secondary"
          data-event-page="${wb.eventPage - 1}"
          ${wb.eventPage <= 1 ? 'disabled' : ''}
        >
          ← Previous</button
        ><span>${wb.eventPage} / ${eventPages}</span
        ><button
          class="secondary"
          data-event-page="${wb.eventPage + 1}"
          ${wb.eventPage >= eventPages ? 'disabled' : ''}
        >
          Next →
        </button>
      </div>
      <p class="table-note">
        ${players.length} eligible records. Full data available above. Select a player for
        positional percentiles.
      </p>
    </section>
    <div class="toolbar">
      ${wbSelect(
        'wb-event-match',
        'Explore a match',
        [...d.matches]
          .reverse()
          .map((m) => [m.id, `${m.date} · ${m.home} ${m.hg}–${m.ag} ${m.away}`]),
        wb.eventMatch,
      )}
    </div>
    ${eventMatchView(match)}`;
}
function forecastFixture(p) {
  const limited = Math.min(p.home_sample, p.away_sample) < 5;
  return `<article class="forecast-fixture"><div><span class="eyebrow">${day(p.date)}</span><h3>${esc(short(p.home))} <span class="muted">vs</span> ${esc(short(p.away))}</h3><small>${p.home_sample} home / ${p.away_sample} away venue matches · ${p.sample} training results</small>${limited ? '<p class="forecast-quality">Limited team sample · substantial prior influence</p>' : ''}<details><summary>Model inputs & explanation</summary><p>Training: ${day(p.training_start)}–${day(p.training_end)}. Prediction cutoff ${day(p.cutoff_exclusive)}, exclusive. Expected goals from result rates: ${p.home_rate.toFixed(2)} home / ${p.away_rate.toFixed(2)} away. These are not shot xG.</p><p>Eight prior games contribute ${Math.round(800 / (p.home_sample + 8))}% of the home venue rate and ${Math.round(800 / (p.away_sample + 8))}% of the away venue rate. The model excludes lineups, injuries and market odds.</p></details></div><div class="forecast-distribution"><div class="forecast-gauges">${p.probabilities.map((prob, i) => `<div class="forecast-gauge"><svg viewBox="0 0 120 80" role="img" aria-label="${['Home win', 'Draw', 'Away win'][i]} ${pct(prob)}"><path d="M15 65A45 45 0 0 1 105 65" fill="none" stroke="#2c3d54" stroke-width="8" pathLength="100"/><path d="M15 65A45 45 0 0 1 105 65" fill="none" stroke="${['#75decd', '#9bb4d6', '#eab174'][i]}" stroke-width="8" stroke-linecap="round" pathLength="100" stroke-dasharray="${100 * prob} 100"/></svg><strong>${pct(prob)}</strong><span>${['Home win', 'Draw', 'Away win'][i]}</span></div>`).join('')}</div></div></article>`;
}
function forecastView(d) {
  const expiry = Date.parse(d.publication?.valid_until);
  const expired = !Number.isFinite(expiry) || Date.now() >= expiry;
  if (expired)
    d = {
      ...d,
      upcoming: [],
      publication: {
        allowed: false,
        reason:
          d.publication?.allowed === false
            ? d.publication.reason
            : 'The verified forecast inputs have expired. A fresh source check is required.',
      },
    };
  d = { ...d, upcoming: d.upcoming.filter((p) => p.date > new Date().toISOString().slice(0, 10)) };
  const e = d.by_season[wb.evalSeason] || d.evaluation;
  const replay = !d.upcoming.length ? wbLoad(`backtest_${leagueId}.json`)?.records?.at(-1) : null;
  const improvement = e.n
    ? (100 * (e.metrics.baseline.log_loss - e.metrics.probabilities.log_loss)) /
      e.metrics.baseline.log_loss
    : null;
  return `<div class="notice"><strong>Experimental forecasts as of ${day(d.as_of)} · ${esc(d.season)}.</strong> Training excludes results on or after this date. ${Date.now() - Date.parse(d.built_at) > 36 * 3600000 ? '<strong>This forecast snapshot is older than 36 hours.</strong> ' : ''}Lineups, injuries and team news are not included.</div>
    <div class="metrics">${metric('Results in the archive', d.history_matches.toLocaleString(), 'Training uses the preceding 365 days')}${metric('Evaluation matches', e.n.toLocaleString(), e.n ? `${day(e.first_date)} – ${day(e.last_date)}` : 'No evaluation available')}${metric('Model log loss', e.n ? e.metrics.probabilities.log_loss.toFixed(3) : '—', 'Lower is better')}${metric('Frequency baseline', e.n ? e.metrics.baseline.log_loss.toFixed(3) : '—', 'Same fixtures, same training window')}</div>
    ${e.n ? `<div class="forecast-evidence"><div><strong>${improvement > 0 ? 'Lower historical error than the league-frequency baseline' : 'The model does not beat the league-frequency baseline'}</strong><p>Reconstructed evaluation · ${e.n.toLocaleString()} matches. This is historical evidence, not a guarantee of future accuracy.</p></div><div class="evidence-value">${Math.abs(improvement).toFixed(1)}%<small>${improvement > 0 ? 'lower' : 'higher'} log loss</small></div></div>` : ''}
    ${d.publication?.allowed === false ? `<div class="notice"><strong>Upcoming probabilities withheld.</strong> ${esc(d.publication.reason)}</div>` : ''}
    ${replay ? wbPanel('Historical fixture replay', `<span class="replay-label">RETROSPECTIVE BACKTEST · NOT A LIVE PREDICTION</span>${forecastFixture(replay)}<p class="muted">Recorded outcome: ${['home win', 'draw', 'away win'][replay.actual]}. Probabilities were reconstructed with results strictly before the fixture date. They were not published before this match. Experimental model; no demonstrated live edge.</p>`) : ''}
    ${wbPanel('Upcoming fixtures', d.upcoming.length ? d.upcoming.slice(0, 6).map(forecastFixture).join('') + (d.upcoming.length > 6 ? `<details class="forecast-more"><summary>Show ${d.upcoming.length - 6} more scheduled fixtures</summary>${d.upcoming.slice(6).map(forecastFixture).join('')}</details>` : '') : empty(d.publication?.allowed === false ? 'Probabilities will return when the data checks pass.' : 'No eligible fixtures within the next 14 days.'), 'Next 14 days · Home / Draw / Away')}
    <div class="toolbar">${wbSelect('wb-eval-season', 'Evaluation period', [['', 'All evaluation seasons'], ...Object.keys(d.by_season).map((s) => [s, s])], wb.evalSeason)}</div>
    ${
      e.n
        ? `<div class="method-grid">${wbPanel(
            'Performance against baselines',
            wbTable(
              ['Model', 'Log loss', 'Brier', 'RPS'],
              [
                ['probabilities', 'Venue Poisson'],
                ['baseline', 'League frequency'],
                ['uniform', 'Equal probabilities'],
                ['elo', 'Elo / Davidson'],
                ['fitted_poisson', 'Fitted attack / defence'],
              ]
                .filter(([key]) => e.metrics[key])
                .map(
                  ([key, name]) =>
                    `<tr><td>${name}</td><td>${e.metrics[key].log_loss.toFixed(3)}</td><td>${e.metrics[key].brier.toFixed(3)}</td><td>${e.metrics[key].rps.toFixed(3)}</td></tr>`,
                ),
              'Forecast validation metrics',
            ) +
              `<p>Challengers use fixed specifications and earlier data only. No model is promoted on these retrospective scores.</p><p>Model minus frequency log-loss difference, 95% date-block bootstrap interval: <strong>${e.log_loss_delta_95ci.map((n) => n.toFixed(3)).join(' to ')}</strong>.</p><p class="muted">${esc(e.note)} Brier sums three outcomes (0–2). RPS order: home, draw, away. Lower is better for all three scores.</p>`,
          )}${wbPanel(
            'Calibration · predicted vs observed',
            `<svg class="calibration-chart" viewBox="0 0 320 270" role="img" aria-label="Forecast calibration; points on the dashed diagonal match the observed rate"><g stroke="#e3e9e4">${[0, 0.25, 0.5, 0.75, 1].map((v) => `<path d="M45 ${225 - v * 200}H295M${45 + v * 250} 25V225"/>`).join('')}</g><path d="M45 225L295 25" stroke="#81998b" stroke-dasharray="5 5"/>${e.calibration.map((b) => `<circle cx="${45 + 250 * b.predicted}" cy="${225 - 200 * b.observed}" r="${3 + Math.min(7, Math.sqrt(b.n) / 8)}" fill="#147d67" fill-opacity=".8" stroke="white"><title>${pct(b.predicted)} predicted; ${pct(b.observed)} observed; ${b.n} outcome probabilities</title></circle>`).join('')}<g fill="#63716d" font-size="10">${[0, 0.5, 1].map((v) => `<text x="${45 + v * 250}" y="243" text-anchor="middle">${v * 100}%</text><text x="36" y="${229 - v * 200}" text-anchor="end">${v * 100}%</text>`).join('')}<text x="170" y="262" text-anchor="middle">Predicted probability</text><text x="45" y="13">Observed frequency</text></g></svg><p class="muted">Home/draw/away probabilities pooled into ten bins. Circle size reflects sample count. This is a diagnostic, not a calibration adjustment.</p><details><summary>Calibration values</summary>${wbTable(
              ['Predicted', 'Observed', 'Count'],
              e.calibration.map(
                (b) =>
                  `<tr><td>${pct(b.predicted)}</td><td>${pct(b.observed)}</td><td>${b.n}</td></tr>`,
              ),
              'Calibration bins',
            )}</details>`,
          )}</div>`
        : empty('Insufficient historical matches for evaluation in this period.')
    }
    ${
      e.n
        ? wbPanel(
            'Outcome calibration and challenger uncertainty',
            `<details><summary>Home, draw and away calibration</summary>${Object.entries(
              e.calibration_by_outcome || {},
            )
              .map(
                ([label, bins]) =>
                  `<h3>${esc(label)}</h3>${wbTable(
                    ['Predicted', 'Observed', 'Count'],
                    bins.map(
                      (b) =>
                        `<tr><td>${pct(b.predicted)}</td><td>${pct(b.observed)}</td><td>${b.n}</td></tr>`,
                    ),
                    'Calibration for ' + label,
                  )}`,
              )
              .join('')}</details>${wbTable(
              ['Comparator', 'Model minus comparator log loss · 95% interval'],
              Object.entries(e.comparison_95ci || {}).map(
                ([name, ci]) =>
                  `<tr><td>${esc(name)}</td><td>${ci.map((v) => v.toFixed(3)).join(' to ')}</td></tr>`,
              ),
              'Challenger uncertainty',
            )}<p class="muted">Negative favors the displayed venue model. These descriptive intervals do not adjust for multiple comparisons. See the downloadable predictions for exact fixtures and training cutoffs.</p>`,
          )
        : ''
    }
    ${wbPanel('Published before the match', `<p><strong>${d.prospective?.settled || 0} settled forecasts</strong> from ${(d.prospective?.recorded || 0).toLocaleString()} stored predictions. Forecasts are fixed before the fixture date; revised dates and administrative results are excluded from scoring.</p>${d.prospective?.settled ? `<p>Observed outcome accuracy: ${pct(d.prospective.accuracy)}. Small samples are not evidence of reliable future performance.</p>` : '<p>Not enough prospective evidence yet. The historical evaluation above must not be described as a live prediction record.</p>'}<a href="data/workbench/forecast_log_${leagueId}.json" download>Download the timestamped forecast record</a>`)}
    ${wbPanel('Method & reproducibility', `<p>${esc(d.methodology)}</p><p>The backtest uses corrected results available now. It cannot reproduce every historical data delay or correction.</p><a href="data/workbench/backtest_${leagueId}.json" download>Download evaluation predictions ↓</a> · <a href="docs/MODEL_CARD.html">Model card ↗</a>`)}`;
}
