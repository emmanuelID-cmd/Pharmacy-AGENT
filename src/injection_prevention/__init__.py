"""Field-aware injection detection; not a guarantee of prompt safety."""
from .contracts import Decision, DetectionResult, Finding, LabelPolicy
from .label_detector import detect_label

__all__ = ["Decision", "DetectionResult", "Finding", "LabelPolicy", "detect_label"]
