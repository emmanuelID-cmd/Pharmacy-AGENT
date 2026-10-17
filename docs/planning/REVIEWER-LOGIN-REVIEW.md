# Individual reviewer login review - October 16, 2026

## Scope and recovery

Approved Supabase/integration work on feature/supabase-migration, through existing
PR #30. Baseline 998e3fe8aafdb23394cc99a9afff9c6e83251b4c is retained in Git.
The additive migration is deployed; prior migrations and teammate accounts remain
unchanged. Ignored credentials remain local. No main merge or branch deletion.
ARCHIVIST retained the source/configuration baseline and verified migration copies;
no password, token or user-data export was made. Hosted backup restoration was not tested.

## Acceptance criteria

- Approved own-account sign-in opens protected workspace: MET; Emmanuel confirmed
  local real-password success. Synthetic tests reject unconfirmed/unapproved users.
- Provider verification precedes private authorization: MET; exact token checked
  with fixed Supabase /user, then membership/session issuance; metadata is ignored.
- Opaque bounded sessions and revocation: MET within tested scope; one-hour cap,
  hash-only persistence, HttpOnly/SameSite cookie, HTTPS outside loopback, logout,
  membership disable and upstream session-deletion cascade verified.
- Paired phone identity isolation: MET in synthetic/store tests; server user UUID
  binds each role. Login/logout retires only the proven old device subscription.
- Failure recovery: MET; same-origin JSON, safe denial, bounded IO, loading,
  missing-field summaries, independently corrected fields and sign-in-again banner.
- Scope boundaries/documentation: MET; original PRD, inventory grants, Agent tools,
  passwords and managed Auth policies unchanged. Modded PRD/policy/setup updated.
- Physical deployed two-phone round trip: PENDING USER ACCEPTANCE after deployment;
  not a source-publication gate under the user's latest instruction. Never claim
  the device test passed from synthetic sender or service acceptance alone.

## Security rounds

Exactly two sequential rounds completed before this publication review. Each
passed 80 targeted methods, four Node simulations and rollback-only SQL contract.
The independent field-feedback correction between rounds was rechecked in round 2.
Initial preflight identified managed Auth RLS denial; runtime Auth table grants
were removed before the rounds. No managed Auth RLS bypass was introduced.
Restricted TLS login and deployed schema contract passed. The existing advisor
warning for disabled leaked-password protection remains acknowledged by the user;
no paid setting was changed. No external alert, email or password-reset was sent.

## Final verification

334 unittest methods passed again on the final source; four browser simulations
passed again. Qualification: 85 contained, 55 unsafe detected, 30 benign accepted,
zero misses and false positives. Python syntax, whitespace, Markdown fences and
ignored-secret exclusion passed. These checks do not certify production security.

## Findings and limits

No source blockers found. Hosted individual login requires the four documented
auth settings and a redeployment; existing demo-storage/VAPID settings are still
required. Brahim activation is deferred; Kerrian login is unobserved. Other account
changes that leave a provider session intact require private membership disable
for immediate exclusion. No automatic refresh, scheduled purge, real ordering,
SMS, inventory mutation or new harness capability is claimed.

## Commit grouping

HEAD contains the prior paired-phone feature and synchronization receipts. At
review start all current changes were unstaged; the index was empty.

1. feat(auth): add approved Supabase reviewer login - private migration/store,
   provider verification, protected routes, identity-bound pairing, page/config,
   contracts and synchronized requirements/setup. One cohesive integration task.
2. fix(auth): clear corrected sign-in field errors independently - auth.js input
   handlers and the corresponding browser assertion only; required error-control
   correction separated according to git.md. Final source includes both groups.
3. chore(review): summarize reviewer login before push - empty metadata marker.

Each ordinary commit uses What changed, Why, Collaboration, Boundaries and
Validation sections. Review marker covers the full verified remote baseline to
the final ordinary endpoint. Publication receipts follow only verified pushes.

## Line Return Reference

