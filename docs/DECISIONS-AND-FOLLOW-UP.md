# Decisions and follow-up

## Human-controlled replenishment demo extension

Status: Proposed; not implemented or authorized for operational use.

- Requirement: Demonstrate a multi-step synthetic workflow with validated inventory reports, quantity recommendations from an approved fixture policy, an unsaved order form with quantity fields prefilled by the Agent, explicit human review and simulated submission, a closing inventory report, and one manufacturer notice per human-submitted order at the start of the manufacturer's morning shift (6:00 AM local target). Prioritize notice lines by inventory status (CRITICAL before LOW), not clinical or patient priority.
- Affected files: `docs/requirements/Pharmacy Inventory Logistics[PRD]-Mod.md`, `docs/requirements/POLICY.md`, and `README.md`.
- Implementation note: Keep this as a synthetic demo until separately approved. The Agent must not persist, submit, transmit, or write orders. Drafts and submitted-but-unreceived orders remain separate from physical on-hand inventory. No external manufacturer notice is sent by the demo.
- Open questions: Approve the quantity formula and required source fields; confirm the manufacturer's timezone and exact shift-start cutoff; choose immediate handling or next shift for orders submitted after shift start; identify channel and recipient; decide whether human submission sends the purchase order or queues a separate notice; define acknowledgements, amendments, cancellations, retries, and idempotency; decide whether this remains demo-only or proceeds to an operational integration.
