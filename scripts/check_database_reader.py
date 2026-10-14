"""Live check using only the ignored backend credential file; prints safe counts."""
from pathlib import Path
import os
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_backend_environment():
    # Exact, generated file format; no eval or shell expansion. Never opens .env.
    path = ROOT / ".env.database"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise SystemExit("BACKEND_CREDENTIAL_FILE_UNAVAILABLE")
    for line in lines:
        if line.startswith("PHARMACY_DATABASE_URL="):
            os.environ["PHARMACY_DATABASE_URL"] = line.split("=", 1)[1]
            return
    raise SystemExit("DATABASE_NOT_CONFIGURED")


def main():
    load_backend_environment()
    from src.pharmacy_tools import read_store_inventory_database, InventoryUnavailable
    from src.injection_prevention import inspect_payload, Source
    try:
        result = read_store_inventory_database(1618)
    except InventoryUnavailable as error:
        raise SystemExit(error.reason_code) from None
    assessment = inspect_payload(result,source=Source.INVENTORY)
    print("Inventory rows:", len(result["items"]))
    print("Snapshot:", result["snapshot_timestamp"])
    print("Source contract valid:", assessment.source_contract_valid)
    print("Required evidence remains unverified; no classifications or orders made.")
    return 0 if assessment.source_contract_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
