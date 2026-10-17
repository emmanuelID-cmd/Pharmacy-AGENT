/* Human-only closing demo. Source text is rendered with textContent, never HTML. */
(() => {
  'use strict';
  let report = null, order = null, submission = null, busy = false;
  let history = [], newDraft = false, orderLimit = 20;
  const lines = new Map();
  const get = id => document.getElementById(id);
  const node = (tag, text, css) => {
    const result = document.createElement(tag);
    if (text !== undefined) result.textContent = String(text);
    if (css) result.className = css;
    return result;
  };
  const status = (id, text, error = false) => {
    const target = get(id); if (!target) return;
    target.hidden = !text; target.textContent = text;
    target.classList.toggle('is-error', error);
  };
  async function post(path, body) {
    const controller = new AbortController(); let timer;
    try {
      return await Promise.race([(async () => {
        const response = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), signal: controller.signal});
        window.handleAuthRequired?.(response);
        const result = await response.json();
        if (!response.ok) {const error = Error('REQUEST_FAILED'); error.code = result.reason_code === 'DEMO_BOTH_PHONES_NOT_READY' ? 'DEMO_BOTH_PHONES_NOT_READY' : ''; throw error;}
        return result;
      })(), new Promise((_, reject) => {
        timer = setTimeout(() => {controller.abort(); reject(Error('REQUEST_TIMED_OUT'));}, 20000);
      })]);
    } finally {clearTimeout(timer);}
  }
  function errors(id, entries, focus = true) {
    const target = get(id); target.replaceChildren(); target.hidden = !entries.length;
    if (!entries.length) return;
    target.append(node('strong', 'Check your order'));
    const list = node('ul');
    entries.forEach(([field, message]) => {
      const item = node('li'), link = node('a', message); link.href = '#' + field;
      link.addEventListener('click', event => {event.preventDefault(); get(field)?.focus();});
      item.append(link); list.append(item);
    });
    target.append(list); if (focus) target.focus();
  }
  function drawReport() {
    const target = get('closing-report'); if (!target || !report) return;
    target.replaceChildren(node('h3', 'Closing inventory report · Before order'));
    const meta = node('dl', undefined, 'report-meta-grid');
    [['Stock as of', report.snapshot_timestamp], ['Snapshot reference', report.snapshot_reference],
      ['Example closing clock', report.demo_clock], ['Report created', report.created_at],
      ['Coverage', `${report.rows.length} synthetic items`], ['Inventory validation', report.report_state]].forEach(([key, value]) => {
      const part = node('div'); part.append(node('dt', key), node('dd', value)); meta.append(part);
    });
    const counts = report.rows.reduce((all, row) => {all[row.local_class] = (all[row.local_class] || 0) + 1; return all;}, {});
    target.append(meta, node('p', Object.entries(counts).map(([key, count]) => `${key}: ${count}`).join(' · ')),
      node('p', report.movement_summary + ' FDA context is not requested in this closing demo.', 'small muted'),
      node('p', 'This report stays fixed at its original stock snapshot. Drafting or submitting an order does not change stock or create another report.', 'notice notice-info'));
    const details = node('details', undefined, 'closing-stock');
    details.append(node('summary', 'Inspect all 150 pre-order stock rows'));
    const wrap = node('div', undefined, 'table-wrap closing-stock-scroll');
    wrap.tabIndex = 0; wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', 'Closing stock snapshot');
    const table = node('table', undefined, 'report-table'), head = node('thead'), tr = node('tr'), body = node('tbody');
    ['Item', 'Package NDC', 'On hand', 'Days of supply', 'Status', 'Evidence'].forEach(label => {const cell = node('th', label); cell.scope = 'col'; tr.append(cell);});
    head.append(tr);
    report.rows.forEach(row => {
      const line = node('tr');
      [row.label, row.package_ndc, row.usable_quantity === null ? 'Unknown' : `${row.usable_quantity} ${row.unit}`,
        row.days_of_supply || 'Unknown', row.local_class, row.reason_codes.length ? row.reason_codes.join(', ') : row.evidence_reference].forEach(value => line.append(node('td', value)));
      body.append(line);
    });
    table.append(head, body); wrap.append(table); details.append(wrap); target.append(details); target.hidden = false;
  }
  function filterItems() {
    if (!report || !get('order-item')) return;
    const select = get('order-item'), previous = select.value, query = get('order-search').value.trim().toLocaleLowerCase();
    const matches = report.rows.filter(row => `${row.label} ${row.item_id} ${row.package_ndc}`.toLocaleLowerCase().includes(query));
    select.replaceChildren(new Option(matches.length ? `Choose an item (${matches.length} matching)` : 'No matching catalog items', ''));
    matches.forEach(row => select.append(new Option(`${row.label} · ${row.package_ndc} · ${row.local_class}`, row.item_id)));
    if (matches.some(row => row.item_id === previous)) select.value = previous;
  }
  function drawLines() {
    if (!report || !get('order-list')) return;
    const target = get('order-list'); target.replaceChildren(); get('order-empty').hidden = !!lines.size;
    lines.forEach((line, id) => {
      const row = report.rows.find(item => item.item_id === id), supported = row.suggestion.suggested_quantity !== null;
      const card = node('article', undefined, 'order-line');
      card.append(node('h4', row.label), node('p', `${row.package_ndc} · ${row.local_class} · ${row.days_of_supply || 'Unknown'} days of supply`, 'small muted'));
      const label = node('label', `Order quantity (${row.unit || 'unknown unit'})`); label.htmlFor = 'qty-' + id;
      const input = node('input'); input.type = 'number'; input.id = label.htmlFor; input.min = '1'; input.max = '1000000'; input.step = '1';
      input.value = line.quantity; input.disabled = !!order || busy;
      input.setAttribute('aria-describedby', `qty-help-${id} qty-error-${id}`); input.setAttribute('aria-invalid', line.error ? 'true' : 'false');
      input.addEventListener('input', () => {
        line.quantity = input.value;
        const value = Number(input.value);
        if (supported && input.value.trim() && Number.isSafeInteger(value) && value >= 1 && value <= 1000000) {
          line.error = ''; input.setAttribute('aria-invalid', 'false'); get('qty-error-' + id).hidden = true;
          const summary = get('order-errors'); summary.querySelector(`a[href="#qty-${id}"]`)?.closest('li').remove();
          summary.hidden = !summary.querySelector('li');
        }
      });
      const help = node('p', supported ? `Suggested: ${row.suggestion.suggested_quantity} ${row.unit}. Human edits are recorded separately.` : 'Quantity withheld for manual review. Remove this item before submitting.', 'field-help'); help.id = 'qty-help-' + id;
      const error = node('p', line.error || '', 'field-error'); error.id = 'qty-error-' + id; error.hidden = !line.error;
      const evidence = node('details'); evidence.append(node('summary', 'Suggestion policy and evidence'));
      evidence.append(node('p', supported ? `${row.suggestion.policy_version}: target ${row.suggestion.target_days} days; target ${row.suggestion.target_units} units; confirmed incoming ${row.suggestion.confirmed_incoming}; multiple ${row.suggestion.order_multiple}; minimum ${row.suggestion.minimum_units}. ${row.suggestion.calculation}. Evidence: ${row.evidence_reference}.` : row.reason_codes.join(', ') || row.suggestion.reason_code, 'small muted'));
      const remove = node('button', 'Remove item', 'button button-text'); remove.type = 'button'; remove.disabled = !!order || busy; remove.setAttribute('aria-label', `Remove ${row.label}`);
      remove.addEventListener('click', () => {
        lines.delete(id); drawLines();
        errors('order-errors', Array.from(lines).filter(([, entry]) => entry.error).map(([key, entry]) => ['qty-' + key, entry.error]), false);
        get('order-item').focus();
      });
      card.append(label, input, help, error, evidence, remove); target.append(card);
    });
  }
  function orderControls() {
    const locked = !!order || busy;
    ['order-search', 'order-item', 'submit-demo-order', 'clear-demo-order'].forEach(id => {get(id).disabled = locked;});
    get('order-add-form').querySelector('button').disabled = locked;
    get('new-demo-order').hidden = !history.length;
    get('new-demo-order').disabled = busy || !order || history.length >= orderLimit;
    get('submit-demo-order').textContent = order ? 'Order submitted' : busy ? 'Submitting…' : 'Submit demo order';
  }
  function drawHistory() {
    const target = get('order-history'); target.replaceChildren();
    if (!history.length) return;
    const details = node('details'), list = node('ol');
    details.append(node('summary', `${history.length} submitted demo order(s) · Limit ${orderLimit}`));
    [...history].reverse().forEach(previous => {
      const entry = node('li');
      entry.append(node('strong', previous.order_id), node('p', `${previous.submitted_at} · ${previous.state}`));
      previous.lines.forEach(line => entry.append(node('p', `${line.local_class} · ${line.label} · ${line.quantity} ${line.unit}`)));
      list.append(entry);
    });
    details.append(list); target.append(details);
    if (history.length >= orderLimit) target.append(node('p', `This demo worker has reached its ${orderLimit}-order limit. Earlier orders and the report are preserved.`, 'notice notice-warn'));
  }
  function drawOrder() {
    if (!order || !get('order-result')) return;
    lines.clear();
    order.lines.forEach(line => lines.set(line.item_id, {quantity: String(line.quantity), error: ''}));
    const target = get('order-result');
    target.replaceChildren(node('h3', 'Human-reviewed demo order'), node('p', `${order.order_id} · Revision ${order.revision} · ${order.state}`),
      node('p', 'Simulation only. No purchase order was placed and no inventory was changed. Optional phone notification status is shown above.', 'notice notice-warn'));
    const list = node('ol', undefined, 'warning-list');
    order.lines.forEach(line => list.append(node('li', `${line.local_class} · ${line.label} · ${line.quantity} ${line.unit}${line.human_edited ? ' · Human-edited quantity' : ''}`)));
    target.append(list);
    if (window.pairingState?.role) {
      target.append(node('p', 'Paired browser alerts go to the receiving demo phone. Delivery confirmation sends the return alert to the ordering phone. No SMS or purchase order is sent.', 'small muted'),
        node('h4', 'Morning-shift preview'), node('p', `Example next shift: ${order.manufacturer_notice.scheduled_for}. This remains a preview; the two-phone demo sends immediately after a human action.`));
    } else {
      target.append( node('h4', 'Test SMS preview'), node('p', order.test_sms.message),
      node('p', 'Provider and destination are not configured. Real-phone SMS is a separate integration step.', 'small muted'),
      node('h4', 'Manufacturer notice preview'), node('p', `One notice for this order, prioritized CRITICAL before LOW. Example next shift: ${order.manufacturer_notice.scheduled_for}. New York is a demo timezone assumption. No manufacturer is contacted.`));
    }
    if (order.delivery) target.append(node('p', `Delivery received (demo): ${order.delivery.confirmed_at}. The frozen inventory report is unchanged.`, 'notice notice-info'));
    target.hidden = false;
    orderControls(); drawLines();
  }
  window.bindClosingDemo = () => {
    const button = get('close-day'); if (!button) return;
    let linkedOrder = new URLSearchParams(window.location.search).get('order');
    window.bindPairedDemo?.();
    window.bindPushNotifications?.();
    const restore = () => {drawReport(); filterItems(); drawLines(); drawHistory(); orderControls(); get('closing-workspace').hidden = false; button.textContent = 'View same closing report'; get('order-result').hidden = !order; drawOrder();};
    if (report) restore();
    button.addEventListener('click', async () => {
      button.disabled = true; status('closing-status', 'Capturing the fixed synthetic closing snapshot…');
      try {
        const result = await post('/api/closing-demo/close', {});
        const sameClosing = report?.closing_id === result.closing.closing_id;
        if (!sameClosing) {lines.clear(); submission = null; order = null; newDraft = false;}
        report = result.closing; history = result.orders; orderLimit = result.order_limit;
        if (linkedOrder !== null) {
          order = /^demo-[a-f0-9]{12}$/.test(linkedOrder) && linkedOrder.length === 17 ?
            history.find(previous => previous.order_id === linkedOrder) || null : null;
          newDraft = false;
        } else if (!newDraft) order = result.order;
        if (!get('close-day')) return;
        restore(); status('closing-status', 'One pre-order report is ready. Select items below; the stock snapshot stays fixed.');
        if (linkedOrder !== null) {
          if (order) {
            const target = get('order-result'); target.tabIndex = -1; target.focus(); target.scrollIntoView();
            status('order-status', 'Opened the submitted order from your notification.');
          } else {
            status('order-status', 'This notification’s order is unavailable in this demo worker. It may have restarted or changed. No other order has been opened. View submitted-order history or start a fresh demo.', true);
          }
        }
      } catch (_) {status('closing-status', 'The closing source could not be verified. No complete report is available. Correct the source and retry.', true);}
      finally {button.disabled = false;}
    });
    get('new-demo-order').addEventListener('click', () => {
      if (busy || !order || history.length >= orderLimit) return;
      linkedOrder = null;
      if (window.location.search) window.history.replaceState(window.history.state, '', '/demo#closing-title');
      order = null; submission = null; newDraft = true; lines.clear();
      get('order-search').value = ''; get('order-result').hidden = true;
      errors('order-errors', [], false); errors('order-add-errors', [], false);
      get('order-item-error').hidden = true; get('order-item').setAttribute('aria-invalid', 'false');
      restore(); get('order-search').focus();
      status('order-status', 'New demo order started. Select items below. The same closing report and earlier orders are preserved.');
    });
    get('order-search').addEventListener('input', filterItems);
    get('order-item').addEventListener('change', () => {
      if (get('order-item').value) {get('order-item').setAttribute('aria-invalid', 'false'); get('order-item-error').hidden = true; errors('order-add-errors', [], false);}
    });
    get('order-add-form').addEventListener('submit', event => {
      event.preventDefault(); if (order || busy) return;
      const select = get('order-item'), row = report?.rows.find(item => item.item_id === select.value);
      if (!row) {
        select.setAttribute('aria-invalid', 'true'); get('order-item-error').textContent = 'Choose a catalog item to add.'; get('order-item-error').hidden = false;
        errors('order-add-errors', [['order-item', 'Choose a catalog item to add.']]); return;
      }
      if (!lines.has(row.item_id)) lines.set(row.item_id, {quantity: row.suggestion.suggested_quantity === null ? '' : String(row.suggestion.suggested_quantity), error: ''});
      drawLines();
      get('order-errors').querySelector('a[href="#order-item"]')?.closest('li').remove();
      get('order-errors').hidden = !get('order-errors').querySelector('li');
      get('qty-' + row.item_id).focus(); status('order-status', 'Item is in your order list. Selecting it again preserves the existing line and your edits.');
    });
    get('clear-demo-order').addEventListener('click', () => {
      if (order || busy) return;
      lines.clear(); drawLines(); errors('order-errors', [], false); status('order-status', 'Order list rejected and cleared. Nothing was submitted or sent.');
    });
    get('demo-order-form').addEventListener('submit', async event => {
      event.preventDefault(); if (order || busy) return;
      const invalid = [];
      if (!lines.size) invalid.push(['order-item', 'Add at least one catalog item before submitting.']);
      lines.forEach((line, id) => {
        const row = report.rows.find(item => item.item_id === id), value = Number(line.quantity);
        line.error = row.suggestion.suggested_quantity === null ? 'Required evidence needs manual review. Remove this item before submitting.' :
          !line.quantity.trim() || !Number.isSafeInteger(value) || value < 1 || value > 1000000 ? 'Enter 1–1,000,000 whole dispensing units, or remove this item.' : '';
        if (line.error) invalid.push(['qty-' + id, line.error]);
      });
      drawLines(); errors('order-errors', invalid); if (invalid.length) return;
      busy = true; orderControls(); drawLines(); submission ||= crypto.randomUUID();
      const selected = Array.from(lines, ([item_id, line]) => ({item_id, quantity: Number(line.quantity)}));
      status('order-status', 'Recording your human-reviewed demo submission…');
      let recorded = null;
      try {
        order = await post('/api/closing-demo/submit', {closing_id: report.closing_id, submission_id: submission, lines: selected});
        newDraft = false;
        if (!history.some(previous => previous.order_id === order.order_id)) history.push(order);
        if (get('order-history')) drawHistory();
        if (get('order-result')) {drawOrder(); status('order-status', 'Order recorded. Use New demo order for another submission. The inventory report is unchanged; phone notification status is shown here separately.');}
        recorded = order;
      } catch (error) {status('order-status', error.code === 'DEMO_BOTH_PHONES_NOT_READY' ? 'Pair both phones and enable notifications on each before submitting. Your list is preserved.' : 'Submission was not confirmed. Your list is preserved. Use “View same closing report” to recover any existing submission before retrying.', true);}
      finally {busy = false; if (get('submit-demo-order')) {orderControls(); drawLines();}}
      if (recorded) {
        try {await window.notifyDemoOrder?.(recorded);}
        catch (_) {status('order-notification-status', 'Order recorded, but notification status is unavailable. No automatic retry will run. Reference: PUSH_CLIENT_ERROR.', true);}
      }
    });
    if (linkedOrder !== null) {
      if (window.pairingReady) window.pairingReady.then(() => {if (window.pairingState?.role !== "manufacturer") button.click();});
      else button.click();
    }
  };
})();
