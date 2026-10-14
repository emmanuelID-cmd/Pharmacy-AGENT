# Pharmacy-AGENT

Pharmacy Inventory Logistics Agent: a collaborative Pursuit assignment in PRD development.

## Team

| Member | Part | Verified contribution/status |
|---|---|---|
| Emmanuel De Jesus | Injection Risk Prevention | Standalone detection, context/action/output guards, synthetic local tester and qualification implemented in Phase 6 |
| Brahim Maouloud | Agent Instructions and Tooling | Read-only inventory reader, openFDA adapter, system prompt and warning display implemented on main |
| Kerrian Gordon | Harness | Deterministic guarded inventory/FDA run, POLICY.md calculations, TrustedFact construction, PRD report, and one guarded model turn implemented in Phases 7–8 |

## Current status

The PRD remains a draft specification. Injection prevention, read-only inventory/FDA tools, and a deterministic harness that calls those tools are implemented. The initial private Supabase schema, synthetic seed, and restricted database reader are also implemented. The default tool fixture now has 150 distinct public FDA-listed human-prescription product/package identities linked to synthetic stock and usage. FDA listings are not approval claims; no live CVS inventory is present. One optional guarded model turn is implemented; a private FastAPI web preview is also implemented. Do not train a model. The new catalog migration is local and has not been applied to hosted Supabase.

The web Agent uses the 150-row catalog fixture; Demo preserves the original 20-row synthetic evaluation fixture explicitly. The harness CLI defaults to the 150-row public-identity/synthetic-stock fixture. Neither path uses live CVS inventory or the database adapter. Hosted catalog migration and web deployment remain pending.

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

Database: Supabase PostgreSQL 17.11, project `xrptinavijhwvydoqdni`. See [schema and migration guide](docs/database/SCHEMA.md). `read_store_inventory` defaults to the 150-row public-identity fixture; the original 20-row fault/evaluation fixture remains available with `--legacy-fixture`. The dedicated database reader remains a separate tool path; the harness still uses the file fixture by default.

