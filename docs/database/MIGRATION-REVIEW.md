# Migration review — October 13, 2026

## Acceptance criteria

- Target identity and empty starting schema: MET through CLI read-only queries.
- Versioned schema: MET; two CLI-generated migrations deployed and recorded.
- Source preservation and repeatable seed: MET; raw payload retained, seed run twice in rollback tests, counts stable.
- Unknown/invalid handling: MET; negative/missing stock null, incomplete window excluded from dated usage, policies not invented.
- Access boundaries: MET; RLS enabled, reader SELECT succeeds, reader insert/update/delete and raw payload read denied, anon/authenticated reads denied.
- Application regressions: MET; 94 tests and 85 selected fixture outcomes pass.
- Presentation cleanup preserved: MET; earlier rename and README folder addition remain uncommitted and separate.

## Security rounds

Round 1: SQL parsing issue corrected, and permission testing adjusted with transaction-only membership. Complete rollback test passed; no schema/role persisted.
Round 2: same constraints, idempotency, preservation and role checks passed sequentially; rollback confirmed again. No public API grants, reader memberships or Agent write tools deployed.

## Findings and limits

CLI .env parsing failure is unresolved; deployment bypassed it with byte-verified nonsecret temporary files. No secret values were printed. Docker unavailable; transaction testing is not an independent local database. Snapshot remains deliberately stale. Reader account provisioning, staff authorization, API exposure and tool adapter integration are not implemented.

## Line scan

- Both SQL migrations: table keys/checks, unit bindings, policy intervals, grants, RLS and indexes reviewed.
- seed.sql: literal escaping, source SHA, idempotency, unknown handling and date mapping reviewed.
- tests/inventory_contract.sql: allow/deny assertions and fixture boundary expectations reviewed.
- config.toml and Supabase-generated ignore rules: project-local defaults; no embedded credentials or pharmacy API exposure.
- README, AGENTS, Team Reference and schema guide: implementation status, integration limits and existing user edits preserved.

## Verdict

APPROVE within the initial synthetic schema/seed scope. No live-readiness claim. No Git publication performed.

## Backend follow-up review — October 13, 2026

The initial review above records the schema-stage boundary. The subsequently approved backend login and separate reader are implemented and live-tested. Migration 20261013042410 is recorded; two rollback-only role tests and actual-login permission probes passed. Reader SELECT succeeds; write, raw-import and escalation probes fail. 103 tests and 85 selected qualification fixtures pass. Credentials are in ignored .env.database; no password is in migrations or tracked sources. Staff writes, API exposure and full harness integration remain pending. See BACKEND-READER.md for the updated boundary.

## Synchronization review - October 13, 2026

## Commit grouping preview

HEAD: bcba78d includes the initial approved database/backend implementation. Nothing is staged.

Group 1: feat(catalog): add public medication identities and synthetic SQL seed

Group 2: feat(harness): review 150 synthetic products through bounded FDA batches

One cohesive catalog/data migration group; one dependent reader/guard/harness integration group. No separate error-control correction exists in the pending baseline.

## Line Return Reference

