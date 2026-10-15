"""Dosage strength identity check (handoff to the harness owner).

PRD-Mod, "Consolidated exception contract": ambiguous strength/form/package/unit ->
AMBIGUOUS_ITEM, keep items separate, withhold the affected calculation. Today no harness
code reads `strength`: the live trace docs/eval/traces/case1_missing_strength.trace.json
shows item-001 (strength removed) reported as ABOVE_THRESHOLD / MAINTAIN.

Proposed rule, v1 scope only (validation; no order quantities, no external send):
1. A `strength` field that is present but empty or not a string is ambiguous.
2. When the source gives `strength` for some rows, a row without it is ambiguous.
3. A source that gives `strength` for no row (today's 20-row fixture and 150-item
   catalog) is unchanged until POLICY/PRD decide strength is required everywhere.

Tests marked expectedFailure describe the missing behavior: they fail today and pass once
the rule is implemented. Remove the decorator then (unittest reports an unexpected success
as a failure, so the suite turns red until it is removed).
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


def with_strength(value, item_id="item-003"):
    payload = copy.deepcopy(read_store_inventory(1618, path=LEGACY_FIXTURE_PATH))
    for row in payload["items"]:
        if row["item_id"] == item_id:
            row["strength"] = value
    return payload


def report_row(report, item_id):
    return next(r for r in report["items"] if r.get("item_id") == item_id)


class HarnessStrengthTests(unittest.TestCase):
    # Passes today: guards against requiring strength before POLICY/PRD say so.
    def test_source_without_any_strength_is_unchanged(self):
        evidence = item_reasons(read_store_inventory(1618, path=LEGACY_FIXTURE_PATH), "item-003")
        self.assertNotIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        self.assertTrue(evidence.identity_ok)

    # Passes today: a valid strength must never be flagged.
    def test_valid_strength_is_not_ambiguous(self):
        evidence = item_reasons(with_strength("10 mg"), "item-003")
        self.assertNotIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        self.assertTrue(evidence.identity_ok)

    @unittest.expectedFailure
    def test_empty_strength_is_ambiguous(self):
        evidence = item_reasons(with_strength("   "), "item-003")
        self.assertIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        self.assertFalse(evidence.identity_ok)

    @unittest.expectedFailure
    def test_non_text_strength_is_ambiguous(self):
        evidence = item_reasons(with_strength(10), "item-003")
        self.assertIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        self.assertFalse(evidence.identity_ok)

    @unittest.expectedFailure
    def test_row_missing_strength_in_a_source_that_has_it_is_ambiguous(self):
        payload = json.loads(CASE_PATH.read_text())
        self.assertIn("strength", payload["items"][1])  # the source does give strength
        self.assertNotIn("strength", payload["items"][0])  # item-001 lacks it
        evidence = item_reasons(payload, "item-001")
        self.assertIn("AMBIGUOUS_ITEM", evidence.reason_codes)
        self.assertFalse(evidence.identity_ok)
        self.assertNotIn("AMBIGUOUS_ITEM", item_reasons(payload, "item-002").reason_codes)

    @unittest.expectedFailure
    def test_ambiguous_item_withholds_days_and_requires_manual_review_end_to_end(self):
        # Same input as the live trace: today item-001 comes out as 6.22 days / MAINTAIN.
        report = run_review(run_at=EVAL_RUN, inventory_path=CASE_PATH, fda_http_get=stub_http())
        row = report_row(report, "item-001")
        self.assertIn("AMBIGUOUS_ITEM", row["reason_codes"])
        self.assertIsNone(row["days_of_supply"])
        self.assertEqual(row["local_action"], "MANUAL_REVIEW")
        self.assertEqual(report["run_state"], "MANUAL_REVIEW")
        # Unaffected rows keep their verified result.
        self.assertEqual(report_row(report, "item-003")["local_class"], "CRITICAL")


if __name__ == "__main__":
    unittest.main()
