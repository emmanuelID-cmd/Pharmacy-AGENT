# Android demo notifications

Approved by Emmanuel on October 16, 2026: replace the proposed SMS integration with optional
Chrome/Android Web Push. Existing SMS/manufacturer previews remain previews. No paid SMS account,
TextNow login or phone number is needed. Chrome's push service still transports encrypted messages.

Approved follow-up: show the selected submitted-order list instead of the generic confirmation.
The user's Android screenshot verifies generic delivery; the new content/tap still needs a phone test.

## Setup

1. Install the project dependencies from requirements-web.txt in the existing virtual environment.
2. Run `python -m src.pharmacy_web.push_keys`. It creates `.env.push` and never prints or overwrites
   the private key. `.env.*` is already ignored; hosting excludes it. Keep this file private.
3. For Vercel, securely copy the `PHARMACY_PUSH_PRIVATE_KEY` setting from that local file into the
   project's environment settings for the deployment you will test, then redeploy the approved
   commit. Do not paste it into a PR, chat or frontend setting. The public key is derived server-side.
4. Optional `PHARMACY_PUSH_SUBJECT` is an HTTPS contact page; the default is this project's GitHub
   page. Its URI path is valid under RFC 8292, although the signing library's strict regex rejects
   paths; the adapter validates the HTTPS contact itself before signing. No contact email is needed.
5. On Android, open the deployed HTTPS Demo page in Chrome and pass existing reviewer login.
   Enable notifications, approve Chrome permission, close the day, add an item and submit there.
6. Check Android's notification tray for the synthetic order ID and selected names, submitted
   quantities, units and priorities. Short orders show their lines; long orders show at most six
   lines (fewer for the 3000-byte UTF-8 limit) and a remaining-item count. Android may truncate further.
   Tap to open that exact order's complete list, even when a newer order exists. Missing worker
   history shows unavailable rather than another order. Names/quantities may appear on the lock screen.
   If Chrome/site/Android notification permissions or battery settings block it, service acceptance
   alone is not proof of delivery. Disable unsubscribes; already accepted messages may still arrive.

### Submission and notification recovery

After the order response arrives, **Submit demo order** changes to **Order submitted** and stays
disabled for that recorded order. **New demo order**, beside the submit/clear controls, starts a
different draft without clearing history or the closing snapshot. It becomes available immediately
after order confirmation, even if the notification request is pending. The static paragraph under
the form is explanatory text, not a submission or delivery confirmation.

Read the live notification status immediately below the form (also shown beside Enable). Browser
request/body waits have a 20-second deadline and are aborted when that wait ends. A timed-out order
may already exist: use View same closing report to reconcile before retrying its retained intent.
A notification timeout is unconfirmed, never an automatic resend. Known server rejections show
fixed references such as DEMO_ORDER_NOT_FOUND, PUSH_KEYS_NOT_CONFIGURED or PUSH_SERVICE_REJECTED;
no endpoint, secret or raw server text is displayed. A newer notification request supersedes older
status messages, and disabling notifications prevents late results from overwriting its feedback.

The existing subscription is restored before an independent worker-update check. Failure or timeout
of that update retains the subscription and reports PUSH_WORKER_UPDATE_UNCONFIRMED when still
relevant; it does not silently turn notifications off. This fixes a reproduced browser setup path,
but does not establish the cause of an unobserved Android delivery failure.

### Browser setup troubleshooting

The embedded Codex preview is useful for reviewing the form; use the deployed HTTPS link directly
in Chrome on Android for the phone test. A localhost/127.0.0.1 address refers to the device opening
it, so copying this computer's local link onto a phone does not connect to this computer.

Enable failures now include a fixed reference identifying PERMISSION, WORKER or SUBSCRIPTION and
the browser error category. These references contain no native error text, delivery endpoint or
key. A SUBSCRIPTION failure is not evidence of denied notification permission; it may be the
browser's push-service connection. If setup fails, the form/order remains usable and Enable can
be tried again. Actual embedded-browser push support is not inferred from the presence of API
objects. No Android delivery is claimed until observed on that device.

