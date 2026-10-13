import datetime, hashlib, json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import controller as c

class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.proc=self.root/"proc"; self.proc.mkdir()
        self.gate=self.root/"gate"; self.gate.mkdir(); self.evidence=self.root/"evidence"; self.evidence.mkdir()
        self.builder=self.root/"manual_build.py"; self.builder.write_text("pinned synthetic builder\n")
        self.pin=c.sha(self.builder.read_bytes()); self.patcher=patch.object(c,"BUILDER_SHA",self.pin); self.patcher.start(); self.addCleanup(self.patcher.stop)
        self.argv=["python3",str(self.builder),"--stage-gate-dir",str(self.gate)]
        self.rawargv=b"\0".join(v.encode() for v in self.argv)+b"\0"
        self.pid=123; folder=self.proc/str(self.pid); folder.mkdir()
        fields=["S"]+["0"]*18+["789"]+["0"]*3
        (folder/"stat").write_text("123 (name with ) spaces) "+" ".join(fields))
        (folder/"cmdline").write_bytes(self.rawargv); (folder/"comm").write_text("python3\n")
        stage=dict(name="stage-one",command=["echo","one"],emulator=None,exclusive_lock=False,action=None)
        self.row=dict(stage=stage,command=stage["command"])
        self.plan=dict(schema_version=1,builder_path=str(self.builder),builder_sha256=self.pin,builder_argv=self.argv,evidence_dir=str(self.evidence),stages=[self.row])
        self.plan_path=self.root/"plan.json"
        self.owner=dict(pid=self.pid,proc_starttime="789",evidence_dir=str(self.evidence),builder_sha256=self.pin,builder_argv_sha256=c.sha(self.rawargv))
        self.req=dict(schema_version=1,**self.owner,stage_index=1,stage_name=stage["name"],stage_sha256=c.sha(c.blob(stage)),argv_sha256=c.sha(c.blob(stage["command"])),previous_receipt=None,nonce="a"*32)
        self.rewrite()
    def rewrite(self):
        self.plan_path.write_bytes(c.blob(self.plan)); self.plan_sha=c.sha(self.plan_path.read_bytes())
        (self.gate/"owner.json").write_bytes(c.blob(self.owner))
        data=c.blob(self.req); self.request=self.gate/(f"{self.req['stage_index']:03d}-"+c.sha(data)+".request.json"); self.request.write_bytes(data)
    def verify(self): return c.verification(self.request,self.plan_path,self.plan_sha,self.proc)
    def rejected(self):
        with self.assertRaises((c.Refusal,OSError)): self.verify()
    def checks(self,result):
        value=dict(schema_version=1,request_sha256=result["request_sha256"],stage_sha256=self.req["stage_sha256"],previous_receipt_sha256=self.req["previous_receipt"]["sha256"] if self.req["previous_receipt"] else None,checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),memory_preflight=dict(passed=True,scope="entire-next-stage"))
        path=self.root/"checks.json"; path.write_bytes(c.blob(value)); return path,value
    def attest(self,result,value):
        path=self.root/"checks.json"; path.write_bytes(c.blob(value)); return c.external_checks(result,path,c.sha(path.read_bytes()))
    def prior(self,report=None):
        first=self.row
        receipt=dict(first["stage"],passed=True,returncode=0,executed_command=first["command"],finished_utc="2026-10-04T00:00:00+00:00")
        if report: receipt["native_report"]=report
        path=self.evidence/"stage-one.json"; path.write_bytes(c.blob(receipt))
        second=dict(first["stage"],name="stage-two"); self.plan["stages"].append(dict(stage=second,command=second["command"]))
        self.req.update(stage_index=2,stage_name="stage-two",stage_sha256=c.sha(c.blob(second)),previous_receipt=dict(path=str(path),sha256=c.sha(path.read_bytes())))
        self.rewrite(); return path
    def test_valid_request_exact_resume(self):
        result=self.verify(); self.assertEqual(result["cleanup_scope"],"not-applicable-first-stage")
        self.assertEqual(set(result["resume"]),c.OWNER|{"request_sha256","stage_index","stage_name","argv_sha256","nonce"})
    def test_noncanonical_request(self):
        self.request.write_text(json.dumps(self.req)); self.rejected()
    def test_filename_tamper(self):
        self.request=self.request.rename(self.gate/("001-"+"0"*64+".request.json")); self.rejected()
    def test_boolean_pid(self):
        self.req["pid"]=True; self.owner["pid"]=True; self.rewrite(); self.rejected()
    def test_float_index(self):
        self.req["stage_index"]=1.0
        raw=c.blob(self.req); self.request=self.gate/("001-"+c.sha(raw)+".request.json"); self.request.write_bytes(raw); self.rejected()
    def test_recycled_pid(self):
        self.req["proc_starttime"]="790"; self.owner["proc_starttime"]="790"; self.rewrite(); self.rejected()
    def test_argv_tamper(self):
        (self.proc/str(self.pid)/"cmdline").write_bytes(b"python3\0wrong\0"); self.rejected()
    def test_builder_tamper(self):
        self.builder.write_text("changed"); self.rejected()
    def test_plan_pin_tamper(self):
        self.plan_path.write_text("{}"); self.rejected()
    def test_stage_command_tamper(self):
        self.req["argv_sha256"]="0"*64; self.rewrite(); self.rejected()
    def test_stage_plan_tamper(self):
        self.req["stage_sha256"]="0"*64; self.rewrite(); self.rejected()
    def test_request_copy_elsewhere(self):
        other=self.root/"other"; other.mkdir(); p=other/self.request.name; p.write_bytes(self.request.read_bytes()); (other/"owner.json").write_bytes(c.blob(self.owner)); self.request=p; self.rejected()
    def test_native_service_presence(self):
        for name in sorted(c.SERVICES):
            folder=self.proc/"999"; folder.mkdir(exist_ok=True); (folder/"comm").write_text(name)
            self.rejected()
        (folder/"comm").unlink(); folder.rmdir()
    def test_previous_failed(self):
        p=self.prior(); x=json.loads(p.read_text()); x["passed"]=False; p.write_bytes(c.blob(x)); self.req["previous_receipt"]["sha256"]=c.sha(p.read_bytes()); self.rewrite(); self.rejected()
    def test_previous_tampered(self):
        p=self.prior(); p.write_text("{}"); self.rejected()
    def test_unfinished_receipt(self):
        p=self.prior(); x=json.loads(p.read_text()); del x["finished_utc"]; p.write_bytes(c.blob(x)); self.req["previous_receipt"]["sha256"]=c.sha(p.read_bytes()); self.rewrite(); self.rejected()
    def test_empty_finish_timestamp(self):
        p=self.prior(); x=json.loads(p.read_text()); x["finished_utc"]=""; p.write_bytes(c.blob(x)); self.req["previous_receipt"]["sha256"]=c.sha(p.read_bytes()); self.rewrite(); self.rejected()
    def test_invalid_finish_timestamp(self):
        p=self.prior(); x=json.loads(p.read_text()); x["finished_utc"]="not-a-date"; p.write_bytes(c.blob(x)); self.req["previous_receipt"]["sha256"]=c.sha(p.read_bytes()); self.rewrite(); self.rejected()
    def test_nested_boolean_integer_stage_mismatch(self):
        self.row["stage"]["action"]={"refresh":True}; p=self.prior(); x=json.loads(p.read_text()); x["action"]={"refresh":1}; p.write_bytes(c.blob(x)); self.req["previous_receipt"]["sha256"]=c.sha(p.read_bytes()); self.rewrite(); self.rejected()
    def test_jackdmp_presence_refused(self):
        folder=self.proc/"999"; folder.mkdir(); (folder/"comm").write_text("jackdmp")
        self.rejected()
    def test_duplicate_and_archived(self):
        result=self.verify(); Path(result["release"]).write_text("{}"); self.rejected()
        Path(result["release"]).unlink(); archive=self.evidence/"stage-gates"; archive.mkdir(); (archive/("001-"+"f"*64+".json")).write_text("{}"); self.rejected()
    def test_atomic_exclusive_complete_json(self):
        result=self.verify(); path=Path(result["release"]); c.publish_exclusive(path,result["resume"])
        self.assertEqual(path.read_bytes(),c.blob(result["resume"]))
        with self.assertRaises(c.Refusal): c.publish_exclusive(path,{"overwrite":True})
        self.assertEqual(path.read_bytes(),c.blob(result["resume"]))
        self.assertEqual(list(self.gate.glob(".resume-*.tmp")),[])
    def test_unsupported_platform_fails_closed(self):
        with patch.object(c.ctypes,"CDLL",return_value=object()):
            with self.assertRaises(c.Refusal): c.publish_exclusive(self.gate/"out",{})
        self.assertFalse((self.gate/"out").exists())
    def test_checks_stale_and_wrong_request(self):
        result=self.verify(); _,checks=self.checks(result); self.attest(result,checks)
        checks["checked_utc"]="2000-01-01T00:00:00+00:00"
        with self.assertRaises(c.Refusal): self.attest(result,checks)
        _,checks=self.checks(result); checks["request_sha256"]="0"*64
        with self.assertRaises(c.Refusal): self.attest(result,checks)
    def test_memory_integer_not_boolean(self):
        result=self.verify(); _,checks=self.checks(result); checks["memory_preflight"]["passed"]=1
        with self.assertRaises(c.Refusal): self.attest(result,checks)
    def test_unsupported_report_needs_external_review(self):
        report=self.root/"report.json"; report.write_bytes(c.blob(dict(passed=True,behaviour_cases=[])))
        self.prior(dict(path=str(report),sha256=c.sha(report.read_bytes())))
        result=self.verify(); self.assertEqual(result["cleanup_scope"],"external-root-review-required")
        _,checks=self.checks(result)
        with self.assertRaises(c.Refusal): self.attest(result,checks)
        proof=self.root/"review.txt"; proof.write_text("root inspected complete participant cleanup")
        checks["cleanup_review"]=dict(passed=True,scope="all-prior-stage-native-participants",report_sha256=result["report_sha256"],assertions=dict(finished=True,no_held_inputs=True,cleanup_verified=True),evidence=[dict(path=str(proof),sha256=c.sha(proof.read_bytes()))])
        self.attest(result,checks); self.assertEqual(result["cleanup_scope"],"external-root-review")
    def native_report(self,held=None):
        root=self.root/"case"; root.mkdir(); (root/"native").mkdir()
        context=dict(finished=True,cleanup_verified=True,held_inputs=[] if held is None else held)
        cp=root/"session-context.json"; cp.write_bytes(c.blob(context))
        cleanup=[dict(service=name,pid=n+1,returncode=-15 if name=="sclang" else 0) for n,name in enumerate(["matron","crone","sclang","jack"])]
        cl=root/"native/cleanup.json"; cl.write_bytes(c.blob(cleanup))
        participant=dict(path=str(root),session_context=context,session_context_sha256=c.sha(cp.read_bytes()),cleanup_sha256=c.sha(cl.read_bytes()))
        manifest=root/"case-participants.json"; manifest.write_bytes(c.blob([participant]))
        evidence=dict(participant,case_participants=[participant],case_participants_path=str(manifest),case_participants_sha256=c.sha(manifest.read_bytes()))
        report=dict(scenes=[dict(evidence=evidence)]); return report,cl
    def test_native_participant_proof(self):
        report,_=self.native_report(); self.assertTrue(c.cleanup_report(report))
    def test_held_inputs_rejected(self):
        report,_=self.native_report(held=[[1,1]])
        with self.assertRaises(c.Refusal): c.cleanup_report(report)
    def test_cleanup_tamper_rejected(self):
        report,cl=self.native_report(); cl.write_text("[]")
        with self.assertRaises(c.Refusal): c.cleanup_report(report)
    def test_duplicate_json_keys(self):
        with self.assertRaises(c.Refusal): c.decode(b'{"pid":1,"pid":2}')
    def test_symlink_request(self):
        target=self.root/"target"; self.request.rename(target); self.request.symlink_to(target); self.rejected()

if __name__=="__main__": unittest.main()
