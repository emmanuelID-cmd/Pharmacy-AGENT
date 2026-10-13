"""POLICY.md days-of-supply arithmetic. The model never computes these values."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from .validate import USAGE_DAYS

CRITICAL_DAYS = Decimal("2")
LOW_DAYS = Decimal("5")
DISPLAY_CENTS = Decimal("0.01")


@dataclass(frozen=True)
class ItemResult:
    item_id: str | None
    package_ndc: str | None
    dispensing_unit: str | None
    usable_quantity: Decimal | None
    usage_total: Decimal | None
    average_daily_usage: Decimal | None
    days_of_supply: Decimal | None
    days_of_supply_display: str | None
    local_class: str
    local_action: str
    zero_stock_fact: bool
    reason_codes: tuple
    evidence_reference: str
    identity_ok: bool
    quantity_ok: bool
    usage_ok: bool
    freshness_ok: bool

    @property
    def ndc_accepted(self):
        return self.package_ndc is not None


def _display(days):
    quantized = days.quantize(DISPLAY_CENTS, rounding=ROUND_HALF_EVEN)
    return f"{quantized:.2f}"


def classify_days(days):
    """Classify the exact (unrounded) days-of-supply value against SYNTHETIC-v0 thresholds."""
    if not isinstance(days, Decimal):
        days = Decimal(str(days))
    if days <= CRITICAL_DAYS:
        return "CRITICAL", "REVIEW"
    if days <= LOW_DAYS:
        return "LOW", "REVIEW"
    return "ABOVE_THRESHOLD", "MAINTAIN"


def calculate_item(evidence, *, evidence_reference):
    """Return a harness result. Days of supply = usable * 14 / total (exact Decimal)."""
    reasons = list(evidence.reason_codes)
    average = None
    days = None
    display = None
    local_class = "UNKNOWN"
    local_action = "MANUAL_REVIEW"
    zero_stock_fact = evidence.quantity_ok and evidence.usable_quantity == 0

    required = (evidence.identity_ok and evidence.quantity_ok and evidence.usage_ok
                and evidence.freshness_ok)
    if required:
        average = evidence.usage_total / USAGE_DAYS
        if average == 0:
            display = "unavailable"
            reasons.append("NO_CONSUMPTION_BASIS")
            if zero_stock_fact:
                local_class = "CRITICAL"
            else:
                local_class = "UNKNOWN"
            local_action = "MANUAL_REVIEW"
        else:
            days = evidence.usable_quantity * USAGE_DAYS / evidence.usage_total
            display = _display(days)
            local_class, local_action = classify_days(days)
            if zero_stock_fact:
                local_class, local_action = "CRITICAL", "REVIEW"
                days = Decimal("0")
                display = "0.00"
    else:
        if zero_stock_fact:
            local_class = "CRITICAL"
        display = "unavailable"

    unique = []
    for code in reasons:
        if code not in unique:
            unique.append(code)
    return ItemResult(
        evidence.item_id, evidence.package_ndc, evidence.dispensing_unit, evidence.usable_quantity,
        evidence.usage_total, average, days, display, local_class, local_action, zero_stock_fact,
        tuple(unique), evidence_reference, evidence.identity_ok, evidence.quantity_ok, evidence.usage_ok,
        evidence.freshness_ok,
    )
