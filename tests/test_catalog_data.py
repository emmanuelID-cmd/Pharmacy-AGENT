import json
import unittest

from src.injection_prevention.boundary_contracts import Source
from src.injection_prevention.safe_context import TrustedFact, assemble_context, inspect_payload
from src.pharmacy_tools.inventory import FIXTURE_PATH, read_store_inventory


class PublicCatalogFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((FIXTURE_PATH.parents[1] / "catalog" / "fda_ndc_150.json").read_text(encoding="utf-8"))
        cls.stock = read_store_inventory(1618)

    def test_catalog_has_150_distinct_human_prescription_products_and_packages(self):
        packages = self.catalog["packages"]
        self.assertEqual(len(packages), 150)
        self.assertEqual(len({row["product_ndc"] for row in packages}), 150)
        self.assertEqual(len({row["package_ndc"] for row in packages}), 150)
        self.assertTrue(all(row["product_type"] == "HUMAN PRESCRIPTION DRUG" for row in packages))
        self.assertIs(self.catalog["fda_approval_claim"], False)

    def test_nlm_gaps_and_classifications_are_explicit(self):
        allowed_rx = {"SINGLE", "MULTIPLE", "MISSING", "UNAVAILABLE"}
        allowed_atc = {"MAPPED", "MISSING", "NOT_MAPPED", "UNAVAILABLE"}
        for row in self.catalog["packages"]:
            self.assertIn(row["rxnorm_mapping_state"], allowed_rx)
            self.assertIn(row["atc_class_state"], allowed_atc)
            if row["rxnorm_mapping_state"] == "SINGLE":
                self.assertEqual(len(row["rxnorm_rxcuis"]), 1)
                self.assertIn(row["atc_class_state"], {"MAPPED", "MISSING", "UNAVAILABLE"})
            else:
                self.assertEqual(row["atc_class_state"], "NOT_MAPPED")
        self.assertTrue(all(entry["class_id"] and entry["class_name"]
                            for row in self.catalog["packages"] for entry in row["atc_classes"]))

    def test_every_public_package_identity_is_linked_to_one_synthetic_stock_row(self):
        packages = self.catalog["packages"]
        items = self.stock["items"]
        self.assertIs(self.stock["synthetic"], True)
        self.assertIn("stock and usage synthetic", self.stock["catalog_source"])
        self.assertEqual(len(items), 150)
        self.assertEqual([row["package_ndc"] for row in items], [row["package_ndc"] for row in packages])
        self.assertEqual([row["product_label"] for row in items], [row["generic_name"] for row in packages])
        self.assertTrue(all("usable_quantity" in row and len(row["daily_usage"]["units"]) == 14 for row in items))

    def test_intake_and_context_preserve_all_rows_without_forwarding_raw_catalog_text(self):
        assessment = inspect_payload(self.stock, source=Source.INVENTORY)
        self.assertTrue(assessment.source_contract_valid)
        facts = tuple(TrustedFact(row["item_id"], row["package_ndc"], float(row["usable_quantity"]),
                                  row["dispensing_unit"], None, "UNKNOWN",
                                  self.stock["snapshot_reference"], True)
                      for row in self.stock["items"])
        context = assemble_context(self.stock, source=Source.INVENTORY, facts=facts)
        self.assertEqual(len(context["items"]), 150)
        self.assertIs(context["external_text_included"], False)
        encoded = json.dumps(context)
        self.assertNotIn('"product_label"', encoded)
        self.assertNotIn('"catalog_source"', encoded)


if __name__ == "__main__":
    unittest.main()
