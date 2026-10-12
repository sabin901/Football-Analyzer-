'use strict';
// View functions return HTML from validated snapshots and the current filters.
// Current summaries and historical event data deliberately remain separate.
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
    `<div class="profile-head">${portrait(p, d)}<p>${p.matches} imported appearances · ${p.starts} starts. Squad age: ${p.age ?? 'unavailable'}. Provider ID ${esc(p.id)}.</p></div><div class="mini-stats">${[
      ['Goals', 'totalGoals'],
      ['Assists', 'goalAssists'],
      ['Shots', 'totalShots'],
      ['Shots on target', 'shotsOnTarget'],
    ]
      .map(
        ([label, key]) =>
          `<div><strong>${p.stats[key] ?? '—'}</strong><span>${label}</span><small>${p.stat_samples[key] || 0} matches with this field</small></div>`,
      )
      .join(
        '',
      )}</div><h3>Recent imported appearances</h3>${games.map((m) => `<button class="fixture-button" data-current-match="${m.id}">${day(m.date.slice(0, 10))}<span>${esc(m.teams.find((t) => t.venue === 'home').name)} vs ${esc(m.teams.find((t) => t.venue === 'away').name)}</span>Open report ↗</button>`).join('') || '<p>No recorded appearance yet.</p>'}<p class="muted">No reliable minutes in this feed. Totals are not a talent ranking and are not adjusted for playing time, opposition or team style.</p>`,
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
            ['goalAssists', 'Assists'],
            ['totalShots', 'Shots'],
            ['shotsOnTarget', 'Shots on target'],
          ],
          wb.sort,
        )}
      </div>
      ${wbTable(
        ['Player / club', 'Position', 'Apps', 'Starts', 'Goals', 'Assists', 'Shots'],
        rows
          .slice((wb.page - 1) * 40, wb.page * 40)
          .map(
            (p) =>
              `<tr><td><button class="player-link" data-player="${p.id}:${p.team_id}">${portrait(p, d)}<span>${esc(p.name)}<small>${esc(p.team)}</small></span></button></td><td>${esc(p.position || '—')}</td><td>${p.matches}</td><td>${p.starts}</td><td>${p.stats.totalGoals ?? '—'}</td><td>${p.stats.goalAssists ?? '—'}</td><td>${p.stats.totalShots ?? '—'}</td></tr>`,
          ),
        'Current player statistics',
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
        A dash means unavailable. Totals cover imported appearances. Reliable minutes and current
        shot xG are unavailable; no per-90 ranking is calculated. Select a player for field-level
        coverage.
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
    sa = average('totalShots', true),
    pos = average('possessionPct');
  return wbPanel(
    'Opposition briefing',
    `<div class="profile-head">${crest(team)}<div><h3>${esc(team.name)}</h3><p class="muted">Last ${games.length} imported completed matches · descriptive evidence</p></div></div><div class="mini-stats">${[
      ['Shots for / match', sf],
      ['Shots against / match', sa],
      ['Possession %', pos],
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
          metrics.map(
            ([name, key]) =>
              `<tr><td>${h.stats[key] ?? '—'}</td><td>${name}</td><td>${a.stats[key] ?? '—'}</td></tr>`,
          ),
          'Team match statistics',
        ),
      )}${wbPanel('Decisive moments', m.moments.map((e) => `<div class="timeline-row"><strong>${esc(e.clock)}</strong><span class="moment-dot ${e.red_card ? 'red' : ''}"></span><div><strong>${e.red_card ? 'Red card' : e.own_goal ? 'Own goal' : 'Goal'}</strong><p>${esc(e.players.filter(Boolean).join(' · '))}</p></div></div>`).join('') || '<p>No goals or dismissals recorded.</p>', 'Goals and dismissals only')}
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
  ['npxg', 'Non-penalty xG'],
  ['shots', 'Non-penalty shots'],
  ['key_passes', 'Shot assists'],
  ['progressive_passes', 'Progressive passes'],
  ['progressive_carries', 'Progressive carries'],
  ['pressures', 'Pressure events'],
  ['recoveries', 'Ball recoveries'],
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
      aria-label="Shot locations; all teams attack toward the right. Circles sized by expected goals; lime indicates a goal."
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
      ${shots.map((s) => `<circle cx="${s.x}" cy="${s.y}" r="${1 + 4 * Math.sqrt(s.xg)}" fill="${s.goal ? '#c6f36b' : '#fff'}" fill-opacity=".8" stroke="#101e18" stroke-width=".4"><title>${esc(s.player)} · ${s.minute}′ · ${esc(s.outcome)} · xG ${decimal(s.xg)}</title></circle>`).join('')}
    </svg>
    <p class="muted">
      Attack → · Circle area increases with xG · Lime = goal · White = other outcome. Coordinates
      use the provider’s 120 × 80 pitch.
    </p>`;
}
function eventMatchView(m) {
  if (!m) return empty('Loading event detail…');
  if (m.error) return empty(esc(m.error));
  return (
    wbPanel(
      `${esc(m.home)} ${m.hg}–${m.ag} ${esc(m.away)}`,
      `<p class="muted">${day(m.date)} · ${m.events.toLocaleString()} recorded events · StatsBomb provider xG</p><div class="method-grid">${[
        [m.home_id, m.home],
        [m.away_id, m.away],
      ]
        .map(([id, name]) => {
          const shots = m.shots.filter((s) => s.team_id === id);
          return /* HTML */ `<div>
            <h3>${esc(name)} · ${decimal(shots.reduce((n, s) => n + s.xg, 0))} xG</h3>
            ${shotMap(m, id)}
          </div>`;
        })
        .join(
          '',
        )}</div><details><summary>Accessible shot table · ${m.shots.length} shots</summary>${wbTable(
        ['Minute', 'Player', 'Outcome', 'xG', 'Type'],
        m.shots.map(
          (s) =>
            `<tr><td>${s.minute}′</td><td>${esc(s.player)}</td><td>${esc(s.outcome)}</td><td>${decimal(s.xg)}</td><td>${s.penalty ? 'Penalty' : esc(s.play_pattern)}</td></tr>`,
        ),
        'Historical shots',
      )}</details><details><summary>Most frequent completed pass connections</summary>${wbTable(
        ['From', 'To', 'Passes'],
        m.pass_links
          .slice(0, 16)
          .map(
            (l) =>
              `<tr><td>${esc(m.players.find((p) => p.id === l.from)?.name || l.from)}</td><td>${esc(m.players.find((p) => p.id === l.to)?.name || l.to)}</td><td>${l.count}</td></tr>`,
          ),
        'Pass connections',
      )}</details><p class="muted">xG describes shot quality, not a deserved result. Penalties are included in match xG; player npxG excludes them. Pass counts do not measure line-breaking or pressure resistance.</p>`,
    ) + xgFlow(m)
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
      <img
        src="https://raw.githubusercontent.com/statsbomb/open-data/master/img/SB%20-%20Icon%20Lockup%20-%20Colour%20positive.png"
        alt="StatsBomb"
        width="150"
        loading="lazy"
      />
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
      ${metric('Imported matches', d.imported_matches, `${d.available_matches} available from provider`)}${metric('Recorded events', d.events.toLocaleString(), 'Passes, carries, shots and more')}${metric('Player-club records', d.players, 'Stable provider IDs')}${metric('Season', esc(d.season), 'Historical research, not current')}
    </div>
    <div class="notice">
      ${esc(d.minutes_note)} Progression: ≥10 provider units closer to goal, ending at x ≥72; only
      completed progressive passes. Pressure counts describe activity, not effectiveness.
    </div>
    ${eventProfile(d)}
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
        ['Player / club', 'Role', 'Min.', 'npxG/90', 'Key passes/90', 'Prog. passes/90'],
        players
          .slice((wb.eventPage - 1) * 30, wb.eventPage * 30)
          .map(
            (p) =>
              `<tr><td><button class="player-link" data-event-player="${p.id}:${p.team_id}"><span>${esc(p.name)}<small>${esc(p.team)}</small></span></button></td><td>${p.position}</td><td>${p.minutes.toFixed(0)}</td><td>${decimal(p.per90.npxg)}</td><td>${decimal(p.per90.key_passes)}</td><td>${decimal(p.per90.progressive_passes)}</td></tr>`,
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
function forecastView(d) {
  const e = d.by_season[wb.evalSeason] || d.evaluation;
  return /* HTML */ `<div class="notice">
      <strong>Forecast cut-off: ${day(d.as_of)} · ${esc(d.season)}.</strong> Results on or after the
      cut-off date are excluded. Early-season or promoted teams may fall back toward league
      averages. These are experimental probabilities, not certain outcomes.
    </div>
    <div class="metrics">
      ${metric('Historical results', d.history_matches.toLocaleString(), 'Imported for this league')}${metric('Unseen-date tests', e.n.toLocaleString(), 'Rolling evaluation from July 2024')}${metric('Model log loss', decimal(e.metrics.probabilities.log_loss), 'Lower is better')}${metric('Frequency baseline', decimal(e.metrics.baseline.log_loss), 'Same fixtures, same training window')}
    </div>
    ${wbPanel('Upcoming · next 14 days', d.upcoming.length ? d.upcoming.map((p) => `<div class="forecast-fixture"><div><span class="muted">${day(p.date)}</span><h3>${esc(short(p.home))} <span class="muted">vs</span> ${esc(short(p.away))}</h3><small>${p.sample} prior results · ${p.home_sample} home / ${p.away_sample} away samples</small></div><div class="forecast-chances">${['Home', 'Draw', 'Away'].map((n, i) => `<div><strong>${pct(p.probabilities[i])}</strong><span>${n}</span></div>`).join('')}</div></div>`).join('') : empty('No scheduled fixtures within the next 14 days.'), 'Schedule changes and team news are not modeled')}
    <div class="toolbar">
      ${wbSelect('wb-eval-season', 'Evaluation period', [['', 'All evaluation seasons'], ...Object.keys(d.by_season).map((s) => [s, s])], wb.evalSeason)}
    </div>
    <div class="method-grid">
      ${wbPanel(
        'Does the model improve on simple baselines?',
        wbTable(
          ['Model', 'Log loss', 'Brier', 'RPS'],
          [
            ['probabilities', 'Venue Poisson'],
            ['baseline', 'League frequency'],
            ['uniform', 'Equal probabilities'],
          ].map(
            ([key, name]) =>
              `<tr><td>${name}</td><td>${e.metrics[key].log_loss.toFixed(3)}</td><td>${e.metrics[key].brier.toFixed(3)}</td><td>${e.metrics[key].rps.toFixed(3)}</td></tr>`,
          ),
          'Forecast validation metrics',
        ) +
          `<p>Model minus frequency log-loss difference, 95% date-block bootstrap interval: <strong>${e.log_loss_delta_95ci.map((n) => n.toFixed(3)).join(' to ')}</strong>.</p><p class="muted">${esc(e.note)} Brier uses the sum across three outcomes (range 0–2). RPS order: home, draw, away. Lower scores are better.</p>`,
      )}${wbPanel(
        'Calibration · predicted versus observed',
        `<svg class="calibration-chart" viewBox="0 0 310 250" role="img" aria-label="Calibration chart comparing forecast probabilities to observed outcome rates"><path d="M35 15V215H285M35 215L275 25" stroke="#a4b2a3" fill="none" stroke-dasharray="4 4"/>${e.calibration.map((b) => `<circle cx="${35 + 240 * b.predicted}" cy="${215 - 190 * b.observed}" r="${3 + Math.min(7, Math.sqrt(b.n) / 8)}" fill="#256345"><title>${pct(b.predicted)} predicted; ${pct(b.observed)} observed; ${b.n} outcome probabilities</title></circle>`).join('')}<text x="35" y="235">0%</text><text x="240" y="235">100%</text><text x="95" y="248">Predicted probability</text><text x="0" y="20">100%</text></svg><p class="muted">Pooled home/draw/away probabilities in ten bins. Points near the diagonal agree with observed rates. This is a diagnostic, not post-hoc calibration.</p><details><summary>Calibration values</summary>${wbTable(
          ['Predicted', 'Observed', 'Count'],
          e.calibration.map(
            (b) =>
              `<tr><td>${pct(b.predicted)}</td><td>${pct(b.observed)}</td><td>${b.n}</td></tr>`,
          ),
          'Calibration bins',
        )}</details>`,
      )}
    </div>
    ${wbPanel(
      'Season scenarios · uncertainty stays visible',
      `<p>${d.scenarios.runs.toLocaleString()} simulations of ${d.scenarios.simulated_fixtures} remaining fixtures. ${d.scenarios.omitted_fixtures} unresolved fixtures omitted.</p>${wbTable(
        ['Team', 'Mean points', '10–90% range', 'Finish first', 'Top four'],
        [...d.scenarios.teams]
          .sort((a, b) => b.mean_points - a.mean_points)
          .map(
            (t) =>
              `<tr><td>${esc(short(t.team))}</td><td>${t.mean_points}</td><td>${t.points_10}–${t.points_90}</td><td>${pct(t.first)}</td><td>${pct(t.top_four)}</td></tr>`,
          ),
        'Season simulations',
      )}<p class="muted">${esc(d.scenarios.limitations)} These long-horizon scenarios have not been independently validated.</p>`,
    )}${wbPanel('Reproduce and challenge the result', `<p>${esc(d.methodology)}</p><p>Reconstructed historical evaluation uses the provider’s corrected results available now. It cannot reproduce every data delay or correction that occurred at the time.</p><a href="data/workbench/backtest_${leagueId}.json" download>Download every evaluation prediction ↓</a><br><a href="docs/MODEL_CARD.html">Read the model card ↗</a>`)} `;
}
function portfolioView() {
  const c = wbLoad('catalogue.json');
  return /* HTML */ `<section class="panel portfolio-hero">
      <p class="eyebrow">BUILT FOR THE FOOTBALL QUESTION</p>
      <h2>Evidence. Interpretation.<br />A decision someone can use.</h2>
      <p>
        A research portfolio connecting football analysis with dependable software. Every claim
        should be traceable to data, a method and a clearly stated limitation.
      </p>
      <div class="toolbar">
        <a class="secondary" href="docs/PROJECT_REVIEW.html">Project comparison ↗</a
        ><a class="secondary" href="docs/APPLICATION_GUIDE.html">Where to apply ↗</a
        ><a class="secondary" href="docs/CAREER_RESEARCH.html">Club role research ↗</a
        ><a class="secondary" href="docs/PORTFOLIO_PLAYBOOK.html">Case-study playbook ↗</a>
      </div>
    </section>
    ${c && !c.error ? `<div class="metrics">${metric('League-seasons', c.league_seasons, 'OpenFootball snapshots')}${metric('Recorded results', c.results.toLocaleString(), 'Across the five leagues')}${metric('Historical events', c.events.toLocaleString(), 'StatsBomb Open Data')}${metric('Current player records', c.current_players.toLocaleString(), 'Player × club, not unique people')}</div>` : ''}
    <div class="method-grid">
      ${wbPanel('01 · Prepare the next opponent', '<p>Start with the Match centre, inspect the recent shot balance and review the source match reports. Turn three observations into video questions and a concise coaching briefing.</p><button class="secondary" data-view="matchlab">Open match centre →</button>')}${wbPanel('02 · Profile a player fairly', '<p>Use the Event lab, set a minutes threshold and compare within a position group. Explain selection bias, role and team context before recommending further scouting.</p><button class="secondary" data-view="events">Open event lab →</button>')}${wbPanel('03 · Test a football hypothesis', '<p>Review the Forecast lab against simple baselines, inspect calibration and reproduce the cutoff for any evaluation match. Report what the model misses as carefully as what it predicts.</p><button class="secondary" data-view="forecast">Open forecast lab →</button>')}${wbPanel('04 · Demonstrate engineering', '<p>Explore a relational warehouse with stable IDs, documented sources, indexed tables, automated imports and regression tests. SQL exercises connect the data model to football questions.</p><a href="data/football.sqlite" download>Download SQLite warehouse ↓</a><br><a href="docs/analysis_queries.sql" download>Get the SQL examples ↓</a>')}
    </div>
    ${wbPanel('What clubs expect—and what still needs your work', '<p>Published Manchester City and Swansea roles emphasize tactical understanding, event data, SQL, visual communication and support for coaches. Leeds’ developer role emphasizes maintainable applications, cloud infrastructure, React/TypeScript and delivery into production.</p><p>This project demonstrates a subset of that work. Add your own written case studies, video-supported observations and experience presenting to a coach. A portfolio cannot substitute for those skills or guarantee recruitment.</p><p>Current full-event feeds, continuous tracking, medical data and licensed video are unavailable here. The open event selections are historical. The frontend uses vanilla JavaScript; it does not establish React/TypeScript experience.</p><a href="docs/CAREER_RESEARCH.html">Read the dated primary sources and skills matrix ↗</a>')}`;
}