The Enable path reports its current stage and limits each awaited browser setup operation to
20 seconds. If a browser permission promise never settles, the page shows
PUSH_PERMISSION_TIMED_OUT and restores Enable instead of remaining stuck. The native prompt or
operation may still be pending in the browser; the timeout does not silently grant permission or
cancel the browser's own operation, and no notification is sent by enabling alone.

## Scope and recovery

This version sends to the browser submitting the order. Desktop-to-phone pairing is not built.
After submitting, New demo order permits another submission against the same fixed closing
report, up to 20 retained orders per worker. Each order has its own single notification attempt.
No notification is attempted when opt-in is absent. The payload contains only the bound submitted
order ID, selected-line count and bounded labels/quantities/units/priorities. Unselected catalog
rows, stock/evidence fields and secrets are excluded. The server never persists the subscription.
Page load checks for a worker update, including for an already-enabled browser. The worker validates
the schema and uses a generic fallback for malformed/legacy pushes; it never follows supplied URLs.
An existing recorded human order is required, with one attempted send per worker/order; duplicates
return its existing result. Timeout means unconfirmed and is not retried automatically.

The demo's closing/order records remain worker-local and clear on restart. Separate Vercel workers
may not share the order, so this is not a production-reliable notification system. A missing order
is rejected rather than sending without a binding. Use the local one-worker demo for predictable
workflow checks; actual phone testing requires HTTPS accessible to that phone. Do not disable HTTPS
or authentication to work around browser restrictions. Scheduling, durable queues and storage would
require separately scoped work; there is no 6 AM send or actual purchase order.

## Original implementation plan and handoff (historical)

The generic-only payload requirement below is superseded by the approved follow-up above;
the original implementation record is preserved. Pairing and delivery acknowledgements remain separate.

Context: closing.py records a human-reviewed simulated order and preview-only notices; no push
connection existed. Approach: extend the existing FastAPI/plain-JavaScript stack with opt-in,
encrypted Web Push. Rejected alternative: paid SMS integration, which the user replaced with push.
Steps in order: server adapter/config and key utility; human-only order-bound route; browser
controls/worker; synthetic encryption/API/browser checks; documentation, two SECURITY rounds and
read-only REVIEWER. No independent agent work is needed for this tightly connected feature.

Acceptance: no automatic prompt; clear enable/disable/denied/offline feedback; existing order only;
fixed minimal payload; Chrome endpoint/key validation; no redirects; bounded IO; one attempt per
worker/order; acceptance distinct from delivery; no inventory mutation or Agent send permission.
Out of scope: SMS, pairing, scheduled delivery, Supabase, purchases and durable notification state.
Unknowns: actual Android display/tap and deployed matching keys. Recommended verification is the
HTTPS phone test above after deployment; both remain unverified until observed. Implementation
approval was supplied by the user's yes; preview/commit/push/merge gates remain separate.

ARCHIVIST baseline: clean feature/order-workflow-demo at
880f05a3b6ae99fbed6b1e20c8873342812e8d86, matching origin, PR #30 open and mergeable. Tracked source
is recoverable from that Git tree; this change adds no database migration or durable order data.
Local sender-key loss requires a new key and new browser subscriptions; never export it into source
archives. No isolated Git restore or remote key backup was performed: RESTORE NOT VERIFIED.

Dependency record: project-local Python 3.13 virtual environment; added http-ece 1.2.1, py-vapid
1.9.6, cryptography 50.0.2, cffi 2.1.1 and pycparser 3.11 from PyPI. Existing dependency pins were
preserved; both web and Vercel manifests receive identical pins. No global runtime or account
installation. Local generated configuration is excluded from source line scans because it contains
a secret; only its ignored status and configuration usability are checked without displaying values.

UX: the primary user is the authorized demo reviewer on Android. Explicit opt-in and adjacent
feedback support visible status and user control; native permission prompts preserve platform
conventions. Buttons use the existing layout, keyboard behavior and live status region. Declining
notifications leaves the order form available. These choices use [Laws of UX](https://lawsofux.com/)
as review prompts, not user research. No new entry fields or field-validation summary are needed.
