# Migration review â€” October 13, 2026

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
