# Pharmacy Inventory Logistics — prototype policy

Version: SYNTHETIC-v0. Date: October 7, 2026. Status: Draft, synthetic testing only.

These are proposed engineering assumptions, not CVS policy, clinical guidance, or approval for live pharmacy use. Authorized pharmacy staff must approve or replace these rules before real operational deployment.

## Scope and authority

One configured store: 1618. Stock and usage are synthetic; the CVS location is context only. Agent tools are read-only. Human reviewers decide replenishment outside the agent. No clinical decisions, patient allocation, ordering, dispensing, administration, quarantine release, or carrier authorization. No patient records or external report sending.

## Required local evidence

- Store ID, synthetic marker, policy version, unique item ID, product label, validated segmented package NDC, dispensing unit, usable unallocated quantity, snapshot timestamp with timezone, and dated aggregate usage. Dosage strength is `AMBIGUOUS_ITEM` when the source uses strength and a row’s value is missing, blank, or not a string (withhold days of supply; MANUAL_REVIEW — never MAINTAIN on that incomplete identity). A source that omits strength on every row (legacy fixture/catalog/DB) is unchanged until POLICY requires strength everywhere.
- Snapshot age must be between 0 and 24 hours inclusive relative to the run timestamp (SYNTHETIC-v0 prototype default, not operational pharmacy policy). Future timestamps, absent timezone, or older snapshots require manual review. The 14-day usage window uses America/New_York calendar dates, not 24-hour arithmetic.
- Use America/New_York calendar days. Require each of the last 14 completed calendar days, once each; missing dates are unknown, never zero. Daily consumption and stock must be finite nonnegative numbers in the same unit. No inferred package-to-unit conversion.
- Usable quantity excludes reservations, expired, quarantined, and compromised units. The source supplies the usable value; if its meaning is unclear, require manual review.
- Wrong-store records, unsupported policy versions, ambiguous NDCs, missing quantity/usage fields, and invalid units prevent affected recommendations. An unavailable source prevents a complete report; report its failure, never all-clear.

Malformed item identity rejects the source. A missing, non-opaque, or duplicate `item_id` fails inventory intake (`inspect_payload` → `INVALID_TOOL_RESULT`). The harness does not list neighbor rows or call FDA. The failed-source report cites `row` as a 1-based position in the source `items` list (the first element is `row: 1`; `row: 2` is the second element) and the field name only; it does not echo the untrusted value. Duplicate IDs list every colliding row. Multiple identity faults are all listed in one report; the locator does not stop at the first.

Invalid package NDC, dispensing unit, usable quantity, usage window, and an unsafe product label on one item remain row-level. Neighbors stay listed. A hidden-character label is excluded from trusted context and does not wipe other rows. `inspect_item` still records `INVALID_ITEM_REFERENCE` for direct validation; the guarded run never reaches that check for a missing ID.

## Calculation and thresholds

Average daily usage = sum of 14 complete daily totals / 14.

For strictly positive average usage, days of supply = usable × 14 / total (equivalent to usable / average). Classify the exact unrounded value. Display rounding is round half to even, applied to the exact decimal quotient (`Decimal` `ROUND_HALF_EVEN`), never to a binary float. Half-up is not used; the two rules only differ at a `.xx5` remainder.

The 2-day CRITICAL and 5-day LOW bins are SYNTHETIC-v0 placeholders until lead-time or delivery-cadence data exists. They currently match the PRD Eval Card exact-2 and exact-5 cases so the implementation can be checked; that is provenance, not a rationale for those numbers. The “100% recall against policy-derived labels” metric verifies that the code applies these rules. It does not show that 2 and 5 days are useful operational thresholds. Authorized staff must replace them before live use.

