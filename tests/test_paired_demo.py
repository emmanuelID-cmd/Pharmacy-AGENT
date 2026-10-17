"""Two logical devices/workers with synthetic browser keys and no external sends."""
import base64
from contextlib import contextmanager
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from threading import RLock
from unittest import TestCase

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from src.pharmacy_agent.config import Settings
from src.pharmacy_web.app import create_app
from src.pharmacy_web.closing import ClosingError
from src.pharmacy_web.demo_store import COOKIE
from src.pharmacy_web.paired_demo import PairedDemo, ORDER_EVENT, DELIVERY_EVENT
from src.pharmacy_web.push import order_message


def subscription(label):
    def encode(value): return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
    public = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return {"endpoint": "https://fcm.googleapis.com/fcm/send/" + label * 32,
            "keys": {"p256dh": encode(public), "auth": encode(b"synthetic-auth!!")}}


class MemoryStore:
    configured = True
    def __init__(self):
        self.lock, self.state, self.joined = RLock(), {}, False
    def create(self): return "owner-device", "a" * 24
    def join(self, code):
        with self.lock:
            if code != "a" * 24 or self.joined: raise ClosingError("DEMO_PAIRING_CODE_INVALID_OR_EXPIRED", 409)
            self.joined = True
            return "recipient-device"
    def renew_invite(self, cookie): return "a" * 24
    @contextmanager
    def room(self, cookie):
        with self.lock:
            if cookie not in ("owner-device", "recipient-device") or (cookie == "recipient-device" and not self.joined):
                raise ClosingError("DEMO_DEVICE_NOT_PAIRED", 403)
            room = {"role": "orderer" if cookie == "owner-device" else "manufacturer",
                    "paired": self.joined, "expires_at": "2026-10-17T18:00:00+00:00", "state": deepcopy(self.state)}
            yield room
            self.state = room["state"]


class Sender:
    def __init__(self): self.calls, self.fail = [], False
    def configuration(self): return {"configured": True}
    def send(self, target, order, *, kind=ORDER_EVENT):
        self.calls.append((deepcopy(target), order_message(order, kind)))
        if self.fail: raise RuntimeError("synthetic transport uncertainty")
        return {"state": "ACCEPTED_BY_PUSH_SERVICE", "reason_code": "PUSH_ACCEPTED", "attempted": True,
                "push_service_accepted": True, "delivery_confirmed": False}


