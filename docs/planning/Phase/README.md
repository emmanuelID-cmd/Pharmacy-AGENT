# Phase planning index

One common parent contains each complete phase: `docs/planning/Phase/Phase<n>/`. Sub-phase folders belong inside their parent, for example `Phase6/Phase6.1/PLAN.md`.

## Phase records

| Phase | Plan | Status |
|---|---|---|
| 1 | [Label contract and hidden-character validation](Phase1/PLAN.md) | Reconstructed historical record |
| 2 | [Safe context gate](Phase2/PLAN.md) | Reconstructed historical record |
| 3 | [Detection pattern catalogue](Phase3/PLAN.md) | Reconstructed historical record |
| 4 | [Synthetic evaluation](Phase4/PLAN.md) | Reconstructed historical record |
| 5 | [Handoff and security review](Phase5/PLAN.md) | Reconstructed historical record |
| 6 | [Approved parent plan](Phase6/PHASE-6-PLAN.md) | Completed standalone prevention build |

Missing older plans are explicitly reconstructed from verified commits. They do not replace the approved parent plan or invent historical authorization.

## Phase 6 sub-phases

| Sub-phase | Plan | Status |
|---|---|---|
| 6.1 | [Contracts and coverage](Phase6/Phase6.1/PLAN.md) | Verified completed sub-phase record |
| 6.2 | [Detection and evasions](Phase6/Phase6.2/PLAN.md) | Verified completed sub-phase record |
| 6.3 | [Context isolation](Phase6/Phase6.3/PLAN.md) | Verified completed sub-phase record |
| 6.4 | [Action and output guards](Phase6/Phase6.4/PLAN.md) | Verified completed sub-phase record |
| 6.5 | [Local visual tester](Phase6/Phase6.5/PLAN.md) | Verified completed sub-phase record |
| 6.6 | [Qualification and handoff](Phase6/Phase6.6/PLAN.md) | Verified completed sub-phase record |

## Rerouted existing evidence

| Previous repository path | Current location |
|---|---|
| `docs/planning/INJECTION-PREVENTION-HANDOFF.md` | [INJECTION-PREVENTION-HANDOFF.md](Phase5/INJECTION-PREVENTION-HANDOFF.md) |
| `docs/planning/INJECTION-PREVENTION-REVIEW.md` | [INJECTION-PREVENTION-REVIEW.md](Phase5/INJECTION-PREVENTION-REVIEW.md) |
| `docs/planning/INJECTION-PREVENTION-CHANGES.html` | [INJECTION-PREVENTION-CHANGES.html](Phase5/INJECTION-PREVENTION-CHANGES.html) |
| `docs/planning/PHASE-6-PLAN.md` | [PHASE-6-PLAN.md](Phase6/PHASE-6-PLAN.md) |
| `docs/planning/PHASE-6-HANDOFF.md` | [PHASE-6-HANDOFF.md](Phase6/PHASE-6-HANDOFF.md) |
| `docs/planning/PHASE-6-REVIEW.md` | [PHASE-6-REVIEW.md](Phase6/PHASE-6-REVIEW.md) |
| `docs/planning/PHASE-6-SECURITY.md` | [PHASE-6-SECURITY.md](Phase6/PHASE-6-SECURITY.md) |
| `docs/planning/PHASE-6-CHANGES.html` | [PHASE-6-CHANGES.html](Phase6/PHASE-6-CHANGES.html) |

The two historical HTML comparisons retain their original bytes. Literal snapshot paths and historical line references describe their original baselines; use this mapping to locate moved files. Active Markdown links follow current locations. The three earlier prevention evidence files live in Phase5 and cover historical Phases 1-5.

## Scope

Keep foundation [plan](../PLAN.md), [review](../REVIEW.md) and [setup plan](../SETUP-PLAN.md) at their existing locations. The original draft, policy, executable package and tests are unchanged by this folder action. External AGENTS is a separate repository/task and is never Phase 7.

## Verification

[Organization review and exact changed lines](ORGANIZATION-REVIEW.md).
