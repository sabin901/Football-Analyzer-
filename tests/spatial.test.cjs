const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const context = vm.createContext({
  document: { addEventListener() {} },
  esc: (s) => String(s),
  wbPanel: (a, b) => b,
});
vm.runInContext(fs.readFileSync('frontend/spatial.js', 'utf8'), context);
const run = (s) => vm.runInContext(s, context);
run(
  `const sample={cols:12,rows:8,players:[{id:1,team_id:10},{id:2,team_id:10},{id:3,team_id:20}],cells:[[0,1,0,0,2],[0,2,1,1,1],[1,1,0,0,3],[2,1,0,0,7]]};`,
);
test('team and player filters preserve counts and normalize independently', () => {
  assert.equal(run(`heatGrid(sample,'10').total`), 6);
  assert.equal(run(`heatGrid(sample,'10','1').total`), 3);
  assert.equal(run(`heatGrid(sample,'20').values.reduce((a,b)=>a+b,0)`), 100);
  assert.ok(Math.abs(run(`heatGrid(sample,'10').values.reduce((a,b)=>a+b,0)`) - 100) < 1e-9);
});
test('period and action filters combine, empty map remains finite', () => {
  run(`hs.period='2';hs.action='0'`);
  assert.equal(run(`heatGrid(sample,'10').total`), 0);
  assert.equal(run(`heatGrid(sample,'10').values.every(v=>v===0)`), true);
  run(`hs.action='1';hs.measure='count'`);
  assert.equal(run(`heatGrid(sample,'10','1').values[1]`), 1);
  run(`hs.period='all';hs.action='all';hs.measure='share'`);
});
test('empty map renders no invalid colours and shared scale has a legend', () => {
  const svg = run(`heatSvg(heatGrid(sample,'99'),0,'Empty','Historical')`);
  assert.ok(!/NaN|undefined/.test(svg));
  assert.ok(svg.includes('0 events'));
  assert.ok(run(`heatSvg(heatGrid(sample,'10'),100,'Home','Historical')`).includes('100.0%'));
});
test('xG curve preserves shot values and includes equal minute events', () => {
  const svg = run(
    `xgFlow({home_id:10,away_id:20,home:'A',away:'B',shots:[{team_id:10,minute:2,xg:.2,goal:false},{team_id:10,minute:2,xg:.3,goal:true,player:'A'},{team_id:20,minute:95,xg:.8,goal:false}]})`,
  );
  assert.ok(svg.includes('0.50 xG'));
  assert.ok(svg.includes('0.80 xG'));
  assert.ok(svg.includes('95′'));
  assert.ok(!/NaN|undefined/.test(svg));
});
