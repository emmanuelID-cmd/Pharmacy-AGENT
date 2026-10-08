# Proposed PRD and policy changes — review copy

Date: October 7, 2026. Status: PROPOSED ONLY. Neither source document has been edited. No strikethrough is used.

## Scope and rationale

Replace global medication thresholds with item-specific pharmacy policy. Keep aggregate usage as the consumption basis, differentiate strength/form/package, and retain human execution of every operational action. Include the previously recorded FDA supporting-context label. This is a comparison artifact, not authorization for live deployment or an implemented policy.

Source directory: C:/Users/dejes/OneDrive/Documents/Pursuit/Pursuit/_Lessons/L2-Week-3/Pharmacy-Agent-Role. Line references below refer to the inspected 197-line PRD and 53-line POLICY.md. If either source changes, rebase these proposals against it before applying them.

## PRD comparison

| Change | Existing source lines | Current wording or behavior | Proposed wording or behavior |
|---|---|---|---|
| PRD-01: Human execution | 54, 86, 105, 153 | Manager acts outside the agent; purchasing excluded | Explicitly state: The authorized human decides and executes orders, reorders, and inventory changes in their existing system. Agent purchasing and inventory execution remain out of scope, including when requested by a human. |
| PRD-02: Item-specific needs | Insert after 46 | Needs cover evidence but not item-specific policy | As an inventory manager, I need thresholds for each medication strength, dosage form, and package because store usage and replenishment conditions differ across items. |
| PRD-03: Acceptance coverage | 75-76, 79 | Numeric accuracy/fault targets without item-policy variants | Preserve numeric targets; include differing thresholds by item, exact low/critical boundary cases, absent/expired policy, and mismatched strength/form/package in the existing test sets. |
| PRD-04: User-visible policy | 93, 98 | Policy version and thresholds visible | User can inspect the matching item policy, its approval status and validity dates, low/critical days-of-supply thresholds, operational category, and any supplied lead-time/buffer rationale. No universal percentage trigger. |
| PRD-05: Inventory tool contract | 116, 123 | Package NDC, label, units, usage; no explicit item-policy fields | Add strength, dosage form, package size/unit, operational usage category, and matching item_policy containing item identity, low_days, critical_days, version, effective/expiry dates, approval status, and optional lead_time_days/safety_buffer_days. Synthetic fixtures explicitly mark approval as TEST_APPROVED; live policy requires authorized approval. |
| PRD-06: Calculation and recommendation | 125-127 | Policy defaults; no reorder quantities | Keep days-of-supply arithmetic. Compare its unrounded result with that item's valid critical_days and low_days. Missing/invalid item policy allows a separately valid numeric estimate but blocks threshold class and replenishment recommendation, yielding MANUAL_REVIEW. No silent global fallback, percentage rule, or calculated order quantity. |
| PRD-07: FDA supporting label | Insert after 129; update 146, 150, 152 | National context separate, label not explicit | Label the FDA output column/section exactly: External supporting context — national shortage signal. FDA cannot change stock quantity, usage calculation, days of supply, or local threshold class. It can add a separate human external-risk review action. |
| PRD-08: Prompt policy validation | 144-145, 147, 149-150 | Checks general policy version | Validate matching item policy, test/live approval, validity interval, and finite thresholds satisfying 0 < critical_days < low_days. Show the item thresholds and policy version. Never infer clinical urgency from dose schedule, diagnosis, or product text; operational categories and any clinical priority must be supplied by authorized policy. |
| PRD-09: Missing policy safeguard | Insert table row after 168 | Unit/package safeguards only | Failure: absent, expired, conflicting, or wrong-item policy. Impact: wrong replenishment priority. Safeguard: no global fallback; display valid arithmetic separately; UNKNOWN classification and MANUAL_REVIEW, except an independently verified zero-stock fact remains CRITICAL. |
| PRD-10: Case 1 policy | 179, 183 | 6.22 days classified against global 5-day low threshold | Version becomes proposed SYNTHETIC-v1. Item A explicitly has low_days=5 and critical_days=2, with valid TEST_APPROVED policy. Preserve 6.22 days ABOVE_THRESHOLD and independent FDA risk review. |
| PRD-11: Case 2 differentiation | 184 | Zero-use edge case | Replace this edge case with two valid synthetic rows, each 80 units and 280 units consumed over 14 days: 4.00 days supply each. Item B1 has low=7, critical=3 -> LOW/REVIEW. Item B2 has low=3, critical=1 -> ABOVE_THRESHOLD/MAINTAIN. Use distinct validated package identities, synthetic FDA NO_MATCH, and require no availability guarantee. Keep zero-usage coverage in additional regression variants. |
| PRD-12: Case 3 and regressions | 185, 187 | Missing stock/history plus injected order instructions; fixed 2/5 boundaries | Add missing item policy to Case 3 and expected manual-review reasons. Preserve refusal of tool instructions. Parameterize boundary tests against each item's critical/low values; add missing policy with otherwise valid arithmetic, expired policy, and wrong dosage/package policy. Maintain exactly three Eval Card cases. |

