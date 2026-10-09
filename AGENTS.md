# Pharmacy-AGENT project instructions

This is a collaborative assignment for Kerrian Gordan, Emmanuel De Jesus, and Brahim Maouloud. The active root is this Pharmacy-Agent-Role directory. Target GitHub owner is emmanuelID-cmd; intended repository name is Pharmacy-AGENT.

## External instruction source

Read `C:/Users/Github/AGENTS/AGENTS.md` and its relevant linked documents before acting. Always read `agents/planner.md` first. Follow `git.md`, `workflow/development.md`, and `workflow/project-initialization.md`. If a required external document is unavailable, report it instead of inventing instructions. Other machines must configure access to the canonical instruction repository, https://github.com/emmanuelID-cmd/AGENTS.git.

User instructions take precedence. Use the prescribed PLANNER, ARCHIVIST, BUILDER, SECURITY when applicable, REVIEWER, and FIXER when applicable handoffs. Real sub-agents are permitted when necessary for bounded independent work; a role handoff alone is not a spawned agent.

## Requirements and documentation

The PRD is a draft. SQL/database work and the proposed-change document remain deferred. Do not silently apply proposed requirements or infer live pharmacy access. Preserve the original template and historical documentation.

Update relevant PRD, policy, README, and architecture documentation alongside approved behavior changes. Keep synthetic data labels, read-only agent authority, and human review explicit. Do not use Team Alignment until the user authorizes it.

## Team Reference and Git

Use the Team Reference skill and maintain `TEAM-REFERENCE.md` inside this project. Inspect actual Git status/history before handoffs. Append verified push timestamps with America/New_York UTC offsets and commit ranges after pushes; do not invent attribution or push evidence.

Follow the external Git approval gates, Conventional Commits, and collaboration body sections: What changed, Why, Collaboration, Boundaries, Validation. Propose branch names before creation. Use pull requests for shared changes; merging into main requires approval and required checks. Preview changes before committing. Never stage unrelated work or secrets. Repository creation does not grant teammate invitations or alter GitHub access permissions.

## Approved responsibilities and Phase 6 boundary

| Member | Part | Verified contribution/status |
|---|---|---|
| Emmanuel De Jesus | Injection Risk Prevention | Standalone detection, context/action/output guards, synthetic local tester and qualification implemented in Phase 6 |
| Brahim Maouloud | Agent Instructions and Tooling | Assigned part; implementation status not established by this build |
| Kerrian Gordan | Harness | Assigned part; implementation status not established by this build |

Phase 6 is the complete standalone injection-prevention task, with sub-phases 6.1–6.6; preserve historical numbering 1–5. Use [plan](docs/planning/PHASE-6-PLAN.md), [integration contract](docs/planning/PHASE-6-HANDOFF.md) and [review](docs/planning/PHASE-6-REVIEW.md). Do not infer that the integrated harness or teammate tools are implemented.

All source/tool/user objects are untrusted. Do not pass submitted booleans, dictionaries or descriptions as trusted facts. Construct TrustedFact only after independent harness verification of identity, units, quantities, usage, freshness and approved item policy. Missing required evidence or binding failure withholds the affected result; optional unsafe descriptions are excluded while supported facts survive. Never reinsert external text after assembly, including ACCEPT text. Keep clinical/patient work, calculations, staff writes and live API adapters in their assigned future scope.

The prevention dispatcher authorizes fixed reads only, using captured arguments and trusted callbacks. Actual adapters need independent IO timeouts; RunBudget cannot interrupt a blocking callback. Never enable order/write/SQL/shell/secret/outbound-disclosure tools. Separate authenticated staff services and read-only database grants must be tested when built. Server-side location and parameterized SQL do not establish prompt-injection safety.

Run the full local unittest suite and qualification CLI before handoff; display misses, containment and false positives separately. New patterns require a prior failing synthetic case, a benign counterexample, rationale and versioned review. Do not train a model or collect hidden reasoning through this component. SECURITY runs exactly two sequential rounds with remediation accounted for; final REVIEWER is read-only.

Keep Pharmacy commits, staging and push history entirely separate from C:/Users/Github/AGENTS. Current authorization is local Pharmacy commits only, with no push/merge. Preserve unrelated Mod edits and untracked skills; never stage them wholesale. Before any later authorized push, follow external git.md's normal commit body plus appended consolidated ##REVIEW/#RANGE convention. No push-review marker is needed merely to complete a local phase.
