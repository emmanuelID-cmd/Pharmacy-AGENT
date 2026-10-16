/* No fetch handler or cache: private reports and credentials are never cached here. */
self.addEventListener('install', event => {event.waitUntil(self.skipWaiting());});
const orderId = value => typeof value === 'string' && value.length === 17 && /^demo-[a-f0-9]{12}$/.test(value);
const exactKeys = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) &&
  Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const displayText = (value, limit) => typeof value === 'string' && value.trim().length > 0 &&
  Array.from(value).length <= limit && !/[\p{C}\p{Zl}\p{Zp}<>]/u.test(value);
function orderPreview(value) {
  if (!exactKeys(value, ['kind', 'order_id', 'total_lines', 'lines']) || !['synthetic-order-v1', 'synthetic-delivery-v1'].includes(value.kind) ||
      !orderId(value.order_id) || !Number.isInteger(value.total_lines) || value.total_lines < 1 || value.total_lines > 150 ||
      !Array.isArray(value.lines) || value.lines.length < 1 || value.lines.length > Math.min(6, value.total_lines)) return null;
  if (!value.lines.every(line => exactKeys(line, ['label', 'quantity', 'unit', 'priority']) &&
      displayText(line.label, 120) && displayText(line.unit, 48) && Number.isInteger(line.quantity) &&
      line.quantity >= 1 && line.quantity <= 1000000 && ['CRITICAL', 'LOW', 'ABOVE_THRESHOLD', 'UNKNOWN'].includes(line.priority))) return null;
  return value;
}
self.addEventListener('push', event => {
  let message = null;
  try {message = orderPreview(event.data?.json());} catch (_) { /* Legacy/malformed push gets fixed fallback text. */ }
  const delivery = message?.kind === 'synthetic-delivery-v1';
  const body = message ? [(delivery ? 'Delivery received (demo) · ' : '') + message.order_id + ` · ${message.total_lines} item(s)`,
    ...message.lines.map(line => `${line.priority}: ${line.label} — ${line.quantity} ${line.unit}`),
    ...(message.total_lines > message.lines.length ? [`+${message.total_lines - message.lines.length} more item(s).`] : []),
    'Tap to view the complete submitted order.'].join('\n') :
    'Your human-reviewed demo order is ready. Open the app to review it.';
  event.waitUntil((async () => {
    await self.registration.showNotification(delivery ? 'Pharmacy delivery received · Synthetic' : 'Pharmacy demo order · Synthetic', {
    body, tag: message ? (delivery ? 'pharmacy-delivery-' : 'pharmacy-') + message.order_id : 'pharmacy-demo-order',
    data: message ? {order_id: message.order_id} : {}
    });
    if (message) {
      try {
        const windows = await self.clients.matchAll({type: 'window', includeUncontrolled: true});
        windows.forEach(client => {if (typeof client.postMessage === 'function') client.postMessage({type: 'pharmacy-demo-updated', order_id: message.order_id});});
      } catch (_) { /* Displayed notification remains valid if no page can refresh. */ }
    }
  })());
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const id = event.notification.data?.order_id;
  // Construct the destination here; supplied URLs and paths are never followed.
  const path = orderId(id) ? `/demo?order=${id}#order-result` : '/demo#closing-title';
  const destination = new URL(path, self.location.origin).href;
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({type: 'window', includeUncontrolled: true});
    const existing = windows.find(client => new URL(client.url).origin === self.location.origin);
    if (existing) {await existing.navigate(destination); return existing.focus();}
    return self.clients.openWindow(destination);
  })());
});
