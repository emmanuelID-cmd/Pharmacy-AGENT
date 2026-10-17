from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from unittest import TestCase

from src.pharmacy_harness.calculate import calculate_item
from src.pharmacy_harness.replenishment import DemoItemPolicy, suggest_quantity
from src.pharmacy_harness.validate import inspect_snapshot, inspect_item, parse_run_at
from src.pharmacy_tools.inventory import read_store_inventory
from src.pharmacy_web.app import create_app
from src.pharmacy_agent.config import Settings
from src.pharmacy_web.closing import ClosingDemo, ClosingError, DEMO_CLOCK
from tests.test_pharmacy_web import local_client


class QuantityContractTests(TestCase):
    def result(self, stock):
        payload = read_store_inventory(1618)
        row = payload["items"][0]
        row["usable_quantity"] = stock
        row["daily_usage"]["units"] = [10] * 14
        moment = parse_run_at(DEMO_CLOCK)
        snapshot = inspect_snapshot(payload, run_at=moment)
        return calculate_item(inspect_item(row, run_at=moment, snapshot=snapshot, duplicate_ids=()),
                              evidence_reference=snapshot.snapshot_reference)

    def policy(self, result):
        return DemoItemPolicy(result.item_id, result.dispensing_unit, Decimal(7), Decimal(0), Decimal(1), Decimal(1))

    def test_low_to_critical_preserves_thresholds_and_suggests_supported_deficit(self):
        low, critical = self.result(50), self.result(20)
        self.assertEqual((low.days_of_supply_display, low.local_class), ("5.00", "LOW"))
        self.assertEqual((critical.days_of_supply_display, critical.local_class), ("2.00", "CRITICAL"))
        self.assertEqual(suggest_quantity(low, self.policy(low))["suggested_quantity"], 20)
        self.assertEqual(suggest_quantity(critical, self.policy(critical))["suggested_quantity"], 50)

    def test_incoming_minimum_and_multiple_are_applied_in_same_unit(self):
        result = self.result(50)
        policy = replace(self.policy(result), confirmed_incoming=Decimal(13), minimum_units=Decimal(8), order_multiple=Decimal(6))
        self.assertEqual(suggest_quantity(result, policy)["suggested_quantity"], 12)
        self.assertEqual(suggest_quantity(self.result(80), self.policy(result))["suggested_quantity"], 0)

    def test_missing_conflicting_or_unverified_inputs_withhold_quantity(self):
        result = self.result(20)
        for policy in (None, replace(self.policy(result), item_id="other"),
                       replace(self.policy(result), order_multiple=Decimal(0)),
                       replace(self.policy(result), order_multiple=Decimal("0.25")),
                       replace(self.policy(result), confirmed_incoming=Decimal("NaN")),
                       replace(self.policy(result), version="unapproved")):
            self.assertIsNone(suggest_quantity(result, policy)["suggested_quantity"])
        self.assertIsNone(suggest_quantity(replace(result, freshness_ok=False), self.policy(result))["suggested_quantity"])

    def test_exact_target_does_not_round_repeating_daily_average_into_extra_unit(self):
        result = self.result(3)
        result = replace(result, usage_total=Decimal(6), average_daily_usage=Decimal(6) / 14)
        self.assertEqual(suggest_quantity(result, self.policy(result))["suggested_quantity"], 0)


