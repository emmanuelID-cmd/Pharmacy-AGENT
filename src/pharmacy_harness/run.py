"""One guarded review: read inventory, validate, calculate, then read FDA for accepted NDCs."""
try:
    from ..injection_prevention.action_guard import RunBudget, execute_guarded
    from ..pharmacy_tools.fda import get_fda_shortage_context
    from ..pharmacy_tools.inventory import read_store_inventory
except ImportError:
    from injection_prevention.action_guard import RunBudget, execute_guarded
    from pharmacy_tools.fda import get_fda_shortage_context
    from pharmacy_tools.inventory import read_store_inventory

from .calculate import calculate_item
from .facts import to_trusted_fact
from .report import assess_fda, build_report, failed_source_report
from .validate import STORE_ID, duplicate_item_ids, inspect_item, inspect_snapshot, parse_run_at


def run_review(*, run_at=None, store_id=STORE_ID, inventory_path=None, fda_http_get=None,
               fda_sleep=None, budget=None):
    """Execute one synthetic-store review. Tool JSON stays untrusted until this function verifies it.

    Tests inject fda_http_get. The CLI omits it so get_fda_shortage_context performs a real read.
    """
    moment = parse_run_at(run_at)
    budget = budget if budget is not None else RunBudget()
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
        return failed_source_report(run_at=moment, inventory_dispatch=inventory_dispatch)

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
    if len(accepted_ndcs) > 20:
        accepted_ndcs = accepted_ndcs[:20]

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
        payload_fda = get_fda_shortage_context(**kwargs)
        fda_payloads[arguments["package_ndc"]] = payload_fda
        return payload_fda

    if accepted_ndcs:
        executors = {"get_fda_shortage_context": fda_reader}
        for ndc in accepted_ndcs:
            dispatch = execute_guarded(
                {"name": "get_fda_shortage_context", "arguments": {"package_ndc": ndc}},
                executors=executors,
                budget=budget,
                allowed_package_ndcs=accepted_ndcs,
            )
            if dispatch.reason_code in {"RUN_BUDGET_EXHAUSTED", "RUN_DEADLINE_EXCEEDED"}:
                break
            if ndc not in fda_payloads:
                fda_payloads[ndc] = {
                    "results": [],
                    "meta": {"state": "UNAVAILABLE", "package_ndc": ndc,
                             "reason": dispatch.reason_code, "source": "openFDA drug shortages"},
                }

    fda_views = {}
    for ndc, payload_fda in fda_payloads.items():
        if payload_fda is None:
            continue
        fda_views[ndc] = assess_fda(payload_fda, run_at=moment)

    return build_report(
        run_at=moment, snapshot=snapshot, item_results=item_results, payload=payload,
        facts=facts, fda_views=fda_views, inventory_dispatch=inventory_dispatch,
    )
