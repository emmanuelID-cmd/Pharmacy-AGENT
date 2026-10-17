# Repeat demo orders

## Context

Emmanuel reported that refresh plus Close day recovered the submitted order but left no way to
start another without leaving the session. The existing ClosingDemo.submit explicitly allowed
only one order per closing report. The second reported issue, notification text, requires a new
submission to reproduce; no actual SMS service is connected. Baseline tree was clean at
c28fc8dbf42c1589a4ac3ca20309585099ae6a18 on feature/order-workflow-demo, matching origin;
main remained 00270b3 and PR #30 remained open/mergeable, with no remote changes to reconcile.

## Approach

Retain one immutable pre-order report and permit separate human-submitted demo orders against it.
Expose New demo order and retained history, preserving the existing authentication, form pattern
and read-only Agent boundary. Rejected alternative: wiping the report/session, which would obscure
earlier evidence and unnecessarily create another closing report.

## Steps

1. src/pharmacy_web/closing.py - retain orders and canonical intents up to a visible limit of 20;
   preserve idempotent older retries and bind each notification attempt to its exact order.
2. web/assets/closing.js and web/templates/page.html - add New demo order, history, fresh intent
   and unlocked form controls while preserving the original report and browser opt-in.
3. tests/test_closing_demo.py and tests/test_push_notifications.py - verify repeat orders,
   unchanged report, copied history, capacity, conflicting intents and per-order notification.
4. Browser regression - verify refresh/recovery, new draft, second submit, retained history,
   tab/report return, validation and narrow layout without real sends.
5. Mod PRD, policy, README, architecture and current setup notes - reconcile the previous one-order
   wording; preserve historical plan/review evidence. Run full tests, qualification, two sequential
   security rounds and final read-only review before preview.

Steps are sequential because UI and tests share the server response contract. No delegation is
needed for this tightly connected change. No new dependencies or runtime are required.

## Acceptance criteria

- A second distinct order can be prepared/submitted after refresh without logging out.
- Report identity, timestamp, original stock and read count remain unchanged.
- Earlier orders remain visible in history and cannot be mutated through returned objects.
- A new draft sends nothing. Distinct human submissions retain distinct notification attempts;
  retries of any older submission/order cannot create another order or resend its notification.
- Reusing an intent with changed contents conflicts. Capacity rejects order 21 without dropping
  history; existing retries still work at capacity. Quantity/item validation remains enforced.
- Report/tab return preserves a newly started draft while the document remains open. Full reload
  restores the latest submission, with New demo order available again.
- No Agent permission, inventory mutation, database write or real purchase order is introduced.

## Out of scope

SMS, actual purchasing, a second end-of-day report, amendments/cancellations, delivery scheduling,
Supabase changes, durable cross-worker/session storage and independent desktop-to-phone pairing.

## Unknowns

The overall two-issue investigation is provisional only for the notification-text observation.
- Unknown: actual Android notification body after a fresh submission.
  Recommendation: complete repeat orders, then inspect the notification title/body on the phone.
  Basis: the existing notification deliberately carries fixed generic text, not inventory details;
  the user cannot currently generate another order to reproduce the reported empty message.
  Verification action: observe a new submitted-order notification and its displayed text, without
  exposing private keys. This does not block the independent repeat-order correction.

## Plan handoff

The user's reported repeat-order issue authorizes this focused correction. Proceed through
ARCHIVIST, BUILDER, SECURITY and REVIEWER, then preview. No new branch or PR is needed. Commit,
push and merge remain subject to the existing approval gates.

ARCHIVIST: tracked source can be selectively reverted to the verified clean c28fc8d baseline;
no database migration, source-fixture change or secret export is needed. Previous demo orders
are retained in memory rather than deleted; restart/multi-worker limitations remain. No isolated
restore or independent backup was tested: RESTORE NOT VERIFIED. No production state was changed.

UX: the authorized reviewer needs a repeatable demo and visible prior evidence. New demo order
is adjacent to the form, history is progressively disclosed with native details, and the existing
report and opt-in remain stable. Keyboard focus moves to item search; errors clear only for the
new draft, while ordinary quantity validation retains valid entries. Layout uses existing classes.
These are continuity, visibility and grouping choices, not claims of user-research proof.