Medication identity: the checked-in catalog comes from the public [openFDA NDC directory](https://open.fda.gov/apis/drug/ndc/) and NLM RxNorm/RxClass ATC lookups. One package NDC represents each of 150 distinct product NDCs. NLM mapping gaps remain explicit. Every quantity and usage value is synthetic and linked to its catalog package by exact package NDC; no pharmacy stock feed is connected.

The web application keeps the separate Supabase database adapter unconnected; the Agent uses the catalog fixture and Demo uses the historical fixture.

References: [FastAPI features](https://fastapi.tiangolo.com/features/) and [FDA shortages endpoint](https://open.fda.gov/apis/drug/drugshortages/how-to-use-the-endpoint/).

## Collaboration and updates

### Run the pharmacy web application

From this repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
.\.venv\Scripts\python.exe -B -m uvicorn app:app --host 127.0.0.1 --port 8770 --no-access-log
```

Open http://127.0.0.1:8770. Home defines the shared design across all eight URLs.
Home includes the full 150-item catalog joined to local synthetic stock and all
14 daily usage values by exact package NDC. The table scrolls within its panel;
source text is escaped for human inspection and does not enter model context.
Navigation uses the shared tabs without a separate in-page Back control.
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

Local Agent runs have a 120-second application deadline, six model turns, at most 24 attempted
tool calls and 90-second per-model caps; hosted settings retain a 50-second run and
45-second model cap. Tool decisions allow up to 4,096 output tokens and the final
150-row exact report allows up to 24,576. There are no automatic provider retries. Each
FDA request/retry rechecks remaining time. The browser's Stop waiting aborts the
wait; an already-started read may finish within its independent timeouts. Each
process permits one active review and a ten-second interval; these limits are
not a distributed rate limiter for multiple workers. A timed-out blocking read
continues to occupy the active-read limit until its worker actually finishes.

The web loop stops on an explicit provider refusal (`MODEL_REFUSAL`) or a missing/empty
response (`MODEL_NO_RESPONSE`). Unexpected provider exceptions and unknown provider
error codes become `MODEL_ERROR`; raw refusal text and error details are omitted.
Turn exhaustion remains `MODEL_TURN_LIMIT`. Any independently verified partial
report survives with a manual-review warning; no further reads or automatic retries run.
These paths are covered by synthetic scripted-provider tests, without live API calls.

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
- `data/catalog/`: public FDA/NLM product, package and classification snapshot with source metadata.
- `data/synthetic/`: labeled 150-row synthetic store 1618 snapshot and retained 20-row evaluation fixture.

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

Qualification: 66 passing behavior-test methods; 85 label fixtures (55 unsafe detected,30 benign accepted), zero fixture misses/false positives; external text excluded 85/85. These count fixtures, not distinct attack techniques or a general detection rate. SECURITY Round1 found two MAJOR and five MINOR gaps; Round2 verified remediation. Historical Phase 6 qualification does not exercise live models; real pharmacy stock provenance and hosted deployment are outside this fixture.

## Harness implementation

Phase 7 is Kerrian's harness lane. It calls Brahim's read-only tools through Emmanuel's `execute_guarded` dispatcher, validates evidence independently, calculates days of supply under [POLICY.md](docs/requirements/POLICY.md), and prints a human report. It does not run a model.

The default 150-product synthetic snapshot is dated 2026-10-07. The CLI defaults to that evaluation clock; `--now` uses the current time and marks it stale. Add `--legacy-fixture` to replay the original 20-row fault/evaluation cases.

```powershell
python3 -m unittest discover -s tests -q
python3 -m src.pharmacy_harness --offline
python3 -m src.pharmacy_harness --offline --model-copy
python3 -m src.pharmacy_harness --offline --json
```

On Windows, create the project virtual environment if it does not already exist, then install its timezone data and use its interpreter:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-harness.txt
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -B -m src.pharmacy_harness --offline
.\.venv\Scripts\python.exe -B -m src.pharmacy_harness --offline --model-copy
.\.venv\Scripts\python.exe -B -m src.pharmacy_harness --offline --json
```

Unit tests stub FDA HTTP. The CLI defaults to the Eval Card clock and prints a manager table. `--offline` uses the recorded Case 1 FDA payload (no network). `--model-copy` runs one guarded model turn without an LLM; `--model` uses `PHARMACY_MODEL_URL` and rejects invented numbers. Omit `--offline` for a live openFDA read; `--now` uses the current clock; `--json` prints `harness-report-v1`. Empty, unreadable, or wrong-store sources never mean healthy stock. FDA `NO_MATCH` is not guaranteed supply; `UNAVAILABLE` is not no shortage. Every exact-match FDA record is listed; conflicting records are `NEEDS_REVIEW` and never change the local class.

- [Phase 7 plan](docs/planning/Phase/Phase7/PHASE-7-PLAN.md)
- [Phase 7 handoff](docs/planning/Phase/Phase7/PHASE-7-HANDOFF.md)

- [Approved Phase 6 plan](docs/planning/Phase/Phase6/PHASE-6-PLAN.md)
- [Integration contract, coverage matrix and pattern-building process](docs/planning/Phase/Phase6/PHASE-6-HANDOFF.md)
- [Two-round security evidence](docs/planning/Phase/Phase6/PHASE-6-SECURITY.md)
- [Final review and exact changed lines](docs/planning/Phase/Phase6/PHASE-6-REVIEW.md)
- [Green additions/red deletions for updated documents](docs/planning/Phase/Phase6/PHASE-6-CHANGES.html)

Historical five-phase handoff/review/comparison files describe their earlier baseline; Phase 6 supersedes their accepted-label forwarding and no-dispatch statements. Original draft and POLICY.md are preserved. Phase 6 was completed with local commits. The later authorized publication publishes this standalone work through a PR to main; merging requires separate approval.

## Local read-only database check

Install the optional database requirements in the project virtual environment, then run `.venv/Scripts/python.exe -B scripts/check_database_reader.py`. It loads only the ignored generated `.env.database` credential file and prints safe counts. This read-only tool returns untrusted source evidence; it does not validate pharmacy truth, calculate supply, or approve operational actions. See [backend reader guide](docs/database/BACKEND-READER.md).
