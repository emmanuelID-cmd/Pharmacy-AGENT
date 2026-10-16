"""Human-only paired demo workflow. No Agent tools or inventory writes."""
from copy import deepcopy
from datetime import datetime, timezone

from .closing import ClosingDemo, ClosingError
from .push import validate_subscription

ORDER_EVENT = "synthetic-order-v1"
DELIVERY_EVENT = "synthetic-delivery-v1"


def pending_result():
    return {"state": "Temporarily Unavailable", "reason_code": "PUSH_DELIVERY_UNCONFIRMED",
            "attempted": True, "push_service_accepted": False, "delivery_confirmed": False}


class PairedDemo:
    def __init__(self, store, sender):
        self.store, self.sender = store, sender

    @staticmethod
    def active(room, role=None):
        if room["state"].get("closed"):
            raise ClosingError("DEMO_PAIRING_ENDED", 409)
        if role and room["role"] != role:
            raise ClosingError("DEMO_ROLE_FORBIDDEN", 403)

    @staticmethod
    def workflow(state):
        workflow = ClosingDemo()
        workflow.snapshot = deepcopy(state.get("snapshot"))
        workflow.orders = deepcopy(state.get("orders", {}))
        workflow.intents = deepcopy(state.get("intents", {}))
        workflow.order = workflow.orders.get(state.get("last_submission"))
        return workflow

    @staticmethod
    def save(state, workflow):
        state.update(snapshot=workflow.snapshot, orders=workflow.orders, intents=workflow.intents)
        if workflow.order:
            state["last_submission"] = workflow.order["submission_id"]

    def status(self, cookie=None):
        result = {"configured": self.store.configured, "role": None, "paired": False, "orders": [], "notifications": {}}
        if not cookie:
            return result
        with self.store.room(cookie) as room:
            self.active(room)
            state = room["state"]
            result.update(role=room["role"], paired=room["paired"], expires_at=room["expires_at"],
                          notifications={role: bool(state.get("subscriptions", {}).get(role)) for role in ("orderer", "manufacturer")})
            # Do not return device hashes, invitation hashes, endpoints or encryption keys.
            fields = ("order_id", "closing_id", "submitted_at", "lines", "delivery", "revision", "state", "order_placed", "inventory_write_effects")
            result["orders"] = [{key: deepcopy(order[key]) for key in fields if key in order}
                                for order in state.get("orders", {}).values()]
        return result

    def renew_invite(self, cookie):
        with self.store.room(cookie) as room:
            self.active(room, "orderer")
            if room["paired"]:
                raise ClosingError("DEMO_PAIRING_ALREADY_BOUND_OR_UNAVAILABLE", 409)
        return self.store.renew_invite(cookie)

    def register(self, cookie, subscription):
        if subscription is not None:
            validate_subscription(subscription)
        with self.store.room(cookie) as room:
            self.active(room)
            room["state"].setdefault("subscriptions", {})[room["role"]] = deepcopy(subscription)
        return {"registered": subscription is not None}

    def leave(self, cookie):
        with self.store.room(cookie) as room:
            room["state"]["closed"] = True
            room["state"]["subscriptions"] = {}
        return {"ended": True}

    def close(self, cookie):
        with self.store.room(cookie) as room:
            self.active(room, "orderer")
            workflow = self.workflow(room["state"])
            result = workflow.close_day()
            self.save(room["state"], workflow)
        return result

    def submit(self, cookie, closing_id, submission_id, lines):
        with self.store.room(cookie) as room:
            self.active(room, "orderer")
            if not room["paired"] or not all(room["state"].get("subscriptions", {}).get(role) for role in ("orderer", "manufacturer")):
                raise ClosingError("DEMO_BOTH_PHONES_NOT_READY", 409)
            workflow = self.workflow(room["state"])
            result = workflow.submit(closing_id, submission_id, lines)
            self.save(room["state"], workflow)
        return result

    def notify(self, cookie, order_id, closing_id=None, kind=ORDER_EVENT):
        if kind not in (ORDER_EVENT, DELIVERY_EVENT):
            raise ClosingError("DEMO_EVENT_INVALID", 422)
        event_id = kind + ":" + order_id
        with self.store.room(cookie) as room:
            self.active(room, "orderer" if kind == ORDER_EVENT else "manufacturer")
            state = room["state"]
            order = next((value for value in state.get("orders", {}).values() if value["order_id"] == order_id), None)
            if order is None or (closing_id is not None and closing_id != order["closing_id"]):
                raise ClosingError("DEMO_ORDER_NOT_FOUND", 409)
            if kind == DELIVERY_EVENT and not order.get("delivery"):
                raise ClosingError("DEMO_DELIVERY_NOT_RECORDED", 409)
            events = state.setdefault("events", {})
            if event_id in events:
                return deepcopy(events[event_id])
            recipient_role = "manufacturer" if kind == ORDER_EVENT else "orderer"
            target = state.get("subscriptions", {}).get(recipient_role)
            if not target:
                raise ClosingError("DEMO_RECIPIENT_NOT_READY", 409)
            validate_subscription(target)
            if not self.sender.configuration()["configured"]:
                raise ClosingError("PUSH_KEYS_NOT_CONFIGURED", 503)
            # Commit reservation before network IO: a worker crash/timeout cannot reopen it.
            events[event_id] = pending_result()
            target, order = deepcopy(target), deepcopy(order)
        result = self.sender.send(target, order, kind=kind)
        try:
            with self.store.room(cookie) as room:
                room["state"].setdefault("events", {})[event_id] = deepcopy(result)
        except ClosingError:
            # The committed reservation remains unconfirmed and is never automatically retried.
            pass
        return result

    def delivery(self, cookie, order_id):
        with self.store.room(cookie) as room:
            self.active(room, "manufacturer")
            order = next((value for value in room["state"].get("orders", {}).values() if value["order_id"] == order_id), None)
            if order is None:
                raise ClosingError("DEMO_ORDER_NOT_FOUND", 409)
            if "delivery" not in order:
                order["delivery"] = {"state": "SIMULATED_DELIVERY_RECEIVED",
                    "confirmed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "inventory_write_effects": 0}
            recorded = deepcopy(order)
        try:
            notification = self.notify(cookie, order_id, kind=DELIVERY_EVENT)
        except ClosingError as error:
            notification = {**pending_result(), "attempted": False, "reason_code": error.code}
        return {"order": recorded, "notification": notification}
