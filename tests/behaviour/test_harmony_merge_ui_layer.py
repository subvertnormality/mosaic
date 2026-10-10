"""Static regression for the Harmony workflow's UI abstraction boundary."""

import ast
import unittest
from pathlib import Path


SOURCE = Path(__file__).with_name("harmony_merge_workflow.py")
BEHAVIOUR = SOURCE.parent
VISUAL_CONTRACT = BEHAVIOUR / "contract" / "harmony_merge_visual.py"


class HarmonyUiLayerTests(unittest.TestCase):
    def test_raw_visual_contract_is_owned_by_contract_package(self):
        self.assertTrue(VISUAL_CONTRACT.is_file())
        self.assertEqual(VISUAL_CONTRACT.resolve().parent,
                         (BEHAVIOUR / "contract").resolve())
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        imports = [node.module for node in ast.walk(tree)
                   if isinstance(node, ast.ImportFrom)]
        self.assertIn("contract.harmony_merge_visual", imports)
        self.assertNotIn("harmony_merge_visual_contract", imports)

    def test_workflow_uses_ui_verbs_and_delegates_only_raw_frame_contracts(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        forbidden_methods = {"tap", "enc", "key", "screen_header", "led_values",
                             "hold_tap"}
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in {"frame", "grid"}:
                violations.append((node.lineno, "raw snapshot surface " + node.value))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "c":
                    if node.func.attr in forbidden_methods:
                        violations.append((node.lineno, "c." + node.func.attr))
                    if node.func.attr == "action":
                        kind = next((kw.value.value for kw in node.keywords
                                     if kw.arg == "type" and
                                     isinstance(kw.value, ast.Constant)), None)
                        if kind in {"grid", "key", "enc"}:
                            violations.append((node.lineno, "raw " + kind + " action"))
            if isinstance(node, ast.ImportFrom) and node.module == "frame_oracle":
                violations.append((node.lineno, "frame_oracle import"))
            if isinstance(node, ast.Import) and any(alias.name == "frame_oracle"
                                                    for alias in node.names):
                violations.append((node.lineno, "frame_oracle import"))
        self.assertEqual(violations, [], "UI coupling remains: %r" % violations)


if __name__ == "__main__":
    unittest.main()
