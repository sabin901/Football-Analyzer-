'use strict';
// Shared display helpers. Escape provider text before inserting it into HTML.
// Dates without kickoff times are rendered in UTC to avoid changing the match day.
const $ = (s) => document.querySelector(s);
const esc = (v) =>
  String(v ?? '').replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );
const short = (name) => name.replace(/\s+(FC|CF|AFC)$/, '');
const day = (value) =>
  value
    ? new Date(`${value}T12:00:00Z`).toLocaleDateString(undefined, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        timeZone: 'UTC',
      })
    : 'Date to be confirmed';
const stamp = (value) =>
  value
    ? new Date(value).toLocaleString(undefined, {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
      })
    : 'Not fetched';
const pct = (v) => `${(100 * v).toFixed(1)}%`;
const decimal = (v) => (v == null ? '—' : Number(v).toFixed(2));
function matchOutcome(match, team) {
  if (match.awarded_winner) return match.awarded_winner === team ? 'W' : 'L';
  const [gf, ga] = match.home === team ? [match.hg, match.ag] : [match.ag, match.hg];
  return gf > ga ? 'W' : gf === ga ? 'D' : 'L';
}
const wbFold = (s) =>
  String(s)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
const wbPanel = (title, body, note = '') =>
  `<section class="panel"><div class="panel-head"><h2>${title}</h2>${note ? `<span class="muted">${note}</span>` : ''}</div><div class="panel-body">${body}</div></section>`;
const wbTable = (labels, rows, name) =>
  `<div class="table-scroll"><table aria-label="${esc(name)}"><thead><tr>${labels.map((l) => `<th scope="col">${l}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
const wbOptions = (rows, value) =>
  rows
    .map(
      ([id, name]) =>
        `<option value="${esc(id)}" ${String(id) === String(value) ? 'selected' : ''}>${esc(name)}</option>`,
    )
    .join('');
const wbSelect = (id, label, rows, value) =>
  `<label for="${id}">${label}<select id="${id}">${wbOptions(rows, value)}</select></label>`;

/** Quote CSV cells and prevent provider text from becoming a spreadsheet formula. */
function csvCell(value) {
  let text = String(value ?? '');
  if (typeof value === 'string' && (/^\s*[=+@-]/.test(text) || /^[\t\r\n]/.test(text))) {
    text = "'" + text;
  }
  return '"' + text.replaceAll('"', '""') + '"';
}

function toCsv(rows) {
  // The BOM lets Excel recognize player names with accents as UTF-8.
  return '\ufeff' + rows.map((row) => row.map(csvCell).join(',')).join('\r\n');
}

/** Browser exports stay local; there is no upload or server side export job. */
function downloadFile(name, body, type = 'text/markdown;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Choose a usable archive for first-time visitors when current coverage has gaps.
// Explicit season links are preserved by the caller; completeness is not verification.
function preferredSeason(league, currentSeason) {
  const usable = (s) => s.completed > 0 && s.overdue === 0 && s.quarantined === 0;
  const current = league.seasons.find((s) => s.id === currentSeason);
  if (
    current &&
    usable(current) &&
    current.refresh_ok === true &&
    Date.now() - Date.parse(current.fetched_at) < 36 * 3600000 &&
    Date.now() - Date.parse(current.last_result) < 14 * 86400000
  )
    return current.id;
  return (
    league.seasons.find((s) => s.id !== currentSeason && usable(s))?.id ||
    current?.id ||
    league.seasons[0]?.id ||
    ''
  );
}
