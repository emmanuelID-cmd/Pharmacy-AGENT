# Selected-order push - implementation and verification

Baseline: `37a4be4a1ede84480c19f11ada7a3e55eda0eef0` on `feature/order-workflow-demo`; PR #30 open/mergeable and remote matched before work.
User approved the next order-list notification step after providing a screenshot of the generic Android push.
No new branch, PR, commit, push, merge, history rewrite or real external send occurred during this implementation.

## Context

ClosingDemo.notify already binds a notification to a recorded order, but PushSender and the phone's service worker used generic text. closing.js retains submitted-order history, so it can select the order identified by a notification tap.

## Approach

Build the notification from the server's recorded order, showing only selected items, quantities, units and stock priority. Keep a bounded preview for long orders, with the complete list available on tap. Browser-supplied message text and destinations remain disallowed.

## Steps

1. Update src/pharmacy_web/push.py and closing.py to construct and encrypt the selected-order preview.
2. Update web/assets/push-worker.js to validate and display it, then open that order on the same site.
3. Update web/assets/closing.js to recover the identified order, or clearly report when it is unavailable.
4. Add encryption, payload, notification-click and order-recovery checks.
5. Update the Mod PRD, policy, README and architecture/setup documentation; run the required reviews and present a local preview.

## Acceptance criteria

- A two-item order produces those two lines with the human-submitted quantities.
- Unselected catalog items never appear.
- Long orders show that more items exist.
- Tapping selects the exact order, including an older order.
- Missing orders produce an unavailable message rather than displaying another order.
- Duplicate requests do not resend; inventory and Agent permissions remain unchanged.

## Out of scope

Recipient pairing, delivery confirmations, SMS, scheduling, Supabase changes and commit squashing.

## Unknowns

- Unknown: Android's visible text limit. Recommendation: preview up to six lines and link to the complete order. Basis: notification space varies by device. Verification action: inspect the deployed notification on the phone; local tests verify the payload first. This device-display acceptance remains provisional until observed.

## Plan handoff

The user's approval covered implementation. Proceeded through ARCHIVIST, BUILDER, two SECURITY rounds and read-only REVIEWER; present the result before committing or pushing under workflow/development.md.

## ARCHIVIST

Activation reason: source, notification behavior and requirements changes.
Environment: authorized local Pharmacy workspace; no external AGENTS changes.
Scope reviewed: tracked source/docs/tests and ignored configuration references only.
Authorization boundary: approved source edits; no secret copy, restore, key rotation or database access.

### Backup Inventory

- P2 standard: tracked source/docs/tests; source of truth is baseline Git commit above and matching remote. Existing Git history, no new archive claimed. Owner Emmanuel; preserve history until approved consolidation. Recovery objective UNKNOWN; verify baseline file content before any restoration.
- P1 high: sender-key configuration reference PHARMACY_PUSH_PRIVATE_KEY; local .env.push exists/ignored, actual values excluded from inspection/exports. Existing hosting configuration was not inspected or changed. Retention and recovery objective UNKNOWN; use the existing private configuration management, not source archives.

### Restore Readiness

Tracked baseline is readable through Git; no isolated restore, byte-for-byte backup or provider restore was run. Production impact: none. RESTORE NOT VERIFIED. ARCHIVIST READY WITH CONDITIONS for bounded source edits using the retained baseline; no claim of full disaster-recovery readiness.

## BUILDER

Implemented all five ordered steps. Payload kind synthetic-order-v1 contains only server-bound demo order ID, total selected count and up to six label/quantity/unit/priority records; UTF-8 encoding stays within 3000 bytes by removing trailing preview lines. Optional malformed labels use a fixed item reference. Required invalid data withholds sending. No new detector pattern or model permission was introduced.

Worker validates the schema, constructs notification text and a same-origin exact-order destination, tags notifications per order, and falls back to fixed text for malformed/legacy content. Page load requests worker updates; install activates the updated worker. UI discloses selected names/quantities on notification/lock screens before opt-in. Existing styling, navigation and order controls remain.

Deviations: none in scope. The first combined patch was rejected for two operations against one file; no changes were applied by that failed patch, and a single update operation corrected it. Normal sandbox Python could not resolve the runtime; the same checks succeeded with authorized project elevation. One browser label locator was ambiguous; the exact observed label resolved it without changing application code.

## UX review

