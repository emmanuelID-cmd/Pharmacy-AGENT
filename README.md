# Pharmacy-AGENT

Pharmacy Inventory Logistics Agent: a collaborative Pursuit assignment in PRD development.

## Team

| Member | Part | Verified contribution/status |
|---|---|---|
| Emmanuel De Jesus | Injection Risk Prevention | Standalone detection, context/action/output guards, synthetic local tester and qualification implemented in Phase 6 |
| Brahim Maouloud | Agent Instructions and Tooling | Read-only inventory reader, openFDA adapter, system prompt and warning display implemented on main |
| Kerrian Gordon | Harness | Deterministic guarded inventory/FDA run, POLICY.md calculations, TrustedFact construction and PRD report implemented in Phase 7 |

## Current status

The PRD remains a draft specification. A FastAPI web application now connects Claude Haiku 5.5 to the existing guarded read tools, deterministic calculations and exact output checks. Its eight views cover Home, Agent, Tools, Harness, Injection Risk Test, Failure State, Demo and Architecture. The active branch is `feature/pharmacy-agent-web-interface`; this build has not been committed, pushed or deployed.

The current web build uses the synthetic fixture and current clock for Agent reviews. The October 7 snapshot can be stale; the separate Demo declares its frozen example clock and makes no model or live FDA calls. Existing Supabase schema/reader work remains on `feature/supabase-inventory-schema`, separate from this branch. No live CVS inventory, staff-write service or approved replacement per-item policy is introduced.

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

`.env.example` documents nonsecret configuration. Local `.env`, optional `.env.local`, and ignored `.env.web` supply server configuration; operating-system variables take precedence. Never commit populated environment files, credentials, or tokens. The web start command is below; the existing harness CLI and standalone tester remain available.

## Technology stack

Python 3.13 with FastAPI/Pydantic, the Anthropic Python SDK, Jinja2, and HTML/CSS/JavaScript. `requirements-web.txt` pins the resolved web dependency set; the hosting `requirements.txt` includes it. Automated checks use the existing unittest conventions. Dependencies are installed inside project `.venv`, not globally.

Python 3.13 is available through the Windows launcher. The prevention, tools, and harness logic uses the standard library and does not adopt the proposed full-application framework. Windows also needs the IANA timezone data pinned in `requirements-harness.txt` for `ZoneInfo("America/New_York")`.

The web application does not merge or alter the separate Supabase database branch.

