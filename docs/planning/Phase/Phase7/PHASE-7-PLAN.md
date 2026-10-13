# Phase 7 - Deterministic pharmacy harness

Authorized as Kerrian Gordan's harness lane after teammate tools and prevention controls were already on `main`. Phases 1–6 are not renumbered. External AGENTS remains a separate repository and is not this phase.

## Objective

Build the trusted run that actually calls `read_store_inventory` and `get_fda_shortage_context` through `execute_guarded`, independently validates evidence, calculates days of supply under POLICY.md (`SYNTHETIC-v0`), constructs `TrustedFact` objects in harness code, and emits a human PRD report plus the prevention `report-v1` safety copy.

## Work

| Piece | Behavior |
|---|---|
| Validation | Store 1618, synthetic label, policy version, segmented NDC, dispensing unit, snapshot 0–24 hours in America/New_York, 14 complete usage days ending the last completed NY day |
| Calculation | Average = 14-day total / 14; days of supply = usable / positive average; unrounded class; two-decimal display |
| Facts | `ItemResult` holds POLICY.md branches including CRITICAL stock with unknown duration; `TrustedFact` maps that case to UNKNOWN |
| Run | One `RunBudget`; inventory first with callback capture; FDA only for accepted NDCs; tests stub HTTP; CLI uses the live adapter |
| Report | Every source row accounted for; critical then low then above-threshold after manual-review rows; FDA cannot change local class |

## Acceptance

- Eval Card Case 1: item-001 displays 6.22 days, ABOVE_THRESHOLD / MAINTAIN, plus FDA external-risk REVIEW when Current/Unavailable
- Eval Card Case 2: item-002 UNKNOWN / MANUAL_REVIEW; duration unavailable, never infinity
- Case 3-shaped rows: missing stock and 13-day usage withhold estimates; FDA timeout is UNAVAILABLE, not no shortage; no order claim
- Fixture boundary rows: exactly 2.00 and 5.00 days, zero stock, negative stock, incomplete usage
- Wrong store, unreadable source, and a stale clock never become healthy stock
- Full local unittest suite remains green
- No LLM, FastAPI, SQL, live CVS, or Mod-PRD per-item thresholds

## Out of scope

Language model loop, FastAPI UI, database, proposed SYNTHETIC-v1 item thresholds, ordering tools, and edits to `src/injection_prevention` or `src/pharmacy_tools` besides documentation status.
