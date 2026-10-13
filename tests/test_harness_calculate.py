import unittest

from src.pharmacy_harness.calculate import calculate_item, classify_days
from src.pharmacy_harness.facts import to_trusted_fact
from src.pharmacy_harness.validate import inspect_item, inspect_snapshot, parse_run_at
from src.pharmacy_tools.inventory import read_store_inventory

EVAL_RUN = parse_run_at("2026-10-07T10:00:00-04:00")
REF = "synthetic-snapshot-2026-10-07"

EXPECTED = {
    "item-001": ("6.22", "ABOVE_THRESHOLD", "MAINTAIN"),
    "item-002": ("unavailable", "UNKNOWN", "MANUAL_REVIEW"),
    "item-003": ("2.00", "CRITICAL", "REVIEW"),
    "item-004": ("5.00", "LOW", "REVIEW"),
    "item-005": ("3.75", "LOW", "REVIEW"),
    "item-006": ("0.00", "CRITICAL", "REVIEW"),
    "item-007": ("25.00", "ABOVE_THRESHOLD", "MAINTAIN"),
    "item-008": ("unavailable", "UNKNOWN", "MANUAL_REVIEW"),
    "item-009": ("5.10", "ABOVE_THRESHOLD", "MAINTAIN"),
    "item-010": ("2.10", "LOW", "REVIEW"),
    "item-011": ("10.00", "ABOVE_THRESHOLD", "MAINTAIN"),
    "item-012": ("unavailable", "UNKNOWN", "MANUAL_REVIEW"),
    "item-013": ("unavailable", "UNKNOWN", "MANUAL_REVIEW"),
    "item-014": ("3.00", "LOW", "REVIEW"),
    "item-015": ("1.00", "CRITICAL", "REVIEW"),
    "item-016": ("8.00", "ABOVE_THRESHOLD", "MAINTAIN"),
    "item-017": ("6.43", "ABOVE_THRESHOLD", "MAINTAIN"),
    "item-018": ("1.33", "CRITICAL", "REVIEW"),
    "item-019": ("4.00", "LOW", "REVIEW"),
    "item-020": ("30.00", "ABOVE_THRESHOLD", "MAINTAIN"),
}


def results():
    payload = read_store_inventory(1618)
    snapshot = inspect_snapshot(payload, run_at=EVAL_RUN)
    out = {}
    for row in snapshot.items:
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        out[evidence.item_id] = calculate_item(evidence, evidence_reference=snapshot.snapshot_reference)
    return out


class HarnessCalculateTests(unittest.TestCase):
    def test_unrounded_boundaries(self):
        self.assertEqual(classify_days(2.0), ("CRITICAL", "REVIEW"))
        self.assertEqual(classify_days(2.0000001), ("LOW", "REVIEW"))
        self.assertEqual(classify_days(5.0), ("LOW", "REVIEW"))
        self.assertEqual(classify_days(5.0000001), ("ABOVE_THRESHOLD", "MAINTAIN"))

    def test_fixture_rows_match_policy_labels(self):
        for item_id, (display, local_class, action) in EXPECTED.items():
            with self.subTest(item_id):
                result = results()[item_id]
                self.assertEqual(result.days_of_supply_display, display)
                self.assertEqual(result.local_class, local_class)
                self.assertEqual(result.local_action, action)

    def test_case_1_unrounded_basis(self):
        result = results()["item-001"]
        self.assertEqual(result.usage_total, 180)
        self.assertAlmostEqual(result.average_daily_usage, 180 / 14)
        self.assertAlmostEqual(result.days_of_supply, 80 / (180 / 14))
        self.assertEqual(round(result.days_of_supply, 2), 6.22)

    def test_zero_usage_is_not_infinity(self):
        result = results()["item-002"]
        self.assertEqual(result.average_daily_usage, 0)
        self.assertIsNone(result.days_of_supply)
        self.assertIn("NO_CONSUMPTION_BASIS", result.reason_codes)

    def test_zero_stock_with_usage_is_critical_zero(self):
        result = results()["item-006"]
        self.assertTrue(result.zero_stock_fact)
        self.assertEqual(result.days_of_supply, 0.0)
        self.assertEqual(result.local_class, "CRITICAL")

    def test_trusted_fact_uses_displayed_days_for_case_1(self):
        fact = to_trusted_fact(results()["item-001"])
        self.assertEqual(fact.days_of_supply, 6.22)
        self.assertEqual(fact.local_class, "ABOVE_THRESHOLD")
        self.assertTrue(fact.verified)
        self.assertEqual(fact.dispensing_unit, "unit")

    def test_zero_usage_fact_is_unknown_duration(self):
        fact = to_trusted_fact(results()["item-002"])
        self.assertIsNone(fact.days_of_supply)
        self.assertEqual(fact.local_class, "UNKNOWN")
        self.assertTrue(fact.verified)

    def test_missing_quantity_does_not_become_a_fact(self):
        self.assertIsNone(to_trusted_fact(results()["item-013"]))

    def test_negative_stock_does_not_become_a_fact(self):
        self.assertIsNone(to_trusted_fact(results()["item-012"]))

    def test_critical_stock_without_usage_maps_unknown_in_prevention_context(self):
        payload = read_store_inventory(1618)
        snapshot = inspect_snapshot(payload, run_at=EVAL_RUN)
        row = {
            "item_id": "item-zero",
            "package_ndc": "99901-199-01",
            "dispensing_unit": "tablet",
            "usable_quantity": 0,
            "daily_usage": {"window_end": "2026-10-05", "units": [1] * 13},  # incomplete
        }
        evidence = inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=frozenset())
        result = calculate_item(evidence, evidence_reference=REF)
        self.assertTrue(result.zero_stock_fact)
        self.assertEqual(result.local_class, "CRITICAL")
        self.assertEqual(result.local_action, "MANUAL_REVIEW")
        self.assertIsNone(result.days_of_supply)
        fact = to_trusted_fact(result)
        self.assertEqual(fact.local_class, "UNKNOWN")
        self.assertIsNone(fact.days_of_supply)
        self.assertFalse(fact.verified)


if __name__ == "__main__":
    unittest.main()
