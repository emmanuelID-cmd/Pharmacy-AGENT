"""CLI: python -m src.pharmacy_harness --run-at 2026-10-07T10:00:00-04:00"""
import argparse
import json
import sys

from .run import run_review
from .validate import STORE_ID


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run one synthetic store-1618 inventory review through the pharmacy harness.",
    )
    parser.add_argument(
        "--run-at",
        help="Aware ISO timestamp used as the review clock (America/New_York). "
             "The dated fixture is fresh at 2026-10-07T10:00:00-04:00. Default: now.",
    )
    parser.add_argument("--store-id", type=int, default=STORE_ID)
    args = parser.parse_args(argv)
    report = run_review(run_at=args.run_at, store_id=args.store_id)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["source_state"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
