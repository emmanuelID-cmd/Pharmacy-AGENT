# Read-only backend login and inventory tool

Approved and verified October 13, 2026 on project xrptinavijhwvydoqdni. The full harness is not required to provision and test this tool independently.

## Login and secrets

pharmacy_agent_backend is LOGIN, non-superuser and NOBYPASSRLS. It inherits pharmacy_inventory_reader; no INSERT/UPDATE/DELETE grants were added. Its default transaction mode is read-only, with 5-second statement/idle transaction limits and a 1-second lock timeout. The database adapter also starts an explicit repeatable-read, read-only transaction.

Migration 20261013042410 contains no password. A generated password was set through authenticated management access without displaying it. It lives only in the ignored local .env.database file as PHARMACY_DATABASE_URL. Do not paste it into chats, model inputs, browser code, migrations, logs or Git. Rotation uses an authorized management action, followed by updating backend secret storage; do not reuse the management account's password.

The existing .env publishable key stays untouched. It does not authenticate this private PostgreSQL login. Verified session-pooler connection: aws-0-us-east-1.pooler.supabase.com:5432, using the project-qualified backend username and TLS. No hosting deployment or public schema exposure was introduced.

## Dependency setup and usage

The optional requirements-database.txt pins psycopg binary support and Windows timezone data. Dependencies were installed inside project .venv, not globally.

From the project root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -B scripts/check_database_reader.py
```

The check script loads the exact generated .env.database format into the backend process; the model receives no credential tool argument. A future backend host should provide PHARMACY_DATABASE_URL through its server-side environment/secret storage instead.

Python interface: src.pharmacy_tools.read_store_inventory_database(1618). The original read_store_inventory remains file-backed. The future harness chooses the trusted callback; user/model text cannot select database URLs or supply SQL.

## Reader behavior

Uses fixed parameterized SELECTs for store 1618, a consistent latest snapshot and at most 20 items. Snapshot conflicts, excessive rows/exceptions, conflicting policies or unavailable database fail closed with static safe codes. Connection timeout is 5 seconds; each SQL statement is limited to 5 seconds. Those per-operation limits do not establish a full agent-loop deadline.

Returns the existing allowlisted inventory shape. Decimal values become JSON numbers, timestamps remain original, and incomplete windows are not filled with zero. Only matching approved policies active at snapshot time are returned as data. Imported identity and reconciliation remain unverified; absence of policy returns ITEM_POLICY_MISSING. Any later operational policy/freshness verification belongs to the harness. The seeded October 7 snapshot is stale, not live inventory.

Returned labels and all other records remain untrusted. Existing context isolation/action/output guards still apply. This adapter never constructs TrustedFact, calculates supply, changes stock, orders medication or treats database access as evidence approval.

## Evidence and limits

103 behavior methods passed, including nine new reader cases. Both sequential rollback-only backend-role permission rounds passed before deployment. Actual pooler login returned 20 items and passed the prevention intake contract.

Live backend credentials could SELECT approved inventory. INSERT, UPDATE, DELETE, raw-import reads and SET ROLE postgres were denied. The test explicitly requested a read-write transaction to confirm that grants enforce denial independently of the default read-only setting. All probes rolled back; no stock changed.

Secrets and .venv are ignored by Git. Historical synthetic evidence and file-reader behavior remain intact. Full model loop, operational source freshness/identity approval, cloud hosting, connection-pool load and harness integration remain outside this work.
