# Pharmacy Inventory Logistics — approved documentation plan

Date: October 7, 2026. Status: PRD preparation authorized; application implementation is a later step.

## Context

Inspected C:/Users/Github/AGENTS/AGENTS.md, README.md, agents/planner.md, and workflow/project-initialization.md. The workspace is Windows x64 with PowerShell 7.6.5 and has no application, runtime manifest, lockfile, database configuration, deployment configuration, or existing product conventions. The uploaded Copy of 20260515 PRD Template (1).md is the authoritative structure. Source SHA-256: FEB08AA6FE09C5A162F86F2057271E7817892C04866F3A46AC1F30C4D7A68BBF.

## Approach

Create documentation for a net new single-store agent before application implementation. Use synthetic local stock and usage, real package identifiers, and a required read-only FDA Drug Shortages API integration in the eventual prototype. No software stack or installation is required to produce Markdown documents. A framework/database scaffold is deferred because the inventory interface is not yet implemented.

## Steps

1. PLAN.md — record authorization, scope, structure, and unresolved live-use prerequisites.
2. Pharmacy Inventory Logistics[PRD]-draft.md — copy the actual uploaded template, then complete every section and remove instructions/placeholders.
3. POLICY.md — define prototype calculation, freshness, threshold, identity, and manual-review rules; link it from the PRD.
4. REVIEW.md — record structural and line checks, arithmetic review, safeguards, and limitations.

Steps are sequential: policy and PRD must agree before review. User approved proceeding on October 7 and specified that draft belongs in the filename, not the agent name.

## Acceptance criteria

- Preserve all named template sections in order; remove direction boxes, examples, and placeholder content.
- Preserve the original template; work on a copy.
- Label synthetic inputs, prototype policies, and proposed metric targets.
- Include one local inventory reader and one real FDA API reader; no invented CVS endpoint.
- Define auditable calculations and three prewritten evaluation cases.
- Missing required local data yields manual review; unavailable FDA context never implies normal supply.
- Restrict v1 to recommendations for one store with no clinical, purchasing, dispensing, or inventory write authority.

## Out of scope

Application code, deployment, real CVS integration, patient records, multi-store operations, NDC Directory integration, purchasing, clinical decisions, and Git publication.

## Unknowns

- Authorized CVS inventory access/schema: use synthetic input for the prototype; verify an authorized deidentified export before live integration.
- Pharmacy-approved thresholds/freshness rules: use explicitly synthetic policy values; verify authorized operational policy before live use.
- Final branding and named product owner: descriptive working name and commissioning project team attribution only; no invented personal names.
- Live API behavior and validated fixture identity: verify exact package matching and capture a dated response during implementation; evaluation fixtures are explicitly synthetic and not a live validation claim.

These are live-build prerequisites, not blockers to the authorized draft PRD. Recommendations were resolved in conversation: CVS #1618 as location context, synthetic inventory, POLICY.md, and required FDA integration.

## Plan handoff

Proceed with the approved documentation work under ARCHIVIST preservation guidance, BUILDER drafting, and REVIEWER checks. Preserve the original source; new deliverables can be regenerated from it and this plan. No backup transfer, installation, branch, commit, or push is authorized or required. Application implementation follows a separate plan after document review.
