import unittest
from copy import deepcopy
from src.injection_prevention.boundary_contracts import ContractError
from src.injection_prevention.demo import SAMPLES, run_demo
from src.injection_prevention.qualification import qualification_report


class DemoTests(unittest.TestCase):
    def test_all_presets_use_real_controls_and_no_writes(self):
        for preset in SAMPLES:
            request={k:v for k,v in preset.items() if k not in {'id','name'}}
            result=run_demo(request)
            self.assertTrue(result['synthetic_only'])
            self.assertFalse(result['model_context']['external_text_included'])
            self.assertEqual(result['simulated_operational_write_effects'],0)
            self.assertTrue(result['output_guard']['accepted'])
            if preset['id']=='request':
                self.assertEqual(result['permission_guard']['state'],'DENIED')
                self.assertEqual(result['simulated_executor_calls'],[])
            if preset['id']=='missing':
                self.assertEqual(result['model_context']['run_state'],'MANUAL_REVIEW')
            if preset['id']=='normal':self.assertEqual(result['detector']['decision'],'ACCEPT')
            if preset['id'] in {'hidden','paraphrase','authority','lookalike','encoded','split','fda','request','media'}:
                self.assertNotEqual(result['detector']['decision'],'ACCEPT')
            if preset['id']=='hidden':
                self.assertTrue(any('U+200B' in v['visible_text'] for v in result['human_inspection']))

    def test_output_tampering_and_bad_request_contract(self):
        sample=deepcopy(SAMPLES[1]);base={k:v for k,v in sample.items() if k not in {'id','name'}}
        for change in ('alter_days','hide_warnings','claim_order'):
            result=run_demo(dict(base,output_change=change))
            self.assertFalse(result['output_guard']['accepted'])
            self.assertEqual(result['output_guard']['report']['items'][0]['days_of_supply'],6.22)
            self.assertFalse(result['output_guard']['report']['order_placed'])
        for extras in ({'source':'fake'},{'evidence_mode':True},{'previous_payloads':{}},{'output_change':{}},{'proposed_report':[], 'output_change':'alter_days'}):
            with self.assertRaises(ContractError):run_demo(dict(base,**extras))

    def test_regression_counts_misses_separately_from_containment(self):
        report=qualification_report()
        self.assertEqual(report['cases'],85)
        self.assertEqual(report['expected_agreement'],85)
        self.assertEqual(report['misses'],0)
        self.assertEqual(report['false_positives'],0)
        self.assertEqual(report['contained_cases'],85)
        self.assertEqual(report['detected']+report['benign_accepted'],85)
