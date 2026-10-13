import copy
import unittest

from src.pharmacy_harness.validate import (
    duplicate_item_ids, inspect_item, inspect_snapshot, last_completed_day, parse_run_at,
)
from src.pharmacy_tools.inventory import read_store_inventory

EVAL_RUN = parse_run_at("2026-10-07T10:00:00-04:00")


def fixture():
    return read_store_inventory(1618)


class HarnessValidationTests(unittest.TestCase):
    def test_eval_clock_last_completed_day_is_october_6(self):
        self.assertEqual(str(last_completed_day(EVAL_RUN)), "2026-10-06")
        self.assertEqual(EVAL_RUN.tzname(), "EDT")

    def test_run_at_requires_timezone(self):
        with self.assertRaises(ValueError):
            parse_run_at("2026-10-07T10:00:00")

    def test_fixture_snapshot_is_fresh_at_eval_run(self):
        snapshot = inspect_snapshot(fixture(), run_at=EVAL_RUN)
        self.assertTrue(snapshot.store_ok and snapshot.synthetic_ok and snapshot.policy_ok)
        self.assertTrue(snapshot.snapshot_ok)
        self.assertEqual(snapshot.reason_codes, ())
        self.assertEqual(len(snapshot.items), 20)

    def test_snapshot_older_than_24_hours_is_stale(self):
        later = parse_run_at("2026-10-08T10:00:00-04:00")
        snapshot = inspect_snapshot(fixture(), run_at=later)
        self.assertIn("STALE_SNAPSHOT", snapshot.reason_codes)
        self.assertFalse(snapshot.snapshot_ok)

    def test_future_snapshot_is_rejected(self):
        earlier = parse_run_at("2026-10-07T08:00:00-04:00")
        snapshot = inspect_snapshot(fixture(), run_at=earlier)
        self.assertIn("FUTURE_SNAPSHOT", snapshot.reason_codes)

    def test_item_001_has_complete_evidence(self):
        payload = fixture()
        snapshot = inspect_snapshot(payload, run_at=EVAL_RUN)
        row = next(item for item in snapshot.items if item["item_id"] == "item-001")
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        self.assertTrue(evidence.identity_ok and evidence.quantity_ok and evidence.usage_ok)
        self.assertTrue(evidence.freshness_ok)
        self.assertEqual(evidence.usable_quantity, 80)
        self.assertEqual(evidence.usage_total, 180)
        self.assertEqual(evidence.usage_day_count, 14)
        self.assertEqual(evidence.reason_codes, ())

    def test_item_008_incomplete_usage_is_unknown_not_zero(self):
        payload = fixture()
        snapshot = inspect_snapshot(payload, run_at=EVAL_RUN)
        row = next(item for item in snapshot.items if item["item_id"] == "item-008")
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        self.assertFalse(evidence.usage_ok)
        self.assertIsNone(evidence.usage_total)
        self.assertEqual(evidence.usage_day_count, 13)
        self.assertIn("INCOMPLETE_USAGE", evidence.reason_codes)

    def test_item_013_missing_stock_is_not_zero(self):
        payload = fixture()
        snapshot = inspect_snapshot(payload, run_at=EVAL_RUN)
        row = next(item for item in snapshot.items if item["item_id"] == "item-013")
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        self.assertFalse(evidence.quantity_ok)
        self.assertIsNone(evidence.usable_quantity)
        self.assertIn("MISSING_USABLE_STOCK", evidence.reason_codes)

    def test_negative_stock_is_invalid(self):
        payload = fixture()
        snapshot = inspect_snapshot(payload, run_at=EVAL_RUN)
        row = next(item for item in snapshot.items if item["item_id"] == "item-012")
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        self.assertIn("INVALID_USABLE_STOCK", evidence.reason_codes)

    def test_duplicate_item_ids_fail_identity(self):
        payload = copy.deepcopy(fixture())
        payload["items"][1]["item_id"] = "item-001"
        snapshot = inspect_snapshot(payload, run_at=EVAL_RUN)
        duplicates = duplicate_item_ids(snapshot.items)
        self.assertEqual(duplicates, frozenset({"item-001"}))
        evidence = inspect_item(payload["items"][0], run_at=EVAL_RUN, snapshot=snapshot,
                                duplicate_ids=duplicates)
        self.assertFalse(evidence.identity_ok)
        self.assertIn("DUPLICATE_ITEM_ID", evidence.reason_codes)

    def test_boolean_true_is_not_a_quantity(self):
        snapshot = inspect_snapshot(fixture(), run_at=EVAL_RUN)
        row = {"item_id": "item-x", "package_ndc": "99901-101-01", "dispensing_unit": "tablet",
               "usable_quantity": True, "daily_usage": {"window_end": "2026-10-06", "units": [0] * 14}}
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        self.assertIn("INVALID_USABLE_STOCK", evidence.reason_codes)


if __name__ == "__main__":
    unittest.main()
