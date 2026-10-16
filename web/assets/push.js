/* Opt-in notifications for the browser submitting the human-reviewed demo order. */
(() => {
  'use strict';
  let subscription = null, configuration = null, busy = false, restoreTask = null, notificationSequence = 0;
  const get = id => document.getElementById(id);
  const supported = () => window.isSecureContext && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  function show(message, error = false) {
    ['push-status', 'order-notification-status'].forEach(id => {
      const target = get(id);
      if (target) {target.hidden = false; target.textContent = message; target.classList.toggle('is-error', error);}
    });
  }
  function controls() {
    if (!get('enable-push')) return;
    get('enable-push').disabled = busy || !supported() || !configuration?.configured || !!subscription;
    get('disable-push').disabled = busy || !subscription;
  }
  function applicationKey(value) {
    const text = atob(value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - value.length % 4) % 4));
    return Uint8Array.from(text, character => character.charCodeAt(0));
  }
  async function bounded(promise) {
    let timer;
    try {
      return await Promise.race([promise, new Promise((_, reject) => {
        timer = setTimeout(() => {const error = Error(); error.name = 'TimeoutError'; reject(error);}, 20000);
      })]);
    } finally {clearTimeout(timer);}
  }
  async function request(path, options = {}) {
    const controller = new AbortController();
    try {
      return await bounded((async () => {
        const response = await fetch(path, {...options, signal: controller.signal});
        window.handleAuthRequired?.(response);
        return {response, result: await response.json()};
      })());
    } finally {controller.abort();}
  }
  async function updateWorker(registration) {
    const sequence = notificationSequence;
    try {await bounded(registration.update());}
    catch (_) {
      if (subscription && sequence === notificationSequence) show('Notifications remain enabled, but the browser worker update was not confirmed. Refresh before your next test. Reference: PUSH_WORKER_UPDATE_UNCONFIRMED.', true);
    }
  }
  function enableFailure(stage, error) {
    const names = {AbortError: 'ABORTED', NotAllowedError: 'NOT_ALLOWED', NotSupportedError: 'UNSUPPORTED',
      SecurityError: 'SECURITY', InvalidStateError: 'INVALID_STATE', InvalidAccessError: 'INVALID_KEY', TypeError: 'SETUP_ERROR', TimeoutError: 'TIMED_OUT'};
    // Only fixed labels leave this handler. Native error messages may contain URLs/keys.
    const reference = `PUSH_${stage}_${names[error?.name] || 'FAILED'}`;
    const advice = !navigator.onLine ? 'No Internet Access. Reconnect, then try Enable again.' :
      error?.name === 'TimeoutError' ? 'The browser has not confirmed notification setup. Respond to any pending permission prompt. For phone testing, open the deployed HTTPS page directly in Android Chrome.' :
      error?.name === 'NotAllowedError' ? 'The browser refused notification access. Check this site’s notification permission in Chrome on Android.' :
      stage === 'PERMISSION' ? 'This browser could not request notification permission. Open the deployed HTTPS page directly in Chrome on Android.' :
      stage === 'WORKER' ? 'This browser could not start notification setup. Open the deployed HTTPS page directly in Chrome on Android.' :
      'This browser could not connect notifications to its push service. For the phone test, use the deployed HTTPS page in Android Chrome, outside an embedded preview. Check your connection and try Enable again.';
    show(`${advice} Your order is unchanged. Reference: ${reference}.`, true);
  }
  async function restore() {
    if (!supported()) {show('Notifications need a supported browser and HTTPS. Use Chrome on Android on the deployed site.'); controls(); return;}
    try {
      const {response, result} = await request('/api/push/config');
      if (!response.ok) throw Error('CONFIG_UNAVAILABLE');
      configuration = result;
      const registration = await bounded(navigator.serviceWorker.getRegistration('/'));
      subscription = registration ? await bounded(registration.pushManager.getSubscription()) : null;
      if (Notification.permission !== 'granted') subscription = null;
      show(!configuration.configured ? 'Notifications are not configured on this server yet. Orders still work.' :
        subscription ? 'Notifications enabled for this browser. Submitted item names and quantities can appear on this device’s notification screen.' :
        Notification.permission === 'denied' ? 'Notifications are blocked. Allow this site in Chrome’s notification settings, then enable here.' :
        'Notifications are off. Enable them to receive your submitted items and quantities on this device’s notification screen.');
      if (registration) void updateWorker(registration);
      try {await bounded(window.registerPairedPush?.(subscription?.toJSON() || null));}
      catch (_) {show("Browser notifications are available, but paired-phone registration is unconfirmed. Refresh pairing before submitting.", true);}
    } catch (_) {show(navigator.onLine ? 'Temporarily Unavailable. Reload to check notification setup again. Orders still work.' : 'No Internet Access. Reconnect and reload. Orders still work when the server is reachable.', true);}
    controls();
  }
  window.bindPushNotifications = () => {
    if (!get('enable-push')) return;
    configuration = null; controls(); restoreTask = restore();
    get('enable-push').addEventListener('click', async () => {
      if (busy || !configuration?.configured || !supported()) return;
      busy = true; controls(); show('Waiting for your browser’s notification permission…');
      let stage = 'PERMISSION';
      try {
        // Permission is requested only in direct response to the button press.
        if (await bounded(Notification.requestPermission()) !== 'granted') {
          show('Notifications were not enabled. You can continue using the order form. To change a blocked choice, use Chrome’s site settings.'); return;
        }
        stage = 'WORKER';
        show('Starting notification setup in this browser…');
        const registration = await bounded(navigator.serviceWorker.register('/push-worker.js', {scope: '/', updateViaCache: 'none'}));
        await bounded(navigator.serviceWorker.ready);
        stage = 'SUBSCRIPTION';
        show('Connecting this browser to its push service…');
        subscription = await bounded(registration.pushManager.getSubscription());
        if (subscription && String(new Uint8Array(subscription.options.applicationServerKey)) !== String(applicationKey(configuration.public_key))) {
          await bounded(subscription.unsubscribe()); subscription = null;
        }
        subscription ||= await bounded(registration.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: applicationKey(configuration.public_key)}));
        await bounded(window.registerPairedPush?.(subscription.toJSON()));
        show('Notifications enabled for this browser. Submitted item names and quantities can appear on this device’s notification screen.');
      } catch (error) {subscription = null; enableFailure(stage, error);}
      finally {busy = false; controls();}
    });
    get('disable-push').addEventListener('click', async () => {
      if (busy || !subscription) return;
      busy = true; notificationSequence++; controls();
      try {
        if (!await subscription.unsubscribe()) throw Error('UNSUBSCRIBE_FAILED');
        subscription = null; await bounded(window.registerPairedPush?.(null)); show('Notifications disabled for this browser. Previously accepted notifications may still arrive.');
      } catch (_) {show('Could not confirm disabling notifications. Block notifications for this site in Chrome settings, or try Disable again.', true);}
      finally {busy = false; controls();}
    });
  };
  window.refreshPairedPush = async () => {
    await bounded(restoreTask);
    await bounded(window.registerPairedPush?.(subscription && Notification.permission === 'granted' ? subscription.toJSON() : null));
  };
  window.notifyDemoOrder = async order => {
    const sequence = ++notificationSequence;
    const label = /^demo-[a-f0-9]{12}$/.test(order.order_id) && order.order_id.length === 17 ? `Order ${order.order_id}: ` : '';
    const report = (message, error = false) => {if (sequence === notificationSequence) show(label + message, error);};
    try {await bounded(restoreTask);}
    catch (_) {report('Notification setup was not confirmed. Your order remains recorded. Try Enable before a new order. Reference: PUSH_SETUP_TIMED_OUT.', true); return;}
    if (!subscription || Notification.permission !== 'granted') {
      report('Demo order recorded. No phone notification requested because notifications are off or setup is incomplete in this browser. Enable notifications before your next order. Reference: PUSH_NOT_ENABLED.'); return;
    }
    report('Order recorded. Requesting its phone notification… You can start a New demo order while this finishes.');
    const reasons = {
      DEMO_BOTH_PHONES_NOT_READY: 'Pair both phones and enable notifications on each before submitting.',
      DEMO_RECIPIENT_NOT_READY: 'The receiving phone has not enabled notifications. The order remains recorded.',
      DEMO_SHARED_STORE_UNAVAILABLE: 'Shared demo storage is temporarily unavailable. The recorded order is preserved.',
      DEMO_PAIRING_ENDED: 'This pairing has ended. The recorded order is preserved.',
      DEMO_DEVICE_NOT_PAIRED_OR_EXPIRED: 'This pairing expired. No notification was sent.',

      DEMO_ORDER_NOT_FOUND: 'The recorded order is unavailable on this server worker. No notification was sent. Refresh and inspect submitted-order history.',
      PUSH_KEYS_NOT_CONFIGURED: 'Notifications are not configured on this server. The order remains recorded.',
      PUSH_SUBSCRIPTION_INVALID: 'The notification subscription could not be verified. Disable and enable notifications before a new order.',
      PUSH_ORDER_CONTENT_INVALID: 'The submitted order could not be formatted for notification. The order remains recorded.',
      PUSH_SERVICE_REJECTED: 'The push service rejected the notification. The order remains recorded.',
      PUSH_SUBSCRIPTION_EXPIRED: 'This notification subscription expired. Disable and enable notifications before a new order.',
      PUSH_DELIVERY_UNCONFIRMED: 'Notification delivery is unconfirmed. The order remains recorded.'
    };
    try {
      const json = subscription.toJSON();
      const {response, result} = await request('/api/closing-demo/notify', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({closing_id: order.closing_id, order_id: order.order_id, subscription: {endpoint: json.endpoint, keys: json.keys}})});
      if (response.ok && result.push_service_accepted === true) report('Accepted by the push service. Check your phone; delivery is not confirmed. Your order remains a simulation.');
      else {
        const code = Object.hasOwn(reasons, result.reason_code) ? result.reason_code :
          result.state === 'SUBSCRIPTION_EXPIRED' ? 'PUSH_SUBSCRIPTION_EXPIRED' : 'PUSH_REQUEST_REJECTED';
        report(`${reasons[code] || 'The notification request was not accepted. Your order remains recorded.'} It will not retry automatically. Reference: ${code}.`, true);
      }
    } catch (error) {
      const code = error?.name === 'TimeoutError' ? 'PUSH_REQUEST_TIMED_OUT' : 'PUSH_REQUEST_UNCONFIRMED';
      report(`${navigator.onLine ? 'Temporarily Unavailable. Notification delivery is unconfirmed.' : 'No Internet Access. Notification delivery is unconfirmed.'} Your order remains recorded; no automatic retry will run. Reference: ${code}.`, true);
    }
  };
})();
