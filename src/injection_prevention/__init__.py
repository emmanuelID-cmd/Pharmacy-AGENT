"""Field-aware injection detection; not a guarantee of prompt safety."""
from .contracts import Decision, DetectionResult, Finding, LabelPolicy
from .label_detector import detect_label

__all__ = ["Decision", "DetectionResult", "Finding", "LabelPolicy", "detect_label"]

from .boundary_contracts import ContractError, Limits, Source, strict_json_loads
from .safe_context import TrustedFact, inspect_payload, assemble_context
from .action_guard import RunBudget, authorize_tool_call, execute_guarded
from .output_guard import expected_report, validate_report

__all__ += ["ContractError", "Limits", "Source", "strict_json_loads", "TrustedFact",
            "inspect_payload", "assemble_context", "RunBudget", "authorize_tool_call",
            "execute_guarded", "expected_report", "validate_report"]
