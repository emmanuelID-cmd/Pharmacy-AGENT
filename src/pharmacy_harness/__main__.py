"""CLI: python -m src.pharmacy_harness --offline"""
import argparse
import json
import sys

from .display import format_manager_report
from .loop import complete_from_env, copying_complete
from .offline import EVAL_RUN_AT, offline_fda_http_get
from .run import run_review
from .validate import STORE_ID
from ..pharmacy_tools.inventory import LEGACY_FIXTURE_PATH


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run one synthetic store-1618 inventory review through the pharmacy harness.",
    )
    parser.add_argument(
        "--run-at",
        help="Aware ISO timestamp used as the review clock (America/New_York). "
             f"Default: {EVAL_RUN_AT} so the dated fixture is fresh.",
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Use the current America/New_York clock. The dated fixture will be stale.",
    )
    parser.add_argument("--store-id", type=int, default=STORE_ID)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print harness-report-v1 JSON instead of the manager table.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Do not call live openFDA. Use the recorded Eval Card Case 1 shortage payload.",
    )
    parser.add_argument(
        "--model-copy",
        action="store_true",
        help="One model turn using a copier that returns expected_report (not an LLM).",
    )
    parser.add_argument(
        "--model",
        action="store_true",
        help="One model turn against PHARMACY_MODEL_URL. Invented numbers are rejected.",
    )
    parser.add_argument("--legacy-fixture", action="store_true",
                        help="Replay the original 20-row evaluation fixture.")
    args = parser.parse_args(argv)
    if args.now and args.run_at:
        parser.error("use either --now or --run-at, not both")
    if args.model and args.model_copy:
        parser.error("use either --model or --model-copy, not both")
    complete = None
    if args.model_copy:
        complete = copying_complete
    elif args.model:
        complete = complete_from_env()
        if complete is None:
            parser.error("set PHARMACY_MODEL_URL for --model, or use --model-copy")
    run_at = None if args.now else (args.run_at or EVAL_RUN_AT)
    report = run_review(
        run_at=run_at,
        store_id=args.store_id,
        inventory_path=LEGACY_FIXTURE_PATH if args.legacy_fixture else None,
        fda_http_get=offline_fda_http_get if args.offline else None,
        complete=complete,
    )
    if args.json:
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_manager_report(report))
    return 0 if report["source_state"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
