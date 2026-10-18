"""Process-local synthetic closing workflow. No database or model calls.

The fixed fixture is captured once. Human-submitted demo orders and notification
previews are separate objects; neither can modify the frozen inventory report.
An explicit human notification request may call the separately scoped push sender.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import json
import secrets
from threading import Lock

from ..injection_prevention.action_guard import RunBudget, execute_guarded
from ..pharmacy_harness.calculate import calculate_item
from ..pharmacy_harness.replenishment import DemoItemPolicy, suggest_quantity, MAX_ORDER_UNITS
from ..pharmacy_harness.validate import inspect_snapshot, inspect_item, duplicate_item_ids, parse_run_at
from ..pharmacy_tools.inventory import read_store_inventory

DEMO_CLOCK = "2026-10-07T18:00:00-04:00"
PRIORITY = {"CRITICAL": 0, "LOW": 1, "ABOVE_THRESHOLD": 2, "UNKNOWN": 3}
MAX_DEMO_ORDERS = 20


class ClosingError(Exception):
    def __init__(self, code, status=422):
        self.code, self.status = code, status


def notification_preview(order):
    """Unconfigured SMS adapter: a preview is never a successful external send."""
    return {"state": "PREVIEW_ONLY", "reason_code": "SMS_PROVIDER_NOT_CONFIGURED",
            "external_sends": 0, "message": f"SYNTHETIC DEMO: {order['order_id']} reviewed by a human; {len(order['lines'])} item line(s). No purchase order was sent."}


def cancel_order(order, *, notified):
    """Mark a submitted demo order cancelled. Idempotent; refused once a notification was attempted."""
    if order.get("state") == "CANCELLED":
        return order
    if notified:
        raise ClosingError("DEMO_ORDER_ALREADY_NOTIFIED", 409)
    order["state"] = "CANCELLED"
    order["cancelled_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    return order


class ClosingDemo:
    def __init__(self, *, inventory_reader=read_store_inventory):
        self.reader = inventory_reader
        self.lock = Lock()
        self.snapshot = None
        self.order = None
        self.intent = None
        self.orders = {}
        self.intents = {}

    def close_day(self):
        with self.lock:
            if self.snapshot is None:
                self.snapshot = self._capture()
            return {"closing": deepcopy(self.snapshot), "order": deepcopy(self.order),
                    "orders": deepcopy(list(self.orders.values())), "order_limit": MAX_DEMO_ORDERS}

    def notify(self, closing_id, order_id, subscription, sender):
        # Separate authenticated human service. It is never exposed as an Agent tool.
        from .push import validate_subscription
        validate_subscription(subscription)
        with self.lock:
            order = next((item for item in self.orders.values()
                          if secrets.compare_digest(order_id, item["order_id"])), None)
            if order is None or not secrets.compare_digest(closing_id, order["closing_id"]):
                raise ClosingError("DEMO_ORDER_NOT_FOUND", 409)
            if order.get("state") == "CANCELLED":
                raise ClosingError("DEMO_ORDER_CANCELLED", 409)
            if "push_notification" in order:
                return deepcopy(order["push_notification"])
            if not sender.configuration()["configured"]:
                raise ClosingError("PUSH_KEYS_NOT_CONFIGURED", 503)
            order["push_notification"] = {"state": "Temporarily Unavailable", "reason_code": "PUSH_DELIVERY_UNCONFIRMED",
                "attempted": True, "push_service_accepted": False, "delivery_confirmed": False}
            order["push_notification"] = sender.send(subscription, order)
            return deepcopy(order["push_notification"])

    def cancel(self, closing_id, order_id):
        """Human cancellation, allowed only while no notification has been attempted."""
        with self.lock:
            order = next((item for item in self.orders.values()
                          if secrets.compare_digest(order_id, item["order_id"])), None)
            if order is None or not secrets.compare_digest(closing_id, order["closing_id"]):
                raise ClosingError("DEMO_ORDER_NOT_FOUND", 409)
            return deepcopy(cancel_order(order, notified="push_notification" in order))

    def _capture(self):
        captured = {}
        def read(**arguments):
            captured["payload"] = self.reader(**arguments)
            return captured["payload"]
        outcome = execute_guarded({"name": "read_store_inventory", "arguments": {"store_id": 1618}},
                                  executors={"read_store_inventory": read}, budget=RunBudget())
        if outcome.state != "COMPLETE" or "payload" not in captured:
            raise ClosingError("CLOSING_SOURCE_UNAVAILABLE", 503)
        payload = captured["payload"]
        moment = parse_run_at(DEMO_CLOCK)
        snapshot = inspect_snapshot(payload, run_at=moment)
        if snapshot.reason_codes or len(snapshot.items) != 150:
            raise ClosingError("CLOSING_SOURCE_REQUIRES_REVIEW", 409)
        duplicates = duplicate_item_ids(snapshot.items)
        rows = []
        for row in snapshot.items:
            evidence = inspect_item(row, run_at=moment, snapshot=snapshot, duplicate_ids=duplicates)
            result = calculate_item(evidence, evidence_reference=snapshot.snapshot_reference)
            # Explicit per-item synthetic policy; never a live default or pack inference.
            policy = DemoItemPolicy(result.item_id, result.dispensing_unit, Decimal(7), Decimal(0), Decimal(1), Decimal(1))
            suggestion = suggest_quantity(result, policy)
            rows.append({"item_id": result.item_id, "package_ndc": result.package_ndc,
                         "label": row.get("product_label", "Item requires review"),
                         "unit": result.dispensing_unit, "usable_quantity": float(result.usable_quantity) if result.usable_quantity is not None else None,
                         "average_daily_usage": str(result.average_daily_usage) if result.average_daily_usage is not None else None,
                         "days_of_supply": result.days_of_supply_display, "local_class": result.local_class,
                         "reason_codes": list(result.reason_codes), "evidence_reference": result.evidence_reference,
                         "suggestion": suggestion})
        rows.sort(key=lambda row: (PRIORITY.get(row["local_class"], 3), row["item_id"]))
        return {"closing_id": secrets.token_urlsafe(24), "synthetic": True, "model_called": False,
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "demo_clock": DEMO_CLOCK, "business_date": moment.date().isoformat(),
                "snapshot_timestamp": snapshot.snapshot_timestamp.isoformat(timespec="seconds"),
                "snapshot_reference": snapshot.snapshot_reference, "inventory_policy": snapshot.policy_version,
                "report_state": "MANUAL_REVIEW" if any(row["reason_codes"] for row in rows) else "COMPLETE",
                "source_sha256": sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "movement_summary": "Unavailable: no verified opening-to-closing movement ledger is connected.",
                "rows": rows}

    def submit(self, closing_id, submission_id, lines):
        with self.lock:
            if self.snapshot is None or not secrets.compare_digest(closing_id, self.snapshot["closing_id"]):
                raise ClosingError("DEMO_SESSION_EXPIRED", 409)
            if not lines or len(lines) > 150:
                raise ClosingError("ORDER_LINES_REQUIRED")
            by_id = {row["item_id"]: row for row in self.snapshot["rows"]}
            selected, seen = [], set()
            for line in lines:
                item_id, quantity = line["item_id"], line["quantity"]
                row = by_id.get(item_id)
                if row is None or item_id in seen:
                    raise ClosingError("ORDER_ITEM_INVALID")
                if type(quantity) is not int or not 1 <= quantity <= MAX_ORDER_UNITS:
                    raise ClosingError("ORDER_QUANTITY_INVALID")
                if row["suggestion"]["suggested_quantity"] is None:
                    raise ClosingError("ORDER_ITEM_REQUIRES_REVIEW")
                seen.add(item_id)
                selected.append({"item_id": item_id, "label": row["label"], "package_ndc": row["package_ndc"],
                                 "quantity": quantity, "unit": row["unit"], "local_class": row["local_class"],
                                 "days_of_supply": row["days_of_supply"], "evidence_reference": row["evidence_reference"],
                                 "suggested_quantity": row["suggestion"]["suggested_quantity"],
                                 "human_edited": quantity != row["suggestion"]["suggested_quantity"]})
            selected.sort(key=lambda row: (PRIORITY.get(row["local_class"], 3), row["item_id"]))
            intent = json.dumps(selected, sort_keys=True, separators=(",", ":"))
            if submission_id in self.orders:
                if self.intents[submission_id] != intent:
                    raise ClosingError("DEMO_ORDER_ALREADY_SUBMITTED", 409)
                return deepcopy(self.orders[submission_id])
            if len(self.orders) >= MAX_DEMO_ORDERS:
                raise ClosingError("DEMO_ORDER_LIMIT_REACHED", 409)
            shift = parse_run_at(DEMO_CLOCK).replace(hour=6, minute=0, second=0, microsecond=0)
            if shift <= parse_run_at(DEMO_CLOCK):
                shift += timedelta(days=1)
            order = {"order_id": "demo-" + secrets.token_hex(6), "submission_id": submission_id,
                     "closing_id": closing_id, "revision": 1, "state": "SIMULATED_SUBMISSION",
                     "submitted_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                     "lines": selected, "order_placed": False, "inventory_write_effects": 0,
                     "manufacturer_notice": {"state": "PREVIEW_ONLY", "scheduled_for": shift.isoformat(timespec="seconds"),
                         "timezone": "America/New_York", "timezone_is_demo_assumption": True, "external_sends": 0}}
            order["test_sms"] = notification_preview(order)
            self.intent, self.order = intent, order
            self.orders[submission_id] = order
            self.intents[submission_id] = intent
            return deepcopy(order)
