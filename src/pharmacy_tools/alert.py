"""Critical-stock Slack alert with a human-in-the-loop checkpoint.

New capability: after a review, tell the pharmacy supervisor which items are CRITICAL.
Posting to Slack is irreversible (people can act on it; it cannot be unsent), so:

- the message is built only from fixed fields of the validated report (no FDA or
  inventory free text, so injected text can never reach Slack);
- the exact text and channel are shown, and nothing is sent unless a human types "yes";
- this is not a model tool: the model cannot call it, and the read-only tool allowlist
  is unchanged. It never orders, writes inventory, or makes clinical decisions.
"""
import json
import re
import urllib.error
import urllib.request

try:  # imported as src.pharmacy_tools (tests run from the repo root)
    from .fda import _ssl_context
except ImportError:  # imported as pharmacy_tools with src on PYTHONPATH
    from pharmacy_tools.fda import _ssl_context

SLACK_POST_URL = "https://slack.com/api/chat.postMessage"  # fixed host, never from input
CHANNEL_ID = re.compile(r"[CG][A-Z0-9]{8,12}", re.ASCII)  # a channel id, never a person or a name
ITEM_ID = re.compile(r"[A-Za-z0-9_.:-]{1,64}", re.ASCII)
NDC = re.compile(r"\d{4}-\d{4}-\d{2}|\d{5}-\d{3}-\d{2}|\d{5}-\d{4}-\d{1}", re.ASCII)
DAYS = re.compile(r"\d{1,6}\.\d{2}", re.ASCII)
FDA_STATES = {"MATCH", "NO_MATCH", "PARTIAL", "STALE", "UNAVAILABLE", "CONFLICTING_RECORDS",
              "NOT_CALLED", "NOT_REACHED", "NOT_RETRIEVED"}  # states the harness report can emit
MAX_ITEMS = 20
TIMEOUT_SECONDS = 10


def build_critical_alert(report):
    """Return the alert text for CRITICAL items, or None when there is nothing to send.

    Only identifiers, numbers and fixed codes are copied, each checked against a strict
    pattern; anything that does not match is shown as "?" instead of being forwarded.
    """
    if type(report) is not dict or report.get("data_mode") != "SYNTHETIC" or type(report.get("items")) is not list:
        return None
    critical = [item for item in report["items"] if type(item) is dict and item.get("local_class") == "CRITICAL"]
    if not critical:
        return None

    def safe(value, pattern):
        return value if type(value) is str and pattern.fullmatch(value) else "?"

    lines = [f"SYNTHETIC TEST DATA: store {report.get('store_id') if report.get('store_id') == 1618 else '?'}",
             f"Critical stock: {len(critical)} item(s) need replenishment review"]
    for item in critical[:MAX_ITEMS]:
        days = "0.00 (zero stock)" if item.get("zero_stock_fact") is True else safe(item.get("days_of_supply_display"), DAYS)
        fda = item.get("fda_state") if item.get("fda_state") in FDA_STATES else "?"
        lines.append(f"- {safe(item.get('item_id'), ITEM_ID)} | NDC {safe(item.get('package_ndc'), NDC)} | "
                     f"{days} days of supply | FDA {fda}")
    if len(critical) > MAX_ITEMS:
        lines.append(f"- ... and {len(critical) - MAX_ITEMS} more")
    lines.append("Review only: no order was placed and no inventory was changed. "
                 "Verify the evidence before acting.")
    return "\n".join(lines)


def confirm_action(description, ask=input):
    """Pause for a human. Only an explicit "yes" proceeds; anything else cancels."""
    try:
        answer = ask(f"About to: {description}\nProceed? (yes/no): ")
    except (EOFError, KeyboardInterrupt):
        return False
    return type(answer) is str and answer.strip().lower() == "yes"


def post_slack_message(channel, text, token, *, urlopen=urllib.request.urlopen):
    """One Slack chat.postMessage call. Returns a static outcome code, never the token or raw error."""
    request = urllib.request.Request(SLACK_POST_URL, method="POST",
                                     data=json.dumps({"channel": channel, "text": text}).encode(),
                                     headers={"Authorization": f"Bearer {token}",
                                              "Content-Type": "application/json; charset=utf-8"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS, context=_ssl_context()) as response:
            body = json.loads(response.read(100_000))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return "SLACK_UNAVAILABLE"
    if type(body) is dict and body.get("ok") is True:
        return "SENT"
    error = body.get("error") if type(body) is dict else None
    return f"SLACK_ERROR_{error.upper()}" if type(error) is str and re.fullmatch(r"[a-z_]{1,40}", error) else "SLACK_ERROR"


def send_critical_alert(report, *, channel, token, ask=input, post=post_slack_message, show=print):
    """Build, preview, confirm, then post. Returns {"state": ..., "text": ...}."""
    if type(channel) is not str or not CHANNEL_ID.fullmatch(channel):
        return {"state": "INVALID_CHANNEL", "text": None}
    text = build_critical_alert(report)
    if text is None:
        return {"state": "NOTHING_TO_SEND", "text": None}
    show(f"\n--- Slack alert preview (channel {channel}) ---\n{text}\n---")
    if not confirm_action(f"post this critical-stock alert to Slack channel {channel} (cannot be unsent)", ask):
        return {"state": "CANCELLED", "text": text}
    if not token:
        return {"state": "TOKEN_MISSING", "text": text}
    return {"state": post(channel, text, token), "text": text}
