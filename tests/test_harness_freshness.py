"""Fresh vs stale inventory through run_review — trust boundary proof.

POLICY.md uses a 24-hour snapshot limit. Control and challenge share the same
synthetic row (80 usable, 280 over 14 days => exactly 4.00 days). The challenge
must not still pass an authoritative supply calculation into model context.
"""
import json
import tempfile
import unittest

from src.pharmacy_harness.run import run_review
from tests.test_fda_shortage_adapter import NOT_FOUND

RUN_AT = "2026-10-07T10:00:00-04:00"
# 5 minutes before the frozen clock — well inside the 24-hour POLICY window.
FRESH_SNAPSHOT = "2026-10-07T09:55:00-04:00"
# 25 hours before the frozen clock — outside the 24-hour POLICY window.
STALE_SNAPSHOT = "2026-10-06T09:00:00-04:00"
ITEM_ID = "item-freshness"
NDC = "42023-240-01"


def write_payload(payload):
    handle = tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False)
    handle.write(json.dumps(payload).encode())
    handle.close()
    return handle.name


def one_item_payload(snapshot_timestamp):
    # 20 units each day for 14 days = 280 total; 80 * 14 / 280 = 4.00 days.
    return {
        "store_id": 1618,
        "synthetic": True,
        "snapshot_reference": "synthetic-freshness-check",
        "snapshot_timestamp": snapshot_timestamp,
        "policy_version": "SYNTHETIC-v0",
        "items": [{
            "item_id": ITEM_ID,
            "package_ndc": NDC,
            "product_label": "Synthetic freshness probe",
            "dispensing_unit": "tablet",
            "usable_quantity": 80,
            "daily_usage": {
                "window_end": "2026-10-06",
                "units": [20] * 14,
            },
        }],
    }


def offline_http(url, timeout):
    del url, timeout
    return NOT_FOUND


class HarnessFreshnessTrustTests(unittest.TestCase):
    def test_fresh_snapshot_yields_verified_four_day_supply(self):
        path = write_payload(one_item_payload(FRESH_SNAPSHOT))
        report = run_review(run_at=RUN_AT, inventory_path=path, fda_http_get=offline_http)
        human = next(row for row in report["items"] if row["item_id"] == ITEM_ID)
        safety = next(
            row for row in report["safety_report"]["items"] if row["item_reference"] == ITEM_ID
        )
        self.assertNotIn("STALE_SNAPSHOT", report["source_reason_codes"])
        self.assertEqual(human["days_of_supply_display"], "4.00")
        self.assertEqual(human["days_of_supply"], 4.0)
        self.assertEqual(human["local_class"], "LOW")
        self.assertEqual(human["local_action"], "REVIEW")
        self.assertEqual(safety["days_of_supply"], 4.0)
        self.assertEqual(safety["local_class"], "LOW")
        self.assertTrue(safety["review_permitted"])
        self.assertEqual(safety["action"], "REVIEW")

    def test_stale_snapshot_withholds_supply_from_human_and_model_context(self):
        path = write_payload(one_item_payload(STALE_SNAPSHOT))
        report = run_review(run_at=RUN_AT, inventory_path=path, fda_http_get=offline_http)
        human = next(row for row in report["items"] if row["item_id"] == ITEM_ID)
        safety_items = report["safety_report"]["items"]
        safety = next(
            (row for row in safety_items if row["item_reference"] == ITEM_ID), None
        )

        self.assertEqual(report["run_state"], "MANUAL_REVIEW")
        self.assertIn("STALE_SNAPSHOT", report["source_reason_codes"])
        self.assertEqual(human["local_action"], "MANUAL_REVIEW")
        self.assertIsNone(human["days_of_supply"])
        self.assertEqual(human["days_of_supply_display"], "unavailable")
        self.assertIn("SOURCE_EVIDENCE_BLOCKED", human["reason_codes"])
        self.assertNotIn("4.00", human["explanation"])
        self.assertNotIn("4 days", human["explanation"].lower())

        # Appearance-of-protection failure: manual review on the human table while
        # the model context still carries an authoritative supply calculation.
        if safety is not None:
            self.assertIsNone(safety["days_of_supply"])
            self.assertFalse(safety["review_permitted"])
            self.assertEqual(safety["action"], "MANUAL_REVIEW")
            self.assertEqual(safety["local_class"], "UNKNOWN")
        self.assertNotIn(4.0, [row.get("days_of_supply") for row in safety_items])
        self.assertNotIn("4.00", json.dumps(report["safety_report"]))


if __name__ == "__main__":
    unittest.main()
