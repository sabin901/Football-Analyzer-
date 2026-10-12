const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync('frontend/snapshot-store.js', 'utf8'), context);
const createStore = vm.runInContext('createSnapshotStore', context);
const tick = () => new Promise((resolve) => setImmediate(resolve));

test('simultaneous views share a request and render when ready', async () => {
  let calls = 0,
    changes = 0;
  const store = createStore(
    async () => {
      calls++;
      return { count: 12 };
    },
    () => changes++,
  );
  assert.equal(store.load('PL'), null);
  assert.equal(store.load('PL'), null);
  assert.equal(store.isLoading(), true);
  await tick();
  assert.equal(calls, 1);
  assert.equal(changes, 1);
  assert.equal(store.load('PL').count, 12);
  assert.equal(store.isLoading(), false);
});

test('a slow response before refresh cannot overwrite fresh data', async () => {
  const responses = [];
  let changes = 0;
  const store = createStore(
    () => new Promise((resolve) => responses.push(resolve)),
    () => changes++,
  );
  store.load('PL');
  await tick();
  store.clear();
  store.load('PL');
  await tick();
  responses[1]({ version: 'new' });
  await tick();
  responses[0]({ version: 'old' });
  await tick();
  assert.equal(store.load('PL').version, 'new');
  assert.equal(changes, 1);
});

test('failed requests stop loading and can be retried after refresh', async () => {
  let fail = true;
  const store = createStore(
    async () => {
      if (fail) throw new Error('offline');
      return { ok: true };
    },
    () => {},
  );
  store.load('PL');
  await tick();
  assert.equal(store.load('PL').error, 'offline');
  assert.equal(store.isLoading(), false);
  fail = false;
  store.clear();
  store.load('PL');
  await tick();
  assert.equal(store.load('PL').ok, true);
});
