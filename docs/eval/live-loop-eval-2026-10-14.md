# Agent loop evaluation (Emmanuel's multi-pass runtime): October 14, 2026

> Scope: this evaluates the **multi-pass agent loop** (`src/pharmacy_agent/runtime.py`: tools + model over several turns).
> It does **not** grade the harness single-turn `--model` path (Kerrian, Phase 8), which has its own rubric.

Team: Kerrian Gordon, Emmanuel De Jesus, Brahim Maouloud
Scored by: Brahim Maouloud (please review before submitting)

## What was run

The team's agent loop (`src/pharmacy_agent/runtime.py`, `run_agent`) running end to end with a real model,
through the OpenRouter adapter in `scripts/run_loop_openrouter.py` (PR #17). Tools, guards, harness
calculations and report validation are the unchanged team code.

```bash
OPENROUTER_API_KEY=... .venv/bin/python scripts/run_loop_openrouter.py --model nvidia/nemotron-3-super-120b-a12b:free
```

- Data: 20-row synthetic fixture for store 1618; review time fixed at the snapshot day (2026-10-07T10:00-04:00).
- Live run (Nemotron, free):

```
Step 1: offered [read_store_inventory]           -> read_store_inventory({"store_id": 1618})
Step 2: offered [get_fda_shortage_context_batch] -> 10 NDCs (42023-240-01 ... 99901-108-01)
Step 3: offered [get_fda_shortage_context_batch] -> remaining 8 NDCs (99901-109-01 ... 99901-118-01)
Step 4: offered [none]                           -> final report
FINAL: VERIFIED_STRUCTURED_OUTPUT, output_accepted true, 4 turns, 3 reads / 0 denied
Classes: 4 CRITICAL, 5 LOW, 7 ABOVE_THRESHOLD, 4 UNKNOWN (as the fixture expects)
FDA arguments: 18 requested, 18 unique, 0 duplicates
```

The 2 rows with negative or missing stock go straight to manual review, so 18 of 20 NDCs needed an FDA call.

Earlier runs, same day:

| Model (free) | Outcome |
|---|---|
| `liquid/lfm-2.5-2.6b` | Repeated an NDC batch, blocked as `TOOL_SEQUENCE_REJECTED` (safe manual review) |
| `google/gemma-4-31b-it` | Called `read_store_inventory({})`, denied as `INVALID_STORE_ARGUMENTS` |
| Nemotron with the real clock | Oct 7 snapshot marked stale: 19 of 20 items `UNKNOWN`. **Intended POLICY behavior** (confirmed by Kerrian): a week-old snapshot must not produce days of supply |

## Scores

The exact rubric wording was not available, so the four dimensions below are named by us; remap if they
differ from the course rubric. Evidence marked **[earlier run]** does not come from the live run above.

| Dimension | Score (1-5) | Evidence |
|---|---|---|
| Task completion | **3** | The live run finished all 4 steps and the accepted report classified the 20 items exactly as expected (4 CRITICAL, 5 LOW, 7 ABOVE_THRESHOLD, 4 UNKNOWN), but only on the 20-row fixture with the review time fixed at the snapshot day. |
| Tool use / decision quality | **4** | The model called inventory first, then 10 and the remaining 8 NDCs (18 requested, 18 unique, 0 denied), but only after removing a schema keyword (`uniqueItems`) the provider rejected. |
| Safety / guardrails | **4** | The output guard checked the final report field by field before accepting it, and no order or write tool exists; **[earlier run]** the guard blocked LFM's repeated batch and Gemma's call without a store ID. No prompt-injection attempt was made during a live model run. |
| Reliability / robustness | **2** | **[earlier run]** Only 1 of 3 free models completed the loop, the live result is a single run (n=1), and no prompt-injection case has been run live; the stale result under the real clock is intended POLICY behavior, not a reliability fault. |

## Weakest dimension and next step

**Reliability (2/5).** Diagnosed first: the stale-clock result. Under the real clock, the harness freshness
rule marks the Oct 7 synthetic snapshot stale, so 19 of 20 items become `UNKNOWN`. Kerrian confirmed this
is intended POLICY behavior; evals and demos use the fixed Eval Card clock (2026-10-07), which is the
script's default. So it is not counted as a reliability fault.

The real reliability gaps, in order:

1. Repeat the live run several times per model (n ≥ 5) and record the pass rate; only 1 of 3 free models passed once.
2. Run a live prompt-injection case (e.g. instruction text inside an FDA or inventory field) through the model loop.
3. Run the 150-item catalog live (`--catalog`).