class PairedDemoTests(TestCase):
    def setUp(self):
        self.store, self.sender = MemoryStore(), Sender()
        self.owner, self.recipient = "owner-device", self.store.join("a" * 24)
        self.workflow = PairedDemo(self.store, self.sender)
        self.a, self.b = subscription("a"), subscription("b")
        self.workflow.register(self.owner, self.a); self.workflow.register(self.recipient, self.b)
        self.report = self.workflow.close(self.owner)["closing"]
        self.item = next(row["item_id"] for row in self.report["rows"] if row["suggestion"]["suggested_quantity"] is not None)
        self.order = self.workflow.submit(self.owner, self.report["closing_id"], "synthetic-intent-0001", [{"item_id": self.item, "quantity": 2}])

    def test_order_routes_to_recipient_and_delivery_routes_back_to_orderer(self):
        self.workflow.notify(self.owner, self.order["order_id"], self.report["closing_id"])
        self.assertEqual(self.sender.calls[0][0], self.b)
        self.assertEqual(self.sender.calls[0][1]["kind"], ORDER_EVENT)
        other_worker = PairedDemo(self.store, self.sender)
        result = other_worker.delivery(self.recipient, self.order["order_id"])
        self.assertEqual(self.sender.calls[1][0], self.a)
        self.assertEqual(self.sender.calls[1][1]["kind"], DELIVERY_EVENT)
        self.assertEqual(self.sender.calls[1][1]["lines"][0]["quantity"], 2)
        self.assertTrue(result["notification"]["push_service_accepted"])
        self.assertEqual(result["order"]["delivery"]["inventory_write_effects"], 0)
        self.assertEqual(other_worker.close(self.owner)["closing"], self.report)

    def test_duplicate_concurrent_delivery_and_send_reserve_once(self):
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _: self.workflow.delivery(self.recipient, self.order["order_id"]), range(5)))
        self.assertEqual(len(self.sender.calls), 1)
        self.assertTrue(all(r["order"]["delivery"] == results[0]["order"]["delivery"] for r in results))
        with ThreadPoolExecutor(max_workers=5) as pool:
            list(pool.map(lambda _: self.workflow.notify(self.owner, self.order["order_id"]), range(5)))
        self.assertEqual(len(self.sender.calls), 2)

    def test_unrelated_device_wrong_role_and_missing_order_cannot_send(self):
        for cookie, identifier in [(self.owner, self.order["order_id"]), ("other-device", self.order["order_id"]), (self.recipient, "demo-000000000000")]:
            with self.assertRaises(ClosingError): self.workflow.delivery(cookie, identifier)
        with self.assertRaises(ClosingError): self.workflow.close(self.recipient)
        with self.assertRaises(ClosingError): self.workflow.notify(self.recipient, self.order["order_id"])
        self.assertEqual(self.sender.calls, [])

    def test_pending_reservation_survives_sender_exception_without_resend(self):
        self.sender.fail = True
        with self.assertRaises(RuntimeError): self.workflow.notify(self.owner, self.order["order_id"])
        self.sender.fail = False
        result = PairedDemo(self.store, self.sender).notify(self.owner, self.order["order_id"])
        self.assertFalse(result["push_service_accepted"])
        self.assertTrue(result["attempted"])
        self.assertEqual(len(self.sender.calls), 1)

    def test_subscriptions_and_secret_bindings_never_leave_status(self):
        status = json.dumps(self.workflow.status(self.recipient))
        self.assertNotIn("fcm.googleapis.com", status)
        self.assertNotIn(self.a["keys"]["p256dh"], status)
        self.assertNotIn("owner_hash", status)
        self.assertEqual(self.workflow.status(self.recipient)["orders"][0]["order_id"], self.order["order_id"])

    def test_disable_and_end_pairing_preserve_orders_but_block_future_sends(self):
        self.workflow.register(self.owner, None)
        result = self.workflow.delivery(self.recipient, self.order["order_id"])
        self.assertEqual(result["notification"]["reason_code"], "DEMO_RECIPIENT_NOT_READY")
        self.assertEqual(self.sender.calls, [])
        self.workflow.leave(self.recipient)
        with self.assertRaises(ClosingError): self.workflow.notify(self.owner, self.order["order_id"])
        self.assertEqual(len(self.store.state["orders"]), 1)

    def test_delivery_payload_requires_a_recorded_delivery(self):
        with self.assertRaises(ClosingError): order_message(self.order, DELIVERY_EVENT)
        with self.assertRaises(ClosingError): order_message(self.order, "arbitrary-event")

    def test_two_api_clients_use_httponly_roles_and_reject_custom_recipients(self):
        store = MemoryStore()
        settings = Settings(app_env="production", reviewer_username="reviewer", reviewer_password="synthetic-password", allowed_hosts=("testserver",))
        apps = [create_app(settings, demo_store=store), create_app(settings, demo_store=store)]
        for app in apps: app.state.paired_demo.sender = self.sender
        with TestClient(apps[0], base_url="https://testserver", headers={"Authorization": "Basic " + base64.b64encode(b"reviewer:synthetic-password").decode()}) as a, TestClient(apps[1], base_url="https://testserver", headers={"Authorization": "Basic " + base64.b64encode(b"reviewer:synthetic-password").decode()}) as b:
            response = a.post("/api/demo-pairing/create", json={})
            self.assertIn("HttpOnly", response.headers["set-cookie"])
            self.assertIn("Secure", response.headers["set-cookie"])
            self.assertIn("SameSite=strict", response.headers["set-cookie"])
            self.assertEqual(b.post("/api/demo-pairing/join", json={"code": response.json()["code"]}).status_code, 200)
            for client, value in [(a,self.a),(b,self.b)]:
                self.assertEqual(client.post("/api/demo-pairing/subscription",json={"subscription":value}).status_code,200)
            report=a.post("/api/closing-demo/close",json={}).json()["closing"]
            order=a.post("/api/closing-demo/submit",json={"closing_id":report["closing_id"],"submission_id":"another-intent-00001","lines":[{"item_id":self.item,"quantity":3}]}).json()
            self.assertEqual(a.post("/api/demo-pairing/delivery",json={"order_id":order["order_id"]}).status_code,403)
            self.assertEqual(b.post("/api/demo-pairing/delivery",json={"order_id":order["order_id"],"recipient":"other"}).status_code,422)
            self.assertEqual(b.post("/api/demo-pairing/delivery",json={"order_id":order["order_id"]}).status_code,200)
            self.assertEqual(a.post("/api/demo-pairing/status",json={"role":"manufacturer"}).status_code,422)
            self.assertEqual(b.post("/api/demo-pairing/subscription",json={"subscription":self.b},headers={"origin":"https://untrusted.example"}).status_code,403)
