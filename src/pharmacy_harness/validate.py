"""Independent evidence checks. Tool JSON is never treated as already trusted."""
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from decimal import Decimal
from zoneinfo import ZoneInfo
import math
import re

STORE_ID = 1618
POLICY_VERSION = "SYNTHETIC-v0"
NEW_YORK = ZoneInfo("America/New_York")
DISPENSING_UNITS = frozenset({"tablet", "capsule", "mL", "unit"})
NDC_PATTERN = re.compile(r"(?:\d{4}-\d{4}-\d{2}|\d{5}-\d{3}-\d{2}|\d{5}-\d{4}-\d{1})", re.ASCII)
ITEM_ID_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
USAGE_DAYS = 14
SNAPSHOT_MAX_HOURS = 24

# Source-level: withhold every recommendation. Row-level: only the affected item.
SOURCE_FAILURE_CODES = frozenset({
    "WRONG_STORE", "NOT_LABELED_SYNTHETIC", "SOURCE_MALFORMED", "EMPTY_SOURCE",
    "SNAPSHOT_MISSING_TIMEZONE", "FUTURE_SNAPSHOT", "STALE_SNAPSHOT", "UNSUPPORTED_POLICY",
})
ROW_FAILURE_CODES = frozenset({
    "DUPLICATE_ITEM_ID", "INVALID_ITEM_REFERENCE", "INVALID_PACKAGE_NDC",
    "INVALID_DISPENSING_UNIT", "MISSING_USABLE_STOCK", "INVALID_USABLE_STOCK",
    "INCOMPLETE_USAGE", "INVALID_USAGE", "NO_CONSUMPTION_BASIS", "SOURCE_EVIDENCE_BLOCKED",
})


def parse_run_at(value=None):
    """Return an aware America/New_York timestamp. Strings must include a timezone."""
    if value is None:
        return datetime.now(tz=NEW_YORK)
    if isinstance(value, datetime):
        moment = value
    elif type(value) is str:
        try:
            moment = datetime.fromisoformat(value)
        except ValueError:
            raise ValueError("INVALID_RUN_AT") from None
    else:
        raise ValueError("INVALID_RUN_AT")
    if moment.tzinfo is None:
        raise ValueError("RUN_AT_MISSING_TIMEZONE")
    return moment.astimezone(NEW_YORK)


def last_completed_day(run_at):
    return parse_run_at(run_at).date() - timedelta(days=1)


def as_nonnegative_decimal(value):
    """Accept JSON int/float as Decimal. Booleans are not quantities."""
    if type(value) is bool:
        return None
    if type(value) is int:
        number = Decimal(value)
    elif type(value) is float:
        if not math.isfinite(value):
            return None
        number = Decimal(str(value))
    elif type(value) is Decimal:
        number = value
    else:
        return None
    if not number.is_finite() or number < 0:
        return None
    return number


@dataclass(frozen=True)
class SnapshotEvidence:
    store_ok: bool
    synthetic_ok: bool
    policy_ok: bool
    snapshot_ok: bool
    snapshot_timestamp: datetime | None
    snapshot_reference: str
    policy_version: str | None
    reason_codes: tuple
    items: tuple


@dataclass(frozen=True)
class ItemEvidence:
    item_id: str | None
    package_ndc: str | None
    dispensing_unit: str | None
    usable_quantity: Decimal | None
    usage_total: Decimal | None
    usage_day_count: int
    window_end: date | None
    identity_ok: bool
    quantity_ok: bool
    usage_ok: bool
    freshness_ok: bool
    reason_codes: tuple


