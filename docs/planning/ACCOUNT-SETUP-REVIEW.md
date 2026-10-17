# Existing-account setup review - October 16, 2026

## Approved scope and recovery

Existing teammate setup approved after the user clarified that stored metadata
was not completed setup. Work stays on feature/supabase-migration and PR #30.
Baseline 8716999335b056ecdf6fd6f48da8e19be7125edb is retained in Git. No user
recreation, schema change or password assignment. Manual private recovery links
avoid SMTP/new service accounts and supersede the earlier activation deferral.
No real recovery proof or teammate password was consumed during testing.

## Acceptance criteria

- Existing accounts only: MET in source/synthetic admin tests; fixed teammate
  UUID/email pairs checked before recovery generation, no signup or duplicate.
- Own password selection: MET in UI; email, 12-character minimum and confirmation,
  independent corrected-field feedback, safe missing-link/failure instructions.
- Proof and authorization before mutation: MET; POST /verify recovery, exact
  token /user validation, email/ID match, enabled private approval, PUT same user.
  Wrong, expired, replayed, malformed and unapproved proof cannot change password.
- No permission expansion: MET; no membership grant, app cookie, database/Agent
  capability, inventory write, admin app secret or automated external message.
- Secret containment: MET in inspected scope; new ignored link files only,
  no stdout/Git links; transient fragment proof removed from current history;
  provider access/refresh tokens remain on server and are discarded.
- Safe errors and recovery: MET; same-origin JSON, bounded rate/IO, explicit
  submit, no automatic replay, password success distinct from logout result.
- Real teammate setup/sign-in and two-phone acceptance: PENDING USER ACTION;
  synthetic tests are not real recipient completion or phone-delivery evidence.

## Security rounds

Round 1: 87 targeted methods and five Node simulations passed. Inspected identity
binding, private membership, fixed provider routes, denial/error leakage, public
setup versus protected workspace, CSRF, proof storage and replay behavior.
No security findings required remediation. A synthetic Membership fixture gained
its missing resolve contract before Round 1; no production fix was necessary.
Round 2: same 87 methods and five simulations passed sequentially after Round 1.
Full regression: 341 unittest methods passed. Qualification: 85 contained,
55 unsafe detected, 30 benign accepted, zero misses and false positives.
Existing login and notification tests remained unchanged and passed.

## Findings and practical limits

No source blockers. Supabase can reject a password under its own policy; a failed
or interrupted attempt may consume proof or change the password. Ask for a fresh
link rather than replaying; if success was shown, try normal sign-in. Newer links
can supersede older links; expiry is provider-controlled. Recovery can confirm a
previously unconfirmed account. Link creation alone is not completed activation.
Manual delivery requires verifying the recipient and sharing only with that
person. A bearer link can be used by whoever holds it before expiry/consumption.

A global provider logout is attempted after password success to remove upstream
sessions and cascade opaque app sessions. Cleanup uncertainty is reported
separately; disable membership for immediate exclusion if needed. No production
security, live password-reset or universal revocation guarantee is claimed.
Vercel protection must allow both users to open the setup page. Real links are
generated only after deployment. Existing management capability was verified
without exposing/storing the admin key; no admin secret enters Settings/Vercel.
No SMTP configuration, email template or redirect allowlist is needed for this
manual fragment-link flow. Current API/source documentation was checked.

## Grouping and final review

HEAD contains the prior login; at review start current changes were unstaged and
index empty. One cohesive feat(auth) commit covers setup service/routes/form,
local admin link helper, tests and requirements/setup. Use five collaboration
body sections and final empty consolidated review marker. Record only verified
push receipts. No new branch/PR, main merge, deletion or unrelated source.
Final REVIEWER completed read-only source/line scan with no findings. This record
is the orchestrator's review documentation. APPROVE for authorized feature-branch
publication; actual teammate and physical phone completion remains pending.

## Line Return Reference

- `README.md`: prior lines 396-396 - replaced content reviewed.
- `README.md`: lines 396-400 - added/modified content reviewed.
- `TEAM-REFERENCE.md`: lines 12-24 - added/modified content reviewed.
- `docs/architecture/Pharmacy-Web-Agent-Architecture.md`: lines 246-260 - added/modified content reviewed.
- `docs/database/REVIEWER-LOGIN.md`: prior lines 6-7 - replaced content reviewed.
- `docs/database/REVIEWER-LOGIN.md`: lines 6-8 - added/modified content reviewed.
- `docs/database/REVIEWER-LOGIN.md`: lines 117-171 - added/modified content reviewed.
- `docs/requirements/POLICY.md`: lines 192-213 - added/modified content reviewed.
- `docs/requirements/Pharmacy Inventory Logistics[PRD]-Mod.md`: prior lines 200-200 - replaced content reviewed.
- `docs/requirements/Pharmacy Inventory Logistics[PRD]-Mod.md`: lines 200-203 - added/modified content reviewed.
- `scripts/create_account_setup_link.py`: lines 1-89 - created file; all lines new.
- `src/pharmacy_web/account_setup.py`: lines 1-72 - created file; all lines new.
- `src/pharmacy_web/app.py`: lines 34-34 - added/modified content reviewed.
- `src/pharmacy_web/app.py`: lines 65-70 - added/modified content reviewed.
- `src/pharmacy_web/app.py`: prior lines 214-215 - replaced content reviewed.
- `src/pharmacy_web/app.py`: lines 221-222 - added/modified content reviewed.
- `src/pharmacy_web/app.py`: prior lines 257-257 - replaced content reviewed.
- `src/pharmacy_web/app.py`: lines 264-264 - added/modified content reviewed.
- `src/pharmacy_web/app.py`: lines 366-396 - added/modified content reviewed.
- `src/pharmacy_web/app.py`: prior lines 390-390 - replaced content reviewed.
- `src/pharmacy_web/app.py`: lines 428-428 - added/modified content reviewed.
- `tests/browser/account_setup_check.mjs`: lines 1-47 - created file; all lines new.
- `tests/test_account_setup.py`: lines 1-120 - created file; all lines new.
- `web/assets/account-setup.js`: lines 1-64 - created file; all lines new.
- `web/templates/account-setup.html`: lines 1-28 - created file; all lines new.
- `web/templates/login.html`: lines 19-19 - added/modified content reviewed.

## Secondary Checks

- Trailing whitespace: PASS.
- Markdown fences: PASS.
- Python syntax and secret-file exclusion: PASS.
- `docs/planning/ACCOUNT-SETUP-REVIEW.md`: lines 1-108 - created review record; all lines new.
