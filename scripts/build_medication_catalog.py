"""Reproducible, bounded public-source catalog export; prints JSON to stdout.

No private inventory, credentials, or database connection is used. The NDC
directory is a listing, not an FDA approval or clinical classification claim.
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FDA_URL = "https://api.fda.gov/drug/ndc.json?limit=500"
RX_URL = "https://rxnav.nlm.nih.gov/REST/rxcui.json"
CLASS_URL = "https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json"
NDC = re.compile(r"(?:[0-9]{4}-[0-9]{4}-[0-9]{2}|[0-9]{5}-[0-9]{3}-[0-9]{2}|[0-9]{5}-[0-9]{4}-[0-9])\Z")
MAX_PRODUCTS = 500
MAX_PACKAGES = 150
MAX_REQUESTS = 301  # one FDA listing, 150 exact RxNorm lookups, 150 class lookups
MAX_RESPONSE_BYTES = 4_000_000
TIMEOUT_SECONDS = 10


def get_json(url, *, max_bytes=MAX_RESPONSE_BYTES):
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("PUBLIC_RESPONSE_TOO_LARGE")
    return json.loads(raw)


def clean(value, max_length=160):
    if not isinstance(value, str) or len(value) > max_length:
        return ""
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return ""
    return value


def collect(get=get_json):
    listing = get(FDA_URL)
    records = listing.get("results")
    if not isinstance(records, list) or len(records) > MAX_PRODUCTS:
        raise ValueError("INVALID_FDA_LISTING")
    chosen = []
    seen = set()
    seen_products = set()
    for record in records:
        if record.get("product_type") != "HUMAN PRESCRIPTION DRUG":
            continue
        product_ndc = clean(record.get("product_ndc"), 12)
        label = clean(record.get("generic_name") or record.get("brand_name"), 120)
        if not product_ndc or not label or product_ndc in seen_products:
            continue
        for package in record.get("packaging", []):
            package_ndc = package.get("package_ndc")
            if not isinstance(package_ndc, str) or not NDC.fullmatch(package_ndc) or package_ndc in seen:
                continue
            seen.add(package_ndc)
            chosen.append({
                "package_ndc": package_ndc,
                "product_ndc": product_ndc,
                "generic_name": label,
                "brand_name": clean(record.get("brand_name"), 120),
                "dosage_form": clean(record.get("dosage_form"), 80),
                "product_type": "HUMAN PRESCRIPTION DRUG",
                "package_description": clean(package.get("description"), 300),
                "marketing_start_date": clean(package.get("marketing_start_date"), 8),
            })
            # One package per distinct product: 150 inventory rows should represent
            # 150 products, while each still has an exact package NDC for linkage.
            seen_products.add(product_ndc)
            break
        if len(chosen) == MAX_PACKAGES:
            break
    if len(chosen) != MAX_PACKAGES:
        raise ValueError("INSUFFICIENT_FDA_PACKAGES")

    class_cache = {}
    requests = 1
    for row in chosen:
        query = urllib.parse.urlencode({"idtype": "NDC", "id": row["package_ndc"]})
        try:
            data = get(f"{RX_URL}?{query}", max_bytes=20000)
            ids = data.get("idGroup", {}).get("rxnormId", [])
            if not isinstance(ids, list) or any(not isinstance(v, str) or not v.isdecimal() for v in ids):
                raise ValueError("INVALID_RXNORM_MAPPING")
            ids = sorted(set(ids))
            state = "MISSING" if not ids else "SINGLE" if len(ids) == 1 else "MULTIPLE"
        except (OSError, ValueError, KeyError, TypeError):
            ids, state = [], "UNAVAILABLE"
        requests += 1
        row["rxnorm_rxcuis"] = ids
        row["rxnorm_mapping_state"] = state
        row["atc_classes"] = []
        row["atc_class_state"] = "NOT_MAPPED"
        if state != "SINGLE":
            continue
        rxcui = ids[0]
        if rxcui not in class_cache:
            query = urllib.parse.urlencode({"rxcui": rxcui, "relaSource": "ATC"})
            try:
                data = get(f"{CLASS_URL}?{query}", max_bytes=100000)
                candidates = data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
                if not isinstance(candidates, list) or len(candidates) > 100:
                    raise ValueError("INVALID_RXCLASS_RESPONSE")
                classes = sorted({
                    (clean(x["rxclassMinConceptItem"].get("classId"), 30),
                     clean(x["rxclassMinConceptItem"].get("className"), 160))
                    for x in candidates if isinstance(x, dict) and isinstance(x.get("rxclassMinConceptItem"), dict)
                })
                classes = [{"class_id": code, "class_name": name} for code, name in classes if code and name]
                class_cache[rxcui] = ("MAPPED" if classes else "MISSING", classes)
            except (OSError, ValueError, KeyError, TypeError):
                class_cache[rxcui] = ("UNAVAILABLE", [])
            requests += 1
        row["atc_class_state"], row["atc_classes"] = class_cache[rxcui]
    if requests > MAX_REQUESTS:
        raise ValueError("REQUEST_BUDGET_EXCEEDED")
    return {
        "source": "openFDA NDC directory",
        "source_url": FDA_URL,
        "dataset_updated": clean(listing.get("meta", {}).get("last_updated"), 10),
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "classification_source": "NLM RxNorm exact NDC and RxClass ATC",
        "classification_urls": [RX_URL, CLASS_URL],
        "fda_approval_claim": False,
        "request_count": requests,
        "packages": chosen,
    }


def fixture(catalog):
    rows = []
    for index, entry in enumerate(catalog["packages"], 1):
        form = entry["dosage_form"].upper()
        unit = "tablet" if "TABLET" in form else "capsule" if "CAPSULE" in form else "mL" if any(
            part in form for part in ("SOLUTION", "SUSPENSION", "LIQUID")) else "unit"
        rows.append({
            "item_id": f"catalog-{index:03d}",
            "package_ndc": entry["package_ndc"],
            "product_label": entry["generic_name"],
            "dosage_form": entry["dosage_form"] or "Unknown",
            "dispensing_unit": unit,
            "usable_quantity": (index * 17) % 201,
            "daily_usage": {"window_end": "2026-10-06",
                            "units": [1 + ((index + day) % 8) for day in range(14)]},
        })
    return {
        "store_id": 1618,
        "synthetic": True,
        "snapshot_reference": "synthetic-snapshot-catalog-2026-10-07",
        "snapshot_timestamp": "2026-10-07T09:00:00-04:00",
        "policy_version": "SYNTHETIC-v0",
        "catalog_source": "openFDA and NLM identities only; stock and usage synthetic",
        "items": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("collect", "fixture"))
    parser.add_argument("--catalog", type=Path)
    args = parser.parse_args()
    if args.mode == "collect":
        result = collect()
    else:
        if args.catalog is None:
            parser.error("--catalog is required for fixture")
        result = fixture(json.loads(args.catalog.read_text(encoding="utf-8")))
    json.dump(result, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