References: [FastAPI features](https://fastapi.tiangolo.com/features/) and [FDA shortages endpoint](https://open.fda.gov/apis/drug/drugshortages/how-to-use-the-endpoint/).

## Collaboration and updates

### Run the pharmacy web application

From this repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
.\.venv\Scripts\python.exe -B -m uvicorn app:app --host 127.0.0.1 --port 8770 --no-access-log
```

Open http://127.0.0.1:8770. Home defines the shared design across all eight URLs.
Agent runs the real guarded model/tool loop; Demo and Injection Risk Test run
existing deterministic Python behavior without calling a model. Failure State
explicitly illustrates recovery scenarios; it does not inject live failures.

Server-only provider configuration: `ANTHROPIC_API_KEY` (also accepts the existing
`ANTHOPIC_API_KEY` spelling) and `ANTHROPIC_MODEL=claude-haiku-5-5`. The authenticated
Models API verified this active Haiku release on October 13. No key is sent to the
browser, tool arguments, model context or diagnostic output. `.env.local` is
optional; copying a key into multiple files is unnecessary.

Hosted mode requires `PHARMACY_REVIEWER_USERNAME`, `PHARMACY_REVIEWER_PASSWORD`,
and trusted `PHARMACY_ALLOWED_HOSTS`, supplied through hosting environment settings.
Without both reviewer credentials, hosted access fails closed. Local unauthenticated
development requires loopback client/listener and rejects forwarded headers.
Configured remote access requires HTTPS, including in development. Failed Basic
login attempts are throttled per requester after five failures for 60 seconds per
process; one requester's failures do not lock out every reviewer on that worker.
Basic reviewer access is a team prototype
gate, not pharmacy staff role administration; use HTTPS on a host.

Runs have a 50-second application deadline, six model turns, at most 24 attempted
tool calls, explicit provider timeouts and no automatic provider retries. Each
FDA request/retry rechecks remaining time. The browser's Stop waiting aborts the
wait; an already-started read may finish within its independent timeouts. Each
process permits one active review and a ten-second interval; these limits are
not a distributed rate limiter for multiple workers. A timed-out blocking read
continues to occupy the active-read limit until its worker actually finishes.

See [web handoff and contract](docs/planning/WEB-INTERFACE-CONTRACT.md),
[runtime architecture](docs/architecture/Pharmacy-Web-Agent-Architecture.md), and
[hosting preparation](docs/planning/WEB-HOSTING.md). Existing diagrams and decks
remain unchanged. Publishing and Git changes require review of the working preview.

GitHub repository: [emmanuelID-cmd/Pharmacy-AGENT](https://github.com/emmanuelID-cmd/Pharmacy-AGENT), verified private on October 8, 2026. Authentication is verified. The foundation is committed and pushed on `chore/pharmacy-agent-foundation`; review through a pull request before merging into `main`.

Follow [project agent instructions](AGENTS.md) and [team handoff](TEAM-REFERENCE.md). Use feature branches and pull requests for shared work. Review before merging into `main`; do not assign teammate ownership or permissions without agreement.

As approved behavior changes, update the affected PRD sections, policy, architecture references, README status, and team handoff in the same work. Preserve discussion proposals separately until accepted. Record verified push history after every push. Automatic documentation updates require an agent or contributor to perform them; this repository does not run a background updater.

## Repository folders

- `docs/requirements/`: draft PRD, current synthetic policy, and deferred proposals.
- `docs/templates/`: unchanged original PRD template.
- `docs/planning/`: historical foundation plan/review and [setup plan](docs/planning/SETUP-PLAN.md).
- `docs/planning/Phase/`: [phase index](docs/planning/Phase/README.md), Phase1 through Phase7, with sub-phase plans inside their parent.
- `docs/architecture/`: original architecture images.
- `docs/presentations/`: editable slides, slide drafts, team presentation, and future mockups.
- `src/pharmacy_harness/`: deterministic validation, calculation, guarded run, and PRD report.
- `src/pharmacy_tools/`: read-only inventory fixture reader and openFDA adapter.
- `data/synthetic/`: labeled synthetic store 1618 snapshot.

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

Qualification: 66 passing behavior-test methods; 85 label fixtures (55 unsafe detected,30 benign accepted), zero fixture misses/false positives; external text excluded 85/85. These count fixtures, not distinct attack techniques or a general detection rate. SECURITY Round1 found two MAJOR and five MINOR gaps; Round2 verified remediation. A language-model loop, live data provenance and database/deployment controls remain untested.

## Harness implementation

Phase 7 is Kerrian's harness lane. It calls Brahim's read-only tools through Emmanuel's `execute_guarded` dispatcher, validates evidence independently, calculates days of supply under [POLICY.md](docs/requirements/POLICY.md), and prints a human report. It does not run a model.

The checked-in snapshot is dated 2026-10-07. Freeze the clock for a fresh eval; omitting `--run-at` uses the current time and will mark that snapshot stale.

```powershell
python3 -m unittest discover -s tests -q
python3 -m src.pharmacy_harness --run-at 2026-10-07T10:00:00-04:00
```

On Windows, create the project virtual environment if it does not already exist, then install its timezone data and use its interpreter:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-harness.txt
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -B -m src.pharmacy_harness --run-at 2026-10-07T10:00:00-04:00
```

Unit tests stub FDA HTTP. The CLI performs real openFDA reads. Empty, unreadable, or wrong-store sources never mean healthy stock. FDA `NO_MATCH` is not guaranteed supply; `UNAVAILABLE` is not no shortage.

- [Phase 7 plan](docs/planning/Phase/Phase7/PHASE-7-PLAN.md)
- [Phase 7 handoff](docs/planning/Phase/Phase7/PHASE-7-HANDOFF.md)

- [Approved Phase 6 plan](docs/planning/Phase/Phase6/PHASE-6-PLAN.md)
- [Integration contract, coverage matrix and pattern-building process](docs/planning/Phase/Phase6/PHASE-6-HANDOFF.md)
- [Two-round security evidence](docs/planning/Phase/Phase6/PHASE-6-SECURITY.md)
- [Final review and exact changed lines](docs/planning/Phase/Phase6/PHASE-6-REVIEW.md)
- [Green additions/red deletions for updated documents](docs/planning/Phase/Phase6/PHASE-6-CHANGES.html)

Historical five-phase handoff/review/comparison files describe their earlier baseline; Phase 6 supersedes their accepted-label forwarding and no-dispatch statements. Original draft and POLICY.md are preserved. Phase 6 was completed with local commits. The later authorized publication publishes this standalone work through a PR to main; merging requires separate approval.
