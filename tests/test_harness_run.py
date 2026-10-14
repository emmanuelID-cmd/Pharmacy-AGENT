import json
import socket
import unittest
from unittest.mock import patch
from pathlib import Path

from src.injection_prevention.action_guard import RunBudget
from src.pharmacy_harness.run import run_review
from src.pharmacy_tools.inventory import CATALOG_FIXTURE_PATH, FIXTURE_PATH, LEGACY_FIXTURE_PATH
from tests.test_fda_shortage_adapter import NOT_FOUND, RECORD, NDC, ok

EVAL_RUN = "2026-10-07T10:00:00-04:00"


def stub_http(match_ndc=NDC, match_record=RECORD, timeout_ndc=None):
    def http_get(url, timeout):
        if timeout_ndc is not None and timeout_ndc in url:
            raise socket.timeout("timed out")
        if match_ndc in url:
            return ok([match_record])
        return NOT_FOUND
    return http_get


def run(**kwargs):
    kwargs.setdefault("run_at", EVAL_RUN)
    kwargs.setdefault("fda_http_get", stub_http())
    kwargs.setdefault("inventory_path", LEGACY_FIXTURE_PATH)
    return run_review(**kwargs)


class HarnessRunTests(unittest.TestCase):
    def test_guarded_inventory_read_uses_store_1618_fixture(self):
        report = run()
        self.assertEqual(report["source_state"], "COMPLETE")
        self.assertEqual(report["store_id"], 1618)
        self.assertEqual(report["data_mode"], "SYNTHETIC")
        self.assertEqual(len(report["items"]), 20)
        self.assertIs(report["order_placed"], False)
        self.assertIs(report["inventory_changed"], False)

    def test_150_catalog_rows_are_all_reviewed_in_fifteen_bounded_batches(self):
        calls = []
        def no_matches(url, timeout):
            calls.append(url)
            return NOT_FOUND
        report = run_review(run_at=EVAL_RUN, inventory_path=CATALOG_FIXTURE_PATH,
                            fda_http_get=no_matches, fda_sleep=lambda _seconds: None)
        self.assertEqual(report["source_state"], "COMPLETE")
        self.assertEqual(len(report["items"]), 150)
        self.assertEqual(len({row["package_ndc"] for row in report["items"]}), 150)
        self.assertEqual(len(calls), 15)
        self.assertTrue(all("OR" in url for url in calls))
        self.assertTrue(all(row["fda_state"] == "NO_MATCH" for row in report["items"]))

    def test_wrong_store_never_means_healthy_stock(self):
        report = run(store_id=1619)
        self.assertEqual(report["items"], [])
        self.assertEqual(report["run_state"], "MANUAL_REVIEW")
        self.assertEqual(report["source_state"], "DENIED")

    def test_unreadable_source_is_manual_review(self):
        missing = str(Path(FIXTURE_PATH).with_name("missing.json"))
        report = run(inventory_path=missing)
        self.assertEqual(report["items"], [])
        self.assertEqual((report["source_state"], report["source_reason"]),
                         ("MANUAL_REVIEW", "READ_FAILED_OR_UNAVAILABLE"))

    def test_fda_called_only_for_accepted_ndcs(self):
        calls = []

        def http_get(url, timeout):
            calls.append(url)
            if NDC in url:
                return ok([RECORD])
            return NOT_FOUND

        report = run(fda_http_get=http_get)
        ndcs = {row["package_ndc"] for row in report["items"] if row["package_ndc"]}
        self.assertEqual(len(calls), (len(ndcs) + 9) // 10)
        self.assertIn(NDC, ndcs)
        case1 = next(row for row in report["items"] if row["item_id"] == "item-001")
        self.assertEqual(case1["fda_state"], "MATCH")
        case2 = next(row for row in report["items"] if row["item_id"] == "item-002")
        self.assertEqual(case2["fda_state"], "NO_MATCH")

    def test_budget_exhaustion_stops_further_reads(self):
        report = run(budget=RunBudget(max_attempts=1))
        # Inventory consumes the only attempt; FDA is not dispatched.
        fda_states = {row["fda_state"] for row in report["items"]}
        self.assertIn("NOT_CALLED", fda_states)
        self.assertEqual(report["source_state"], "COMPLETE")

    def test_late_fda_result_is_discarded_and_further_reads_stop(self):
        clock = [0.0]
        calls = []
        budget = RunBudget(seconds=1, clock=lambda: clock[0])

        def late_http(url, timeout):
            calls.append(url)
            clock[0] = 2.0
            return ok([RECORD])

        report = run(budget=budget, fda_http_get=late_http)
        row = next(item for item in report["items"] if item["package_ndc"] == NDC)
        self.assertEqual(row["fda_state"], "UNAVAILABLE")
        self.assertIsNone(row["fda_status"])
        self.assertIsNone(row["fda_availability"])
        self.assertIsNone(row["external_action"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(budget.counts()["completed"], 1)
        self.assertIn("NOT_CALLED", {item["fda_state"] for item in report["items"]})
        self.assertEqual(row["days_of_supply_display"], "6.22")
        self.assertEqual(row["local_action"], "MAINTAIN")
        self.assertIn("UNAVAILABLE", row["explanation"])

    def test_invalid_captured_fda_result_cannot_bypass_dispatch_rejection(self):
        invalid = {"results": "invalid source rows", "meta": {"state": "MATCH"}}
        with patch("src.pharmacy_harness.run.get_fda_shortage_context_batch", return_value=invalid):
            report = run()
        self.assertEqual({item["fda_state"] for item in report["items"]}, {"UNAVAILABLE"})
        self.assertTrue(all(item["fda_status"] is None for item in report["items"]))
        self.assertTrue(all(item["external_action"] is None for item in report["items"]))

    def test_safety_report_is_report_v1_and_never_claims_an_order(self):
        report = run()
        safety = report["safety_report"]
        self.assertIsNotNone(safety)
        self.assertEqual(safety["schema_version"], "report-v1")
        self.assertEqual(safety["store_id"], 1618)
        self.assertIs(safety["order_placed"], False)
        self.assertIs(safety["inventory_changed"], False)
        tampered = json.loads(json.dumps(safety))
        tampered["order_placed"] = True
        self.assertNotEqual(tampered["order_placed"], safety["order_placed"])

    def test_stale_clock_marks_snapshot_but_still_lists_rows(self):
        report = run(run_at="2026-10-13T10:00:00-04:00")
        self.assertEqual(report["run_state"], "MANUAL_REVIEW")
        self.assertTrue(all(row["local_action"] == "MANUAL_REVIEW" for row in report["items"]))
        self.assertTrue(all(row["days_of_supply"] is None for row in report["items"]))

    def test_partial_fda_pagination_survives_run_review(self):
        def http_get(url, timeout):
            if NDC in url:
                return ok([RECORD], total=2)
            return NOT_FOUND

        report = run(fda_http_get=http_get)
        row = next(item for item in report["items"] if item["item_id"] == "item-001")
        self.assertEqual(row["fda_state"], "PARTIAL")
        self.assertEqual(row["local_class"], "ABOVE_THRESHOLD")
        self.assertEqual(row["days_of_supply_display"], "6.22")
        self.assertIn("not a complete national result", row["explanation"])

    def test_malformed_fda_body_is_unavailable_not_no_shortage(self):
        def http_get(url, timeout):
            if NDC in url:
                return 200, b"<html>not json"
            return NOT_FOUND

        report = run(fda_http_get=http_get)
        row = next(item for item in report["items"] if item["item_id"] == "item-001")
        self.assertEqual(row["fda_state"], "UNAVAILABLE")
        self.assertEqual(row["local_class"], "ABOVE_THRESHOLD")
        self.assertIn("not no shortage", row["explanation"])

    def test_fda_package_mismatch_is_no_match_and_keeps_local_class(self):
        other = dict(RECORD, package_ndc="42023-240-02")

        def http_get(url, timeout):
            if NDC in url:
                return ok([other])
            return NOT_FOUND

        report = run(fda_http_get=http_get)
        row = next(item for item in report["items"] if item["item_id"] == "item-001")
        self.assertEqual(row["package_ndc"], NDC)
        self.assertEqual(row["fda_state"], "NO_MATCH")
        self.assertEqual(row["local_class"], "ABOVE_THRESHOLD")
        self.assertIsNone(row["external_action"])
        self.assertIn("not guaranteed supply", row["explanation"])


if __name__ == "__main__":
    unittest.main()
