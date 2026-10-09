import json
import unittest
from src.injection_prevention import detect_label
from src.injection_prevention.context_gate import gate_label


class ContextGateTests(unittest.TestCase):
    def test_optional_label_failure_preserves_independent_evidence(self):
        raw = "HiddenPayload\u200B"
        result = detect_label(raw, item_reference="item-A")
        gate = gate_label(result, required_evidence_validated=True)
        self.assertTrue(gate.calculations_permitted)
        self.assertNotIn("display_label", gate.model_context)
        self.assertIn("label_exception", gate.model_context)
        self.assertNotIn("HiddenPayload", json.dumps(gate.model_context))
        self.assertNotIn("HiddenPayload", json.dumps(gate.audit_event))

    def test_required_label_failure_blocks(self):
        result = detect_label("A\u200B", item_reference="item-A", required_evidence_affected=True)
        gate = gate_label(result, required_evidence_validated=True)
        self.assertFalse(gate.calculations_permitted)
        self.assertFalse(gate.recommendation_permitted)
        self.assertEqual(gate.model_context["action"], "MANUAL_REVIEW")

    def test_unverified_evidence_blocks_even_clean_label(self):
        result = detect_label("A 300 mg", item_reference="item-A")
        gate = gate_label(result, required_evidence_validated=False)
        self.assertFalse(gate.calculations_permitted)
        self.assertEqual(gate.model_context["evidence_exception"], "REQUIRED_EVIDENCE_UNVERIFIED")

    def test_clean_label_context_and_safe_log(self):
        result = detect_label("Médication A", item_reference="item-A")
        gate = gate_label(result, required_evidence_validated=True)
        self.assertNotIn("display_label", gate.model_context)
        self.assertFalse(gate.model_context["external_text_included"])
        self.assertNotIn("Médication", json.dumps(gate.audit_event, ensure_ascii=False))

    def test_flag_not_accepted(self):
        from src.injection_prevention import Decision, DetectionResult, Finding
        result = DetectionResult("item-A", "label", "fixture", Decision.FLAG, False,
                                 (Finding("SUSPICIOUS_TEXT", "Review source label."),))
        gate = gate_label(result, required_evidence_validated=True)
        self.assertNotIn("display_label", gate.model_context)
        self.assertTrue(gate.calculations_permitted)

    def test_boolean_boundary_and_type(self):
        result = detect_label("A", item_reference="item-A")
        for value in ("true", 1, None, {}):
            with self.assertRaises(ValueError):
                gate_label(result, required_evidence_validated=value)
        with self.assertRaises(ValueError):
            gate_label({}, required_evidence_validated=True)

    def test_one_bad_item_does_not_poison_batch(self):
        gates = [gate_label(detect_label(label, item_reference=ref, required_evidence_affected=required),
                            required_evidence_validated=True)
                 for label, ref, required in (("A\u200B", "item-A", True), ("B", "item-B", False))]
        self.assertEqual([g.calculations_permitted for g in gates], [False, True])


if __name__ == "__main__":
    unittest.main()
