"""get_fda_shortage_context: read-only adapter for the openFDA drug shortages API.

Returns a payload in the injection_prevention FDA source shape ({"results", "meta"}).
"results" holds only records whose package_ndc matches exactly, reduced to the 11
PRD fields. "meta" labels the outcome so the harness never mistakes a failure for
"no shortage":

  MATCH        exact package_ndc found
  NO_MATCH     successful search, no exact match (never guaranteed supply)
  PARTIAL      fewer records retrieved than the API reported (never complete)
  UNAVAILABLE  timeout, rate limit, server/transport error, malformed or oversized body

Everything returned stays untrusted data for inspect_payload. National context never
replaces or changes local stock facts.
"""
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

try:  # imported as src.pharmacy_tools (tests run from the repo root)
    from ..injection_prevention.boundary_contracts import ContractError, InventoryLimits, Limits, validate_tree
except ImportError:  # imported as pharmacy_tools with src on PYTHONPATH
    from injection_prevention.boundary_contracts import ContractError, InventoryLimits, Limits, validate_tree

FDA_URL = "https://api.fda.gov/drug/shortages.json"  # fixed HTTPS host, never from input
TIMEOUT_SECONDS = 10
MAX_ATTEMPTS = 2  # first request + one bounded retry for transient errors
PAGE_LIMIT = 100
MAX_RECORDS = 1000
MAX_BODY_BYTES = 1_000_000
BATCH_SIZE = 10
BATCH_TIMEOUT_SECONDS = 3

# Segmented package NDC formats only (4-4-2, 5-3-2, 5-4-1); no guessed conversion.
NDC_PATTERN = re.compile(r"\d{4}-\d{4}-\d{2}|\d{5}-\d{3}-\d{2}|\d{5}-\d{4}-\d{1}", re.ASCII)

# The 11 PRD fields accepted by the prevention FDA source contract.
PRD_FIELDS = ("package_ndc", "generic_name", "availability", "related_info", "update_date",
              "therapeutic_category", "dosage_form", "presentation", "company_name",
              "shortage_reason", "status")


class InvalidPackageNdc(ValueError):
    """Raised before any request when the NDC is not a segmented package NDC."""


