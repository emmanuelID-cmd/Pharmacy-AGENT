"""Bounded Claude tool loop. Permission and evidence checks remain outside Claude."""
import asyncio
from copy import deepcopy
import json
import re
import threading

from ..injection_prevention.action_guard import RunBudget, authorize_tool_call, execute_guarded
from ..injection_prevention.boundary_contracts import ContractError, Source, strict_json_loads
from ..injection_prevention.contracts import Decision
from ..injection_prevention.output_guard import expected_report, validate_report
from ..injection_prevention.safe_context import inspect_payload
from ..pharmacy_harness.validate import parse_run_at
from ..pharmacy_tools.instructions import render_warnings
from .anthropic_client import ClaudeClient, ProviderUnavailable, claude_tools
from .review import EvidenceReview


class ReadActivity:
    """Keep cancelled read workers visible to the server's existing run limit."""
    def __init__(self):
        self.lock = threading.Lock()
        self.count = 0

    @property
    def pending(self):
        with self.lock:
            return self.count > 0

    async def execute(self, callback, call):
        with self.lock:
            self.count += 1

        def read():
            try:
                return callback(call)
            finally:
                with self.lock:
                    self.count -= 1

        task = asyncio.create_task(asyncio.to_thread(read))
        # Do not cancel the worker future when the HTTP/model wait ends. Keep its
        # completion observable, and consume exceptions without private logging.
        def completed(future):
            if not future.cancelled():
                future.exception()
        task.add_done_callback(completed)
        return await asyncio.shield(task)


def envelope(*, state, reason, report, settings, called=False, accepted=False, turns=0, counts=None):
    return {"state": state, "reason_code": reason, "report": report,
            "agent": {"model": settings.model, "model_called": called,
                      "output_accepted": accepted, "turns": turns,
                      "counts": counts or {"attempted": 0, "denied": 0, "dispatched": 0, "completed": 0}}}


def mark_manual(report, code, safety=None):
    if report is None:
        return None
    report = deepcopy(report)
    report["run_state"] = "MANUAL_REVIEW"
    if code not in report["source_reason_codes"]:
        report["source_reason_codes"].append(code)
    for warning in ("MANUAL_REVIEW_REQUIRED", "OUTPUT_REJECTED" if safety else None):
        if warning and warning not in report["warning_codes"]:
            report["warning_codes"].append(warning)
    report["warnings"] = render_warnings(report["warning_codes"])
    if safety is not None:
        report["safety_report"] = safety
    return report


