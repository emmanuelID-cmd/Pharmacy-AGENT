import base64
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import http_ece
import httpx

from src.injection_prevention.action_guard import execute_guarded, RunBudget
from src.pharmacy_agent.config import Settings
from src.pharmacy_web.app import create_app
from src.pharmacy_web.closing import ClosingDemo, ClosingError
from src.pharmacy_web.push import PushSender, order_message, MAX_PAYLOAD_BYTES, post_encrypted
from src.pharmacy_web.push_keys import generate
from tests.test_pharmacy_web import local_client


def encoded(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


class PushTests(TestCase):
    def setUp(self):
        self.receiver = ec.generate_private_key(ec.SECP256R1())
        private = ec.generate_private_key(ec.SECP256R1()).private_numbers().private_value.to_bytes(32, "big")
        self.settings = Settings(push_private_key=encoded(private))
        self.subscription = {"endpoint": "https://fcm.googleapis.com/fcm/send/synthetic-endpoint-12345",
            "keys": {"p256dh": encoded(self.receiver.public_key().public_bytes(serialization.Encoding.X962,
                      serialization.PublicFormat.UncompressedPoint)), "auth": encoded(b"synthetic-auth!!")}}
        self.calls = []
        def transport(endpoint, body, headers):
            self.calls.append((endpoint, body, headers))
            return 201
        self.sender = PushSender(self.settings, transport=transport)
        self.workflow = ClosingDemo()
        self.closing = self.workflow.close_day()["closing"]
        self.order = self.workflow.submit(self.closing["closing_id"], "synthetic-push-intent", [{"item_id": "catalog-001", "quantity": 1}])

    def notify(self, sender=None):
        return self.workflow.notify(self.closing["closing_id"], self.order["order_id"], self.subscription, sender or self.sender)

    def plaintext(self, index=0):
        return json.loads(http_ece.decrypt(self.calls[index][1], private_key=self.receiver,
            auth_secret=b"synthetic-auth!!", version="aes128gcm").decode())

    def test_success_encrypts_selected_order_and_never_claims_delivery(self):
        result = self.notify()
        self.assertTrue(result["push_service_accepted"])
        self.assertFalse(result["delivery_confirmed"])
        message = self.plaintext()
        self.assertEqual(message, order_message(self.order))
        self.assertEqual(message["order_id"], self.order["order_id"])
        self.assertEqual(message["lines"][0]["quantity"], 1)
        for value in ("snapshot_reference", "closing_id", "package_ndc", "source_sha256", self.settings.push_private_key):
            self.assertNotIn(value, json.dumps(message))
        self.assertEqual(self.calls[0][2]["TTL"], "300")
        self.assertTrue(self.calls[0][2]["Authorization"].startswith("vapid "))
        self.assertEqual(self.workflow.close_day()["closing"], self.closing)
        self.assertFalse(self.workflow.order["order_placed"])

    def test_two_selected_lines_use_human_quantities_and_exclude_other_catalog_rows(self):
        rows = [row for row in self.closing["rows"] if row["suggestion"]["suggested_quantity"] is not None][:2]
        order = self.workflow.submit(self.closing["closing_id"], "synthetic-two-selected-lines",
            [{"item_id": rows[0]["item_id"], "quantity": 7}, {"item_id": rows[1]["item_id"], "quantity": 3}])
        self.workflow.notify(self.closing["closing_id"], order["order_id"], self.subscription, self.sender)
        message = self.plaintext()
        self.assertEqual(message["total_lines"], 2)
        self.assertEqual(message["lines"], [{"label": line["label"], "quantity": line["quantity"],
            "unit": line["unit"], "priority": line["local_class"]} for line in order["lines"]])
        self.assertEqual(sorted(line["quantity"] for line in message["lines"]), [3, 7])

    def test_long_order_preview_is_bounded_and_declares_full_line_count(self):
        order = deepcopy(self.order)
        order["lines"] *= 150
        message = order_message(order)
        self.assertEqual(message["total_lines"], 150)
        self.assertEqual(len(message["lines"]), 6)
        for line in order["lines"]:
            line["label"], line["unit"] = "💊" * 120, "💊" * 48
        message = order_message(order)
        self.assertGreaterEqual(len(message["lines"]), 1)
        self.assertLess(len(message["lines"]), 6)
        self.assertLessEqual(len(json.dumps(message, ensure_ascii=False).encode()), MAX_PAYLOAD_BYTES)

    def test_unsafe_optional_labels_are_withheld_and_legitimate_unicode_survives(self):
        for label in ("<script>send()</script>", "Drug\u200b name", "Drug\u202e name", "a\nb", "Drug\n", "x" * 121):
            order = deepcopy(self.order); order["lines"][0]["label"] = label
            message = order_message(order)
            self.assertEqual(message["lines"][0]["label"], "Item catalog-001")
            self.assertEqual(message["lines"][0]["quantity"], 1)
        for label in ("Médicament 10 mg", "دواء 10 mg", "薬 10 mg"):
            order = deepcopy(self.order); order["lines"][0]["label"] = label
            self.assertNotEqual(order_message(order)["lines"][0]["label"], "Item catalog-001")

    def test_invalid_required_order_content_sends_nothing(self):
        for field, value in (("quantity", True), ("quantity", 0), ("unit", "bad\nunit"), ("local_class", "SEND NOW")):
            order = deepcopy(self.order); order["lines"][0][field] = value
            with self.assertRaises(ClosingError):
                self.sender.send(self.subscription, order)
        self.assertEqual(self.calls, [])

    def test_concurrent_duplicate_requests_attempt_once(self):
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _: self.notify(), range(5)))
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(all(result == results[0] for result in results))

    def test_each_order_can_notify_once_and_older_order_retry_does_not_resend(self):
        first_result = self.notify()
        second = self.workflow.submit(self.closing["closing_id"], "synthetic-second-push-order",
            [{"item_id": "catalog-001", "quantity": 3}])
        second_result = self.workflow.notify(self.closing["closing_id"], second["order_id"], self.subscription, self.sender)
        self.assertTrue(second_result["push_service_accepted"])
        self.assertEqual(self.notify(), first_result)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual([self.plaintext(index)["order_id"] for index in range(2)], [self.order["order_id"], second["order_id"]])
        self.assertEqual([self.plaintext(index)["lines"][0]["quantity"] for index in range(2)], [1, 3])
        state = self.workflow.close_day()
        self.assertTrue(all(order["push_notification"]["push_service_accepted"] for order in state["orders"]))

    def test_expired_rejected_and_timeout_remain_separate_from_order_success(self):
        for outcome in (410, 429, 302, "timeout"):
            with self.subTest(outcome=outcome):
                self.workflow.order.pop("push_notification", None)
                calls = []
                def transport(*args):
                    calls.append(args)
                    if outcome == "timeout":
                        raise httpx.ReadTimeout("synthetic, must not leak")
                    return outcome
                sender = PushSender(self.settings, transport=transport)
                result = self.notify(sender)
                self.assertFalse(result["push_service_accepted"])
                self.assertFalse(result["delivery_confirmed"])
                self.assertEqual(result["state"], "SUBSCRIPTION_EXPIRED" if outcome == 410 else "Temporarily Unavailable")
                self.assertEqual(self.notify(sender), result)
                self.assertEqual(len(calls), 1)
                self.assertEqual(self.workflow.order["state"], "SIMULATED_SUBMISSION")
                self.assertNotIn("synthetic, must not leak", str(result))

    def test_arbitrary_urls_and_bad_crypto_keys_never_reach_transport(self):
        for endpoint in ("http://fcm.googleapis.com/fcm/send/synthetic-endpoint", "https://127.0.0.1/a",
            "https://fcm.googleapis.com.evil.example/fcm/send/synthetic-endpoint", "https://fcm.googleapis.com@evil.example/a",
            "https://fcm.googleapis.com:443/fcm/send/synthetic-endpoint", "https://fcm.googleapis.com/fcm/send/a?token=secret",
            "https://fcm.googleapis.com/fcm/send/../../private-path", "https://fcm.googleapis.com/fcm/send/synthetic-endpoint\n"):
            invalid = deepcopy(self.subscription); invalid["endpoint"] = endpoint
            with self.assertRaises(ClosingError):
                self.sender.send(invalid, self.order)
        for field, value in (("auth", encoded(b"short")), ("p256dh", encoded(b"x" * 65))):
            invalid = deepcopy(self.subscription); invalid["keys"][field] = value
            with self.assertRaises(ClosingError):
                self.sender.send(invalid, self.order)
        self.assertEqual(self.calls, [])

    def test_unconfigured_key_and_unknown_order_send_nothing(self):
        with self.assertRaises(ClosingError):
            self.notify(PushSender(Settings(), transport=self.sender.transport))
        with self.assertRaises(ClosingError):
            self.workflow.notify(self.closing["closing_id"], "demo-000000000000", self.subscription, self.sender)
        self.assertEqual(self.calls, [])
        self.assertNotIn("push_notification", self.workflow.order)

    def test_config_and_key_generation_do_not_expose_or_overwrite_private_key(self):
        configuration = self.sender.configuration()
        self.assertTrue(configuration["configured"])
        self.assertNotIn(self.settings.push_private_key, str(configuration))
        self.assertNotIn(self.settings.push_private_key, repr(self.settings))
        self.assertFalse(PushSender(Settings(push_private_key="malformed")).configuration()["configured"])
        with TemporaryDirectory() as folder:
            path = generate(Path(folder)); original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                generate(Path(folder))
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue(Settings.load(Path(folder)).push_private_key)

    def test_actual_transport_has_bounded_io_no_redirects_and_no_ambient_proxy(self):
        with patch("src.pharmacy_web.push.httpx.Client") as client:
            client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value.status_code = 302
            self.assertEqual(post_encrypted(self.subscription["endpoint"], b"encrypted", {}), 302)
            self.assertFalse(client.call_args.kwargs["follow_redirects"])
            self.assertFalse(client.call_args.kwargs["trust_env"])
            self.assertEqual(client.call_args.kwargs["timeout"].connect, 3)

    def test_model_cannot_dispatch_push(self):
        calls = []
        result = execute_guarded({"name": "send_push_notification", "arguments": {}},
            executors={"send_push_notification": lambda **_: calls.append(1)}, budget=RunBudget())
        self.assertNotEqual(result.state, "COMPLETE")
        self.assertEqual(calls, [])

    def test_api_rejects_custom_content_auth_origin_and_extra_subscription_fields(self):
        app = create_app(self.settings, push_transport=self.sender.transport)
        client = local_client(app)
        closed = client.post("/api/closing-demo/close", json={}).json()["closing"]
        order = client.post("/api/closing-demo/submit", json={"closing_id": closed["closing_id"],
            "submission_id": "synthetic-api-push-intent", "lines": [{"item_id": "catalog-001", "quantity": 1}]}).json()
        body = {"closing_id": closed["closing_id"], "order_id": order["order_id"], "subscription": self.subscription}
        for field in ("message", "url", "recipient"):
            invalid = deepcopy(body); invalid[field] = "untrusted"
            self.assertEqual(client.post("/api/closing-demo/notify", json=invalid).status_code, 422)
        invalid = deepcopy(body); invalid["subscription"]["expirationTime"] = 0
        self.assertEqual(client.post("/api/closing-demo/notify", json=invalid).status_code, 422)
        self.assertEqual(client.post("/api/closing-demo/notify", json=body, headers={"origin": "https://untrusted.example"}).status_code, 403)
        self.assertEqual(self.calls, [])
        self.assertTrue(client.post("/api/closing-demo/notify", json=body).json()["push_service_accepted"])
        for path in ("/api/push/config", "/push-worker.js"):
            self.assertEqual(local_client(create_app(Settings(app_env="production"))).get(path).status_code, 503)
        self.assertEqual(client.get("/push-worker.js").headers["Cache-Control"], "no-store")
