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
- Deliver inventory reports and threshold alerts only in the authorized review session. Email, SMS, Slack, webhooks, scheduled runs and external report delivery are excluded. The separate approved browser-notification demo below sends a bounded synthetic submitted-order list. The model cannot create or change alert classes and cannot place orders, send notifications or write inventory.

A diagnostic evaluation trace may show timestamped request, tool, permission, evidence, validation and final-state events. Keep it to safe metadata and bounded arguments; do not retain raw prompts, source free text, full records, credentials or hidden model reasoning. Trace evidence supplements the human report and does not establish live-source accuracy.

### Approved synthetic closing/order demo - October 16, 2026

This separate demo does not change SYNTHETIC-v0 stock classification, the Agent tool allowlist, or its read-only credentials. Close day captures one validated 150-row pre-order snapshot at a visibly frozen October 7 closing clock. Its report never changes after order submission. A source failure withholds closure; row-level exceptions remain visible. No movement ledger is connected, so opening-to-closing movements are unavailable rather than invented.

The additive deterministic contract is SYNTHETIC-DEMO-REPLENISHMENT-v1. For each exact item and dispensing unit, the explicit demo policy supplies target_days=7, confirmed_incoming=0, order_multiple=1 and minimum_units=1. These values are synthetic test assumptions, not authorized operational pharmacy policy or inferred manufacturer package quantities. The policy never enters or expands the existing model context.

Target units = verified average daily usage * target_days. Deficit = max(0, target units - usable on-hand - confirmed incoming). If deficit is positive, apply the minimum, then round up to the order multiple. A zero deficit yields a zero suggestion, not an instruction to order. Missing/mismatched policy, invalid/nonfinite values, ambiguous identity, invalid stock, incomplete/zero usage, or stale evidence withholds the suggestion. Suggestions exceeding the demo limit of 1,000,000 units are also withheld. No live open-order book is assumed to be empty.

A human selects from all 150 catalog entries, edits or removes supported suggestions, and explicitly submits a simulated order. Human-entered quantities must be whole dispensing units in 1..1,000,000. Unsupported items cannot be submitted as supported evidence. The application retains up to 20 distinct demo orders per process-local closing session, each with a scoped submission intent. Identical retries return the same order, including older orders; changed content under the same intent is rejected. New demo order starts a separate draft against the original report, without changing or deleting earlier submissions. Reaching the visible limit preserves history and rejects further new orders. The Agent has no submit/write tool. A simulated submission is not a placed order, stock receipt or consumption event.

After human submission only, show separate SMS and per-order manufacturer notice previews, with CRITICAL before LOW inventory priority. The demo next-shift time is 6:00 AM America/New_York, explicitly an assumption; after-shift submissions target the next shift. This is neither a scheduler nor an external send. The unconfigured adapter reports PREVIEW_ONLY and SMS_PROVIDER_NOT_CONFIGURED, never SENT. Real-phone SMS is unconfigured; the user selected the browser confirmation below for the current demo instead. No Slack integration is planned.

The report and simulated orders are memory-only, shared within the authorized prototype worker, and clear on restart; no cross-worker durability, real purchase-order transmission, post-submit revision/cancellation service or delivery acknowledgement is claimed. Durable orders/outbox and a protected human write service require separate Supabase scope on its assigned branch. An actual receipt, not an order submission, would change on-hand stock.

### Approved Android browser notification - October 16, 2026

Recovery clarification: order recording and notification delivery are separate outcomes. Once
recorded, the order remains immutable and its submit button displays Order submitted; adjacent
New demo order becomes available without awaiting notification delivery. A 20-second browser
request/body deadline releases pending waits, preserves uncertain order intents for reconciliation,
and never automatically retries a send. Fixed allowlisted notification failure references appear
below the form without exposing arbitrary response text or keys. Restore an existing subscription
before a separate worker-update check; an update failure must not silently discard that subscription.

After an explicit Enable notifications gesture and browser permission, a human submitting a demo order in that same Chrome browser may request one encrypted Web Push notification. This is an authenticated human application service, never an Agent tool. Emmanuel approved replacing the initial generic confirmation with the submitted-order list on October 16, 2026. The server constructs a versioned payload from the retained order: demo order ID, total selected-line count and up to six selected labels, submitted quantities, units and local inventory priorities; reduce that preview further when needed to remain within 3000 UTF-8 bytes. The full catalog, stock report, NDCs, evidence, raw input, credentials and private key are excluded. Labels are bounded single-line display text; unsafe optional labels use their item reference, while invalid required values withhold the send. The notification/lock screen may show these synthetic item names and quantities; the Enable guidance says so. Only validated HTTPS fcm.googleapis.com Chrome endpoints and valid subscription encryption keys are accepted; no arbitrary hosts, redirects or browser-supplied message/link are allowed. Chrome's push infrastructure receives delivery metadata and encrypted content. No SMS account, TextNow login or phone number is collected.

Browser subscriptions remain in that browser. The request carries its subscription only for this send; the server does not persist or return the endpoint/auth key. Disable unsubscribes this browser, while already accepted notifications may still arrive. The service worker has no fetch/cache handler; it validates the payload and constructs only a protected same-origin link to the exact order. Malformed/legacy messages show fixed fallback text, never supplied URLs. A missing order shows unavailable instead of another order. Push-service acceptance is not device delivery acknowledgement. One attempted send per process-local demo order prevents automatic duplicate attempts, including after uncertain timeouts. Failed/expired/unconfigured notifications do not roll back the simulated order or change its stock snapshot. There is no durable retry, scheduled send or desktop-to-phone pairing. Do not claim multi-worker reliability; an order missing from the current worker cannot notify. The user supplied Android evidence of generic confirmation display; the new selected-order display/tap still requires observed acceptance after HTTPS deployment.