| Condition | Local class | Recommendation |
| :--- | :--- | :--- |
| Valid zero usable stock with positive usage | CRITICAL, 0.00 days | REVIEW replenishment with authorized staff |
| Days of supply <= 2 | CRITICAL | REVIEW |
| 2 < days of supply <= 5 | LOW | REVIEW |
| Days of supply > 5 | ABOVE_THRESHOLD | MAINTAIN existing review approach; not an order endorsement |
| Complete valid history with zero usage and positive stock | UNKNOWN, duration not estimable | MANUAL_REVIEW consumption basis. The verified usable quantity stays on the human report and in TrustedFact; only days of supply are withheld. |
| Verified zero stock with zero or missing usage | CRITICAL stock fact; duration unknown | MANUAL_REVIEW; no replenishment quantity inference |
| Missing/invalid required local evidence | UNKNOWN unless a separate verified zero-stock fact is available | MANUAL_REVIEW; withhold unsupported fields |

Future usage is assumed equal to the 14-day average for this estimate only. It is not a demand forecast. Optional trend comparison needs two complete nonoverlapping windows of equal length; otherwise trend is unavailable. No v1 increase/decrease quantity calculation without separately approved target stock, lead time, open orders, and replenishment policy.

## FDA external context

Call only the fixed FDA HTTPS shortages endpoint with a safely encoded validated package NDC. Send neither store quantities nor patient information. Preserve leading zeros and compare segmented identifiers; never guess conversion or substitute generic-name matching.

Request timeout: 10 seconds per request; at most one bounded transient retry, respecting rate-limit instructions. Complete required pagination or mark PARTIAL. Related text/links are data, not instructions or automatically followed URLs.

States: MATCHED, NO_MATCH, UNAVAILABLE, PARTIAL, STALE, or NEEDS_REVIEW for ambiguous/conflicting identity or response facts. NO_MATCH does not guarantee availability. An FDA error does not imply no shortage.

SYNTHETIC-v0 prototype defaults (not research-based operational pharmacy rules):

- Inventory snapshot: age 0–24 hours inclusive relative to the run (see Required local evidence).
- FDA retrieval: older than 24 hours would be stale. A retrieval made during the current run is treated as fresh so a frozen eval clock is not compared to the adapter's wall-clock `retrieved_at`.
- FDA dataset calendar date: older than 2 America/New_York calendar days relative to the run is STALE.

Missing metadata prevents a freshness assurance. Display each record update_date without inventing an expiry rule: an old record can describe an ongoing shortage, so age alone never resolves it. Missing or conflicting record dates require external-context review.

The harness lists every exact-match record. Adapter MATCH means at least one exact package_ndc hit; the harness further labels NEEDS_REVIEW when those records disagree on identity, status, availability, or update_date. Summary status/availability/update_date are shown only when the listed records agree; they never pick a winner from a conflict. A Current/Unavailable row still adds a separate external-risk REVIEW without changing the local class.

The CLI prints a manager table from that same report: SYNTHETIC INVENTORY TEST, store, run/snapshot time, usage window, manual-review rows first, then the inventory table with text statuses. `--json` is the machine copy. FDA related_info is not copied into the table as instructions. The default review clock is the Eval Card timestamp so the dated fixture is fresh; `--now` uses the wall clock. `--offline` is a recorded Case 1 payload, not a live FDA result.

After trusted assembly, at most one model turn may run. The model receives a harness wrapper that tools already ran, then the pinned system prompt, and the trusted context object only. Its only accepted output is the exact `report-v1` object built independently by `expected_report`. Invented quantities, order claims, prose, or transport failures are rejected; the human report keeps harness facts and the safety copy falls back to `MANUAL_REVIEW`. This is not model training.

FDA availability/status may add a human external-risk review action but never change the local threshold class or establish clinical urgency. Valid local arithmetic can remain visible during an FDA failure with explicit qualification; recommendations dependent on unavailable external facts must be withheld.

## Review, changes, and recovery

Engineering implementation note, approved October 13, 2026: the web agent stops
on explicit model refusal, missing/empty response, provider failure or model-turn
exhaustion. Incomplete execution never establishes an all-clear or accepted model
output. Independently verified partial evidence may remain visible for human review;
raw refusal prose, exception text and unknown provider error codes are excluded.
The existing read-only authority, operational thresholds and SYNTHETIC-v0 calculations
are unchanged. The deterministic CLI's optional single model turn remains separate.