Primary user: authorized reviewer on Android inspecting a human-submitted synthetic order. Task: recognize selected lines and return to that exact order. Chunking/progressive disclosure supports the bounded list with remaining-count text; continuity supports exact older-order selection and retained report; visible feedback supports unavailable-order errors and focus on the opened result. Reference: [Laws of UX](https://lawsofux.com/), used as design prompts, not user research.

Existing semantic controls, keyboard focus, live status messages and responsive styles are preserved; no new form fields or CSS. The visible narrow browser showed selected lines wrapping and focused the result. Cold-start, missing-worker and offline limitations remain explicit. No device research or complete screen-reader/mobile hardware audit is claimed.

## Security scope

Boundaries: strict human notification request -> retained server order -> minimized encrypted payload -> worker validation/text display -> same-origin exact-order lookup. Agent tools, reviewer auth, origin/body limits, fixed FCM host, no redirects/proxies, bounded IO and one-attempt lock remain in force. No patient/live pharmacy data, key disclosure or third-party scan.

## Environment tested

Local Python 3.13 virtual environment; unittest synthetic fixtures; fake encryption receiver/transport; Node isolated worker/client/DOM simulations; loopback preview on port 8771 with no push key/model credentials. No real notification send during these checks.

## Tests executed

- Full local unittest discovery: 308 methods PASS.
- Qualification CLI: 85 contained, 55 unsafe detected, 30 benign accepted, zero misses and zero false positives. Fixture agreement is not a universal detection rate.
- Two sequential SECURITY rounds: each 31 affected closing/push methods, push_client_check.mjs, closing_link_check.mjs, JavaScript syntax and diff checks PASS.
- Fake encrypted payload decrypts to exact selected order/human quantities; bounded Unicode/150-line previews, invalid required fields, malformed optional labels and legitimate Unicode tested.
- Worker simulations cover malformed/legacy payloads, quantity/ID bounds, injected destinations, exact new-window and existing-window order links, permission failures and update handling.
- DOM simulation covers older-order selection, focus/scroll, missing/malformed links, new draft, latest-order default and safe failed request.

## Round 1

All 31 affected tests, both Node simulations, syntax/whitespace checks and ignored-key check passed. Source review found no security finding requiring remediation. No external sends.

## Round 2

Repeated those checks after accounting for Round 1 (no findings/remediation). All passed. Confirmed endpoint/auth restrictions and one-attempt lock were preserved; source text remains display data and never model authority, executable HTML or a supplied navigation target.

## Passed checks

Selected-order minimization, exact human quantities, bounded Unicode payload, safe label fallback, malformed-worker fallback, same-origin links, retained-order binding, concurrent deduplication, auth/origin restrictions, bounded transport and secret exclusion within tested scope.

## Failed checks

No application test failures. Initial patch/runtime/locator tool failures are disclosed under BUILDER and were resolved. Existing Git CRLF-to-LF notices are warnings; diff whitespace checks pass.

## Warnings

Phone/OS may truncate previews further. Shared-reviewer, process-local state can disappear on restart or be absent on a different Vercel worker; missing references show unavailable. No cross-device pairing or durable order service is implemented.

## Leaks detected

None observed within synthetic tests. No real secrets or pharmacy records were inspected or exported.

## Authentication and authorization findings

No findings in the scoped review/tests. Existing protected routes and strict notification request schema remain unchanged. External content cannot add a message, recipient or destination to the request. The Agent cannot dispatch notifications.

## Network and API findings

Fake transport tests verify encrypted selected content and no plaintext key leakage; existing fixed FCM validation, IO bounds, redirect/proxy restrictions and service-acceptance distinction remain. Live FCM acceptance/device display for this payload is UNTESTED.

## AI-detection findings

No detector pattern, model context or model tool changed. Existing qualification remains 85 contained, zero misses/false positives in its selected fixtures. No universal detection claim.

## URL and connection findings

Exact ID constructs only /demo?order=demo-<12 hex>#order-result on the current origin. Visible browser opened older demo-f889b76d289e with quantities 20/30 despite newer demo-23970913ca55 having quantity 1; unknown demo-000000000000 displayed unavailable and hid the result. The report creation time remained 2026-10-16T11:42:12-04:00. Browser captured no warn/error logs. Full existing CDP regression was not run in this follow-up.

## Recommended remediation

No in-scope security remediation required. Deploy after preview/publication approval, then observe selected-order notification content and tap on Android before claiming phone acceptance. Pairing/shared persistence and delivery confirmation require their separate scoped implementation.

## Alerts

No breach or external security alert generated. No new alerting channel configured.

## Untested or unavailable controls

New payload's actual Android display, OS truncation, real notification tap, live FCM send, multi-worker durability and isolated backup restore. Earlier generic display is supported only by the user's supplied screenshot.

## Security verdict

SECURITY CLEAR WITHIN TESTED SCOPE.

## REVIEWER acceptance

- Two selected lines/human quantities - MET by encryption/decryption and worker tests; visible local order shows 20 and 30 tablets.
- Unselected catalog data excluded - MET: payload is assembled only from recorded order.lines, with explicit field allowlist; no snapshot/evidence/NDC/secret fields.
- Long order disclosed - MET by 150-line and 3000-byte bounds plus remaining-count tests; Android visual extent remains untested.
- Exact older order - MET in worker/DOM tests and visible browser, including result focus.
- Missing order - MET in DOM and visible browser; no latest-order substitution.
- Duplicate containment/read-only - MET in existing concurrent/older retry tests and source review; snapshot unchanged.
- Documentation matches scope - MET: Mod PRD, policy, README, setup and architecture updated; original PRD/templates and historical reviews preserved.

## Findings

No unresolved in-scope correctness or security findings. FIXER not required. Hardware display/tap remains a deployment acceptance step and is not claimed as completed.

## Line scan

Every file/range in the following Line Return Reference was inspected against the plan, including this report's created lines. No findings.

## Line Return Reference

- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\README.md`: prior 136-137 deleted/replaced; current 136-139 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\architecture\Pharmacy-Web-Agent-Architecture.md`: prior 151 deleted/replaced; current 151-156 added; prior 157-158 deleted/replaced; current 162-168 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\planning\ANDROID-PUSH.md`: current 6-8 added; prior 20 deleted/replaced; current 23-27 added; prior 48-49 deleted/replaced; current 55-59 added; prior 60 deleted/replaced; current 70-73 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\requirements\POLICY.md`: prior 100 deleted/replaced; current 100 added; prior 120 deleted/replaced; current 120 added; prior 122 deleted/replaced; current 122 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\requirements\Pharmacy Inventory Logistics[PRD]-Mod.md`: prior 166 deleted/replaced; current 166 added; prior 170 deleted/replaced; current 170-171 added; prior 172 deleted/replaced; current 173 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\src\pharmacy_web\closing.py`: prior 69 deleted/replaced; current 69 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\src\pharmacy_web\push.py`: current 6 added; prior 16 deleted/replaced; current 17-19 added; current 21-53 added; prior 71 deleted/replaced; current 107 added; current 109 added; prior 80 deleted/replaced; current 117 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\tests\browser\closing_link_check.mjs`: current 1-82 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\tests\browser\push_client_check.mjs`: prior 18 deleted/replaced; current 18 added; prior 21 deleted/replaced; current 21 added; current 57 added; current 89 added; current 91 added; prior 91 deleted/replaced; current 94 added; prior 95 deleted/replaced; current 98 added; prior 98 deleted/replaced; current 101-131 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\tests\test_push_notifications.py`: current 2 added; prior 18 deleted/replaced; current 19 added; prior 47 deleted/replaced; current 48-52 added; prior 51-55 deleted/replaced; current 56-61 added; current 66-106 added; current 122-123 added; prior 105 deleted/replaced; current 154 added; prior 109 deleted/replaced; current 158 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\web\assets\closing.js`: current 144 added; prior 154 deleted/replaced; current 155-159 added; current 162-169 added; current 175-176 added; current 229 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\web\assets\push-worker.js`: current 2-16 added; prior 3-7 deleted/replaced; current 18-27 added; prior 12 deleted/replaced; current 32-35 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\web\assets\push.js`: current 48 added; prior 51 deleted/replaced; current 52 added; prior 53 deleted/replaced; current 54 added; prior 80 deleted/replaced; current 81 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\web\templates\page.html`: prior 170 deleted/replaced; current 170 added; prior 172 deleted/replaced; current 172 added. Reviewed approved scope.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\planning\ORDER-PUSH-REVIEW.md`: current 1-190 added; created review, all lines new.

## Secondary Checks

- Trailing whitespace: PASS
- Markdown fences: PASS

## Verdict

APPROVE for local preview within tested scope. Commit/push, deployment, selected-order phone observation and eventual consolidation remain separate.
