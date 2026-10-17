# Closing/order demo implementation review

Scope: approved October 16, 2026 synthetic form/report extension, with the user's later explicit
instruction to defer SMS provider integration and all external sending. This is a local preview
review, not deployment approval, operational pharmacy approval or a live Agent evaluation.

## Completed

- Created feature/order-workflow-demo from verified main 00270b3c11db6fcfd1c43a6c1893ff7b20b96da5.
  All five persistent local/remote tips matched before work; no open PRs were returned by gh pr list.
- Captured one independently validated 150-item pre-order report with original snapshot time,
  visible example closing clock and actual creation time. Subsequent human order actions do not
  change the report; missing movements and unrequested FDA context remain explicit.
- Added the searchable catalog dropdown, selected-line queue, deterministic demo suggestions,
  human quantity edits/removal/rejection and explicit simulated submit. Notification previews
  are separate from the stock report and display zero external effects.
- Updated only the Mod PRD extension, current prototype policy, README and runtime architecture.
  The original PRD draft/template, fixtures, Supabase, credentials and existing Agent tools are unchanged.

## Deviations

A dedicated web/assets/closing.js keeps this workflow separate from existing review code; it is
loaded through the shared shell and rebound on tab navigation. Existing Python/FastAPI/Jinja/plain
JavaScript conventions remain. The quantity contract is additive under pharmacy_harness;
calculate_item and existing output/report contracts were not changed. This is not proof of
Kerrian's review/approval: coordinate that shared-contract review before publication.

## Acceptance criteria

- One fixed pre-order report before submission: MET. Snapshot ID/content/timestamps remain equal
  after source mutation, a human submission and repeated close calls (unit and browser checks).
- Complete 150-row source coverage and original time labels: MET. Browser checks see 150 selectable
  items and a separate collapsed stock table; source exceptions are retained, and source failures
  do not capture a complete report. The frozen historical clock is clearly labeled.
- Search, selected-only queue, same-item deduplication, human edits and rejection: MET. Browser
  checks retain one line and its edited quantity, clear/reject drafts and preserve drafts across tabs. Submitted lines and read-only quantities also recover after a full page reload.
- Supported deterministic suggestions and missing-evidence withholding: MET. Four quantity-contract
  methods cover 50/10=5 LOW and 20/10=2 CRITICAL, target/incoming/minimum/multiple, policy mismatch,
  nonfinite/fractional policy faults, stale evidence and exact target rounding.
- Explicit human submit, no Agent tool, no purchase order or inventory write: MET. The server
  rebinds opaque selected IDs to its frozen evidence. Unsupported/duplicate/unknown lines are
  rejected. The model's attempt to use a submit tool dispatched zero callbacks in security checks.
- Input errors preserve work and report each affected field: MET. Client/browser checks cover
  empty selection/order, invalid quantities, clearing a corrected field and retaining other errors
  when a line is removed. Server rejects booleans, floats, strings, range violations and extra fields.
- Retry without duplicate demo orders: MET within one process. Concurrent identical intents return
  one order ID; changed intents conflict. This is not durable or cross-worker idempotency.
- Distinct prioritized notification previews after submit only: MET. Submitted lines are ordered
  CRITICAL before LOW/other classes, retain evidence and human edit status, and reference one order.
  The next 6 AM New York timestamp is an explicitly labeled demo assumption, not a scheduled task.
- Real-phone SMS/provider delivery: DEFERRED BY USER. Preview state is PREVIEW_ONLY with
  SMS_PROVIDER_NOT_CONFIGURED and zero sends. Actual delivery/failure/retry is NOT TESTED because
  no provider, destination or external transport is configured.
- No secrets/source text added to model context: MET by code/route scan and existing boundary
  regressions. New human-visible labels use textContent/Option; no HTML interpretation is introduced.
- Responsive shared shell and existing features: MET. All eight routes passed at 1024/640/320 widths,
  existing 20-row Demo and injection tester remain functional; zero browser exceptions observed.

## Validation

- .venv/Scripts/python.exe -B -m unittest discover -s tests -q: 291 methods PASS (14 new methods).
- Qualification CLI/function: 85 fixtures; detected 55 unsafe; accepted 30 benign; misses 0;
  false positives 0; external text excluded 85/85. Fixture agreement is not universal safety.
- node --check: closing.js and pharmacy.js PASS.
- tests/browser/pharmacy_web_check.mjs: route/mobile/navigation, existing demo/tester/failure states
  and new search/edit/error/reject/submit/report-invariance/reload checks PASS. An initial browser launch
  raced the CDP startup; rerun after readiness passed. Final run passed on a fresh server.
- git diff --check: PASS. Changed Markdown fences and trailing whitespace: PASS.

## Security scope

Synthetic local application, new closing/submit APIs and inherited access/input boundaries.
No production, database, model-provider, phone-provider or manufacturer service was tested.

## Environment tested

