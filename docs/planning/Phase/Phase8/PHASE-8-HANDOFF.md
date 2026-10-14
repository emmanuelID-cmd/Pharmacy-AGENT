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

`--model-copy` is not a language model. `--model` is one live turn: `PHARMACY_MODEL_URL` (OpenAI-compatible chat completions) or `ANTHROPIC_API_KEY` (Messages API with `x-api-key`, default `claude-haiku-5-5` per Anthropic docs Oct 2026). It uses the 20-row evaluation fixture. The harness prepends “tools already ran / JSON only” before Brahim's prompt; `pharmacy_tools` is not edited. Invented quantities never appear on `safety_report`.

Model turn states: `ACCEPTED` (exact `report-v1`), `REJECTED` / `OUTPUT_EVIDENCE_MISMATCH` (a returned answer failed validation), `MODEL_UNAVAILABLE` (auth, timeout, transport, or response-shape failure — the model never produced a usable answer). Do not treat `MODEL_UNAVAILABLE` as evidence the guard blocked invented numbers.

## Validation

Copying complete is ACCEPTED. A completer that sets `usable_quantity=999` or `order_placed=true` is REJECTED; human Case 1 remains 80 units / 6.22 days. Prose is REJECTED. Auth/timeouts are `MODEL_UNAVAILABLE`, not `REJECTED`. Unit tests stub the provider. A live Console API key (`sk-ant-api…`) against `api.anthropic.com` (or a confirmed gateway URL via `PHARMACY_MODEL_URL`) is still required before claiming a live model copied or failed validation. Until then, how a language model reacts to injected text remains unproven.
