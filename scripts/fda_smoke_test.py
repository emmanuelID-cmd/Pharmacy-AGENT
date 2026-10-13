"""FDA Drug Shortages API smoke test (Agent Instructions and Tooling).

Proves a real, read-only request to the openFDA drug shortages endpoint and checks
that every outcome is labeled the way the PRD requires:

  MATCH        exact package_ndc found (all matching records shown)
  NO_MATCH     successful search with no exact match (never "guaranteed supply")
  PARTIAL      more results than were retrieved (never a complete answer)
  UNAVAILABLE  timeout, rate limit, server/transport error or malformed body

A control query with a package NDC known to be listed runs first: if it returns
NO_MATCH, the integration is reported BROKEN instead of trusting any NO_MATCH.

Standard library only. No API key, no patient data, no stock values are sent.
Usage:
  python scripts/fda_smoke_test.py                  # control + default NDC
  python scripts/fda_smoke_test.py 0009-0280-02     # control + your NDCs
  python scripts/fda_smoke_test.py --simulate-timeout
"""

import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

FDA_URL = "https://api.fda.gov/drug/shortages.json"  # fixed HTTPS host, never from input
TIMEOUT_SECONDS = 10
MAX_ATTEMPTS = 2  # first request + one bounded retry for transient errors
PAGE_LIMIT = 100

# Known-listed NDC, verified against a dated FDA response on 2026-10-12
# (Methylprednisolone Acetate Injection, Current / Unavailable). Re-verify if it stops matching.
CONTROL_NDC = "42023-240-01"

# Segmented package NDC formats only (4-4-2, 5-3-2, 5-4-1); no guessed conversion.
NDC_PATTERN = re.compile(r"^(\d{4}-\d{4}-\d{2}|\d{5}-\d{3}-\d{2}|\d{5}-\d{4}-\d{1})$")

# Fields shown to the reviewer. Free-text/URL fields (related_info, contact_info) are not displayed.
SHOWN_FIELDS = [
    "package_ndc", "generic_name", "status", "availability", "update_date",
    "initial_posting_date", "dosage_form", "presentation", "company_name",
    "therapeutic_category", "shortage_reason",
]


def ssl_context():
    """Default certificates; use certifi's bundle when it is installed (Homebrew Python)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch_page(ndc, skip, timeout):
    """One bounded attempt. Returns (state, body_or_reason)."""
    query = urllib.parse.urlencode(
        {"search": f'package_ndc:"{ndc}"', "limit": PAGE_LIMIT, "skip": skip}
    )
    try:
        with urllib.request.urlopen(f"{FDA_URL}?{query}", timeout=timeout,
                                    context=ssl_context()) as response:
            return "OK", json.loads(response.read(1_000_000))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            try:
                error = json.loads(e.read(10_000)).get("error", {})
            except (ValueError, AttributeError):
                error = {}
            if error.get("code") == "NOT_FOUND":
                return "NOT_FOUND", None  # documented openFDA no-match response
            return "UNAVAILABLE", "HTTP 404 without documented NOT_FOUND body"
        transient = e.code == 429 or e.code >= 500
        return ("RETRY" if transient else "UNAVAILABLE"), f"HTTP {e.code}"
    except (TimeoutError, urllib.error.URLError) as e:
        return "RETRY", f"transport error or timeout ({type(e).__name__})"
    except ValueError:
        return "UNAVAILABLE", "malformed JSON body"


def fetch_with_retry(ndc, skip, timeout, log):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        log.append(attempt)
        state, payload = fetch_page(ndc, skip, timeout)
        if state != "RETRY":
            return state, payload
        if attempt < MAX_ATTEMPTS:
            time.sleep(1)
    return "UNAVAILABLE", payload


def check_ndc(ndc, timeout=TIMEOUT_SECONDS):
    """Return a labeled result dict for one package NDC."""
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = {"ndc": ndc, "retrieved_at": retrieved_at, "requests": 0}
    if not NDC_PATTERN.match(ndc):
        return {**result, "state": "INVALID_NDC",
                "reason": "not a segmented 4-4-2, 5-3-2 or 5-4-1 package NDC"}

    records, skip, total, dataset_updated, log = [], 0, None, None, []
    while True:
        state, body = fetch_with_retry(ndc, skip, timeout, log)
        result["requests"] = len(log)
        if state == "NOT_FOUND":
            return {**result, "state": "NO_MATCH", "dataset_updated": dataset_updated}
        if state != "OK":
            return {**result, "state": "UNAVAILABLE", "reason": body}
        # Validate the response shape before reading fields
        if not isinstance(body, dict) or not isinstance(body.get("results"), list):
            return {**result, "state": "UNAVAILABLE", "reason": "unexpected response shape"}
        meta = body.get("meta", {})
        total = meta.get("results", {}).get("total")
        dataset_updated = meta.get("last_updated")
        records.extend(body["results"])
        skip += PAGE_LIMIT
        if not isinstance(total, int) or skip >= total or skip >= 1000:
            break

    exact = [r for r in records if r.get("package_ndc") == ndc]  # exact string, leading zeros kept
    if isinstance(total, int) and len(records) < total:
        state = "PARTIAL"
    else:
        state = "MATCH" if exact else "NO_MATCH"
    return {**result, "state": state, "dataset_updated": dataset_updated,
            "total_reported": total, "records": [{k: r.get(k) for k in SHOWN_FIELDS} for r in exact]}


def print_result(label, r):
    print(f"\n== {label}: {r['ndc']}")
    print(f"   state: {r['state']}   requests: {r['requests']}   retrieved_at (fetch time): {r['retrieved_at']}")
    if r.get("dataset_updated"):
        print(f"   FDA dataset last_updated: {r['dataset_updated']}")
    if r.get("reason"):
        print(f"   reason: {r['reason']}")
    for rec in r.get("records", []):
        print(f"   - {rec['generic_name']} | status={rec['status']} | availability={rec['availability']}"
              f" | record update_date={rec['update_date']} | {rec['company_name']}")
    if r["state"] == "NO_MATCH":
        print("   meaning: no matching shortage record found. This does NOT guarantee supply.")
    if r["state"] in ("UNAVAILABLE", "PARTIAL"):
        print("   meaning: national shortage status could not be checked. Do not infer normal supply.")


def main(argv):
    if "--simulate-timeout" in argv:
        # Force a timeout on the control NDC to prove UNAVAILABLE after exactly 2 requests
        r = check_ndc(CONTROL_NDC, timeout=0.001)
        print_result("SIMULATED TIMEOUT", r)
        ok = r["state"] == "UNAVAILABLE" and r["requests"] == MAX_ATTEMPTS
        print(f"\nRESULT: {'PASS' if ok else 'FAIL'} (expected UNAVAILABLE after exactly {MAX_ATTEMPTS} requests)")
        return 0 if ok else 1

    control = check_ndc(CONTROL_NDC)
    print_result("CONTROL (known-listed NDC)", control)
    if control["state"] != "MATCH":
        print("\nRESULT: INTEGRATION BROKEN or FDA unavailable. The control NDC was not matched,"
              "\nso no NO_MATCH result below can be trusted. Re-verify the control NDC and query.")
        return 1

    for ndc in [a for a in argv if not a.startswith("--")]:
        print_result("CHECK", check_ndc(ndc))

    print("\nRESULT: integration OK (control NDC matched exactly).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