Windows PowerShell; project Python 3.13.15 virtual environment; Node 26.8.1; isolated headless Chrome.
Loopback preview 127.0.0.1:8770 with empty provider credentials; separate synthetic HTTPS TestClient
with reviewer credentials for hosted access cases. No new dependencies installed.

## Round 1

30 targeted methods passed across closing, security boundaries, action/output guards and bounded
contracts. Additional direct checks verified hosted authentication, same-origin enforcement,
JSON duplicate-key rejection, body size cap and CSP. A proposed submit_demo_order model tool was
rejected outside the model; successful dispatches: 0. No security findings required remediation.

## Round 2

After Round 1 was accounted for, final 291-method suite, qualification and complete browser checks
passed. Submission reported inventory_write_effects=0, order_placed=false, test SMS external_sends=0,
and manufacturer notice external_sends=0. No additional security round was declared or required.
After FIXER corrected UI reload recovery, the 20 affected closing/security methods and complete browser checks passed again; this was an affected-check recheck, not a third audit round.

## Findings

Initial REVIEWER result: REQUEST CHANGES for one NIT: encoding substitutions in newly added
Mod PRD/policy/architecture headings and an instruction implying the normal catalog has a withheld
row. FIXER replaced only the new heading separators and clarified fault-fixture coverage. Second
read-only review identified one MINOR recovery issue: after a full reload, the submitted result
was visible but its queued quantity fields were not restored, leaving an empty-list instruction
beside disabled controls. The second FIXER pass rebuilt those fields from the server's bound
submitted lines; the new reload browser regression passed. Affected security/input and complete
browser checks were rerun successfully. Final read-only re-review verified both corrections.
Older pre-existing encoding issues were left untouched. No unresolved in-scope correctness or
security findings remain; two FIXER/re-review cycles were used.

## Alerts

No breach or bypass was observed. No authorized external alert channel is configured; no alert sent.

## Untested or unavailable controls

Real SMS/provider delivery, live manufacturer acknowledgement, production 6 AM scheduler, actual
orders/receipts, durable order/outbox storage, distributed concurrency, and future operational policy
are outside this preview. Process-local demo state is shared within the authorized prototype worker
and clears on restart. Full independent backup/restore was not tested. Legacy worktree cleanup
permission errors from earlier verification were not addressed in this feature.

## Security verdict

SECURITY CLEAR WITHIN TESTED SCOPE. Exactly two sequential rounds completed.

## Line Return Reference

- `README.md`: current added/modified lines 106, 122-135; replaced/deleted prior lines 106, 122-129; line scan passed.
- `docs/architecture/Pharmacy-Web-Agent-Architecture.md`: current added/modified lines 103-137; line scan passed.
- `docs/planning/ORDER-WORKFLOW-PLAN.md`: lines 1-76 - created file; all lines reviewed.
- `docs/requirements/POLICY.md`: current added/modified lines 104, 106, 108-116; replaced/deleted prior lines 104, 106, 108; line scan passed.
- `docs/requirements/Pharmacy Inventory Logistics[PRD]-Mod.md`: current added/modified lines 11, 128, 130, 132, 134-137, 139, 141-153, 157-162, 164, 166; replaced/deleted prior lines 11, 128, 130, 132, 134-136, 138, 140-142, 146-151, 153, 155; line scan passed.
- `src/pharmacy_harness/replenishment.py`: lines 1-62 - created file; all lines reviewed.
- `src/pharmacy_web/app.py`: current added/modified lines 28, 74-84, 139, 231, 277-291; line scan passed.
- `src/pharmacy_web/closing.py`: lines 1-129 - created file; all lines reviewed.
- `tests/browser/pharmacy_web_check.mjs`: current added/modified lines 108-171; line scan passed.
- `tests/test_closing_demo.py`: lines 1-173 - created file; all lines reviewed.
- `web/assets/closing.js`: lines 1-178 - created file; all lines reviewed.
- `web/assets/pharmacy.css`: current added/modified lines 113-126; line scan passed.
- `web/assets/pharmacy.js`: current added/modified lines 471; line scan passed.
- `web/templates/base.html`: current added/modified lines 10; line scan passed.
- `web/templates/page.html`: current added/modified lines 165-201; line scan passed.
- `docs/planning/ORDER-WORKFLOW-REVIEW.md`: lines 1-161 - created review record; all lines reviewed.

## Secondary Checks

- Trailing whitespace: PASS
- Markdown fences: PASS

## Line scan

Every file and range above was inspected for its stated responsibility: additive calculation and
safe withholding; server snapshot/intent binding; strict APIs/inherited auth; text-only UI and
field feedback; responsive shell; meaningful behavior tests; and matching Mod PRD/policy/README/
architecture/recovery documentation. Replaced prior ranges were checked for unintended removal.
The final scan completed with no unresolved findings. This review record contains only redacted
local evidence and source paths; no credentials, personal phone number or raw model reasoning.

## Verdict

APPROVE for the accepted local, preview-only demo. The user subsequently approved the running
preview for grouped commits, feature-branch push and PR creation. Merge, deployment and branch
deletion remain subject to their approval gates; no live integration has been authorized.
