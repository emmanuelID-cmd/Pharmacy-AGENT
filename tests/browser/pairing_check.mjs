// Two-device UI simulations: no real browser permission, database or push sends.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const id = 'demo-012345abcdef';
const submitted = {order_id: id, submitted_at: 'synthetic-time', lines: [{local_class: 'CRITICAL', label: 'Synthetic item', quantity: 2, unit: 'tablet'}]};
async function fixture({role = null, configured = true, orders = [], rejectedCode = false, pendingDelivery = false, pendingStatus = false} = {}) {
  const elements = new Map(), calls = [];
  class Element {
    constructor(tag = 'div') {
      this.tag = tag; this.children = []; this.hidden = false; this.disabled = false; this.value = ''; this.textContent = '';
      this.listeners = {}; this.attributes = {}; this.dataset = {}; this.classes = new Set();
      this.classList = {contains: key => this.classes.has(key), toggle: (key, value) => value ? this.classes.add(key) : this.classes.delete(key)};
    }
    set id(value) {this.identity = value; elements.set(value, this);}
    get id() {return this.identity;}
    append(...nodes) {this.children.push(...nodes);}
    replaceChildren(...nodes) {this.children = nodes;}
    setAttribute(name, value) {this.attributes[name] = value;}
    addEventListener(name, callback) {this.listeners[name] = callback;}
    focus() {this.focused = true;}
    scrollIntoView() {this.scrolled = true;}
    querySelectorAll() {const all = this.children.flatMap(node => [node, ...node.querySelectorAll()]); return all.filter(node => node.tag === 'button' && node.dataset.deliveryOrder);}
    async click() {await this.listeners.click?.();}
  }
  const ids = ['pair-create','pair-join-submit','pair-code','pair-code-error','pair-errors','pair-refresh','pair-end','pair-renew','pair-join-form',
    'pair-invite','pair-invite-code','pair-copy','pair-inbox','pair-status','close-day','closing-report','closing-workspace','closing-status'];
  ids.forEach(key => {const element = new Element(); element.id = key;});
  let status = {configured, role, paired: !!role, orders, notifications: {orderer: true, manufacturer: true}};
  const get = key => elements.get(key) || null;
  const ctx = vm.createContext({URLSearchParams, AbortController, clearTimeout,
    setTimeout: (callback, delay) => setTimeout(callback, pendingDelivery || pendingStatus ? 5 : delay),
    document: {getElementById: get, createElement: tag => new Element(tag)},
    navigator: {serviceWorker: {addEventListener() {}}, clipboard: {writeText: async () => {}}},
    async fetch(path, options) {
      calls.push([path, JSON.parse(options.body)]);
      let ok = true, result;
      if (path.endsWith('/status')) return {ok: true, json: async () => pendingStatus ? new Promise(() => {}) : structuredClone(status)};
      if (path.endsWith('/join')) {
        if (rejectedCode) {ok = false; result = {reason_code: 'DEMO_PAIRING_CODE_INVALID_OR_EXPIRED', message: 'native-secret-must-not-leak'};}
        else {status = {...status, role: 'manufacturer', paired: true}; result = {role: 'manufacturer'};}
      } else if (path.endsWith('/delivery')) {
        if (pendingDelivery) return new Promise(() => {});
        status = {...status, orders: status.orders.map(order => ({...order, delivery: {confirmed_at: 'synthetic-confirmation'}}))};
        result = {notification: {push_service_accepted: true}};
      } else if (path.endsWith('/create')) {status = {...status, role: 'orderer', paired: false}; result = {code: 'a'.repeat(24)};}
      else result = {};
      return {ok, json: async () => result};
    }});
  ctx.window = ctx; ctx.location = {search: '', reload() {}};
  vm.runInContext(fs.readFileSync('web/assets/pairing.js', 'utf8'), ctx);
  ctx.bindPairedDemo(); await ctx.pairingReady;
  const settle = async () => {await new Promise(resolve => setImmediate(resolve)); await new Promise(resolve => setImmediate(resolve));};
  const allText = node => node.textContent + node.children.map(allText).join(' ');
  return {get, ctx, calls, settle, allText, deliveries: () => get('pair-inbox').querySelectorAll('button[data-delivery-order]')};
}
const missing = await fixture({configured: false});
assert.equal(missing.get('pair-create').disabled, true);
assert.match(missing.get('pair-status').textContent, /not configured/);
const invalid = await fixture();
invalid.get('pair-code').value = 'short';
invalid.get('pair-join-form').listeners.submit({preventDefault() {}});
assert.equal(invalid.get('pair-errors').hidden, false);
assert.equal(invalid.get('pair-code').attributes['aria-invalid'], 'true');
assert.equal(invalid.calls.some(([path]) => path.endsWith('/join')), false);
assert.equal(invalid.get('pair-code').value, 'short');
const rejected = await fixture({rejectedCode: true});
rejected.get('pair-code').value = 'a'.repeat(24);
rejected.get('pair-join-form').listeners.submit({preventDefault() {}}); await rejected.settle();
assert.equal(rejected.get('pair-errors').hidden, false);
assert.equal(rejected.get('pair-code').attributes['aria-invalid'], 'true');
assert.equal(rejected.get('pair-status').textContent.includes('native-secret'), false);
assert.equal(rejected.get('pair-join-submit').disabled, false);
const waiting = await fixture({role: 'manufacturer'});
assert.equal(waiting.deliveries().length, 0);
assert.equal(waiting.get('close-day').hidden, true);
const ready = await fixture({role: 'manufacturer', orders: [submitted]});
assert.equal(ready.deliveries().length, 1);
assert.equal(ready.deliveries()[0].disabled, false);
await ready.get('pair-refresh').click();
assert.equal(ready.deliveries()[0].disabled, false, 'Refreshing while busy must release delivery controls afterward');
await ready.deliveries()[0].click();
assert.equal(ready.deliveries()[0].disabled, true);
assert.equal(ready.deliveries()[0].textContent, 'Delivery confirmed');
assert.equal(ready.calls.filter(([path]) => path.endsWith('/delivery')).length, 1);
assert.match(ready.get('pair-status').textContent, /return alert was accepted/);
const pending = await fixture({role: 'manufacturer', orders: [submitted], pendingDelivery: true});
await pending.deliveries()[0].click();
assert.equal(pending.deliveries()[0].disabled, false);
assert.match(pending.get('pair-status').textContent, /not confirmed/);
const stalled = await fixture({pendingStatus: true});
assert.match(stalled.get('pair-status').textContent, /not confirmed/);
console.log('PASS: pairing config/code validation, server-code redaction, role view, no pre-submit delivery, refreshed control release, delivery confirmation and timeout recovery. No sends.');
