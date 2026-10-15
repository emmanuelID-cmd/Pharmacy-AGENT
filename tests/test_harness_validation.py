import copy
import unittest

from src.pharmacy_harness.calculate import calculate_item
from src.pharmacy_harness.validate import (
    SOURCE_FAILURE_CODES, duplicate_item_ids, inspect_item, inspect_snapshot,
    last_completed_day, locate_identity_source_faults, parse_run_at,
)
from src.pharmacy_tools.inventory import LEGACY_FIXTURE_PATH, read_store_inventory

EVAL_RUN = parse_run_at("2026-10-07T10:00:00-04:00")


def fixture():
    return read_store_inventory(1618, path=LEGACY_FIXTURE_PATH)


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

    def test_inspect_item_still_flags_a_missing_item_id(self):
        snapshot = inspect_snapshot(fixture(), run_at=EVAL_RUN)
        row = {"package_ndc": "99901-101-01", "strength": "10 mg", "dispensing_unit": "tablet",
               "usable_quantity": 1, "daily_usage": {"window_end": "2026-10-06", "units": [0] * 14}}
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        self.assertIn("INVALID_ITEM_REFERENCE", evidence.reason_codes)
        self.assertIsNone(evidence.item_id)

    def test_missing_strength_is_ambiguous_when_source_reports_strength(self):
        # Fixture rows carry strength; dropping it on one row must fail closed.
        payload = copy.deepcopy(fixture())
        snapshot = inspect_snapshot(payload, run_at=EVAL_RUN)
        row = next(item for item in snapshot.items if item["item_id"] == "item-001")
        del row["strength"]
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        self.assertFalse(evidence.identity_ok)
        self.assertIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        result = calculate_item(evidence, evidence_reference="test-ref")
        self.assertEqual(result.local_action, "MANUAL_REVIEW")
        self.assertIsNone(result.days_of_supply)
        self.assertNotEqual(result.local_action, "MAINTAIN")

    def test_blank_strength_is_ambiguous(self):
        payload = copy.deepcopy(fixture())
        snapshot = inspect_snapshot(payload, run_at=EVAL_RUN)
        row = next(item for item in snapshot.items if item["item_id"] == "item-001")
        row["strength"] = "   "
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        self.assertFalse(evidence.identity_ok)
        self.assertIn("AMBIGUOUS_ITEM", evidence.reason_codes)

    def test_source_without_strength_keys_is_unchanged(self):
        payload = copy.deepcopy(fixture())
        for item in payload["items"]:
            item.pop("strength", None)
        snapshot = inspect_snapshot(payload, run_at=EVAL_RUN)
        row = next(item for item in snapshot.items if item["item_id"] == "item-001")
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        self.assertNotIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        self.assertTrue(evidence.identity_ok)

    def test_identity_source_faults_cite_row_and_field_only(self):
        faults = locate_identity_source_faults([
            {"item_id": "item-001"},
            {"package_ndc": "42023-240-01"},
            {"item_id": "item 001"},
            {"item_id": "item-001"},
        ])
        self.assertEqual(faults, (
            {"row": 1, "field": "item_id", "reason": "DUPLICATE_ITEM_ID"},
            {"row": 2, "field": "item_id", "reason": "MISSING_ITEM_ID"},
            {"row": 3, "field": "item_id", "reason": "INVALID_ITEM_REFERENCE"},
            {"row": 4, "field": "item_id", "reason": "DUPLICATE_ITEM_ID"},
        ))
        self.assertTrue(all("item 001" not in str(fault) for fault in faults))

    def test_identity_source_faults_name_every_duplicate_row(self):
        faults = locate_identity_source_faults([
            {"item_id": "item-001"},
            {"item_id": "item-002"},
            {"item_id": "item-001"},
        ])
        self.assertEqual(faults, (
            {"row": 1, "field": "item_id", "reason": "DUPLICATE_ITEM_ID"},
            {"row": 3, "field": "item_id", "reason": "DUPLICATE_ITEM_ID"},
        ))

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
        row = {"item_id": "item-x", "package_ndc": "99901-101-01", "strength": "10 mg",
               "dispensing_unit": "tablet",
               "usable_quantity": True, "daily_usage": {"window_end": "2026-10-06", "units": [0] * 14}}
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        self.assertIn("INVALID_USABLE_STOCK", evidence.reason_codes)

    def test_source_failures_are_not_copied_onto_row_codes(self):
        later = parse_run_at("2026-10-13T10:00:00-04:00")
        payload = fixture()
        snapshot = inspect_snapshot(payload, run_at=later)
        self.assertIn("STALE_SNAPSHOT", snapshot.reason_codes)
        self.assertTrue(SOURCE_FAILURE_CODES.issuperset({"STALE_SNAPSHOT", "WRONG_STORE"}))
        row = next(item for item in snapshot.items if item["item_id"] == "item-001")
        evidence = inspect_item(row, run_at=later, snapshot=snapshot, duplicate_ids=frozenset())
        self.assertNotIn("STALE_SNAPSHOT", evidence.reason_codes)
        self.assertIn("SOURCE_EVIDENCE_BLOCKED", evidence.reason_codes)
        self.assertFalse(evidence.freshness_ok)


if __name__ == "__main__":
    unittest.main()
