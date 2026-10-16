// Isolated browser API simulations: no permission prompt, push subscription or external send.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync('web/assets/push.js', 'utf8');
async function fixture({permission = 'default', configured = true, outcome = 'accepted', offline = false, failAt = '', pendingPermission = false,
  restored = false, updateFails = false, updatePending = false, pendingSend = false, pendingBody = false, rejection = '', deferFirstSend = false} = {}) {
  function fail(stage) {
    if (failAt === stage) {
      const error = Error('synthetic-private-endpoint-and-key-must-not-appear');
      error.name = stage === 'SUBSCRIPTION' ? 'AbortError' : 'TypeError'; throw error;
    }
  }
  const elements = Object.fromEntries(['enable-push', 'disable-push', 'push-status', 'order-notification-status'].map(id => [id, {
    disabled: false, hidden: true, textContent: '', classList: {toggle() {}}, listeners: {},
    addEventListener(name, handler) {this.listeners[name] = handler;}
  }]));
  const counts = {permission: 0, subscribe: 0, notify: 0, unsubscribe: 0, update: 0};
  const key = new Uint8Array([4, 1, 2]);
  const subscribed = () => ({options: {applicationServerKey: key},
    toJSON: () => ({endpoint: 'https://fcm.googleapis.com/fcm/send/synthetic-endpoint', expirationTime: null, keys: {p256dh: 'synthetic', auth: 'synthetic'}}),
    async unsubscribe() {counts.unsubscribe++; current = null; return true;}});
  let current = restored ? subscribed() : null, finishSend;
  const registration = {async update() {counts.update++; if (updateFails) throw Error('private-worker-failure'); if (updatePending) return new Promise(() => {});}, pushManager: {
    async getSubscription() {return current;},
    async subscribe() {
      fail('SUBSCRIPTION');
      counts.subscribe++;
      current = subscribed();
      return current;
    }
  }};
  const context = vm.createContext({Uint8Array, AbortController, atob, console, clearTimeout,
    setTimeout: (callback, delay) => setTimeout(callback, pendingPermission || updatePending || pendingSend || pendingBody ? 5 : delay),
    document: {getElementById: id => elements[id]},
    navigator: {onLine: !offline, serviceWorker: {getRegistration: async () => registration,
      register: async () => {fail('WORKER'); return registration;}, ready: Promise.resolve(registration)}},
    Notification: {permission, async requestPermission() {fail('PERMISSION'); counts.permission++; if (pendingPermission) return new Promise(() => {}); return this.permission;}},
    async fetch(path, options) {
      if (offline) throw Error('offline');
      if (path === '/api/push/config') return {ok: true, json: async () => ({configured, public_key: 'BAEC'})};
      counts.notify++;
      const submitted = JSON.parse(options.body);
      assert.equal('expirationTime' in submitted.subscription, false);
      assert.equal('message' in submitted, false);
      if (pendingSend) return new Promise(() => {});
      if (deferFirstSend && counts.notify === 1) return new Promise(resolve => {
        finishSend = () => resolve({ok: false, json: async () => ({reason_code: 'PUSH_SERVICE_REJECTED'})});
      });
      return {ok: !rejection, json: async () => pendingBody ? new Promise(() => {}) :
        ({reason_code: rejection, push_service_accepted: outcome === 'accepted' && !rejection, state: outcome === 'expired' ? 'SUBSCRIPTION_EXPIRED' : 'Temporarily Unavailable'})};
    }});
  context.window = context; context.isSecureContext = true; context.PushManager = {};
  vm.runInContext(source, context); context.bindPushNotifications();
  await new Promise(resolve => setImmediate(resolve));
  return {context, elements, counts, async enable() {await elements['enable-push'].listeners.click();},
    async disable() {await elements['disable-push'].listeners.click();},
    async send(id = 'synthetic-order') {await context.notifyDemoOrder({closing_id: 'synthetic-closing', order_id: id});},
    finishSend() {finishSend();},
    status() {return elements['push-status'].textContent;}};
}

