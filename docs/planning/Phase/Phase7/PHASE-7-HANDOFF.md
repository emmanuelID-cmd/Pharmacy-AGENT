# Phase 7 Integration Handoff

Deterministic harness for one synthetic store. Read [plan](PHASE-7-PLAN.md). Original draft PRD and POLICY.md stay authoritative; proposed item-policy changes remain deferred. No model, database, or live CVS inventory.

## Ownership

| Member | Part | Verified contribution/status |
|---|---|---|
| Emmanuel De Jesus | Injection Risk Prevention | Standalone detection, context/action/output guards, synthetic local tester and qualification implemented in Phase 6 |
| Brahim Maouloud | Agent Instructions and Tooling | Read-only inventory reader, openFDA adapter, system prompt and warning display merged on main (PRs #5–#8) |
| Kerrian Gordan | Harness | Deterministic guarded run, POLICY.md calculations, TrustedFact construction and PRD report implemented in Phase 7 |

## How to run

From the repository root. The dated fixture snapshot is `2026-10-07T09:00:00-04:00`; freeze the clock or the snapshot is stale:

```powershell
python3 -m unittest discover -s tests -q
python3 -m src.pharmacy_harness --run-at 2026-10-07T10:00:00-04:00
```

`--run-at` is required for a fresh eval against the checked-in fixture. Omitting it uses the current time. The CLI calls the real openFDA shortages endpoint; unit tests inject `fda_http_get` and do not use the network.

## Integration

1. `execute_guarded` inventory with a callback that keeps the JSON (`execute_guarded` returns only a safe assessment).
2. Harness validates identity, units, freshness and the 14-day window, then calculates days of supply.
3. `TrustedFact` objects are constructed in harness code and passed to `assemble_context`.
4. `execute_guarded` FDA for each accepted package NDC on the same `RunBudget`.
5. Human report lists every input row. `report-v1` is the prevention safety copy. `order_placed` and `inventory_changed` stay false.

TrustedFact cannot store CRITICAL with a missing duration. A verified zero-stock fact with no usage basis stays CRITICAL on the human report and maps to UNKNOWN in prevention context.

## Validation

Harness tests cover snapshot freshness, POLICY.md branches on the 20-row fixture, guarded dispatch, budget stop, Eval Card Cases 1–2, Case 3-shaped missing stock / incomplete window / FDA timeout, and output-guard fallback on a tampered `report-v1`. Run the full unittest suite before handoff. These tests do not prove live FDA provenance, a language-model loop, database grants, or operational pharmacy policy.
