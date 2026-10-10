"""Same-lineage continuation of a failed audio recording run (characterisation of manual-audio
publication integrity, outside README.md): identical recording identity => completed examples are
reused after re-audit; any identity difference rejects the whole resume; the publication audit
verifies the provenance strictly."""
import copy, hashlib, json, os, shutil, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TOOLS=Path(__file__).resolve().parent
sys.path.insert(0,str(TOOLS))
sys.path.insert(0,str(TOOLS.parent/"tests/behaviour"))
import manual_audio_resume as R
import manual_audio

def h(b):return hashlib.sha256(b).hexdigest()
def put(path,text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);return path
def manifest_of(files):return hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
AUTHORED=[dict(id=i,bars=1,bpm=120,tracks=[dict(channel=1,voice="v")],purpose="plain") for i in ("ex1","ex2","ex3")]
FROZEN={"source.yaml":"source_sha256","capture-tool.py":"tool_sha256","capture-helpers.py":"helper_sha256","capture-setups.py":"setups_sha256","audio.schema.json":"schema_sha256"}

class Fixture(unittest.TestCase):
    done=("ex1","ex2")
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.base=Path(tmp.name)
        self.root=self.base/"repo";self.old=self.base/"runs/old";self.new=self.base/"runs/new"
        self.old.mkdir(parents=True);self.new.mkdir(parents=True)
        for rel,text in (("mosaic.lua","m"),("lib/a.lua","a"),("lib/tests/skip.lua","x"),("docs/ui-reimplementation/code/b.lua","b"),("tests/behaviour/driver.py","d")):put(self.root/rel,text)
        self.report=dict(schema_version=1,source_sha256="s",tool_sha256="t",helper_sha256="h",setups_sha256="u",schema_sha256="c",
            harness_sha256={"driver.py":h(b"d")},voice_pins={"oilcan":{"commit":"1"}},clock_mode="controlled-experimental",
            validation_scope="controlled-manual-generation",realtime_qualification="pending-ci",audio_capture_clock_mode="real-time",
            controlled_lane="inapplicable: native DSP audio depends on real host time",complete_regression_run=False,passed=False,examples=[])
        for name,key in FROZEN.items():
            text=name+"-body";put(self.old/name,text);self.report[key]=h(text.encode())
        put(self.old/"driver.py","d")
        for name in list(FROZEN)+["driver.py"]:shutil.copyfile(self.old/name,self.new/name)
        for rel in ("mosaic.lua","lib/a.lua","docs/ui-reimplementation/code/b.lua"):put(self.old/"application"/rel,(self.root/rel).read_text())
        for rel in ("mosaic.lua","lib/a.lua","docs/ui-reimplementation/code/b.lua"):put(self.new/"application"/rel,(self.root/rel).read_text())
        self.emus={}
        for kind in ("audio","midi"):
            put(self.base/(kind+"-emu/e.txt"),kind+"-emulator");self.emus[kind]=self.base/(kind+"-emu")
        self.installs={}
        for kind in ("audio","midi"):
            self.installs[kind]=self.base/(kind+"-install.json")
            self.installs[kind].write_text(json.dumps(dict(lock_sha256=kind,source="/src/"+kind,binaries={"m":{"sha256":"1"}})))
        self.report["examples"]=[self.example(self.old,i) for i in self.done]
        self.write_old()
        self.ma=SimpleNamespace(audit_example_native=lambda *a,**k:3)
    def identity(self,kind,out):
        files=[dict(path="a",sha256="1"*64,size=1)]
        emu=[dict(path="e.txt",sha256=R.sha(self.emus[kind]/"e.txt"),size=1)]
        json.dump(dict(session_id=out.name,runtime_identity=json.loads(self.installs[kind].read_text()),
            application_identity=dict(code_root=str(out/"code"),digest=manifest_of(files),files=files),
            emulator_identity=dict(revision="r",digest=manifest_of(emu),files=emu)),(out/"native/identity.json").open("w"))
    def session(self,run,name,kind,job=None):
        out=run/name;(out/"native").mkdir(parents=True,exist_ok=True);self.identity(kind,out);ev=dict(path=str(out))
        if job:
            wav=out/"native/audio-captures"/job/"output.wav";wav.parent.mkdir(parents=True,exist_ok=True);wav.write_bytes(job.encode()+b"-pcm")
            ev.update(job=dict(job_id=job),wav_sha256=R.sha(wav))
        return ev
    def example(self,run,ident,lane=False):
        a=next(v for v in AUTHORED if v["id"]==ident)
        row=dict(a,evidence=self.session(run,ident+"-mix","audio",ident+"-jm"),metrics={},timeline=[],acceptance_case="MA-"+ident,
            solo_contributions=[dict(channel=1,voice="v",metrics={},evidence=self.session(run,ident+"-solo-1","audio",ident+"-js"))],
            files=["audio/"+ident+".ogg","audio/"+ident+".mp3"],file_sha256={"audio/"+ident+".ogg":"0"*64,"audio/"+ident+".mp3":"0"*64})
        if lane:row["musical_evidence"]=[dict(path=self.session(run,ident+"-midi","midi")["path"],clock_mode="controlled-experimental")]
        return row
    def write_old(self):(self.old/"report.json").write_text(json.dumps(self.report))
    def current(self):return {k:copy.deepcopy(v) for k,v in self.report.items() if k not in ("examples","passed")}
    def convert(self,ffmpeg,wav,target,seconds,codec):Path(target).write_bytes(Path(wav).read_bytes()+codec.encode())
    def prepare(self,current=None,**over):
        args=dict(audio_install=self.installs["audio"],midi_install=self.installs["midi"],audio_emulator=self.emus["audio"],midi_emulator=self.emus["midi"],converter=self.convert,session_check=lambda *a:None)
        args.update(over)
        return R.prepare_same_lineage(self.ma,self.root,self.old,json.loads((self.old/"report.json").read_text()),self.new,current or self.current(),dict(examples=AUTHORED),"ffmpeg",**args)

