"""Independent evidence checks. Tool JSON is never treated as already trusted."""
from dataclasses import dataclass
from datetime import datetime, timedelta, date
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


def _finite_nonnegative(value):
    if type(value) is bool or type(value) not in (int, float):
        return False
    return math.isfinite(value) and value >= 0


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
    usable_quantity: float | None
    usage_total: float | None
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


def inspect_item(row, *, run_at, snapshot, duplicate_ids):
    """Check one inventory row. Missing days are unknown, never zero."""
    reasons = []
    if snapshot.reason_codes:
        for code in snapshot.reason_codes:
            if code not in ("DUPLICATE_ITEM_ID", "EMPTY_SOURCE"):
                reasons.append(code)

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

    identity_ok = item_id is not None and package_ndc is not None and dispensing_unit is not None
    if item_id is not None and item_id in duplicate_ids:
        identity_ok = False
    freshness_ok = (
        snapshot.store_ok and snapshot.synthetic_ok and snapshot.policy_ok and snapshot.snapshot_ok
    )

    usable_quantity = None
    if "usable_quantity" not in row:
        reasons.append("MISSING_USABLE_STOCK")
    elif not _finite_nonnegative(row["usable_quantity"]):
        reasons.append("INVALID_USABLE_STOCK")
    else:
        usable_quantity = float(row["usable_quantity"])
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
        if window_end is None or window_end != expected_end:
            reasons.append("INCOMPLETE_USAGE")
        elif type(units) is not list or len(units) != USAGE_DAYS:
            reasons.append("INCOMPLETE_USAGE")
        elif any(not _finite_nonnegative(value) for value in units):
            reasons.append("INVALID_USAGE")
        else:
            usage_total = float(sum(units))
    usage_ok = usage_total is not None

    # Deduplicate while preserving order.
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
