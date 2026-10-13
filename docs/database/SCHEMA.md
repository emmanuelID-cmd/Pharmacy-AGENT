# Pharmacy inventory schema

Deployed October 13, 2026 to Supabase project xrptinavijhwvydoqdni, PostgreSQL 17.11. The private pharmacy schema is not exposed through the Data API. A publishable key alone cannot read these tables or perform migrations.

## Tables

- stores: configured store 1618 and America/New_York.
- synthetic_imports: raw JSON, source SHA-256, synthetic marker and import time. No reader grant.
- medication_items: exact segmented NDC and source label/unit. Missing strength/package fields stay null; identity_verified is false.
- item_policies: validated thresholds, approval and validity intervals. No seed policies; approved intervals cannot overlap per item.
- inventory_events: source identity/version uniqueness. Empty until authorized accounting evidence exists.
- inventory_snapshots: original snapshot time and stock; negative/missing values become null with review status. Source values remain in raw imports.
- daily_usage: exact 14-day windows mapped to documented dates. 13-day window is not dated by guessing. SOURCE_REPORTED is not VERIFIED.
- inventory_exceptions: safe reason codes for absent policy/identity and invalid stock/incomplete usage.
- audit_events: future authorized actor/action history; no fabricated audit rows.

## Access

RLS on all nine tables. public, anon and authenticated have no pharmacy schema/table grants. pharmacy_inventory_reader is NOLOGIN, NOBYPASSRLS and has SELECT only on stores/items/policies/snapshots/usage/exceptions, scoped to 1618. The approved pharmacy_agent_backend login now inherits this reader role. Its password is provisioned outside migrations and stored only in ignored local backend configuration. Raw imports, audit records and movements are not accessible to that reader. No write tool or staff write service is implemented.

## Seed integrity

The original JSON is unchanged. Its SHA-256 is a1c24a4125fced0fb88229492cf3fb9bd629d5db846be528efe35a4302b683d6. The seed is repeatable and refuses an existing import ID with a different source hash. Counts: 20 items/snapshots, 266 dated usage rows, 20 exceptions, two null stock values. Dates remain October 7/September 23–October 6; the seed is deliberately stale, not a current operational snapshot.

All 20 items lack per-item policy and complete package evidence. Do not treat importing them as approving classifications. The original file reader remains available; the separate database adapter now reads normalized source evidence. Full harness integration remains pending.

## Migration workflow

CLI generated the two files under supabase/migrations. Use supabase migration new for later changes. Inspect existing migration history and run a dry run before deploying; coordinate one deployer at a time. Do not reset the remote database or edit deployed migrations.

Target arguments: --linked --project-ref xrptinavijhwvydoqdni. Deployment used supabase db push --include-seed --skip-vault. No vault secrets were changed.

The repository .env is currently rejected by the CLI parser. Do not print its values. Use a fresh temporary directory containing byte-verified copies of supabase/config.toml, migrations and seed, and supply --workdir to that directory. Never copy .env or credentials there. The account's existing CLI management session performs deployment.

## Verification and recovery

With Docker unavailable, schema/access migrations and seed were exercised in a BEGIN/ROLLBACK transaction on the empty target. Seed ran twice and supabase/tests/inventory_contract.sql asserted constraints, preserved evidence, date mapping, counts and read/write denial. A reader role membership was granted to postgres only inside those rolled-back tests so role impersonation could be verified. Rollback left no pharmacy schema or role.

Two sequential security rounds passed. After deployment, both migration versions and seeded counts were queried successfully; RLS was confirmed on every table. All 94 application tests and 85 selected fixture outcomes passed. These checks do not prove live pharmacy readiness, full harness integration or concurrent policy-update behavior under every transaction isolation mode.

Recovery baseline had no application tables or migration history. Original files remain recoverable from Git and retained local work; no independent cloud restore was tested. Future corrections use forward migrations. Destructive rollback requires separate approval. No backup of patient data exists or is needed for this synthetic seed.

Rerun checks with `python -B scripts/verify_schema_migration.py`. This runs seed/constraint/permission tests inside a transaction and rolls it back, including the test-only role membership. Use `--empty-baseline` only on an empty target to test DDL; it will fail rather than replace an existing schema. The script targets only the approved project.

Backend login/adapter implementation and live permission tests are documented in [BACKEND-READER.md](BACKEND-READER.md). Migration 20261013042410 creates the login without a password in source; provisioning occurs separately.