def inspect_snapshot(payload, *, run_at):
    """Shape-check the inventory snapshot against POLICY.md. Does not calculate supply."""
    reasons = []
    if type(payload) is not dict:
        return SnapshotEvidence(False, False, False, False, None, "harness-run-snapshot",
                                None, ("SOURCE_MALFORMED",), ())
    store_ok = type(payload.get("store_id")) is int and payload["store_id"] == STORE_ID
    synthetic_ok = payload.get("synthetic") is True
    policy_version = payload.get("policy_version") if type(payload.get("policy_version")) is str else None
    policy_ok = policy_version == POLICY_VERSION
    if not store_ok:
        reasons.append("WRONG_STORE")
    if not synthetic_ok:
        reasons.append("NOT_LABELED_SYNTHETIC")
    if not policy_ok:
        reasons.append("UNSUPPORTED_POLICY")

    snapshot_timestamp = None
    raw_ts = payload.get("snapshot_timestamp")
    if type(raw_ts) is not str:
        reasons.append("SNAPSHOT_MISSING_TIMEZONE")
    else:
        try:
            parsed = datetime.fromisoformat(raw_ts)
        except ValueError:
            parsed = None
        if parsed is None or parsed.tzinfo is None:
            reasons.append("SNAPSHOT_MISSING_TIMEZONE")
        else:
            snapshot_timestamp = parsed.astimezone(NEW_YORK)
            age_hours = (run_at - snapshot_timestamp).total_seconds() / 3600
            if age_hours < 0:
                reasons.append("FUTURE_SNAPSHOT")
            elif age_hours > SNAPSHOT_MAX_HOURS:
                reasons.append("STALE_SNAPSHOT")

    snapshot_ok = snapshot_timestamp is not None and "FUTURE_SNAPSHOT" not in reasons and "STALE_SNAPSHOT" not in reasons
    reference = payload.get("snapshot_reference")
    if type(reference) is not str or ITEM_ID_PATTERN.fullmatch(reference) is None:
        reference = "harness-run-snapshot"

    items = payload.get("items")
    if type(items) is not list or not items:
        reasons.append("EMPTY_SOURCE")
        item_rows = ()
    else:
        item_rows = tuple(row if type(row) is dict else {} for row in items)
        seen = {}
        for row in item_rows:
            item_id = row.get("item_id")
            if type(item_id) is str:
                seen[item_id] = seen.get(item_id, 0) + 1
        if any(count > 1 for count in seen.values()):
            reasons.append("DUPLICATE_ITEM_ID")

    return SnapshotEvidence(store_ok, synthetic_ok, policy_ok, snapshot_ok, snapshot_timestamp,
                            reference, policy_version, tuple(reasons), item_rows)


def locate_identity_source_faults(items):
    """Return row/field locators for identity defects. Never include the untrusted value.

    Positions are 1-based in the source items list (row 1 is the first element).
    Used when intake rejects the payload so the reviewer is not left hunting.
    """
    if type(items) is not list:
        return ()
    faults = []
    seen = {}
    for index, row in enumerate(items):
        position = index + 1
        if type(row) is not dict:
            faults.append({"row": position, "field": "item_id", "reason": "MALFORMED_ROW"})
            continue
        if "item_id" not in row or row.get("item_id") is None:
            faults.append({"row": position, "field": "item_id", "reason": "MISSING_ITEM_ID"})
            continue
        item_id = row.get("item_id")
        if type(item_id) is not str or ITEM_ID_PATTERN.fullmatch(item_id) is None:
            faults.append({"row": position, "field": "item_id", "reason": "INVALID_ITEM_REFERENCE"})
            continue
        seen.setdefault(item_id, []).append(position)
    for positions in seen.values():
        if len(positions) > 1:
            for position in positions:
                faults.append({"row": position, "field": "item_id", "reason": "DUPLICATE_ITEM_ID"})
    return tuple(sorted(faults, key=lambda fault: (fault["row"], fault["reason"])))


