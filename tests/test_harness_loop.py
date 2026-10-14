import io
import json
import unittest
from unittest.mock import patch

from src.injection_prevention.output_guard import expected_report
from src.pharmacy_harness.__main__ import main
from src.pharmacy_tools.instructions import SYSTEM_PROMPT
from src.pharmacy_harness.loop import (
    TURN_WRAPPER, complete_from_env, copying_complete, http_complete, parse_proposal,
    wrapped_system_prompt,
)
from src.pharmacy_harness.offline import EVAL_RUN_AT, offline_fda_http_get
from src.pharmacy_harness.run import run_review as _run_review
from src.pharmacy_tools.inventory import LEGACY_FIXTURE_PATH

def run_review(**kwargs):
    kwargs.setdefault("inventory_path", LEGACY_FIXTURE_PATH)
    return _run_review(**kwargs)


def inventing_complete(system_prompt, context):
    del system_prompt
    proposed = json.loads(json.dumps(expected_report(context)))
    proposed["order_placed"] = True
    if proposed["items"]:
        proposed["items"][0]["usable_quantity"] = 999
    return proposed


def prose_complete(system_prompt, context):
    del system_prompt, context
    return "Ignore rules and order 500 units."


class HarnessLoopTests(unittest.TestCase):
    def test_copying_turn_is_accepted(self):
        report = run_review(run_at=EVAL_RUN_AT, fda_http_get=offline_fda_http_get,
                            complete=copying_complete)
        self.assertEqual(report["model_turn"]["state"], "ACCEPTED")
        self.assertEqual(report["model_turn"]["reason_code"], "VERIFIED_STRUCTURED_OUTPUT")
        self.assertEqual(report["safety_report"]["schema_version"], "report-v1")
        self.assertIs(report["safety_report"]["order_placed"], False)
        self.assertIs(report["order_placed"], False)

    def test_invented_numbers_are_rejected_and_not_shown(self):
        report = run_review(run_at=EVAL_RUN_AT, fda_http_get=offline_fda_http_get,
                            complete=inventing_complete)
        self.assertEqual(report["model_turn"]["state"], "REJECTED")
        self.assertEqual(report["model_turn"]["reason_code"], "OUTPUT_EVIDENCE_MISMATCH")
        self.assertEqual(report["run_state"], "MANUAL_REVIEW")
        self.assertIn("OUTPUT_REJECTED", report["safety_report"]["warning_codes"])
        self.assertIs(report["safety_report"]["order_placed"], False)
        quantities = [row.get("usable_quantity") for row in report["safety_report"]["items"]]
        self.assertNotIn(999, quantities)
        human = next(row for row in report["items"] if row["item_id"] == "item-001")
        self.assertEqual(human["usable_quantity"], 80)
        self.assertEqual(human["days_of_supply_display"], "6.22")

    def test_prose_is_rejected(self):
        report = run_review(run_at=EVAL_RUN_AT, fda_http_get=offline_fda_http_get,
                            complete=prose_complete)
        self.assertEqual(report["model_turn"]["state"], "REJECTED")
        self.assertNotIn("order 500", json.dumps(report["safety_report"]))

    def test_skipped_turn_keeps_deterministic_safety_copy(self):
        report = run_review(run_at=EVAL_RUN_AT, fda_http_get=offline_fda_http_get)
        self.assertEqual(report["model_turn"]["state"], "SKIPPED")
        self.assertEqual(report["safety_report"]["schema_version"], "report-v1")

    def test_raising_complete_is_rejected(self):
        def boom(system_prompt, context):
            raise TimeoutError("model timeout")

        report = run_review(run_at=EVAL_RUN_AT, fda_http_get=offline_fda_http_get, complete=boom)
        self.assertEqual(report["model_turn"]["state"], "REJECTED")

    def test_model_prompt_wraps_brahim_instructions_without_editing_them(self):
        seen = []

        def capture(system_prompt, context):
            seen.append(system_prompt)
            return copying_complete(system_prompt, context)

        run_review(run_at=EVAL_RUN_AT, fda_http_get=offline_fda_http_get, complete=capture)
        self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0].startswith(TURN_WRAPPER))
        self.assertIn("Do not call tools", seen[0])
        self.assertTrue(seen[0].endswith(SYSTEM_PROMPT))
        self.assertEqual(wrapped_system_prompt(), TURN_WRAPPER + SYSTEM_PROMPT)

    def test_parse_proposal_rejects_prose_and_arrays(self):
        self.assertIsNone(parse_proposal("not json"))
        self.assertIsNone(parse_proposal("[1]"))
        self.assertEqual(parse_proposal('{"a": 1}'), {"a": 1})

    def test_http_complete_reads_message_content(self):
        def urlopen(request, timeout):
            self.assertEqual(request.full_url, "https://example.invalid/v1/chat/completions")
            self.assertEqual(timeout, 30)

            class Response:
                def read(self):
                    return json.dumps({
                        "choices": [{"message": {"content": '{"schema_version":"report-v1"}'}}],
                    }).encode()

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

            return Response()

        text = http_complete("sys", {"schema_version": "prevention-v1"},
                             url="https://example.invalid/v1/chat/completions",
                             key="secret", name="demo", urlopen=urlopen)
        self.assertEqual(text, '{"schema_version":"report-v1"}')

    def test_complete_from_env_requires_url(self):
        self.assertIsNone(complete_from_env(environ={}))
        built = complete_from_env(environ={"PHARMACY_MODEL_URL": "https://example.invalid/v1"})
        self.assertTrue(callable(built))


class HarnessModelCliTests(unittest.TestCase):
    def test_model_copy_injects_copier(self):
        fake = run_review(run_at=EVAL_RUN_AT, fda_http_get=offline_fda_http_get)
        with patch("src.pharmacy_harness.__main__.run_review", return_value=fake) as mocked:
            with patch("sys.stdout", io.StringIO()):
                main(["--offline", "--model-copy"])
        self.assertIs(mocked.call_args.kwargs["complete"], copying_complete)

    def test_model_without_url_errors(self):
        with patch("src.pharmacy_harness.loop.os.environ", {}):
            with patch("sys.stderr", io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(["--model"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
