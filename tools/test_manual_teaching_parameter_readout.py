"""Integration of the strict native Trig Params receipt into reader bindings."""
import copy
import json
import os
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
PROJECT=Path(os.environ["MOSAIC_PROJECT_ROOT"]).resolve()
REPORT=Path(os.environ["MOSAIC_PARAMETER_REPORT"])
sys.path.insert(0,str(HERE/"tools"))
import manual_teaching_v8 as teaching
from manual_teaching_v8_contract import native_transition_hash_v8
from manual_test_fixtures import load_pinned_projection_book


def authored_fixture():
    book=load_pinned_projection_book()
    report=json.loads(REPORT.read_text(encoding="utf-8"))
    scene=next(row for row in report["scenes"] if row["id"]=="fixed-note-default-and-locks")
    book["scenes"][scene["id"]]=scene
    effect=next(step for step in scene["steps"] if step["id"]=="channel60")["output"]["binding"]["assertion"]
    book["learning_path"][0]["stages"].append({
        "id":"fixed-note-native-receipt-test",
        "binding":{"status":"verified","scene":scene["id"],"step":"channel60"},
        "teaching_binding":{
            "from_step_id":"list","transition_scope":"interval",
            "actions":[
                {"id":"assign-fixed-note","kind":"select-value","control":"E3",
                 "field_label":"Fixed Note","value":"C5","label":"Set Fixed Note to C5"},
                {"id":"preview","kind":"preview-recorded-result","target_step_id":"channel60",
                 "label":"Preview the captured note"}],
            "semantic_requires":{"parameter_readout_equals":{
                "schema_version":1,"parameter_label":"Fixed Note","display_label":"Note",
                "slot":1,"value":"C5","marker":None,"picker_step_id":"list",
                "assignment_step_id":"assigned","readout_step_id":"default",
                "effect_step_id":"channel60","effect_assertion":effect}},
            "human_outcome":"The assigned Fixed Note remains C5 after returning from Trig Params.",
            "practice_prompt":"Assign Fixed Note, return to the channel, and check its displayed value."}})
    chunks={scene["id"]:{"path":"reader-chunks/scenes/fixture.json","sha256":"a"*64}}
    return book,chunks


class ParameterReadoutProjectionTests(unittest.TestCase):
    def test_exact_native_receipt_is_emitted_and_hash_bound(self):
        book,chunks=authored_fixture()
        contracts=teaching.build_teaching_contracts(book,chunks,project_root=PROJECT)
        binding=contracts["fixed-note-native-receipt-test"]
        proof=next(row for row in binding["action_checkpoints"] if row["action_id"]=="assign-fixed-note")
        receipt=proof["parameter_readout_receipt"]
        self.assertEqual(receipt["kind"],"parameter-readout-assignment")
        self.assertEqual(receipt["observation_indices"],{"picker":29,"assignment":34,"readout":36,"effect":41})
        self.assertEqual(receipt["request"]["value"],"C5")
        self.assertEqual(binding["native_transition_contract_sha256"],
            native_transition_hash_v8({
                **teaching._native(book["scenes"]["fixed-note-default-and-locks"],"list","channel60","interval"),
                "parameter_readout_receipts":[receipt]}))

    def test_changed_receipt_or_unrecognized_predicate_fails_closed(self):
        book,chunks=authored_fixture()
        expected=teaching.build_teaching_contracts(book,chunks,project_root=PROJECT)
        altered=copy.deepcopy(expected)
        altered["fixed-note-native-receipt-test"]["action_checkpoints"][0]["parameter_readout_receipt"]["proof_sha256"]="0"*64
        with self.assertRaises(teaching.Error):
            teaching.validate_teaching_contracts(book,chunks,altered,project_root=PROJECT)
        invalid=copy.deepcopy(book)
        invalid["learning_path"][0]["stages"][-1]["teaching_binding"]["semantic_requires"]["parameter_readout_equals"]["slot"]=0
        with self.assertRaises(teaching.Error):
            teaching.build_teaching_contracts(invalid,chunks,project_root=PROJECT)


if __name__=="__main__": unittest.main()