class Reuse(Fixture):
    def test_identical_identity_reuses_every_completed_example(self):
        rows,prov,stage=self.prepare()
        self.assertEqual([r["id"] for r in rows],["ex1","ex2"])
        self.assertEqual(prov["kind"],R.SAME);self.assertEqual(prov["reused_ids"],["ex1","ex2"]);self.assertEqual(prov["deferred_ids"],["ex3"])
        self.assertIs(prov["passed"],False);self.assertIs(prov["complete_regression_run"],False)
        for r in rows:
            self.assertTrue(r["evidence"]["path"].startswith(str(self.new)))
            self.assertEqual(Path(r["evidence"]["path"]).resolve(),(self.old/(r["id"]+"-mix")).resolve())
            self.assertEqual(sorted(p.name for p in (stage/"audio").iterdir() if p.name.startswith(r["id"])),[r["id"]+".mp3",r["id"]+".ogg"])
            for f in r["files"]:self.assertEqual(r["file_sha256"][f],R.sha(stage/f))
        self.assertTrue((self.new/"resume-provenance.required.json").is_file())

    def test_each_reused_example_is_reaudited_with_its_authored_record(self):
        seen=[]
        self.ma.audit_example_native=lambda row,authored,local:seen.append((row["id"],authored["id"],local))
        self.prepare();self.assertEqual(seen,[("ex1","ex1",True),("ex2","ex2",True)])

    def test_failed_reaudit_rejects_the_whole_resume(self):
        def audit(row,authored,local):
            if row["id"]=="ex2":raise ValueError("PCM metrics changed")
        self.ma.audit_example_native=audit
        with self.assertRaisesRegex(R.Rejected,"ex2.*PCM metrics changed"):self.prepare()
        self.assertFalse((self.new/"resume-provenance.required.json").exists())

    def test_changed_authored_record_is_rejected(self):
        self.report["examples"][0]["bars"]=2;self.write_old()
        with self.assertRaisesRegex(R.Rejected,"authored field changed ex1.bars"):self.prepare()

    def test_unknown_example_is_rejected(self):
        self.report["examples"][0]["id"]="other";self.write_old()
        with self.assertRaisesRegex(R.Rejected,"outside the authored inventory"):self.prepare()

    def test_nested_resume_and_passed_reports_are_rejected(self):
        self.report["resume_provenance"]={"kind":R.SAME};self.write_old()
        with self.assertRaisesRegex(R.Rejected,"nested resume"):self.prepare()
        del self.report["resume_provenance"];self.report["passed"]=True;self.write_old()
        with self.assertRaisesRegex(R.Rejected,"failed partial"):self.prepare()

    def test_empty_partial_run_has_nothing_to_resume(self):
        self.report["examples"]=[];self.write_old()
        with self.assertRaisesRegex(R.Rejected,"no completed example"):self.prepare()