- `README.md`: prior 15 deleted/replaced; current 15 added/replaced; prior 51 deleted/replaced; current 51-53 added/replaced; prior 73 deleted/replaced; current 75-76 added/replaced; prior 99 deleted/replaced; current 102 added/replaced; prior 105 deleted/replaced; current 108 added/replaced
- `docs/database/BACKEND-READER.md`: current 42-45 added/replaced
- `docs/database/SCHEMA.md`: prior 23 deleted/replaced; current 23 added/replaced; current 46-53 added/replaced
- `src/injection_prevention/action_guard.py`: prior 7 deleted/replaced; current 7 added/replaced; prior 21 deleted/replaced; current 21 added/replaced; current 37-43 added/replaced; prior 85 deleted/replaced; current 92-95 added/replaced; prior 104 deleted/replaced; current 114-116 added/replaced
- `src/injection_prevention/boundary_contracts.py`: current 36-47 added/replaced
- `src/injection_prevention/output_guard.py`: prior 4 deleted/replaced; current 4 added/replaced; current 19-20 added/replaced; prior 20 deleted/replaced; current 22 added/replaced; prior 39 deleted/replaced; current 41 added/replaced
- `src/injection_prevention/safe_context.py`: prior 5 deleted/replaced; current 5 added/replaced; prior 68 deleted/replaced; current 68 added/replaced; prior 115 deleted/replaced; current 115 added/replaced; prior 117 deleted/replaced; current 117-119 added/replaced; prior 153-155 deleted/replaced; current 155-159 added/replaced; prior 158 deleted/replaced; current 162 added/replaced; prior 171 deleted/replaced; current 175 added/replaced
- `src/pharmacy_harness/__main__.py`: current 8 added/replaced; current 21-22 added/replaced; prior 21 deleted/replaced; current 24-25 added/replaced
- `src/pharmacy_harness/run.py`: prior 4 deleted/replaced; current 4 added/replaced; prior 8 deleted/replaced; current 8 added/replaced; prior 55-57 deleted/replaced; prior 72-73 deleted/replaced; current 69-70 added/replaced; prior 77-78 deleted/replaced; current 74-76 added/replaced; prior 80 deleted/replaced; current 78 added/replaced; prior 85-92 deleted/replaced; current 83-92 added/replaced
- `src/pharmacy_tools/__init__.py`: prior 2 deleted/replaced; current 2 added/replaced; prior 7 deleted/replaced; current 7-8 added/replaced
- `src/pharmacy_tools/database_inventory.py`: current 11 added/replaced; current 14 added/replaced; prior 14 deleted/replaced; current 16 added/replaced; prior 45 deleted/replaced; current 47 added/replaced; prior 57 deleted/replaced; current 59 added/replaced; prior 64 deleted/replaced; current 66 added/replaced; prior 66 deleted/replaced; current 68 added/replaced; prior 79 deleted/replaced; current 81 added/replaced; prior 107 deleted/replaced; current 109 added/replaced
- `src/pharmacy_tools/fda.py`: prior 26 deleted/replaced; current 26 added/replaced; prior 28 deleted/replaced; current 28 added/replaced; current 36-37 added/replaced; current 163-226 added/replaced
- `src/pharmacy_tools/instructions.py`: prior 9 deleted/replaced; current 9 added/replaced; prior 15 deleted/replaced; current 15 added/replaced; prior 23 deleted/replaced; current 23 added/replaced; prior 68-69 deleted/replaced; current 68-69 added/replaced; prior 72-73 deleted/replaced; current 72-74 added/replaced
- `src/pharmacy_tools/inventory.py`: current 11 added/replaced; current 14 added/replaced; prior 15 deleted/replaced; current 17-19 added/replaced; prior 40 deleted/replaced; current 44 added/replaced
- `supabase/seed.sql`: current 24-88 added/replaced
- `supabase/tests/backend_reader.sql`: prior 6 deleted/replaced; current 6 added/replaced
- `supabase/tests/inventory_contract.sql`: prior 3-7 deleted/replaced; current 3-7 added/replaced; prior 10 deleted/replaced; current 10 added/replaced; prior 13 deleted/replaced; current 13-25 added/replaced; prior 27 deleted/replaced; current 39-40 added/replaced
- `tests/test_action_output_guards.py`: prior 7 deleted/replaced; current 7 added/replaced; current 12-27 added/replaced
- `tests/test_agent_instructions.py`: prior 28 deleted/replaced; current 28 added/replaced; prior 30 deleted/replaced; current 30 added/replaced; prior 43 deleted/replaced; current 43 added/replaced
- `tests/test_database_inventory.py`: prior 51 deleted/replaced; current 51-55 added/replaced
- `tests/test_eval_card.py`: prior 10 deleted/replaced; current 10 added/replaced; prior 33 deleted/replaced; current 33 added/replaced; prior 67 deleted/replaced; current 67-68 added/replaced; prior 83 deleted/replaced; current 84 added/replaced; prior 90 deleted/replaced; current 91 added/replaced
- `tests/test_fda_shortage_adapter.py`: prior 9 deleted/replaced; current 9 added/replaced; current 54-84 added/replaced
- `tests/test_harness_calculate.py`: prior 7 deleted/replaced; current 7 added/replaced; prior 42 deleted/replaced; current 42 added/replaced; prior 112 deleted/replaced; current 112 added/replaced
- `tests/test_harness_invariants.py`: prior 9 deleted/replaced; current 9 added/replaced; prior 32-33 deleted/replaced; current 32-33 added/replaced; prior 41 deleted/replaced; current 41 added/replaced; prior 63 deleted/replaced; current 63 added/replaced
- `tests/test_harness_run.py`: prior 9 deleted/replaced; current 9 added/replaced; current 28 added/replaced; current 42-55 added/replaced; prior 65 deleted/replaced; current 80 added/replaced; prior 104 deleted/replaced; current 119 added/replaced
- `tests/test_harness_validation.py`: prior 8 deleted/replaced; current 8 added/replaced; prior 14 deleted/replaced; current 14 added/replaced
- `tests/test_read_store_inventory.py`: prior 10 deleted/replaced; current 10 added/replaced; prior 22 deleted/replaced; current 22-34 added/replaced
- `data/catalog/fda_ndc_150.json`: new lines 1-1
- `data/synthetic/store_1618_inventory_150.json`: new lines 1-1
- `scripts/build_medication_catalog.py`: new lines 1-178
- `scripts/render_catalog_seed.py`: new lines 1-92
- `supabase/migrations/20261013230004_medication_catalog.sql`: new lines 1-62
- `tests/test_catalog_data.py`: new lines 1-63