def inspect_item(row, *, run_at, snapshot, duplicate_ids):
    """Check one inventory row. Source-level codes stay on the snapshot, not copied here.

    INVALID_ITEM_REFERENCE still fires here for direct callers and defense-in-depth.
    On the guarded run, a missing, non-opaque, or duplicate item_id fails intake
    first (execute_guarded INVALID_TOOL_RESULT) and never reaches this check.
    Invalid NDC, unit, quantity, and usage stay row-level on that path.
    """
    reasons = []
    item_id = row.get("item_id") if type(row.get("item_id")) is str else None
    if item_id is None or ITEM_ID_PATTERN.fullmatch(item_id) is None:
        item_id = None
        reasons.append("INVALID_ITEM_REFERENCE")
    elif item_id in duplicate_ids:
        reasons.append("DUPLICATE_ITEM_ID")

    package_ndc = row.get("package_ndc") if type(row.get("package_ndc")) is str else None
    if package_ndc is None or NDC_PATTERN.fullmatch(package_ndc) is None:
        package_ndc = None
        reasons.append("INVALID_PACKAGE_NDC")

    dispensing_unit = row.get("dispensing_unit") if type(row.get("dispensing_unit")) is str else None
    if dispensing_unit not in DISPENSING_UNITS:
        dispensing_unit = None
        reasons.append("INVALID_DISPENSING_UNIT")

    # PRD AMBIGUOUS_ITEM: strength is required identity. Missing/blank/non-string
    # withholds calculation — never MAINTAIN on an incomplete package identity.
    raw_strength = row.get("strength") if "strength" in row else None
    if type(raw_strength) is not str or not raw_strength.strip():
        reasons.append("AMBIGUOUS_ITEM")

    identity_ok = (
        item_id is not None and package_ndc is not None and dispensing_unit is not None
        and type(raw_strength) is str and bool(raw_strength.strip())
    )
    if item_id is not None and item_id in duplicate_ids:
        identity_ok = False
    freshness_ok = (
        snapshot.store_ok and snapshot.synthetic_ok and snapshot.policy_ok and snapshot.snapshot_ok
    )
    if not freshness_ok:
        reasons.append("SOURCE_EVIDENCE_BLOCKED")

    usable_quantity = None
    if "usable_quantity" not in row:
        reasons.append("MISSING_USABLE_STOCK")
    else:
        usable_quantity = as_nonnegative_decimal(row["usable_quantity"])
        if usable_quantity is None:
            reasons.append("INVALID_USABLE_STOCK")
    quantity_ok = usable_quantity is not None

    usage_total = None
    usage_day_count = 0
    window_end = None
    usage = row.get("daily_usage")
    expected_end = last_completed_day(run_at)
    if type(usage) is not dict:
        reasons.append("INCOMPLETE_USAGE")
    else:
        raw_end = usage.get("window_end")
        units = usage.get("units")
        if type(raw_end) is str:
            try:
                window_end = date.fromisoformat(raw_end)
            except ValueError:
                window_end = None
        if type(units) is list:
            usage_day_count = len(units)
        parsed_units = [as_nonnegative_decimal(value) for value in units] if type(units) is list else None
        if window_end is None or window_end != expected_end:
            reasons.append("INCOMPLETE_USAGE")
        elif parsed_units is None or len(parsed_units) != USAGE_DAYS:
            reasons.append("INCOMPLETE_USAGE")
        elif any(value is None for value in parsed_units):
            reasons.append("INVALID_USAGE")
        else:
            usage_total = sum(parsed_units, Decimal(0))
    usage_ok = usage_total is not None

    unique = []
    for code in reasons:
        if code not in unique:
            unique.append(code)
    return ItemEvidence(item_id, package_ndc, dispensing_unit, usable_quantity, usage_total,
                        usage_day_count, window_end, identity_ok, quantity_ok, usage_ok, freshness_ok,
                        tuple(unique))


def duplicate_item_ids(items):
    counts = {}
    for row in items:
        item_id = row.get("item_id") if type(row) is dict else None
        if type(item_id) is str:
            counts[item_id] = counts.get(item_id, 0) + 1
    return frozenset(item_id for item_id, count in counts.items() if count > 1)
