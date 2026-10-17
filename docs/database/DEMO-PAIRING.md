# Private two-phone demo storage

Approved October 16, 2026 after the user required fast-forwarding the Supabase
branch first. Both feature/supabase-migration and feature/order-workflow-demo
were verified at aef261217e6a9a293cc909ab58784e9552a05980 before this work. No new
remote branch or PR is needed; application integration continues through PR #30.

## Scope

The new private pharmacy_demo.rooms table stores synthetic pairing, frozen
closing reports, human-submitted demo orders, receiving-browser subscriptions,
and reserved notification attempt results. It is not an inventory ledger,
purchase order, patient record, manufacturer integration or Agent tool.
Existing pharmacy_agent_backend grants and its read-only default stay unchanged.

The dedicated pharmacy_demo_backend login has access only to the demo schema,
with RLS, no bypass/superuser/role-creation privileges, an eight-connection cap,
five-second statement/idle limits and a one-second lock timeout. Anonymous,
authenticated and service_role Data API roles have no demo schema grants. The
schema is not added to exposed API schemas. The server supplies validated device
fingerprints through transaction-local settings and parameterized SQL; browsers
hold no database credential and cannot submit SQL or claim a stored role.

Pairing codes contain 144 bits of random entropy, expire in ten minutes, and
are stored only as SHA-256 hashes. Atomic row locking allows one manufacturer
to consume a code. Device secrets are separate random values; their hashes bind
room access. API integration must keep the actual device secret in a host-only,
HttpOnly, SameSite=Strict cookie, Secure on HTTPS, with the room's bounded life.

Rooms expire after 24 hours. API reads/updates require a live room. The private
backend can inspect expired rows for cleanup and deletes them when another room
is created; this is opportunistic cleanup, not a running deletion scheduler.
If the demo is no longer used, an authorized maintainer must purge expired demo
records. No legal/production retention policy is inferred.

## Server credential

Use a separate server-only PHARMACY_DEMO_DATABASE_URL for the restricted login,
project-qualified through aws-0-us-east-1.pooler.supabase.com:5432 with required
TLS. The store rejects another project, inventory role, host, database, port,
query options or non-PostgreSQL scheme. Never use a publishable key, inventory
reader URL, management password or service-role API key for demo writes.

Provision a strong password separately from the migration and store it only in
ignored .env.demo or the host's secret settings. Do not print it or commit it.
The existing VAPID key is retained; it is not regenerated or used as a database
password. Hosted configuration and actual two-phone delivery require later
verification after the application integration is deployed.

## Deployment and verification

Migration 20261016191734_demo_phone_pairing.sql was generated with the Supabase
CLI. It is additive and contains no password. Before deployment, both sequential
security rounds applied its DDL and role/access fixtures inside BEGIN/ROLLBACK;
both passed and retained no schema, roles or rows. Six synthetic Python store
boundary tests pass without a live connection. Deployment and the post-deployment rollback contract succeeded. The live
restricted login was verified over TLS through two independent store instances;
shared state and consumed-code rejection passed. Inventory SELECT/DELETE and
SET ROLE postgres were denied. The synthetic verification record was removed.
The actual secret is present only in ignored .env.demo; hosting remains pending
until its server environment is configured and application integration lands.

Read-only discovery found PostgreSQL 17.11 and four applied migrations through
20261013230004. This confirms that the old catalog migration is already in remote
history; no seed rerun, inventory migration or existing role change is required.
Use a neutral temporary CLI workdir with byte-verified config/migration copies
to avoid parsing the project's populated .env. Dry-run first, require that only
the new demo migration is pending, and use --skip-vault without --include-seed.

Rerun `python -B scripts/verify_demo_pairing_schema.py --before-deployment` while
the demo schema is absent, or omit the flag after deployment. All fixtures,
temporary role memberships and permission probes are rolled back. The test
runner targets only xrptinavijhwvydoqdni and never resets an existing schema.

Recovery baseline: the demo schema and login were absent. Existing inventory
schema, seed and reader login were not altered. Source baseline remains in Git;
corrections should use forward migrations. Destructive rollback requires separate
approval. No independent hosted backup/restore or production readiness is claimed.
