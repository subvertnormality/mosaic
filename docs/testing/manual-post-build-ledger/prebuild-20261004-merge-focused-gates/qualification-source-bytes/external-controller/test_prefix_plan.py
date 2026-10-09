import contextlib, io, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import controller as c
import prefix_plan as p

class PrefixTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name); self.builder=root/"builder.py"; self.builder.write_text("synthetic")
        pin=c.sha(self.builder.read_bytes()); obj=patch.object(c,"BUILDER_SHA",pin); obj.start(); self.addCleanup(obj.stop)
        self.context=dict(schema_version=1,builder_path=str(self.builder),builder_sha256=pin,builder_argv=["python3",str(self.builder),"--stage-gate-dir",str(root/"gate")],evidence_dir=str(root))
        self.original=[dict(name="one",command=["ordinary"],action=None),dict(name="ready",command=["needs-future-fixture"],action=dict(doctor_ready=True)),dict(name="audit",command=[],action=dict(doctor_options_audit=True))]
    def extend(self,index,command,previous=None): return p.extend(self.original,self.context,command,index,previous,3)
    def test_bootstrap_and_future_dependency_append(self):
        one=self.extend(1,["ordinary"]); before=c.blob(one)
        two=self.extend(2,["capture","--ready-fixture","/actual/future/fixture.json"],one)
        three=self.extend(3,["audit","--manual-right-report","/actual/future/report.json"],two)
        self.assertEqual(len(one["stages"]),1); self.assertEqual(len(three["stages"]),3)
        self.assertEqual(c.blob(one),before); self.assertEqual(three["stages"][:2],two["stages"])
        three["stages"][0]["command"].append("changed"); self.assertEqual(c.blob(one),before)
    def test_no_bootstrap_at_future_stage(self):
        with self.assertRaises(c.Refusal): self.extend(2,["fake"])
    def test_no_skipped_extension(self):
        one=self.extend(1,["ordinary"])
        with self.assertRaises(c.Refusal): self.extend(3,["fake"],one)
    def test_no_repeated_extension(self):
        one=self.extend(1,["ordinary"])
        with self.assertRaises(c.Refusal): self.extend(1,["fake"],one)
    def test_original_plan_change_detected(self):
        one=self.extend(1,["ordinary"]); self.original[0]["action"]={"changed":True}
        with self.assertRaises(c.Refusal): self.extend(2,["ready"],one)
    def test_bootstrap_evidence_change_detected(self):
        one=self.extend(1,["ordinary"]); self.context["builder_argv"].append("changed")
        with self.assertRaises(c.Refusal): self.extend(2,["ready"],one)
    def test_nested_types_are_exact(self):
        self.original[0]["action"]={"flag":True}; one=self.extend(1,["ordinary"])
        one["stages"][0]["stage"]["action"]={"flag":1}
        with self.assertRaises(c.Refusal): self.extend(2,["ready"],one)
    def test_original_count_pin(self):
        with self.assertRaises(c.Refusal): p.extend(self.original,self.context,["ordinary"],1)
    def test_previous_commands_preserved_literally(self):
        one=self.extend(1,["literal","--value","True"]); two=self.extend(2,["ready"],one)
        self.assertEqual(two["stages"][0]["command"],["literal","--value","True"])
    def test_cli_version_receipt_and_duplicate_refusal(self):
        root=Path(self.temp.name); versions=root/"versions"; versions.mkdir()
        refs={}
        for name,value in (("original-plan",self.original),("context",self.context),("command",["ordinary"])):
            path=root/(name+".json"); path.write_bytes(c.blob(value)); refs[name]=(str(path),c.sha(path.read_bytes()))
        args=["prefix_plan.py","--stage-index","1","--original-count","3","--output-directory",str(versions)]
        for name,(path,pin) in refs.items(): args += ["--"+name,path,"--"+name+"-sha256",pin]
        out=io.StringIO()
        with patch.object(sys,"argv",args),contextlib.redirect_stdout(out): self.assertEqual(p.main(),0)
        receipt=json.loads(out.getvalue()); self.assertEqual(receipt["original_stage_count"],3)
        self.assertIsNone(receipt["previous_prefix"]); self.assertFalse(receipt["release_published"])
        self.assertEqual(c.sha(Path(receipt["prefix"]["path"]).read_bytes()),receipt["prefix"]["sha256"])
        unchanged={path:path.read_bytes() for path in versions.iterdir()}
        with patch.object(sys,"argv",args),contextlib.redirect_stderr(io.StringIO()): self.assertEqual(p.main(),2)
        self.assertEqual({path:path.read_bytes() for path in versions.iterdir()},unchanged)
    def test_source_pin_required(self):
        self.builder.write_text("tampered")
        with self.assertRaises(c.Refusal): self.extend(1,["ordinary"])
if __name__=="__main__": unittest.main()
