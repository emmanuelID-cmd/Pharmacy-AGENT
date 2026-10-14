# Web interface build and review evidence

Local feature build, October 13, 2026. Branch feature/pharmacy-agent-web-interface;
baseline d08a6b444ef1f71bca8c4e524410ccd4dce2cd3c. This is not a push/deployment record.
The user approved the PLANNER interface/Claude plan and newest Haiku recommendation.

## Builder results

- Shared eight-route pharmacy interface, canonical Home tokens/header/footer,
  logo placeholder, keyboard navigation, responsive layouts and evidence display.
- Existing read-only tool schemas adapted to Anthropic; bounded custom model loop,
  guarded inventory-first/once-per-NDC calls and exact report verification.
- Server JSON/field/origin/host limits, safe errors, hosted access gate, HTTPS for
  non-loopback credential use, loopback/proxy checks and per-process throttles.
- Existing Python synthetic tester/demo exposed through protected fixed endpoints.
  No arbitrary callback, write, patient, SQL, shell or secret API was added.
- Pinned project-local dependencies, ignored configuration, entry point and proposed
  hosting files. Vercel account/plan/access/deployment are not configured by this build.

## Verified checks

Parent ran the full unittest suite: **180 passing methods** after the final FIXER pass. New runtime and web
methods exercise tool permissions/order/binding, source validity, immutable facts,
output tampering/prose, time budgets, key absence/provider failure, Unicode,
duplicate/nonfinite/oversized JSON, origin/host/auth protection, proxies, failures,
throttle expiry and fixed synthetic endpoints. Existing teammate tests remain intact.

Existing qualification: **85/85 fixture agreement and external-text exclusions**;
55 selected unsafe detected, 30 benign accepted, zero fixture misses/false positives.
This does not establish universal detection or source authenticity.

Working browser check: all eight URLs at 1024/640/320px; no document overflow;
shared shell aligned; blank/whitespace/oversize/Unicode feedback; preserved draft,
arrow-key navigation; actual 20-row Python demo with actions/expandable evidence;
forbidden synthetic write denied; altered output rejected; explicitly simulated
offline recovery; mobile report and dark theme; zero JavaScript exceptions.
Repeatable script: tests/browser/pharmacy_web_check.mjs (requires a separate local
headless Chrome debugging profile; never point it at a remote service).

Provider verification used the existing server key without showing it. Models API
returned active claude-haiku-5-5, released October 7. Of two explicitly frozen
synthetic live-model checks with stubbed FDA, one exact report was accepted and one
was rejected into the safe deterministic fallback. Both ran three model turns and
19 guarded reads. The actual HTTP/current-clock check also completed three turns
and 19 guarded inventory/FDA reads, preserved all 20 human-report rows, flagged the
stale snapshot and rejected nonmatching model output. Orders/writes remained false.
Nondeterministic model output can require fallback even when tools work; the exact
guard was not weakened to make a live check appear successful.

Dependency consistency: pip check passed. Parent queried OSV using only the 28
public pinned PyPI package names/versions; no advisories returned on this date.
No source files, credentials or user input were sent for that dependency check.

## Security scope

New web and Claude modules, route protection, template/DOM boundaries, configuration,
dependencies and hosting preparation. Existing adjacent guard/adapter code inspected.
Tests use synthetic credentials/data; no populated secret file is in the report.

## Environment tested

Windows, Python 3.13 project .venv, Node 26, isolated headless Chrome, loopback
FastAPI on port 8770. SECURITY independently used scripted providers only; parent
ran the separately attributed live Haiku/read-only API checks.

## Tests executed

SECURITY Round 1: 30 focused web/runtime methods passed. Round 2 after remediation:
36 focused methods passed. Parent's broader 180-method/browser/dependency evidence
is separate from those independently repeated security results.

## Passed checks

Input bounds, read allowlist, omission of untrusted text, output fallback, provider
host, hosted route/asset gate, host/origin/CSP, safe DOM, synthetic-only tester/demo,
remote-development HTTPS and proxy-denial regressions, failed-login throttle/expiry.

## Failed checks

Round 1 found a MAJOR remote-development plain-HTTP Basic access path, MINOR missing
failed-login throttling, and NIT stale configuration comment. BUILDER fixed all three;
Round 2 confirmed their remediation within the tested local environment.

## Warnings

Per-worker throttles are not distributed controls. Wider hosting requires verified
project access protection or shared edge authentication limits before exposure.
Client stop cannot forcibly interrupt an already blocking read. Exact output copying
can be rejected; verified deterministic facts remain available with manual review.

## Leaks detected

No confirmed secret disclosure in tested routes/results. Source and browser tests
use synthetic marker values; this is not a claim that all leakage paths are impossible.

## Authentication and authorization findings

Non-loopback credentials require HTTPS in any mode. Local bypass requires loopback
client/listener and no forwarded headers. Missing hosted reviewer configuration fails
closed. Five failed Basic attempts trigger a 60-second per-requester/per-worker
throttle, not a global reviewer lockout. The bounded map uses ASGI requester
identity, not submitted headers.

## Network and API findings

Fixed Anthropic/FDA hosts, explicit provider timeouts and remaining-time FDA caps.
Actual cloud TLS/proxy behavior and real fault-injected socket cancellation remain
untested. HTTP live model output rejection returned a safe manual-review report.

## AI-detection findings

Fixture detection agreement is limited to the named synthetic set. Raw external
and request text is excluded independently of detection. Model output is not trusted.

## URL and connection findings

Eight GET pages; favicon; three fixed assets; GET status/test-samples; POST review,
demo/test-input/failure-preview. No broken tested local route. No operational write,
upload, public database, arbitrary redirect or vulnerability-dashboard route.

## Recommended remediation

