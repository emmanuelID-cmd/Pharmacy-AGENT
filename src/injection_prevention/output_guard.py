"""Exact structured report validation. Arbitrary model prose is not approved."""
from dataclasses import dataclass
import json
from .boundary_contracts import ContractError, validate_tree


@dataclass(frozen=True)
class OutputResult:
    accepted: bool
    reason_code: str
    report: dict


def expected_report(context: dict) -> dict:
    """Only pass context made by assemble_context in trusted application code."""
    if type(context) is not dict or context.get('schema_version')!='prevention-v1':
        raise ContractError('TRUSTED_CONTEXT_REQUIRED')
    # Audit exception metadata is deeper than input; report facts stay bounded.
    validate_tree({'items':context.get('items'),'run_state':context.get('run_state'),
                   'external_context':context.get('external_context')})
    if context.get('authority')!='HUMAN_EXECUTION_ONLY' or context.get('external_text_included') is not False:
        raise ContractError('INVALID_CONTEXT_AUTHORITY')
    warnings=[]
    if context['exceptions']: warnings.append('EXTERNAL_FIELD_EXCEPTION')
    if context['run_state']=='MANUAL_REVIEW':warnings.append('MANUAL_REVIEW_REQUIRED')
    if context['external_context']['state']!='VERIFIED':warnings.append('EXTERNAL_CONTEXT_UNVERIFIED')
    return {'schema_version':'report-v1','data_mode':'SYNTHETIC','store_id':1618,
            'items':[dict(row) for row in context['items']],
            'warning_codes':warnings,'run_state':context['run_state'],
            'external_context':dict(context['external_context']),
            'human_next_step':'Verify evidence and execute any operational action outside the agent.',
            'order_placed':False,'inventory_changed':False}


def validate_report(proposed: object, *, context: dict) -> OutputResult:
    expected=expected_report(context)
    valid=False
    try:
        validate_tree(proposed)
        valid=(type(proposed) is dict and json.dumps(proposed,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False))
    except (ContractError,ValueError,TypeError):
        pass
    if valid:return OutputResult(True,'VERIFIED_STRUCTURED_OUTPUT',expected)
    # Use only deterministic facts and safe warnings; never return rejected prose.
    expected['warning_codes'].append('OUTPUT_REJECTED')
    expected['run_state']='MANUAL_REVIEW'
    return OutputResult(False,'OUTPUT_EVIDENCE_MISMATCH',expected)
