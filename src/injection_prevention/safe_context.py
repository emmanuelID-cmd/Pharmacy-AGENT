"""Minimal context from harness facts; external free text never enters it."""
from dataclasses import dataclass
import math
import re
from .boundary_contracts import ContractError, Limits, Source, opaque_reference, validate_tree
from .contracts import Decision
from .label_detector import detect_label
from .text_detector import inspect_text


@dataclass(frozen=True)
class TrustedFact:
    """Construct only in trusted harness code, never deserialize a tool/user object.

    These checks validate shape, not pharmacy accuracy or source authenticity.
    Classification/calculation and policy approval remain the harness's work.
    """
    item_reference: str
    package_ndc: str
    usable_quantity: float
    dispensing_unit: str
    days_of_supply: float | None
    local_class: str
    evidence_reference: str
    verified: bool = False

    def __post_init__(self):
        if not opaque_reference(self.item_reference) or not opaque_reference(self.evidence_reference):
            raise ContractError("INVALID_EVIDENCE_REFERENCE")
        if type(self.package_ndc) is not str or not re.fullmatch(r"(?:\d{4}-\d{4}-\d{2}|\d{5}-\d{3}-\d{2}|\d{5}-\d{4}-\d{1})",self.package_ndc,flags=re.ASCII):
            raise ContractError("INVALID_EVIDENCE_NDC")
        if type(self.dispensing_unit) is not str or self.dispensing_unit not in {"tablet","capsule","mL","unit"}:
            raise ContractError("INVALID_EVIDENCE_UNIT")
        for index,number in enumerate((self.usable_quantity,self.days_of_supply)):
            if index==1 and number is None:
                continue
            if type(number) not in (int,float) or not math.isfinite(number) or not 0<=number<=10**9:
                raise ContractError("INVALID_EVIDENCE_NUMBER")
        if type(self.verified) is not bool or type(self.local_class) is not str or self.local_class not in {"ABOVE_THRESHOLD","LOW","CRITICAL","UNKNOWN"}:
            raise ContractError("INVALID_EVIDENCE_STATE")
        if self.days_of_supply is None and self.local_class!='UNKNOWN':
            raise ContractError("UNKNOWN_DURATION")

    def as_context(self):
        valid=self.verified and self.local_class!='UNKNOWN' and self.days_of_supply is not None
        return {"item_reference":self.item_reference,"package_ndc":self.package_ndc,
                "usable_quantity":self.usable_quantity,"dispensing_unit":self.dispensing_unit,
                "days_of_supply":self.days_of_supply if self.verified else None,
                "local_class":self.local_class if self.verified else 'UNKNOWN',
                "evidence_reference":self.evidence_reference,"review_permitted":valid,
                "action":('MAINTAIN' if self.local_class=='ABOVE_THRESHOLD' else 'REVIEW') if valid else 'MANUAL_REVIEW'}


@dataclass(frozen=True)
class Assessment:
    decision: Decision
    source: Source
    source_contract_valid: bool
    findings: tuple[dict,...]
    inspected_text_fields: int = 0

    def safe_summary(self):
        return {"decision":self.decision.value,"source":self.source.value,
                "source_contract_valid":self.source_contract_valid,
                "findings":list(self.findings),"inspected_text_fields":self.inspected_text_fields}


_INVENTORY_TOP={'store_id','synthetic','snapshot_reference','snapshot_timestamp','policy_version','items'}
_ITEM_KEYS={'item_id','package_ndc','product_label','strength','dosage_form','package_quantity',
            'package_unit','dispensing_unit','usable_quantity','daily_usage','item_policy',
            'reconciliation_state','exceptions','notes'}
_POLICY_KEYS={'low_days','critical_days','version','approval','effective_at','expires_at'}
_FDA_KEYS={'package_ndc','generic_name','availability','related_info','update_date','therapeutic_category',
           'dosage_form','presentation','company_name','shortage_reason','status'}


def _source_shape(payload, source, limits):
    if type(payload) is not dict:
        raise ContractError('INVALID_SOURCE_OBJECT')
    if source==Source.USER_REQUEST:
        if set(payload)!={'request'} or type(payload['request']) is not str:
            raise ContractError('INVALID_REQUEST_CONTRACT')
        return
    keys=_INVENTORY_TOP if source==Source.INVENTORY else {'results','meta'}
    if not set(payload)<=keys:
        raise ContractError('UNEXPECTED_SOURCE_FIELD')
    rows=payload.get('items' if source==Source.INVENTORY else 'results')
    if type(rows) is not list or len(rows)>limits.max_rows:
        raise ContractError('INVALID_ROW_COUNT')
    if source==Source.INVENTORY:
        if type(payload.get('store_id')) is not int or payload['store_id']!=1618 or payload.get('synthetic') is not True:
            raise ContractError('INVALID_STORE_SCOPE')
    ids=set()
    for row in rows:
        if type(row) is not dict or not set(row)<=(_ITEM_KEYS if source==Source.INVENTORY else _FDA_KEYS):
            raise ContractError('INVALID_ROW_CONTRACT')
        if source==Source.FDA:
            for key,value in row.items():
                if key=='package_ndc' and type(value) is list and all(type(v) is str for v in value):
                    continue
                if type(value) is not str:
                    raise ContractError('UNSUPPORTED_FDA_FIELD_TYPE')
        if source==Source.INVENTORY:
            ref=row.get('item_id')
            if not opaque_reference(ref) or ref in ids:
                raise ContractError('INVALID_ITEM_REFERENCE')
            ids.add(ref)
            if 'item_policy' in row and (type(row['item_policy']) is not dict or not set(row['item_policy'])<=_POLICY_KEYS):
                raise ContractError('INVALID_POLICY_CONTRACT')
            for key in ('notes','product_label','strength','dosage_form','dispensing_unit','package_unit'):
                if key in row and type(row[key]) is not str:
                    raise ContractError('UNSUPPORTED_FIELD_TYPE')


