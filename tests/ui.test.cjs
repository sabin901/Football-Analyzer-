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
