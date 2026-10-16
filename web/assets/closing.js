/* Human-only closing demo. Source text is rendered with textContent, never HTML. */
(() => {
  'use strict';
  let report = null, order = null, submission = null, busy = false;
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
    const response = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    const result = await response.json();
    if (!response.ok) throw Error(result.reason_code || 'REQUEST_FAILED');
    return result;
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
      remove.addEventListener('click', () => {lines.delete(id); drawLines(); errors('order-errors', [], false); get('order-item').focus();});
      card.append(label, input, help, error, evidence, remove); target.append(card);
    });
  }
  function drawOrder() {
    if (!order || !get('order-result')) return;
    const target = get('order-result');
    target.replaceChildren(node('h3', 'Human-reviewed demo order'), node('p', `${order.order_id} · Revision ${order.revision} · ${order.state}`),
      node('p', 'Simulation only. No purchase order was placed, no inventory was changed, and no notification was sent.', 'notice notice-warn'));
    const list = node('ol', undefined, 'warning-list');
    order.lines.forEach(line => list.append(node('li', `${line.local_class} · ${line.label} · ${line.quantity} ${line.unit}${line.human_edited ? ' · Human-edited quantity' : ''}`)));
    target.append(list, node('h4', 'Test SMS preview'), node('p', order.test_sms.message),
      node('p', 'Provider and destination are not configured. Real-phone SMS is a separate integration step.', 'small muted'),
      node('h4', 'Manufacturer notice preview'), node('p', `One notice for this order, prioritized CRITICAL before LOW. Example next shift: ${order.manufacturer_notice.scheduled_for}. New York is a demo timezone assumption. No manufacturer is contacted.`));
    target.hidden = false;
    ['order-search', 'order-item', 'submit-demo-order', 'clear-demo-order'].forEach(id => {get(id).disabled = true;});
    get('order-add-form').querySelector('button').disabled = true; drawLines();
  }
  window.bindClosingDemo = () => {
    const button = get('close-day'); if (!button) return;
    const restore = () => {drawReport(); filterItems(); drawLines(); get('closing-workspace').hidden = false; button.textContent = 'View same closing report'; drawOrder();};
    if (report) restore();
    button.addEventListener('click', async () => {
      button.disabled = true; status('closing-status', 'Capturing the fixed synthetic closing snapshot…');
      try {
        const result = await post('/api/closing-demo/close', {});
        if (report && report.closing_id !== result.closing.closing_id) {lines.clear(); submission = null; order = null;}
        report = result.closing; order = result.order;
        if (!get('close-day')) return;
        restore(); status('closing-status', 'One pre-order report is ready. Select items below; the stock snapshot stays fixed.');
      } catch (_) {status('closing-status', 'The closing source could not be verified. No complete report is available. Correct the source and retry.', true);}
      finally {button.disabled = false;}
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
      busy = true; get('submit-demo-order').disabled = true; drawLines(); submission ||= crypto.randomUUID();
      const selected = Array.from(lines, ([item_id, line]) => ({item_id, quantity: Number(line.quantity)}));
      status('order-status', 'Recording your human-reviewed demo submission…');
      try {
        order = await post('/api/closing-demo/submit', {closing_id: report.closing_id, submission_id: submission, lines: selected});
        if (get('order-result')) {drawOrder(); status('order-status', 'Demo submission recorded. Notification previews are below; the inventory report is unchanged.');}
      } catch (_) {status('order-status', 'Submission was not confirmed. Your list is preserved. Use “View same closing report” to recover any existing submission before retrying.', true);}
      finally {busy = false; if (get('submit-demo-order')) {get('submit-demo-order').disabled = !!order; drawLines();}}
    });
  };
})();
