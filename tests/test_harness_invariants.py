import copy
import json
import tempfile
import unittest

from src.pharmacy_harness.report import assess_fda
from src.pharmacy_harness.run import run_review
from src.pharmacy_harness.validate import parse_run_at
from src.pharmacy_tools.inventory import read_store_inventory
from tests.test_fda_shortage_adapter import NOT_FOUND, RECORD, NDC, ok

EVAL_RUN = "2026-10-07T10:00:00-04:00"


def eval_http():
    def http_get(url, timeout):
        if NDC in url:
            return ok([RECORD])
        return NOT_FOUND
    return http_get


def write_payload(payload):
    handle = tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False)
    handle.write(json.dumps(payload).encode())
    handle.close()
    return handle.name


class HarnessInvariantTests(unittest.TestCase):
    def test_human_report_has_every_source_row_exactly_once(self):
        payload = read_store_inventory(1618)
        report = run_review(run_at=EVAL_RUN, fda_http_get=eval_http())
        source_ids = [row["item_id"] for row in payload["items"]]
        human_ids = [row["item_id"] for row in report["items"]]
        self.assertEqual(len(human_ids), len(source_ids))
        self.assertEqual(len(human_ids), len(set(human_ids)))
        self.assertEqual(set(human_ids), set(source_ids))

    def test_outputs_agree_except_documented_critical_unknown_mapping(self):
        report = run_review(run_at=EVAL_RUN, fda_http_get=eval_http())
        safety_by_id = {row["item_reference"]: row for row in report["safety_report"]["items"]}
        for row in report["items"]:
            safety = safety_by_id.get(row["item_id"])
            if row["usable_quantity"] is None or (row["usable_quantity"] is not None and row["usable_quantity"] < 0):
                self.assertIsNone(safety)
                self.assertEqual(row["local_action"], "MANUAL_REVIEW")
                continue
            self.assertIsNotNone(safety)
            if row["zero_stock_fact"] and row["days_of_supply"] is None:
                self.assertEqual(row["local_class"], "CRITICAL")
                self.assertEqual(safety["local_class"], "UNKNOWN")
                self.assertIsNone(safety["days_of_supply"])
                continue
            if row["days_of_supply"] is None:
                self.assertEqual(row["local_class"], "UNKNOWN")
                self.assertEqual(safety["local_class"], "UNKNOWN")
                continue
            self.assertEqual(safety["local_class"], row["local_class"])
            self.assertEqual(round(safety["days_of_supply"], 2), round(row["days_of_supply"], 2))

    def test_shared_ndc_is_not_a_duplicate(self):
        base = read_store_inventory(1618)
        first = copy.deepcopy(next(row for row in base["items"] if row["item_id"] == "item-001"))
        second = copy.deepcopy(first)
        second["item_id"] = "item-shared-b"
        second["usable_quantity"] = 40
        payload = {
            "store_id": 1618, "synthetic": True,
            "snapshot_reference": "synthetic-snapshot-2026-10-07",
            "snapshot_timestamp": "2026-10-07T09:00:00-04:00",
            "policy_version": "SYNTHETIC-v0",
            "items": [first, second],
        }
        calls = []

        def http_get(url, timeout):
            calls.append(url)
            return ok([RECORD])

        report = run_review(run_at=EVAL_RUN, inventory_path=write_payload(payload), fda_http_get=http_get)
        self.assertEqual(len(report["items"]), 2)
        self.assertEqual({row["item_id"] for row in report["items"]}, {"item-001", "item-shared-b"})
        self.assertEqual({row["package_ndc"] for row in report["items"]}, {NDC})
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(row["fda_state"] == "MATCH" for row in report["items"]))
        by_id = {row["item_id"]: row for row in report["items"]}
        self.assertEqual(by_id["item-001"]["local_class"], "ABOVE_THRESHOLD")
        self.assertEqual(by_id["item-shared-b"]["days_of_supply_display"], "3.11")  # 40 * 14 / 180
        self.assertEqual(by_id["item-shared-b"]["local_class"], "LOW")

    def test_same_run_retrieved_at_after_frozen_clock_is_not_stale(self):
        payload = {
            "results": [{
                "package_ndc": NDC, "generic_name": "X", "availability": "Unavailable",
                "related_info": "", "update_date": "10/06/2026", "therapeutic_category": "X",
                "dosage_form": "Injection", "presentation": "X", "company_name": "X",
                "shortage_reason": "X", "status": "Current",
            }],
            "meta": {
                "state": "MATCH",
                "retrieved_at": "2026-10-13T14:27:00+00:00",
                "dataset_updated": "2026-10-06",
            },
        }
        view = assess_fda(payload, run_at=parse_run_at(EVAL_RUN))
        self.assertEqual(view["state"], "MATCH")
        self.assertTrue(view["external_risk"])

    def test_dataset_older_than_two_calendar_days_is_stale(self):
        payload = {
            "results": [{
                "package_ndc": NDC, "generic_name": "X", "availability": "Available",
                "related_info": "", "update_date": "09/01/2026", "therapeutic_category": "X",
                "dosage_form": "Injection", "presentation": "X", "company_name": "X",
                "shortage_reason": "X", "status": "Current",
            }],
            "meta": {"state": "MATCH", "retrieved_at": "2026-10-13T14:27:00+00:00",
                     "dataset_updated": "2026-10-01"},
        }
        view = assess_fda(payload, run_at=parse_run_at(EVAL_RUN))
        self.assertEqual(view["state"], "STALE")
        self.assertEqual(view["reason"], "DATASET_OLDER_THAN_TWO_DAYS")


if __name__ == "__main__":
    unittest.main()
