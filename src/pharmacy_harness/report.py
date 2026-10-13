"""Deterministic human report. Warning sentences come from trusted display text, not a model."""
from datetime import date, timedelta
from decimal import Decimal

try:
    from ..injection_prevention.output_guard import expected_report
    from ..injection_prevention.safe_context import assemble_context
    from ..injection_prevention.boundary_contracts import Source
    from ..pharmacy_tools.instructions import HUMAN_NEXT_STEP, render_warnings
except ImportError:
    from injection_prevention.output_guard import expected_report
    from injection_prevention.safe_context import assemble_context
    from injection_prevention.boundary_contracts import Source
    from pharmacy_tools.instructions import HUMAN_NEXT_STEP, render_warnings

from .validate import POLICY_VERSION, STORE_ID, USAGE_DAYS, last_completed_day

CLASS_ORDER = {"MANUAL_REVIEW": 0, "CRITICAL": 1, "LOW": 2, "ABOVE_THRESHOLD": 3, "UNKNOWN": 4}
FDA_DATASET_STALE_DAYS = 2
FDA_RECORD_FIELDS = (
    "package_ndc", "generic_name", "availability", "related_info", "update_date",
    "therapeutic_category", "dosage_form", "presentation", "company_name",
    "shortage_reason", "status",
)
# Identity, shortage facts, and record dates. Narrative related_info is shown, not compared.
FDA_CONFLICT_FIELDS = (
    "package_ndc", "generic_name", "dosage_form", "presentation",
    "status", "availability", "update_date",
)


