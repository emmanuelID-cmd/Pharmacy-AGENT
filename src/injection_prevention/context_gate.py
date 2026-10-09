"""Context gate for detector results, not an inventory validator or calculator."""
from dataclasses import dataclass
from .contracts import Decision, DetectionResult


@dataclass(frozen=True)
class GateResult:
    model_context: dict
    audit_event: dict
    calculations_permitted: bool
    recommendation_permitted: bool


def gate_label(result: DetectionResult, *, required_evidence_validated: bool) -> GateResult:
    """The trusted harness supplies the validation boolean, never the tool/model.

    No numeric payload is accepted here. The team harness separately validates
    item identity, units, quantities, usage and policy before using a true value.
    """
    if not isinstance(result, DetectionResult):
        raise ValueError("A detector result is required.")
    if type(required_evidence_validated) is not bool:
        raise ValueError("The trusted evidence flag must be a boolean.")
    accepted = result.decision == Decision.ACCEPT
    permitted = required_evidence_validated and (accepted or not result.required_evidence_affected)
    context = {"item_reference": result.item_reference, "source": result.source,
               "calculations_permitted": permitted,
               "recommendation_permitted": permitted,
               "action": "CONTINUE_VALIDATED_REVIEW" if permitted else "MANUAL_REVIEW"}
    context["external_text_included"] = False
    if not accepted:
        context["label_exception"] = result.safe_summary()
    if not required_evidence_validated:
        context["evidence_exception"] = "REQUIRED_EVIDENCE_UNVERIFIED"
    event = result.safe_summary()
    event["calculations_permitted"] = permitted
    event["recommendation_permitted"] = permitted
    return GateResult(context, event, permitted, permitted)
