"""Local deterministic fixture evaluation. No model/API/database calls."""
import argparse
import json
from pathlib import Path
from .contracts import Decision
from .label_detector import detect_label
from .context_gate import gate_label
from .patterns import PATTERN_VERSION
from .reporting import explain_detection

DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "labels.json"


def evaluate_cases(cases: list) -> dict:
    if not isinstance(cases, list) or not 1 <= len(cases) <= 1000:
        raise ValueError("Use 1-1000 trusted synthetic fixture cases.")
    results = []
    ids = set()
    for case in cases:
        if not isinstance(case, dict) or "label" not in case:
            raise ValueError("Invalid synthetic case contract.")
        expected = case.get("expected")
        if expected not in {decision.value for decision in Decision}:
            raise ValueError("Each fixture needs an expected decision.")
        result = detect_label(case["label"], item_reference=case.get("id"),
                              required_evidence_affected=case.get("required_evidence_affected", False))
        if result.item_reference in ids:
            raise ValueError("Fixture IDs must be unique.")
        ids.add(result.item_reference)
        evidence_validated = case.get("required_evidence_validated", True)
        gate = gate_label(result, required_evidence_validated=evidence_validated)
        decision_match = result.decision.value == expected
        reason_match = "reason" not in case or case["reason"] in {f.reason_code for f in result.findings}
        pattern_match = "pattern" not in case or case["pattern"] in {f.pattern_id for f in result.findings}
        expected_calculation = case.get("calculations_permitted")
        calculation_match = "calculations_permitted" not in case or (
            type(expected_calculation) is bool and gate.calculations_permitted == expected_calculation)
        results.append({"case_id": result.item_reference, "expected": expected,
                        "actual": result.decision.value,
                        "passed": decision_match and reason_match and pattern_match and calculation_match,
                        "calculations_permitted": gate.calculations_permitted,
                        "raw_rejected_label_in_context": (result.decision != Decision.ACCEPT
                                                          and "display_label" in gate.model_context),
                        "audit_event": gate.audit_event, "explanation": explain_detection(result)})
    benign = [row for row in results if row["expected"] == Decision.ACCEPT]
    exceptions = [row for row in results if row["expected"] != Decision.ACCEPT]
    return {"pattern_version": PATTERN_VERSION, "synthetic_only": True,
            "cases": len(results), "passed": sum(row["passed"] for row in results),
            "benign_cases": len(benign),
            "benign_false_flags": sum(row["actual"] != Decision.ACCEPT for row in benign),
            "exception_cases": len(exceptions),
            "missed_fixture_exceptions": sum(row["actual"] == Decision.ACCEPT for row in exceptions),
            "results": results,
            "limitations": ["Fixture agreement is not a general attack detection rate.",
                            "Unrecognized paraphrases and factual lies may pass.",
                            "No model, FDA API, database or production harness exercised.",
                            "This component has no operational write or tool-dispatch capability."]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURE,
                        help="Trusted local synthetic fixture file, not a user upload.")
    args = parser.parse_args(argv)
    try:
        if args.fixtures.stat().st_size > 1024 * 1024:
            raise ValueError("Fixture file too large.")
        cases = json.loads(args.fixtures.read_text(encoding="utf-8"))
        report = evaluate_cases(cases)
    except (OSError, UnicodeError, ValueError, TypeError):
        print(json.dumps({"state": "INVALID_FIXTURE", "action": "MANUAL_REVIEW"}))
        return 2
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["passed"] == report["cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
