# Web hosting preparation

The original build prepared these files locally. A Vercel project now exists;
the verified preview-build result and remaining runtime checks are recorded below.

## Prepared files

- `app.py`: supported FastAPI entry point.
- `.python-version`: Python 3.13.
- `requirements.txt`: lists the same pinned dependencies as `requirements-web.txt`
  inline, avoiding a nested requirements-file include in the hosting parser.
- `vercel.json`: requests 60 seconds, above the application's 50-second deadline;
  excludes local environments, virtual environments, tests, presentations and
  unrelated documentation from the function bundle. Templates, assets, the
  synthetic fixture and original architecture PNG remain necessary runtime files.

## Before publishing

1. Verify the selected Vercel project/plan permits the configured function duration.
2. Configure `APP_ENV=production`, `ANTHROPIC_MODEL=claude-sonnet-5-5`, server-only
   `ANTHROPIC_API_KEY` (or the documented alias), and reviewer username/password.
   Check the hostname guidance below. Provider/database keys are never frontend variables.
3. Require Vercel project access protection (or an independently verified shared
   edge authentication-failure limiter) before wider exposure. The application's
   five-failure/60-second throttle is per requester/process and is not a distributed
   control. Verify the actual proxy supplies trustworthy requester identity.
4. Inspect dependency/bundle output for populated environment files and verify
   protected pages, APIs and assets over HTTPS. Missing reviewer settings deny access.
5. Use a preview deployment with team access restrictions. Check provider failure,
   body/origin bounds, current-clock stale data, output rejection and safe retries.
6. Verify actual duration and access behavior on the host before approving production.

The existing reviewer gate uses HTTP Basic over HTTPS. It does not create Supabase
Auth users, change roles, implement operational staff login, or expose inventory
tables. Per-process run limits do not claim to prevent all distributed abuse;
retain platform project protection and assess stronger limits before wider access.

## Requirements parsing and hosted configuration

The reported Vercel error at position 73 in the original root requirements file
points exactly to `-r requirements-web.txt`. Both original files were valid UTF-8
and pip parsed all 28 pins successfully; the supplied error does not identify the
underlying Vercel include failure. The root file now repeats those same pins
directly, with no dependency upgrades. Local pip parsing alone is not a Vercel
build result; the verified hosted result is recorded below.

In Vercel Project Settings / Environment Variables, configure the relevant
Production and Preview environments:

| Name | Value |
| --- | --- |
| APP_ENV | production |
| ANTHROPIC_MODEL | claude-sonnet-5-5 |
| ANTHROPIC_API_KEY | Complete existing provider API key, stored as a secret; no wrapping quotes |
| PHARMACY_REVIEWER_USERNAME | Reviewer login username |
| PHARMACY_REVIEWER_PASSWORD | Strong reviewer login password, stored as a secret |
| PHARMACY_ALLOWED_HOSTS | Optional override: exact hostnames, comma-separated; no scheme or path |

The reviewer credentials protect the prototype using HTTP Basic over HTTPS; they
are separate from Supabase Auth accounts. Without both reviewer settings, hosted
pages and APIs fail closed. Keep the API key and reviewer password server-only.

For an initial deployment, omit `PHARMACY_ALLOWED_HOSTS`: the application includes
Vercel's deployment hostname from `VERCEL_URL` automatically. If you set the
override for a custom domain or stable project alias, include every hostname you
will visit, including the preview deployment hostname where needed. Do not copy
the localhost-only value from `.env.example` into Vercel.

The FDA adapter pins `https://api.fda.gov/drug/shortages.json` in code and does not
read `FDA_SHORTAGES_BASE_URL`; no FDA key or URL variable is required. If kept as
an informational setting, use the complete HTTPS endpoint, not Markdown link text.

The current web Agent does not read `SUPABASE_URL` or `SUPABASE_PUBLISHABLE_KEY`.
For the separately scoped Supabase integration, `SUPABASE_URL` is the project URL
(`https://xrptinavijhwvydoqdni.supabase.co`); an `sb_publishable_...` value belongs
under `SUPABASE_PUBLISHABLE_KEY`, never under the URL name. Adding those variables
does not connect the web Agent to the database. Do not add database credentials
to this fixture-backed deployment.

Environment changes apply to new deployments; redeploy afterward. Missing model
configuration cannot cause requirements parsing errors. Supabase credentials are
not required by the current fixture-backed Agent. Local environment files are
excluded from the function bundle; never upload or commit their populated values.
See [Vercel environment variables](https://vercel.com/docs/environment-variables).

### Verified preview build - October 14, 2026

PR #19 preview commit `418aae857c9f59fd95deacf93212e5217be8fa2e` received a
successful Vercel build check. This verifies the requirements-parser workaround
for that deployment. An unauthenticated request redirects to Vercel's login page,
so application reviewer settings, provider authentication and live review behavior
remain unverified on the host. No main merge or live model call is claimed.

If the separate Supabase reader is later integrated, verify its review findings,
credentials, pooler mode and total connection/statement deadlines against the
selected host. The original web build did not merge that branch or widen database grants. Current integration preserves the separate adapter and does not connect it to the web runtime.

Sources verified October 13, 2026:
[Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi),
[Python runtime](https://vercel.com/docs/functions/runtimes/python),
[function duration](https://vercel.com/docs/functions/configuring-functions/duration),
[Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/overview).
