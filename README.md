# Pharmacy-AGENT

Pharmacy Inventory Logistics Agent: a collaborative Pursuit assignment in PRD development.

## Team

- Kerrian Gordan
- Emmanuel De Jesus
- Brahim Maouloud

## Current status

The PRD is a draft. No application or live CVS integration exists. SQL, database implementation, per-item policy changes, and other proposed requirements remain deferred while the team discusses the specification. Team Alignment is excluded for now.

## Product foundation

The proposed agent helps an inventory manager at one configured store review synthetic stock and aggregate usage, calculate days of supply, and inspect separate FDA national shortage context. It provides recommendations for human review. It has no ordering, dispensing, clinical, inventory-write, or policy-edit authority. No patient records are in scope.

The complete PRD, including journeys, priorities, success metrics, tool contracts, safeguards, prompts, and evaluation cases, remains the requirements source:

- [Draft PRD](Pharmacy%20Inventory%20Logistics%5BPRD%5D-draft.md)
- [Original PRD template](Copy%20of%2020260515%20PRD%20Template%20%281%29.md)
- [Current synthetic policy](POLICY.md)
- [Proposed changes: discussion only](PRD-POLICY-PROPOSED-CHANGES.md)
- [Original documentation plan](PLAN.md)
- [Original documentation review](REVIEW.md)
- [Digital architecture](Pharmacy-Agent-Architecture-Digital.png)
- [Handwritten architecture](Pharmacy-Agent-Architecture-Handwritten.png)
- [Web architecture reference](Web-Application-Architecture-Reference.png)

Architecture images are design references, not evidence of implemented controls. Proposed changes do not supersede the current PRD or policy until explicitly approved and synchronized.

## Workspace and configuration

Open `Pharmacy-AGENT.code-workspace` in VS Code. Its folder is this repository root, `Pharmacy-Agent-Role`.

`.env.example` documents nonsecret configuration. `.env` is local and ignored; it initially contains only safe placeholders. Never commit populated environment files, credentials, or tokens. There is no application start command yet.

## Proposed technology stack

Python with FastAPI and Pydantic for validated backend/tool contracts; pytest for deterministic calculations and fault cases; simple HTML/CSS/JavaScript for the initial interface. Versions and dependencies will be selected and locked during the approved application plan. No packages are installed by this setup.

Python was unavailable through `python` on PATH during inspection. Verify the Windows launcher before recommending an installation. Git is available. Node.js is available but is not required by this documentation setup.

SQLite and other SQL/database work are deferred. No database engine is selected for implementation.

References: [FastAPI features](https://fastapi.tiangolo.com/features/) and [FDA shortages endpoint](https://open.fda.gov/apis/drug/drugshortages/how-to-use-the-endpoint/).

## Collaboration and updates

GitHub repository: [emmanuelID-cmd/Pharmacy-AGENT](https://github.com/emmanuelID-cmd/Pharmacy-AGENT), verified private on October 8, 2026. Authentication is verified. The foundation is committed and pushed on `chore/pharmacy-agent-foundation`; review through a pull request before merging into `main`.

Follow [project agent instructions](AGENTS.md) and [team handoff](TEAM-REFERENCE.md). Use feature branches and pull requests for shared work. Review before merging into `main`; do not assign teammate ownership or permissions without agreement.

As approved behavior changes, update the affected PRD sections, policy, architecture references, README status, and team handoff in the same work. Preserve discussion proposals separately until accepted. Record verified push history after every push. Automatic documentation updates require an agent or contributor to perform them; this repository does not run a background updater.
