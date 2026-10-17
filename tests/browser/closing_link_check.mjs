// Isolated DOM simulation of notification entry: no browser/network or external send.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const firstId = 'demo-012345abcdef', latestId = 'demo-abcdef012345';
const row = {item_id: 'catalog-001', label: 'Synthetic medication', package_ndc: '00000-000-00',
  unit: 'tablet', usable_quantity: 20, days_of_supply: '2.00', local_class: 'CRITICAL',
  reason_codes: [], suggestion: {suggested_quantity: 50}, evidence_reference: 'synthetic-evidence'};
const order = (id, quantity) => ({order_id: id, revision: 1, state: 'SIMULATED_SUBMISSION',
  submitted_at: 'synthetic-time', lines: [{...row, quantity}], test_sms: {message: 'Preview only'},
  manufacturer_notice: {scheduled_for: 'synthetic-next-shift'}});
const first = order(firstId, 20), latest = order(latestId, 30);
async function fixture(search, {unavailable = false, pendingNotification = false, pendingSubmit = false} = {}) {
  const elements = new Map(), requests = [], replacements = [];
  let notificationResolve;
  class Element {
    constructor(tag = 'div') {
      this.tag = tag; this.children = []; this.hidden = true; this.disabled = false;
      this.value = ''; this.textContent = ''; this.listeners = {}; this.attributes = {};
      this.classList = {toggle() {}};
    }
    append(...nodes) {this.children.push(...nodes);}
    replaceChildren(...nodes) {this.children = nodes;}
    setAttribute(key, value) {this.attributes[key] = value;}
    addEventListener(name, listener) {this.listeners[name] = listener;}
    querySelector(selector) {return selector === 'button' ? new Element('button') : null;}
    focus() {this.focused = true;}
    scrollIntoView() {this.scrolled = true;}
    async click() {await this.listeners.click?.();}
  }
  const get = id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  };
  const context = vm.createContext({URLSearchParams, Map, AbortController, clearTimeout,
    setTimeout: (callback, delay) => setTimeout(callback, pendingSubmit ? 5 : delay),
    crypto: {randomUUID: () => 'synthetic-intent-0001'}, Option: class extends Element {
    constructor(text, value) {super('option'); this.textContent = text; this.value = value;}
  }, document: {getElementById: get, createElement: tag => new Element(tag)},
  async fetch(path) {
    requests.push(path);
    if (unavailable) throw Error('synthetic-private-server-error');
    if (path === '/api/closing-demo/submit') return pendingSubmit ? new Promise(() => {}) :
      {ok: true, json: async () => order('demo-111111111111', 50)};
    return {ok: true, json: async () => ({closing: {closing_id: 'synthetic-close', rows: [row]},
      order: latest, orders: [first, latest], order_limit: 20})};
  }});
  context.window = context;
  context.location = {search};
  context.history = {state: null, replaceState: (...args) => replacements.push(args)};
  if (pendingNotification) context.notifyDemoOrder = () => new Promise(resolve => {notificationResolve = resolve;});
  vm.runInContext(fs.readFileSync('web/assets/closing.js', 'utf8'), context);
  context.bindClosingDemo();
  await new Promise(resolve => setImmediate(resolve));
  const text = element => element.textContent + element.children.map(text).join(' ');
  return {get, text, requests, replacements, finishNotification() {notificationResolve();}};
}

const older = await fixture('?order=' + firstId);
assert.deepEqual(older.requests, ['/api/closing-demo/close']);
assert.equal(older.get('order-result').hidden, false);
assert.match(older.text(older.get('order-result')), new RegExp(firstId));
assert.equal(older.text(older.get('order-result')).includes(latestId), false);
assert.match(older.text(older.get('order-result')), /20 tablet/);
assert.equal(older.get('order-result').focused, true);
assert.equal(older.get('order-result').scrolled, true);
await older.get('new-demo-order').click();
assert.equal(older.get('order-result').hidden, true);
assert.equal(older.get('submit-demo-order').disabled, false);
assert.equal(older.replacements[0][2], '/demo#closing-title');

for (const id of ['demo-000000000000', firstId + '%0A', 'https://untrusted.example', '']) {
  const missing = await fixture('?order=' + id);
  assert.equal(missing.get('order-result').hidden, true);
  assert.match(missing.get('order-status').textContent, /unavailable/);
  assert.equal(missing.get('order-status').textContent.includes(latestId), false);
}
const normal = await fixture('');
assert.equal(normal.requests.length, 0);
await normal.get('close-day').click();
assert.match(normal.text(normal.get('order-result')), new RegExp(latestId));
const failed = await fixture('?order=' + firstId, {unavailable: true});
assert.equal(failed.get('order-result').hidden, true);
assert.match(failed.get('closing-status').textContent, /could not be verified/);
assert.equal(failed.get('closing-status').textContent.includes('private-server-error'), false);
assert.equal(failed.get('close-day').disabled, false);
const pending = await fixture('', {pendingNotification: true});
await pending.get('close-day').click();
await pending.get('new-demo-order').click();
pending.get('order-item').value = 'catalog-001';
pending.get('order-add-form').listeners.submit({preventDefault() {}});
const submit = pending.get('demo-order-form').listeners.submit({preventDefault() {}});
await new Promise(resolve => setImmediate(resolve));
assert.equal(pending.get('new-demo-order').disabled, false, 'A pending push must not lock the next order');
assert.equal(pending.get('submit-demo-order').disabled, true);
assert.equal(pending.get('submit-demo-order').textContent, 'Order submitted');
await pending.get('new-demo-order').click();
assert.equal(pending.get('submit-demo-order').disabled, false);
pending.finishNotification(); await submit;
assert.equal(pending.get('submit-demo-order').disabled, false);
const stalledOrder = await fixture('', {pendingSubmit: true});
await stalledOrder.get('close-day').click();
await stalledOrder.get('new-demo-order').click();
stalledOrder.get('order-item').value = 'catalog-001';
stalledOrder.get('order-add-form').listeners.submit({preventDefault() {}});
await Promise.race([stalledOrder.get('demo-order-form').listeners.submit({preventDefault() {}}),
  new Promise((_, reject) => setTimeout(() => reject(Error('Order request never settled')), 100))]);
assert.equal(stalledOrder.get('submit-demo-order').disabled, false);
assert.equal(stalledOrder.get('submit-demo-order').textContent, 'Submit demo order');
assert.match(stalledOrder.get('order-status').textContent, /not confirmed/);
assert.match(stalledOrder.text(stalledOrder.get('order-list')), /Synthetic medication/);
console.log('PASS: exact older-order entry, focus, unavailable/malformed link, new-draft recovery, normal latest recovery and failed request. No sends.');