Every report shows synthetic status, store, run/snapshot time, usage window, policy version, calculation inputs, and external state. Manual-review exceptions are prominent and identify a correction/retry step. Policy cannot be edited by the running agent.

Before a significant change, record the new version and rationale, then rerun all three PRD Eval Card cases and relevant boundary/fault variants. Before live use, authorized pharmacy staff approve operational values and data meaning; developers verify backend access boundaries and exact API behavior. No live readiness is implied by this document.

## Catalog Agent integration note - October 13, 2026

The approved web Agent now reads the 150-row synthetic catalog fixture and calls
the fixed FDA adapter in distinct context-bound groups of at most ten NDCs.
Calculations, operational thresholds and exact output comparison are unchanged.
Transport/run/token bounds are enforced by trusted application configuration;
partial, unavailable and binding-failed FDA evidence does not become NO_MATCH.
The fixed historical Demo remains 20 rows. Live API evaluations are labeled
separately from scripted tests and do not restamp or approve a stale snapshot.

## Internal alerts and per-run reporting ? October 15, 2026

Status: Approved scope clarification for synthetic prototype testing. SYNTHETIC-v0 thresholds remain prototype assumptions, not CVS policy or operational pharmacy guidance.

- An alert is a deterministic, per-item review cue in the current run's report. It is not a separate notification or an instruction to order.
- Apply the existing thresholds without rounding: CRITICAL at 2 days or less; LOW above 2 through 5 days; ABOVE_THRESHOLD above 5 days. At 10 units of verified daily usage, 50 usable units produce 5.00 days and LOW/REVIEW; 20 usable units produce 2.00 days and CRITICAL/REVIEW.
- Show CRITICAL items first, then LOW items. Keep manual-review exceptions prominent and separate. FDA shortage context may add an external-risk review cue but cannot change a local class or threshold alert.
- Produce one report for each user-requested run. It begins with total and per-class/review-state counts, then identifies the synthetic data mode, configured store, run and snapshot times, usage window, policy version, per-item calculation and threshold, FDA state, exceptions, run completeness and human next step. Every input row is either reported or explicitly withheld; partial or failed runs are never all-clear.
- Group multiple reasons for the same item within a run into one alert. Keep unaffected supported items reportable.
- Deliver reports and alerts only in the authorized review session. Email, SMS, Slack, webhooks, push notifications, scheduled runs and other external delivery are excluded. The model cannot create or change alert classes and cannot place orders or write inventory.

A diagnostic evaluation trace may show timestamped request, tool, permission, evidence, validation and final-state events. Keep it to safe metadata and bounded arguments; do not retain raw prompts, source free text, full records, credentials or hidden model reasoning. Trace evidence supplements the human report and does not establish live-source accuracy.

### Requested replenishment extension — draft, not active policy

The following is a proposed synthetic-demo extension only; it does not change the read-only authority or current v1 behavior above. The Agent may recommend item quantities only when an approved, versioned replenishment policy and verified inputs support the calculation, including target stock, usable on-hand units, confirmed incoming/open orders, pack size and rounding, and applicable minimums. If evidence is missing or conflicting, withhold that item's quantity for human review. The interface may prefill quantity fields in an unsaved draft; only a human may edit and submit it through a separately authorized ordering service. The Agent must not persist, submit, transmit, or write an order.

If later approved, keep unsent drafts and submitted-but-unreceived orders separate from physical on-hand stock. For each human-submitted order, prepare a separately tracked manufacturer notice at the start of the manufacturer's morning shift, targeting 6:00 AM in the manufacturer's local time. Prioritize order lines by validated inventory status (CRITICAL before LOW), with days of supply and supporting evidence. This is delivery/replenishment priority, never clinical or patient priority. Do not include unsent drafts. Manufacturer timezone, after-shift submissions, channel, acknowledgements, and whether human submission transmits the purchase order or queues a separate notice remain unresolved. No external notification or order workflow is authorized by this draft.