## Secondary Checks

- Trailing whitespace: PASS (git diff --check).
- Markdown fences: PASS for changed Markdown files.

Validation: 161 passing tests; qualification 85/85, misses 0, false positives 0, containment 85. SQL execution remains untested; no hosted deployment.

## Harness integration review

The fetched harness head `2f950ac` is integrated with the retained 150-row batches and `--legacy-fixture`. Three textual conflicts in `.env.example`, README and CLI were reconciled without removing either approved configuration path. Historical tests explicitly select the original fixture. The reviewed FDA `related_info` reinsertion is corrected in a separate error-control commit with a regression test. Combined validation: 192 tests pass. Final integrated security and review remain required before push.

## Final integrated validation

The historical web preview is retained explicitly on the 20-row fixture and single-NDC schema; catalog CLI behavior remains 150 rows and ten-NDC batches. All original database and web PRD appendices survive their conflict resolution. Source reads remain guarded, arithmetic is reconstructed by the harness, external narrative stays out of outgoing JSON, and no hosted migration or web deployment occurred.

Integrated SECURITY Round 1: 100 security-facing tests pass and 85/85 qualification cases agree (55 detected, 0 misses, 0 false positives, 85 contained). Integrated SECURITY Round 2: full 233-test regression suite passes; no remediation is outstanding within tested scope. Docker/isolated SQL, hosted permission/deployment and live model calls remain untested. Browser checks cover all eight routes at 1024/640/320 widths, retained drafts, Unicode/required input, keyboard navigation, declared 20-row demo, denied writes, tampered reports and failure recovery; no browser exceptions.

UX review: the inventory reviewer has stable navigation, visible synthetic/read-only status, grouped evidence and an explicit human next step. Keyboard, responsive, loading/error/recovery checks pass; retaining the historical web fixture intentionally avoids expanding its model/output budget during catalog integration. Laws of UX grouping and continuity informed review: https://lawsofux.com/. These principles do not substitute for user research.

## Integrated Line Return Reference

- `.env.example`: prior 1 removed/replaced; current 1 added/replaced; current 21-27 added/replaced
- `.python-version`: current 1 added/replaced
- `AGENTS.md`: prior 31 removed/replaced; current 31 added/replaced
- `README.md`: prior 11 removed/replaced; current 11 added/replaced; prior 15 removed/replaced; current 15-17 added/replaced; prior 23 removed/replaced; current 25 added/replaced; prior 43 removed/replaced; current 45 added/replaced; prior 45 removed/replaced; current 47 added/replaced; prior 47 removed/replaced; current 49 added/replaced; current 57-58 added/replaced; current 63-105 added/replaced; prior 82 removed/replaced; current 129 added/replaced
- `TEAM-REFERENCE.md`: current 13-26 added/replaced; prior 67 removed/replaced; current 81 added/replaced; prior 75 removed/replaced; current 89 added/replaced
- `app.py`: current 1-4 added/replaced
- `docs/architecture/Pharmacy-Web-Agent-Architecture.md`: current 1-73 added/replaced
- `docs/planning/WEB-HOSTING.md`: current 1-45 added/replaced
- `docs/planning/WEB-INTERFACE-CONTRACT.md`: current 1-62 added/replaced
- `docs/planning/WEB-REVIEW.md`: current 1-183 added/replaced
- `docs/requirements/Pharmacy Inventory Logistics[PRD]-Mod.md`: current 322-369 added/replaced
- `requirements-web.txt`: current 1-30 added/replaced
- `requirements.txt`: current 1-2 added/replaced
- `src/pharmacy_agent/__init__.py`: current 1 added/replaced
- `src/pharmacy_agent/anthropic_client.py`: current 1-73 added/replaced
- `src/pharmacy_agent/config.py`: current 1-76 added/replaced
- `src/pharmacy_agent/review.py`: current 1-106 added/replaced
- `src/pharmacy_agent/runtime.py`: current 1-184 added/replaced
- `src/pharmacy_web/__init__.py`: current 1 added/replaced
- `src/pharmacy_web/app.py`: current 1-281 added/replaced
- `tests/browser/pharmacy_web_check.mjs`: current 1-104 added/replaced
- `tests/test_claude_runtime.py`: current 1-277 added/replaced
- `tests/test_pharmacy_web.py`: current 1-224 added/replaced
- `vercel.json`: current 1-9 added/replaced
- `web/assets/pharmacy.css`: current 1-167 added/replaced
- `web/assets/pharmacy.js`: current 1-486 added/replaced
- `web/templates/base.html`: current 1-43 added/replaced
- `web/templates/page.html`: current 1-162 added/replaced

## Secondary Checks

- Trailing whitespace: PASS.
- Markdown fences: PASS.
- Conflict markers in working content: absent.
- `docs/database/MIGRATION-REVIEW.md`: current 34; current 96-140; final self-reference line added.
