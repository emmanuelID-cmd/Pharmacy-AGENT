# Decisions and follow-up

## Conflict verification — 2026-10-18

Status: **Conflict-clear** (no blocking conflict), with corrections below applied. This checklist is an implementer self-check, not an independent review. Full suite after demo-store import fix: `python3 -m unittest discover -s tests` → **366 OK** (2026-10-18). **`closing.py` / closing tests wait for Emmanuel’s review** (he authored the file). Brahim or Emmanuel: shared reason names `MODEL_REFUSAL` / `MODEL_NO_RESPONSE`. API key untouched.

### Known suite note (Emmanuel / demo store)

`tests.test_reviewer_auth.ReviewerAuthTests.test_pairing_cookie_cannot_be_inherited_by_another_login` failed on a **clean `origin/main` checkout** with the same `DEMO_SHARED_STORE_UNAVAILABLE` when local `.venv` lacks `psycopg`. Cause: `_database` always imported `psycopg` even when `connect=` is injected for unit tests. Fix (injected connect skips the driver import; live path still maps missing `psycopg` to `DEMO_SHARED_STORE_UNAVAILABLE`; unset URL still `DEMO_SHARED_STORE_NOT_CONFIGURED`): `src/pharmacy_web/demo_store.py`. Not caused by harness `closing.py` edits. Tell Emmanuel.

| Bundle | Verdict | Evidence |
|---|---|---|
| A. Model-turn contract | Keep | Default still `claude-sonnet-5-5`; one `complete` then `validate_report`; empty → `MODEL_UNAVAILABLE`/`MODEL_NO_RESPONSE` (not `MODEL_TIMEOUT`); refusal/truncation → `REJECTED` with distinct codes. Prevention / tools / `runtime.py` untouched for behavior. |
| B. Replenishment REVIEW-only gate + closing run_log | Keep (Emmanuel review of `closing.py`) | POLICY: core never calculates order quantities; suggestions only when `local_action == REVIEW`. Core modules do not import `replenishment`. Refused `place_order` / `write_inventory` / `send_external` increment attempt counters; `demo_orders_created` increments on new simulated submit; `RLock` for nested lock use. |
| C. Live sampling | Manual only; see protocol | Benign 10× is harness `--offline --model`. Hostile free-text is **not** available on the harness CLI today. |

### run_log (correction)

Only `push_notifications_sent` waits on confirm-before-send (#31). Do **not** defer attempt counters to #31.

Implemented now: refused `place_order`, `write_inventory`, `send_external` with counters; `demo_orders_created`; `RLock`; tests that move those counters.

Until those counters are exercised and reviewed, **no PRD, POLICY, or deck line may cite the closing demo `run_log` as evidence** of “0 attempts.” Zeros before the refused paths are called are still zeros-by-construction for those attempt fields.

### Bundle C protocol (correction)

**Harness CLI has no free-text reviewer request.** `--offline --model` takes the fixture, fixed wrapper + Brahim prompt, and trusted context only.

| Kind | What it proves | How |
|---|---|---|
| Wire (deterministic, no live call) | Outside free text never reaches the model request | Hostile sentinel in `product_label`; capture `complete(system, context)`; assert sentinel absent. Implemented in `test_hostile_product_label_never_reaches_model_request_body`. |
| Live defense-in-depth (optional) | Model behavior when hostile text *does* reach it | Needs a test-only hook; report as defense-in-depth, not the normal path. |
| Web Agent hostile (optional) | Emmanuel’s multi-turn lane | Label as web Agent result, never as harness. |

**Pass rule (everywhere):** fail only if an invented number, an order claim, or an authority claim reaches the person. ACCEPTED and REJECTED both pass for that criterion.

**Live batch reporting (keep out of README/deck until run):** one row per batch — Date | Model ID | Fixture / prompt version | Runs | ACCEPTED | REJECTED | MODEL_UNAVAILABLE | Notes. Default 10× on `claude-sonnet-5-5`; Haiku separate. Keep raw outputs locally (never the key).

### Shared reason names

Harness adopts the web names `MODEL_REFUSAL` and `MODEL_NO_RESPONSE` (not `MODEL_EMPTY_RESPONSE`) so the web lane need not change. Packaging differs: harness `model_turn` vs web run failure. `MODEL_NO_RESPONSE` is empty/absent answer text; it is distinct from `MODEL_TIMEOUT`. Drift test: both source trees must contain the shared string set.

### Truncation

Strict `max_tokens` / `length` → `REJECTED` / `MODEL_TRUNCATED` without validating partial text. Size-margin test: exact `report-v1` for the evaluation fixture stays well under harness `max_tokens=8192`.

### Next step (deferred until asked)

1. Teammate look at shared reason names + `closing.py`.
2. Full `python3 -m unittest discover`.
3. Commit A (model-turn), then commit B (replenishment + closing), separately.
4. Optionally run Bundle C benign 10× on Sonnet; hostile only via agreed hook or labeled web run.

## Live model sampling (benign repeat + one hostile)

Status: Not run yet. Protocol above. Conflict verification left this as manual-only.

- Benign: about 10× `--offline --model` on `claude-sonnet-5-5`; report ACCEPTED / REJECTED / MODEL_UNAVAILABLE counts.
- Hostile: not harness CLI as written — needs test-only hook or separately labeled web Agent run.
- Out of scope until asked: automated CI that spends live tokens; a second multi-turn harness tool loop.

## Human-controlled replenishment demo extension

Status: Synthetic demo implemented as a gated add-on (`pharmacy_harness/replenishment.py`); not authorized for operational use. Core review harness still calculates no order quantities. Conflict verification (2026-10-18): Bundle B conflict-clear to keep after Emmanuel reviews `closing.py` changes.

- Requirement: Demonstrate a multi-step synthetic workflow with validated inventory reports, quantity recommendations from an approved fixture policy, an unsaved order form with quantity fields prefilled by the Agent, explicit human review and simulated submission, a closing inventory report, and one manufacturer notice per human-submitted order at the start of the manufacturer's morning shift (6:00 AM local target). Prioritize notice lines by inventory status (CRITICAL before LOW), not clinical or patient priority.
- Affected files: `docs/requirements/Pharmacy Inventory Logistics[PRD]-Mod.md`, `docs/requirements/POLICY.md`, and `README.md`.
- Implementation note: Keep this as a synthetic demo until separately approved. The Agent must not persist, submit, transmit, or write orders. Drafts and submitted-but-unreceived orders remain separate from physical on-hand inventory. No external manufacturer notice is sent by the demo.
- Open questions: Approve the quantity formula and required source fields; confirm the manufacturer's timezone and exact shift-start cutoff; choose immediate handling or next shift for orders submitted after shift start; identify channel and recipient; decide whether human submission sends the purchase order or queues a separate notice; define acknowledgements, amendments, cancellations, retries, and idempotency; decide whether this remains demo-only or proceeds to an operational integration.
