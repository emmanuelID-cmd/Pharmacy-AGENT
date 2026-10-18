"""Core inventory-review modules must stay free of demo quantity logic."""
import ast
import json
import pathlib
import unittest

from src.pharmacy_harness.offline import EVAL_RUN_AT, offline_fda_http_get
from src.pharmacy_harness.run import run_review
from src.pharmacy_tools.inventory import LEGACY_FIXTURE_PATH

ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "pharmacy_harness"
CORE = [
    "run", "report", "display", "loop", "facts", "calculate",
    "validate", "offline", "__main__",
]


class CoreStaysFreeOfReplenishment(unittest.TestCase):
    def test_no_core_module_imports_replenishment(self):
        for name in CORE:
            source = (ROOT / f"{name}.py").read_text(encoding="utf-8")
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Import):
                    mods = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    mods = [node.module or ""] + [alias.name for alias in node.names]
                else:
                    continue
                self.assertFalse(
                    any("replenishment" in (mod or "") for mod in mods),
                    f"{name}.py imports replenishment",
                )

    def test_core_source_never_mentions_suggested_quantity(self):
        for name in CORE:
            source = (ROOT / f"{name}.py").read_text(encoding="utf-8")
            self.assertNotIn("suggested_quantity", source, name)

    def test_run_review_report_has_no_suggested_quantity_key(self):
        report = run_review(
            run_at=EVAL_RUN_AT,
            inventory_path=LEGACY_FIXTURE_PATH,
            fda_http_get=offline_fda_http_get,
        )
        encoded = json.dumps(report, default=str)
        self.assertNotIn("suggested_quantity", encoded)
        self.assertNotIn("suggested_quantity", report)


if __name__ == "__main__":
    unittest.main()
