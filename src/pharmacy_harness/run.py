"""One guarded review: read inventory, validate, calculate, then read FDA for accepted NDCs."""
try:
    from ..injection_prevention.action_guard import RunBudget, execute_guarded
    from ..pharmacy_tools.fda import get_fda_shortage_context_batch
    from ..pharmacy_tools.inventory import read_store_inventory
except ImportError:
    from injection_prevention.action_guard import RunBudget, execute_guarded
    from pharmacy_tools.fda import get_fda_shortage_context_batch
    from pharmacy_tools.inventory import read_store_inventory

from .calculate import calculate_item
from .facts import to_trusted_fact
from .report import assess_fda, build_report, failed_source_report
from .validate import (
    STORE_ID, duplicate_item_ids, inspect_item, inspect_snapshot,
    locate_identity_source_faults, parse_run_at,
)


def run_review(*, run_at=None, store_id=STORE_ID, inventory_path=None, fda_http_get=None,
               fda_sleep=None, budget=None, complete=None):
    """Execute one synthetic-store review. Tool JSON stays untrusted until this function verifies it.

    Tests and `--offline` inject fda_http_get. The CLI omits it so get_fda_shortage_context
    performs a real read. `complete` is one optional model turn; invented numbers are rejected.
    """
    moment = parse_run_at(run_at)
    budget = budget if budget is not None else RunBudget()
    fda_source = "OFFLINE" if fda_http_get is not None else "LIVE"
    captured = {}

    def inventory_reader(**arguments):
        kwargs = dict(arguments)
        if inventory_path is not None:
            kwargs["path"] = inventory_path
        captured["inventory"] = read_store_inventory(**kwargs)
        return captured["inventory"]

    inventory_dispatch = execute_guarded(
        {"name": "read_store_inventory", "arguments": {"store_id": store_id}},
        executors={"read_store_inventory": inventory_reader},
        budget=budget,
    )
    if inventory_dispatch.state != "COMPLETE" or "inventory" not in captured:
        payload = captured.get("inventory")
        faults = ()
        if type(payload) is dict:
            faults = locate_identity_source_faults(payload.get("items"))
        return failed_source_report(
            run_at=moment, inventory_dispatch=inventory_dispatch, fda_source=fda_source,
            source_faults=faults,
        )

    payload = captured["inventory"]
    snapshot = inspect_snapshot(payload, run_at=moment)
    duplicates = duplicate_item_ids(snapshot.items)
    item_results = tuple(
        calculate_item(inspect_item(row, run_at=moment, snapshot=snapshot, duplicate_ids=duplicates),
                       evidence_reference=snapshot.snapshot_reference)
        for row in snapshot.items
    )
    facts = tuple(fact for fact in (to_trusted_fact(result) for result in item_results) if fact is not None)

    accepted_ndcs = tuple(dict.fromkeys(
        result.package_ndc for result in item_results if result.package_ndc is not None
    ))
    fda_payloads = {}
    if fda_sleep is not None:
        sleep = fda_sleep
    elif fda_http_get is not None:
        sleep = lambda _seconds: None
    else:
        sleep = None

    def fda_reader(**arguments):
        kwargs = dict(arguments)
        if fda_http_get is not None:
            kwargs["http_get"] = fda_http_get
        if sleep is not None:
            kwargs["sleep"] = sleep
        payload_fda = get_fda_shortage_context_batch(**kwargs)
        fda_payloads[tuple(arguments["package_ndcs"])] = payload_fda
        return payload_fda

    if accepted_ndcs:
        executors = {"get_fda_shortage_context_batch": fda_reader}
        for offset in range(0,len(accepted_ndcs),10):
            ndcs = accepted_ndcs[offset:offset+10]
            dispatch = execute_guarded(
                {"name": "get_fda_shortage_context_batch", "arguments": {"package_ndcs": list(ndcs)}},
                executors=executors,
                budget=budget,
                allowed_package_ndcs=accepted_ndcs,
            )
            # A captured callback is never usable after a failed inspection/deadline.
            batch = fda_payloads.pop(ndcs, None) if dispatch.state == "COMPLETE" else None
            if batch is None:
                batch = {"results": [], "meta": {"state": "UNAVAILABLE",
                         "reason": dispatch.reason_code, "source": "openFDA drug shortages"}}
            meta = batch["meta"]
            for ndc in ndcs:
                exact = [row for row in batch["results"] if row.get("package_ndc") == ndc]
                state = meta["state"] if meta["state"] in {"PARTIAL","UNAVAILABLE"} else "MATCH" if exact else "NO_MATCH"
                fda_payloads[ndc] = {"results": exact, "meta": {**meta, "state": state, "package_ndc": ndc}}
            if dispatch.reason_code in {"RUN_BUDGET_EXHAUSTED", "RUN_DEADLINE_EXCEEDED"}:
                break

    fda_views = {}
    for ndc, payload_fda in fda_payloads.items():
        if payload_fda is None:
            continue
        fda_views[ndc] = assess_fda(payload_fda, run_at=moment)

    return build_report(
        run_at=moment, snapshot=snapshot, item_results=item_results, payload=payload,
        facts=facts, fda_views=fda_views, inventory_dispatch=inventory_dispatch,
        fda_source=fda_source, complete=complete,
    )
