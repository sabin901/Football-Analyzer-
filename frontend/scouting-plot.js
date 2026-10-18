'use strict';
function scoutingPlot(d) {
  const colors = {
    GK: '#9aa9c1',
    DEF: '#79a9f1',
    MID: '#78dbca',
    FWD: '#eab373',
    UNKNOWN: '#c5b7e7',
  };
  const rows = d.player_rows.filter(
    (p) =>
      p.minutes >= wb.minutes &&
      (!wb.eventPosition || p.position === wb.eventPosition) &&
      Number.isFinite(p.per90.shots) &&
      Number.isFinite(p.per90.progressive_passes),
  );
  if (!rows.length) return '';
  const xmax = Math.max(1, Math.ceil(Math.max(...rows.map((p) => p.per90.progressive_passes)))),
    ymax = Math.max(1, Math.ceil(Math.max(...rows.map((p) => p.per90.shots))));
  const x = (v) => 70 + (v / xmax) * 690,
    y = (v) => 350 - (v / ymax) * 285;
  const selected = rows.find((p) => `${p.id}:${p.team_id}` === wb.eventPlayer);
  const labels = [
    ...new Set(
      [
        selected,
        ...[...rows].sort((a, b) => b.per90.shots - a.per90.shots).slice(0, 3),
        ...[...rows]
          .sort((a, b) => b.per90.progressive_passes - a.per90.progressive_passes)
          .slice(0, 2),
      ].filter(Boolean),
    ),
  ];
  return wbPanel(
    'Player tendencies · progression and shooting',
    `<div class="plot-legend">${Object.entries(colors)
      .filter(([role]) => rows.some((p) => p.position === role))
      .map(([role, c]) => `<span><i style="background:${c}"></i>${role}</span>`)
      .join(
        '',
      )}<span>${rows.length} player-club records · ≥${wb.minutes} estimated minutes</span></div><div class="plot-scroll"><svg class="scout-plot" viewBox="0 0 840 415" role="img" aria-label="Player scatter plot. Horizontal axis: progressive passes per 90 minutes. Vertical axis: non-penalty shots per 90. Values are in the player table. Select a point to open its profile.">${[0, 0.25, 0.5, 0.75, 1].map((f) => `<path d="M70 ${y(f * ymax)}H760M${x(f * xmax)} 65V350" stroke="#2b3d54" stroke-width="1"/><text x="55" y="${y(f * ymax) + 4}" fill="#8fa8c3" text-anchor="end" font-size="11">${(f * ymax).toFixed(1)}</text><text x="${x(f * xmax)}" y="373" fill="#8fa8c3" text-anchor="middle" font-size="11">${(f * xmax).toFixed(1)}</text>`).join('')}${rows.map((p) => `<circle class="plot-point" data-plot-player="${p.id}:${p.team_id}" cx="${x(p.per90.progressive_passes)}" cy="${y(p.per90.shots)}" r="${p === selected ? 7 : 4}" fill="${colors[p.position] || colors.UNKNOWN}" fill-opacity="${p === selected ? 1 : 0.7}" role="button" tabindex="0" aria-label="${esc(p.name)}, ${esc(p.team)}: ${p.per90.progressive_passes} progressive passes and ${p.per90.shots} shots per 90"><title>${esc(p.name)} · ${esc(p.team)} · ${p.minutes.toFixed(0)} estimated minutes</title></circle>`).join('')}${labels.map((p) => `<text x="${Math.min(737, x(p.per90.progressive_passes) + 7)}" y="${y(p.per90.shots) - 9}" text-anchor="${x(p.per90.progressive_passes) > 630 ? 'end' : 'start'}" font-size="10" fill="#e2edf9" stroke="#142030" stroke-width="3" paint-order="stroke">${esc(p.name)}</text>`).join('')}<text x="415" y="402" text-anchor="middle" fill="#b0c5dc" font-size="12">Progressive passes / 90 →</text><text transform="translate(18 210) rotate(-90)" text-anchor="middle" fill="#b0c5dc" font-size="12">Non-penalty shots / 90 →</text><text x="70" y="30" fill="#84dcca" font-size="10" letter-spacing="2">${esc(d.competition.toUpperCase())} · ${esc(d.season)}</text></svg></div><p class="muted">Historical event counts, not xG or a talent rating. The axes use estimated regulation minutes and are not adjusted for possession or opposition. Select a point or use the searchable player table. Position and minutes filters apply to both.</p>`,
  );
}
function openPlotPlayer(e) {
  const p = e.target.closest('[data-plot-player]');
  if (!p) return;
  if (e.type === 'keydown' && !['Enter', ' '].includes(e.key)) return;
  e.preventDefault();
  wb.eventPlayer = p.dataset.plotPlayer;
  render();
}
document.addEventListener('click', openPlotPlayer);
document.addEventListener('keydown', openPlotPlayer);
