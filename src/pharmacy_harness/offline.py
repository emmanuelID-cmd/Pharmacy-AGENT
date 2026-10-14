"""Recorded openFDA HTTP for reviewer runs. Not a live API call and not CVS data."""
import json
from urllib.parse import unquote

EVAL_RUN_AT = "2026-10-07T10:00:00-04:00"
OFFLINE_CASE1_NDC = "42023-240-01"

# Eval Card Case 1 recorded facts. related_info stays empty so it cannot look like instructions.
OFFLINE_CASE1_RECORD = {
    "package_ndc": OFFLINE_CASE1_NDC,
    "generic_name": "Methylprednisolone Acetate Injection",
    "availability": "Unavailable",
    "related_info": "",
    "update_date": "10/06/2026",
    "therapeutic_category": "Rheumatology",
    "dosage_form": "Injection",
    "presentation": "Methylprednisolone Acetate, Injection, 80 mg/1 mL (NDC 42023-240-01)",
    "company_name": "Par Health, USA LLC",
    "shortage_reason": "Other",
    "status": "Current",
}

_NOT_FOUND = (404, json.dumps({"error": {"code": "NOT_FOUND", "message": "No matches found!"}}).encode())


def offline_fda_http_get(url, timeout):
    """Same (status, body) contract as the live adapter's http_get. No network."""
    del timeout
    decoded = unquote(url) if type(url) is str else ""
    if OFFLINE_CASE1_NDC not in decoded:
        return _NOT_FOUND
    body = {
        "meta": {"last_updated": "2026-10-06", "results": {"total": 1}},
        "results": [dict(OFFLINE_CASE1_RECORD)],
    }
    return 200, json.dumps(body).encode()