class IdentityMismatch(Fixture):
    def test_every_recorded_identity_field_must_match(self):
        for key,value in (("source_sha256","x"),("tool_sha256","x"),("helper_sha256","x"),("setups_sha256","x"),("schema_sha256","x"),
                ("harness_sha256",{"driver.py":"x"}),("voice_pins",{"oilcan":{"commit":"2"}}),("clock_mode","real-time")):
            with self.subTest(key):
                current=self.current();current[key]=value
                with self.assertRaisesRegex(R.Rejected,"identity mismatch.*"+key):self.prepare(current)

    def test_all_mismatching_fields_are_named(self):
        current=self.current();current.update(tool_sha256="x",source_sha256="y")
        with self.assertRaisesRegex(R.Rejected,"source_sha256, tool_sha256"):self.prepare(current)

    def test_frozen_copies_in_the_old_run_must_match_the_report(self):
        for name in list(FROZEN)+["driver.py"]:
            with self.subTest(name):
                original=(self.old/name).read_text();(self.old/name).write_text(original+"!")
                with self.assertRaisesRegex(R.Rejected,"frozen run file changed: "+name):self.prepare()
                (self.old/name).write_text(original)

    def test_current_harness_file_must_match(self):
        (self.root/"tests/behaviour/driver.py").write_text("changed")
        with self.assertRaisesRegex(R.Rejected,"harness identity mismatch: driver.py"):self.prepare()

    def test_application_tree_must_be_identical(self):
        (self.root/"lib/a.lua").write_text("edited")
        with self.assertRaisesRegex(R.Rejected,"application source tree changed"):self.prepare()
        (self.root/"lib/a.lua").write_text("a");put(self.root/"lib/new.lua","n")
        with self.assertRaisesRegex(R.Rejected,"application source tree changed"):self.prepare()

    def test_tests_and_caches_are_not_part_of_the_application_tree(self):
        put(self.root/"lib/tests/more.lua","ignored");put(self.root/"lib/__pycache__/x","ignored")
        self.assertEqual([r["id"] for r in self.prepare()[0]],["ex1","ex2"])

    def test_copied_application_in_the_new_run_must_match(self):
        (self.new/"application/lib/a.lua").write_text("edited")
        with self.assertRaisesRegex(R.Rejected,"application source tree changed"):self.prepare()

    def test_audio_and_midi_installation_identity_must_match(self):
        self.report["examples"][0]=self.example(self.old,"ex1",lane=True);self.write_old()
        for kind,arg in (("audio","audio_install"),("midi","midi_install")):
            with self.subTest(kind):
                other=self.base/(kind+"-other.json");other.write_text(json.dumps(dict(lock_sha256="other",source="/src/other")))
                with self.assertRaisesRegex(R.Rejected,kind+" runtime identity differs from the current installation"):self.prepare(**{arg:other})

    def test_emulator_identity_must_match(self):
        self.report["examples"][0]=self.example(self.old,"ex1",lane=True);self.write_old()
        for kind,arg in (("audio","audio_emulator"),("midi","midi_emulator")):
            with self.subTest(kind):
                (self.emus[kind]/"e.txt").write_text("edited")
                with self.assertRaisesRegex(R.Rejected,kind+" emulator source changed"):self.prepare()
                (self.emus[kind]/"e.txt").write_text(kind+"-emulator")
            with self.subTest(kind+"-missing"):
                with self.assertRaisesRegex(R.Rejected,"required"):self.prepare(**{arg:None})

    def test_mixed_runtime_identities_inside_the_old_run_are_rejected(self):
        path=self.old/"ex2-solo-1/native/identity.json";d=json.loads(path.read_text());d["runtime_identity"]["lock_sha256"]="drift";path.write_text(json.dumps(d))
        with self.assertRaisesRegex(R.Rejected,"not uniform"):self.prepare()

