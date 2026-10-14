# Web hosting preparation

The working application is local. No Vercel project, domain or deployment was
created by this build. Review the actual application before deployment approval.

## Prepared files

- `app.py`: supported FastAPI entry point.
- `.python-version`: Python 3.13.
- `requirements.txt`: includes the pinned `requirements-web.txt` dependency set.
- `vercel.json`: requests 60 seconds, above the application's 50-second deadline;
  excludes local environments, virtual environments, tests, presentations and
  unrelated documentation from the function bundle. Templates, assets, the
  synthetic fixture and original architecture PNG remain necessary runtime files.

## Before publishing

1. Verify the selected Vercel project/plan permits the configured function duration.
2. Configure `APP_ENV=production`, `ANTHROPIC_MODEL=claude-haiku-5-5`, server-only
   `ANTHROPIC_API_KEY` (or the documented alias), reviewer username/password and
   an exact allowed hostname. Provider/database keys are never frontend variables.
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

If the separate Supabase reader is later integrated, verify its review findings,
credentials, pooler mode and total connection/statement deadlines against the
selected host. The original web build did not merge that branch or widen database grants. Current integration preserves the separate adapter and does not connect it to the web runtime.

Sources verified October 13, 2026:
[Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi),
[Python runtime](https://vercel.com/docs/functions/runtimes/python),
[function duration](https://vercel.com/docs/functions/configuring-functions/duration),
[Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/overview).
