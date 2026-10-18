'use strict';
// Lazy, same-origin snapshots keep the public site independent of API uptime.
const WORKBENCH_VIEWS = new Set(['players', 'matchlab', 'events', 'heatmap', 'forecast']);
const snapshotStore = createSnapshotStore(
  (file) => fetchJson(`data/workbench/${file}`),
  () => {
    if (WORKBENCH_VIEWS.has(view)) render();
  },
);
const wbCache = snapshotStore.cache;
const wbLoad = (file) => snapshotStore.load(file);
const wb = {
  search: '',
  team: '',
  position: '',
  min: 1,
  sort: 'totalGoals',
  page: 1,
  player: '',
  match: '',
  set: '',
  eventPlayer: '',
  eventMatch: '',
  minutes: 450,
  eventSort: 'npxg',
  eventPosition: '',
  briefTeam: '',
  eventSearch: '',
  eventPage: 1,
  evalSeason: '',
};
function crest(team) {
  const url = team?.logo;
  return url && /^https:\/\/a\.espncdn\.com\//.test(url)
    ? `<img class="club-crest" src="${esc(url)}" alt="" loading="lazy" width="36" height="36">`
    : `<span class="club-monogram" aria-hidden="true">${esc(
        (team?.name || 'FC')
          .split(' ')
          .map((s) => s[0])
          .join('')
          .slice(0, 3),
      )}</span>`;
}
function portrait(p, d) {
  return p.photo && /^https:\/\/a\.espncdn\.com\//.test(p.photo)
    ? `<img class="club-crest player-photo" src="${esc(p.photo)}" alt="" title="Provider portrait; kit may reflect an older club" width="44" height="44" loading="lazy">`
    : crest(d.teams.find((t) => t.id === p.team_id));
}
function wbSource(d) {
  return `<div class="notice source-note"><strong>${esc(d.season)} · ${esc(d.source)}</strong> · Snapshot built ${stamp(d.fetched_at)}${!d.refresh_ok ? ' · Some refresh requests failed. Retained data may be older.' : ''}${Date.now() - Date.parse(d.fetched_at) > 36 * 3600000 ? ' · STALE: this snapshot is older than 36 hours.' : ''}<br>${d.coverage.match_summaries} imported match summaries / ${d.coverage.schedule_results} recorded schedule results.</div>`;
}
function workbenchView(kind) {
  if (kind === 'heatmap') return heatmapView();
  if (kind === 'events') return eventView();
  const d = wbLoad(`${kind === 'forecast' ? 'forecast' : 'current'}_${leagueId}.json`);
  if (!d) return empty('Loading the analyst workspace…');
  if (d.error) return empty(`This dataset is unavailable: ${esc(d.error)}. Use Refresh to retry.`);
  return kind === 'forecast'
    ? forecastView(d)
    : kind === 'players'
      ? playersView(d)
      : matchLabView(d);
}
document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  if (b.dataset.player) {
    wb.player = b.dataset.player;
    render();
    $('#content').scrollIntoView({ block: 'start' });
  }
  if (b.dataset.currentMatch) {
    wb.match = b.dataset.currentMatch;
    showView('matchlab');
  }
  if (b.dataset.eventPlayer) {
    wb.eventPlayer = b.dataset.eventPlayer;
    render();
    $('#content').scrollIntoView({ block: 'start' });
  }
  if (b.dataset.eventPage) {
    wb.eventPage = Number(b.dataset.eventPage);
    render();
  }
  if (b.dataset.wbPage) {
    wb.page = Number(b.dataset.wbPage);
    render();
  }
  if (b.hasAttribute('data-export-players')) {
    const d = wbCache.get(`current_${leagueId}.json`);
    if (!d) return;
    const rows = d.players.filter(
      (p) =>
        (!wb.search || wbFold(p.name).includes(wbFold(wb.search))) &&
        (!wb.team || p.team_id === wb.team) &&
        (!wb.position || p.position === wb.position) &&
        p.matches >= wb.min,
    );
    downloadFile(
      `footlyzer-${leagueId}-players.csv`,
      toCsv([
        [
          'player_id',
          'player',
          'team',
          'position',
          'appearances',
          'goals',
          'assists',
          'goals_sample',
          'assists_sample',
          'source',
          'fetched_at',
        ],
        ...rows.map((p) => [
          p.id,
          p.name,
          p.team,
          p.position,
          p.matches,
          p.stats.totalGoals,
          p.stats.goalAssists,
          p.stat_samples.totalGoals,
          p.stat_samples.goalAssists,
          d.source,
          d.fetched_at,
        ]),
      ]),
      'text/csv;charset=utf-8',
    );
  }
  if (b.dataset.exportBrief) {
    const d = wbCache.get(`current_${leagueId}.json`),
      id = b.dataset.exportBrief,
      team = d.teams.find((t) => t.id === id),
      games = d.matches.filter((m) => m.teams.some((t) => t.id === id)).slice(-5);
    downloadFile(
      `footlyzer-${leagueId}-${id}-brief.md`,
      `# Opposition research: ${team.name}\n\nSource: ESPN. Snapshot: ${d.fetched_at}. Season: ${d.season}.\n\n## Evidence\n` +
        games
          .map((m) => {
            const t = m.teams.find((t) => t.id === id),
              o = m.teams.find((t) => t.id !== id);
            return `- ${m.date}: ${t.name} ${t.goals}–${o.goals} ${o.name}; shots ${t.stats.totalShots ?? 'missing'}–${o.stats.totalShots ?? 'missing'}; possession ${t.stats.possessionPct ?? 'missing'}%. Source: ${m.source_url}`;
          })
          .join('\n') +
        '\n\n## Questions to verify on video\n- Separate transitions, set pieces and settled attacks.\n- Check score state and opponent quality.\n- Identify repeatable patterns before recommending a tactical intervention.\n\n## Analyst interpretation\nAdd your observations and timestamped video evidence here.\n\n## Limits\nLast five imported matches only. No shot xG, reliable minutes, continuous tracking or injury context.\n',
    );
  }
});
document.addEventListener('change', (e) => {
  const mapping = {
    'wb-team': 'team',
    'wb-position': 'position',
    'wb-min': 'min',
    'wb-sort': 'sort',
    'wb-match': 'match',
    'wb-brief': 'briefTeam',
    'wb-set': 'set',
    'wb-minutes': 'minutes',
    'wb-event-position': 'eventPosition',
    'wb-event-sort': 'eventSort',
    'wb-event-match': 'eventMatch',
    'wb-eval-season': 'evalSeason',
  };
  const key = mapping[e.target.id];
  if (!key) return;
  wb[key] = ['min', 'minutes'].includes(key) ? Number(e.target.value) : e.target.value;
  wb.page = 1;
  wb.eventPage = 1;
  if (key === 'set') {
    wb.eventPlayer = '';
    wb.eventMatch = '';
    wb.eventSearch = '';
  }
  render();
});
document.addEventListener('input', (e) => {
  if (e.target.id !== 'wb-search') return;
  wb.search = e.target.value;
  wb.page = 1;
  const pos = e.target.selectionStart;
  render();
  $('#wb-search').focus();
  $('#wb-search').setSelectionRange(pos, pos);
});

document.addEventListener('input', (e) => {
  if (e.target.id !== 'wb-event-search') return;
  wb.eventSearch = e.target.value;
  wb.eventPage = 1;
  const pos = e.target.selectionStart;
  render();
  $('#wb-event-search').focus();
  $('#wb-event-search').setSelectionRange(pos, pos);
});
document.addEventListener(
  'error',
  (e) => {
    if (e.target instanceof HTMLImageElement && e.target.classList.contains('club-crest')) {
      const fallback = document.createElement('span');
      fallback.className = 'club-monogram';
      fallback.textContent = 'FC';
      fallback.setAttribute('aria-hidden', 'true');
      e.target.replaceWith(fallback);
    }
  },
  true,
);

document.addEventListener('click', (e) => {
  const b = e.target.closest('[data-open-player-map]');
  if (!b) return;
  const [player, team] = b.dataset.openPlayerMap.split(':');
  Object.assign(hs, {
    set: wb.set,
    scope: 'season',
    team,
    player,
    compare: '',
    action: 'all',
    period: 'all',
  });
  showView('heatmap');
});