class Audit(Fixture):
    """The resumed report as main() would write it, audited the way audit_publication audits it."""
    def resumed(self,fresh=True,**over):
        rows,prov,stage=self.prepare(**over)
        for f in stage.joinpath("audio").iterdir():
            dest=self.root/"manual/audio"/f.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
        report=dict(self.current(),passed=False,examples=rows,resume_provenance=prov)
        if fresh:
            row=self.example(self.new,"ex3");row["files"]=["audio/ex3.ogg"];row["file_sha256"]={"audio/ex3.ogg":"1"*64};report["examples"].append(row)
        return report
    def audit(self,report,**kw):
        return R.audit_resume_provenance(self.ma,report,self.new,self.root,**kw)
    def test_resumed_report_is_accepted_and_dispatched_by_kind(self):
        self.resumed_report=self.resumed();result=self.audit(self.resumed_report);self.assertTrue(result["passed"]);self.assertEqual(result["reused_examples"],2);self.assertEqual(result["deferred_examples"],1)
        self.assertTrue(R.require_resume_provenance(self.resumed_report,self.new))
    def test_report_without_marker_but_with_provenance_is_rejected(self):
        report=self.resumed();(self.new/"resume-provenance.required.json").unlink()
        with self.assertRaisesRegex(R.Rejected,"no durable run marker"):R.require_resume_provenance(report,self.new)
    def rejects(self,report,pattern):
        with self.assertRaisesRegex(R.Rejected,pattern):self.audit(report)
    def test_tampered_original_record_is_rejected(self):
        report=self.resumed();self.report["examples"][0]["metrics"]={"rms":1};self.write_old()
        self.rejects(report,"original report changed")
    def test_tampered_original_wav_is_rejected(self):
        report=self.resumed();(self.old/"ex1-mix/native/audio-captures/ex1-jm/output.wav").write_bytes(b"x")
        self.rejects(report,"raw WAV changed")
    def test_tampered_staged_asset_is_rejected(self):
        report=self.resumed();(self.root/"manual/audio/ex1.ogg").write_bytes(b"x")
        self.rejects(report,"reused encoded asset hash changed")
    def test_missing_staged_asset_is_rejected(self):
        report=self.resumed();(self.root/"manual/audio/ex2.mp3").unlink()
        self.rejects(report,"reused encoded asset hash changed")
    def test_tampered_current_reused_row_is_rejected(self):
        report=self.resumed();report["examples"][0]["metrics"]={"rms":1}
        self.rejects(report,"current reused report row differs")
    def test_dropped_reused_row_is_rejected(self):
        report=self.resumed();del report["examples"][0]
        self.rejects(report,"missing reused current report row")
    def test_alias_relink_is_rejected(self):
        report=self.resumed();other=self.base/"elsewhere";other.mkdir();link=self.new/"ex1-mix";link.unlink();link.symlink_to(other,target_is_directory=True)
        self.rejects(report,"reused evidence alias changed")
    def test_marker_edit_is_rejected(self):
        report=self.resumed();m=self.new/"resume-provenance.required.json";d=json.loads(m.read_text());d["reused_ids"]=["ex1"];m.write_text(json.dumps(d))
        self.rejects(report,"durable resume marker")
    def test_manifest_edit_is_rejected(self):
        report=self.resumed();m=self.new/"resume-reuse/resume-reuse-manifest.json";m.write_text(m.read_text()+" ")
        self.rejects(report,"qualification manifest changed")
    def test_provenance_cannot_claim_completion_or_another_kind(self):
        report=self.resumed();report["resume_provenance"]["passed"]=True;self.rejects(report,"falsely claims completion")
    def test_reused_ids_must_be_every_completed_original_example(self):
        report=self.resumed();m=self.new/"resume-provenance.required.json";d=json.loads(m.read_text());d["reused_ids"]=["ex1"];m.write_text(json.dumps(d))
        report["resume_provenance"].update(reused_ids=["ex1"],marker_sha256=R.sha(m));self.rejects(report,"reused ids are not every completed")
    def test_changed_report_identity_is_rejected(self):
        base=self.resumed()
        for key in ("tool_sha256","source_sha256","voice_pins"):
            with self.subTest(key):
                report=copy.deepcopy(base);report[key]="x";self.rejects(report,"identity mismatch.*"+key)
    def test_frozen_files_of_the_new_run_must_match_the_old_run(self):
        report=self.resumed();(self.new/"capture-tool.py").write_text("other")
        self.rejects(report,"frozen run file changed: capture-tool.py")
    def test_application_copy_of_the_new_run_must_match(self):
        report=self.resumed();(self.new/"application/mosaic.lua").write_text("other")
        self.rejects(report,"application source tree changed")
    def test_fresh_session_with_different_runtime_identity_is_rejected(self):
        report=self.resumed();p=self.new/"ex3-mix/native/identity.json";d=json.loads(p.read_text());d["runtime_identity"]["lock_sha256"]="drift";p.write_text(json.dumps(d))
        self.rejects(report,"native audio runtime identity is not uniform")
    def test_fresh_session_with_different_emulator_identity_is_rejected(self):
        report=self.resumed();p=self.new/"ex3-solo-1/native/identity.json";d=json.loads(p.read_text())
        d["emulator_identity"]["files"][0]["sha256"]="2"*64;d["emulator_identity"]["digest"]=manifest_of(d["emulator_identity"]["files"]);p.write_text(json.dumps(d))
        self.rejects(report,"emulator identity is not uniform")
    def test_nested_resume_origin_is_rejected(self):
        report=self.resumed();self.report["resume_provenance"]={"kind":R.SAME};self.write_old()
        self.rejects(report,"original report changed")
    def test_historical_kind_still_audits_against_its_pin(self):
        report=self.resumed();report["resume_provenance"]["kind"]="strict-partial-audio-resume"
        with self.assertRaises(R.Rejected):self.audit(report)