def inspect_payload(payload: object, *, source: Source, limits: Limits = Limits(), previous_payloads: tuple = ()) -> Assessment:
    """Raw records are data only. Results contain no original/decoded text."""
    if type(source) is not Source or type(limits) is not Limits or type(previous_payloads) is not tuple:
        raise ContractError('INVALID_INTAKE_CONFIGURATION')
    strings=[]
    labels=[]
    try:
        validate_tree([*previous_payloads,payload],limits)
        for record in (*previous_payloads,payload):
            _source_shape(record,source,limits)
            if source==Source.INVENTORY:
                labels.extend(row['product_label'] for row in record['items'] if 'product_label' in row)
            def collect(node):
                if type(node) is str and node.strip():
                    strings.append(node)
                elif type(node) is dict:
                    for child in node.values(): collect(child)
                elif type(node) is list:
                    for child in node: collect(child)
            collect(record)
    except ContractError as error:
        return Assessment(Decision.REJECT,source,False,({'reason_code':str(error),'correction':'Correct the source contract; manual review required.'},))
    findings=[]
    decisions=[]
    for index,label in enumerate(labels):
        result=detect_label(label,item_reference=f'label-{index}',source=source.value)
        decisions.append(result.decision)
        if result.decision!=Decision.ACCEPT:
            findings.append(result.safe_summary())
    for index,text in enumerate(strings):
        result=inspect_text(text,item_reference=f'field-{index}',source=source.value)
        decisions.append(result.decision)
        if result.decision!=Decision.ACCEPT:
            findings.append(result.safe_summary())
    # Cross-field/record/turn signals, bounded by the same total text budget.
    combined=' '.join(strings)
    if combined:
        from .patterns import matched_patterns
        if len(combined)>4096:
            return Assessment(Decision.REJECT,source,False,({'reason_code':'COMBINED_TEXT_LIMIT','correction':'Reduce the source batch; manual review required.'},),len(strings))
        patterns=matched_patterns(combined)
        if patterns:
            decisions.append(Decision.FLAG)
            findings.append({'reason_code':'COMBINED_TEXT_SIGNAL','pattern_ids':[p.pattern_id for p in patterns],
                             'correction':'Review combined external records; no text is forwarded.'})
    if Decision.REJECT in decisions:
        decision=Decision.REJECT
    elif Decision.FLAG in decisions:
        decision=Decision.FLAG
    else:
        decision=Decision.ACCEPT
    return Assessment(decision,source,True,tuple(findings),len(strings))


def assemble_context(payload: object, *, source: Source, facts: tuple[TrustedFact,...], previous_payloads: tuple = ()) -> dict:
    """Public import boundary. No tool-provided result, fact or flag is trusted."""
    if type(facts) is not tuple or len(facts)>20 or any(type(f) is not TrustedFact for f in facts):
        raise ContractError('TRUSTED_FACTS_REQUIRED')
    if len({f.item_reference for f in facts})!=len(facts):
        raise ContractError('DUPLICATE_TRUSTED_ITEM')
    assessment=inspect_payload(payload,source=source,previous_payloads=previous_payloads)
    rows=[fact.as_context() for fact in facts]
    if source==Source.INVENTORY:
        source_rows={r['item_id']:r for r in payload['items']} if assessment.source_contract_valid else {}
        for row in rows:
            matched=source_rows.get(row['item_reference'])
            if matched is None or ('package_ndc' in matched and matched['package_ndc']!=row['package_ndc']):
                row.update(review_permitted=False,action='MANUAL_REVIEW',days_of_supply=None,
                           local_class='UNKNOWN',usable_quantity=None,
                           evidence_state='IDENTITY_UNVERIFIED')
    if source==Source.USER_REQUEST and assessment.decision!=Decision.ACCEPT:
        for row in rows:
            row.update(review_permitted=False,action='MANUAL_REVIEW')
    if not rows:
        state='MANUAL_REVIEW'
    elif any(not row['review_permitted'] for row in rows):
        state='MANUAL_REVIEW'
    else:
        state='READY_FOR_HUMAN_REVIEW'
    return {'schema_version':'prevention-v1','store_id':1618,'data_mode':'SYNTHETIC',
            'items':rows,'run_state':state,'external_text_included':False,
            'exceptions':[] if assessment.decision==Decision.ACCEPT else [assessment.safe_summary()],
            'external_context':{'label':'External supporting context - national shortage signal',
                                'state':'NOT_ENRICHED' if source!=Source.FDA else ('UNAVAILABLE' if not assessment.source_contract_valid else 'UNVERIFIED')},
            'authority':'HUMAN_EXECUTION_ONLY'}
