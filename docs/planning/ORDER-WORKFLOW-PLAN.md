# Closing inventory and human order demo

Later user-requested correction: the initial one-order-per-close limit below is superseded by
the repeat-order flow in [REPEAT-DEMO-ORDERS.md](REPEAT-DEMO-ORDERS.md). The original approval
record remains preserved; one immutable closing report still applies.

Approved scope: user approved the full PLANNER plan and default recommendations on October 16,
2026, then explicitly separated real-phone SMS/provider setup from the form/report work.
This record describes the approved synthetic implementation. The later preview approval authorizes
grouped commits, a feature-branch push and a PR; deployment, operational pharmacy policy, real order/
notification delivery and merging remain outside that approval.

## Sequence and acceptance

1. Human clicks Close day. Capture one validated pre-order stock snapshot and one report.
2. Inspect all 150 stock rows and exceptions, retaining original snapshot and creation times.
3. Search the 150-item dropdown. Add only selected items to the bottom order list; preserve edits
   when an item is selected twice. Edit/remove or reject the draft.
4. Prefill quantities only from the separate explicit synthetic policy and independently checked
   evidence. Withhold unsupported suggestions and block their demo submission.
5. Human clicks Submit demo order. Record one simulated order without stock changes or a purchase
   order send. Identical submission retries return the same order; changed intents conflict.
6. Show distinct SMS and prioritized next-shift manufacturer notice previews. Keep the original
   report unchanged, even if source data later changes. No second after-order report exists.

Required outcomes: exactly one report and at most one demo order per process-local close;
150 selectable catalog entries; every source row reported or withheld; zero invented quantities,
Agent submissions, operational writes and external sends. Validate client/server errors, concurrent
retries, missing/stale evidence, human edits, rejection, duplicate selection, tab return, mobile
layout, safe text rendering and unchanged existing read-only Agent behavior.

## Defaults and boundaries

- Use the existing Python/FastAPI/Jinja/plain JavaScript stack and shared page design. No new runtime
  or dependency is needed. The original Demo remains 20 rows; the closing workflow uses 150.
- Close is manually triggered. Demo clock: 2026-10-07 18:00 America/New_York; original snapshot
  timestamps are retained. No live source is silently restamped.
- Additive SYNTHETIC-DEMO-REPLENISHMENT-v1 policy: target seven days, confirmed incoming zero,
  one dispensing-unit minimum and multiple, maximum submitted quantity 1,000,000 whole units.
  These are visible synthetic examples, not manufacturer pack conversion or live pharmacy policy.
- The stock report does not invent movements from the absent opening-to-closing ledger.
- One revision-1 simulated order per close. New same-item selection focuses the existing line.
  Cancellation/rejection before submit clears a draft; actual post-submit amendments/cancellations
  require a separate ordering-service scope.
- Notification is preview-only. The next 6:00 AM New York shift is an explicit demo assumption.
  No provider, phone number or real manufacturer is configured. Real SMS remains a separate step.
- Records are process-local, clear on restart and are not durable/cross-worker state. No Supabase,
  staff write service, production scheduler or ordering integration is included.
- New deterministic suggestion logic is an additive harness contract for this approved integration;
  existing calculate_item, stock bins and model output contracts remain unchanged. Coordinate review
  with Kerrian before shared publication; do not rewrite her persistent branch.

## ARCHIVIST baseline and recovery

Tracked source/config/docs (P2) are recoverable from main/origin at
00270b3c11db6fcfd1c43a6c1893ff7b20b96da5. The current tree was clean before implementation,
and all five persistent remote branches matched that commit. No data migrations, existing fixture
changes, secret exports or external backups are needed for this additive demo. Existing source
objects are readable in Git; full isolated restore and independent backup retention were not
verified. Do not discard unrelated work or alter legacy worktrees to restore these changes.
Recovery is selective reversion of this feature's reviewed diff, after checking current status.

## Workflow

Temporary branch: feature/order-workflow-demo; owner Emmanuel; target main. Keep Supabase work
on feature/supabase-migration if it is separately approved later. Preview before commit; run the
full unittest suite and qualification CLI, browser flow/keyboard/mobile checks, exactly two
sequential security rounds and final read-only review. Git publication and merge remain subject
to existing preview/approval gates; delete the temporary branch only after merged-work/archive/
activity checks and the required deletion approval. Do not modify external AGENTS in this task.

## Design decisions

Primary user: an authorized inventory reviewer preparing a synthetic closing review. Search and
progressive disclosure reduce 150-item choice overload; queued rows group evidence, quantity and
remove actions together; the shared shell and native dropdown preserve familiar interaction.
These choices follow the relevant choice-overload, proximity and familiar-pattern prompts from
[Laws of UX](https://lawsofux.com/); they do not substitute for user research. Quantity errors
retain work, identify fields and remain keyboard accessible. The report is collapsed for detailed
inspection; the order list shows only selected items. Phone delivery is not simulated as success.
