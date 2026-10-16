# Two-phone browser demo - implementation and acceptance

Approved October 16, 2026. No SMS, real ordering, stock mutation, Agent write
tool or 6 AM scheduler. Existing feature/order-workflow-demo and PR #30 stay open.
The Supabase prerequisite was implemented on feature/supabase-migration after
its approved fast-forward; the demo branch was then fast-forwarded locally and
remotely to the same 198-commit tip before application integration.

## Setup

- Existing reviewer username/password and VAPID sender configuration remain.
- Add PHARMACY_DEMO_DATABASE_URL from ignored .env.demo to the intended Vercel
  Preview/Production environment server settings and redeploy the tested commit.
  This is the separate restricted demo identity; never use the inventory URL,
  public key or management credential. Do not paste its value into chat or Git.
- Both devices use the same HTTPS origin in Android Chrome. Each phone enables
  browser notifications independently. No phone number or third-party SMS account.

## Demo steps

1. A: Use this phone to order. Share the displayed single-use code only with B.
2. B: paste the 24-character code and Join as receiving phone within ten minutes.
3. Enable notifications on both; Refresh pairing / orders confirms both ready.
4. A: Close day / Generate report, select catalog items, edit quantities, submit.
5. B: observe the browser order notification with selected items/quantities;
   tap to open the exact received order. Full catalog rows are never pushed.
6. B: Delivery Received is available only for that submitted order. Press it.
7. A: observe a distinct delivery-received browser alert for the same order;
   tap to open its acknowledgement. The frozen report and stock remain unchanged.
8. B: the confirmation becomes disabled/Delivery confirmed. Duplicate requests
   return the same stored outcome without another send. A can prepare another
   order against the same report, up to twenty orders in that closing session.
9. End pairing stops further paired actions and clears subscriptions. Accepted
   messages may still arrive. A new pairing is explicit, not a silent retarget.

## Failure and privacy checks

No code/role/database credential is a phone number. Only the intended paired
recipient is selected server-side. Device secrets are HttpOnly cookie values;
no invitation hash, raw subscription or encryption key appears in status/order
responses. The pairing code is shown only when explicitly created/renewed and
is cleared from the page after successful binding. Invalid codes retain input
and show field feedback; expired/consumed codes require a new invitation.

Browser waits are bounded. Submission, delivery record and push outcome are
separate. Duplicate notification reservations are committed before IO, so an
uncertain response is not retried automatically. A missing configuration,
wrong-role/cookie/order, ended/expired room or storage outage cannot silently
fall back to another recipient or the process-local demo.

## Evidence and remaining acceptance

Private schema deployment, real restricted TLS login, shared state across two
independent store instances, consumed-code rejection and denied inventory/admin
access were verified. Two rollback-only SQL security rounds and the deployed
contract passed. Synthetic service/API/browser checks use fake receiving keys
and no external notification sends. Record full-suite/qualification, security
rounds and visible UI verification alongside the final change before push.

Actual deployed two-phone display, exact-order tap and return-alert observation
remain pending until the user performs steps 1-7. Do not label service acceptance,
a local mock or a successful build as proof of phone delivery. The initial
single-browser notification was user-confirmed; that evidence does not prove
the newly added paired round trip.

## Publication validation - October 16, 2026

- Full local unittest discovery: 322 methods passed.
- Qualification CLI: 85 contained fixtures; 55 unsafe detected, 30 benign
  accepted, zero misses and zero false positives. This is fixture evidence,
  not a universal detection rate or live-model result.
- Node simulations: pairing_check, push_client_check and closing_link_check
  passed with no external sends.
- SECURITY Round 1: 68 targeted store, pairing, closing, push and web methods
  passed, along with pairing/worker simulations. Role, exact-order, cookie,
  request-origin, payload, replay/concurrency, bounded waits and redaction
  checks found no outstanding executable-code findings requiring remediation.
- SECURITY Round 2: the same 68 methods and all three browser simulations
  passed sequentially after Round 1 was accounted for. No new Agent tools,
  inventory grants or outbound destinations were added.
- Real private TLS store: two independent service/store instances passed
  single-use enrollment, A-to-B selected order, B-to-A delivery, duplicate
  suppression and unchanged 150-item report assertions. The sender was fake;
  no external push was sent. The synthetic test pair was ended and its
  subscriptions cleared; its retained demo row uses the existing 24-hour expiry.
- Visible local preview: pairing panel, role guidance, required-code summary,
  linked field feedback and available controls inspected in the browser.
  Screenshot retained locally outside Git. Embedded preview does not prove
  phone permission or delivery.
- Final read-only REVIEWER: server-bound roles and recipients, minimized
  payloads, unchanged snapshot/stock, legacy unpaired behavior, setup/privacy
  documents and changed-line scan inspected. APPROVE for branch publication;
  physical two-phone acceptance remains explicitly pending.

Security verdict: CLEAR WITHIN TESTED SCOPE. Hosted secret configuration,
Vercel deployment and physical Chrome display/tap remain unverified here.
No release, main merge, branch deletion, production retention guarantee or
real manufacturer-delivery claim follows from this publication review.
