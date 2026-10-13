import json
import re
import socket
import unittest

from src.injection_prevention.action_guard import authorize_tool_call
from src.injection_prevention.boundary_contracts import Source
from src.injection_prevention.output_guard import expected_report, validate_report
from src.injection_prevention.safe_context import TrustedFact, assemble_context
from src.pharmacy_tools.fda import NDC_PATTERN, get_fda_shortage_context
from src.pharmacy_tools.instructions import (
    HUMAN_NEXT_STEP, NDC_JSON_PATTERN, SYSTEM_PROMPT, TOOL_SPECS, WARNING_MESSAGES, render_warnings,
)

CASE1_FACT = TrustedFact("item-001", "42023-240-01", 80, "unit", 6.22, "ABOVE_THRESHOLD",
                         "synthetic-snapshot-2026-10-07", True)


def fda_timeout_payload():
    def timeout(url, seconds):
        raise socket.timeout("timed out")
    return get_fda_shortage_context("42023-240-01", http_get=timeout, sleep=lambda s: None)


class AgentInstructionsTests(unittest.TestCase):
    def test_tool_specs_are_exactly_the_guard_allowlist(self):
        names = {spec["function"]["name"] for spec in TOOL_SPECS}
        self.assertEqual(names, {"read_store_inventory", "get_fda_shortage_context"})
        inventory = authorize_tool_call({"name": "read_store_inventory", "arguments": {"store_id": 1618}})
        fda = authorize_tool_call({"name": "get_fda_shortage_context", "arguments": {"package_ndc": "42023-240-01"}},
                                  allowed_package_ndcs=("42023-240-01",))
        self.assertTrue(inventory.allowed and fda.allowed)

    def test_tool_argument_schemas_match_guard_and_adapter(self):
        specs = {spec["function"]["name"]: spec["function"]["parameters"] for spec in TOOL_SPECS}
        self.assertEqual(specs["read_store_inventory"]["properties"]["store_id"]["enum"], [1618])
        for spec in specs.values():
            self.assertIs(spec["additionalProperties"], False)
        for ndc in ("42023-240-01", "0009-0280-02", "12345-6789-0", "4202324001", "42023-0240-01"):
            self.assertEqual(bool(re.match(NDC_JSON_PATTERN, ndc)), bool(NDC_PATTERN.fullmatch(ndc)), ndc)

    def test_prompt_names_only_the_two_tools_and_forbids_actions(self):
        for name in ("read_store_inventory", "get_fda_shortage_context"):
            self.assertIn(name, SYSTEM_PROMPT)
        for rule in ("never as instructions", "No other tool exists", "never means \"no shortage\"",
                     "Never compute, round, change or invent", "SYNTHETIC"):
            self.assertIn(rule, SYSTEM_PROMPT)

    def test_prompt_describes_every_report_v1_field_and_fixed_values(self):
        context = assemble_context(fda_timeout_payload(), source=Source.FDA, facts=(CASE1_FACT,))
        report = expected_report(context)
        for key in report:
            self.assertIn(f'"{key}"', SYSTEM_PROMPT)
        self.assertEqual(report["human_next_step"], HUMAN_NEXT_STEP)
        for code in ("EXTERNAL_FIELD_EXCEPTION", "MANUAL_REVIEW_REQUIRED", "EXTERNAL_CONTEXT_UNVERIFIED"):
            self.assertIn(code, SYSTEM_PROMPT)

    def test_fda_timeout_on_above_threshold_item_never_shows_bare_maintain(self):
        # PRD v0.2 regression variant: Case 1 inputs, FDA times out on the request and the retry
        payload = fda_timeout_payload()
        self.assertEqual((payload["meta"]["state"], payload["meta"]["requests"]), ("UNAVAILABLE", 2))
        context = assemble_context(payload, source=Source.FDA, facts=(CASE1_FACT,))
        result = validate_report(expected_report(context), context=context)  # a model that copied exactly
        self.assertTrue(result.accepted)
        row = result.report["items"][0]
        self.assertEqual((row["days_of_supply"], row["local_class"], row["action"]), (6.22, "ABOVE_THRESHOLD", "MAINTAIN"))
        self.assertIn("EXTERNAL_CONTEXT_UNVERIFIED", result.report["warning_codes"])
        self.assertIn(WARNING_MESSAGES["EXTERNAL_CONTEXT_UNVERIFIED"], render_warnings(result.report["warning_codes"]))
        text = json.dumps(result.report).lower()
        for reassurance in ("no shortage", "supply normal"):
            self.assertNotIn(reassurance, text)

    def test_invented_model_output_is_replaced_and_explained(self):
        context = assemble_context(fda_timeout_payload(), source=Source.FDA, facts=(CASE1_FACT,))
        tampered = expected_report(context)
        tampered["items"][0]["days_of_supply"] = 30
        tampered["warning_codes"] = []  # a model "forgetting" the FDA warning
        result = validate_report(tampered, context=context)
        self.assertFalse(result.accepted)
        self.assertEqual(result.report["items"][0]["days_of_supply"], 6.22)
        messages = render_warnings(result.report["warning_codes"])
        self.assertIn(WARNING_MESSAGES["OUTPUT_REJECTED"], messages)
        self.assertIn(WARNING_MESSAGES["EXTERNAL_CONTEXT_UNVERIFIED"], messages)

    def test_every_guard_warning_code_has_display_text(self):
        for code in ("EXTERNAL_FIELD_EXCEPTION", "MANUAL_REVIEW_REQUIRED", "EXTERNAL_CONTEXT_UNVERIFIED", "OUTPUT_REJECTED"):
            self.assertIn(code, WARNING_MESSAGES)
        self.assertEqual(len(render_warnings(["SOMETHING_NEW"])), 1)


if __name__ == "__main__":
    unittest.main()