async def run_agent(request, *, settings, provider=None, run_at=None,
                    inventory_reader=None, fda_http_get=None, read_activity=None):
    """Callbacks, clock and settings are trusted application dependencies, never JSON fields."""
    assessment = inspect_payload({"request": request}, source=Source.USER_REQUEST)
    if not assessment.source_contract_valid or assessment.decision != Decision.ACCEPT:
        return envelope(state="Manual Review", reason="REQUEST_REQUIRES_REVIEW", report=None, settings=settings)
    if provider is None and not settings.api_key:
        return envelope(state="Temporarily Unavailable", reason="PROVIDER_NOT_CONFIGURED", report=None, settings=settings)
    provider = provider or ClaudeClient(settings)
    read_activity = read_activity or ReadActivity()
    budget = RunBudget(max_attempts=24, seconds=settings.run_seconds)
    review = EvidenceReview(moment=parse_run_at(run_at), budget=budget,
                            inventory_reader=inventory_reader, fda_http_get=fda_http_get)
    messages = [{"role": "user", "content": "Run one read-only inventory review for configured store 1618."}]
    tools = claude_tools()
    turns = 0
    called = False

    def failed(code, unavailable=False, safety=None):
        report = mark_manual(review.report(), code, safety)
        return envelope(state="Temporarily Unavailable" if unavailable else "Manual Review",
                        reason=code, report=report, settings=settings,
                        called=called, turns=turns, counts=budget.counts())

    try:
        async with asyncio.timeout(settings.run_seconds):
            while turns < settings.max_turns:
                remaining_ndcs = tuple(ndc for ndc in review.ndcs if ndc not in review.called_ndcs)
                if review.context is None:
                    offered = [tools[0]]
                    choice = {"type": "tool", "name": "read_store_inventory", "disable_parallel_tool_use": True}
                elif remaining_ndcs:
                    offered = [deepcopy(tools[1])]
                    offered[0]["input_schema"]["properties"]["package_ndc"]["enum"] = list(remaining_ndcs)
                    choice = {"type": "any"}
                else:
                    offered, choice = [], None
                    messages.append({"role": "user", "content": "Tool reads are complete. Return the exact JSON report below, built from trusted context. Add nothing.\n" + json.dumps(expected_report(review.context), allow_nan=False)})
                turns += 1
                called = True
                if review.remaining() <= 0:
                    return failed("RUN_DEADLINE_EXCEEDED", unavailable=True)
                response = await provider.complete(messages=deepcopy(messages), tools=offered,
                    choice=choice, timeout=min(settings.model_seconds, review.remaining()))
                if review.remaining() <= 0:
                    return failed("RUN_DEADLINE_EXCEEDED", unavailable=True)
                if type(response) is not dict or type(response.get("content")) is not list:
                    return failed("INVALID_MODEL_RESPONSE")
                blocks = response["content"]
                if not blocks or len(blocks) > 24:
                    return failed("INVALID_MODEL_RESPONSE")
                calls = [block for block in blocks if type(block) is dict and block.get("type") == "tool_use"]
                if calls:
                    # A tool batch must be explicitly identified by the provider.
                    if response.get("stop_reason") != "tool_use":
                        return failed("INVALID_MODEL_STOP")
                    ids = [block.get("id") for block in calls]
                    if any(type(v) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", v) for v in ids) or len(set(ids)) != len(ids):
                        return failed("INVALID_TOOL_REFERENCE")
                    tool_results = []
                    assistant_calls = []
                    for block in calls:
                        call = {"name": block.get("name"), "arguments": block.get("input")}
                        # General permission checks run even for out-of-order/repeated calls.
                        name, args = call["name"], call["arguments"]
                        permission = authorize_tool_call(call, allowed_package_ndcs=review.ndcs)
                        if not permission.allowed:
                            dispatch = execute_guarded(call, executors={}, budget=budget,
                                                       allowed_package_ndcs=review.ndcs)
                            return failed(dispatch.reason_code)
                        if name == "read_store_inventory" and review.context is None:
                            dispatch, safe = await read_activity.execute(review.read_inventory, call)
                        elif name == "get_fda_shortage_context" and review.context is not None and type(args) is dict and args.get("package_ndc") not in review.called_ndcs:
                            dispatch, safe = await read_activity.execute(review.read_fda, call)
                        else:
                            dispatch = execute_guarded(call, executors={}, budget=budget,
                                                       allowed_package_ndcs=review.ndcs)
                            return failed("TOOL_SEQUENCE_REJECTED")
                        if dispatch.state != "COMPLETE" or safe is None:
                            return failed(dispatch.reason_code)
                        assistant_calls.append({"type": "tool_use", "id": block["id"],
                                                "name": name, "input": deepcopy(args)})
                        tool_results.append({"type": "tool_result", "tool_use_id": block["id"],
                                             "content": json.dumps(safe, allow_nan=False)})
                    messages.extend([{"role": "assistant", "content": assistant_calls},
                                     {"role": "user", "content": tool_results}])
                    continue
                if response.get("stop_reason") != "end_turn" or offered:
                    return failed("INCOMPLETE_MODEL_REVIEW")
                if any(type(block) is not dict or block.get("type") != "text" or type(block.get("text")) is not str for block in blocks):
                    return failed("INVALID_MODEL_RESPONSE")
                text = "".join(block["text"] for block in blocks)
                try:
                    proposed = strict_json_loads(text.encode("utf-8"))
                except (ContractError, UnicodeError):
                    proposed = None
                output = validate_report(proposed, context=review.context)
                report = review.report()
                if not output.accepted:
                    return failed(output.reason_code, safety=output.report)
                report["safety_report"] = output.report
                return envelope(state="Manual Review" if report["run_state"] == "MANUAL_REVIEW" else "Live",
                                reason=output.reason_code, report=report, settings=settings,
                                called=called, accepted=True, turns=turns, counts=budget.counts())
            return failed("MODEL_TURN_LIMIT")
    except ProviderUnavailable as error:
        return failed(error.code, unavailable=True)
    except TimeoutError:
        return failed("RUN_DEADLINE_EXCEEDED", unavailable=True)
    except Exception:
        return failed("REVIEW_UNAVAILABLE", unavailable=True)
