"""Rollback-only contract for the private synthetic two-phone demo schema."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "xrptinavijhwvydoqdni"
MIGRATION = "20261016191734_demo_phone_pairing.sql"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-deployment", action="store_true", help="Test only the new demo DDL when its schema is absent; always roll back.")
    args = parser.parse_args()
    parts = ["BEGIN;"]
    if args.before_deployment:
        parts.append("DO $$ BEGIN IF to_regnamespace('pharmacy_demo') IS NOT NULL THEN RAISE EXCEPTION 'demo schema already exists; refuse pre-deployment DDL'; END IF; END $$;")
        parts.append((ROOT / "supabase/migrations" / MIGRATION).read_text(encoding="utf-8"))
    parts.append((ROOT / "supabase/tests/demo_pairing_contract.sql").read_text(encoding="utf-8"))
    parts.extend(["ROLLBACK;", "SELECT true AS demo_contract_rolled_back;"])
    with tempfile.TemporaryDirectory(prefix="pharmacy-demo-contract-") as work:
        sql = Path(work) / "contract.sql"
        sql.write_text("\n".join(parts), encoding="utf-8")
        result = subprocess.run(["supabase", "db", "query", "--linked", "--project-ref", PROJECT,
                                 "--file", str(sql), "--output", "json"], cwd=work,
                                capture_output=True, text=True, timeout=45)
        if result.returncode:
            # Test SQL contains no secrets, but avoid native request diagnostics in ordinary output.
            print("DEMO_SCHEMA_CONTRACT_FAILED: inspect the authorized local query diagnostics.")
            return result.returncode
        print("PASS: owner/recipient binding, consumed-code replay, RLS, expiry cleanup, JSON constraints, and inventory/public-access denial; all test effects rolled back.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
