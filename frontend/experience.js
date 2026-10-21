'use strict';
// One identity renderer for result tables, fixtures, archives and forecasts.
// Original identifiers, not official club crests. Approved local assets can override them.
function teamIdentity(name, logo = '') {
  const label = String(name || 'Club');
  if (/^assets\/clubs\/[a-zA-Z0-9_-]+\.(svg|png|webp)$/.test(logo))
    return `<img class="club-crest" src="${esc(logo)}" alt="" width="36" height="36" loading="lazy" data-team-name="${esc(label)}">`;
  const key = wbFold(label)
    .replace(/\b(fc|cf|afc|ac|as|club)\b/g, '')
    .trim();
  let hash = 0;
  for (const char of key) hash = (Math.imul(hash, 31) + char.charCodeAt(0)) >>> 0;
  const colours = ['#a9d7cb', '#edb78f', '#a9bce5', '#d3b7dc', '#d4d69a', '#a4d0df'];
  const initials = label
    .split(/\s+/)
    .filter((s) => !/^(fc|cf|afc|ac|as)$/i.test(s))
    .map((s) => s[0])
    .join('')
    .slice(0, 3)
    .toUpperCase();
  return `<svg class="team-emblem" viewBox="0 0 48 52" aria-hidden="true"><title>${esc(label)} · Footlyzer identifier, not an official crest</title><path d="M3 3h42v31L24 49 3 34Z" fill="#172628" stroke="${colours[hash % colours.length]}" stroke-width="2"/><path d="M8 8h32v5H8zM8 33l16 11 16-11" fill="none" stroke="${colours[hash % colours.length]}" stroke-width="3"/><text x="24" y="30" text-anchor="middle" fill="#f5f1e6" font-size="${initials.length > 2 ? 13 : 16}" font-family="system-ui" font-weight="800">${esc(initials)}</text></svg>`;
}
const viewGuides = {
  overview: [
    'Read a season',
    'Start with the recorded results, then change venue and compare per-match rates. A computed table can differ from official standings.',
    'Open 2017/18 example',
  ],
  matches: [
    'Find the evidence',
    'Filter by team and result status. An empty score means unavailable or unplayed, never a draw.',
    'Open historical results',
  ],
  compare: [
    'Compare like for like',
    'Use the same season, venue and sample window. The line in each chart marks the match-weighted league average.',
    'Compare two historical teams',
  ],
  players: [
    'Explore a player',
    'Select a player row to open their profile. All records in this archive are from 2017/18.',
    'Open a player example',
  ],
  matchlab: [
    'Read a match',
    'Inspect the recorded shots, lineups and match summary. This is a historical archive, not today’s match centre.',
    'Open a match example',
  ],
  events: [
    'Investigate a pattern',
    'Start with the positional scatterplot, select a player and inspect the underlying actions before drawing a conclusion.',
    'Open event analysis',
  ],
  heatmap: [
    'Read the pitch',
    'Brighter cells mean a higher share of recorded actions. They do not measure running distance or off-ball positioning.',
    'Open a team heatmap',
  ],
  forecast: [
    'Explore uncertainty',
    'Choose a historical replay to inspect probabilities, likely scores and model disagreement. Reconstructed probabilities are not a live record.',
    'Open forecast replay',
  ],
  coverage: [
    'Check before trusting',
    'Check source, last recorded match, fetch time and missing fixtures. A recent fetch alone does not guarantee complete data.',
    'Inspect current coverage',
  ],
  analyst: [
    'Build a decision brief',
    'Import your own permitted events or use the synthetic example below. Local files stay on your device.',
    'See the example controls',
  ],
};
function renderGuide() {
  const [title, description, action] = viewGuides[view];
  $('#view-guide').innerHTML =
    `<details><summary>${title} <span>Quick start</span></summary><p>${description}</p><button class="secondary" data-example="${view}">${action} ↗</button><p class="muted">${view === 'analyst' ? 'Synthetic examples are labelled and opening one uses the workspace’s existing replacement confirmation.' : view === 'coverage' ? 'Coverage describes the selected published source and season.' : 'Examples use the actual published historical archive. They are not current-season demonstrations.'}</p></details>`;
}
async function openExample(kind) {
  if (kind === 'analyst') {
    document.querySelector('[data-analyst="demo"]')?.focus();
    document.querySelector('[data-analyst="demo"]')?.scrollIntoView({ block: 'center' });
    return;
  }
  if (['overview', 'matches', 'compare'].includes(kind)) {
    seasonId =
      manifest.leagues.find((l) => l.id === leagueId).seasons.find((s) => s.id === '2017-18')?.id ||
      seasonId;
    await loadLeague(true);
    if (kind === 'compare') {
      const rivals = [
        ['Barcelona', 'Real Madrid'],
        ['Manchester City', 'Manchester United'],
        ['Bayern', 'Dortmund'],
        ['Juventus', 'Napoli'],
        ['Paris', 'Marseille'],
      ];
      for (const [a, b] of rivals) {
        const first = data.table.find((r) => r.team.includes(a));
        const second = data.table.find((r) => r.team.includes(b));
        if (first && second) {
          home = first.team;
          away = second.team;
          break;
        }
      }
    }
    matchFilter = 'results';
    render();
  } else if (kind === 'coverage') {
    seasonId = manifest.current_season;
    await loadLeague(true);
  } else {
    Object.assign(wb, {
      team: '',
      search: '',
      player: '',
      match: '',
      set: '',
      eventMatch: '',
      eventPlayer: '',
      replay: '',
      page: 1,
    });
    Object.assign(hs, {
      set: '',
      scope: 'season',
      team: '',
      player: '',
      compare: '',
      action: 'all',
      period: 'all',
    });
    if (kind === 'players') {
      const d = wbLoad(`current_${leagueId}.json`);
      const p = d?.players?.find((p) => p.stats?.totalGoals > 0) || d?.players?.[0];
      if (p) wb.player = `${p.id}:${p.team_id}`;
    }
    render();
  }
  $('#main').focus({ preventScroll: true });
  $('#content').scrollIntoView({ block: 'start' });
}
document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-example]');
  if (button)
    openExample(button.dataset.example).catch(() => {
      $('#view-guide').textContent =
        'Example unavailable. Refresh the published data and try again.';
    });
});
// Announce a new publication without replacing filters or unsaved private work.
let releaseCheckAt = 0;
async function checkPublication() {
  if (document.hidden || !manifest || Date.now() - releaseCheckAt < 300000) return;
  releaseCheckAt = Date.now();
  try {
    const next = await fetchJson('data/manifest.json');
    if (next.built_at !== manifest.built_at) $('#release-update').hidden = false;
  } catch {
    /* Keep the working snapshot when offline. */
  }
}
setInterval(checkPublication, 300000);
document.addEventListener('visibilitychange', checkPublication);
