# Phase 7 Integration Handoff

Deterministic harness for one synthetic store. Read [plan](PHASE-7-PLAN.md). Original draft PRD and POLICY.md stay authoritative; proposed item-policy changes remain deferred. No model, database, or live CVS inventory.

## Ownership

| Member | Part | Verified contribution/status |
|---|---|---|
| Emmanuel De Jesus | Injection Risk Prevention | Standalone detection, context/action/output guards, synthetic local tester and qualification implemented in Phase 6 |
| Brahim Maouloud | Agent Instructions and Tooling | Read-only inventory reader, openFDA adapter, system prompt and warning display merged on main (PRs #5–#8) |
| Kerrian Gordon | Harness | Deterministic guarded run, POLICY.md calculations, TrustedFact construction and PRD report implemented in Phase 7 |

## How to run

From the repository root. The dated fixture snapshot is `2026-10-07T09:00:00-04:00`; freeze the clock or the snapshot is stale:

```powershell
python3 -m unittest discover -s tests -q
python3 -m src.pharmacy_harness --offline
python3 -m src.pharmacy_harness --offline --model-copy
python3 -m src.pharmacy_harness --offline --json
```

The CLI defaults to `2026-10-07T10:00:00-04:00` so the dated fixture is fresh. `--now` uses the current clock (the snapshot will be stale). `--offline` injects the recorded Case 1 FDA payload and does not call openFDA. `--model-copy` runs one guarded model turn without an LLM; `--model` requires `PHARMACY_MODEL_URL`. Omit `--offline` for a live read-only openFDA request. `--json` prints `harness-report-v1`. Unit tests inject `fda_http_get` and do not use the network.

## Integration

1. `execute_guarded` inventory with a callback that keeps the JSON (`execute_guarded` returns only a safe assessment).
2. Harness validates identity, units, freshness and the 14-day window, then calculates days of supply.
3. `TrustedFact` objects are constructed in harness code and passed to `assemble_context`.
4. `execute_guarded` FDA for each accepted package NDC on the same `RunBudget`.
5. Human report lists every input row and every exact-match FDA record. Conflicting FDA records are `NEEDS_REVIEW`; they never change local class. `report-v1` is the prevention safety copy. `order_placed` and `inventory_changed` stay false.

TrustedFact cannot store CRITICAL with a missing duration. A verified zero-stock fact with no usage basis stays CRITICAL on the human report and maps to UNKNOWN in prevention context.

## Validation

Harness tests cover snapshot freshness, POLICY.md branches on the 20-row fixture, guarded dispatch, budget stop, Eval Card Cases 1–2, Case 3-shaped missing stock / incomplete window / FDA timeout, output-guard fallback on a tampered `report-v1`, Decimal exact-2/exact-5 boundaries, source vs row isolation, shared-NDC reuse, the human/`report-v1` invariant, multi-record FDA agreement versus conflict/`NEEDS_REVIEW`, PARTIAL/malformed/package-mismatch survival through `run_review`, a Case 2 same-NDC overlay, and the manager-table CLI. Run the full unittest suite before handoff.

These evals test harness arithmetic and prevention guards. They do not test how a language model reacts to injected text. A future model whose report must match `expected_report` exactly adds no independent judgment. Live FDA provenance, database grants, and operational pharmacy policy remain untested.

## Approved guard follow-up — October 13, 2026

- A captured FDA callback result is usable only after its dispatcher completes. Deadline and source-contract failures replace it with UNAVAILABLE; deadline/budget exhaustion stops further reads. Verified local calculations remain unchanged.
- Tester error responses are flushed and half-closed before draining rejected request bytes. Cleanup is bounded to 65,537 bytes and one second; rejected bodies never enter JSON evaluation. Content-type, origin, route and malformed-request denials are preserved.
- Windows startup needs the IANA timezone data in requirements-harness.txt; see the README virtual-environment commands. No full application framework was adopted.
- Review first reproduced late/invalid FDA-result use and the Windows connection abort. After remediation, all 141 discovered methods and all 85 qualification fixtures passed. Three targeted Tester reruns passed 9/9 each, including stalled-body cleanup and headerless parse failures.
- These checks use synthetic local inputs and stubbed FDA HTTP. They do not prove universal injection prevention, a model loop, database integration or operational pharmacy readiness. Database policy-write work remains deferred.
