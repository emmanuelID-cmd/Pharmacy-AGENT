"""Human-only Chrome Web Push. No model tool, arbitrary message or arbitrary host."""
import base64
import json
import re
import time
import unicodedata
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import http_ece
import httpx
from py_vapid import Vapid

from .closing import ClosingError

MAX_PREVIEW_LINES = 6
MAX_PAYLOAD_BYTES = 3000
PRIORITIES = {"CRITICAL", "LOW", "ABOVE_THRESHOLD", "UNKNOWN"}
ENDPOINT = re.compile(r"https://fcm[.]googleapis[.]com/(?:fcm/send|wp)/[A-Za-z0-9_:/-]{16,2048}")


def display_text(value, limit):
    """Single-line display data, never instructions, markup or a destination."""
    if not isinstance(value, str):
        return None
    value = unicodedata.normalize("NFC", value)
    if (not value or len(value) > limit or any(
            unicodedata.category(char).startswith("C") or char in "<>\u2028\u2029" for char in value)):
        return None
    return value.strip() or None


def order_message(order):
    """Minimize an existing server-bound synthetic order, never a submitted message."""
    if (order.get("state") != "SIMULATED_SUBMISSION" or order.get("order_placed") is not False
            or not re.fullmatch(r"demo-[a-f0-9]{12}", order.get("order_id", ""))
            or not isinstance(order.get("lines"), list) or not 1 <= len(order["lines"]) <= 150):
        raise ClosingError("PUSH_ORDER_CONTENT_INVALID")
    preview = []
    for line in order["lines"][:MAX_PREVIEW_LINES]:
        item_id = line.get("item_id", "")
        quantity, unit, priority = line.get("quantity"), display_text(line.get("unit"), 48), line.get("local_class")
        if (not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", item_id) or type(quantity) is not int
                or not 1 <= quantity <= 1_000_000 or unit is None or priority not in PRIORITIES):
            raise ClosingError("PUSH_ORDER_CONTENT_INVALID")
        preview.append({"label": display_text(line.get("label"), 120) or f"Item {item_id}",
                        "quantity": quantity, "unit": unit, "priority": priority})
    message = {"kind": "synthetic-order-v1", "order_id": order["order_id"],
               "total_lines": len(order["lines"]), "lines": preview}
    while len(json.dumps(message, ensure_ascii=False).encode("utf-8")) > MAX_PAYLOAD_BYTES:
        preview.pop()
    return message


def decode_key(value, size):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("INVALID_PUSH_KEY")
    raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if len(raw) != size or base64.urlsafe_b64encode(raw).rstrip(b"=").decode() != value:
        raise ValueError("INVALID_PUSH_KEY")
    return raw


def validate_subscription(subscription):
    try:
        if set(subscription) != {"endpoint", "keys"} or set(subscription["keys"]) != {"p256dh", "auth"}:
            raise ValueError
        if not ENDPOINT.fullmatch(subscription["endpoint"]):
            raise ValueError
        receiver = decode_key(subscription["keys"]["p256dh"], 65)
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), receiver)
        decode_key(subscription["keys"]["auth"], 16)
    except (ValueError, TypeError, KeyError):
        raise ClosingError("PUSH_SUBSCRIPTION_INVALID") from None


def post_encrypted(endpoint, body, headers):
    # Do not follow redirects or ambient proxies. Never read/log response bodies.
    with httpx.Client(timeout=httpx.Timeout(5, connect=3), follow_redirects=False, trust_env=False) as client:
        with client.stream("POST", endpoint, content=body, headers=headers) as response:
            return response.status_code


class PushSender:
    def __init__(self, settings, *, transport=post_encrypted):
        self.settings, self.transport = settings, transport

    def vapid(self):
        contact = urlsplit(self.settings.push_subject)
        if (contact.scheme != "https" or not contact.hostname or contact.username or contact.password
                or contact.query or contact.fragment or any(ord(c) < 33 for c in self.settings.push_subject)):
            raise ValueError("INVALID_PUSH_CONTACT")
        key = decode_key(self.settings.push_private_key, 32)
        private = ec.derive_private_key(int.from_bytes(key, "big"), ec.SECP256R1())
        # RFC 8292 permits an HTTPS contact URI. The library's strict regex rejects
        # valid URI paths, so validate above and allow the project's contact page.
        return Vapid(private_key=private, conf={"no-strict": True})

    def configuration(self):
        try:
            public = self.vapid().public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
            return {"configured": True, "public_key": base64.urlsafe_b64encode(public).rstrip(b"=").decode(), "browser": "Chrome on Android"}
        except (ValueError, TypeError):
            return {"configured": False, "reason_code": "PUSH_KEYS_NOT_CONFIGURED"}

    def send(self, subscription, order):
        validate_subscription(subscription)
        message = order_message(order)
        result = {"state": "Temporarily Unavailable", "reason_code": "PUSH_DELIVERY_UNCONFIRMED",
                  "attempted": True, "push_service_accepted": False, "delivery_confirmed": False}
        try:
            vapid = self.vapid()
            headers = vapid.sign({"aud": "https://fcm.googleapis.com", "sub": self.settings.push_subject,
                                  "exp": int(time.time()) + 3600})
            headers.update({"Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream", "TTL": "300", "Urgency": "normal"})
            encrypted = http_ece.encrypt(json.dumps(message, ensure_ascii=False).encode("utf-8"),
                private_key=ec.generate_private_key(ec.SECP256R1()),
                dh=decode_key(subscription["keys"]["p256dh"], 65),
                auth_secret=decode_key(subscription["keys"]["auth"], 16), version="aes128gcm")
            status = self.transport(subscription["endpoint"], encrypted, headers)
            if status in (200, 201, 202):
                result.update(state="ACCEPTED_BY_PUSH_SERVICE", reason_code="PUSH_ACCEPTED", push_service_accepted=True)
            elif status in (404, 410):
                result.update(state="SUBSCRIPTION_EXPIRED", reason_code="PUSH_SUBSCRIPTION_EXPIRED")
            else:
                result["reason_code"] = "PUSH_SERVICE_REJECTED"
        except Exception:
            # A timeout may have happened after acceptance. Do not automatically retry.
            pass
        return result