class OriginAudit(unittest.TestCase):
    def test_origin_audit_accepts_the_same_lineage_kind_and_rejects_unknown_kinds(self):
        import manual_audio_origin_audit as origin
        for kind,ok in ((R.SAME,True),("other-kind",False)):
            with self.subTest(kind):
                try:origin.audit_resumed_audio_sessions(None,{"resume_provenance":{"kind":kind}},{},[],{},tempfile.gettempdir(),{"passed":True})
                except origin.OriginAuditError as error:self.assertFalse(ok);self.assertIn("approved strict resume provenance",str(error))
                except Exception:self.assertTrue(ok)
                else:self.fail("expected a later failure or rejection")

class MainIntegration(Fixture):
    """manual_audio.main() records only the missing examples; a mismatch records nothing."""
    def run_main(self,extra=()):
        calls=[];root=self.root;put(root/"manual/audio-scenes.yaml","source");(root/"manual/generated").mkdir(exist_ok=True)
        (root/"manual").mkdir(exist_ok=True);put(root/"manual/audio.schema.json","audio.schema.json-body");put(root/"tools/manual_capture.py","capture-helpers.py-body")
        put(root/"tools/manual_audio_setups.py","capture-setups.py-body")
        tool=put(self.base/"tool.py","capture-tool.py-body")
        fake_capture=lambda example,tracks,out,options,case:(calls.append(case),(out/"o.wav").write_bytes(b"pcm"),
            {"metrics":{},"evidence":dict(path=str(out),job=dict(job_id="j"),wav_sha256="0"*64),"wav":str(out/"o.wav"),"timeline":[]})[2]
        def run(cmd,**k):
            if cmd[0]=="ffmpeg":Path(cmd[-1]).write_bytes(b"enc")
        class Lock:
            def __enter__(s):return s
            def __exit__(s,*a):return False
        real_open=open
        argv=["manual_audio.py","--mod-code-root",str(self.base),"--audio-install",str(self.installs["audio"]),"--midi-emulator",str(self.emus["midi"]),
              "--midi-controlled-install",str(self.installs["midi"]),"--controlled-local","--resume-from",str(self.old)]+list(extra)
        patches=[patch.object(manual_audio,"ROOT",root),patch.object(manual_audio,"MANUAL",root/"manual"),patch.object(sys,"argv",argv),
            patch.object(manual_audio,"validate",lambda d:dict(examples=copy.deepcopy(AUTHORED))),patch.object(manual_audio,"pin_check",lambda r:{"oilcan":{"commit":"1"}}),
            patch.object(manual_audio,"capture",fake_capture),patch.object(manual_audio.subprocess,"run",run),
            patch.object(manual_audio.subprocess,"check_output",lambda *a,**k:"rev"),patch.object(manual_audio,"__file__",str(tool)),
            patch.object(manual_audio.fcntl,"flock",lambda *a:None),
            patch.object(manual_audio,"open",lambda p,*a,**k:Lock() if str(p)=="/tmp/mosaic-manual-native.lock" else real_open(p,*a,**k),create=True),
            patch.object(R,"encoder_identity",lambda f:{"path":f,"version":"v"}),patch.object(R,"ffmpeg_convert",self.convert),
            patch.dict(os.environ,{"MONOME_EMULATOR":str(self.emus["audio"])}),
            patch.object(R,"_default_session_check",lambda *a:None),patch.object(manual_audio,"audit_example_native",lambda *a:0)]
        for p in patches:p.start();self.addCleanup(p.stop)
        # The run directory is ROOT.parent/mosaic-manual-audio-runs/<uuid>
        runs=root.parent/"mosaic-manual-audio-runs"
        # main() freezes tool/helper/setups hashes into its report; the fixture's old run was frozen from the same bytes
        self.report.update(source_sha256=h(b"source"),tool_sha256=h(b"capture-tool.py-body"),helper_sha256=h(b"capture-helpers.py-body"),
                           setups_sha256=h(b"capture-setups.py-body"),schema_sha256=h(b"audio.schema.json-body"))
        put(self.old/"source.yaml","source");self.write_old()
        code=manual_audio.main();return code,calls,runs
    def test_only_missing_examples_are_recorded_and_all_are_published(self):
        code,calls,runs=self.run_main();self.assertEqual(code,0)
        self.assertEqual(calls,["MA-AUDIO-ex3-SOLO-1","MA-AUDIO-ex3"])
        new=next(iter(runs.iterdir()))
        report=json.loads((new/"report.json").read_text())
        self.assertEqual([r["id"] for r in report["examples"]],["ex1","ex2","ex3"]);self.assertIs(report["passed"],True)
        self.assertEqual(report["resume_provenance"]["kind"],R.SAME)
        self.assertEqual(sorted(p.name for p in (self.root/"manual/audio").iterdir()),["ex1.mp3","ex1.ogg","ex2.mp3","ex2.ogg","ex3.mp3","ex3.ogg"])
        for row in report["examples"]:
            for f in row["files"]:self.assertEqual(row["file_sha256"][f],R.sha(self.root/"manual"/f))
    def test_identity_mismatch_records_nothing_and_leaves_no_run(self):
        self.report["voice_pins"]={"oilcan":{"commit":"other"}}
        code,calls,runs=self.run_main()
        self.assertNotEqual(code,0);self.assertEqual(calls,[])
        self.assertEqual(list(runs.iterdir()),[])
        self.assertFalse((self.root/"manual/audio").exists())

if __name__=="__main__":unittest.main()
