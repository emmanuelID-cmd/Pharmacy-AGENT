# Notification and order-control recovery - review

Baseline: 0f13c51662e6fd62a8aee246db6e8b6013bed334 on feature/order-workflow-demo, matching origin before work. PR #30 was open/mergeable with successful Vercel deployment. The user reported no Android notification and an indefinitely faded submit button. The supplied follow-up quoted the form's static helper paragraph, not a delivery status. The exact phone failure stage remains UNKNOWN.

## Context

closing.js keeps the form busy while push.js waits for a notification response. The request was unbounded, and notification errors hid the server's specific safe reason. A newly introduced worker update also ran before existing subscription restoration, so update failure skipped that restoration.

## Approach

Release order controls once submission is confirmed, independently of notification delivery. Bound browser requests and worker setup, and display fixed failure references without exposing keys or endpoints. Re-enabling the same completed order's submit button was rejected because it would blur recorded state and duplicate-submission prevention.

## Steps

1. Add tests for a stalled notification request, failed worker update and rejected notification.
2. Correct subscription restoration and request deadlines in web/assets/push.js.
3. Correct submission completion and button feedback in web/assets/closing.js.
4. Update setup/review documentation, run regression checks and two security rounds, then present the local result.

## Acceptance criteria

- A recorded order enables New demo order even while notification delivery is pending.
- A stalled request ends with clear feedback and never retries automatically.
- Worker-update failure preserves an existing subscription.
- A rejected send shows a safe, specific reference.
- The same recorded order cannot be submitted again; its button says Order submitted.

## Out of scope

Recipient pairing, delivery confirmations, storage changes, new PRs and squashing. No sender key, permission, model capability, API route, purchase order or database changed.

## Unknowns

- Unknown: exact failed stage on Android. Recommendation: retain existing permissions and keys while adding diagnostic references. Basis: generic delivery previously worked, but no current request/result trace was provided. Verification action: inspect live status under the form on the corrected deployment, then retest on Android. The phone-cause conclusion remains provisional.

## Plan handoff

Implemented as a bounded correction to the approved notification work. ARCHIVIST -> BUILDER -> two sequential SECURITY rounds -> read-only REVIEWER. Publication remains subject to completed-preview approval; no commit/push occurred in this correction.

## ARCHIVIST

Activation: source, UI behavior and documentation changes. Environment: authorized Pharmacy workspace only. P2 source/docs/tests are retained in readable baseline Git and matching remote history. P1 private configuration references remain ignored and unaltered; values were not inspected, copied or exported. No database, external archive or production restore was attempted. Retention/recovery-time objectives remain UNKNOWN. Restore prerequisites: baseline Git, project dependencies and independently managed private configuration. No isolated restore or byte-for-byte backup verification was performed: RESTORE NOT VERIFIED. Verdict: ARCHIVIST READY WITH CONDITIONS for these bounded source edits; no broader recovery claim.

## BUILDER completed

- Preserved existing subscription restoration before an independent bounded worker update; update failure/pending state does not silently lose that subscription.
- Added a 20-second fetch/body deadline with abort for notification/configuration and close/submit requests. A timed-out submission retains its intent/draft for reconciliation; notification uncertainty never triggers an automatic resend.
- Released order busy state before awaiting notification; separated notification failure from recorded-order success. Button labels identify Submitting and Order submitted.
- Moved the single New demo order button beside submit/clear and mirrored notification feedback below the form, with order ID and fixed allowlisted rejection/timeout references. Newer notifications and Disable suppress stale feedback.
- Updated README, Mod PRD, policy, architecture and Android setup instructions without altering historical reviews or the original PRD.

Deviations: none beyond clarifying the feedback placement after the user could find only the static helper paragraph. That placement remains within the planned button-feedback correction. No new detector pattern, service, dependency, staff-write feature or Agent permission.

## Prior failing evidence

Before changing runtime code, the new isolated tests failed against baseline with:
- push_client_check.mjs: existing subscription lost when worker update failed; expected notification count 1, actual 0.
- closing_link_check.mjs: pending push kept New demo order disabled; expected false, actual true.

