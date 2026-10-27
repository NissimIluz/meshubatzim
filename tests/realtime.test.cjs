const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('initial connection joins the week; reconnect reloads current board state', () => {
  const handlers = {};
  const emitted = [];
  let reloads = 0;
  const socket = {
    on: (event, handler) => { handlers[event] = handler; },
    emit: (...args) => emitted.push(args),
  };
  const context = {
    document: { readyState: 'loading', addEventListener() {} },
    window: { location: { reload: () => { reloads++; } } },
    io: () => socket,
  };
  const source = fs.readFileSync(path.join(__dirname, '../app/static/js/app.js'), 'utf8')
    .replace('if (document.readyState ===', 'globalThis.startRealtime = setupRealtime;\n  if (document.readyState ===');
  vm.runInNewContext(source, context);
  context.startRealtime('2026-11-01');
  handlers.connect();
  assert.equal(reloads, 0);
  assert.equal(emitted[0][0], 'join');
  assert.equal(emitted[0][1].week, '2026-11-01');
  handlers.connect();
  assert.equal(reloads, 1);
  assert.equal(emitted.length, 1);
});
