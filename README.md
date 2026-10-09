# Pharmacy-AGENT

Pharmacy Inventory Logistics Agent: a collaborative Pursuit assignment in PRD development.

## Team

| Member | Part | Verified contribution/status |
|---|---|---|
| Emmanuel De Jesus | Injection Risk Prevention | Standalone detection, context/action/output guards, synthetic local tester and qualification implemented in Phase 6 |
| Brahim Maouloud | Agent Instructions and Tooling | Assigned part; implementation status not established by this build |
| Kerrian Gordan | Harness | Assigned part; implementation status not established by this build |

## Current status

The PRD remains a draft specification. A standalone injection-prevention package and local synthetic visual tester are implemented; the integrated pharmacy application and live CVS integration are not built. SQL, database implementation, per-item policy changes, and other proposed requirements remain deferred while the team discusses the specification. Team Alignment is excluded for now.

## Product foundation

The proposed agent helps an inventory manager at one configured store review synthetic stock and aggregate usage, calculate days of supply, and inspect separate FDA national shortage context. It provides recommendations for human review. It has no ordering, dispensing, clinical, inventory-write, or policy-edit authority. No patient records are in scope.

The complete PRD, including journeys, priorities, success metrics, tool contracts, safeguards, prompts, and evaluation cases, remains the requirements source:

- [Updated PRD — MOD review copy](docs/requirements/Pharmacy%20Inventory%20Logistics%5BPRD%5D-Mod.md)
- [PRD changes report](docs/requirements/Pharmacy%20Inventory%20Logistics%5BPRD%5D-Changes.html)
- [Original draft PRD](docs/requirements/Pharmacy%20Inventory%20Logistics%5BPRD%5D-draft.md)
- [Original PRD template](docs/templates/Copy%20of%2020260515%20PRD%20Template%20%281%29.md)
- [Current synthetic policy](docs/requirements/POLICY.md)
- [Proposed changes: discussion only](docs/requirements/PRD-POLICY-PROPOSED-CHANGES.md)
- [Original documentation plan](docs/planning/PLAN.md)
- [Original documentation review](docs/planning/REVIEW.md)
- [Digital architecture](docs/architecture/Pharmacy-Agent-Architecture-Digital.png)
- [Handwritten architecture](docs/architecture/Pharmacy-Agent-Architecture-Handwritten.png)
- [Web architecture reference](docs/architecture/Web-Application-Architecture-Reference.png)

The MOD PRD is the updated consolidated review copy; it does not automatically replace the original draft or POLICY.md. The HTML report preserves the comparison prepared before this commit.

Architecture images are design references, not evidence of implemented controls. Proposed changes do not supersede the current PRD or policy until explicitly approved and synchronized.

## Workspace and configuration

Open `Pharmacy-AGENT.code-workspace` in VS Code. Its folder is this repository root, `Pharmacy-Agent-Role`.

`.env.example` documents nonsecret configuration. `.env` is local and ignored; it initially contains only safe placeholders. Never commit populated environment files, credentials, or tokens. The standalone synthetic tester has the start command below; the integrated pharmacy application has no start command yet.

## Proposed technology stack

Python with FastAPI and Pydantic for validated backend/tool contracts; pytest for deterministic calculations and fault cases; simple HTML/CSS/JavaScript for the initial interface. Versions and dependencies will be selected and locked during the approved application plan. No packages are installed by this setup.

Python 3.13 is available through the Windows launcher. The prevention component uses only the standard library and does not adopt the proposed full-application framework.

SQLite and other SQL/database work are deferred. No database engine is selected for implementation.

