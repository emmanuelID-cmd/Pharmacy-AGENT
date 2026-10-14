"""Transaction-only synthetic schema checks; never resets the remote database."""
import argparse
from pathlib import Path
import subprocess
import tempfile

PROJECT = "xrptinavijhwvydoqdni"
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--empty-baseline", action="store_true",
                        help="Include DDL only when target has no pharmacy schema; otherwise test existing deployment.")
    args = parser.parse_args()
    parts = ["begin;"]
    if args.empty_baseline:
        parts.extend(path.read_text(encoding="utf-8")
                     for path in sorted((ROOT / "supabase/migrations").glob("*.sql")))
    parts.append("grant pharmacy_inventory_reader to postgres with set true;")
    seed = (ROOT / "supabase/seed.sql").read_text(encoding="utf-8")
    parts.extend([seed, seed,
                  (ROOT / "supabase/tests/inventory_contract.sql").read_text(encoding="utf-8"),
                  "rollback;"])
    with tempfile.TemporaryDirectory(prefix="pharmacy-schema-check-") as workdir:
        sql = Path(workdir) / "verify.sql"
        sql.write_text("\n".join(parts), encoding="utf-8")
        # Neutral cwd avoids the repository .env parser issue; uses CLI login.
        result = subprocess.run(["supabase", "db", "query", "--linked",
                                 "--project-ref", PROJECT, "--file", str(sql),
                                 "--output", "json"], cwd=workdir, check=False)
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
