"""Map harness ItemResult to TrustedFact. Never deserialize tool JSON into a fact."""
from decimal import Decimal, ROUND_HALF_EVEN

try:
    from ..injection_prevention.safe_context import TrustedFact
except ImportError:
    from injection_prevention.safe_context import TrustedFact


def _as_float(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def to_trusted_fact(result):
    """Return a TrustedFact after harness verification, or None when identity/quantity cannot bind.

    TrustedFact forbids CRITICAL with a missing duration and requires float numbers. A verified
    zero-stock fact with no usage basis stays CRITICAL on the human report and maps to UNKNOWN
    in prevention context. Days are converted to float only after two-decimal quantization.
    """
    if result.item_id is None or result.package_ndc is None or result.dispensing_unit is None:
        return None
    if result.usable_quantity is None:
        return None
    verified = result.identity_ok and result.quantity_ok and result.usage_ok and result.freshness_ok
    if result.days_of_supply is not None and result.local_class in {"CRITICAL", "LOW", "ABOVE_THRESHOLD"}:
        days = float(result.days_of_supply.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))
        prevention_class = result.local_class
    else:
        days = None
        prevention_class = "UNKNOWN"
    return TrustedFact(
        result.item_id,
        result.package_ndc,
        _as_float(result.usable_quantity),
        result.dispensing_unit,
        days,
        prevention_class,
        result.evidence_reference,
        verified,
    )
