"""Human-only catalog display from fixed local files; never model evidence."""
from datetime import date, timedelta
import json

from ..injection_prevention.boundary_contracts import InventoryLimits, strict_json_loads
from ..pharmacy_agent.config import ROOT
from ..pharmacy_tools.inventory import InventoryUnavailable, read_store_inventory

CATALOG_PATH = ROOT / "data/catalog/fda_ndc_150.json"
COLUMNS = (
    ("item_id", "Item ID"), ("package_ndc", "Package NDC"),
    ("product_ndc", "Product NDC"), ("generic_name", "Generic name"),
    ("brand_name", "Brand name"), ("dosage_form", "Catalog dosage form"),
    ("product_label", "Inventory label"), ("inventory_dosage_form", "Inventory dosage form"),
    ("product_type", "Product type"), ("package_description", "Package description"),
    ("marketing_start_date", "Marketing start date (YYYYMMDD)"),
    ("rxnorm_rxcuis", "RxNorm RXCUIs"), ("rxnorm_mapping_state", "RxNorm mapping state"),
    ("atc_classes", "ATC classes"), ("atc_class_state", "ATC mapping state"),
    ("dispensing_unit", "Dispensing unit"), ("usable_quantity", "Usable quantity"),
    ("window_end", "Usage window end"),
)


def display(value):
    if value is None:
        return "Not provided"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def home_catalog():
    """Join exact package identifiers for escaped display, without API calls."""
    try:
        catalog = strict_json_loads(CATALOG_PATH.read_bytes(), InventoryLimits())
        inventory = read_store_inventory(1618)
        packages, items = catalog["packages"], inventory["items"]
        if len(packages) != 150 or len(items) != 150:
            raise ValueError
        by_ndc = {row["package_ndc"]: row for row in packages}
        item_ndcs = {row["package_ndc"] for row in items}
        if len(by_ndc) != 150 or len(item_ndcs) != 150 or set(by_ndc) != item_ndcs:
            raise ValueError
        ends = {row["daily_usage"]["window_end"] for row in items}
        if len(ends) != 1:
            raise ValueError
        end = date.fromisoformat(ends.pop())
        usage_columns = [str(end - timedelta(days=13-index)) for index in range(14)]
        rows = []
        for item in items:
            units = item["daily_usage"]["units"]
            if type(units) is not list or len(units) != 14:
                raise ValueError
            joined = {**by_ndc[item["package_ndc"]], **item,
                      "dosage_form": by_ndc[item["package_ndc"]].get("dosage_form"),
                      "inventory_dosage_form": item.get("dosage_form"),
                      "window_end": item["daily_usage"]["window_end"]}
            rows.append([display(joined.get(key)) for key, _ in COLUMNS] + [display(v) for v in units])
        metadata = [("Store", inventory["store_id"]), ("Synthetic stock and usage", inventory["synthetic"]),
                    ("Snapshot reference", inventory["snapshot_reference"]),
                    ("Snapshot timestamp", inventory["snapshot_timestamp"]),
                    ("Policy version", inventory["policy_version"]), ("Inventory source", inventory["catalog_source"])]
        metadata += [(key.replace("_", " ").capitalize(), value)
                     for key, value in catalog.items() if key != "packages"]
        return {"columns": [label for _, label in COLUMNS] + usage_columns, "rows": rows,
                "metadata": [(label, display(value)) for label, value in metadata]}
    except (OSError, ValueError, TypeError, KeyError, AttributeError, InventoryUnavailable):
        return None
