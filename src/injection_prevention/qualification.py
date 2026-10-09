"""Synthetic regression counts keep detection misses separate from containment."""
import json
from pathlib import Path
from .contracts import Decision
from .label_detector import detect_label
from .boundary_contracts import Source, ContractError, opaque_reference
from .safe_context import TrustedFact, assemble_context


def qualification_report():
    root=Path(__file__).resolve().parents[2]
    files=(root/'tests/fixtures/labels.json',root/'tests/fixtures/phase6_labels.json')
    rows=[]
    for file in files:
        try:
            if file.stat().st_size>1024*1024:raise ValueError()
            cases=json.loads(file.read_text(encoding='utf-8'))
            if type(cases) is not list or not 1<=len(cases)<=1000:raise ValueError()
            if any(type(c) is not dict or not opaque_reference(c.get('id')) or
                   c.get('expected') not in ('ACCEPT','FLAG','REJECT','BLOCK') or 'label' not in c for c in cases):raise ValueError()
            if len({c['id'] for c in cases})!=len(cases):raise ValueError()
        except (OSError,UnicodeError,ValueError,TypeError,RecursionError):
            raise ContractError('QUALIFICATION_UNAVAILABLE') from None
        for case in cases:
            result=detect_label(case['label'],item_reference=case['id'])
            attack=case['expected']!='ACCEPT'
            detected=result.decision!=Decision.ACCEPT
            expected_ok=detected if case['expected']=='BLOCK' else result.decision.value==case['expected']
            outcome=('DETECTED' if detected else 'MISSED') if attack else ('FALSE_POSITIVE' if detected else 'BENIGN_ACCEPTED')
            payload={'store_id':1618,'synthetic':True,'items':[{'item_id':'item-A','product_label':case['label']}]}
            fact=TrustedFact('item-A','0001-0123-01',80,'tablet',6.22,'ABOVE_THRESHOLD','snapshot-A',True)
            context=assemble_context(payload,source=Source.INVENTORY,facts=(fact,))
            contained=context['external_text_included'] is False and not any('product_label' in row or 'notes' in row for row in context['items'])
            rows.append({'case_id':file.stem+':'+case['id'],'expected':case['expected'],
                         'decision':result.decision.value,'detection_outcome':outcome,
                         'expectation_met':expected_ok,'external_text_excluded':contained,
                         'reason_codes':[f.reason_code for f in result.findings],
                         'pattern_ids':[f.pattern_id for f in result.findings if f.pattern_id]})
    return {'synthetic_only':True,'cases':len(rows),'expected_agreement':sum(r['expectation_met'] for r in rows),
            'detected':sum(r['detection_outcome']=='DETECTED' for r in rows),
            'misses':sum(r['detection_outcome']=='MISSED' for r in rows),
            'false_positives':sum(r['detection_outcome']=='FALSE_POSITIVE' for r in rows),
            'benign_accepted':sum(r['detection_outcome']=='BENIGN_ACCEPTED' for r in rows),
            'contained_cases':sum(r['external_text_excluded'] for r in rows),
            'results':rows,'limitations':['Selected fixture agreement is not a universal detection rate.',
                                         'No live model, inventory API, FDA API or production harness exercised.']}


def main():
    try:report=qualification_report()
    except (ContractError,ValueError,TypeError,KeyError):
        print(json.dumps({'state':'MANUAL_REVIEW','reason_code':'QUALIFICATION_UNAVAILABLE'}))
        return 2
    print(json.dumps(report,indent=2))
    return 0 if report['expected_agreement']==report['cases'] and report['misses']==0 and report['false_positives']==0 else 1


if __name__=='__main__':raise SystemExit(main())