def _ssl_context():
    """Default certificates; use certifi's bundle when it is installed (Homebrew Python)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _http_get(url, timeout):
    """One real GET. Returns (status_code, body_bytes); raises on transport failure."""
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=_ssl_context()) as response:
            return response.status, response.read(MAX_BODY_BYTES + 1)
    except urllib.error.HTTPError as error:
        return error.code, error.read(MAX_BODY_BYTES + 1)


def _fetch_page(ndc, skip, timeout, http_get):
    """One bounded attempt. Returns (outcome, body_or_reason)."""
    query = urllib.parse.urlencode({"search": f'package_ndc:"{ndc}"', "limit": PAGE_LIMIT, "skip": skip})
    try:
        status, raw = http_get(f"{FDA_URL}?{query}", timeout)
    except (TimeoutError, OSError):  # URLError and socket timeouts are OSError subclasses
        return "RETRY", "TRANSPORT_ERROR_OR_TIMEOUT"
    if len(raw) > MAX_BODY_BYTES:
        return "UNAVAILABLE", "RESPONSE_TOO_LARGE"
    try:
        body = json.loads(raw)
    except ValueError:
        return ("RETRY" if status >= 500 else "UNAVAILABLE"), "MALFORMED_BODY"
    if status == 200:
        return "OK", body
    if status == 404 and isinstance(body, dict) and isinstance(body.get("error"), dict) \
            and body["error"].get("code") == "NOT_FOUND":
        return "NOT_FOUND", None  # documented openFDA no-match response
    if status == 429 or status >= 500:
        return "RETRY", f"HTTP_{status}"
    return "UNAVAILABLE", f"HTTP_{status}"


def _fetch_with_retry(ndc, skip, timeout, http_get, sleep, attempts):
    reason = None
    for attempt in range(MAX_ATTEMPTS):
        attempts.append(1)
        outcome, payload = _fetch_page(ndc, skip, timeout, http_get)
        if outcome != "RETRY":
            return outcome, payload
        reason = payload
        if attempt + 1 < MAX_ATTEMPTS:
            sleep(1)
    return "UNAVAILABLE", reason


def _prd_record(record):
    """Keep only the 11 PRD fields, as strings (therapeutic_category list is joined)."""
    row = {}
    for key in PRD_FIELDS:
        value = record.get(key)
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            value = "; ".join(value) if key != "package_ndc" else value
        if isinstance(value, str) or (key == "package_ndc" and isinstance(value, list)):
            row[key] = value
    return row


def get_fda_shortage_context(package_ndc, *, timeout=TIMEOUT_SECONDS, http_get=_http_get, sleep=time.sleep):
    """Return national shortage context for one validated package NDC (read-only)."""
    if type(package_ndc) is not str or not NDC_PATTERN.fullmatch(package_ndc):
        raise InvalidPackageNdc("INVALID_PACKAGE_NDC")

    meta = {"source": "openFDA drug shortages", "package_ndc": package_ndc,
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    attempts, records, skip, total = [], [], 0, None

    def finish(state, results=(), reason=None):
        meta.update(state=state, requests=len(attempts))
        if reason:
            meta["reason"] = reason
        payload = {"results": list(results), "meta": meta}
        try:
            validate_tree(payload)  # same bounds inspect_payload will apply
        except ContractError:
            return {"results": [], "meta": {**meta, "state": "UNAVAILABLE", "reason": "RESPONSE_EXCEEDS_BOUNDS"}}
        return payload

    while True:
        outcome, body = _fetch_with_retry(package_ndc, skip, timeout, http_get, sleep, attempts)
        if outcome == "NOT_FOUND":
            return finish("NO_MATCH")
        if outcome != "OK":
            return finish("UNAVAILABLE", reason=body)
        # Validate the response shape before reading fields
        if not isinstance(body, dict) or not isinstance(body.get("results"), list) \
                or not isinstance(body.get("meta"), dict):
            return finish("UNAVAILABLE", reason="UNEXPECTED_RESPONSE_SHAPE")
        total = body["meta"].get("results", {}).get("total") if isinstance(body["meta"].get("results"), dict) else None
        if isinstance(body["meta"].get("last_updated"), str):
            meta["dataset_updated"] = body["meta"]["last_updated"]
        records.extend(r for r in body["results"] if isinstance(r, dict))
        skip += PAGE_LIMIT
        if not isinstance(total, int) or skip >= total or skip >= MAX_RECORDS:
            break

    meta["total_reported"] = total if isinstance(total, int) else None
    exact = [_prd_record(r) for r in records if r.get("package_ndc") == package_ndc]  # exact string, leading zeros kept
    if len(exact) > Limits().max_rows:
        return finish("PARTIAL", exact[:Limits().max_rows], reason="TOO_MANY_MATCHING_RECORDS")
    if not isinstance(total, int) or len(records) < total:
        return finish("PARTIAL", exact, reason="INCOMPLETE_RETRIEVAL")
    return finish("MATCH" if exact else "NO_MATCH", exact)


def get_fda_shortage_context_batch(package_ndcs, *, http_get=_http_get, sleep=time.sleep):
    """One bounded OR query for up to ten exact NDCs; incomplete results stay PARTIAL.

    A successful response with more than 100 reported records is not paged in a
    150-item run. It is explicitly PARTIAL for every NDC in the batch.
    """
    if type(package_ndcs) not in (list, tuple) or not 1 <= len(package_ndcs) <= BATCH_SIZE or len(set(package_ndcs)) != len(package_ndcs) or any(
        type(ndc) is not str or not NDC_PATTERN.fullmatch(ndc) for ndc in package_ndcs
    ):
        raise InvalidPackageNdc("INVALID_PACKAGE_NDC_BATCH")
    ndcs = tuple(package_ndcs)
    meta = {"source": "openFDA drug shortages", "package_ndcs": list(ndcs),
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    query = urllib.parse.urlencode({
        "search": "package_ndc:(" + " OR ".join(f'"{ndc}"' for ndc in ndcs) + ")",
        "limit": PAGE_LIMIT,
    })
    url = f"{FDA_URL}?{query}"
    outcome, body = None, None
    for attempt in range(MAX_ATTEMPTS):
        try:
            status, raw = http_get(url, BATCH_TIMEOUT_SECONDS)
            if len(raw) > MAX_BODY_BYTES:
                outcome, body = "UNAVAILABLE", "RESPONSE_TOO_LARGE"
                break
            data = json.loads(raw)
        except (TimeoutError, OSError):
            outcome, body = "RETRY", "TRANSPORT_ERROR_OR_TIMEOUT"
        except ValueError:
            outcome, body = "UNAVAILABLE", "MALFORMED_BODY"
        else:
            if status == 200:
                outcome, body = "OK", data
                break
            if status == 404 and type(data) is dict and type(data.get("error")) is dict and data["error"].get("code") == "NOT_FOUND":
                outcome, body = "NOT_FOUND", None
                break
            outcome, body = ("RETRY", f"HTTP_{status}") if status == 429 or status >= 500 else ("UNAVAILABLE", f"HTTP_{status}")
        if outcome != "RETRY" or attempt + 1 == MAX_ATTEMPTS:
            break
        sleep(1)
    meta["requests"] = attempt + 1
    if outcome == "NOT_FOUND":
        meta["state"] = "NO_MATCH"
        return {"results": [], "meta": meta}
    if outcome != "OK" or type(body) is not dict or type(body.get("results")) is not list or type(body.get("meta")) is not dict:
        meta.update(state="UNAVAILABLE", reason=body if type(body) is str else "UNEXPECTED_RESPONSE_SHAPE")
        return {"results": [], "meta": meta}
    total = body["meta"].get("results", {}).get("total") if type(body["meta"].get("results")) is dict else None
    if type(body["meta"].get("last_updated")) is str:
        meta["dataset_updated"] = body["meta"]["last_updated"]
    meta["total_reported"] = total if type(total) is int else None
    exact = [_prd_record(row) for row in body["results"] if type(row) is dict and row.get("package_ndc") in ndcs]
    meta["state"] = "PARTIAL" if type(total) is not int or total > len(body["results"]) else "MATCH" if exact else "NO_MATCH"
    if meta["state"] == "PARTIAL":
        meta["reason"] = "INCOMPLETE_BATCH_RETRIEVAL"
    payload = {"results": exact, "meta": meta}
    try:
        validate_tree(payload, InventoryLimits())
    except ContractError:
        return {"results": [], "meta": {**meta, "state": "UNAVAILABLE", "reason": "RESPONSE_EXCEEDS_BOUNDS"}}
    return payload
