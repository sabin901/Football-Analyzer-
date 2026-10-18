const test = require('node:test'),
  assert = require('node:assert/strict');
const core = require('../frontend/analyst-core.js');
const row = 'e1,1,120,Team A,"Player, One",Pass,100,100,90,80,Complete';
const source = core.headers.join(',') + '\n' + row;
test('CSV supports quoted names, reordered headers and boundary locations', () => {
  const events = core.csv(source);
  assert.equal(events[0].player, 'Player, One');
  assert.equal(core.grid(events).bins[95], 1);
  assert.equal(core.grid(events).located, 1);
});
test('Missing coordinates remain missing, not zero locations', () => {
  const events = core.csv(source.replace('100,100,90,80', ',,,'));
  assert.equal(core.grid(events).located, 0);
  assert.equal(core.grid(events).missing, 1);
});
test('CSV rejects malformed, duplicated and nonfinite events', () => {
  for (const bad of [
    source + '\n' + row,
    source.replace(',1,120,', ',1,,'),
    source.replace(',100,100,', ',101,100,'),
    source.replace(',100,100,', ',NaN,100,'),
    source.replace(',100,100,', ',,100,'),
    source.replace('"Player, One"', '"unterminated'),
    source.replace(',1,120,', ',5,120,'),
    source.replace('id,period', 'id,id'),
  ])
    assert.throws(() => core.csv(bad));
});
test('A project backup validates schema, references and bounds', () => {
  const p = core.demo();
  assert.deepEqual(core.backup(JSON.stringify(p)), p);
  assert.throws(() => core.backup(JSON.stringify({ ...p, version: 2 })));
  p.notes[0].evidence = ['missing'];
  assert.throws(() => core.validate(p));
  assert.throws(() => core.validate({ ...core.demo(), offsets: [0, Infinity, 0, 0] }));
});
test('Brief separates claims and includes traceable event references', () => {
  const p = core.demo();
  p.notes[0].observation = '<script>alert(1)</script>';
  const brief = core.brief(p);
  assert.match(brief, /SYNTHETIC/);
  assert.match(brief, /Interpretation:/);
  assert.match(brief, /Limitation/);
  assert.match(brief, /Event demo-1/);
  assert.doesNotMatch(brief, /<script>/);
  assert.match(brief, /video 120s/);
});
test('Event text is preserved as data; no arbitrary project object keys survive', () => {
  const p = core.demo();
  p.events[0].player = '=HYPERLINK("https://example.org")';
  p.evil = '<img>';
  const valid = core.validate(p);
  assert.equal(valid.evil, undefined);
  assert.equal(valid.events[0].player, p.events[0].player);
});
test('All grid mass is conserved independently of missing coordinates', () => {
  const rows = core.demo().events;
  rows[0].x = null;
  rows[0].y = null;
  const g = core.grid(rows);
  assert.equal(
    g.bins.reduce((a, b) => a + b, 0),
    17,
  );
  assert.equal(g.located + g.missing, rows.length);
});
test('Accepted projects always round-trip within the backup limit', () => {
  const p = core.demo();
  assert.deepEqual(core.backup(JSON.stringify(core.validate(p))), p);
  p.events = Array.from({ length: 20000 }, (_, i) => ({
    ...p.events[0],
    id: `e${i}`,
    player: 'é'.repeat(160),
    team: 'é'.repeat(160),
  }));
  p.notes = [];
  assert.throws(() => core.validate(p), /5 MB/);
});
