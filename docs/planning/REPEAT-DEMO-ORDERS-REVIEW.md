# Repeat demo orders - verification

Baseline: c28fc8dbf42c1589a4ac3ca20309585099ae6a18; feature/order-workflow-demo.

## Line Return Reference

- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\README.md`: current 129-133 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\architecture\Pharmacy-Web-Agent-Architecture.md`: current 162-177 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\planning\ANDROID-PUSH.md`: current 46-47 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\planning\ORDER-WORKFLOW-PLAN.md`: current 2-5 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\planning\REPEAT-DEMO-ORDERS.md`: current 1-79 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\requirements\POLICY.md`: prior 112 deleted/replaced; current 112 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\requirements\Pharmacy Inventory Logistics[PRD]-Mod.md`: prior 146 deleted/replaced; current 146 added; prior 164 deleted/replaced; current 164 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\src\pharmacy_web\closing.py`: current 23 added; current 44-45 added; prior 48 deleted/replaced; current 51-52 added; prior 55-56 deleted/replaced; current 59-61 added; prior 58-59 deleted/replaced; current 63-64 added; prior 62 deleted/replaced; current 67 added; prior 64-65 deleted/replaced; current 69-70 added; prior 132-133 deleted/replaced; current 137-138 added; prior 135 deleted/replaced; current 140-142 added; current 154-155 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\tests\browser\pharmacy_web_check.mjs`: current 172-192 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\tests\test_closing_demo.py`: current 105-129 added; current 179-191 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\tests\test_push_notifications.py`: current 66-76 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\web\assets\closing.js`: current 5 added; current 106-126 added; prior 118-119 deleted/replaced; current 140 added; prior 124 deleted/replaced; current 145 added; prior 130-131 deleted/replaced; current 151-154 added; current 159-167 added; current 206-208 added; prior 177 deleted/replaced; current 212 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\web\templates\page.html`: current 180-181 added; prior 199 deleted/replaced; current 201 added.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\planning\REPEAT-DEMO-ORDERS-REVIEW.md`: current 1-92 added; created review, all lines new.

## Secondary Checks

- Trailing whitespace: PASS
- Markdown fences: PASS


## BUILDER result

Implemented distinct per-intent demo orders against one report, bounded retained history, exact
per-order notification lookup, New demo order/form recovery and current requirements. No new
dependency, API route, model tool, database write, report reset, branch or PR. The original source
and plan remain recoverable from baseline Git; no secrets or production orders were changed.
An initial documentation patch failed on stale architecture context; no partial edits were applied,
and the correction used the actual file context. No scope expansion resulted.

## SECURITY scope and environment

Local Python 3.13, unittest synthetic fixtures, fake push transport and the loopback preview.
Existing reviewer authentication, origin/strict-JSON/body limits and read-only tool guards are
unchanged. Boundary: human draft -> validated order intent -> exact closing/item evidence ->
retained order -> per-order notification binding; no user text becomes model authority or HTML.
History is bounded at 20 orders and returned as copies; capacity never evicts old intents.

## SECURITY Round 1

27 affected closing/push tests passed, covering distinct orders, old idempotent retries, conflicting
intent content, copied history, unchanged snapshot/read count, capacity with old retries, independent
notification attempts and the existing host/key/auth/origin/Agent denials. Notification client
simulations and browser-script syntax passed. No security finding required remediation.

## SECURITY Round 2

Repeated the 27 affected tests, notification simulations, JavaScript syntax and diff checks after
Round 1. All passed. Read-only source review confirmed the existing lock serializes intent creation
and notification attempts; exact retained orders are found before sending, including older orders.
No real push network call, SMS, live data, production scan or secret access was performed.

Findings/leaks/alerts: no security findings or leaks observed within tested scope; no breach or
external security alert was generated. Residual limits: shared reviewer/worker-local prototype
records, lost state after restart, no cross-worker durability or notification delivery guarantee.
Verdict: SECURITY CLEAR WITHIN TESTED SCOPE.

## REVIEWER acceptance

- Second order after refresh without logout - MET. In the visible loopback browser, submitted
  demo-a2f2022a5b29 with quantity 3, refreshed, viewed the report, started New demo order and
  submitted demo-6f7f61f55cb5 with quantity 4. Both remained visible in history.
- One unchanged report - MET. Creation time remained 2026-10-16T10:33:07-04:00 through both orders;
  server tests independently assert exact snapshot equality and a single inventory read.
- Earlier orders and safe copies - MET in unit/API tests and expanded visible history.
- New draft sends nothing; each submitted order has its own attempt; old retries do not resend -
  MET with fake transport tests. Browser preview used unconfigured push so it could not send.
- Changed contents under one intent conflict; capacity rejects order 21 and retains old retries -
  MET in unit tests. Current server/client validation and visible 20-order limit remain intact.
- View same report preserves the new draft - MET in visible browser with quantity 4 before its
  second submission. Native narrow-preview layout displayed history and the New demo order button.
- Existing report/Agent authority - MET in tests and source diff. No model permission expanded.
- Notification text on Android - NOT TESTED in this correction. User must repeat on the deployed
  updated branch; no actual SMS exists. This unresolved observation was explicitly separated from
  the independently verified order-flow fix.

Regression: 304 unittest methods pass; qualification has 85 contained fixtures, 55 unsafe detected,
30 benign accepted, zero misses and zero false positives. Notification browser simulations pass.
The existing browser regression script now includes repeat-order assertions and passes syntax;
that full CDP script was not rerun in this follow-up. The actual refresh/new-order/second-submit
sequence was verified using the user-visible browser instead. No browser exception was displayed.

Line scan: every file and exact range above was inspected for the stated scope. The report's own
new lines were reviewed separately. No unresolved in-scope correctness or security findings.
Verdict: APPROVE for local preview; publication, deployment and actual Android-message observation
remain separate. Nothing staged, committed, pushed or merged during this correction.