These are confirmed local defects, not proof of the original phone's failure stage. No real external sends were used to reproduce them.

## UX review

Primary user: authorized Android demo reviewer trying to understand whether an order recorded and start another. Continuity keeps the stock report/history/intent intact; proximity places New demo order and notification feedback beside the completed action; visible status distinguishes recorded order from notification delivery. Existing styles, accessible live status regions, native controls and field validation remain. Visible narrow browser verified labels, enabled next-order action and fresh-draft recovery. No new fields/CSS, invented user research or complete assistive-technology audit. Reference: [Laws of UX](https://lawsofux.com/).

## Security scope

Human submission -> retained order -> independent notification attempt; browser fetch/body/setup wait bounds; safe failure mapping and stale-status handling. Existing authenticated/origin/JSON limits, FCM validation, encrypted selected payload, model tool denial and server one-attempt lock remain unchanged.

## Environment tested

Local Python 3.13 virtual environment; synthetic unittest data; fake push transport; isolated Node browser/DOM simulations; visible loopback preview on port 8772 with no push key/model credentials. No live model, FDA, database, actual phone push or production security scan.

## Tests executed

Full unittest discovery: 308 methods PASS. Qualification: 85 contained, 55 unsafe detected, 30 benign accepted, zero misses/false positives; these fixture results are not a universal detection rate. Both Node simulations pass with stalled fetch/body, failed/pending worker update, specific/unknown rejection redaction, mirrored feedback, late responses, Disable and form recovery. JavaScript syntax and whitespace checks pass.

## Round 1

31 affected closing/push methods, both Node simulations, syntax/diff checks and ignored-key check passed. Reviewed complete runtime diff; no security finding requiring remediation. No external send or alert generated.

## Round 2

Repeated the 31 affected methods, both Node simulations and syntax/diff checks after accounting for Round 1 (no remediation needed). All passed. Confirmed no automatic resend, unsafe response reflection, endpoint/secret disclosure, permission expansion or stock mutation was introduced.

## Passed checks

Existing subscription survival, bounded pending fetch/body waits, order-control release, next-draft recovery during pending notification, retained intent on submission uncertainty, safe reason mapping, duplicate-send containment, unchanged encrypted selected-order payload and same-origin click protections within tested scope.

## Failed checks

The two initial regression tests above failed before correction and pass afterward. No unresolved in-scope test failure. Existing CRLF-to-LF notices are warnings; whitespace checks pass.

## Warnings

A browser timeout is not proof that the server stopped or the order did not record. Reconcile the same intent before retry. Already-dispatched pushes cannot be recalled by Disable. State remains worker-local; missing orders on a different Vercel worker remain possible. Android display/cause is not established by these local checks.

## Leaks detected

None observed in synthetic checks; private configuration and third-party response bodies were not inspected. Arbitrary server reason strings are replaced by fixed references.

## Authentication and authorization findings

No findings in the affected checks/source review. Existing auth, origin and strict request schema remain unchanged. Agent notification dispatch remains denied.

## Network and API findings

Added browser-side 20-second fetch/body wait limits and abort signals; preserved server transport IO bounds, no redirects/proxies and at-most-one attempt. Config/setup errors retain explicit uncertainty. Actual FCM and Vercel runtime responses for the reported phone event are UNTESTED/UNAVAILABLE.

## AI-detection findings

No model context, guard pattern or tool allowlist changes. Existing qualification remains 85 contained, zero fixture misses/false positives; no universal safety claim.

## URL and connection findings

No route, external host or click destination changed. Both existing exact-order/malformed-link simulations still pass. Local browser recorded demo-8f0a1fec2ff7 with quantity 20, showed Order submitted with enabled adjacent New demo order and PUSH_NOT_ENABLED beside the form because this local server intentionally has no push configuration. Clicking New demo order enabled Submit demo order, cleared only the draft and preserved report/history. This is not a phone send. Full CDP regression was not rerun.

## Recommended remediation

No further in-scope security remediation. After preview approval, publish on the existing branch/PR and inspect the actual Android notification status/reference before identifying the phone failure cause. Do not rotate keys, retry uncertain sends, weaken authentication or squash history based on these local results.

## Alerts

No breach signal or external alert generated. No new alert channel or third-party integration.

## Untested or unavailable controls

Actual Android selected-order delivery/display/tap and its failing request trace, live worker-update behavior on that device, production multi-worker durability and isolated restore readiness.

## Security verdict

SECURITY CLEAR WITHIN TESTED SCOPE.

## REVIEWER acceptance

- Recorded order unlocks next action while notification pending - MET in DOM simulation and visible browser.
- Bounded wait/uncertainty without automatic resend - MET in stalled fetch/body and stalled-submit simulations; draft/intent retained.
- Failed/pending update preserves subscription - MET in browser API simulations; prior failure reproduced before fix.
- Safe specific failure reference - MET for known rejections and timeout; arbitrary/private reason redacted; mirrored beneath form.
- Recorded order remains locked and clearly labeled - MET in visible browser and DOM simulation; New demo order restores active empty form.
- Existing order/notification boundaries preserved - MET in 31 affected tests and source review; no permissions, report or stock changed.

## Findings

No unresolved in-scope correctness/security finding. Original Android missing-alert cause remains unknown; hardware delivery is not claimed as fixed. FIXER not required after final review.

## Line scan

Inspected all changed files/ranges below, including newly created report lines, for approved scope and actual claims. No findings.

## Line Return Reference

- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\README.md`: current 140-143 added. Reviewed approved correction.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\architecture\Pharmacy-Web-Agent-Architecture.md`: current 168-176 added. Reviewed approved correction.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\planning\ANDROID-PUSH.md`: prior 31 deleted/replaced; current 31-52 added. Reviewed approved correction.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\requirements\POLICY.md`: current 120-127 added. Reviewed approved correction.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\requirements\Pharmacy Inventory Logistics[PRD]-Mod.md`: current 173 added. Reviewed approved correction.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\tests\browser\closing_link_check.mjs`: prior 14 deleted/replaced; current 14 added; current 16 added; prior 26 deleted/replaced; current 27 added; prior 35 deleted/replaced; current 36-38 added; current 44-45 added; current 52 added; prior 51 deleted/replaced; current 57 added; current 88-112 added. Reviewed approved correction.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\tests\browser\push_client_check.mjs`: prior 7 deleted/replaced; current 7-8 added; prior 14 deleted/replaced; current 15 added; prior 20-21 deleted/replaced; current 21-25 added; prior 26-28 deleted/replaced; current 30 added; prior 32-33 deleted/replaced; current 34-35 added; prior 45 deleted/replaced; current 47-52 added; prior 52 deleted/replaced; current 59-60 added; current 69 added; current 97-133 added. Reviewed approved correction.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\web\assets\closing.js`: prior 20-23 deleted/replaced; current 20-30 added; current 119 added; prior 216 deleted/replaced; current 224 added; current 227 added; prior 224-225 deleted/replaced; current 233-234 added; current 237-240 added. Reviewed approved correction.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\web\assets\push.js`: prior 4 deleted/replaced; current 4 added; prior 8-9 deleted/replaced; current 8-11 added; current 30-45 added; prior 44 deleted/replaced; current 62 added; prior 46-49 deleted/replaced; current 64-66 added; current 72 added; prior 60 deleted/replaced; current 78 added; prior 87 deleted/replaced; current 105 added; current 114-118 added; prior 97 deleted/replaced; current 120 added; prior 99 deleted/replaced; current 122-131 added; prior 102 deleted/replaced; current 134 added; prior 104-109 deleted/replaced; current 136-145 added. Reviewed approved correction.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\web\templates\page.html`: prior 181 deleted/replaced; prior 200 deleted/replaced; current 199 added; current 203 added. Reviewed approved correction.
- `C:\Users\dejes\OneDrive\Documents\Pursuit\Pursuit\_Lessons\L2-Week-3\Pharmacy-Agent-Role\docs\planning\PUSH-RECOVERY-REVIEW.md`: current 1-172 added; created review, all lines new.

## Secondary Checks

- Trailing whitespace: PASS
- Markdown fences: PASS

## Verdict

APPROVE for local preview within tested scope. Preview approval, commit/push and actual Android acceptance remain separate.
