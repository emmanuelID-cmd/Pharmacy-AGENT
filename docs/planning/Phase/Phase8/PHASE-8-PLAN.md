# Phase 8 - One guarded model turn

Authorized as Kerrian Gordon's harness follow-up after Phase 7. Phases 1–7 are not renumbered. External AGENTS remains a separate repository.

## Objective

After trusted tools, validation, and `TrustedFact` assembly, call a model once. The only accepted answer is exact `report-v1`. Invented numbers, prose, and API failures are rejected through `validate_report` and replaced with deterministic `MANUAL_REVIEW`. Do not train a model.

## Work

| Piece | Behavior |
|---|---|
| Turn | One `complete(system_prompt, context)` call. No tool loop, no retry |
| Prompt | Harness wrapper (tools already ran; JSON only) plus Brahim's `SYSTEM_PROMPT` and the trusted `prevention-v1` context JSON. No raw tool payload |
| Guard | Emmanuel's `validate_report`. Copy matches `expected_report`; a returned mismatch is `REJECTED` / `OUTPUT_EVIDENCE_MISMATCH`. Auth, timeout, and transport failures are `MODEL_UNAVAILABLE` |
| CLI | `--model-copy` proves the wire without an LLM; `--model` is one live turn (`PHARMACY_MODEL_URL` or `ANTHROPIC_API_KEY`) on the 20-row fixture |
| Human report | Local days of supply stay harness-computed even when the model is rejected |

## Out of scope

Training a model, FastAPI UI, database, live CVS, edits to `src/injection_prevention` or `src/pharmacy_tools` besides documentation status.