Local findings resolved. Before deployment verify project protection, duration,
HTTPS/proxy/host settings, bundle exclusions and multi-worker limitations on the
actual selected host. Review separate Supabase and teammate PR #13 independently.

## Security verdict

Two sequential rounds: **SECURITY CLEAR WITHIN TESTED LOCAL SCOPE**. No alert action
was taken because no confirmed breach was found. This verdict does not clear a
public deployment; deployment gates remain explicitly untested.

## Recovery and scope

ARCHIVIST checked the clean tracked Git baseline before implementation. Original
tracked sources are recoverable from the recorded commit; no restore or backup
copy of populated environments was authorized or performed. New work remains local
until the separately approved Git workflow. Restore of a complete hosted system is
not verified because none was deployed. No schema/grant/data changes occurred.

Original draft/POLICY, synthetic fixture, architecture PNGs, editable presentations,
source validators/guards/adapters, deterministic CLI and local tester are unchanged.
Supabase branch/stashes are preserved. No staging, commit, push, merge or deployment
was performed. Final REVIEWER inspects the complete change set after this record.

## Initial final REVIEWER and FIXER pass

Initial verdict: REQUEST CHANGES despite all seven functional criteria being MET.
The reviewer found three in-scope defects: global auth-failure lockout (MAJOR),
OS key-alias precedence (MINOR), and active-read accounting after timeout (MINOR).
This initial report is preserved; it is not silently replaced by a later verdict.

FIXER corrected the existing boundaries without new permissions or public APIs:
resolve key spellings within each configuration layer before applying precedence;
scope auth failure queues to requester with a bounded 128-entry map; and track
shielded read-worker completion so cancelled waits cannot release the read gate early.
Regression tests use distinct synthetic requesters, file/OS alias combinations, and
a genuinely blocking synthetic reader. All 180 behavior methods passed afterward.
Affected SECURITY checks and a new read-only REVIEWER pass follow this correction.

SECURITY's targeted follow-up within Round 2 independently passed all 39 focused
methods, including the real blocked-worker cancellation regression. Its local
verdict remains CLEAR WITHIN TESTED LOCAL SCOPE; no new permissions, outbound
endpoint or model-text sink was introduced. Hosting proxy/requester identity and
shared platform controls remain untested. Final REVIEWER rechecks this corrected set.

First re-review: REQUEST CHANGES for one MINOR same-layer canonical-empty/alias-
present edge case. Second FIXER pass chooses by key presence, preserving an explicit
canonical clear even when a legacy alias is populated. Added OS and file-layer
counterexamples to the existing configuration regression. This preserves the
initial and re-review findings rather than replacing their history. No guard,
permission, API or model change is involved; affected checks are repeated before
the second final re-review.

## Final verdict

The second final read-only REVIEWER returned **APPROVE for the local, uncommitted
web build**. All seven approved criteria are MET; all 27 changed files were scanned;
the initial three findings and the same-layer empty-key edge case are resolved.
SECURITY independently passed the final credential regression and retained its
local-scope clearance. Actual hosting, proxy identity and shared platform controls
remain deployment checks. This verdict does not authorize staging, Git publication
or a main merge; the working preview is available for the user's review.

## October 13, 2026: 150-item Agent evaluation

This follow-up covers the approved Agent catalog expansion and terminal refusal/error
handling. The historical Demo remains on its original 20-row fixture. Changes are
local and unstaged; no migration, hosting deployment or Git publication occurred.

Two real Claude Haiku 5.5/openFDA evaluations completed without automatic retries.
The direct runner used the fixture evaluation clock; the web endpoint used the
current clock through the application's ASGI route. Both used the configured
provider service and actual FDA HTTP reads. Only fixed diagnostic metadata was
recorded; model text and credentials were excluded.

| Evaluation (America/New_York) | Reads completed | Verified rows | Model turns | Outcome |
| --- | --- | --- | --- | --- |
| Direct runner, 2026-10-13 23:23:10 -04:00 | 16 (inventory + 15 FDA batches) | 150 | 3 | OUTPUT_EVIDENCE_MISMATCH; Manual Review |
| Web endpoint, 2026-10-13 23:23:44 -04:00 | 16 (inventory + 15 FDA batches) | 150 | 3 | OUTPUT_EVIDENCE_MISMATCH; Manual Review |

Each evaluation returned 149 FDA NO_MATCH items and one MATCH item; HTTP results
were fourteen 404 responses and one 200 response. The current-clock evaluation
also correctly flagged STALE_SNAPSHOT. Neither evaluation accepted model output,
placed an order or changed inventory. Final model output was 611 and 686 tokens,
respectively; the expected compact report measured 20,117 tokens through the
provider token-count API, within the 24,576-token final-output ceiling. The raw
responses were not retained, so their precise mismatch content is not asserted.

The actual agent selected the tools and completed all bounded reads. End-to-end
acceptance of the exact 150-row model report remains unresolved. Successful local
scripted-provider tests do not establish successful live model acceptance; the
output guard remains strict. No third live evaluation was attempted.

SECURITY Round 1 passed 88 focused behavior methods. Review identified that the
90-second model timeout was only a default; FIXER enforced it as a hard ceiling
and added a 91-second rejection counterexample before Round 2.

SECURITY Round 2 passed all 247 unittest methods in the project virtual environment
and the qualification CLI: 85/85 contained fixtures, 55 unsafe detected, 30 benign
accepted, zero misses and zero false positives. The first full-suite command used
system Python without the project's dependencies and failed imports; the corrected
virtual-environment run passed. Whitespace validation passed. Browser checks at
1024, 640 and 320 pixels passed earlier in this follow-up. Live exact-report
acceptance remains an explicit outstanding issue despite these local passes.
