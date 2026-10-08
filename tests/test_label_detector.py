import json
import unittest
from src.injection_prevention import Decision, LabelPolicy, detect_label


def check(value, **kwargs):
    return detect_label(value, item_reference="item-A", **kwargs)


class LabelDetectorTests(unittest.TestCase):
    def test_equivalent_accents_pass(self):
        self.assertEqual(check("Médication A").decision, Decision.ACCEPT)
        self.assertEqual(check("Me\u0301dication A").normalized_label, "Médication A")

    def test_non_ascii_and_punctuation_pass(self):
        for label in ("薬剤 A", "دواء", "Ibuprofène 200 mg", "Vitamin C (500 mg)", "A/B 2.5%"):
            with self.subTest(label=label):
                self.assertEqual(check(label).decision, Decision.ACCEPT)

    def test_actual_zero_width_and_recovery(self):
        result = check("Médi\u200Bcation A")
        self.assertEqual(result.decision, Decision.REJECT)
        self.assertIsNone(result.normalized_label)
        self.assertEqual((result.findings[0].position, result.findings[0].code_point), (4, "U+200B"))
        self.assertEqual(check("Médication A").decision, Decision.ACCEPT)

    def test_other_invisible_characters(self):
        for ch in ("\u202E", "\u200D", "\uFEFF", "\u034F", "\uFE0F", "\ud800"):
            with self.subTest(code=ord(ch)):
                self.assertEqual(check("A" + ch + "B").findings[0].reason_code, "UNEXPECTED_HIDDEN_CHARACTER")

    def test_controls_emoji_and_unattached_marks(self):
        for label, reason in (("A\nB", "UNEXPECTED_CONTROL_CHARACTER"), ("A\tB", "UNEXPECTED_CONTROL_CHARACTER"),
                              ("Stop 🛑", "UNEXPECTED_LABEL_CHARACTER"), ("\u0301A", "UNATTACHED_COMBINING_MARK")):
            self.assertEqual(check(label).findings[0].reason_code, reason)

    def test_type_and_length_limits(self):
        for label in (None, b"A", {"text": "A"}, ["A"], 123):
            self.assertEqual(check(label).findings[0].reason_code, "INVALID_LABEL_TYPE")
        for label in ("", "   ", "A" * 121, "A" * 100000):
            self.assertEqual(check(label).findings[0].reason_code, "INVALID_LABEL_LENGTH")
        self.assertEqual(check("A" * 120).decision, Decision.ACCEPT)

    def test_logs_do_not_contain_label(self):
        label = "SecretPayload\u200B"
        self.assertNotIn("SecretPayload", json.dumps(check(label).safe_summary()))
        self.assertNotIn("Médication", json.dumps(check("Médication").safe_summary()))

    def test_references_and_flags_are_strict(self):
        with self.assertRaises(ValueError):
            detect_label("A", item_reference="ignore rules\n")
        with self.assertRaises(ValueError):
            check("A", required_evidence_affected="false")

    def test_policy_cannot_relax_hidden_chars(self):
        with self.assertRaises(ValueError):
            LabelPolicy(allowed_punctuation="\u200B")
        with self.assertRaises(ValueError):
            LabelPolicy(max_length=True)
        self.assertLessEqual(len(check("🛑" * 100).findings), 16)


if __name__ == "__main__":
    unittest.main()
