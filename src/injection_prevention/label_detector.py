"""Single-line medication display-label validation, before model context."""
import unicodedata
from .contracts import Decision, DetectionResult, Finding, LabelPolicy
from .patterns import matched_patterns

_HIDDEN_CATEGORIES = {"Cf", "Cs"}
# Invisible marks not categorized as format/control by Unicode.
_INVISIBLE = {0x034F, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x180B, 0x180C,
              0x180D, 0x3164, 0xFFA0}


def _hidden(ch: str) -> bool:
    cp = ord(ch)
    return (unicodedata.category(ch) in _HIDDEN_CATEGORIES or cp in _INVISIBLE
            or 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF)


def detect_label(label: object, *, item_reference: str, field_reference: str = "product_label",
                 source: str = "synthetic_inventory", required_evidence_affected: bool = False,
                 policy: LabelPolicy | None = None) -> DetectionResult:
    """Format acceptance is not a semantic safety guarantee. Never coerces inputs."""
    policy = policy or LabelPolicy()
    def result(decision, findings=(), normalized=None):
        return DetectionResult(item_reference, field_reference, source, decision,
                               required_evidence_affected, tuple(findings), normalized)
    if not isinstance(label, str):
        return result(Decision.REJECT, [Finding("INVALID_LABEL_TYPE", "Supply a text label.")])
    if not policy.min_length <= len(label) <= policy.max_length or not label.strip():
        return result(Decision.REJECT, [Finding("INVALID_LABEL_LENGTH", "Supply a nonempty label within the configured length limit.")])
    findings = []
    mark_attached = False
    for position, ch in enumerate(label):
        category = unicodedata.category(ch)
        reason = None
        if _hidden(ch):
            reason = "UNEXPECTED_HIDDEN_CHARACTER"
        elif category.startswith("C") or ch in "\r\n\t":
            reason = "UNEXPECTED_CONTROL_CHARACTER"
        elif category.startswith("M"):
            if not mark_attached:
                reason = "UNATTACHED_COMBINING_MARK"
        elif category.startswith("L"):
            mark_attached = True
        elif category.startswith("N") or ch == " " or ch in policy.allowed_punctuation:
            mark_attached = False
        else:
            reason = "UNEXPECTED_LABEL_CHARACTER"
            mark_attached = False
        if reason:
            findings.append(Finding(reason, "Correct the label in the authorized source and retry.",
                                    position, f"U+{ord(ch):04X}"))
            if len(findings) >= policy.max_findings:
                break
    format_failed = bool(findings)
    for pattern in matched_patterns(label):
        if len(findings) >= policy.max_findings:
            break
        findings.append(Finding("SUSPICIOUS_TEXT_PATTERN", pattern.rationale,
                                pattern_id=pattern.pattern_id))
    if findings:
        return result(Decision.REJECT if format_failed else Decision.FLAG, findings)
    normalized = unicodedata.normalize("NFC", label)
    return result(Decision.ACCEPT, normalized=normalized)
