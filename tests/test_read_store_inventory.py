import json
import tempfile
import unittest
from pathlib import Path

from src.injection_prevention.action_guard import RunBudget, execute_guarded
from src.injection_prevention.boundary_contracts import Source
from src.injection_prevention.contracts import Decision
from src.injection_prevention.safe_context import inspect_payload
from src.pharmacy_tools.inventory import FIXTURE_PATH, InventoryUnavailable, read_store_inventory


def write_tmp(content):
    handle = tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False)
    handle.write(content if type(content) is bytes else json.dumps(content).encode())
    handle.close()
    return handle.name


class ReadStoreInventoryTests(unittest.TestCase):
    def setUp(self):
        self.payload = read_store_inventory(1618)

    def test_returns_labeled_synthetic_snapshot_for_store_1618(self):
        self.assertEqual(self.payload["store_id"], 1618)
        self.assertIs(self.payload["synthetic"], True)
        self.assertEqual(self.payload["policy_version"], "SYNTHETIC-v0")
        self.assertEqual(self.payload["snapshot_timestamp"], "2026-10-07T09:00:00-04:00")
        self.assertEqual(len(self.payload["items"]), 20)

    def test_fixture_passes_prevention_intake_contract(self):
        assessment = inspect_payload(self.payload, source=Source.INVENTORY)
        self.assertTrue(assessment.source_contract_valid)
        self.assertEqual(assessment.decision, Decision.ACCEPT)

    def test_eval_card_cases_are_present(self):
        rows = {r["item_id"]: r for r in self.payload["items"]}
        case1, case2 = rows["item-001"], rows["item-002"]
        self.assertEqual((case1["package_ndc"], case1["usable_quantity"], sum(case1["daily_usage"]["units"])),
                         ("42023-240-01", 80, 180))
        self.assertEqual(round(180 / 14, 2), 12.86)
        self.assertEqual(round(80 / (180 / 14), 2), 6.22)
        self.assertEqual(case2["daily_usage"]["units"], [0] * 14)

    def test_usage_windows_end_on_last_completed_day(self):
        for row in self.payload["items"]:
            self.assertEqual(row["daily_usage"]["window_end"], "2026-10-06")
            expected_days = 13 if row["item_id"] == "item-008" else 14  # item-008 is the incomplete-history fault
            self.assertEqual(len(row["daily_usage"]["units"]), expected_days)

    def test_fault_rows_are_kept_for_manual_review(self):
        rows = {r["item_id"]: r for r in self.payload["items"]}
        self.assertNotIn("usable_quantity", rows["item-013"])  # missing stock is absent, never 0
        self.assertEqual(rows["item-012"]["usable_quantity"], -5)  # negative stock is passed through, not fixed

    def test_wrong_store_is_refused_before_reading(self):
        for store in (1619, "1618", 1618.0, True, None):
            with self.assertRaises(InventoryUnavailable) as ctx:
                read_store_inventory(store)
            self.assertEqual(ctx.exception.reason_code, "WRONG_STORE")

    def test_unreadable_malformed_and_empty_sources_are_never_healthy(self):
        cases = {
            "SOURCE_UNREADABLE": str(Path(FIXTURE_PATH).with_name("missing.json")),
            "SOURCE_MALFORMED": write_tmp(b'{"store_id": 1618, "store_id": 1618}'),  # duplicate key
            "WRONG_STORE": write_tmp({"store_id": 1619, "synthetic": True, "items": [{}]}),
            "NOT_LABELED_SYNTHETIC": write_tmp({"store_id": 1618, "synthetic": False, "items": [{}]}),
            "EMPTY_SOURCE": write_tmp({"store_id": 1618, "synthetic": True, "items": []}),
        }
        for reason, path in cases.items():
            with self.assertRaises(InventoryUnavailable) as ctx:
                read_store_inventory(1618, path=path)
            self.assertEqual(ctx.exception.reason_code, reason)

    def test_dispatched_through_prevention_guard(self):
        calls = []

        def reader(**arguments):
            calls.append(arguments)
            return read_store_inventory(**arguments)

        executors = {"read_store_inventory": reader}
        allowed = execute_guarded({"name": "read_store_inventory", "arguments": {"store_id": 1618}},
                                  executors=executors, budget=RunBudget())
        denied = execute_guarded({"name": "read_store_inventory", "arguments": {"store_id": 1619}},
                                 executors=executors, budget=RunBudget())
        self.assertEqual(calls, [{"store_id": 1618}])
        self.assertEqual((allowed.state, allowed.reason_code), ("COMPLETE", "READ_INSPECTED"))
        self.assertEqual(denied.state, "DENIED")

    def test_unavailable_source_becomes_manual_review_through_guard(self):
        def broken_reader(**arguments):
            return read_store_inventory(**arguments, path=str(Path(FIXTURE_PATH).with_name("missing.json")))

        result = execute_guarded({"name": "read_store_inventory", "arguments": {"store_id": 1618}},
                                 executors={"read_store_inventory": broken_reader}, budget=RunBudget())
        self.assertEqual((result.state, result.reason_code), ("MANUAL_REVIEW", "READ_FAILED_OR_UNAVAILABLE"))


if __name__ == "__main__":
    unittest.main()
