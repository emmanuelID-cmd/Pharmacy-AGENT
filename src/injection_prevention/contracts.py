"""Immutable contracts. Rejected results never carry the input label."""
from dataclasses import dataclass
from enum import StrEnum
import re


class Decision(StrEnum):
    ACCEPT = "ACCEPT"
    FLAG = "FLAG"
    REJECT = "REJECT"


@dataclass(frozen=True)
class Finding:
    reason_code: str
    correction: str
    position: int | None = None  # zero-based Unicode code-point index
    code_point: str | None = None
    pattern_id: str | None = None


@dataclass(frozen=True)
class DetectionResult:
    item_reference: str
    field_reference: str
    source: str
    decision: Decision
    required_evidence_affected: bool
    findings: tuple[Finding, ...]
    normalized_label: str | None = None

    def __post_init__(self):
        # References are opaque application-generated IDs, not product/user text.
        for reference in (self.item_reference, self.field_reference, self.source):
            if not isinstance(reference, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", reference):
                raise ValueError("Use an opaque ASCII reference of 1-64 characters.")
        if type(self.required_evidence_affected) is not bool:
            raise ValueError("required_evidence_affected must be a boolean.")
        if not isinstance(self.decision, Decision):
            raise ValueError("Unknown detector decision.")
        if self.decision != Decision.ACCEPT and self.normalized_label is not None:
            raise ValueError("Unaccepted results must not contain label text.")
        if self.decision == Decision.ACCEPT and (self.findings or not self.normalized_label):
            raise ValueError("Accepted results require a label and no findings.")
        if self.decision != Decision.ACCEPT and not self.findings:
            raise ValueError("Unaccepted results require safe findings.")

    def safe_summary(self) -> dict:
        """For logs/exception context. Contains no original or normalized label."""
        return {
            "item_reference": self.item_reference,
            "field_reference": self.field_reference,
            "source": self.source,
            "decision": self.decision.value,
            "required_evidence_affected": self.required_evidence_affected,
            "reason_codes": [finding.reason_code for finding in self.findings],
            "findings": [
                {"reason_code": f.reason_code, "correction": f.correction,
                 "position": f.position, "code_point": f.code_point,
                 "pattern_id": f.pattern_id}
                for f in self.findings
            ],
        }


@dataclass(frozen=True)
class LabelPolicy:
    min_length: int = 1
    max_length: int = 120
    allowed_punctuation: str = ".,-/()+%"
    max_findings: int = 16

    def __post_init__(self):
        if any(type(v) is not int for v in (self.min_length, self.max_length, self.max_findings)):
            raise ValueError("Limits must be integers.")
        if not 1 <= self.min_length <= self.max_length <= 4096:
            raise ValueError("Label limits must satisfy 1 <= min <= max <= 4096.")
        if not 1 <= self.max_findings <= 64:
            raise ValueError("Finding limit must be 1-64.")
        if not isinstance(self.allowed_punctuation, str):
            raise ValueError("Punctuation must be text.")
        if any(ch not in ".,-/()+%" for ch in self.allowed_punctuation):
            raise ValueError("Only the approved single-line punctuation subset is allowed.")
