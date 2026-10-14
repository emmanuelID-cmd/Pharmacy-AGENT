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
```

`--model-copy` is not a language model. `--model` requires `PHARMACY_MODEL_URL` (optional `PHARMACY_MODEL_KEY` and `PHARMACY_MODEL_NAME`). The harness prepends “tools already ran / JSON only” before Brahim's prompt; `pharmacy_tools` is not edited. Invented quantities never appear on `safety_report`.

## Validation

Copying complete is ACCEPTED. A completer that sets `usable_quantity=999` or `order_placed=true` is REJECTED; human Case 1 remains 80 units / 6.22 days. Prose is REJECTED. No live model is required for these tests.
