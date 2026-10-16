/* Explicit two-device demo enrollment; credentials stay in HttpOnly cookies. */
(() => {
  'use strict';
  let state = null, generation = 0, busy = false;
  const get = id => document.getElementById(id);
  const text = (tag, value) => {const node = document.createElement(tag); node.textContent = String(value); return node;};
  const messages = {
    DEMO_SHARED_STORE_NOT_CONFIGURED: 'Two-phone storage is not configured on this deployment. The existing single-browser demo remains available.',
    DEMO_SHARED_STORE_UNAVAILABLE: 'Shared demo storage is temporarily unavailable. Keep your work and retry the status check.',
    DEMO_PAIRING_CODE_INVALID: 'Paste the complete 24-character pairing code.',
    DEMO_PAIRING_CODE_INVALID_OR_EXPIRED: 'This code expired or was already used. Ask the ordering phone for a new code.',
    DEMO_END_CURRENT_PAIRING_FIRST: 'End the current pairing before starting another.',
    DEMO_DEVICE_NOT_PAIRED_OR_EXPIRED: 'This pairing expired. End pairing here, then create or join a new one.',
    DEMO_DEVICE_NOT_PAIRED: 'This phone is not paired. Create or join a pairing first.',
    DEMO_PAIRING_ENDED: 'This pairing was ended. End pairing here to clear it, then create or join a new one.',
    DEMO_ROLE_FORBIDDEN: 'This action belongs to the other paired phone.',
    DEMO_ORDER_NOT_FOUND: 'That submitted order is unavailable. Refresh the received-order list.',
    DEMO_BOTH_PHONES_NOT_READY: 'Pair both phones and enable notifications on each before submitting.',
    DEMO_RECIPIENT_NOT_READY: 'The receiving phone has not enabled notifications. The recorded order or delivery is preserved.'
  };
  function show(message, error = false) {
    const target = get('pair-status'); if (!target) return;
    target.hidden = false; target.textContent = message; target.classList.toggle('is-error', error);
  }
  async function request(path, body = {}) {
    const controller = new AbortController(); let timer;
    try {
      return await Promise.race([(async () => {
        const response = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), signal: controller.signal});
        const result = await response.json();
        if (!response.ok) {const error = Error(); error.code = Object.hasOwn(messages, result.reason_code) ? result.reason_code : 'PAIR_REQUEST_UNCONFIRMED'; throw error;}
        return result;
      })(), new Promise((_, reject) => {timer = setTimeout(() => {controller.abort(); const error = Error(); error.code = 'PAIR_REQUEST_UNCONFIRMED'; reject(error);}, 20000);})]);
    } finally {clearTimeout(timer); controller.abort();}
  }
  function failure(error) {
    if (['DEMO_PAIRING_CODE_INVALID', 'DEMO_PAIRING_CODE_INVALID_OR_EXPIRED'].includes(error?.code) && get('pair-code')) {
      get('pair-code').setAttribute('aria-invalid', 'true');
      get('pair-code-error').textContent = messages[error.code]; get('pair-code-error').hidden = false;
      const summary = get('pair-errors'); summary.replaceChildren(text('strong', 'Check the pairing code'));
      const link = text('a', messages[error.code]); link.href = '#pair-code';
      link.addEventListener('click', event => {event.preventDefault(); get('pair-code').focus();});
      summary.append(link); summary.hidden = false; summary.focus();
    }
    show(messages[error?.code] || 'The request was not confirmed. Refresh pairing or orders before trying again; nothing will resend automatically.', true);
  }
  function controls() {
    if (!get('pair-create')) return;
    get('pair-create').disabled = busy || !state?.configured || !!state?.role;
    get('pair-join-submit').disabled = busy || !state?.configured || !!state?.role;
    get('pair-code').disabled = busy || !!state?.role;
    get('pair-refresh').disabled = busy || !state?.configured;
    get('pair-end').disabled = busy;
    get('pair-end').hidden = !state?.role && !get('pair-status')?.classList.contains('is-error');
    get('pair-renew').hidden = state?.role !== 'orderer' || state?.paired;
    get('pair-renew').disabled = busy;
    if (state?.paired) {get('pair-invite-code').value = ''; get('pair-invite').hidden = true;}
    get('pair-join-form').hidden = !!state?.role;
    get('pair-create').hidden = !!state?.role;
    get('pair-inbox')?.querySelectorAll('button[data-delivery-order]').forEach(button => {button.disabled = busy || !!state?.orders.find(order => order.order_id === button.dataset.deliveryOrder)?.delivery;});
    const supplier = state?.role === 'manufacturer';
    if (get('close-day')) get('close-day').hidden = supplier;
    if (supplier) ['closing-report', 'closing-workspace', 'closing-status'].forEach(id => {if (get(id)) get(id).hidden = true;});
  }
  function draw() {
    controls(); const inbox = get('pair-inbox'); if (!inbox) return;
    inbox.replaceChildren(); inbox.hidden = state?.role !== 'manufacturer';
    if (state?.role !== 'manufacturer') return;
    inbox.append(text('h3', 'Received demo orders'));
    if (!state.orders.length) {inbox.append(text('p', 'Waiting for the ordering phone to submit. No delivery can be confirmed yet.')); return;}
    [...state.orders].reverse().forEach(order => {
      const card = text('article', ''); card.className = 'order-line'; card.id = 'paired-' + order.order_id;
      card.append(text('h4', order.order_id), text('p', 'Synthetic order · ' + order.submitted_at));
      const list = text('ul', '');
      order.lines.forEach(line => list.append(text('li', `${line.local_class} · ${line.label} · ${line.quantity} ${line.unit}`)));
      const button = text('button', order.delivery ? 'Delivery confirmed' : 'Delivery Received');
      button.type = 'button'; button.dataset.deliveryOrder = order.order_id; button.className = 'button'; button.disabled = !!order.delivery || busy;
      button.addEventListener('click', () => act(async () => {
        const result = await request('/api/demo-pairing/delivery', {order_id: order.order_id});
        await refresh();
        show(result.notification.push_service_accepted ? 'Demo delivery recorded. The return alert was accepted for the ordering phone; device display is not confirmed.' : 'Demo delivery recorded. Its return notification is unconfirmed. No automatic resend will run.');
      }));
      card.append(list, text('p', 'Demo confirmation only. No stock changes or actual delivery transaction.'), button); inbox.append(card);
    });
    const requested = new URLSearchParams(window.location.search).get('order');
    if (requested !== null) {
      const target = /^demo-[a-f0-9]{12}$/.test(requested) ? get('paired-' + requested) : null;
      if (target) {target.tabIndex = -1; target.focus(); target.scrollIntoView();}
      else show('This notification’s exact order is unavailable. No substitute order was selected.', true);
    }
  }
  async function refresh(ticket = generation) {
    const result = await request('/api/demo-pairing/status');
    if (ticket !== generation || !get('pair-status')) return result;
    state = result; window.pairingState = result;
    const lastDelivered = [...result.orders].reverse().find(order => order.delivery);
    show(!result.configured ? messages.DEMO_SHARED_STORE_NOT_CONFIGURED : !result.role ?
      'For two phones, create a pairing on the ordering phone and join with its code on the receiving phone. Enable notifications on both.' :
      `${result.role === 'orderer' ? 'Ordering phone' : 'Receiving / manufacturer demo phone'} · ${result.paired ? 'Paired' : 'Waiting for the second phone'} · Notifications: ordering ${result.notifications.orderer ? 'on' : 'off'}, receiving ${result.notifications.manufacturer ? 'on' : 'off'}.` +
      (result.role === 'orderer' && lastDelivered ? ` Delivery received for ${lastDelivered.order_id} (demo).` : ''));
    draw(); return result;
  }
  async function act(operation) {
    if (busy) return; busy = true; controls();
    try {await operation();} catch (error) {failure(error);}
    finally {busy = false; controls();}
  }
  function invite(code) {get('pair-invite-code').value = code; get('pair-invite').hidden = false;}
  function clearFieldError() {
    get('pair-code').setAttribute('aria-invalid', 'false'); get('pair-code-error').hidden = true; get('pair-errors').hidden = true;
  }
  window.refreshPairingStatus = refresh;
  window.registerPairedPush = async subscription => {
    await window.pairingReady;
    if (!window.pairingState?.role) return;
    await request('/api/demo-pairing/subscription', {subscription: subscription ? {endpoint: subscription.endpoint, keys: subscription.keys} : null});
    await refresh();
  };
  window.bindPairedDemo = () => {
    if (!get('pair-create')) return;
    const ticket = ++generation; state = null; busy = false; controls();
    window.pairingReady = refresh(ticket).catch(error => {failure(error); controls(); return null;});
    get('pair-create').addEventListener('click', () => act(async () => {
      const result = await request('/api/demo-pairing/create'); invite(result.code);
      window.pairingReady = refresh(); await window.pairingReady; await window.refreshPairedPush?.();
      ['closing-workspace', 'closing-report'].forEach(id => {if (get(id)) get(id).hidden = true;});
    }));
    get('pair-join-form').addEventListener('submit', event => {
      event.preventDefault(); const code = get('pair-code').value.trim();
      if (!/^[A-Za-z0-9_-]{24}$/.test(code)) {
        get('pair-code').setAttribute('aria-invalid', 'true'); get('pair-code-error').hidden = false;
        const summary = get('pair-errors'); summary.replaceChildren(text('strong', 'Check the pairing code'));
        const link = text('a', 'Paste the complete 24-character code from the ordering phone.'); link.href = '#pair-code';
        link.addEventListener('click', e => {e.preventDefault(); get('pair-code').focus();}); summary.append(link); summary.hidden = false; summary.focus(); return;
      }
      clearFieldError(); act(async () => {
        await request('/api/demo-pairing/join', {code}); get('pair-code').value = '';
        window.pairingReady = refresh(); await window.pairingReady; await window.refreshPairedPush?.();
      });
    });
    get('pair-code').addEventListener('input', () => {if (/^[A-Za-z0-9_-]{24}$/.test(get('pair-code').value.trim())) clearFieldError();});
    get('pair-renew').addEventListener('click', () => act(async () => {const result = await request('/api/demo-pairing/invite'); invite(result.code); show('New pairing code ready. The previous code no longer works.');}));
    get('pair-copy').addEventListener('click', () => act(async () => {
      let timer;
      try {
        await Promise.race([navigator.clipboard.writeText(get('pair-invite-code').value), new Promise((_, reject) => {timer = setTimeout(() => reject(Error()), 20000);})]);
        show('Pairing code copied. Share it only with your second demo phone.');
      } catch (_) {show('Copy was not confirmed. Select the code and copy it manually; the pairing is unchanged.', true);}
      finally {clearTimeout(timer);}
    }));
    get('pair-refresh').addEventListener('click', () => act(() => refresh()));
    get('pair-end').addEventListener('click', () => act(async () => {await request('/api/demo-pairing/leave'); window.location.reload();}));
    navigator.serviceWorker?.addEventListener('message', event => {if (event.data?.type === 'pharmacy-demo-updated') void refresh(ticket).catch(failure);});
  };
})();