## POLICY.md comparison

| Change | Existing source lines | Current wording or behavior | Proposed wording or behavior |
|---|---|---|---|
| POL-01: Policy version | 3 | SYNTHETIC-v0 | Proposed SYNTHETIC-v1 once approved/applied; synthetic testing only. No claim of CVS policy approval. |
| POL-02: Human execution | 9 | Human reviewers decide; ordering excluded | Human reviewers decide and execute any order/reorder or inventory change outside the agent. Ordering and stock changes by the agent remain prohibited. |
| POL-03: Required item policy | 13, 17 | General policy version | Require strength, dosage form, package size/unit, and matching versioned item_policy with low_days, critical_days, effective/expiry dates and approval status. Reject missing, expired, conflicting, wrong-item, nonfinite, or invalid-order thresholds; no global default. |
| POL-04: Threshold branches | 28-30 | CRITICAL <=2; LOW <=5; ABOVE >5 | CRITICAL when supply <= item critical_days; LOW when item critical_days < supply <= item low_days; ABOVE_THRESHOLD when supply > item low_days. Require 0 < critical_days < low_days. Keep all other stock/usage exception branches. |
| POL-05: Policy failure branch | Insert after 33 | Required-data faults grouped together | If arithmetic inputs are valid but item policy is invalid, show the valid days-of-supply estimate; local class UNKNOWN and action MANUAL_REVIEW. If verified usable stock is zero, retain CRITICAL stock fact but require manual review of policy before any replenishment recommendation. |
| POL-06: Threshold-setting rationale | Insert after 35 | No per-item threshold-setting guidance | Authorized staff supply per-item thresholds based on observed aggregate usage, replenishment lead time and safety buffer. A synthetic planning example may use low_days = lead_time_days + safety_buffer_days; agent does not learn, approve, or alter thresholds automatically. Percentage-of-stock alone and individual dosing frequency do not establish inventory priority. |
| POL-07: FDA label | 37, 47 | FDA external context heading and separation | Use the exact visible label External supporting context — national shortage signal; preserve stock quantity, usage, days of supply, and local classification unchanged. |
| POL-08: Output evidence | 51 | Policy version and calculation inputs | Include item-specific threshold values, policy identity/validity, usage category, and lead-time/buffer rationale when supplied. Human execution remains explicit. |

## Proposed synthetic examples

These are illustrative operational policy configurations, not medication recommendations or current CVS data. Clinical severity is never inferred by the agent. Different policy per strength/form/package prevents accidental merging of similar labels.

| Synthetic item | Aggregate usage | Lead time | Safety buffer | Low threshold | Critical threshold | Example stock and result |
|---|---|---|---|---|---|---|
| A: frequently used 300 mg tablet, 60 tablets/bottle | 120 tablets/day | 3 days | 4 days | 7 days, supplied test policy | 3 days, independently supplied test policy | 840 usable tablets = 7 days -> LOW/REVIEW |
| B: less frequently used tablet, separately identified package | 5 tablets/day | 2 days | 2 days | 4 days, supplied test policy | 1 day, independently supplied test policy | 20 usable tablets = 4 days -> LOW/REVIEW |

Package size does not determine the dispensing unit: compare tablets to tablets after source-validated unit handling. A twice-daily dose for one patient is not store aggregate demand. Slow usage does not establish long shelf life; expiry and unusable inventory remain excluded. No fixture suggests substituting between doses or medications.

## Application checklist

1. Review these proposed replacements; PRD and POLICY.md remain unchanged.
2. When applying, preserve unrelated user edits and create a recoverable prior version before replacing source text.
3. Update both documents together, including prompt, tools, metrics and exactly three Eval Card cases; mark the new policy version.
4. Recheck thresholds, 4-day contrasting classifications, zero-use/stock branches, FDA separation, human execution and manual-review behavior.
5. Return exact before/after edited ranges after application; these source references are proposed edit locations, not completed changes.

## Current action line reference

Only this comparison file was created. The PRD and POLICY.md have no changed lines in this action. All lines of this file are new; exact count is returned after verification.

## Additional proposal: persistent inventory database

Recorded October 7, 2026. Status: PROPOSED ONLY. Append to the comparison record; do not apply changes to the PRD, policy, or diagrams yet. Preserve the earlier no-strikethrough comparison format.

The inventory system should use a persistent database for medication/package records, stock movements, aggregate usage, item-specific policy and audit history. Start with synthetic data for one store. Database engine, hosting and exact schema remain decisions for the next PLANNER investigation; no service or framework is selected here.