- `.env.example`: lines 39-47 - added/modified content; reviewed.
- `README.md`: lines 380-396 - added/modified content; reviewed.
- `TEAM-REFERENCE.md`: lines 12-30 - added/modified content; reviewed.
- `docs/architecture/Pharmacy-Web-Agent-Architecture.md`: lines 224-245 - added/modified content; reviewed.
- `docs/database/REVIEWER-LOGIN.md`: lines 1-115 - created file; all lines new; reviewed.
- `docs/requirements/POLICY.md`: lines 163-191 - added/modified content; reviewed.
- `docs/requirements/Pharmacy Inventory Logistics[PRD]-Mod.md`: lines 190-200 - added/modified content; reviewed.
- `scripts/verify_reviewer_auth_schema.py`: lines 1-37 - created file; all lines new; reviewed.
- `src/pharmacy_agent/config.py`: lines 15-16 - added/modified content; reviewed.
- `src/pharmacy_agent/config.py`: lines 27-30 - added/modified content; reviewed.
- `src/pharmacy_agent/config.py`: lines 41-42 - added/modified content; reviewed.
- `src/pharmacy_agent/config.py`: lines 64-65 - added/modified content; reviewed.
- `src/pharmacy_agent/config.py`: prior lines 62-62 - deleted/replaced content; reviewed.
- `src/pharmacy_agent/config.py`: lines 72-72 - added/modified content; reviewed.
- `src/pharmacy_agent/config.py`: lines 93-96 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: lines 9-9 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 11-11 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 12-12 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 15-15 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 16-16 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: lines 33-33 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: lines 58-63 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 160-160 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 168-168 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: lines 181-182 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: lines 184-227 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 177-187 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 231-232 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 189-195 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 234-252 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 200-200 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 257-259 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: lines 311-311 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: lines 313-375 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 267-267 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 390-390 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 328-328 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 451-451 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 337-337 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 460-460 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 347-347 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 470-470 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 355-355 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 478-478 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 363-363 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 486-486 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 374-374 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 497-497 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 387-387 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 510-510 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 396-396 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 519-519 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 410-410 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 533-533 - added/modified content; reviewed.
- `src/pharmacy_web/app.py`: prior lines 421-421 - deleted/replaced content; reviewed.
- `src/pharmacy_web/app.py`: lines 544-544 - added/modified content; reviewed.
- `src/pharmacy_web/demo_store.py`: prior lines 43-43 - deleted/replaced content; reviewed.
- `src/pharmacy_web/demo_store.py`: lines 43-43 - added/modified content; reviewed.
- `src/pharmacy_web/demo_store.py`: lines 46-51 - added/modified content; reviewed.
- `src/pharmacy_web/demo_store.py`: lines 76-89 - added/modified content; reviewed.
- `src/pharmacy_web/demo_store.py`: prior lines 75-75 - deleted/replaced content; reviewed.
- `src/pharmacy_web/demo_store.py`: lines 95-96 - added/modified content; reviewed.
- `src/pharmacy_web/demo_store.py`: prior lines 83-83 - deleted/replaced content; reviewed.
- `src/pharmacy_web/demo_store.py`: lines 104-104 - added/modified content; reviewed.
- `src/pharmacy_web/demo_store.py`: prior lines 87-87 - deleted/replaced content; reviewed.
- `src/pharmacy_web/demo_store.py`: lines 108-114 - added/modified content; reviewed.
- `src/pharmacy_web/demo_store.py`: lines 118-120 - added/modified content; reviewed.
- `src/pharmacy_web/demo_store.py`: lines 143-145 - added/modified content; reviewed.
- `src/pharmacy_web/reviewer_auth.py`: lines 1-162 - created file; all lines new; reviewed.
- `supabase/migrations/20261016221032_reviewer_auth_sessions.sql`: lines 1-46 - created file; all lines new; reviewed.
- `supabase/tests/reviewer_auth_contract.sql`: lines 1-66 - created file; all lines new; reviewed.
- `tests/browser/reviewer_auth_check.mjs`: lines 1-47 - created file; all lines new; reviewed.
- `tests/test_reviewer_auth.py`: lines 1-211 - created file; all lines new; reviewed.
- `web/assets/auth.js`: lines 1-89 - created file; all lines new; reviewed.
- `web/assets/closing.js`: lines 24-24 - added/modified content; reviewed.
- `web/assets/pairing.js`: lines 16-16 - added/modified content; reviewed.
- `web/assets/pairing.js`: lines 31-31 - added/modified content; reviewed.
- `web/assets/pharmacy.css`: lines 189-194 - added/modified content; reviewed.
- `web/assets/pharmacy.js`: lines 63-63 - added/modified content; reviewed.
- `web/assets/pharmacy.js`: prior lines 102-102 - deleted/replaced content; reviewed.
- `web/assets/pharmacy.js`: lines 103-104 - added/modified content; reviewed.
- `web/assets/pharmacy.js`: lines 468-468 - added/modified content; reviewed.
- `web/assets/push.js`: lines 35-35 - added/modified content; reviewed.
- `web/templates/base.html`: lines 10-11 - added/modified content; reviewed.
- `web/templates/base.html`: lines 16-16 - added/modified content; reviewed.
- `web/templates/base.html`: lines 32-32 - added/modified content; reviewed.
- `web/templates/base.html`: lines 41-42 - added/modified content; reviewed.
- `web/templates/login.html`: lines 1-22 - created file; all lines new; reviewed.

## Secondary Checks

- Trailing whitespace: PASS.
- Markdown fences: PASS.
- Review covers every changed source, test, migration, template and document.

## Verdict

APPROVE for authorized feature-branch publication. Keep main and PR #30 merge
untouched. Hosted configuration and physical two-phone acceptance remain pending.
- `docs/planning/REVIEWER-LOGIN-REVIEW.md`: lines 1-176 - created review record; all lines new.
