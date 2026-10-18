"""PRD manager table. Built from the harness report; never reinserts FDA narrative text."""

SYNTHETIC_LABEL = "SYNTHETIC INVENTORY TEST"

FDA_LIMIT_TEXT = {
    "NO_MATCH": "NO_MATCH is not guaranteed supply.",
    "UNAVAILABLE": "UNAVAILABLE is not no shortage.",
    "PARTIAL": "PARTIAL is not a complete national result.",
    "STALE": "National dataset date is stale relative to this run.",
    "NEEDS_REVIEW": "Matching records conflict; compare all returned records.",
    "NOT_CALLED": "FDA was not called for one or more rows.",
}


def _qty(row):
    qty = row.get("usable_quantity")
    unit = row.get("dispensing_unit") or ""
    if qty is None:
        return "withheld"
    return f"{qty:g} {unit}".strip()


def _days(row):
    display = row.get("days_of_supply_display")
    if display in (None, "unavailable"):
        return "unavailable"
    return str(display)


def _action(row):
    local = row.get("local_action") or ""
    if row.get("external_action") == "REVIEW":
        return f"{local}+ext REVIEW"
    return local


def _fda_cell(row):
    state = row.get("fda_state") or ""
    records = row.get("fda_records") or []
    status = row.get("fda_status")
    availability = row.get("fda_availability")
    if status and availability:
        facts = f"{status}/{availability}"
    elif status or availability:
        facts = status or availability
    else:
        facts = None
    extra = f" ({len(records)} records)" if len(records) > 1 else ""
    if facts:
        return f"{state} {facts}{extra}"
    return f"{state}{extra}"


def _fda_record_line(record):
    status = record.get("status") or "?"
    availability = record.get("availability") or "?"
    update_date = record.get("update_date") or "no update_date"
    return f"{status}/{availability} {update_date}"


def format_manager_report(report):
    """Render the PRD human report: header, manual review, table, FDA limits, next step."""
    lines = [SYNTHETIC_LABEL]
    window = report.get("usage_window") or {}
    window_text = "unavailable"
    if window.get("start") and window.get("end"):
        window_text = f"{window['start']} .. {window['end']}"
    lines.append(
        f"Store {report.get('store_id')}    Policy {report.get('policy_version')}    "
        f"Run {report.get('run_at')}"
    )
    lines.append(
        f"Snapshot {report.get('snapshot_timestamp') or 'unavailable'}    "
        f"Usage window {window_text}"
    )
    states = sorted({row.get("fda_state") for row in report.get("items") or [] if row.get("fda_state")})
    fda_header = ", ".join(states) if states else report.get("source_state")
    lines.append(
        f"Run state {report.get('run_state')}    Source {report.get('source_state')}    "
        f"FDA {fda_header}"
    )
    if report.get("fda_source") == "OFFLINE":
        lines.append("FDA source: recorded offline payload (not a live openFDA call).")
    elif report.get("fda_source") == "LIVE":
        lines.append("FDA source: live openFDA.")
    turn = report.get("model_turn") or {}
    provider = turn.get("provider_model")
    provider_note = f" Provider model: {provider}." if provider else ""
    if turn.get("state") == "ACCEPTED":
        lines.append(f"Model turn: ACCEPTED. Copied report-v1.{provider_note}")
    elif turn.get("state") == "REJECTED":
        reason = turn.get("reason_code") or "OUTPUT_EVIDENCE_MISMATCH"
        lines.append(
            f"Model turn: REJECTED ({reason}). Using verified facts only.{provider_note}"
        )
    elif turn.get("state") == "MODEL_UNAVAILABLE":
        reason = turn.get("reason_code") or "MODEL_TRANSPORT_FAILED"
        lines.append(
            f"Model turn: MODEL_UNAVAILABLE ({reason}). "
            f"No live model answer; using verified facts only.{provider_note}"
        )
    elif turn.get("state") == "SKIPPED":
        lines.append("Model turn: skipped (deterministic report only).")
    if report.get("source_reason"):
        lines.append(f"Source reason {report['source_reason']}")
    lines.append("")

    items = list(report.get("items") or [])
    review_rows = [row for row in items if row.get("local_action") == "MANUAL_REVIEW"]
    lines.append("Needs manual review")
    if not items and report.get("run_state") == "MANUAL_REVIEW":
        reason = report.get("source_reason") or "source unavailable"
        lines.append(f"  Entire source. {reason}. No stock condition is claimed.")
        for fault in report.get("source_faults") or ():
            if type(fault) is not dict:
                continue
            row = fault.get("row")
            field = fault.get("field")
            code = fault.get("reason")
            if type(row) is not int or type(field) is not str:
                continue
            extra = f" ({code})" if type(code) is str else ""
            lines.append(f"  row {row}, {field}{extra}")
    elif not review_rows:
        lines.append("  None.")
    else:
        for row in review_rows:
            codes = ", ".join(row.get("reason_codes") or []) or "see explanation"
            lines.append(
                f"  {row.get('item_id')}  {row.get('package_ndc') or 'no NDC'}  {codes}"
            )
    lines.append("")

    lines.append("Inventory review")
    header = (
        f"{'item':<12} {'NDC':<14} {'qty/unit':<14} {'days':<12} "
        f"{'class':<18} {'action':<22} {'FDA'}"
    )
    lines.append(header)
    if not items:
        lines.append("  (no item rows)")
    for row in items:
        lines.append(
            f"{str(row.get('item_id') or ''):<12} {str(row.get('package_ndc') or ''):<14} "
            f"{_qty(row):<14} {_days(row):<12} {str(row.get('local_class') or ''):<18} "
            f"{_action(row):<22} {_fda_cell(row)}"
        )
        records = row.get("fda_records") or []
        if len(records) > 1:
            shown = "; ".join(_fda_record_line(record) for record in records)
            lines.append(f"             FDA records: {shown}")
        explanation = row.get("explanation") or ""
        if explanation:
            lines.append(f"             {explanation}")
    lines.append("")

    lines.append("External context limitations")
    present = {row.get("fda_state") for row in items}
    noted = [state for state in ("NO_MATCH", "UNAVAILABLE", "PARTIAL", "STALE", "NEEDS_REVIEW", "NOT_CALLED")
             if state in present]
    if not noted:
        lines.append("  No FDA limitation states on this run.")
    else:
        for state in noted:
            lines.append(f"  {FDA_LIMIT_TEXT[state]}")
    lines.append("")

    for warning in report.get("warnings") or []:
        lines.append(str(warning))
    lines.append(report.get("human_next_step") or "")
    lines.append("No order has been placed.")
    return "\n".join(lines).rstrip() + "\n"
