(() => {
  'use strict';

  const paths = {
    home: '/', agent: '/agent', tools: '/tools', harness: '/harness',
    'injection-risk-test': '/injection-risk-test', 'failure-state': '/failure-state',
    demo: '/demo', architecture: '/architecture'
  };
  const warningText = {
    EXTERNAL_FIELD_EXCEPTION: 'Some source fields were excluded or flagged by the safety checks. Review the source data.',
    MANUAL_REVIEW_REQUIRED: 'One or more items need manual review before any decision.',
    EXTERNAL_CONTEXT_UNVERIFIED: 'National shortage status could not be checked. Verify current context before relying on a local classification.',
    OUTPUT_REJECTED: 'The proposed report did not match verified facts. Only verified facts are shown; manual review is required.'
  };
  const safeErrors = {
    INVALID_REQUEST: 'Enter a request with 1–1,000 non-whitespace characters.',
    INVALID_FORM_INPUT: 'Review the request fields and correct any missing or invalid value.',
    REQUEST_REQUIRES_REVIEW: 'This request needs manual review. Use the supported inventory review request and try again.',
    PROVIDER_NOT_CONFIGURED: 'The server-side model provider is not configured. A maintainer must configure it before a live review can run.',
    PROVIDER_AUTHENTICATION_FAILED: 'The model provider rejected its server-side credentials. A maintainer must update the server configuration.',
    MODEL_NOT_AVAILABLE: 'The selected model is unavailable. A maintainer must choose an available configured model.',
    PROVIDER_RATE_LIMITED: 'The model provider is temporarily rate limiting requests. Wait briefly, then retry.',
    MODEL_TIMEOUT: 'The model did not respond within its time limit. Your request is preserved; retry later.',
    RUN_DEADLINE_EXCEEDED: 'The review reached its bounded run deadline. Your request is preserved; retry later.',
    REVIEW_RATE_LIMITED: 'A review was just run. Wait 10 seconds before starting another review.',
    REVIEW_ALREADY_RUNNING: 'A review is already running. Wait for it to finish or stop waiting before starting another.',
    PROVIDER_UNAVAILABLE: 'The review service is temporarily unavailable. Your request is preserved; retry when it is available.',
    REVIEW_TIMEOUT: 'The review reached its time limit. Your request is preserved; retry the review.',
    INVENTORY_UNAVAILABLE: 'Inventory could not be verified. No complete review is available.',
    REPORT_REJECTED: 'The report did not pass verification. The result requires manual review.',
    TEST_UNAVAILABLE: 'The synthetic test is temporarily unavailable. Try again when the service is available.',
    DEMO_UNAVAILABLE: 'The fixed demo could not be completed. Try again when the service is available.',
    STATUS_UNAVAILABLE: 'Service status is temporarily unavailable.'
  };

  let agentDraft = '';
  let agentNotice = '';
  let reviewController = null;
  let navigationBusy = false;

  const byId = (id, root = document) => root.getElementById(id);
  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  };
  const displayText = value => (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') ? String(value) : 'Unavailable';
  const setStatus = (node, message, mode = 'info') => {
    if (!node) return;
    node.hidden = !message;
    node.textContent = message || '';
    node.classList.toggle('is-error', mode === 'error');
    node.classList.toggle('is-loading', mode === 'loading');
  };
  const requestJson = async (url, payload, signal) => {
    const options = { method: payload === undefined ? 'GET' : 'POST', headers: { Accept: 'application/json' }, signal };
    if (payload !== undefined) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(payload);
    }
    const response = await fetch(url, options);
    window.handleAuthRequired?.(response);
    let body;
    try { body = await response.json(); } catch (_) { throw new Error('SAFE_RESPONSE'); }
    if (!response.ok) {
      const error = new Error('SAFE_RESPONSE');
      error.reasonCode = typeof body?.reason_code === 'string' ? body.reason_code : '';
      throw error;
    }
    return body;
  };
  const safeMessage = (error, fallback) => {
    if (error?.name === 'AbortError') return 'The browser stopped waiting. The server may still finish its bounded reads; your request is preserved.';
    if (typeof navigator !== 'undefined' && navigator.onLine === false) return 'No Internet Access. Reconnect, then retry; your draft is preserved.';
    return safeErrors[error?.reasonCode] || fallback;
  };

  function updateClock() {
    const clock = byId('current-clock');
    if (!clock) return;
    const now = new Date();
    clock.dateTime = now.toISOString();
    clock.textContent = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', second: '2-digit', timeZoneName: 'short' }).format(now);
  }

  function navigate(url, { replace = false } = {}) {
    const target = new URL(url, window.location.href);
    if (target.origin !== window.location.origin || !Object.values(paths).includes(target.pathname) || navigationBusy) return;
    const request = byId('review-request');
    if (request) agentDraft = request.value;
    if (reviewController) {
      const activeController = reviewController;
      reviewController = null;
      agentNotice = 'Browser wait stopped when navigation started. Server reads may finish within their own bounded limits; your draft is preserved.';
      activeController.abort();
    }
    navigationBusy = true;
    const routeStatus = byId('navigation-status');
    const navigationNotice = agentNotice;
    setStatus(routeStatus, navigationNotice || 'Opening page…', navigationNotice ? 'info' : 'loading');
    fetch(target.pathname, { headers: { Accept: 'text/html' } })
      .then(response => {
        if (response.redirected && new URL(response.url).pathname === '/login') {window.location.assign(response.url); throw Error('AUTH_SIGN_IN_REQUIRED');} if (!response.ok) throw new Error('ROUTE_UNAVAILABLE'); return response.text(); })
      .then(html => {
        const nextDocument = new DOMParser().parseFromString(html, 'text/html');
        const nextMain = nextDocument.getElementById('main-content');
        const currentMain = byId('main-content');
        if (!nextMain || !currentMain) throw new Error('ROUTE_UNAVAILABLE');
        currentMain.replaceWith(nextMain);
        document.title = nextDocument.title || 'Pharmacy-AGENT';
        document.querySelectorAll('.nav-link').forEach(link => {
          const active = new URL(link.href).pathname === target.pathname;
          link.classList.toggle('is-active', active);
          if (active) link.setAttribute('aria-current', 'page');
          else link.removeAttribute('aria-current');
        });
        if (replace) {
          history.replaceState({ pharmacy: true }, '', target.pathname);
        } else {
          history.pushState({ pharmacy: true }, '', target.pathname);
        }
        setStatus(routeStatus, navigationNotice, 'info');
        bindPage();
        const heading = byId('page-title');
        if (heading) heading.focus({ preventScroll: true });
        else byId('main-content')?.focus({ preventScroll: true });
        window.scrollTo({ top: 0, behavior: 'auto' });
      })
      .catch(() => {
        if (agentNotice) {
          setStatus(byId('review-status'), agentNotice);
          agentNotice = '';
        }
        setStatus(routeStatus, 'That page could not be loaded. Your current page and draft are still here; retry the link.', 'error');
      })
      .finally(() => { navigationBusy = false; });
  }

  function bindNavigation() {
    document.addEventListener('click', event => {
      const link = event.target.closest('a[data-route]');
      if (link && !event.defaultPrevented && event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
        event.preventDefault();
        navigate(link.href);
        return;
      }
    });
    document.querySelector('.primary-nav')?.addEventListener('keydown', event => {
      if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
      const links = Array.from(event.currentTarget.querySelectorAll('.nav-link'));
      const index = links.indexOf(document.activeElement);
      if (index < 0 || !links.length) return;
      event.preventDefault();
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? links.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : links.length - 1)) % links.length;
      links[next].focus();
    });
    window.addEventListener('popstate', () => {
      const path = window.location.pathname;
      navigate(path, { replace: true });
    });
  }

  function renderReport(container, report, { demo = false } = {}) {
    container.replaceChildren();
    if (!report || !Array.isArray(report.items)) {
      container.append(make('p', 'notice notice-error', 'No verified report is available. Manual review is required.'));
      container.hidden = false;
      return;
    }
    const state = displayText(report.run_state || 'MANUAL_REVIEW').replaceAll('_', ' ');
    container.append(make('h2', 'result-heading', demo ? 'Fixed synthetic demo report' : `Review result · ${state}`));
    container.append(make('p', 'result-meta', `${demo ? 'Frozen example clock: October 7, 2026' : 'Current-clock review'} · Store ${displayText(report.store_id)} · ${displayText(report.data_mode)} · ${report.items.length} rows`));
    const metadata = make('dl', 'report-meta-grid');
    const addMetadata = (label, value) => {
      const field = make('div');
      field.append(make('dt', '', label), make('dd', '', displayText(value)));
      metadata.append(field);
    };
    addMetadata('Run time', report.run_at);
    addMetadata('Inventory snapshot', report.snapshot_timestamp);
    addMetadata('Policy version', report.policy_version);
    addMetadata('Usage window', report.usage_window ? `${displayText(report.usage_window.start)} to ${displayText(report.usage_window.end)}` : 'Unavailable');
    container.append(metadata);
    const wrap = make('div', 'table-wrap');
    const table = make('table', 'report-table');
    const head = make('thead');
    const headerRow = make('tr');
    ['Item', 'Days of supply', 'Local class', 'Action', 'FDA state', 'Item evidence'].forEach(label => headerRow.append(make('th', '', label)));
    head.append(headerRow);
    const body = make('tbody');
    report.items.forEach(row => {
      const tr = make('tr');
      const reasons = Array.isArray(row.reason_codes) ? row.reason_codes : Array.isArray(row.exceptions) ? row.exceptions.map(item => item?.reason_code).filter(Boolean) : [];
      const action = row.local_action ?? row.action;
      const values = [
        row.item_reference ?? row.item_id,
        row.days_of_supply_display ?? (row.days_of_supply == null ? 'Unavailable' : row.days_of_supply),
        row.local_class,
        action,
        row.fda_state ?? report.external_context?.state ?? 'Not verified',
        reasons.length ? reasons.join(', ') : (row.review_permitted === false || action === 'MANUAL_REVIEW' ? 'Manual review required' : 'Expand for details')
      ];
      values.forEach(value => tr.append(make('td', '', displayText(value))));
      body.append(tr);
      const evidenceRow = make('tr', 'report-detail-row');
      const evidenceCell = make('td');
      evidenceCell.colSpan = 6;
      const details = make('details');
      details.append(make('summary', '', `Evidence for ${displayText(row.item_id ?? row.item_reference)}`));
      const evidence = make('dl', 'evidence-grid');
      const addEvidence = (label, value) => {
        const field = make('div');
        field.append(make('dt', '', label), make('dd', '', displayText(value)));
        evidence.append(field);
      };
      addEvidence('Package NDC', row.package_ndc);
      addEvidence('Usable stock', row.usable_quantity);
      addEvidence('Dispensing unit', row.dispensing_unit);
      addEvidence('Average daily usage', row.average_daily_usage);
      addEvidence('FDA status', row.fda_status);
      addEvidence('FDA availability', row.fda_availability);
      addEvidence('FDA update date', row.fda_update_date);
      addEvidence('Reason codes', reasons.length ? reasons.join(', ') : 'None reported');
      addEvidence('Explanation', row.explanation);
      details.append(evidence);
      evidenceCell.append(details);
      evidenceRow.append(evidenceCell);
      body.append(evidenceRow);
    });
    table.append(head, body);
    wrap.append(table);
    container.append(wrap);
    const codes = Array.isArray(report.warning_codes) ? report.warning_codes : [];
    const warnings = make('ul', 'warning-list');
    codes.forEach(code => warnings.append(make('li', '', warningText[code] || 'Unrecognized warning. Treat this run as requiring manual review.')));
    if (!codes.length) warnings.append(make('li', '', report.external_context?.state === 'VERIFIED' ? 'External context verified for this report.' : 'FDA context is not verified; confirm it before relying on the local review.'));
    container.append(make('h3', '', 'Warnings and evidence limits'), warnings);
    container.append(make('p', 'notice notice-warn', 'Human review required. No order was placed and inventory was not changed.'));
    container.hidden = false;
  }

  function renderTesterResult(container, result) {
    container.replaceChildren();
    container.append(make('h2', 'result-heading', 'Synthetic test result'));
    container.append(make('p', 'result-meta', 'Fixed synthetic data · no live model, inventory, FDA request, SQL, shell, order, or inventory write'));
    const summary = make('dl', 'tester-summary');
    const addPair = (label, value) => { summary.append(make('dt', '', label), make('dd', '', displayText(value))); };
    addPair('Detector decision', result.detector?.decision || 'Unavailable');
    addPair('Source contract', result.detector?.source_contract_valid === true ? 'Valid' : 'Rejected or unavailable');
    addPair('Permission guard', result.permission_guard?.state || 'Unavailable');
    addPair('Authorized simulated reads', Array.isArray(result.simulated_executor_calls) ? result.simulated_executor_calls.length : 0);
    addPair('Operational write effects', displayText(result.simulated_operational_write_effects ?? 'Unavailable'));
    addPair('Output guard', result.output_guard?.accepted === true ? 'Accepted verified report' : 'Rejected changed report; safe report returned');
    container.append(summary);
    const limitations = Array.isArray(result.limitations) ? result.limitations : [];
    if (limitations.length) {
      container.append(make('h3', '', 'Limits of this test'));
      const list = make('ul', 'warning-list');
      limitations.forEach(item => list.append(make('li', '', displayText(item))));
      container.append(list);
    }
    container.hidden = false;
  }

  async function bindReview() {
    const form = byId('review-form');
    const input = byId('review-request');
    if (!form || !input) return;
    const count = byId('request-counter');
    const fieldError = byId('request-error');
    const summary = byId('review-errors');
    const summaryLink = byId('review-error-link');
    const run = byId('run-review');
    const stop = byId('stop-review');
    const retry = byId('retry-review');
    const status = byId('review-status');
    const result = byId('review-result');
    input.value = agentDraft;
    if (agentNotice) {
      setStatus(status, agentNotice);
      agentNotice = '';
    }
    const updateCount = () => { count.textContent = `${Array.from(input.value).length.toLocaleString()} / 1,000`; agentDraft = input.value; };
    const validationMessage = () => {
      const length = Array.from(input.value).length;
      if (!input.value.trim()) return 'Enter an inventory review request.';
      if (length > 1000) return 'Your request exceeds 1,000 Unicode characters. Shorten it to continue; the draft is preserved.';
      return '';
    };
    const updateError = message => {
      fieldError.textContent = message;
      summaryLink.textContent = message;
      fieldError.hidden = false;
      summary.hidden = false;
      input.setAttribute('aria-invalid', 'true');
    };
    const clearError = () => {
      fieldError.hidden = true;
      fieldError.textContent = '';
      input.setAttribute('aria-invalid', 'false');
      summary.hidden = true;
    };
    input.addEventListener('input', () => {
      updateCount();
      if (!fieldError.hidden) {
        const message = validationMessage();
        if (message) updateError(message);
        else clearError();
      }
    });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (reviewController) return;
      updateCount();
      const message = validationMessage();
      if (message) {
        updateError(message);
        summary.focus();
        return;
      }
      clearError();
      const controller = new AbortController();
      reviewController = controller;
      run.disabled = true;
      stop.disabled = false;
      retry.hidden = true;
      result.hidden = true;
      setStatus(status, 'Running the guarded inventory review…', 'loading');
      try {
        const envelope = await requestJson('/api/review', { request: input.value }, controller.signal);
        if (reviewController !== controller) return;
        reviewController = null;
        run.disabled = false;
        stop.disabled = true;
        if (envelope.report) {
          setStatus(status, `Review finished · ${displayText(envelope.state || 'Manual Review')}. The structured report is ready for human review.`);
          renderReport(result, envelope.report);
        } else {
          setStatus(status, safeErrors[envelope.reason_code] || 'No verified report is available. Manual review is required.', 'error');
          retry.hidden = false;
        }
      } catch (error) {
        if (reviewController !== controller) return;
        reviewController = null;
        run.disabled = false;
        stop.disabled = true;
        setStatus(status, safeMessage(error, 'The review service is temporarily unavailable. Your request is preserved; retry when it is available.'), error?.name === 'AbortError' ? 'info' : 'error');
        if (error?.name !== 'AbortError') retry.hidden = false;
      }
    });
    stop.addEventListener('click', () => { if (reviewController) reviewController.abort(); });
    retry.addEventListener('click', () => form.requestSubmit());
    updateCount();
    try {
      const statusData = await requestJson('/api/status');
      const provider = document.querySelector('.provider-status');
      if (provider) provider.textContent = statusData.provider_configured ? 'Configured' : 'Unavailable';
    } catch (_) { /* Keep the server-rendered safe configuration state. */ }
  }

  async function bindTester() {
    const form = byId('tester-form');
    if (!form) return;
    const sampleSelect = byId('test-sample');
    const requestInput = byId('test-request');
    const requestError = byId('test-request-error');
    const requestCounter = byId('test-request-counter');
    const status = byId('tester-status');
    const resultNode = byId('tester-result');
    const updateRequestCount = () => { requestCounter.textContent = `${Array.from(requestInput.value).length.toLocaleString()} / 1,000`; };
    requestInput.addEventListener('input', () => {
      updateRequestCount();
      if (Array.from(requestInput.value).length <= 1000) {
        requestError.hidden = true;
        requestInput.setAttribute('aria-invalid', 'false');
      }
    });
    try {
      const data = await requestJson('/api/test-samples');
      sampleSelect.replaceChildren();
      sampleSelect.append(new Option('Choose a synthetic sample', ''));
      (Array.isArray(data.samples) ? data.samples : []).forEach(sample => {
        if (!sample || typeof sample.id !== 'string' || typeof sample.name !== 'string') return;
        sampleSelect.append(new Option(sample.name, sample.id));
      });
    } catch (_) {
      sampleSelect.replaceChildren(new Option('Samples unavailable', ''));
      setStatus(status, 'Synthetic samples are temporarily unavailable. Retry when the service is available.', 'error');
    }
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (Array.from(requestInput.value).length > 1000) {
        requestError.textContent = 'Optional request text must be 1,000 Unicode characters or fewer. Shorten it to continue; your draft is preserved.';
        requestError.hidden = false;
        requestInput.setAttribute('aria-invalid', 'true');
        requestInput.focus();
        return;
      }
      requestError.hidden = true;
      requestInput.setAttribute('aria-invalid', 'false');
      if (!sampleSelect.value) {
        sampleSelect.setAttribute('aria-invalid', 'true');
        setStatus(status, 'Choose one synthetic sample before running the test.', 'error');
        sampleSelect.focus();
        return;
      }
      sampleSelect.setAttribute('aria-invalid', 'false');
      const button = form.querySelector('button[type="submit"]');
      button.disabled = true;
      setStatus(status, 'Running the synthetic tester…', 'loading');
      resultNode.hidden = true;
      const requestText = requestInput.value;
      const payload = { sample_id: sampleSelect.value, output_change: byId('output-change').value };
      if (requestText) payload.request_text = requestText;
      try {
        const data = await requestJson('/api/test-input', payload);
        renderTesterResult(resultNode, data);
        setStatus(status, 'Synthetic test complete. Review the boundary results and limitations below.');
      } catch (error) {
        setStatus(status, safeMessage(error, safeErrors.TEST_UNAVAILABLE), 'error');
      } finally { button.disabled = false; }
    });
    updateRequestCount();
  }

  async function bindDemo() {
    const button = byId('run-demo');
    if (!button) return;
    const status = byId('demo-status');
    const result = byId('demo-result');
    button.addEventListener('click', async () => {
      button.disabled = true;
      result.hidden = true;
      setStatus(status, 'Running the fixed demo…', 'loading');
      try {
        const data = await requestJson('/api/demo', {});
        if (!data.report) throw Object.assign(new Error('SAFE_RESPONSE'), { reasonCode: data.reason_code });
        renderReport(result, data.report, { demo: true });
        setStatus(status, 'Fixed demo complete. This result uses its declared example clock and simulated context.');
      } catch (error) { setStatus(status, safeMessage(error, safeErrors.DEMO_UNAVAILABLE), 'error'); }
      finally { button.disabled = false; }
    });
  }

  async function bindFailurePreview() {
    const button = byId('preview-failure');
    if (!button) return;
    button.addEventListener('click', async () => {
      const output = byId('failure-result');
      button.disabled = true;
      setStatus(output, 'Loading recovery guidance…', 'loading');
      try {
        const scenario = byId('failure-scenario').value;
        const data = await requestJson('/api/failure-preview', { scenario });
        const offlineExample = scenario === 'offline' && navigator.onLine !== false;
        const title = offlineExample ? 'Offline browser scenario (simulated)' : displayText(data.title);
        const detail = offlineExample ? 'This example represents an offline browser state. The browser currently reports an internet connection.' : displayText(data.detail);
        setStatus(output, '', 'info');
        output.replaceChildren(make('h2', '', title), make('p', '', detail), make('p', '', displayText(data.recovery)), make('p', 'small muted', data.simulated === true ? 'Simulated scenario · no live fault was triggered' : 'Preview result'));
        output.hidden = false;
      } catch (error) { setStatus(output, safeMessage(error, 'Recovery guidance is temporarily unavailable.'), 'error'); }
      finally { button.disabled = false; }
    });
  }

  function bindPage() {
    window.bindReviewerAuth?.();
    updateClock();
    bindReview();
    bindTester();
    bindDemo();
    bindFailurePreview();
    window.bindClosingDemo?.();
  }

  bindNavigation();
  bindPage();
  window.setInterval(updateClock, 1000);
})();
