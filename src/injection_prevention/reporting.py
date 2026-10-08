"""Evidence-based rule explanations. No inferred intent or raw matched text."""
from .contracts import Decision, DetectionResult


def explain_detection(result: DetectionResult) -> str:
    if result.decision == Decision.ACCEPT:
        return "No configured label-format or pattern signal found; semantic safety is not established."
    reasons = sorted({finding.reason_code for finding in result.findings})
    patterns = sorted({finding.pattern_id for finding in result.findings if finding.pattern_id})
    details = "; ".join(reasons)
    if patterns:
        details += "; pattern rules: " + ", ".join(patterns)
    impact = ("Required evidence is affected: manual review before calculation."
              if result.required_evidence_affected else
              "Exclude this optional label; independently validated evidence may still be used.")
    return f"{result.decision.value}: {details}. {impact}"
