# Individual reviewer login

Approved October 16, 2026, on feature/supabase-migration. This migrates the web
entry point to existing Supabase email/password accounts. It does not change
Agent tools, inventory permissions, pairing purpose, actual orders or SMS.
Account activation was initially deferred. The user subsequently approved the
existing-account setup flow described below. No maintainer assigns or reads a
teammate password; the teammate chooses it through a private recovery link.

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

## Approved existing-account setup - October 16, 2026

The user clarified that teammate account records did not establish usable
self-chosen passwords. Email confirmation/password-present flags alone do not
prove a person completed setup or knows their password. Earlier readiness notes
are metadata observations, not live teammate sign-in acceptance.

The approved minimal demo flow uses manually delivered Supabase recovery links.
It sends no email and needs no SMTP account, email template or redirect allowlist
change. The maintainer verifies the recipient personally and shares each link
privately with that recipient only. Possession of a link is account-recovery
proof; anyone holding it could choose that account's password before it expires.
Never commit it, put it in a PR/chat/group channel, or send it to another person.

1. Deploy this change to the intended HTTPS Preview and ensure /account/setup
   opens past Vercel protection. Keep the four existing auth environment values.
2. Run scripts/create_account_setup_link.py using --account kerrian or brahim,
   --origin with that verified Preview origin, and --output with a NEW ignored
   .env.account-setup-* filename. It checks the existing account UUID/email, then
   generates recovery proof; it never calls signup or creates a replacement user.
   Management CLI credentials are used transiently; no admin key is added to
   Vercel, application Settings or generated files. Output contains only the
   recipient and their private bearer link; stdout never prints the link.
3. Open the ignored output locally and privately give the entire link to its
   named recipient. It opens /account/setup with recovery proof in the fragment,
   which is removed from browser history by the page and kept only in memory.
   Reloading loses proof; obtain a fresh link. Vercel protection is separate:
   use an accessible preview, or first grant preview access without exposing
   the account link to any unrelated viewer. Do not consume it yourself.
4. The teammate enters their own matching account email, new password of 12-1024
   characters and matching confirmation. Only explicit submit consumes proof.
   The server verifies it with Supabase /verify using type recovery, validates
   the exact access token via /user, checks existing private approval and email,
   and only then updates that same user's password. Provider access/refresh
   tokens stay on the server and are discarded, never sent to the browser.
5. Success returns to normal /login; setup does not issue an app cookie or grant
   membership. A global provider logout is attempted after password change to
   remove upstream sessions and cascade private app sessions. Cleanup uncertainty
   is reported separately from confirmed password success; a maintainer must
   disable membership for immediate exclusion if cleanup cannot be confirmed.
   Sign in with the new password, then pair the phones again.

Supabase enforces proof expiry and one-use verification. Generating a newer link
can supersede an older one. A rejected, timed-out or interrupted attempt may have
consumed proof or changed the password: never automatically replay. Ask for a
fresh link; if success was already shown, try normal sign-in. No provider text,
password, proof or token is serialized into error messages. Input checks occur
before mutation, and requests require same-origin JSON and bounded rate/IO.

The existing-account recovery verification can confirm an unconfirmed account;
this is authorized only through the privately delivered proof. Generating a link
alone is not completed activation. Real Kerrian/Brahim setup and subsequent
sign-in remain pending until they perform and confirm those steps. No real
teammate password is used in tests. No automatic external message is sent.
