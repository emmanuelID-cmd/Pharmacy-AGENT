"""POLICY.md days-of-supply arithmetic. The model never computes these values."""
from dataclasses import dataclass
from .validate import USAGE_DAYS

CRITICAL_DAYS = 2
LOW_DAYS = 5


@dataclass(frozen=True)
class ItemResult:
    item_id: str | None
    package_ndc: str | None
    dispensing_unit: str | None
    usable_quantity: float | None
    usage_total: float | None
    average_daily_usage: float | None
    days_of_supply: float | None
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
    return f"{round(days, 2):.2f}"


def classify_days(days):
    """Classify unrounded days of supply against SYNTHETIC-v0 thresholds."""
    if days <= CRITICAL_DAYS:
        return "CRITICAL", "REVIEW"
    if days <= LOW_DAYS:
        return "LOW", "REVIEW"
    return "ABOVE_THRESHOLD", "MAINTAIN"


def calculate_item(evidence, *, evidence_reference):
    """Return a harness result. Withhold any number that required evidence cannot support."""
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
                # POLICY: critical stock fact; duration unknown; no replenishment inference.
                local_class = "CRITICAL"
            else:
                local_class = "UNKNOWN"
            local_action = "MANUAL_REVIEW"
        else:
            days = evidence.usable_quantity / average
            display = _display(days)
            local_class, local_action = classify_days(days)
            if zero_stock_fact:
                local_class, local_action = "CRITICAL", "REVIEW"
                days = 0.0
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