const allowed = await fixture({permission: 'granted'});
assert.equal(allowed.counts.update, 1);
assert.equal(allowed.counts.permission, 0); assert.equal(allowed.counts.subscribe, 0);
await allowed.enable(); assert.equal(allowed.counts.permission, 1); assert.equal(allowed.counts.subscribe, 1);
await allowed.send(); assert.equal(allowed.counts.notify, 1); assert.match(allowed.status(), /delivery is not confirmed/);
assert.equal(allowed.elements['order-notification-status'].textContent, allowed.status());
await allowed.disable(); await allowed.send(); assert.equal(allowed.counts.unsubscribe, 1); assert.equal(allowed.counts.notify, 1);

const denied = await fixture({permission: 'denied'});
await denied.enable(); await denied.send(); assert.equal(denied.counts.subscribe, 0); assert.equal(denied.counts.notify, 0);
assert.match(denied.status(), /notifications are off/);
const missing = await fixture({configured: false});
assert.equal(missing.elements['enable-push'].disabled, true); await missing.enable(); assert.equal(missing.counts.permission, 0);
const offline = await fixture({offline: true}); assert.match(offline.status(), /No Internet Access/);
const expired = await fixture({permission: 'granted', outcome: 'expired'});
await expired.enable(); await expired.send(); assert.match(expired.status(), /expired/);
const failed = await fixture({permission: 'granted', outcome: 'failed'});
await failed.enable(); await failed.send(); assert.match(failed.status(), /will not retry automatically/);
for (const stage of ['PERMISSION', 'WORKER', 'SUBSCRIPTION']) {
  const broken = await fixture({permission: 'granted', failAt: stage});
  await broken.enable();
  assert.match(broken.status(), new RegExp('PUSH_' + stage + '_'));
  assert.match(broken.status(), /Your order is unchanged/);
  assert.equal(broken.status().includes('synthetic-private-endpoint-and-key'), false);
  assert.equal(broken.elements['enable-push'].disabled, false);
  assert.equal(broken.counts.notify, 0);
}
const pendingPermission = await fixture({permission: 'granted', pendingPermission: true});
await pendingPermission.enable();
assert.match(pendingPermission.status(), /PUSH_PERMISSION_TIMED_OUT/);
assert.equal(pendingPermission.elements['enable-push'].disabled, false);
assert.equal(pendingPermission.counts.subscribe, 0);

const updateFailure = await fixture({permission: 'granted', restored: true, updateFails: true});
await updateFailure.send();
assert.equal(updateFailure.counts.notify, 1, 'An update failure must not lose the existing subscription');
const updatePending = await fixture({permission: 'granted', restored: true, updatePending: true});
await updatePending.send();
assert.equal(updatePending.counts.notify, 1, 'An update wait must not block a restored subscription');
for (const options of [{pendingSend: true}, {pendingBody: true}]) {
  const stalled = await fixture({permission: 'granted', restored: true, ...options});
  await Promise.race([stalled.send(), new Promise((_, reject) => setTimeout(() => reject(Error('Notification request never settled')), 100))]);
  assert.match(stalled.status(), /PUSH_REQUEST_TIMED_OUT/);
  assert.equal(stalled.counts.notify, 1);
}
for (const reason of ['DEMO_ORDER_NOT_FOUND', 'PUSH_KEYS_NOT_CONFIGURED', 'PUSH_SERVICE_REJECTED']) {
  const rejected = await fixture({permission: 'granted', restored: true, rejection: reason});
  await rejected.send();
  assert.match(rejected.status(), new RegExp(reason));
}
const unknownReason = await fixture({permission: 'granted', restored: true, rejection: 'private-key-or-endpoint-must-not-appear'});
await unknownReason.send();
assert.match(unknownReason.status(), /PUSH_REQUEST_REJECTED/);
assert.equal(unknownReason.status().includes('private-key-or-endpoint'), false);
const superseded = await fixture({permission: 'granted', restored: true, deferFirstSend: true});
const firstSend = superseded.send('demo-111111111111');
await new Promise(resolve => setImmediate(resolve));
await superseded.send('demo-222222222222');
const latestStatus = superseded.status();
superseded.finishSend(); await firstSend;
assert.equal(superseded.status(), latestStatus);
assert.match(latestStatus, /demo-222222222222/);
const disabledDuringSend = await fixture({permission: 'granted', restored: true, deferFirstSend: true});
const lateSend = disabledDuringSend.send();
await new Promise(resolve => setImmediate(resolve));
await disabledDuringSend.disable();
const disabledStatus = disabledDuringSend.status();
disabledDuringSend.finishSend(); await lateSend;
assert.equal(disabledDuringSend.status(), disabledStatus);

