# Phase 8 Integration Handoff

One guarded model turn on top of the Phase 7 deterministic run. Read [plan](PHASE-8-PLAN.md).

## Ownership

| Member | Part | Role in this turn |
|---|---|---|
| Kerrian Gordon | Harness | Wires one `complete` call after trusted assembly and applies `validate_report` |
| Emmanuel De Jesus | Injection Risk Prevention | `expected_report` / `validate_report` already on main |
| Brahim Maouloud | Agent Instructions and Tooling | `SYSTEM_PROMPT` already on main |

## How to run

```powershell
python3 -m src.pharmacy_harness --offline --model-copy
python3 -m src.pharmacy_harness --offline --model
```

`--model-copy` is not a language model. `--model` is one live turn: `PHARMACY_MODEL_URL` (OpenAI-compatible chat completions) or `ANTHROPIC_API_KEY` (Messages API with `x-api-key`, default `claude-sonnet-5-5`). It uses the 20-row evaluation fixture. The harness prepends “tools already ran / JSON only” before Brahim's prompt; `pharmacy_tools` is not edited. Invented quantities never appear on `safety_report`.

Model turn states: `ACCEPTED` (exact `report-v1`); `REJECTED` with `OUTPUT_EVIDENCE_MISMATCH` (returned answer failed validation), `MODEL_REFUSAL`, or `MODEL_TRUNCATED` (provider stopped at token limit — partial text is not validated); `MODEL_UNAVAILABLE` (auth, timeout, transport, response-shape, or empty/`None` reply — no answer to judge). Empty/`None` uses shared reason `MODEL_NO_RESPONSE`, which is not `MODEL_TIMEOUT`. Reason code names `MODEL_REFUSAL` and `MODEL_NO_RESPONSE` match the web Agent; packaging differs (harness `model_turn` vs web run failure). Do not treat `MODEL_UNAVAILABLE` as evidence the guard blocked an invented number, order claim, or authority claim.

## Validation

Copying complete is ACCEPTED. A completer that sets `usable_quantity=999` or `order_placed=true` is REJECTED; human Case 1 remains 80 units / 6.22 days. Prose is REJECTED. Auth/timeouts are `MODEL_UNAVAILABLE`, not `REJECTED`. Unit tests stub the provider. Historical live proof (2026-10-15): a Console key with `claude-haiku-5-5` returned **ACCEPTED** (exact `report-v1`). Current live proof (2026-10-16): `claude-sonnet-5-5` with the local Anthropic credential returned **ACCEPTED** (exact `report-v1`) via `--offline --model`; the offline flag applies to the recorded FDA payload, not the model call. The overall synthetic run remained `MANUAL_REVIEW` because the fixture contains seeded invalid/unknown rows. The current default is `claude-sonnet-5-5`. The Anthropic Messages adapter omits `temperature` to avoid model-specific validation errors. A confirmed gateway via `PHARMACY_MODEL_URL` remains an alternate path. This one-turn guarded path is the finished harness model integration; a separate multi-turn tool loop lives in the web Agent, not a second harness build.

Note on the October 15 Haiku line: that was a real `--offline --model` Messages call to `api.anthropic.com` after a revoked/invalid key was replaced and `temperature` was omitted from the request body (HTTP 400 had previously been mapped to transport failure). It is not `--model-copy`. `claude-haiku-5-5` is the Claude Platform model id for Haiku 5.5 (released 2026-10-07) and was the id that run used. Current default remains `claude-sonnet-5-5`. Each dated ACCEPTED sample was on benign harness context (no untrusted free text): it proves wire + exact copy, not live behavior under hostile input.
