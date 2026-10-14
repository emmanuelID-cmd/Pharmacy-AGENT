"""Trusted per-run evidence; reuse harness validators and calculations unchanged."""
import time
from dataclasses import replace

from ..injection_prevention.action_guard import execute_guarded
from ..injection_prevention.boundary_contracts import Source
from ..injection_prevention.safe_context import assemble_context
from ..pharmacy_harness.calculate import calculate_item
from ..pharmacy_harness.facts import to_trusted_fact
from ..pharmacy_harness.report import assess_fda, build_report, failed_source_report
from ..pharmacy_harness.validate import duplicate_item_ids, inspect_item, inspect_snapshot
from ..pharmacy_tools.fda import _http_get, get_fda_shortage_context_batch
from ..pharmacy_tools.inventory import read_store_inventory


class EvidenceReview:
    def __init__(self, *, moment, budget, inventory_reader=None, fda_http_get=None):
        self.moment = moment
        self.budget = budget
        self.inventory_reader = inventory_reader or read_store_inventory
        self.http_get = fda_http_get or _http_get
        self.payload = None
        self.snapshot = None
        self.results = ()
        self.facts = ()
        self.context = None
        self.inventory_dispatch = None
        self.fda_views = {}
        self.called_ndcs = set()

    def remaining(self):
        return max(0, self.budget.seconds - (self.budget.clock() - self.budget.started))

    @property
    def ndcs(self):
        if self.context is None:
            return ()
        return tuple(dict.fromkeys(row["package_ndc"] for row in self.context["items"]))

    def read_inventory(self, call):
        captured = {}

        def reader(**arguments):
            captured["payload"] = self.inventory_reader(**arguments)
            return captured["payload"]

        dispatch = execute_guarded(call, executors={"read_store_inventory": reader}, budget=self.budget)
        self.inventory_dispatch = dispatch
        if dispatch.state != "COMPLETE" or "payload" not in captured:
            return dispatch, None
        self.payload = captured["payload"]
        self.snapshot = inspect_snapshot(self.payload, run_at=self.moment)
        duplicates = duplicate_item_ids(self.snapshot.items)
        self.results = tuple(calculate_item(
            inspect_item(row, run_at=self.moment, snapshot=self.snapshot, duplicate_ids=duplicates),
            evidence_reference=self.snapshot.snapshot_reference) for row in self.snapshot.items)
        self.facts = tuple(fact for fact in (to_trusted_fact(row) for row in self.results) if fact is not None)
        self.context = assemble_context(self.payload, source=Source.INVENTORY, facts=self.facts)
        return dispatch, self.context

    def read_fda(self, call):
        captured = {}

        def bounded_http(url, timeout):
            remaining = self.remaining()
            if remaining <= 0:
                raise TimeoutError("RUN_DEADLINE_EXCEEDED")
            return self.http_get(url, min(timeout, remaining, 5))

        def bounded_sleep(seconds):
            remaining = self.remaining()
            if remaining <= seconds:
                raise TimeoutError("RUN_DEADLINE_EXCEEDED")
            time.sleep(seconds)

        def reader(**arguments):
            captured["ndcs"] = tuple(arguments["package_ndcs"])
            captured["payload"] = get_fda_shortage_context_batch(
                **arguments, http_get=bounded_http, sleep=bounded_sleep)
            return captured["payload"]

        dispatch = execute_guarded(call, executors={"get_fda_shortage_context_batch": reader},
                                   budget=self.budget, allowed_package_ndcs=self.ndcs)
        ndcs = captured.get("ndcs", ())
        if dispatch.state == "COMPLETE" and captured["payload"]["meta"].get("package_ndcs") != list(ndcs):
            dispatch = replace(dispatch, state="MANUAL_REVIEW", reason_code="FDA_BATCH_BINDING_FAILED")
        if dispatch.state != "COMPLETE" or "payload" not in captured:
            for ndc in ndcs:
                self.fda_views[ndc] = assess_fda({"results": [], "meta": {
                    "state": "UNAVAILABLE", "reason": dispatch.reason_code}}, run_at=self.moment)
            return dispatch, None
        payload = captured["payload"]
        meta = payload["meta"]
        safe_rows = []
        for ndc in ndcs:
            exact = [row for row in payload["results"] if row.get("package_ndc") == ndc]
            state = meta["state"] if meta["state"] in {"PARTIAL", "UNAVAILABLE"} else "MATCH" if exact else "NO_MATCH"
            view = assess_fda({"results": exact, "meta": {**meta, "state": state, "package_ndc": ndc}},
                              run_at=self.moment)
            self.fda_views[ndc] = view
            self.called_ndcs.add(ndc)
            # No FDA narrative, URL or label is sent to the model.
            safe_state = view["state"] if view["state"] in {
                "MATCH", "NO_MATCH", "UNAVAILABLE", "PARTIAL", "STALE"} else "UNAVAILABLE"
            safe_rows.append({"package_ndc": ndc, "state": safe_state,
                              "external_risk": bool(view["external_risk"])})
        return dispatch, {"package_ndcs": list(ndcs), "results": safe_rows,
                          "authority": "NATIONAL_CONTEXT_ONLY"}

    def report(self):
        if self.context is None:
            if self.inventory_dispatch is None:
                return None
            return failed_source_report(run_at=self.moment, inventory_dispatch=self.inventory_dispatch)
        return build_report(run_at=self.moment, snapshot=self.snapshot, item_results=self.results,
                            payload=self.payload, facts=self.facts, fda_views=self.fda_views,
                            inventory_dispatch=self.inventory_dispatch)
