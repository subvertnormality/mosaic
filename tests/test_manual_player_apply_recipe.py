"""Focused recipe tests; native-frame acceptance still runs in the controlled build."""
import importlib.util
import sys
import types
import unittest
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

pixel = types.ModuleType("frame_oracle")
pixel.footer_matches = lambda state, text: state.get("frame", {}).get("footer") == text
_MISSING = object()

def load_candidate_module():
    previous = sys.modules.get("frame_oracle", _MISSING)
    spec = importlib.util.spec_from_file_location("manual_player_apply_cases",
        ROOT / "tools" / "manual_player_apply_cases.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"frame_oracle": pixel}):
        spec.loader.exec_module(module)
    if previous is _MISSING:
        assert "frame_oracle" not in sys.modules
    else:
        assert sys.modules.get("frame_oracle") is previous
    return module

mod = load_candidate_module()

class Driver:
    def __init__(self, *, prompt=True, lose=False, keep_prompt=False):
        self.results=[]; self.observations=[]; self.ui=UI(self, prompt, lose, keep_prompt)

class UI:
    def __init__(self, c, prompt, lose, keep_prompt):
        self.c=c; self.prompt=prompt; self.lose=lose; self.keep_prompt=keep_prompt
        self.channel=1; self.page="home"; self.value="n.b."; self.pending=False
        self.applied=False; self.last_target=None
    def select_channel(self, channel): self.channel=channel
    def channel_page(self, page, channel=1):
        self.channel=channel; self.page=page
        if self.applied:
            self.pending=self.keep_prompt
    def expect_header(self, page, channel=1):
        assert self.page==page and self.channel==channel
    def shown_device(self, candidates):
        self.last_target=candidates[0]
        return self.value if self.value in candidates else "?"
    def turn(self, encoder, detents):
        assert encoder==3 and detents==1
        self.value=self.last_target; self.pending=True
    def expect_selected_field(self, layout, label=None, value=None):
        assert self.page=="midi_config" and layout=="detail" and label=="Device"
        if value is not None and self.value!=value:
            raise AssertionError("persisted public Device value differs")
        footer="Press K3 to confirm" if self.pending and self.prompt else "E3 SET  K3 APPLY  K2 BACK"
        index=len(self.c.observations)
        frame={"footer":footer,"sha256":f"{index+1:064x}"}
        self.c.observations.append({"state":{"frame":frame}})
        self.c.results.append({"kind":"selected-field","layout":layout,
                               "label":label,"value":value,"matched":True,
                               "observation_index":index,"frame_sha256":frame["sha256"]})
    def press_key(self, number):
        assert number==3 and self.pending
        self.pending=False; self.applied=True
        if self.lose: self.value="n.b."
        self.page="midi_config"

def custom(c, kind): return [row for row in c.results if row.get("kind")==kind]

class PlayerApplyRecipeTests(unittest.TestCase):
    def test_all_three_players_have_before_pending_and_reopened_checkpoints(self):
        c=Driver(); mod.apply_and_reopen_players(c)
        self.assertEqual([r["value"] for r in custom(c,"manual-player-apply-pending")],
                         ["Oilcan 1","Polyperc 1","Doubledecker"])
        done=custom(c,"manual-player-apply-reopened")
        self.assertEqual([r["value"] for r in done],["Oilcan 1","Polyperc 1","Doubledecker"])
        self.assertTrue(all(r["confirmation_prompt_absent"] for r in done))
        applied=custom(c,"manual-player-apply-applied")
        self.assertEqual([r["value"] for r in applied], ["Oilcan 1","Polyperc 1","Doubledecker"])
        self.assertEqual(len(custom(c,"manual-player-apply-start")),3)

    def test_missing_pending_confirmation_is_rejected(self):
        with self.assertRaisesRegex(AssertionError,"not visibly waiting"):
            mod.apply_and_reopen_players(Driver(prompt=False))

    def test_lost_assignment_after_reopen_is_rejected(self):
        with self.assertRaisesRegex(AssertionError,"persisted public Device value differs"):
            mod.apply_and_reopen_players(Driver(lose=True))

    def test_pending_prompt_after_reopen_is_rejected(self):
        with self.assertRaisesRegex(AssertionError,"still shows pending"):
            mod.apply_and_reopen_players(Driver(keep_prompt=True))

    def test_applied_value_and_cleared_prompt_use_the_same_latest_observation(self):
        c=Driver()
        c.ui.page="midi_config"
        c.ui.value="Oilcan 1"
        c.ui.expect_selected_field("detail", label="Device", value="Oilcan 1")
        c.observations[-1]["state"]["frame"]["footer"]="Press K3 to confirm"
        with self.assertRaisesRegex(AssertionError,"still shows pending"):
            mod._no_pending_prompt(c, 1, "Oilcan 1", "manual-player-apply-applied")
        self.assertEqual(custom(c,"manual-player-apply-applied"), [])

    def test_field_receipt_must_match_the_latest_footer_frame(self):
        c=Driver()
        c.ui.page="midi_config"; c.ui.value="Oilcan 1"; c.ui.pending=False
        c.ui.expect_selected_field("detail", label="Device", value="Oilcan 1")
        c.observations.append({"state":{"frame":{"footer":"E3 SET  K3 APPLY  K2 BACK","sha256":"f"*64}}})
        with self.assertRaisesRegex(AssertionError,"not bound to the latest native frame"):
            mod._no_pending_prompt(c, 1, "Oilcan 1", "manual-player-apply-applied")

    def test_actual_capture_loader_accepts_case_and_preserves_requirement(self):
        # Exercise the real `load_extra_cases` function from the source-pinned
        # capture runner, but isolate ROOT under a temp directory so no capture
        # or source-tree write can occur.
        source_root=ROOT
        runner_source=source_root / "tools" / "manual_case_capture.py"
        with tempfile.TemporaryDirectory() as temp:
            isolated=Path(temp); (isolated / "tools").mkdir()
            shutil.copy2(runner_source, isolated / "tools" / "manual_case_capture.py")
            shutil.copy2(ROOT / "tools" / "manual_player_apply_cases.py",
                         isolated / "tools" / "manual_player_apply_cases.py")
            spec=importlib.util.spec_from_file_location(
                "isolated_manual_case_capture", isolated / "tools" / "manual_case_capture.py")
            runner=importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
            loader_oracle=types.ModuleType("loader_frame_oracle")
            loader_oracle.footer_matches=pixel.footer_matches
            with patch.dict(sys.modules, {"frame_oracle": loader_oracle}):
                registry,blobs=runner.load_extra_cases(
                    ["tools/manual_player_apply_cases.py"], {}, root=isolated)
                self.assertIs(sys.modules["frame_oracle"], loader_oracle)
            entry=registry["M-MANUAL-PLAYER-APPLY-001"]
            self.assertEqual(entry["requirements"], ["CH-DEVICE"])
            self.assertEqual(len(blobs),1)
            self.assertEqual(entry["citation"], "manual:mods-and-software-devices")

    def test_plan_has_separate_apply_and_reopen_cues(self):
        import yaml
        plan=yaml.safe_load((ROOT / "manual" / "scene-plans-player-apply.yaml").read_text())
        for scene in plan["scenes"]:
            kinds=[step["assertion"]["kind"] for step in scene["steps"]]
            self.assertEqual(kinds.count("manual-player-apply-applied"), 1)
            self.assertEqual(kinds.count("manual-player-apply-reopened"), 1)
            self.assertEqual(scene["citation"], "manual:mods-and-software-devices")
            self.assertEqual(scene["requirements"], ["CH-DEVICE"])
            self.assertTrue(all(step["assertion"]["citation"] == scene["citation"] for step in scene["steps"]))

    def test_candidate_import_restores_preexisting_frame_oracle(self):
        sentinel=types.ModuleType("existing_frame_oracle")
        with patch.dict(sys.modules, {"frame_oracle": sentinel}):
            load_candidate_module()
            self.assertIs(sys.modules["frame_oracle"], sentinel)

    def test_candidate_schema_accepts_stable_citations_and_preserves_readme_aliases(self):
        import json, yaml
        from jsonschema import validate
        schema=json.loads((ROOT / "manual" / "case-scenes.schema.json").read_text())
        citation=schema["properties"]["scenes"]["items"]["properties"]["citation"]["pattern"]
        for value in ["manual:mods-and-software-devices", "manual:a", "manual:a1-b2"]:
            self.assertRegex(value, citation)
        for value in ["README.md#mods-and-software-devices", "README.md#legacy-alias"]:
            self.assertRegex(value, citation)
        for value in ["manual:../outside", "manual:-bad", "manual:bad-", "manual:bad--id",
                      "manual:Bad", "manual:bad\n"]:
            self.assertNotRegex(value, citation)
        plan=yaml.safe_load((ROOT / "manual" / "scene-plans-player-apply.yaml").read_text())
        validate(plan, schema)

if __name__=="__main__": unittest.main()