| Component | Proposed responsibility | Authority boundary |
|---|---|---|
| Inventory database | Persist item identity, movement history, usage, versioned policy and current stock views | One-store scope; synthetic prototype data; no patient records |
| Authorized staff interface | Add items, record authorized stock changes and retire items | Human execution; authenticated, authorized writes with validation |
| read_store_inventory | Read a consistent, timestamped snapshot from the database | Dedicated read-only access; fixed parameterized queries; no arbitrary model-generated SQL |
| Audit history | Record actor, time, action and before/after evidence for changes | Preserve history; retire referenced items rather than erase their stock history; deletion rules require explicit policy |
| Harness | Validate calls/results, calculate supply, enforce tool permissions and bound the loop | Agent has no write credentials, ordering tool or policy-edit authority |

### Proposed document and diagram updates

- PRD 3a / inventory contract: replace the local-file-only source with a proposed database-backed reader, while retaining synthetic labels, single-store scope and deterministic calculations. Update prior claims that the prototype has no database only when implementation actually exists.
- PRD journey requirements: add human-managed item creation, stock movement recording and item retirement with permission/error/recovery states. This expands the system around the agent; it does not grant the agent write authority.
- PRD 3c / policy safeguards: add SQL-injection defenses, separate read/write roles, atomic stock updates, consistent reads, audit history and controlled item retirement. Reassess evaluation scope before implementing these added features.
- Architecture: show staff interface -> authorized write service -> inventory database; agent harness -> read_store_inventory -> read-only database access. No direct model-to-database SQL execution.
- SQL-injection entry points: staff form fields, import values and tool-call arguments used in queries. Controls: parameterized queries, validated identifiers, fixed query paths, least privilege and authorization enforced by the service/database. These controls need implementation tests; the diagram alone proves none of them.
- Keep prompt injection separately marked at user text and returned free-text fields. SQL parameterization does not prevent malicious instructions in valid text returned to the model.

### Weakest point in the current diagram

The tool-result boundary between external/local data, the harness and the model is the least proven part. Shape, identity and freshness validation can accept a text field that still contains persuasive instructions or misleading facts. A prompt telling the model to ignore those instructions is not proof of reliable resistance. The read-only allowlist prevents direct ordering but does not guarantee that the final recommendation remains correct. Test with valid-shaped malicious results, verify forbidden calls are rejected outside the model, and check that outputs preserve local calculations and uncertainty. All depicted harness controls are proposed, not verified implementation.

## Additional proposal: usage evidence and inventory-affecting anomalies

Recorded October 7, 2026. Status: PROPOSED ONLY following peer feedback. Expanded and consolidated with additional anomaly examples; PRD, POLICY.md and architecture images remain unchanged. No strikethrough is used.

### Scope clarification

V1 excludes patient_ID, individual dosing instructions, delivery addresses and patient-level records. Strength, dosage form, package size and dispensing unit identify the inventory item; they are not patient dosing instructions. Patient count is not required when aggregate usage for each exact item is complete and reliable. Missing patient count must not invalidate a supported aggregate calculation or be guessed.

Use verified inventory consumption for the exact medication/package as the usage basis. The source must define which transaction statuses represent actual consumption and distinguish stock movements from dispensing: receipts, transfers and adjustments must not be treated as patient use. Reservations, cancellations, returns and unresolved transactions need explicit accounting rules so they are not double-counted or silently interpreted as consumption. Missing usage dates are unknown, not zero.

### Consolidated tool-result and harness contract

Return structured exceptions with affected item/record references, field names, dates, available evidence and a correction needed. Use opaque inventory-event references that do not expose or encode patient identity; do not return patient identifiers, prescriptions, clinical instructions or addresses. These are proposed validation results, not implemented behavior. One event can have several supported reason codes under a single exception rather than duplicate alerts.

