# Individual reviewer login

Approved October 16, 2026, on feature/supabase-migration. This migrates the web
entry point to existing Supabase email/password accounts. It does not change
Agent tools, inventory permissions, pairing purpose, actual orders or SMS.
Account activation/invitation/password-reset UI was explicitly deferred by the
user. No teammate password is assigned, changed, read or stored by this work.

## Configuration and use

Server settings for the intended local or Vercel Preview/Production environment:

- PHARMACY_AUTH_MODE=supabase
- SUPABASE_URL=https://xrptinavijhwvydoqdni.supabase.co
- SUPABASE_PUBLISHABLE_KEY: the existing project publishable key.
- PHARMACY_AUTH_DATABASE_URL: the new restricted auth-backend pooler URL.

Ignored .env.auth holds the local server configuration. Keep the existing
PHARMACY_DEMO_DATABASE_URL for paired state and the existing VAPID settings for
push. The auth database URL and demo database URL use different restricted
identities and cannot substitute for one another. Never commit/paste values.
The legacy SUPABASE_PUBLISABLE_KEY spelling is accepted per environment-layer
precedence; use the canonical spelling for new configuration.

In supabase mode visit /login and use your own existing account email/password.
No repeated reviewer username/password environment variables are needed.
Protected pages redirect to sign-in; APIs return a safe authentication state.
Both phones still pair explicitly and enable their own browser notifications.
Login starts a new device pairing. Logout retires this device's subscription,
revokes its application session and clears both host cookies. Already accepted
pushes can still arrive. Sign-in failure preserves the email and clears password;
required-field errors clear independently as the user corrects each field.

PHARMACY_AUTH_MODE=basic explicitly retains the original shared/local prototype
for transition/testing. Supabase mode never falls back to Basic or unauthenticated
loopback access on configuration, provider or database failures.

## Private authorization and session model

Migration 20261016221032_reviewer_auth_sessions.sql creates private pharmacy_web
reviewers/sessions tables with RLS and no public Data API grants. Initial approved
IDs are the three existing teammates only. The new pharmacy_web_auth_backend
login can read reviewer UUID/enabled flags and issue/read/revoke scoped application
sessions. It cannot grant membership, read/write inventory or paired data, read
password hashes/provider secrets, or modify managed Auth tables/policies.

Credential verification uses fixed project HTTPS Auth token and user endpoints,
no redirects, bounded IO and minimized response contracts. The exact access token
is validated with Supabase /user before its subject/session claims are used.
User-editable metadata, submitted roles/IDs and the model never authorize access.
Supabase access/refresh tokens and passwords are discarded; they are not persisted
in application storage, placed in cookies or returned to the browser.

The browser holds a random 256-bit opaque HttpOnly, SameSite=Strict cookie,
Secure on HTTPS. The database stores only its SHA-256 hash, verified user/session
UUIDs and timestamps. The fixed maximum lifetime is one hour, capped to the
verified credential token's expiry; no automatic refresh is claimed. Server-side
session resolution checks private reviewer membership on every request. Disabling
that membership immediately denies further app requests. Foreign keys remove app
sessions when the upstream user/provider-session row is deleted. Provider account
changes that do not delete that session are not claimed instant app revocation;
a maintainer must disable reviewer membership for immediate application exclusion.
Expired app rows are cleaned on later successful sign-in, not by a scheduler.

Paired JSON state binds each device role to the server-verified user UUID. A new
login cannot inherit an earlier account's paired order access or subscription.
Login/logout retires only the proven old device, not the opposite phone's role.
Unpaired historical demo state remains shared synthetic worker-local state; this
change does not turn it into a private per-user purchasing system.

## Existing account readiness

Read-only checks found Emmanuel and Kerrian confirmed with passwords already set.
Brahim's existing account is unconfirmed with no password. His approval entry is
present, but Supabase credential/confirmation checks still deny login until he
finishes separate account activation. No account readiness is silently changed.

## Verification and recovery

Run python -B scripts/verify_reviewer_auth_schema.py --before-deployment only
while pharmacy_web is absent; omit the flag after deployment. The script uses
synthetic fixtures in BEGIN/ROLLBACK, never real passwords or saved user changes.
Test denial of cross-cookie access, unverified user context, overlong lifetime,
password/provider-secret reads, membership writes, inventory and public access.
Test app logout and upstream provider-session deletion revocation separately.

The migration is additive. Preserve the existing five applied migrations and
accounts; dry-run must identify only this new migration. Provision the restricted
login password separately, keep it only in ignored server configuration, and
verify TLS/least-privilege access after deployment. Do not reset the project,
rerun inventory seeds or add public grants. Recovery uses forward corrections;
destructive schema/account rollback requires separate approval. No independent
hosted backup/restore or production-auth certification is claimed.

Live real-password acceptance requires the user to sign in through the completed
page. Synthetic provider tests and a deployment build do not prove their password
or email/account readiness. No real password should be pasted into chat.

## Verified deployment and acceptance - October 16, 2026

The CLI dry-run identified only this migration; deployment and the deployed
rollback contract passed. The restricted TLS login was provisioned with a
separate strong password held only in ignored .env.auth. Live checks confirmed
three approved IDs, denied managed Auth secrets/inventory/demo access and a
200 response from the provider health endpoint. Emmanuel subsequently confirmed
that his own password login opened the local workspace. Kerrian's own login
has not been observed; Brahim activation remains separately deferred.

Both security rounds passed 80 targeted methods, four browser simulations and
the rollback database contract. Full unittest discovery passed 334 methods;
qualification contained all 85 fixtures with 55 unsafe detected, 30 benign
accepted, zero misses/false positives. Local browser verified required-field
feedback and independent correction. The database advisor reported existing
leaked-password protection disabled; the user acknowledged its paid-subscription
requirement and this setting remains unchanged. No production-auth guarantee.
