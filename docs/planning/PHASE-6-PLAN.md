# Phase 6 - Complete Standalone Injection Prevention

Approved October 8, 2026. Continues historical Phases 1-5; do not renumber them. Execute every sub-phase continuously, test locally and commit completed sub-phases only. No Pharmacy push or merge is authorized. External AGENTS is a separate repository and task.

| Sub-phase | Objective | Work |
|---|---|---|
| 6.1 | Contracts and coverage | Source/field contracts, bounded intake, safe failures and risk-to-test matrix |
| 6.2 | Detection and evasions | Paraphrases, fake authority, disguises, selected multilingual variants and counterexamples |
| 6.3 | Context isolation | Controlled assembly; omit untrusted free text; prevent reinsertion and forged trust |
| 6.4 | Action/output guards | Importable permission/output checks with synthetic evidence and simulated execution |
| 6.5 | Local visual tester | Real Python results, visible Unicode and safe responsive display |
| 6.6 | Qualification/handoff | Full regression, SECURITY Round 1/remediation/Round 2, REVIEWER, documentation and imports |

## Approved risk-to-test matrix

| Family | Required checks |
|---|---|
| Hidden/control | Zero-width, bidi, invisible marks, controls and combinations |
| Legitimate Unicode | Accents, combining sequences, scripts and punctuation |
| Paraphrase | Warning suppression, report redirection, keyword-free commands |
| Fake authority | Claimed approval, exceptions, role changes |
| Obfuscation | Spacing, misspellings, lookalikes, encoded attempts |
| Multilingual | Selected attacks plus benign names |
| Other sources | Stored inventory, FDA/tool fields, scoped requests, malformed records |
| Split/persistent | Fields, records and simulated turns |
| Forged trust | Supplied flags, fabricated objects, nesting, raw reinsertion |
| Actions/disclosure | Orders/writes, SQL/commands, destinations and secrets |
| Output | Altered facts, omitted warnings, classes and false action claims |
| Bounds/failures | Size/depth/repetition, missing evidence, exhausted budget |
| Media | Unsupported image/audio/OCR-shaped intake |
| Rendering | HTML/script-shaped text and misleading visible characters |

## Acceptance

Known demonstrated instruction cases must not ACCEPT. Distinguish detection misses from containment, false positives and untested behavior. Omit unnecessary external text even when detection misses. External content cannot approve policies, validate itself or grant authority. Required uncertainty becomes MANUAL_REVIEW; unaffected valid evidence remains usable. Supported legitimate Unicode passes its field contract. Deny forbidden simulated execution and reject output that changes verified evidence or omits required warnings. The tester uses real imported controls, not duplicate JavaScript logic. Every matrix family gets explicit fixtures/behavior tests. Finish both SECURITY rounds and final REVIEWER with no blockers. Import from a clean process without the tester. Update documentation only after clearance; preserve the original draft and unrelated work.

## Responsibilities

| Member | Approved part |
|---|---|
| Emmanuel De Jesus | Injection Risk Prevention |
| Brahim Maouloud | Agent Instructions and Tooling |
| Kerrian Gordan | Harness |

Do not infer teammate implementation progress. Accepted assumptions: strict versioned synthetic contracts and labelled synthetic catalog while live catalog/final harness schemas are unavailable. No clinical reasoning, patient data, inventory calculations, database/staff-write implementation or live API integration. Security-facing reusable guards are included; actual harness integration remains a later test boundary.

## Runtime and integration

Keep Python 3.13 standard-library conventions and the existing package/tests. Prototype intake defaults: UTF-8 JSON <=64 KiB, depth <=6, <=2048 nodes, <=20 rows, <=1000 characters per generic field, <=4096 total value-text characters. Label limit remains 120. These are explicit local-prototype assumptions, not operational pharmacy policy. Limits fail closed without silent truncation. The harness supplies validated facts independently; the prevention package never derives quantity from descriptions.

Recovery baseline: HEAD 0f9c657. Existing Mod edits and untracked skills remain preserved outside this build's staging. Original draft and POLICY.md hashes are checked before final handoff. Current scope is standalone local enforcement, not universal detection or production readiness.

## Execution evidence

All sub-phases 6.1–6.6 are complete. The independent final read-only REVIEWER approved the complete implementation and documentation with no findings. Sub-phases 6.1–6.5 are committed locally; this final qualification/handoff is the authorized 6.6 local commit. SECURITY ran two sequential rounds; seven findings resolved, including scoped dispatch snapshots and required identity result withholding. Current evidence: 66 behavior methods;85 label fixtures,55 unsafe detected,30 benign accepted,0 fixture misses/false positives,85 text exclusions. Browser checks cover desktop/mobile, Unicode, denied execution, rejected report claims, JSON duplicates and stale in-flight response handling. Clean package import passed without starting the tester. See PHASE-6-HANDOFF.md and PHASE-6-SECURITY.md for evidence and untested integration limits.
