# Approved web interface contract

Approved October 13, 2026 after the PLANNER mockup. User selected the newest Haiku;
the authenticated Models API lists active `claude-haiku-5-5` (released October 7).
The root remains Pharmacy-Agent-Role on feature/pharmacy-agent-web-interface.

## Shared interface

Home is the canonical shell. Navigation order and proposed routes:
Home `/`, Agent `/agent`, Tools `/tools`, Harness `/harness`,
Injection Risk Test `/injection-risk-test`, Failure State `/failure-state`,
Demo `/demo`, Architecture `/architecture` (Steps-to-connect).
All pages use the same template, banner, footer, logo placeholder and tokens.
Each navigable view has a consistent top-left back control. No patient data,
orders, inventory writes, numerical reorder quantities or policy changes.

## Server/client contract

- Template context: `active_view`, `navigation` (key/label/path), `model`,
  `provider_configured`, `source_mode` (fixture), `store_id` (1618).
- GET `/api/status`: model, provider_configured, source_mode, store_id, read_only.
- POST `/api/review`: JSON `{request: string}`; 1-1000 Unicode code points,
  non-whitespace. Response: state, reason_code, report (harness-report-v1 or null),
  agent (model, model_called, output_accepted, turns, counts). User text stays
  outside model instructions/context; the fixed supported intent is inventory review.
- POST `/api/demo`: JSON `{}`; same envelope, state Demo. Existing harness runs
  the fixture with a declared October 7 example clock and stubbed FDA; no model.
- GET `/api/test-samples`: `samples` containing id/name/source, no credentials.
- POST `/api/test-input`: sample_id, optional request_text, output_change
  (none/alter_days/hide_warnings/claim_order). Executes the existing synthetic
  Python tester. Returns its detector/model_context/permission_guard/output_guard
  and limitations; never executes arbitrary tools or raw submitted facts.
- POST `/api/failure-preview`: scenario
  (timeout/key/malformed/store/empty/fda/offline); returns scenario/title/detail/
  recovery and simulated=true. This route illustrates recovery, not live faults.
- Errors contain fixed reason codes and safe messages, never raw provider errors.
- Agent states: Live, Manual Review, Temporarily Unavailable. Browser offline is
  labelled No Internet Access only when navigator.onLine indicates offline.

JSON bodies are bounded; all routes are protected in hosted mode. Local unauthenticated
development is loopback-only. Hosting requires configured reviewer credentials;
the browser receives no provider/database key. POST origins must match the request
origin when present; no permissive CORS. Model turns, reads, output and run time
are bounded. Stop waiting aborts the client wait; a server read can finish within
its independent limits. No unvalidated model prose is streamed to the user.

## Historical original build dependencies and boundaries

Frontend and Claude adapter may proceed independently after this contract;
endpoint integration depends on the adapter. Existing deterministic CLI/tests,
local tester, presentations and historical PRD/policy are preserved.
Supabase reader/schema are on a separate branch; this build does not merge them.
PR #13 (teammate FDA reporting) remains separate. No commit, push, merge or deploy
is authorized by the implementation approval. Review a running preview first.

Verification: form and route tests, scripted provider success/failure/denial,
all existing unittest/qualification checks, browser keyboard/mobile recovery,
exactly two sequential security rounds and a read-only final review.

## Integration fixture boundary

The web Agent uses the 150-product catalog fixture and ten-NDC FDA batches. Demo explicitly retains the original 20-row fixture. Each batch must contain distinct, context-bound identifiers that have not already been read. Requested identifiers are captured before IO; mismatched returned batch binding withholds FDA evidence. No database adapter is wired into either endpoint. Hosted migration and web deployment remain pending.

## Approved loop termination handling - October 13, 2026

- A provider `stop_reason` of `refusal` returns Manual Review / `MODEL_REFUSAL`,
  before examining or dispatching any tool blocks in that response. Refusal prose is omitted.
- `None` or an empty content-block list returns Manual Review / `MODEL_NO_RESPONSE`.
  Other malformed responses retain their existing validation reason codes.
- Unexpected exceptions from the provider call return Temporarily Unavailable /
  `MODEL_ERROR`. Only known fixed provider failure codes survive; unknown codes and
  raw exception details are excluded. Existing timeout/deadline behavior is preserved.
- Exhausted model turns return Manual Review / `MODEL_TURN_LIMIT`.
- Every terminal path stops further model/tool calls, leaves output unaccepted,
  and preserves independently verified partial facts under manual review when available.
  No refusal retry, new tool, database connection or budget increase is introduced.

## Approved 150-row Agent limits

Local default: 120 seconds overall, 90 seconds per model call, six model turns and
24 attempted reads. Fifteen ten-NDC FDA batches plus inventory cover 150 rows.
The provider receives copied shared tool schemas and pinned instructions; tool
decisions are capped at 4,096 output tokens, final output at 24,576. Final JSON
uses the fixed 150-row inventory limits and the unchanged exact report guard.
Hosted configuration loading retains a 50-second run and 45-second model cap
within the prepared 60-second host budget; full catalog completion on that host
requires separate deployment validation. Refusal/no-response handling is preserved.

Tests inject scripted providers and FDA responses. Authorized live evaluation uses
the configured model and fixed FDA endpoint, records sanitized outcomes separately,
and makes at most two end-to-end runs without automatic model retries. A frozen
October 7 evaluation clock is explicitly labeled; normal Agent reviews use current
time and preserve stale-snapshot review requirements.
