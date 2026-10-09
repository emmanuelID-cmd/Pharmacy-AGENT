"""Generic external-text signals. Labels retain their stricter field contract."""
import unicodedata
from .contracts import Decision, DetectionResult, Finding
from .patterns import matched_patterns
from .label_detector import _hidden


def inspect_text(text: object, *, item_reference: str = "record", source: str = "external") -> DetectionResult:
    def result(decision, findings=(), normalized=None):
        return DetectionResult(item_reference, "external_text", source, decision, False, tuple(findings), normalized)
    if type(text) is not str:
        return result(Decision.REJECT, [Finding("INVALID_LABEL_TYPE", "Supply supported text only.")])
    if not text.strip() or len(text) > 1000:
        return result(Decision.REJECT, [Finding("INVALID_LABEL_LENGTH", "Use a bounded nonempty field.")])
    findings=[]
    for index,ch in enumerate(text):
        cat=unicodedata.category(ch)
        if _hidden(ch) or (cat.startswith("C") and ch not in "\n\r\t"):
            findings.append(Finding("UNEXPECTED_HIDDEN_CHARACTER", "Review the original source field.", index, f"U+{ord(ch):04X}"))
            if len(findings)>=16:
                break
    invalid=bool(findings)
    for pattern in matched_patterns(text):
        if len(findings)>=16:
            break
        findings.append(Finding("SUSPICIOUS_TEXT_PATTERN", pattern.rationale, pattern_id=pattern.pattern_id))
    if findings:
        return result(Decision.REJECT if invalid else Decision.FLAG, findings)
    return result(Decision.ACCEPT, normalized=unicodedata.normalize("NFC",text))
