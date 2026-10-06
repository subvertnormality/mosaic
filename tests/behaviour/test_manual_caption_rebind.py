"""Characterisation: editorial receipt refresh requires independently audited native data."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
import manual_caption_rebind as rebind
from manual_caption_overlay import contract_sha256

class CaptionRebindTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"repository";self.generated=self.root/"manual/generated"
        self.generated.mkdir(parents=True)
        self.native=self.generated/"reference-scenes.json"
        self.scenes=[{"id":"phrase","title":"Phrase","steps":[
            {"id":"a","caption":"Original technical caption","inputs":[{"key":3}],"expect":{"note":60},
             "output":{"screen":[1,2],"binding":{"assertion_index":1}}},
            {"id":"b","caption":"Second original caption","inputs":[],"expect":{"note":62},
             "output":{"grid":[4],"binding":{"assertion_index":2}}}],"evidence":{"results_sha256":"native"}}]
        self.native.write_text(json.dumps({"scenes":self.scenes}))
        self.source=self.root/"manual/scene-captions.yaml"
        self.entries=[dict(scene_id="phrase",step_id=step["id"],caption="Press K3." if i==0 else "Press K2.",
                           baseline_caption=step["caption"],contract_sha256="0"*64)
                      for i,step in enumerate(self.scenes[0]["steps"])]
        self.write_source(self.entries)
        self.evidence=Path(self.temp.name)/"receipt"
    def write_source(self,entries):
        self.source.write_text(yaml.safe_dump({"schema_version":1,"overlays":entries},sort_keys=False))
    def run_rebind(self,auditor=None):
        return rebind.rebind(self.evidence,root=self.root,auditor=auditor or (lambda:{"passed":True,"native_checked":True}))
    def test_success_refreshes_all_hashes_preserves_native_and_desired_captions(self):
        raw=self.native.read_bytes();before=self.source.read_bytes()
        def audit():
            self.assertEqual(self.source.read_bytes(),before)
            self.assertFalse(self.evidence.exists())
            return {"passed":True,"native_checked":True}
        report=self.run_rebind(audit)
        expected=contract_sha256(dict(self.scenes[0],data_path="generated/reference-scenes.json"))
        updated=yaml.safe_load(self.source.read_text())["overlays"]
        self.assertEqual([e["contract_sha256"] for e in updated],[expected,expected])
        self.assertEqual([e["caption"] for e in updated],["Press K3.","Press K2."])
        self.assertEqual(self.native.read_bytes(),raw)
        self.assertEqual((self.evidence/"source-before.yaml").read_bytes(),before)
        self.assertEqual((self.evidence/"source-after.yaml").read_bytes(),self.source.read_bytes())
        self.assertTrue(json.loads((self.evidence/"audit.json").read_text())["passed"])
        self.assertEqual(report["refreshed"],["phrase/a","phrase/b"])
        self.assertTrue(report["passed"]);self.assertFalse(report["complete_regression_run"])
    def test_failed_audit_writes_nothing(self):
        before=self.source.read_bytes()
        def failed():raise ValueError("native acceptance failed")
        with self.assertRaisesRegex(ValueError,"native acceptance"):self.run_rebind(failed)
        self.assertEqual(self.source.read_bytes(),before);self.assertFalse(self.evidence.exists())
        with self.assertRaisesRegex(ValueError,"audit did not pass"):self.run_rebind(lambda:{"passed":False})
        self.assertFalse(self.evidence.exists())
    def test_changed_baseline_or_missing_step_writes_nothing(self):
        for entry in (dict(self.entries[0],baseline_caption="Wrong"),dict(self.entries[0],step_id="missing"),
                      dict(self.entries[0],scene_id="missing")):
            self.write_source([entry]);before=self.source.read_bytes()
            with self.assertRaises(ValueError):self.run_rebind()
            self.assertEqual(self.source.read_bytes(),before);self.assertFalse(self.evidence.exists())
    def test_duplicate_entry_and_unknown_field_reject(self):
        for entries in ([self.entries[0],self.entries[0]],[dict(self.entries[0],output={})]):
            self.write_source(entries);before=self.source.read_bytes()
            with self.assertRaises(ValueError):self.run_rebind()
            self.assertEqual(self.source.read_bytes(),before);self.assertFalse(self.evidence.exists())
    def test_raw_data_changed_during_audit_rejects_without_source_write(self):
        before=self.source.read_bytes()
        def altered():
            self.native.write_text(self.native.read_text()+" ")
            return {"passed":True}
        with self.assertRaisesRegex(ValueError,"Native publication changed"):self.run_rebind(altered)
        self.assertEqual(self.source.read_bytes(),before);self.assertFalse(self.evidence.exists())
    def test_editorial_source_changed_during_audit_rejects(self):
        def altered():
            self.source.write_text(self.source.read_text()+"# concurrent edit\n")
            return {"passed":True}
        with self.assertRaisesRegex(ValueError,"Caption source changed"):self.run_rebind(altered)
        self.assertTrue(self.source.read_text().endswith("# concurrent edit\n"))
        self.assertFalse(self.evidence.exists())
    def test_current_receipts_produce_immutable_noop_evidence(self):
        scene=dict(self.scenes[0],data_path="generated/reference-scenes.json")
        for entry in self.entries:entry["contract_sha256"]=contract_sha256(scene)
        self.write_source(self.entries);before=self.source.read_bytes()
        report=self.run_rebind()
        self.assertEqual(report["refreshed"],[])
        self.assertEqual(self.source.read_bytes(),before)
        self.assertEqual(report["source_before_sha256"],report["source_after_sha256"])
        self.assertEqual((self.evidence/"source-after.yaml").read_bytes(),before)
    def test_fresh_desired_wording_requires_no_new_historic_receipt(self):
        self.scenes[0]["steps"][0]["caption"]=self.entries[0]["caption"]
        self.native.write_text(json.dumps({"scenes":self.scenes}))
        report=self.run_rebind()
        self.assertEqual(report["fresh_wording"],["phrase/a"])
        self.assertEqual(yaml.safe_load(self.source.read_text())["overlays"][0],self.entries[0])
    def test_existing_evidence_cannot_be_overwritten(self):
        self.evidence.mkdir();marker=self.evidence/"keep";marker.write_text("immutable")
        before=self.source.read_bytes()
        with self.assertRaisesRegex(ValueError,"Evidence already exists"):self.run_rebind()
        self.assertEqual(marker.read_text(),"immutable");self.assertEqual(self.source.read_bytes(),before)
    def test_default_audit_calls_independent_raw_entry_point(self):
        with patch("manual_publication_verify.audit_raw_publications",return_value={"passed":True},create=True) as audit:
            rebind.rebind(self.evidence,root=self.root)
        audit.assert_called_once_with()
    def test_atomic_write_failure_keeps_original_and_removes_temporary_file(self):
        before=self.source.read_bytes()
        with patch.object(rebind.os,"replace",side_effect=OSError("failed atomic replacement")):
            with self.assertRaisesRegex(OSError,"failed atomic"):self.run_rebind()
        self.assertEqual(self.source.read_bytes(),before)
        self.assertFalse(list(self.source.parent.glob(".scene-captions.rebind.*.tmp")))
        self.assertEqual((self.evidence/"source-before.yaml").read_bytes(),before)
        self.assertFalse((self.evidence/"source-after.yaml").exists())
if __name__=="__main__":unittest.main()
