"""Rollback-only private authentication contract; no real password/token access."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
PROJECT="xrptinavijhwvydoqdni"
MIGRATION="20261016221032_reviewer_auth_sessions.sql"


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--before-deployment",action="store_true")
    args=parser.parse_args()
    parts=["BEGIN;"]
    if args.before_deployment:
        parts.append("DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='pharmacy_web') THEN RAISE EXCEPTION 'auth schema already deployed'; END IF; END $$;")
        parts.append((ROOT/"supabase/migrations"/MIGRATION).read_text(encoding="utf-8"))
    parts.append((ROOT/"supabase/tests/reviewer_auth_contract.sql").read_text(encoding="utf-8"))
    parts.extend(["ROLLBACK;","SELECT true AS auth_contract_rolled_back;"])
    cli=shutil.which("supabase") or str(Path.home()/"AppData/Local/Programs/SupabaseCLI/supabase.exe")
    with tempfile.TemporaryDirectory(prefix="pharmacy-auth-contract-") as work:
        sql=Path(work)/"contract.sql";sql.write_text("\n".join(parts),encoding="utf-8")
        result=subprocess.run([cli,"db","query","--linked","--project-ref",PROJECT,"--file",str(sql),"--output","json"],cwd=work,capture_output=True,text=True,timeout=45)
        if result.returncode:
            # This fixture/migration contains no secrets; keep provider diagnostics local.
            (ROOT/".env.auth-contract-diagnostic").write_text(result.stderr,encoding="utf-8")
            print("AUTH_SCHEMA_CONTRACT_FAILED: redacted console; inspect ignored local diagnostic.")
            return result.returncode
        print("PASS: private reviewer/session schema, identity binding, RLS/cookie scope, revocation, one-hour cap, password/provider-secret and inventory/public-access denial. All fixtures rolled back.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