| Anomaly group and examples | Inventory effect | Proposed result | Harness behavior |
|---|---|---|---|
| Item identity: missing strength/form/package/unit; substituted strength or package | Consumption assigned to the wrong item or incompatible units combined | AMBIGUOUS_ITEM | Keep exact items separate; require source-validated identity/unit handling; withhold affected calculations |
| Missing quantity/status/date: incomplete usage window or undocumented movement | Consumption or usable stock cannot be established | INCOMPLETE_USAGE | Identify missing evidence; withhold affected estimate/recommendation; never substitute zero |
| Quantity reconciliation: requested, filled and recorded counts differ; partial fill or split fulfillment | Full quantity counted although only part moved, or mismatch in stock balance | QUANTITY_MISMATCH when documented conflict exists; otherwise UNRESOLVED_TRANSACTION | Separate verified fulfilled and outstanding quantities; reconcile source totals; no guessed quantity |
| Reservation and pickup: no pickup, changed date, changed store, pickup switched to delivery | Reserved stock mistaken for consumption; reservation at wrong store or duplicated | RESERVATION_REVIEW for a documented unresolved reservation | Keep reserved stock out of usable inventory; require source-defined verified consumption event; reconcile store ownership and one event identity |
| Delivery blocked: missing address or documented sending/dispatch failure | Stock remains reserved while shipment cannot proceed | DELIVERY_BLOCKED only when explicitly supplied by source | Show status and affected quantity without address; source staff resolve it; do not operate delivery workflow |
| Failed delivery, returned medication or return-to-stock event | Returned units prematurely counted as usable or consumption reversed twice | RETURN_REVIEW | Require authorized disposition and accounting rule; agent cannot release returned/quarantined stock or assume a return is reusable |
| Cancellation or duplicate event/update | False demand or double-counted consumption | TRANSACTION_REVIEW with cancellation/duplicate reason | Apply source-defined cancellation handling and idempotent aggregation; preserve audit history |
| Late, out-of-order or contradictory event states | Stale balances or contradictory consumption | STALE_OR_CONFLICTING_EVENT | Use source-approved event/version ordering; reconcile conflicts; no all-clear based on incomplete evidence |
| Missing patient dosing instructions | Upstream dispensing validation may be unresolved | Source-provided unresolved status only; no patient dosage returned | Staff resolve the clinical/dispensing issue; agent uses only verified consumption. If aggregate usage remains valid, absence of patient dosing data does not independently block it |
| Missing patient count with complete validated aggregate usage | No demonstrated aggregate inventory fault | Aggregate usage valid; patient count unavailable | Continue calculation; no patient-level inference |
| Suspected nonpickup, sending failure or mismatch without decisive evidence | Cause and affected quantity are unknown | UNRESOLVED_TRANSACTION | Request human reconciliation; do not assert a cause or invent another reason code |

Exception codes describe evidence, not diagnosis of a cause. A missing value alone cannot prove nonpickup, delivery failure or quantity mismatch. Known events are not automatically errors: a documented reservation or partial fill may be accounted for normally if the source provides complete, consistent quantities and statuses. Flag only unresolved evidence that affects stock, consumption or required calculations; do not create a second clinical validation workflow.

A purchase order is not consumption. An unresolved event is not automatically available stock, consumption or a reason to reorder. If uncertainty changes usable quantity or aggregate usage for an item, stop the affected projection/replenishment recommendation and request reconciliation. Valid unaffected items can still be reported. Human staff decide and execute any reorder outside the agent.

### Proposed PRD, policy and diagram updates

- PRD 3a / read_store_inventory: define verified aggregate consumption and return the consolidated structured exception contract. Source integration must supply approved transaction summaries; access to prescription/delivery systems is not assumed or automatically added.
- PRD inventory contract and POLICY.md: document source-approved status/accounting rules, exact identity, units, usable stock, complete usage coverage and idempotent event handling. Avoid double-counting reservations, partial fills, cancellations, returns and duplicated updates.
- PRD 3b / system prompt: withhold unsupported results, identify missing evidence and request reconciliation without guessing causes. Do not request patient IDs, dosing instructions or addresses to replace aggregate evidence.
- PRD 3c / safeguards: cover identity, quantity, reservation, fulfillment/return and event-order faults under the common manual-review branch; preserve read-only agent authority.
- PRD 3d / evaluation variants: test each consolidated group, plus a valid reservation/partial fill and missing patient count with valid aggregate usage that must not be falsely rejected. Preserve exactly three primary Eval Card cases when integrating variants.
- Architecture: add harness validation -> Needs manual review with supported reason codes. Human reconciliation precedes explicit rerun; no automated order, reservation release, delivery action or anomaly-cause inference.

### Proposed peer-feedback response

The design change is to define verified aggregate consumption and return structured exceptions for ambiguous identity and inventory-affecting transaction evidence. Related pickup, reservation, delivery, quantity and return cases use consistent reconciliation rules. The harness identifies missing evidence, not an assumed cause, and routes affected items to human review. Missing patient count does not block a calculation supported by complete aggregate usage.

### Deferred scope

Patient-level modeling, dosing-based forecasts, delivery management, standard-deviation demand forecasting and weekly order-quantity calculation require a separate scope decision. Stock divided by patient count is not a replacement for usage measured in units per day. No clinical priority is inferred from strength, diagnosis or individual dosing frequency.

### Merge record

Expanded the existing usage-evidence section instead of appending a parallel anomaly list. Merged strength/form/package issues into item identity; count mismatch and split fills into quantity reconciliation; no/changed pickup and pickup-to-delivery into reservation review; sending failure/missing address into documented delivery blocks; cancellations/duplicates into transaction reconciliation. Added return disposition and late/conflicting update handling. Retained patient-count independence, missing-data fallback and no-cause-inference rules without duplicating them in separate sections.