const listeners = {}, opened = [], shown = [];
let windows = [];
const worker = vm.createContext({URL, self: {location: {origin: 'https://demo.example'},
  skipWaiting: async () => {},
  addEventListener: (name, listener) => {listeners[name] = listener;},
  registration: {showNotification: async (...args) => {shown.push(args);}},
  clients: {matchAll: async () => windows, openWindow: async url => {opened.push(url);}}}});
vm.runInContext(fs.readFileSync('web/assets/push-worker.js', 'utf8'), worker);
let work;
listeners.push({data: {json: () => ({title: 'injected', url: 'https://untrusted.example'})}, waitUntil: promise => {work = promise;}}); await work;
assert.equal(shown[0][0], 'Pharmacy demo order · Synthetic'); assert.equal('fetch' in listeners, false);
listeners.notificationclick({notification: {close() {}, data: {url: 'https://untrusted.example'}}, waitUntil: promise => {work = promise;}}); await work;
assert.deepEqual(opened, ['https://demo.example/demo#closing-title']);
const message = {kind: 'synthetic-order-v1', order_id: 'demo-012345abcdef', total_lines: 2, lines: [
  {label: 'Amlodipine 10 mg', quantity: 20, unit: 'tablet', priority: 'CRITICAL'},
  {label: 'Metformin 500 mg', quantity: 30, unit: 'tablet', priority: 'LOW'}]};
async function push(value) {
  listeners.push({data: {json: () => value}, waitUntil: promise => {work = promise;}}); await work;
  return shown.at(-1)[1];
}
const preview = await push(message);
assert.match(preview.body, /CRITICAL: Amlodipine 10 mg — 20 tablet/);
assert.match(preview.body, /LOW: Metformin 500 mg — 30 tablet/);
assert.equal(preview.tag, 'pharmacy-demo-012345abcdef');
listeners.notificationclick({notification: {close() {}, data: preview.data}, waitUntil: promise => {work = promise;}}); await work;
assert.equal(opened.at(-1), 'https://demo.example/demo?order=demo-012345abcdef#order-result');
const navigated = []; let focused = 0;
windows = [{url: 'https://demo.example/tools', async navigate(url) {navigated.push(url);}, async focus() {focused++;}}];
listeners.notificationclick({notification: {close() {}, data: {...preview.data, url: 'https://untrusted.example'}}, waitUntil: promise => {work = promise;}}); await work;
assert.deepEqual(navigated, ['https://demo.example/demo?order=demo-012345abcdef#order-result']);
assert.equal(focused, 1);
const long = await push({...message, total_lines: 150});
assert.match(long.body, /\+148 more item/);
for (const invalid of [null, {...message, url: 'https://untrusted.example'}, {...message, order_id: message.order_id + '\n'},
  {...message, lines: []}, {...message, total_lines: 151}, {...message, lines: [{...message.lines[0], quantity: true}]},
  ...['<script>bad</script>', 'Drug\u200b name', 'Drug\u202e name', 'a\nb'].map(label => ({...message, lines: [{...message.lines[0], label}]}))]) {
  const result = await push(invalid);
  assert.match(result.body, /^Your human-reviewed demo order is ready/);
  assert.equal(Object.keys(result.data).length, 0);
}
listeners.push({data: {json() {throw Error('malformed-private-text');}}, waitUntil: promise => {work = promise;}}); await work;
assert.equal(shown.at(-1)[1].body.includes('malformed-private-text'), false);
listeners.install({waitUntil: promise => {work = promise;}}); await work;
console.log('PASS: opt-in, worker update, failure states, selected-order text, long-list summary, malformed fallback and exact same-origin order click. No external sends.');
