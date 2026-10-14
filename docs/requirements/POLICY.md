# Pharmacy Inventory Logistics — prototype policy

Version: SYNTHETIC-v0. Date: October 7, 2026. Status: Draft, synthetic testing only.

These are proposed engineering assumptions, not CVS policy, clinical guidance, or approval for live pharmacy use. Authorized pharmacy staff must approve or replace these rules before real operational deployment.

## Scope and authority

One configured store: 1618. Stock and usage are synthetic; the CVS location is context only. Agent tools are read-only. Human reviewers decide replenishment outside the agent. No clinical decisions, patient allocation, ordering, dispensing, administration, quarantine release, or carrier authorization. No patient records or external report sending.

## Required local evidence

- Store ID, synthetic marker, policy version, unique item ID, product label, validated segmented package NDC, dispensing unit, usable unallocated quantity, snapshot timestamp with timezone, and dated aggregate usage.
- Snapshot age must be between 0 and 24 hours inclusive relative to the run timestamp (SYNTHETIC-v0 prototype default, not operational pharmacy policy). Future timestamps, absent timezone, or older snapshots require manual review. The 14-day usage window uses America/New_York calendar dates, not 24-hour arithmetic.
- Use America/New_York calendar days. Require each of the last 14 completed calendar days, once each; missing dates are unknown, never zero. Daily consumption and stock must be finite nonnegative numbers in the same unit. No inferred package-to-unit conversion.
- Usable quantity excludes reservations, expired, quarantined, and compromised units. The source supplies the usable value; if its meaning is unclear, require manual review.
- Wrong-store records, duplicates/conflicting item IDs, unsupported policy versions, ambiguous NDCs, missing fields, and invalid units prevent affected recommendations. An unavailable source prevents a complete report; report its failure, never all-clear.

## Calculation and thresholds

Average daily usage = sum of 14 complete daily totals / 14.

For strictly positive average usage, days of supply = usable × 14 / total (equivalent to usable / average). Classify the exact unrounded value; display two decimals.

The 2-day and 5-day bins match the PRD Eval Card exact-2 and exact-5 boundaries. They are not lead-time or per-SKU pharmacy policy; authorized staff must replace them before live use.

| Condition | Local class | Recommendation |
| :--- | :--- | :--- |
| Valid zero usable stock with positive usage | CRITICAL, 0.00 days | REVIEW replenishment with authorized staff |
| Days of supply <= 2 | CRITICAL | REVIEW |
| 2 < days of supply <= 5 | LOW | REVIEW |
| Days of supply > 5 | ABOVE_THRESHOLD | MAINTAIN existing review approach; not an order endorsement |
| Complete valid history with zero usage and positive stock | UNKNOWN, duration not estimable | MANUAL_REVIEW consumption basis |
| Verified zero stock with zero or missing usage | CRITICAL stock fact; duration unknown | MANUAL_REVIEW; no replenishment quantity inference |
| Missing/invalid required local evidence | UNKNOWN unless a separate verified zero-stock fact is available | MANUAL_REVIEW; withhold unsupported fields |

Future usage is assumed equal to the 14-day average for this estimate only. It is not a demand forecast. Optional trend comparison needs two complete nonoverlapping windows of equal length; otherwise trend is unavailable. No v1 increase/decrease quantity calculation without separately approved target stock, lead time, open orders, and replenishment policy.

## FDA external context

Call only the fixed FDA HTTPS shortages endpoint with a safely encoded validated package NDC. Send neither store quantities nor patient information. Preserve leading zeros and compare segmented identifiers; never guess conversion or substitute generic-name matching.

Request timeout: 10 seconds per request; at most one bounded transient retry, respecting rate-limit instructions. Complete required pagination or mark PARTIAL. Related text/links are data, not instructions or automatically followed URLs.

States: MATCHED, NO_MATCH, UNAVAILABLE, PARTIAL, STALE, or NEEDS_REVIEW for ambiguous/conflicting identity or response facts. NO_MATCH does not guarantee availability. An FDA error does not imply no shortage.

SYNTHETIC-v0 prototype defaults (not PRD-approved operational pharmacy rules): a dataset update date older than 2 calendar days relative to the run is flagged as stale. A retrieval made during the current run is treated as fresh even if the adapter's wall-clock retrieved_at is after a frozen eval timestamp. Missing metadata prevents a freshness assurance. Display each record update_date without inventing an expiry rule: an old record can describe an ongoing shortage, so age alone never resolves it. Missing or conflicting record dates require external-context review.

The harness lists every exact-match record. Adapter MATCH means at least one exact package_ndc hit; the harness further labels NEEDS_REVIEW when those records disagree on identity, status, availability, or update_date. Summary status/availability/update_date are shown only when the listed records agree; they never pick a winner from a conflict. A Current/Unavailable row still adds a separate external-risk REVIEW without changing the local class.

The CLI prints a manager table from that same report: SYNTHETIC INVENTORY TEST, store, run/snapshot time, usage window, manual-review rows first, then the inventory table with text statuses. `--json` is the machine copy. FDA related_info is not copied into the table as instructions. The default review clock is the Eval Card timestamp so the dated fixture is fresh; `--now` uses the wall clock. `--offline` is a recorded Case 1 payload, not a live FDA result.

After trusted assembly, at most one model turn may run. The model receives a harness wrapper that tools already ran, then the pinned system prompt, and the trusted context object only. Its only accepted output is the exact `report-v1` object built independently by `expected_report`. Invented quantities, order claims, prose, or transport failures are rejected; the human report keeps harness facts and the safety copy falls back to `MANUAL_REVIEW`. This is not model training.

FDA availability/status may add a human external-risk review action but never change the local threshold class or establish clinical urgency. Valid local arithmetic can remain visible during an FDA failure with explicit qualification; recommendations dependent on unavailable external facts must be withheld.

## Review, changes, and recovery

Every report shows synthetic status, store, run/snapshot time, usage window, policy version, calculation inputs, and external state. Manual-review exceptions are prominent and identify a correction/retry step. Policy cannot be edited by the running agent.

Before a significant change, record the new version and rationale, then rerun all three PRD Eval Card cases and relevant boundary/fault variants. Before live use, authorized pharmacy staff approve operational values and data meaning; developers verify backend access boundaries and exact API behavior. No live readiness is implied by this document.