def json_number(value):
    """JSON-safe number. Decimal is converted only at the report edge."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def _copy_fda_record(row):
    copied = {}
    for key in FDA_RECORD_FIELDS:
        value = row.get(key)
        copied[key] = value if type(value) is str else None
    return copied


def _fda_view(*, state, status=None, availability=None, update_date=None, dataset_updated=None,
              external_risk=False, reason=None, records=()):
    return {
        "state": state, "status": status, "availability": availability, "update_date": update_date,
        "dataset_updated": dataset_updated, "external_risk": external_risk, "reason": reason,
        "records": tuple(records),
    }


def assess_fda(payload, *, run_at):
    """Label national context without changing local stock class.

    Every exact-match result row is copied. Summary status/availability/update_date are
    filled only when those copied records agree. Conflicting identity, shortage facts,
    or record dates become NEEDS_REVIEW; the harness does not pick a winner.

    A fetch performed during this run is fresh: adapter retrieved_at uses wall-clock now()
    and must not be compared to a frozen --run-at (that would look like a future timestamp).
    Dataset calendar age is compared to run_at in America/New_York. A dataset date newer
    than the run (negative age) is not stale. SYNTHETIC-v0 prototype: older than two
    calendar days is STALE when records otherwise agree.
    """
    empty = _fda_view(state="UNAVAILABLE", reason="NOT_RETRIEVED")
    if type(payload) is not dict or type(payload.get("meta")) is not dict:
        return empty
    meta = payload["meta"]
    state = meta.get("state") if type(meta.get("state")) is str else "UNAVAILABLE"
    results = payload.get("results") if type(payload.get("results")) is list else []
    records = tuple(_copy_fda_record(row) for row in results if type(row) is dict)
    signatures = {tuple(record[key] for key in FDA_CONFLICT_FIELDS) for record in records}
    conflict = len(signatures) > 1
    dataset_updated = meta.get("dataset_updated") if type(meta.get("dataset_updated")) is str else None
    reason = meta.get("reason") if type(meta.get("reason")) is str else None
    if conflict and state in {"MATCH", "PARTIAL", "STALE"}:
        state = "NEEDS_REVIEW"
        reason = "CONFLICTING_RECORDS"
    # Intentionally ignore meta.retrieved_at: same-run fetches are fresh.
    if state in {"MATCH", "PARTIAL"} and dataset_updated:
        try:
            dataset_date = date.fromisoformat(dataset_updated[:10])
        except ValueError:
            dataset_date = None
        if dataset_date is not None and (run_at.date() - dataset_date).days > FDA_DATASET_STALE_DAYS:
            state = "STALE"
            reason = "DATASET_OLDER_THAN_TWO_DAYS"
    if len(signatures) == 1:
        status = records[0]["status"]
        availability = records[0]["availability"]
        update_date = records[0]["update_date"]
    else:
        status = availability = update_date = None
    shortage_signal = any(
        record["status"] == "Current" and record["availability"] == "Unavailable"
        for record in records
    )
    external_risk = shortage_signal and state in {"MATCH", "PARTIAL", "STALE", "NEEDS_REVIEW"}
    return _fda_view(
        state=state, status=status, availability=availability, update_date=update_date,
        dataset_updated=dataset_updated, external_risk=external_risk, reason=reason,
        records=records,
    )


def explain(result, fda):
    parts = []
    if result.days_of_supply is not None:
        parts.append(
            f"{result.usable_quantity:g} {result.dispensing_unit} / ({result.usage_total:g}/{USAGE_DAYS}) "
            f"= {result.days_of_supply_display} days displayed (unrounded {result.days_of_supply})."
        )
        parts.append("Classified against SYNTHETIC-v0 thresholds: critical 2 days, low 5 days.")
        if result.local_action == "MAINTAIN":
            parts.append("MAINTAIN existing review approach; not an order endorsement.")
        else:
            parts.append("REVIEW with authorized staff.")
    else:
        if result.reason_codes:
            parts.append("Days of supply withheld (" + ", ".join(result.reason_codes) + ").")
        else:
            parts.append("Days of supply withheld.")
        if result.zero_stock_fact:
            parts.append("Verified zero stock is a CRITICAL stock fact; replenishment quantity is not inferred.")
        if result.average_daily_usage == 0:
            parts.append("Zero usage does not establish infinite supply.")
        parts.append("MANUAL_REVIEW: correct local inputs and retry.")
    if fda["state"] == "NOT_CALLED":
        parts.append("FDA was not called for this row.")
    else:
        parts.append(f"FDA {fda['state']}: national context does not change the local class.")
        if fda["external_risk"]:
            parts.append("FDA Current/Unavailable adds a separate external-risk REVIEW.")
        if fda["state"] == "NO_MATCH":
            parts.append("NO_MATCH is not guaranteed supply.")
        if fda["state"] == "UNAVAILABLE":
            parts.append("UNAVAILABLE is not no shortage.")
        if fda["state"] == "PARTIAL":
            parts.append("PARTIAL is not a complete national result.")
        if fda["state"] == "STALE":
            parts.append("National dataset date is stale relative to this run.")
        if fda["state"] == "NEEDS_REVIEW":
            parts.append(
                f"{len(fda.get('records') or ())} matching records conflict; "
                "compare all returned records."
            )
        elif len(fda.get("records") or ()) > 1:
            parts.append(f"{len(fda['records'])} matching records shown; they agree.")
    parts.append("No order quantity. Human executes operational action outside the agent.")
    return " ".join(parts)


def sort_items(rows):
    def key(row):
        action_rank = 0 if row["local_action"] == "MANUAL_REVIEW" else 1
        class_rank = CLASS_ORDER.get(row["local_class"], 9)
        return (action_rank, class_rank, row["input_index"])
    return sorted(rows, key=key)


def build_item_row(result, *, input_index, fda, run_at):
    view = fda if fda is not None else _fda_view(state="NOT_CALLED")
    external_action = "REVIEW" if view.get("external_risk") else None
    records = [dict(row) for row in view.get("records") or ()]
    return {
        "input_index": input_index,
        "item_id": result.item_id,
        "package_ndc": result.package_ndc,
        "usable_quantity": json_number(result.usable_quantity),
        "dispensing_unit": result.dispensing_unit,
        "average_daily_usage": json_number(result.average_daily_usage),
        "days_of_supply": json_number(result.days_of_supply),
        "days_of_supply_display": result.days_of_supply_display,
        "local_class": result.local_class,
        "local_action": result.local_action,
        "zero_stock_fact": result.zero_stock_fact,
        "fda_state": view["state"],
        "fda_status": view["status"],
        "fda_availability": view["availability"],
        "fda_update_date": view["update_date"],
        "fda_records": records,
        "external_action": external_action,
        "reason_codes": list(result.reason_codes),
        "explanation": explain(result, view),
    }


def build_report(*, run_at, snapshot, item_results, payload, facts, fda_views, inventory_dispatch):
    rows = []
    for index, result in enumerate(item_results):
        ndc = result.package_ndc
        view = fda_views.get(ndc) if ndc else None
        rows.append(build_item_row(result, input_index=index, fda=view, run_at=run_at))
    ordered = sort_items(rows)
    run_state = "READY_FOR_HUMAN_REVIEW"
    if any(row["local_action"] == "MANUAL_REVIEW" for row in ordered) or snapshot.reason_codes:
        run_state = "MANUAL_REVIEW"
    if inventory_dispatch.state != "COMPLETE":
        run_state = "MANUAL_REVIEW"
    try:
        context = assemble_context(payload, source=Source.INVENTORY, facts=facts)
        safety = expected_report(context)
        warning_codes = list(safety["warning_codes"])
    except Exception:
        context = None
        safety = None
        warning_codes = ["MANUAL_REVIEW_REQUIRED"]
        run_state = "MANUAL_REVIEW"
    if run_state == "MANUAL_REVIEW" and "MANUAL_REVIEW_REQUIRED" not in warning_codes:
        warning_codes.append("MANUAL_REVIEW_REQUIRED")
    window_end = last_completed_day(run_at)
    return {
        "schema_version": "harness-report-v1",
        "data_mode": "SYNTHETIC",
        "store_id": STORE_ID,
        "policy_version": snapshot.policy_version or POLICY_VERSION,
        "run_at": run_at.isoformat(timespec="seconds"),
        "snapshot_timestamp": snapshot.snapshot_timestamp.isoformat(timespec="seconds") if snapshot.snapshot_timestamp else None,
        "snapshot_reference": snapshot.snapshot_reference,
        "usage_window": {
            "start": (window_end - timedelta(days=USAGE_DAYS - 1)).isoformat(),
            "end": window_end.isoformat(),
        },
        "run_state": run_state,
        "source_state": inventory_dispatch.state,
        "source_reason": inventory_dispatch.reason_code,
        "source_reason_codes": list(snapshot.reason_codes),
        "items": ordered,
        "warning_codes": warning_codes,
        "warnings": render_warnings(warning_codes),
        "human_next_step": HUMAN_NEXT_STEP,
        "order_placed": False,
        "inventory_changed": False,
        "safety_report": safety,
    }


def failed_source_report(*, run_at, inventory_dispatch):
    warning_codes = ["MANUAL_REVIEW_REQUIRED"]
    return {
        "schema_version": "harness-report-v1",
        "data_mode": "SYNTHETIC",
        "store_id": STORE_ID,
        "policy_version": POLICY_VERSION,
        "run_at": run_at.isoformat(timespec="seconds"),
        "snapshot_timestamp": None,
        "snapshot_reference": None,
        "usage_window": None,
        "run_state": "MANUAL_REVIEW",
        "source_state": inventory_dispatch.state,
        "source_reason": inventory_dispatch.reason_code,
        "source_reason_codes": [inventory_dispatch.reason_code],
        "items": [],
        "warning_codes": warning_codes,
        "warnings": render_warnings(warning_codes),
        "human_next_step": HUMAN_NEXT_STEP,
        "order_placed": False,
        "inventory_changed": False,
        "safety_report": None,
    }
