"""Deterministic human report. Warning sentences come from trusted display text, not a model."""
from datetime import timedelta

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


def assess_fda(payload, *, run_at):
    """Label national context without changing local stock class."""
    empty = {"state": "UNAVAILABLE", "status": None, "availability": None, "update_date": None,
             "dataset_updated": None, "external_risk": False, "reason": "NOT_RETRIEVED"}
    if type(payload) is not dict or type(payload.get("meta")) is not dict:
        return empty
    meta = payload["meta"]
    state = meta.get("state") if type(meta.get("state")) is str else "UNAVAILABLE"
    results = payload.get("results") if type(payload.get("results")) is list else []
    row = results[0] if results and type(results[0]) is dict else {}
    status = row.get("status") if type(row.get("status")) is str else None
    availability = row.get("availability") if type(row.get("availability")) is str else None
    update_date = row.get("update_date") if type(row.get("update_date")) is str else None
    dataset_updated = meta.get("dataset_updated") if type(meta.get("dataset_updated")) is str else None
    reason = meta.get("reason") if type(meta.get("reason")) is str else None
    if state in {"MATCH", "PARTIAL"} and dataset_updated:
        try:
            from datetime import date
            dataset_date = date.fromisoformat(dataset_updated[:10])
        except ValueError:
            dataset_date = None
        if dataset_date is not None and (run_at.date() - dataset_date).days > 2:
            state = "STALE"
            reason = "DATASET_OLDER_THAN_TWO_DAYS"
    external_risk = state in {"MATCH", "PARTIAL", "STALE"} and status == "Current" and availability == "Unavailable"
    return {"state": state, "status": status, "availability": availability, "update_date": update_date,
            "dataset_updated": dataset_updated, "external_risk": external_risk, "reason": reason}


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
    parts.append("No order quantity. Human executes operational action outside the agent.")
    return " ".join(parts)


def sort_items(rows):
    def key(row):
        action_rank = 0 if row["local_action"] == "MANUAL_REVIEW" else 1
        class_rank = CLASS_ORDER.get(row["local_class"], 9)
        return (action_rank, class_rank, row["input_index"])
    return sorted(rows, key=key)


def build_item_row(result, *, input_index, fda, run_at):
    view = fda if fda is not None else {
        "state": "NOT_CALLED", "status": None, "availability": None, "update_date": None,
        "dataset_updated": None, "external_risk": False, "reason": None,
    }
    external_action = "REVIEW" if view.get("external_risk") else None
    return {
        "input_index": input_index,
        "item_id": result.item_id,
        "package_ndc": result.package_ndc,
        "usable_quantity": result.usable_quantity,
        "dispensing_unit": result.dispensing_unit,
        "average_daily_usage": result.average_daily_usage,
        "days_of_supply": result.days_of_supply,
        "days_of_supply_display": result.days_of_supply_display,
        "local_class": result.local_class,
        "local_action": result.local_action,
        "zero_stock_fact": result.zero_stock_fact,
        "fda_state": view["state"],
        "fda_status": view["status"],
        "fda_availability": view["availability"],
        "fda_update_date": view["update_date"],
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
        "items": [],
        "warning_codes": warning_codes,
        "warnings": render_warnings(warning_codes),
        "human_next_step": HUMAN_NEXT_STEP,
        "order_placed": False,
        "inventory_changed": False,
        "safety_report": None,
    }
