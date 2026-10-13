"""One model turn: copy report-v1 or be rejected. No training, no retry, no tool loop."""
import json
import os
import urllib.error
import urllib.request

try:
    from ..injection_prevention.output_guard import expected_report, validate_report
    from ..pharmacy_tools.instructions import SYSTEM_PROMPT
except ImportError:
    from injection_prevention.output_guard import expected_report, validate_report
    from pharmacy_tools.instructions import SYSTEM_PROMPT

MODEL_TIMEOUT_SECONDS = 30


def parse_proposal(raw):
    """Accept only one JSON object. Prose, arrays, and markdown are not reports."""
    if type(raw) is dict:
        return raw
    if type(raw) is str:
        try:
            value = json.loads(raw)
        except ValueError:
            return None
        return value if type(value) is dict else None
    return None


def copying_complete(system_prompt, context):
    """Wire check only. Returns expected_report. Not a language model."""
    del system_prompt
    return expected_report(context)


def run_model_turn(context, complete):
    """Call complete once with Brahim's prompt and the trusted context, then validate_report.

    Exceptions, unreadable output, and invented fields all become OUTPUT_EVIDENCE_MISMATCH.
    """
    try:
        raw = complete(SYSTEM_PROMPT, context)
    except Exception:
        raw = None
    proposed = parse_proposal(raw)
    if proposed is None:
        proposed = {"schema_version": "not-report-v1"}
    return validate_report(proposed, context=context)


def http_complete(system_prompt, context, *, url, key, name, timeout=MODEL_TIMEOUT_SECONDS,
                  urlopen=urllib.request.urlopen):
    """One OpenAI-compatible chat completion. Caller supplies URL and key."""
    body = json.dumps({
        "model": name,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(context, allow_nan=False)},
        ],
    }).encode()
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if key:
        request.add_header("Authorization", "Bearer " + key)
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        raise
    try:
        return payload["choices"][0]["message"]["content"]
    except (TypeError, KeyError, IndexError) as error:
        raise ValueError("MODEL_RESPONSE_SHAPE") from error


def complete_from_env(*, environ=None):
    """Build http_complete from PHARMACY_MODEL_URL, PHARMACY_MODEL_KEY, PHARMACY_MODEL_NAME."""
    env = environ if environ is not None else os.environ
    url = env.get("PHARMACY_MODEL_URL") or ""
    if not url.strip():
        return None
    key = env.get("PHARMACY_MODEL_KEY") or ""
    name = env.get("PHARMACY_MODEL_NAME") or "pharmacy-report-v1"

    def complete(system_prompt, context):
        return http_complete(system_prompt, context, url=url, key=key, name=name)

    return complete
