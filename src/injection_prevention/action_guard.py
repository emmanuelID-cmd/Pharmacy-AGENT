"""Fixed pre-dispatch read permission guard and bounded execution helper."""
from dataclasses import dataclass, field
import math
import re
import threading
import time
from .boundary_contracts import ContractError, validate_tree
from .safe_context import inspect_payload
from .boundary_contracts import Source
from .contracts import Decision


@dataclass(frozen=True)
class CallDecision:
    allowed: bool
    reason_code: str
    tool_reference: str


def authorize_tool_call(call: object, *, allowed_package_ndcs: tuple[str,...] = ()) -> CallDecision:
    if type(allowed_package_ndcs) is not tuple or len(allowed_package_ndcs)>20 or any(type(v) is not str or not re.fullmatch(r'(?:\d{4}-\d{4}-\d{2}|\d{5}-\d{3}-\d{2}|\d{5}-\d{4}-\d{1})',v,flags=re.ASCII) for v in allowed_package_ndcs):
        raise ContractError('INVALID_TOOL_POLICY')
    deny=lambda code,tool='unknown_tool':CallDecision(False,code,tool)
    try: validate_tree(call)
    except ContractError:return deny('INVALID_CALL')
    if type(call) is not dict or set(call)!={'name','arguments'} or type(call['name']) is not str or type(call['arguments']) is not dict:
        return deny('INVALID_CALL')
    name=call['name'];args=call['arguments']
    if name=='read_store_inventory':
        if set(args)=={'store_id'} and type(args['store_id']) is int and args['store_id']==1618:
            return CallDecision(True,'SCOPED_READ',name)
        return deny('INVALID_STORE_ARGUMENTS',name)
    if name=='get_fda_shortage_context':
        if set(args)=={'package_ndc'} and type(args['package_ndc']) is str and args['package_ndc'] in allowed_package_ndcs:
            return CallDecision(True,'SCOPED_READ',name)
        return deny('INVALID_PACKAGE_ARGUMENTS',name)
    return deny('TOOL_NOT_ALLOWED')


class RunBudget:
    """Trusted runtime configuration. Enforces entry and return deadlines.

    Blocking adapter IO still needs its own timeout; this helper cannot kill
    arbitrary Python callbacks. Do not expose the clock/limits as user input.
    """
    def __init__(self, max_attempts=100, seconds=120, clock=time.monotonic):
        if type(max_attempts) is not int or not 1<=max_attempts<=100 or type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<seconds<=120:
            raise ContractError('INVALID_RUN_BUDGET')
        self.max_attempts=max_attempts;self.seconds=seconds;self.clock=clock
        self.started=clock();self.attempted=0;self.denied=0;self.dispatched=0;self.completed=0
        self.lock=threading.RLock()

    def expired(self):
        return self.clock()-self.started>=self.seconds

    def counts(self):
        with self.lock:
            return {k:getattr(self,k) for k in ('attempted','denied','dispatched','completed')}


@dataclass(frozen=True)
class DispatchResult:
    state: str
    reason_code: str
    tool_reference: str
    counts: dict
    tool_assessment: dict | None = None


def execute_guarded(call, *, executors: dict, budget: RunBudget, allowed_package_ndcs: tuple = ()) -> DispatchResult:
    """A trusted caller owns the fixed callbacks/credentials, never model input.

    This helper returns only a safe assessment. The actual harness separately
    manages read results/numeric validation; no external data is made trusted.
    """
    if type(budget) is not RunBudget or type(executors) is not dict:
        raise ContractError('TRUSTED_EXECUTION_CONFIGURATION_REQUIRED')
    # Capture only exact built-in containers. Allowed arguments are immutable
    # scalar values; never dispatch from the caller's mutable object again.
    snapshot=None
    try:
        if type(call) is dict and set(call)=={'name','arguments'}:
            name=call['name'];arguments=call['arguments']
            if type(arguments) is dict:
                snapshot={'name':name,'arguments':dict(arguments)}
    except (KeyError,RuntimeError):
        pass
    decision=authorize_tool_call(snapshot,allowed_package_ndcs=allowed_package_ndcs)
    with budget.lock:
        budget.attempted+=1
        if budget.attempted>budget.max_attempts or budget.expired():
            budget.denied+=1
            return DispatchResult('MANUAL_REVIEW','RUN_BUDGET_EXHAUSTED',decision.tool_reference,budget.counts())
        if not decision.allowed:
            budget.denied+=1
            return DispatchResult('DENIED',decision.reason_code,decision.tool_reference,budget.counts())
        executor=executors.get(decision.tool_reference)
        if not callable(executor):
            budget.denied+=1
            return DispatchResult('MANUAL_REVIEW','READ_ADAPTER_UNAVAILABLE',decision.tool_reference,budget.counts())
        budget.dispatched+=1
    try:
        raw=executor(**dict(snapshot['arguments']))
        assessment=inspect_payload(raw,source=Source.INVENTORY if decision.tool_reference=='read_store_inventory' else Source.FDA)
    except Exception:
        return DispatchResult('MANUAL_REVIEW','READ_FAILED_OR_UNAVAILABLE',decision.tool_reference,budget.counts())
    with budget.lock:
        if budget.expired():
            return DispatchResult('MANUAL_REVIEW','RUN_DEADLINE_EXCEEDED',decision.tool_reference,budget.counts())
        budget.completed+=1
    return DispatchResult('COMPLETE' if assessment.source_contract_valid else 'MANUAL_REVIEW',
                          'READ_INSPECTED' if assessment.source_contract_valid else 'INVALID_TOOL_RESULT',
                          decision.tool_reference,budget.counts(),assessment.safe_summary())