References: [FastAPI features](https://fastapi.tiangolo.com/features/) and [FDA shortages endpoint](https://open.fda.gov/apis/drug/drugshortages/how-to-use-the-endpoint/).

## Collaboration and updates

GitHub repository: [emmanuelID-cmd/Pharmacy-AGENT](https://github.com/emmanuelID-cmd/Pharmacy-AGENT), verified private on October 8, 2026. Authentication is verified. The foundation is committed and pushed on `chore/pharmacy-agent-foundation`; review through a pull request before merging into `main`.

Follow [project agent instructions](AGENTS.md) and [team handoff](TEAM-REFERENCE.md). Use feature branches and pull requests for shared work. Review before merging into `main`; do not assign teammate ownership or permissions without agreement.

As approved behavior changes, update the affected PRD sections, policy, architecture references, README status, and team handoff in the same work. Preserve discussion proposals separately until accepted. Record verified push history after every push. Automatic documentation updates require an agent or contributor to perform them; this repository does not run a background updater.

## Repository folders

- `docs/requirements/`: draft PRD, current synthetic policy, and deferred proposals.
- `docs/templates/`: unchanged original PRD template.
- `docs/planning/`: historical foundation plan/review and [setup plan](docs/planning/SETUP-PLAN.md).
- `docs/planning/Phase/`: [phase index](docs/planning/Phase/README.md), Phase1 through Phase6, with sub-phase plans inside their parent.
- `docs/architecture/`: original architecture images.

README, AGENTS, Team Reference, workspace, and environment configuration remain at the root. Historical documents retain their original filenames and references; use this directory map to locate them.

## Injection prevention implementation

Phase 6 continues completed historical Phases 1–5 on `feature/injection-risk-prevention`. This is Emmanuel's standalone prevention lane. Typed facts and fixed read callbacks are supplied by trusted harness code; a model, live source, database, staff-write service and operational calculations are not implemented here. Server-side placement alone does not make a record safe.

| Boundary | Implemented behavior | Evidence |
|---|---|---|
| Intake | Bounded UTF-8 JSON, source shapes, hidden/control checks and versioned instruction signals | Contract, Unicode, evasion and source tests |
| Context | All external free text omitted, including detector misses; independently verified facts only | Binding/missing-evidence and reinsertion tests |
| Action | Snapshot then authorize; fixed store/NDC read scope; forbidden tools denied before executor | Mutation, permission and simulated-call tests |
| Output | Exact structured facts/warnings checked; altered reports produce deterministic manual-review fallback | Tampering and false action-claim tests |
| Local tester | Loopback-only actual Python results, visible character evidence, safe display and stale-result handling | Local HTTP tests and desktop/mobile browser checks |

From this repository root:

```powershell
py -3.13 -m unittest discover -s tests -q
py -3.13 -m src.injection_prevention.qualification
py -3.13 -m src.injection_prevention.local_tester --port 8765
```

Open http://127.0.0.1:8765 after starting the tester. No credentials or third-party packages are required. This page executes synthetic controls; it does not call a model, FDA/CVS, SQL, a shell or an ordering service.

Qualification: 66 passing behavior-test methods; 85 label fixtures (55 unsafe detected,30 benign accepted), zero fixture misses/false positives; external text excluded 85/85. These count fixtures, not distinct attack techniques or a general detection rate. SECURITY Round1 found two MAJOR and five MINOR gaps; Round2 verified remediation. Live model/harness, real data provenance and database/deployment controls remain untested.

- [Approved Phase 6 plan](docs/planning/Phase/Phase6/PHASE-6-PLAN.md)
- [Integration contract, coverage matrix and pattern-building process](docs/planning/Phase/Phase6/PHASE-6-HANDOFF.md)
- [Two-round security evidence](docs/planning/Phase/Phase6/PHASE-6-SECURITY.md)
- [Final review and exact changed lines](docs/planning/Phase/Phase6/PHASE-6-REVIEW.md)
- [Green additions/red deletions for updated documents](docs/planning/Phase/Phase6/PHASE-6-CHANGES.html)

Historical five-phase handoff/review/comparison files describe their earlier baseline; Phase 6 supersedes their accepted-label forwarding and no-dispatch statements. Original draft and POLICY.md are preserved. Phase 6 was completed with local commits. The later authorized publication publishes this standalone work through a PR to main; merging requires separate approval.
