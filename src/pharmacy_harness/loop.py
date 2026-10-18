"""One model turn: copy report-v1 or be rejected. No training, no retry, no tool loop."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

try:
    from ..injection_prevention.output_guard import expected_report, validate_report
    from ..pharmacy_tools.instructions import SYSTEM_PROMPT
except ImportError:
    from injection_prevention.output_guard import expected_report, validate_report
    from pharmacy_tools.instructions import SYSTEM_PROMPT

MODEL_TIMEOUT_SECONDS = 30
ANTHROPIC_TIMEOUT_SECONDS = 60
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
# Keep the CLI default aligned with the shared Sonnet runtime configuration.
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5-5"


@dataclass(frozen=True)
class ModelTurnResult:
    """Outcome of one guarded model turn.

    ACCEPTED: live answer matched expected_report.
    REJECTED: the model returned something that failed validate_report, or the
    provider stopped with refusal/truncation (distinct reason_code).
    MODEL_UNAVAILABLE: transport/auth/timeout/shape/empty failure; no answer
    to judge. Same idea as FDA UNAVAILABLE vs NO_MATCH.
    """
    state: str
    reason_code: str
    report: dict
    provider_model: str | None = None


@dataclass(frozen=True)
class ModelCompletion:
    """Text returned by a provider, plus the model id the API reported when present.

    Stub completers may still return a bare string. Live adapters should return
    this so batch records can cite the response model, not only the config value.
    """
    text: object
    provider_model: str | None = None


class ModelAnswerRejected(Exception):
    """Provider finished with a terminal stop that is not a usable report body."""

    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def _unwrap_completion(raw):
    if isinstance(raw, ModelCompletion):
        return raw.text, raw.provider_model
    return raw, None


MODEL_ENV_KEYS = (
    "PHARMACY_MODEL_URL", "PHARMACY_MODEL_KEY", "PHARMACY_MODEL_NAME",
    "ANTHROPIC_API_KEY", "ANTHOPIC_API_KEY", "ANTHROPIC_MODEL",
)
# Harness-owned. Brahim's prompt still lists tools; those reads already ran.
TURN_WRAPPER = (
    "Tools already ran. Do not call tools. Reply with only the report-v1 JSON object.\n\n"
)


def _dotenv_values(root):
    values = {}
    for name in (".env", ".env.local", ".env.web"):
        path = Path(root) / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, raw = stripped.split("=", 1)
            key = key.strip()
            if key not in MODEL_ENV_KEYS:
                continue
            values[key] = raw.strip().strip('"').strip("'")
    return values


def model_env(*, environ=None, root=None):
    """Return model settings. File values first; explicit environ wins. Never logs values."""
    values = {}
    if environ is None:
        values.update(_dotenv_values(root or Path(__file__).resolve().parents[2]))
        environ = os.environ
    for key in MODEL_ENV_KEYS:
        if key in environ:
            values[key] = environ[key]
    return values


def wrapped_system_prompt():
    return TURN_WRAPPER + SYSTEM_PROMPT


def parse_proposal(raw):
    """Accept only one JSON object. Optional ``` fences are stripped. Prose is not a report."""
    if type(raw) is dict:
        return raw
    if type(raw) is not str:
        return None
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return value if type(value) is dict else None


def copying_complete(system_prompt, context):
    """Wire check only. Returns expected_report. Not a language model."""
    del system_prompt
    return expected_report(context)


def _transport_reason(error):
    """Map provider/transport failures to static reason codes. Never include secrets."""
    if isinstance(error, TimeoutError):
        return "MODEL_TIMEOUT"
    if isinstance(error, urllib.error.HTTPError):
        if error.code in {401, 403}:
            return "MODEL_AUTH_FAILED"
        if error.code == 404:
            return "MODEL_NOT_FOUND"
        return "MODEL_TRANSPORT_FAILED"
    if isinstance(error, urllib.error.URLError):
        return "MODEL_TRANSPORT_FAILED"
    if isinstance(error, ValueError) and str(error) == "MODEL_RESPONSE_SHAPE":
        return "MODEL_RESPONSE_SHAPE"
    return "MODEL_TRANSPORT_FAILED"


def _manual_review_safety(context):
    safety = expected_report(context)
    if safety["run_state"] != "MANUAL_REVIEW":
        safety = dict(safety)
        safety["run_state"] = "MANUAL_REVIEW"
    if "MANUAL_REVIEW_REQUIRED" not in safety["warning_codes"]:
        safety = dict(safety)
        safety["warning_codes"] = list(safety["warning_codes"]) + ["MANUAL_REVIEW_REQUIRED"]
    return safety


def _is_empty_reply(raw):
    """True when a working call produced no answer text to validate."""
    if raw is None:
        return True
    if type(raw) is str and not raw.strip():
        return True
    return False


def run_model_turn(context, complete):
    """Call complete once, then validate_report when a response body exists.

    Transport/shape/empty failures stay MODEL_UNAVAILABLE. A returned answer that
    fails validation is REJECTED (usually OUTPUT_EVIDENCE_MISMATCH). Provider
    refusal or max_tokens stop become REJECTED with MODEL_REFUSAL / MODEL_TRUNCATED.
    """
    provider_model = None
    try:
        raw, provider_model = _unwrap_completion(complete(wrapped_system_prompt(), context))
    except ModelAnswerRejected as error:
        return ModelTurnResult("REJECTED", error.reason_code, _manual_review_safety(context),
                               provider_model=provider_model)
    except Exception as error:
        return ModelTurnResult("MODEL_UNAVAILABLE", _transport_reason(error),
                               _manual_review_safety(context), provider_model=provider_model)
    if _is_empty_reply(raw):
        # Same reason code name as the web Agent; harness packages it as
        # MODEL_UNAVAILABLE (no answer to judge), not a validated REJECTED body.
        return ModelTurnResult("MODEL_UNAVAILABLE", "MODEL_NO_RESPONSE",
                               _manual_review_safety(context), provider_model=provider_model)
    proposed = parse_proposal(raw)
    if proposed is None:
        proposed = {"schema_version": "not-report-v1"}
    outcome = validate_report(proposed, context=context)
    if outcome.accepted:
        return ModelTurnResult("ACCEPTED", outcome.reason_code, outcome.report,
                               provider_model=provider_model)
    return ModelTurnResult("REJECTED", outcome.reason_code, outcome.report,
                           provider_model=provider_model)


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
        choice = payload["choices"][0]
        content = choice["message"]["content"]
        finish = choice.get("finish_reason")
    except (TypeError, KeyError, IndexError) as error:
        raise ValueError("MODEL_RESPONSE_SHAPE") from error
    if finish == "content_filter":
        raise ModelAnswerRejected("MODEL_REFUSAL")
    if finish == "length":
        raise ModelAnswerRejected("MODEL_TRUNCATED")
    reported = payload.get("model") if type(payload) is dict else None
    if type(reported) is not str or not reported.strip():
        reported = None
    return ModelCompletion(content, provider_model=reported)


def anthropic_text(payload):
    """Return the first text block from an Anthropic Messages response."""
    if type(payload) is not dict or type(payload.get("content")) is not list:
        raise ValueError("MODEL_RESPONSE_SHAPE")
    texts = [
        block.get("text") for block in payload["content"]
        if type(block) is dict and block.get("type") == "text"
    ]
    if not texts or type(texts[0]) is not str:
        raise ValueError("MODEL_RESPONSE_SHAPE")
    return texts[0]


def anthropic_complete(system_prompt, context, *, key, name, timeout=ANTHROPIC_TIMEOUT_SECONDS,
                       urlopen=urllib.request.urlopen):
    """One Anthropic Messages call. No tools. Caller supplies the key."""
    # Avoid model-specific temperature validation errors; output checks enforce the report contract.
    body = json.dumps({
        "model": name,
        "max_tokens": 8192,
        "system": system_prompt,
        "messages": [{"role": "user", "content": json.dumps(context, allow_nan=False)}],
    }).encode()
    request = urllib.request.Request(ANTHROPIC_MESSAGES_URL, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("x-api-key", key)
    request.add_header("anthropic-version", ANTHROPIC_VERSION)
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        raise
    stop = payload.get("stop_reason") if type(payload) is dict else None
    if stop == "refusal":
        raise ModelAnswerRejected("MODEL_REFUSAL")
    if stop == "max_tokens":
        raise ModelAnswerRejected("MODEL_TRUNCATED")
    reported = payload.get("model") if type(payload) is dict else None
    if type(reported) is not str or not reported.strip():
        reported = None
    return ModelCompletion(anthropic_text(payload), provider_model=reported)


def complete_from_env(*, environ=None, root=None):
    """Build one complete() from OpenAI-compatible URL or Anthropic key."""
    env = model_env(environ=environ, root=root)
    url = (env.get("PHARMACY_MODEL_URL") or "").strip()
    if url:
        key = env.get("PHARMACY_MODEL_KEY") or ""
        name = env.get("PHARMACY_MODEL_NAME") or "pharmacy-report-v1"

        def complete(system_prompt, context):
            return http_complete(system_prompt, context, url=url, key=key, name=name)

        return complete
    key = (env.get("ANTHROPIC_API_KEY") or env.get("ANTHOPIC_API_KEY") or "").strip()
    if not key:
        return None
    name = env.get("ANTHROPIC_MODEL") or env.get("PHARMACY_MODEL_NAME") or DEFAULT_ANTHROPIC_MODEL

    def complete(system_prompt, context):
        return anthropic_complete(system_prompt, context, key=key, name=name)

    return complete
