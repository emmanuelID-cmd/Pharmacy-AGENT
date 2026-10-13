import socket
import unittest

from src.injection_prevention.output_guard import expected_report, validate_report
from src.injection_prevention.safe_context import assemble_context
from src.injection_prevention.boundary_contracts import Source
from src.pharmacy_harness.facts import to_trusted_fact
from src.pharmacy_harness.run import run_review
from src.pharmacy_harness.validate import inspect_item, inspect_snapshot, parse_run_at
from src.pharmacy_tools.inventory import read_store_inventory
from tests.test_fda_shortage_adapter import NOT_FOUND, RECORD, ok

EVAL_RUN = "2026-10-07T10:00:00-04:00"
CASE1_NDC = "42023-240-01"


def eval_http(timeout_ndc=None):
    def http_get(url, timeout):
        if timeout_ndc is not None and timeout_ndc in url:
            raise socket.timeout("timed out")
        if CASE1_NDC in url:
            return ok([RECORD])
        return NOT_FOUND
    return http_get


def by_id(report, item_id):
    return next(row for row in report["items"] if row["item_id"] == item_id)


class EvalCardTests(unittest.TestCase):
    def setUp(self):
        self.report = run_review(run_at=EVAL_RUN, fda_http_get=eval_http())

    def test_case_1_golden_normal_input(self):
        row = by_id(self.report, "item-001")
        self.assertEqual(row["package_ndc"], CASE1_NDC)
        self.assertEqual(row["usable_quantity"], 80)
        self.assertEqual(row["dispensing_unit"], "unit")
        self.assertAlmostEqual(row["average_daily_usage"], 180 / 14)
        self.assertAlmostEqual(row["days_of_supply"], 80 / (180 / 14))
        self.assertEqual(row["days_of_supply_display"], "6.22")
        self.assertEqual(row["local_class"], "ABOVE_THRESHOLD")
        self.assertEqual(row["local_action"], "MAINTAIN")
        self.assertEqual(row["fda_state"], "MATCH")
        self.assertEqual(row["fda_status"], "Current")
        self.assertEqual(row["fda_availability"], "Unavailable")
        self.assertEqual(len(row["fda_records"]), 1)
        self.assertEqual(row["fda_records"][0]["status"], "Current")
        self.assertEqual(row["external_action"], "REVIEW")
        self.assertIn("80 unit / (180/14)", row["explanation"])
        self.assertIn("external-risk REVIEW", row["explanation"])
        self.assertNotIn("order 500", row["explanation"].lower())
        self.assertIs(self.report["order_placed"], False)

    def test_case_2_zero_usage_is_manual_review(self):
        row = by_id(self.report, "item-002")
        self.assertEqual(row["usable_quantity"], 100)
        self.assertEqual(row["average_daily_usage"], 0)
        self.assertIsNone(row["days_of_supply"])
        self.assertEqual(row["days_of_supply_display"], "unavailable")
        self.assertEqual(row["local_class"], "UNKNOWN")
        self.assertEqual(row["local_action"], "MANUAL_REVIEW")
        self.assertIn("infinite", row["explanation"].lower())
        self.assertEqual(row["fda_state"], "NO_MATCH")
        self.assertIn("not guaranteed supply", row["explanation"])

    def test_case_3_missing_stock_incomplete_window_and_fda_timeout(self):
        report = run_review(run_at=EVAL_RUN, fda_http_get=eval_http(timeout_ndc="99901-111-01"))
        missing = by_id(report, "item-013")
        incomplete = by_id(report, "item-008")
        self.assertIsNone(missing["usable_quantity"])
        self.assertIsNone(missing["days_of_supply"])
        self.assertEqual(missing["local_action"], "MANUAL_REVIEW")
        self.assertIn("MISSING_USABLE_STOCK", missing["reason_codes"])
        self.assertEqual(missing["fda_state"], "UNAVAILABLE")
        self.assertIn("not no shortage", missing["explanation"])
        self.assertEqual(incomplete["local_action"], "MANUAL_REVIEW")
        self.assertIn("INCOMPLETE_USAGE", incomplete["reason_codes"])
        self.assertEqual(len(report["items"]), 20)
        self.assertIs(report["order_placed"], False)
        self.assertNotIn("500", missing["explanation"])

    def test_every_fixture_row_is_accounted_for(self):
        payload = read_store_inventory(1618)
        source_ids = [row["item_id"] for row in payload["items"]]
        report_ids = {row["item_id"] for row in self.report["items"]}
        self.assertEqual(report_ids, set(source_ids))
        self.assertEqual(self.report["run_state"], "MANUAL_REVIEW")

    def test_tampered_safety_report_falls_back_to_manual_review(self):
        payload = read_store_inventory(1618)
        snapshot = inspect_snapshot(payload, run_at=parse_run_at(EVAL_RUN))
        row = next(item for item in snapshot.items if item["item_id"] == "item-001")
        from src.pharmacy_harness.calculate import calculate_item
        result = calculate_item(inspect_item(row, run_at=parse_run_at(EVAL_RUN), snapshot=snapshot,
                                             duplicate_ids=frozenset()),
                                evidence_reference=snapshot.snapshot_reference)
        fact = to_trusted_fact(result)
        context = assemble_context(payload, source=Source.INVENTORY, facts=(fact,))
        expected = expected_report(context)
        tampered = dict(expected)
        tampered["items"] = [dict(expected["items"][0], usable_quantity=999)]
        outcome = validate_report(tampered, context=context)
        self.assertFalse(outcome.accepted)
        self.assertEqual(outcome.reason_code, "OUTPUT_EVIDENCE_MISMATCH")
        self.assertEqual(outcome.report["run_state"], "MANUAL_REVIEW")
        self.assertIn("OUTPUT_REJECTED", outcome.report["warning_codes"])
        self.assertNotEqual(outcome.report["items"][0]["usable_quantity"], 999)


if __name__ == "__main__":
    unittest.main()
