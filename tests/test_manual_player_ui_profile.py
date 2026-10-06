"""Offline policy checks for the controlled software-player UI profile.

This file can be installed at tests/test_manual_player_ui_profile.py alongside
the proposed Driver and manual scene-plan/schema changes. It imports no emulator
and starts no native or audio session.
"""
import ast
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DRIVER_PATH = ROOT / "tests/behaviour/driver.py"

def load_driver():
    spec = importlib.util.spec_from_file_location("manual_player_ui_policy_driver", DRIVER_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, {"MONOME_EMULATOR": ""}):
        spec.loader.exec_module(module)
    return module

class ManualPlayerUiProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = load_driver()
        cls.source = DRIVER_PATH.read_text()
        cls.profiles = json.loads((ROOT / "tests/behaviour/output-profiles.json").read_text())["profiles"]

    def test_profile_is_controlled_only_and_has_three_exact_source_pins(self):
        profile = self.driver.MANUAL_PLAYER_UI_PROFILE
        self.assertTrue(profile["controlled_ui_only"])
        self.assertEqual(set(profile["mods"]), {"doubledecker", "nb_polyperc", "oilcan"})
        self.assertEqual(profile["mods"], self.profiles["manual-trio"]["mods"])
        self.assertNotIn("manual-player-ui", self.profiles)

    def test_clock_policy_is_narrow_and_keeps_legacy_output_gates(self):
        check = self.driver.validate_profile_clock
        check("manual-player-ui", "controlled-experimental", self.profiles)
        with self.assertRaisesRegex(ValueError, "controlled UI-only"):
            check("manual-player-ui", "real-time", self.profiles)
        check("manual-trio", "real-time", self.profiles)
        with self.assertRaisesRegex(ValueError, "require real time"):
            check("manual-trio", "controlled-experimental", self.profiles)
        with self.assertRaisesRegex(ValueError, "require real time"):
            check("crow-jf", "controlled-experimental", {"crow-jf": {}})
        self.assertIn("if profile in output_profiles:\n                capability=self.runtime.capabilities()", self.source)

    def test_ui_profile_reuses_managed_origin_revision_clean_and_ignored_checks(self):
        self.assertIn("if profile in output_profiles or manual_player_ui:\n                    origin=", self.source)
        self.assertIn("if profile in output_profiles or manual_player_ui:\n                    ignored=", self.source)
        self.assertIn("revision=subprocess.check_output(['git','rev-parse','HEAD']", self.source)
        self.assertIn("dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=all']", self.source)
        self.assertIn("enabled_mods=list(self.mod_revisions)", self.source)
        self.assertIn("diagnostics['enabled_mods']==len(self.mod_revisions) and diagnostics['loaded_mods']==len(self.mod_revisions)", self.source)

    def test_schema_and_plan_allow_only_the_new_profile_delta(self):
        import yaml
        from jsonschema import validate
        schema=json.loads((ROOT / "manual/case-scenes.schema.json").read_text())
        plan=yaml.safe_load((ROOT / "manual/scene-plans-player-apply.yaml").read_text())
        profiles=schema["properties"]["scenes"]["items"]["properties"]["profile"]["enum"]
        self.assertIn("manual-player-ui", profiles)
        self.assertNotIn("manual-trio", profiles)
        validate(plan, schema)
        self.assertEqual({scene["profile"] for scene in plan["scenes"]},{"manual-player-ui"})
        self.assertEqual(len(plan["scenes"]),3)
        for scene in plan["scenes"]:
            kinds=[step["assertion"]["kind"] for step in scene["steps"]]
            self.assertEqual(kinds,["manual-player-apply-start","manual-player-apply-pending","manual-player-apply-applied","manual-player-apply-reopened"])
            self.assertFalse(any(any(key in step["assertion"] for key in ("midi_phrase","midi_events","audio","sequence")) for step in scene["steps"]))

if __name__ == "__main__":
    unittest.main()
