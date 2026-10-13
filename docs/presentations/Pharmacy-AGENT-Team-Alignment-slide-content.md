# Pharmacy-AGENT Team Alignment — slide content

Source snapshot: main 0b7c4bc, October 9, 2026. Presentation content prepared from the MOD PRD and current standalone implementation. PPTX/PDF rendering is blocked by the unavailable required bundled presentation runtime.

## 1. Pharmacy Inventory Logistics Agent

One store. Explained inventory review. Human operational decisions.

- Kerrian Gordon: Harness
- Brahim Maouloud: Agent Instructions and Tooling
- Emmanuel De Jesus: Injection Risk Prevention

Speaker notes: Ownership is documented in the MOD PRD and Phase 6 handoff. Do not infer teammate implementation status. The CVS location is project context, not a partnership or authorized inventory access.

## 2. The Agent turns stock and usage into a reviewable supply estimate

- Read a synthetic inventory snapshot for store 1618.
- Use independently validated stock and 14 completed days of aggregate consumption to estimate days of supply.
- Compare with validated item policy; explain inputs and uncertainty.
- Present FDA national shortage context separately from local supply.
- Authorized staff decide and execute replenishment outside the Agent.

Speaker notes: Product intent comes from docs/requirements/Pharmacy Inventory Logistics[PRD]-Mod.md. The standalone prevention package does not calculate pharmacy supply or establish medication/source truth. No clinical, dispensing, ordering, inventory-write or policy-edit authority is granted.

## 3. The harness enforces boundaries around the model and tools

Diagram sequence: untrusted input → bounded intake → safe exceptions and minimal facts → future model → guarded read tools → validated results → output check → human review.

| Component | Responsibility | Current status |
|---|---|---|
| Future pharmacy harness | Verify identity, source evidence, units, freshness, policy and calculations; share a run budget | Planned integration |
| read_store_inventory | Read a consistent single-store snapshot | Synthetic guarded callback; live adapter pending |
| get_fda_shortage_context | Retrieve exact-package national context | Synthetic guarded callback; live adapter pending |
| Prevention package | Isolate text and enforce context/action/output contracts | Implemented standalone |

Speaker notes: Use the Phase 6 handoff integration diagram. Callback demonstrations are not live adapters. Read-only credentials, adapter IO timeouts, provenance, operational policy and the complete model loop still need integration verification.

## 4. Implemented controls protect separate boundaries

- Intake: bounded JSON, source contracts, Unicode checks and 15 versioned instruction signals.
- Context: exclude all external free text, including accepted descriptions; use facts constructed in trusted application code.
- Evidence: withhold affected results when required verification or item/store/NDC binding fails.
- Actions: authorize captured arguments before dispatch; allow only configured read callbacks.
- Output: reject changed facts, omitted warnings and unauthorized action claims; return a deterministic manual-review fallback.

Speaker notes: Sources are boundary_contracts.py, text_detector.py, safe_context.py, action_guard.py and output_guard.py. Instruction detection can miss wording. SQL parameterization addresses executable SQL, not prompt injection; no live database grants or staff-write authorization were exercised.

## 5. The local Tester exposes attempts and actual containment

Input controls: inventory/FDA/request samples and custom JSON; verified or missing synthetic evidence; proposed tool; proposed report tampering.

Results to capture: decision and safe reasons; visible code points; context exclusion; action permission/dispatch; report validation and fallback.

Demonstrations:

- A hidden-character instruction: inspect the code point and context exclusion.
- A forbidden order or inventory write: inspect the denied dispatch.
- Supply changed to 999 or an order claim: inspect output rejection and safe fallback.
- Missing evidence: inspect manual review instead of a confident result.

Speaker notes: web/local_tester/index.html and src/injection_prevention/local_tester.py. This is a loopback-only Python tester with fixed synthetic facts, no live model, database or operational write. Capture observed output rather than creating simulated screenshots.

## 6. Input tests exercise attacks and legitimate counterexamples

| Test family | Risk | Expected prevention behavior |
|---|---|---|
| Hidden/zero-width/bidi characters | Concealed instructions or misleading labels | Field-contract exception; visible code points for human inspection; raw text excluded |
| Role spoofing and ignore/order instructions | External data treated as authority | Detection signal when recognized; text omitted regardless |
| Valid-shaped FDA or stored text | Malicious meaning passes syntax validation | No external description enters model context |
| Keyword-free unfamiliar wording | Detector misses an instruction | Detection may miss; independent text exclusion still contains the text |
| Duplicate keys, nonfinite values, size/depth excess | Ambiguous input or resource exhaustion | Bounded parser/contract rejection |
| Accents and visible non-Latin text | Legitimate input rejected | Benign counterexamples accepted under the supported field policy |

Speaker notes: Tests/fixtures labels.json and phase6_labels.json; test_boundary_contracts.py, test_detection_v2.py and test_safe_context.py. Joiner-dependent legitimate language needs a reviewed field policy; do not claim a universal Unicode rule. A passing selected fixture is not proof of all future attacks being detected.

## 7. Action and output tests verify enforcement beyond detection

| Attempt | Boundary | Expected result |
|---|---|---|
| order_medication / update_inventory | Fixed action allowlist | Denied; no forbidden callback dispatched |
| run_sql / run_shell / secret access | Tool permissions | Denied; no execution capability granted |
| Wrong store or unconfigured package NDC | Captured call scope | Denied before dispatch |
| Submitted verified flag or mismatched identity | Trusted fact assembly | Submitted claims cannot establish trust; affected result requires manual review |
| Change days of supply to 999 | Exact output facts | Reject proposal; deterministic fallback |
| Hide required warnings / claim an order | Output warnings and action claims | Reject proposal; deterministic fallback |
| Exhaust request/run limits | Budget enforcement | Stop safely; adapter cancellation still needs integration testing |

Speaker notes: test_action_output_guards.py, test_security_boundaries.py and test_phase6_remediation.py. Distinguish attempted calls from dispatches and effects: blocked attempts can be nonzero while forbidden dispatches remain zero. No clinical urgency or human write authority is inferred.

## 8. Tested evidence and next integration work

Fresh qualification run, October 9, 2026:

- 85 selected fixtures matched their predefined outcomes.
- 55 unsafe fixtures detected; 30 benign fixtures accepted.
- 0 fixture misses and 0 false positives in this selected sample.
- External text excluded in all 85 cases.

Fresh behavior suite: 66 methods ran; 65 passed and one errored. The Tester oversized-request test encountered Windows connection abort WinError 10053; a 413 response was not observed in that run. Earlier recorded evidence reports 66 passing methods.

Next work: verify the HTTP failure, connect independently verified harness facts and scoped read adapters, and test the complete model/tool loop. Live CVS/FDA connectivity, database grants, source authenticity and blocking IO cancellation remain outside current verification.

Speaker notes: Fresh python -B -m unittest discover -s tests -q and qualification_report() at source snapshot 0b7c4bc. Report detection and containment separately. All preventative claims refer to the tested cases, not every possible injection risk. The full suite failure is not evidence that the oversized body was accepted, and it is not a confirmed pass for the expected HTTP response.