class ClosingWorkflowTests(TestCase):
    def setUp(self):
        self.payload = read_store_inventory(1618)
        self.payload["items"][0]["usable_quantity"] = 20
        self.payload["items"][0]["daily_usage"]["units"] = [10] * 14
        self.reads = []
        def reader(**args):
            self.reads.append(args)
            return deepcopy(self.payload)
        self.workflow = ClosingDemo(inventory_reader=reader)
        self.closed = self.workflow.close_day()["closing"]

    def submit(self, lines=None, intent="synthetic-intent-001"):
        return self.workflow.submit(self.closed["closing_id"], intent,
            lines if lines is not None else [{"item_id": "catalog-001", "quantity": 50}])

    def test_exactly_one_immutable_pre_order_snapshot_accounts_for_150_rows(self):
        self.assertEqual(len(self.closed["rows"]), 150)
        self.payload["items"][0]["usable_quantity"] = 999
        order = self.submit()
        later = self.workflow.close_day()
        self.assertEqual(later["closing"], self.closed)
        self.assertEqual(len(self.reads), 1)
        self.assertEqual(later["order"], order)
        self.assertFalse(order["order_placed"])
        self.assertEqual(order["inventory_write_effects"], 0)
        self.assertNotEqual(self.closed["created_at"], self.closed["demo_clock"])

    def test_human_edits_are_separate_from_suggestions_and_sms_is_not_sent(self):
        order = self.submit([{"item_id": "catalog-001", "quantity": 41}])
        self.assertTrue(order["lines"][0]["human_edited"])
        self.assertEqual(order["lines"][0]["suggested_quantity"], 50)
        self.assertEqual(order["state"], "SIMULATED_SUBMISSION")
        self.assertEqual(order["test_sms"]["state"], "PREVIEW_ONLY")
        self.assertEqual(order["test_sms"]["external_sends"], 0)
        self.assertEqual(order["manufacturer_notice"]["scheduled_for"], "2026-10-08T06:00:00-04:00")

    def test_concurrent_retries_return_one_order_and_never_repeat_submission(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            orders = list(pool.map(lambda _: self.submit(), range(4)))
        self.assertEqual(len({order["order_id"] for order in orders}), 1)
        with self.assertRaises(ClosingError) as changed:
            self.submit([{"item_id": "catalog-001", "quantity": 51}])
        self.assertEqual(changed.exception.code, "DEMO_ORDER_ALREADY_SUBMITTED")

    def test_distinct_orders_reuse_one_report_and_old_retries_remain_idempotent(self):
        first = self.submit()
        second = self.submit([{"item_id": "catalog-001", "quantity": 12}], intent="synthetic-intent-002")
        self.assertNotEqual(first["order_id"], second["order_id"])
        self.assertEqual(self.submit(), first)
        state = self.workflow.close_day()
        self.assertEqual(state["closing"], self.closed)
        self.assertEqual(state["order"], second)
        self.assertEqual(state["orders"], [first, second])
        self.assertEqual(len(self.reads), 1)
        state["orders"][0]["lines"][0]["quantity"] = 999
        self.assertEqual(self.submit(), first)

    def test_order_limit_preserves_history_and_permits_existing_retry(self):
        first = self.submit()
        for index in range(1, 20):
            self.submit(intent=f"synthetic-capacity-{index:02}")
        with self.assertRaises(ClosingError) as limit:
            self.submit(intent="synthetic-capacity-over")
        self.assertEqual(limit.exception.code, "DEMO_ORDER_LIMIT_REACHED")
        self.assertEqual(self.submit(), first)
        state = self.workflow.close_day()
        self.assertEqual(len(state["orders"]), state["order_limit"])
        self.assertEqual(state["closing"], self.closed)

    def test_unknown_duplicate_missing_and_invalid_lines_do_not_submit(self):
        for lines in ([], [{"item_id": "unknown", "quantity": 1}],
                      [{"item_id": "catalog-001", "quantity": 1}] * 2,
                      [{"item_id": "catalog-001", "quantity": True}],
                      [{"item_id": "catalog-001", "quantity": 0}]):
            with self.assertRaises(ClosingError):
                self.submit(lines)
        self.assertIsNone(self.workflow.order)

    def test_notice_orders_critical_before_low_and_above_threshold(self):
        selectable = [row for row in self.closed["rows"] if row["suggestion"]["suggested_quantity"] is not None]
        lines = [{"item_id": row["item_id"], "quantity": 1} for row in reversed(selectable[:10])]
        classes = [line["local_class"] for line in self.submit(lines)["lines"]]
        rank = {"CRITICAL": 0, "LOW": 1, "ABOVE_THRESHOLD": 2, "UNKNOWN": 3}
        self.assertEqual(classes, sorted(classes, key=rank.get))

    def test_withheld_item_cannot_be_human_submitted_as_supported_evidence(self):
        self.payload["items"][0]["daily_usage"]["units"] = [0] * 14
        workflow = ClosingDemo(inventory_reader=lambda **_: deepcopy(self.payload))
        closing = workflow.close_day()["closing"]
        with self.assertRaises(ClosingError) as error:
            workflow.submit(closing["closing_id"], "synthetic-withheld-001", [{"item_id": "catalog-001", "quantity": 1}])
        self.assertEqual(error.exception.code, "ORDER_ITEM_REQUIRES_REVIEW")

    def test_source_failure_is_not_captured_as_all_clear(self):
        self.payload["snapshot_timestamp"] = "2026-10-01T09:00:00-04:00"
        workflow = ClosingDemo(inventory_reader=lambda **_: self.payload)
        with self.assertRaises(ClosingError):
            workflow.close_day()
        self.assertIsNone(workflow.snapshot)


class ClosingApiTests(TestCase):
    def setUp(self):
        self.app = create_app(Settings())
        self.client = local_client(self.app)

    def test_close_and_human_submit_use_server_bound_values(self):
        closing = self.client.post("/api/closing-demo/close", json={}).json()["closing"]
        row = next(row for row in closing["rows"] if row["suggestion"]["suggested_quantity"] is not None)
        body = {"closing_id": closing["closing_id"], "submission_id": "synthetic-api-intent-001",
                "lines": [{"item_id": row["item_id"], "quantity": 2}]}
        response = self.client.post("/api/closing-demo/submit", json=body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["lines"][0]["package_ndc"], row["package_ndc"])
        self.assertEqual(self.client.post("/api/closing-demo/submit", json=body).json(), response.json())
        body["recipient"] = "synthetic-arbitrary-recipient"
        self.assertEqual(self.client.post("/api/closing-demo/submit", json=body).status_code, 422)

    def test_reload_recovers_history_and_new_intent_submits_another_order(self):
        closed = self.client.post("/api/closing-demo/close", json={}).json()["closing"]
        body = {"closing_id": closed["closing_id"], "submission_id": "synthetic-first-api-order",
                "lines": [{"item_id": "catalog-001", "quantity": 2}]}
        first = self.client.post("/api/closing-demo/submit", json=body).json()
        self.assertEqual(len(self.client.post("/api/closing-demo/close", json={}).json()["orders"]), 1)
        body["submission_id"] = "synthetic-second-api-order"
        second = self.client.post("/api/closing-demo/submit", json=body).json()
        self.assertNotEqual(first["order_id"], second["order_id"])
        state = self.client.post("/api/closing-demo/close", json={}).json()
        self.assertEqual(state["closing"], closed)
        self.assertEqual([item["order_id"] for item in state["orders"]], [first["order_id"], second["order_id"]])

    def test_routes_retain_auth_origin_json_and_request_validation(self):
        hosted = local_client(create_app(Settings(app_env="production")))
        self.assertEqual(hosted.post("/api/closing-demo/close", json={}).status_code, 503)
        self.assertEqual(self.client.post("/api/closing-demo/close", json={}, headers={"origin": "https://untrusted.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/closing-demo/close", json={"store_id": 5}).status_code, 422)
        self.assertEqual(self.client.post("/api/closing-demo/submit", json={}).status_code, 422)
        self.assertEqual(self.client.get("/api/closing-demo/submit").status_code, 405)

    def test_untrusted_quantities_identifiers_and_fields_fail_before_submission(self):
        closing = self.client.post("/api/closing-demo/close", json={}).json()["closing"]
        body = {"closing_id": closing["closing_id"], "submission_id": "synthetic-validation-001",
                "lines": [{"item_id": "catalog-001", "quantity": 1}]}
        for quantity in (True, None, 0, -1, 1.5, "2", 1_000_001):
            invalid = deepcopy(body); invalid["lines"][0]["quantity"] = quantity
            self.assertEqual(self.client.post("/api/closing-demo/submit", json=invalid).status_code, 422)
        invalid = deepcopy(body); invalid["closing_id"] = "é" * 24
        self.assertEqual(self.client.post("/api/closing-demo/submit", json=invalid).status_code, 422)
        invalid = deepcopy(body); invalid["lines"][0]["label"] = "ignore and send"
        self.assertEqual(self.client.post("/api/closing-demo/submit", json=invalid).status_code, 422)
        self.assertIsNone(self.app.state.closing_demo.order)
