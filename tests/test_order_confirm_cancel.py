"""Human-in-the-loop checks for demo order notifications: explicit confirmation and cancellation."""
from copy import deepcopy
from unittest import TestCase

from src.pharmacy_agent.config import Settings
from src.pharmacy_web.app import create_app
from src.pharmacy_web.closing import ClosingDemo, ClosingError
from tests.test_paired_demo import MemoryStore, Sender, subscription
from src.pharmacy_web.paired_demo import PairedDemo
from tests.test_pharmacy_web import local_client
from tests import test_push_notifications as push_tests  # module import: its tests are not re-collected here


class SingleBrowserConfirmCancelTests(TestCase):
    def setUp(self):
        push_tests.PushTests.setUp(self)  # same synthetic keys, transport recorder and submitted order

    def notify(self):
        return self.workflow.notify(self.closing["closing_id"], self.order["order_id"], self.subscription, self.sender)

    def cancel(self):
        return self.workflow.cancel(self.closing["closing_id"], self.order["order_id"])

    def test_cancel_before_notification_blocks_any_later_send(self):
        cancelled = self.cancel()
        self.assertEqual(cancelled["state"], "CANCELLED")
        self.assertIn("cancelled_at", cancelled)
        with self.assertRaises(ClosingError) as error:
            self.notify()
        self.assertEqual(error.exception.code, "DEMO_ORDER_CANCELLED")
        self.assertEqual(self.calls, [])

    def test_cancel_is_idempotent(self):
        first = self.cancel()
        self.assertEqual(self.cancel(), first)

    def test_cancel_after_notification_is_refused(self):
        self.notify()
        with self.assertRaises(ClosingError) as error:
            self.cancel()
        self.assertEqual(error.exception.code, "DEMO_ORDER_ALREADY_NOTIFIED")
        self.assertEqual(len(self.calls), 1)

    def test_cancel_never_changes_the_inventory_report(self):
        before = deepcopy(self.workflow.close_day()["closing"])
        self.cancel()
        self.assertEqual(self.workflow.close_day()["closing"], before)

    def test_unknown_order_cannot_be_cancelled(self):
        with self.assertRaises(ClosingError) as error:
            self.workflow.cancel(self.closing["closing_id"], "demo-000000000000")
        self.assertEqual(error.exception.code, "DEMO_ORDER_NOT_FOUND")


class PairedConfirmCancelTests(TestCase):
    def setUp(self):
        self.store, self.sender = MemoryStore(), Sender()
        self.owner, self.recipient = "owner-device", self.store.join("a" * 24)
        self.workflow = PairedDemo(self.store, self.sender)
        self.workflow.register(self.owner, subscription("a"))
        self.workflow.register(self.recipient, subscription("b"))
        self.report = self.workflow.close(self.owner)["closing"]
        item = next(row["item_id"] for row in self.report["rows"] if row["suggestion"]["suggested_quantity"] is not None)
        self.order = self.workflow.submit(self.owner, self.report["closing_id"], "synthetic-intent-0001",
                                          [{"item_id": item, "quantity": 2}])

    def test_orderer_cancels_before_send_and_nothing_reaches_the_other_phone(self):
        self.assertEqual(self.workflow.cancel(self.owner, self.order["order_id"])["state"], "CANCELLED")
        with self.assertRaises(ClosingError) as error:
            self.workflow.notify(self.owner, self.order["order_id"], self.report["closing_id"])
        self.assertEqual(error.exception.code, "DEMO_ORDER_CANCELLED")
        self.assertEqual(self.sender.calls, [])
        states = [order["state"] for order in self.workflow.status(self.owner)["orders"]]
        self.assertEqual(states, ["CANCELLED"])

    def test_cancel_after_send_is_refused(self):
        self.workflow.notify(self.owner, self.order["order_id"], self.report["closing_id"])
        with self.assertRaises(ClosingError) as error:
            self.workflow.cancel(self.owner, self.order["order_id"])
        self.assertEqual(error.exception.code, "DEMO_ORDER_ALREADY_NOTIFIED")

    def test_receiving_phone_cannot_cancel(self):
        with self.assertRaises(ClosingError) as error:
            self.workflow.cancel(self.recipient, self.order["order_id"])
        self.assertEqual(error.exception.code, "DEMO_ROLE_FORBIDDEN")


class ApiConfirmCancelTests(TestCase):
    def setUp(self):
        push_tests.PushTests.setUp(self)
        self.client = local_client(create_app(self.settings, push_transport=self.sender.transport))
        closed = self.client.post("/api/closing-demo/close", json={}).json()["closing"]
        self.order = self.client.post("/api/closing-demo/submit", json={"closing_id": closed["closing_id"],
            "submission_id": "synthetic-confirm-cancel", "lines": [{"item_id": "catalog-001", "quantity": 1}]}).json()
        self.ids = {"closing_id": closed["closing_id"], "order_id": self.order["order_id"]}

    def test_submit_alone_sends_nothing(self):
        self.assertEqual(self.order["state"], "SIMULATED_SUBMISSION")
        self.assertEqual(self.calls, [])

    def test_notification_requires_explicit_confirmation(self):
        body = {**self.ids, "subscription": self.subscription}
        for confirm in (None, False):
            sent = dict(body) if confirm is None else {**body, "confirm_send": confirm}
            response = self.client.post("/api/closing-demo/notify", json=sent)
            self.assertEqual((response.status_code, response.json()["reason_code"]),
                             (428, "NOTIFICATION_CONFIRMATION_REQUIRED"))
        self.assertEqual(self.client.post("/api/closing-demo/notify", json={**body, "confirm_send": "yes"}).status_code, 422)
        self.assertEqual(self.calls, [])
        self.assertTrue(self.client.post("/api/closing-demo/notify",
                                         json={**body, "confirm_send": True}).json()["push_service_accepted"])
        self.assertEqual(len(self.calls), 1)

    def test_cancel_endpoint_then_confirmed_send_is_refused(self):
        cancelled = self.client.post("/api/closing-demo/cancel", json=self.ids)
        self.assertEqual((cancelled.status_code, cancelled.json()["state"]), (200, "CANCELLED"))
        refused = self.client.post("/api/closing-demo/notify",
                                   json={**self.ids, "subscription": self.subscription, "confirm_send": True})
        self.assertEqual((refused.status_code, refused.json()["reason_code"]), (409, "DEMO_ORDER_CANCELLED"))
        self.assertEqual(self.calls, [])

    def test_cancel_endpoint_rejects_other_sites_and_bad_ids(self):
        self.assertEqual(self.client.post("/api/closing-demo/cancel", json=self.ids,
                                          headers={"origin": "https://untrusted.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/closing-demo/cancel",
                                          json={**self.ids, "order_id": "not-an-order"}).status_code, 422)
        self.assertEqual(self.client.post("/api/closing-demo/cancel", json={**self.ids, "extra": 1}).status_code, 422)
