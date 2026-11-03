const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync('frontend/ui.js', 'utf8'), context);
const run = (source) => vm.runInContext(source, context);

test('CSV preserves accents, quotes and absent values', () => {
  assert.equal(run(`toCsv([['Özil', 'a"b', null]])`), '\ufeff"Özil","a""b",""');
});
test('CSV neutralizes text formulas while preserving numeric negatives', () => {
  assert.equal(run(`csvCell(' =SUM(A1)')`), '"\' =SUM(A1)"');
  assert.equal(run(`csvCell('-2')`), '"\'-2"');
  assert.equal(run(`csvCell(-2)`), '"-2"');
});
test('provider text is escaped and missing metrics are not zero', () => {
  assert.equal(run(`esc('<script>"&')`), '&lt;script&gt;&quot;&amp;');
  assert.equal(run(`decimal(null)`), '—');
  assert.equal(run(`decimal(0)`), '0.00');
});

test('awarded outcomes do not become draws from an administrative 0-0 score', () => {
  assert.equal(
    run(`matchOutcome({home:'Bastia', away:'Lyon', hg:0, ag:0, awarded_winner:'Lyon'}, 'Lyon')`),
    'W',
  );
  assert.equal(
    run(`matchOutcome({home:'Bastia', away:'Lyon', hg:0, ag:0, awarded_winner:'Lyon'}, 'Bastia')`),
    'L',
  );
  assert.equal(run(`matchOutcome({home:'A', away:'B', hg:0, ag:0}, 'A')`), 'D');
});

test('new visitors avoid current seasons with missing results or stale source dates', () => {
  const fresh = {
    id: '2026-27',
    completed: 50,
    overdue: 0,
    quarantined: 0,
    refresh_ok: true,
    fetched_at: new Date().toISOString(),
    last_result: new Date().toISOString(),
  };
  const archive = { id: '2025-26', completed: 380, overdue: 0, quarantined: 0 };
  context.league = { seasons: [fresh, archive] };
  assert.equal(run("preferredSeason(league, '2026-27')"), '2026-27');
  fresh.overdue = 40;
  assert.equal(run("preferredSeason(league, '2026-27')"), '2025-26');
  fresh.overdue = 0;
  fresh.last_result = '2000-01-01';
  assert.equal(run("preferredSeason(league, '2026-27')"), '2025-26');
  archive.quarantined = 1;
  assert.equal(run("preferredSeason(league, '2026-27')"), '2026-27');
  context.league = { seasons: [] };
  assert.equal(run("preferredSeason(league, '2026-27')"), '');
});
