const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function harness() {
  const handlers = {};
  const timers = new Map();
  const requests = [];
  let timerId = 0;
  const classes = new Set(['is-editing']);
  const fields = {
    '.cell-name': { value: 'draft' }, '.cell-notes': { value: '' },
    '.cell-name-text': { textContent: 'old' }, '.cell-notes-text': { textContent: '' },
    '.cell-save-status': { dataset: {}, textContent: '', setAttribute() {} },
    '.cell-close': { hidden: false, closest: () => cell },
    '.cell-form': { action: '/api/slot?groupId=test-group' },
  };
  const cell = {
    classList: {
      contains: name => classes.has(name), add: name => classes.add(name),
      remove: name => classes.delete(name),
      toggle: (name, active) => active ? classes.add(name) : classes.delete(name),
    },
    contains: () => false, setAttribute() {}, focus() {},
    querySelector: selector => fields[selector],
  };
  const context = {
    document: {
      readyState: 'loading', activeElement: null,
      addEventListener: (name, handler) => { handlers[name] = handler; },
      querySelector: () => ({ content: 'csrf-token' }), querySelectorAll: () => [cell],
    },
    setTimeout: callback => { timers.set(++timerId, callback); return timerId; },
    clearTimeout: id => timers.delete(id),
    FormData: function () { this.assignee = fields['.cell-name'].value; },
    fetch: (url, options) => new Promise((resolve, reject) => requests.push({ url, options, resolve, reject })),
  };
  const source = fs.readFileSync(path.join(__dirname, '../app/static/js/app.js'), 'utf8')
    .replace('if (document.readyState ===', 'globalThis.api = {setupAutosave, setupClickEdit, applyRemoteUpdate, pageClientId};\n  if (document.readyState ===');
  vm.runInNewContext(source, context);
  context.api.setupAutosave();
  context.api.setupClickEdit();
  return {
    fields, cell, requests, timers, api: context.api,
    close() { handlers.click({ target: { closest: selector => selector === '.cell-close' ? fields['.cell-close'] : cell } }); },
    input(value) {
      fields['.cell-name'].value = value;
      handlers.input({ target: { matches: () => true, closest: () => cell } });
    },
    tick() { const pending = [...timers.values()]; timers.clear(); pending.forEach(callback => callback()); },
    async complete(index, name) {
      requests[index].resolve({ ok: true, json: async () => ({ day_index: 0, shift: 'morning', assignee: name, notes: '' }) });
      await new Promise(resolve => setImmediate(resolve));
    },
  };
}

test('typing debounces to one save and displays success without closing editor', async () => {
  const h = harness();
  h.input('A');
  h.input('AB');
  assert.equal(h.timers.size, 1);
  assert.equal(h.fields['.cell-save-status'].dataset.state, 'saving');
  assert.equal(h.requests.length, 0);
  h.tick();
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].options.body.assignee, 'AB');
  assert.equal(h.requests[0].options.headers['X-CSRFToken'], 'csrf-token');
  await h.complete(0, 'AB');
  assert.equal(h.fields['.cell-save-status'].textContent, '✓');
  assert.equal(h.fields['.cell-name-text'].textContent, 'AB');
  assert(h.cell.classList.contains('is-editing'));
});

test('saves are serialized and an older response cannot replace newer typing', async () => {
  const h = harness();
  h.input('first'); h.tick();
  h.input('second'); h.tick();
  assert.equal(h.requests.length, 1);
  await h.complete(0, 'first');
  assert.equal(h.fields['.cell-name'].value, 'second');
  assert.equal(h.requests.length, 2);
  assert.equal(h.requests[1].options.body.assignee, 'second');
  await h.complete(1, 'second');
  assert.equal(h.fields['.cell-save-status'].dataset.state, 'saved');
});

test('remote updates cancel pending drafts, but our own echo keeps editing intact', () => {
  const h = harness();
  h.input('draft');
  h.api.applyRemoteUpdate({ client_id: h.api.pageClientId, day_index: 0, shift: 'morning', assignee: 'own echo' });
  assert.equal(h.fields['.cell-name'].value, 'draft');
  assert(h.cell.classList.contains('is-editing'));
  h.api.applyRemoteUpdate({ day_index: 0, shift: 'morning', assignee: 'remote' });
  h.tick();
  assert.equal(h.requests.length, 0);
  assert.equal(h.fields['.cell-name'].value, 'remote');
  assert(!h.cell.classList.contains('is-editing'));
});

test('a failed save shows an error and preserves the draft for another attempt', async () => {
  const h = harness();
  h.input('draft'); h.tick();
  h.requests[0].reject(new Error('offline'));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.fields['.cell-save-status'].dataset.state, 'error');
  assert.equal(h.fields['.cell-name'].value, 'draft');
  h.input('retry'); h.tick();
  await h.complete(1, 'retry');
  assert.equal(h.fields['.cell-save-status'].dataset.state, 'saved');
});

test('unchanged input shows exit instead of sending a save', () => {
  const h = harness();
  h.input('changed');
  assert.equal(h.fields['.cell-close'].hidden, true);
  h.input('old');
  assert.equal(h.fields['.cell-close'].hidden, false);
  assert.equal(h.timers.size, 0);
  h.close();
  assert(!h.cell.classList.contains('is-editing'));
  assert.equal(h.requests.length, 0);
});

test('success tick returns to exit button after its confirmation period', async () => {
  const h = harness();
  h.input('saved'); h.tick();
  assert.equal(h.fields['.cell-close'].hidden, true);
  await h.complete(0, 'saved');
  assert.equal(h.fields['.cell-save-status'].textContent, '✓');
  assert.equal(h.fields['.cell-close'].hidden, true);
  h.tick();
  assert.equal(h.fields['.cell-save-status'].textContent, '');
  assert.equal(h.fields['.cell-close'].hidden, false);
});
