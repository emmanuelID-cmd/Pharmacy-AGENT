"""Synthetic demo quantity contract; independent of the existing review policy.

Not operational pharmacy policy. Callers must first use the existing independent
snapshot/item checks; descriptions and model output never supply these inputs.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING

from .calculate import ItemResult
from .validate import USAGE_DAYS

DEMO_POLICY_VERSION = "SYNTHETIC-DEMO-REPLENISHMENT-v1"
MAX_ORDER_UNITS = 1_000_000


@dataclass(frozen=True)
class DemoItemPolicy:
    item_id: str
    dispensing_unit: str
    target_days: Decimal
    confirmed_incoming: Decimal
    order_multiple: Decimal
    minimum_units: Decimal
    version: str = DEMO_POLICY_VERSION


def suggest_quantity(result: ItemResult, policy: DemoItemPolicy | None):
    """Return a supported demo suggestion, or withhold it with a fixed reason.

    The one-unit multiple is explicitly a synthetic dispensing-unit rule, not
    an inferred manufacturer package conversion. Zero incoming is supplied by
    the demo policy, never assumed for an unknown live order book.
    """
    blocked = {"suggested_quantity": None, "reason_code": "QUANTITY_REQUIRES_REVIEW"}
    if not isinstance(result, ItemResult) or not isinstance(policy, DemoItemPolicy):
        return blocked
    if not (result.identity_ok and result.quantity_ok and result.usage_ok and result.freshness_ok):
        return blocked
    if policy.version != DEMO_POLICY_VERSION or (policy.item_id, policy.dispensing_unit) != (result.item_id, result.dispensing_unit):
        return blocked
    fields = (policy.target_days, policy.confirmed_incoming, policy.order_multiple, policy.minimum_units)
    if any(type(value) is not Decimal or not value.is_finite() for value in fields):
        return blocked
    if not (0 < policy.target_days <= 30 and 0 <= policy.confirmed_incoming <= MAX_ORDER_UNITS
            and 0 < policy.order_multiple <= MAX_ORDER_UNITS and 0 < policy.minimum_units <= MAX_ORDER_UNITS):
        return blocked
    if any(value != value.to_integral_value() for value in (policy.order_multiple, policy.minimum_units)):
        return blocked
    if result.average_daily_usage is None or result.average_daily_usage <= 0:
        return blocked
    # Multiply before division, matching calculate_item's avoidance of double rounding.
    target = result.usage_total * policy.target_days / USAGE_DAYS
    deficit = max(Decimal(0), target - result.usable_quantity - policy.confirmed_incoming)
    amount = Decimal(0) if deficit == 0 else max(deficit, policy.minimum_units)
    amount = (amount / policy.order_multiple).to_integral_value(rounding=ROUND_CEILING) * policy.order_multiple
    if amount > MAX_ORDER_UNITS:
        return blocked
    return {"suggested_quantity": int(amount), "reason_code": "SUPPORTED_DEMO_POLICY",
            "policy_version": policy.version, "target_days": str(policy.target_days),
            "target_units": str(target), "confirmed_incoming": str(policy.confirmed_incoming),
            "order_multiple": str(policy.order_multiple), "minimum_units": str(policy.minimum_units),
            "calculation": "max(0, average_daily_usage * target_days - usable_stock - confirmed_incoming); apply minimum and round up to order multiple"}
