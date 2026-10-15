"""Dosage strength identity check (Rule B / PR #20).

PRD-Mod: ambiguous strength/form/package/unit -> AMBIGUOUS_ITEM, withhold the
affected calculation. v1 rule:
1. strength present but empty or not a string is ambiguous.
2. When the source gives strength for some rows, a row without it is ambiguous.
3. A source that gives strength for no row is unchanged until POLICY requires it.
"""
import copy
import json
import unittest
from pathlib import Path

from src.pharmacy_harness.run import run_review
from src.pharmacy_harness.validate import duplicate_item_ids, inspect_item, inspect_snapshot, parse_run_at
from src.pharmacy_tools.inventory import LEGACY_FIXTURE_PATH, read_store_inventory
from tests.test_harness_run import stub_http

EVAL_RUN = parse_run_at("2026-10-07T10:00:00-04:00")
CASE_PATH = Path(__file__).resolve().parents[1] / "docs" / "eval" / "cases" / "case1_missing_strength.json"


def item_reasons(payload, item_id):
    snapshot = inspect_snapshot(payload, run_at=EVAL_RUN)
    duplicates = duplicate_item_ids(snapshot.items)
    row = next(r for r in snapshot.items if r.get("item_id") == item_id)
    return inspect_item(row, run_at=EVAL_RUN, snapshot=snapshot, duplicate_ids=duplicates)


def without_any_strength(payload=None):
    payload = copy.deepcopy(payload or read_store_inventory(1618, path=LEGACY_FIXTURE_PATH))
    for row in payload["items"]:
        row.pop("strength", None)
    return payload


def with_strength(value, item_id="item-003"):
    payload = without_any_strength()
    for row in payload["items"]:
        if row["item_id"] == item_id:
            row["strength"] = value
    return payload


def report_row(report, item_id):
    return next(r for r in report["items"] if r.get("item_id") == item_id)


class HarnessStrengthTests(unittest.TestCase):
    def test_source_without_any_strength_is_unchanged(self):
        evidence = item_reasons(without_any_strength(), "item-003")
        self.assertNotIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        self.assertTrue(evidence.identity_ok)

    def test_valid_strength_is_not_ambiguous(self):
        evidence = item_reasons(with_strength("10 mg"), "item-003")
        self.assertNotIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        self.assertTrue(evidence.identity_ok)

    def test_empty_strength_is_ambiguous(self):
        evidence = item_reasons(with_strength("   "), "item-003")
        self.assertIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        self.assertFalse(evidence.identity_ok)

    def test_non_text_strength_is_ambiguous(self):
        evidence = item_reasons(with_strength(10), "item-003")
        self.assertIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        self.assertFalse(evidence.identity_ok)

    def test_row_missing_strength_in_a_source_that_has_it_is_ambiguous(self):
        payload = json.loads(CASE_PATH.read_text())
        self.assertIn("strength", payload["items"][1])
        self.assertNotIn("strength", payload["items"][0])
        evidence = item_reasons(payload, "item-001")
        self.assertIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        self.assertFalse(evidence.identity_ok)
        self.assertNotIn("AMBIGUOUS_ITEM", item_reasons(payload, "item-002").reason_codes)

    def test_ambiguous_item_withholds_days_and_requires_manual_review_end_to_end(self):
        report = run_review(run_at=EVAL_RUN, inventory_path=CASE_PATH, fda_http_get=stub_http())
        row = report_row(report, "item-001")
        self.assertIn("AMBIGUOUS_ITEM", row["reason_codes"])
        self.assertIsNone(row["days_of_supply"])
        self.assertEqual(row["local_action"], "MANUAL_REVIEW")
        self.assertEqual(report["run_state"], "MANUAL_REVIEW")
        self.assertEqual(report_row(report, "item-003")["local_class"], "CRITICAL")


if __name__ == "__main__":
    unittest.main()
