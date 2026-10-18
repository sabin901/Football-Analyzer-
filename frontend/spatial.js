'use strict';
const hs = {
  set: '',
  scope: 'season',
  match: '',
  team: '',
  player: '',
  compare: '',
  action: 'all',
  period: 'all',
  measure: 'share',
};
let heatExport = null;
function xgFlow(m) {
  if (!m.shots.length || m.shots.some((s) => !Number.isFinite(s.xg)))
    return empty('Expected goals are unavailable in this source.');
  const end = Math.max(90, ...m.shots.map((s) => s.minute));
  const totals = [m.home_id, m.away_id].map((id) =>
    m.shots.filter((s) => s.team_id === id).reduce((n, s) => n + s.xg, 0),
  );
  const ymax = Math.max(1, Math.ceil(Math.max(...totals) * 2) / 2);
  const px = (min) => 48 + (min / end) * 520,
    py = (v) => 222 - (v / ymax) * 184;
  const paths = [m.home_id, m.away_id]
    .map((id, i) => {
      let sum = 0,
        path = 'M48 222',
        goals = '';
      for (const s of m.shots.filter((s) => s.team_id === id).sort((a, b) => a.minute - b.minute)) {
        sum += s.xg;
        path += `H${px(s.minute)}V${py(sum)}`;
        if (s.goal)
          goals += `<circle cx="${px(s.minute)}" cy="${py(sum)}" r="4" fill="${i ? '#7c54a8' : '#256345'}" stroke="white"><title>${esc(s.player)} · ${s.minute} minutes · goal</title></circle>`;
      }
      return `<path d="${path}H568" fill="none" stroke="${i ? '#7c54a8' : '#256345'}" stroke-width="2.5" ${i ? 'stroke-dasharray="7 4"' : ''}/>${goals}`;
    })
    .join('');
  return wbPanel(
    'Chance creation through the match',
    `<div class="xg-legend"><span><i class="xg-key"></i>${esc(m.home)} · ${totals[0].toFixed(2)} xG</span><span><i class="xg-key away"></i>${esc(m.away)} · ${totals[1].toFixed(2)} xG</span></div><svg class="xg-flow" viewBox="0 0 610 267" role="img" aria-label="Cumulative expected goals for ${esc(m.home)} and ${esc(m.away)}. Goal markers are circles. Shot table above provides the underlying values.">${[0, 0.5, 1].map((f) => `<path d="M48 ${py(f * ymax)}H568" stroke="#dbe3d5"/><text x="34" y="${py(f * ymax) + 4}" text-anchor="end" fill="#657169" font-size="11">${(f * ymax).toFixed(1)}</text>`).join('')}${paths}${[0, 45, end].map((t) => `<text x="${px(t)}" y="245" text-anchor="middle" fill="#657169" font-size="11">${t}′</text>`).join('')}<text x="48" y="20" fill="#657169" font-size="11">Cumulative xG</text></svg><p class="muted">Provider shot xG accumulated by recorded minute. Penalties included. Dots mark goals from shots; own goals are not shot xG. This describes chance creation, not momentum, possession or the deserved winner.</p>`,
  );
}
// Perceptually ordered, colour-blind-friendly luminance: deep teal to warm yellow.
const heatColors = ['#142e31', '#205d63', '#298a88', '#59b5a0', '#a9d7a3', '#e4e5a0', '#f9dc78'];
function heatColor(value, maximum) {
  if (!value || maximum <= 0) return heatColors[0];
  const level = Math.max(0, Math.min(6, (value / maximum) * 6));
  const low = Math.min(5, Math.floor(level)),
    mix = level - low;
  const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const a = rgb(heatColors[low]),
    b = rgb(heatColors[low + 1]);
  return (
    '#' +
    a
      .map((v, i) =>
        Math.round(v + (b[i] - v) * mix)
          .toString(16)
          .padStart(2, '0'),
      )
      .join('')
  );
}
function heatGrid(d, team, player = '') {
  const bins = Array(d.cols * d.rows).fill(0);
  for (const [i, period, kind, cell, n] of d.cells) {
    const p = d.players[i];
    if (String(p.team_id) !== String(team) || (player && String(p.id) !== String(player))) continue;
    if (hs.action !== 'all' && kind !== Number(hs.action)) continue;
    if (hs.period !== 'all' && period !== Number(hs.period)) continue;
    bins[cell] += n;
  }
  const total = bins.reduce((a, b) => a + b, 0);
  return {
    bins,
    total,
    values: bins.map((n) => (hs.measure === 'share' ? (total ? (100 * n) / total : 0) : n)),
  };
}
function heatSvg(grid, maximum, title, subtitle) {
  const value = (v) =>
    hs.measure === 'share' ? `${v.toFixed(1)}%` : Number(v.toFixed(1)).toString();
  const cells = grid.values
    .map((v, i) => {
      const x = 60 + (i % 12) * 60,
        y = 100 + Math.floor(i / 12) * 60;
      const label = `x ${(i % 12) * 10}–${(i % 12) * 10 + 10}, y ${Math.floor(i / 12) * 10}–${Math.floor(i / 12) * 10 + 10}: ${grid.bins[i]} events · ${value(v)}`;
      return `<g><title>${label}</title><rect x="${x + 0.7}" y="${y + 0.7}" width="58.6" height="58.6" rx="2" fill="${heatColor(v, maximum)}"/>${v > 0 && v >= maximum * 0.55 ? `<text x="${x + 30}" y="${y + 35}" text-anchor="middle" fill="${v / maximum > 0.7 ? '#173b35' : '#0c3030'}" font-size="13" font-weight="600">${value(v)}</text>` : ''}</g>`;
    })
    .join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" class="heat-pitch" viewBox="0 0 840 712" role="img" aria-label="${esc(title)} activity heatmap. ${grid.total} located events. Both teams attack right. Numeric grid available below." font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"><rect width="840" height="712" rx="14" fill="#102729"/><text x="60" y="41" fill="#eff6ef" font-size="23" font-weight="600">${esc(title)}</text><text x="60" y="67" fill="#a6c0b9" font-size="13">${esc(subtitle)}</text><text x="780" y="87" text-anchor="end" fill="#a6c0b9" font-size="10" letter-spacing="2">ATTACKING →</text>${cells}<g fill="none" stroke="#ebf5e9" stroke-opacity=".65" stroke-width="1.4"><rect x="60" y="100" width="720" height="480"/><path d="M420 100V580M60 208H168V472H60M780 208H672V472H780M60 280H96V400H60M780 280H744V400H780M60 316H48V364H60M780 316H792V364H780"/><circle cx="420" cy="340" r="60"/><path d="M168 292A60 60 0 0 1 168 388M672 292A60 60 0 0 0 672 388"/><path d="M60 112A12 12 0 0 0 72 100M768 100A12 12 0 0 0 780 112M60 568A12 12 0 0 1 72 580M768 580A12 12 0 0 1 780 568"/></g><g fill="#eff6ef" fill-opacity=".75"><circle cx="420" cy="340" r="2.6"/><circle cx="132" cy="340" r="2.6"/><circle cx="708" cy="340" r="2.6"/></g><g fill="#a6c0b9" font-size="10" letter-spacing="1.2" text-anchor="middle"><text x="180" y="602">DEFENSIVE THIRD</text><text x="420" y="602">MIDDLE THIRD</text><text x="660" y="602">ATTACKING THIRD</text></g><text x="60" y="639" fill="#f0f6ef" font-size="15" font-weight="600">${grid.total.toLocaleString()} events</text><text x="60" y="661" fill="#a6c0b9" font-size="11">${hs.measure === 'share' ? 'Share of selected events per cell' : 'Recorded events per cell'} · 12 × 8 exact grid</text>${Array.from({ length: 60 }, (_, i) => `<rect x="${510 + i * 4.5}" y="626" width="4.6" height="10" fill="${heatColor(i, 59)}"/>`).join('')}<text x="510" y="655" fill="#a6c0b9" font-size="11">0</text><text x="645" y="655" text-anchor="middle" fill="#a6c0b9" font-size="11">${value(maximum / 2)}</text><text x="780" y="655" text-anchor="end" fill="#e4eedf" font-size="11">${value(maximum)}</text><path d="M60 679H780" stroke="#2b4544"/><text x="60" y="700" fill="#8ea9a2" font-size="10">FOOTLYZER / HISTORICAL EVENT ACTIVITY</text><text x="780" y="700" text-anchor="end" fill="#8ea9a2" font-size="10">Source: Pappalardo / Wyscout · CC BY 4.0</text></svg>`;
}
function heatmapView() {
  heatExport = null;
  const manifest = wbLoad('spatial_manifest.json');
  if (!manifest) return empty('Loading the spatial archive…');
  if (manifest.error) return empty('Spatial archive unavailable. Refresh to retry.');
  const sets = manifest.sets.filter((s) => s.league === leagueId && s.imported_matches);
  if (!sets.length) return empty('No spatial data imported for this league.');
  if (!sets.some((s) => s.key === hs.set))
    hs.set = sets.find((s) => s.imported_matches >= 300)?.key || sets[0].key;
  const season = wbLoad(`spatial_${hs.set}.json`),
    events = wbLoad(`events_${hs.set}.json`);
  if (!season || !events) return empty('Loading historical locations…');
  if (season.error || events.error)
    return empty('This spatial dataset is unavailable. Refresh to retry.');
  const matches = events.matches.filter((m) => season.match_ids.includes(m.id));
  if (!matches.some((m) => String(m.id) === hs.match)) hs.match = String(matches.at(-1)?.id || '');
  const d = hs.scope === 'match' ? wbLoad(`spatial_matches/${hs.match}.json`) : season;
  if (!d) return empty('Loading match locations…');
  if (d.error) return empty('Match locations unavailable. Choose another match or refresh.');
  const teams = [...new Map(d.players.map((p) => [String(p.team_id), p.team])).entries()].sort(
    (a, b) => a[1].localeCompare(b[1]),
  );
  if (!teams.some(([id]) => id === hs.team)) {
    hs.team = teams[0]?.[0] || '';
    hs.player = '';
  }
  if (!teams.some(([id]) => id === hs.compare) || hs.compare === hs.team) hs.compare = '';
  const players = d.players
    .filter((p) => String(p.team_id) === hs.team)
    .sort((a, b) => a.name.localeCompare(b.name));
  if (!players.some((p) => String(p.id) === hs.player)) hs.player = '';
  const p = players.find((p) => String(p.id) === hs.player),
    name = p?.name || teams.find(([id]) => id === hs.team)?.[1] || 'Team';
  const grid = heatGrid(d, hs.team, hs.player),
    other = hs.compare ? heatGrid(d, hs.compare) : null;
  const maximum = Math.max(0, ...grid.values, ...(other?.values || []));
  const currentMatch = matches.find((m) => String(m.id) === hs.match);
  const context =
    hs.scope === 'match'
      ? `${currentMatch.date} · ${currentMatch.home} vs ${currentMatch.away}`
      : `${season.competition} ${season.season} · imported season sample`;
  const action = hs.action === 'all' ? 'All located actions' : d.actions[Number(hs.action)];
  const period = hs.period === 'all' ? 'All periods' : `Period ${hs.period}`;
  const subtitle = `${season.season} · ${action} · ${period}`;
  const svg = heatSvg(grid, maximum, name, subtitle);
  heatExport = { d, grid, other, maximum, name, context, action, period, svg };
  const third = [0, 0, 0];
  grid.bins.forEach((n, i) => (third[Math.floor((i % 12) / 4)] += n));
  // Participation is independent of the selected action or period.
  const playerMatches =
    hs.scope === 'match'
      ? Number(
          d.cells.some(
            ([index]) =>
              String(d.players[index].team_id) === hs.team &&
              (!hs.player || String(d.players[index].id) === hs.player),
          ),
        )
      : (p?.matches ??
        matches.filter((m) => String(m.home_id) === hs.team || String(m.away_id) === hs.team)
          .length);
  return `<section class="spatial-intro"><div><p class="eyebrow">SPATIAL INTELLIGENCE</p><h2>Where does the game happen?</h2><p>Explore the spaces teams use and the actions players make.</p></div><span class="spatial-tag">${icon('scan-line')} Historical event data</span></section><div class="toolbar heat-source">${wbSelect(
    'heat-set',
    'Historical dataset',
    sets.map((s) => [s.key, `${s.competition} ${s.season} · ${s.imported_matches} matches`]),
    hs.set,
  )}${wbSelect(
    'heat-scope',
    'Sample',
    [
      ['season', 'Imported season sample'],
      ['match', 'Single match'],
    ],
    hs.scope,
  )}${
    hs.scope === 'match'
      ? wbSelect(
          'heat-match',
          'Match',
          [...matches].reverse().map((m) => [m.id, `${m.date} · ${m.home} vs ${m.away}`]),
          hs.match,
        )
      : ''
  }</div><div class="heat-context"><span class="small-dot"></span>${esc(context)}<span>${season.imported_matches} / ${season.available_matches} archive matches mapped</span></div><section class="panel"><div class="toolbar heat-filters">${wbSelect('heat-team', 'Team', teams, hs.team)}${wbSelect('heat-player', 'Player', [['', 'Whole team'], ...players.map((p) => [p.id, p.name])], hs.player)}${wbSelect('heat-action', 'Action', [['all', 'All actions'], ...d.actions.map((n, i) => [i, n])], hs.action)}${wbSelect(
    'heat-period',
    'Period',
    [
      ['all', 'All periods'],
      [1, 'First half'],
      [2, 'Second half'],
      [3, 'Extra time first'],
      [4, 'Extra time second'],
    ],
    hs.period,
  )}${wbSelect(
    'heat-measure',
    'Colour scale',
    [
      ['share', 'Event share %'],
      ['count', 'Event counts'],
    ],
    hs.measure,
  )}${wbSelect('heat-compare', 'Compare with team', [['', 'No comparison'], ...teams.filter(([id]) => id !== hs.team)], hs.compare)}</div><div class="panel-body"><div class="heat-maps ${other ? 'two-maps' : ''}"><div><div class="heat-map-caption"><h3>${esc(name)}</h3><p>${esc(action)} · ${period}</p></div>${svg}<p class="heat-scale-note">Attack right · Colour: 0 to ${hs.measure === 'share' ? maximum.toFixed(1) + '%' : maximum} per cell</p>${grid.total ? '' : empty('No located events match this selection. Try another action or period.')}</div>${other ? `<div><div class="heat-map-caption"><h3>${esc(teams.find(([id]) => id === hs.compare)[1])}</h3><p>Whole team · ${esc(action)} · ${period}</p></div>${heatSvg(other, maximum, teams.find(([id]) => id === hs.compare)[1], subtitle)}<p class="heat-scale-note">Attack right · Colour: 0 to ${hs.measure === 'share' ? maximum.toFixed(1) + '%' : maximum} per cell</p>${other.total ? '' : empty('No located events in this comparison.')}</div>` : ''}</div><div class="heat-summary"><div><strong>${grid.total.toLocaleString()}</strong><span>Selected events</span></div><div><strong>${playerMatches}</strong><span>${p ? 'Matches with any located action' : 'Team matches in sample'}</span></div></div><div class="heat-territory" aria-label="Distribution across pitch thirds">${['Defensive third', 'Middle third', 'Attacking third'].map((label, i) => `<div><span>${label}</span><strong>${grid.total ? ((100 * third[i]) / grid.total).toFixed(1) + '%' : '—'}</strong></div>`).join('')}</div><div class="heat-actions"><button class="secondary" data-heat-csv>${icon('download')} Export grid CSV</button><button class="secondary" data-heat-svg>${icon('image')} Save selected map SVG</button><a href="docs/SPATIAL_METHOD.html">Method and coordinate guide ${icon('arrow-up-right')}</a></div><p class="muted">${other ? 'Both maps share the same colour maximum. ' : ''}${hs.measure === 'share' ? 'Each map sums to 100% when events exist. This compares distributions, not work rate.' : 'Counts depend on playing time, possession and sample size.'} A brighter cell means more recorded activity, not better performance.</p><details><summary>Accessible numeric grid for ${esc(name)}</summary>${wbTable(
    ['Y / X', ...Array.from({ length: 12 }, (_, i) => `${i * 10} to ${i * 10 + 10}`)],
    Array.from(
      { length: 8 },
      (_, y) =>
        `<tr><th scope="row">${y * 10} to ${y * 10 + 10}</th>${grid.values
          .slice(y * 12, y * 12 + 12)
          .map((v) => `<td>${hs.measure === 'share' ? v.toFixed(2) + '%' : v}</td>`)
          .join('')}</tr>`,
    ),
    'Selected heatmap numeric grid',
  )}</details><details><summary>Coverage and interpretation</summary><p>Pappalardo / Wyscout · CC BY 4.0. ${season.first_date} to ${season.last_date}. ${season.errors.length} spatial import failures. The full ${hs.scope === 'match' ? 'match' : 'dataset'} contains ${d.located.toLocaleString()} located player events, ${d.missing_location.toLocaleString()} events without locations, ${d.invalid_location} invalid locations excluded, and ${d.edge_clamped} boundary locations clamped for binning. These quality counts cover the whole sample, before filters.</p><p>Locations are rescaled from the provider’s 0–100 axes into 120 × 80 display units. Both teams attack right; no half is rotated again. Defensive duels, interceptions and clearances are separate from passes and shots. All actions include other located events; they are not unique touches. Missing coordinates never become zero coordinates.</p></details></div></section><div class="notice"><strong>Event activity, not player tracking.</strong> These maps show recorded historical actions, not distance covered, off ball positioning or time spent in a zone. Current free match summaries have no reliable event locations. The 2017/18 archive covers all fixtures in these five leagues.</div><div class="spatial-credit"><a href="https://doi.org/10.6084/m9.figshare.c.4415000">Pappalardo and colleagues · Wyscout research data · CC BY 4.0</a> · <a href="docs/ASSET_CREDITS.html">Attribution and transformations</a></div>`;
}
document.addEventListener('change', (e) => {
  if (!e.target.id.startsWith('heat-')) return;
  const key = e.target.id.slice(5);
  if (!(key in hs)) return;
  hs[key] = e.target.value;
  if (['set', 'scope', 'match', 'team'].includes(key)) {
    hs.player = '';
    hs.compare = '';
  }
  render();
  document.getElementById(e.target.id)?.focus();
});
document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b || !heatExport) return;
  const h = heatExport;
  if (b.hasAttribute('data-heat-csv')) {
    const rows = [
      [
        'dataset',
        'sample',
        'selection',
        'team_id',
        'player_id',
        'action',
        'period',
        'x_min',
        'x_max',
        'y_min',
        'y_max',
        'count',
        'share_pct',
        'source',
      ],
    ];
    h.grid.bins.forEach((n, i) =>
      rows.push([
        hs.set,
        h.context,
        h.name,
        hs.team,
        hs.player || 'all',
        h.action,
        h.period,
        (i % 12) * 10,
        (i % 12) * 10 + 10,
        Math.floor(i / 12) * 10,
        Math.floor(i / 12) * 10 + 10,
        n,
        h.grid.total ? ((100 * n) / h.grid.total).toFixed(4) : 0,
        'Pappalardo / Wyscout · CC BY 4.0',
      ]),
    );
    downloadFile(`footlyzer-heatmap-${hs.set}.csv`, toCsv(rows), 'text/csv;charset=utf-8');
  }
  if (b.hasAttribute('data-heat-svg')) {
    const metadata = `<metadata>${esc(JSON.stringify({ dataset: hs.set, sample: h.context, team: hs.team, player: hs.player || 'all', action: h.action, period: h.period, measure: hs.measure, source: 'Pappalardo / Wyscout · CC BY 4.0', method: '12 by 8 event start bins, both teams attack right', limitation: 'Historical event activity, not continuous tracking' }))}</metadata>`;
    downloadFile(
      `footlyzer-heatmap-${hs.set}.svg`,
      h.svg.replace(/(<svg[^>]*>)/, `$1${metadata}`),
      'image/svg+xml',
    );
  }
});
