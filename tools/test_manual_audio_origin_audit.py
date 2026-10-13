"""Path and provenance regressions for mixed-origin audio resume audits."""
import sys
import tempfile
import unittest
import hashlib
import json
import importlib
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

TOOLS=Path(__file__).resolve().parent
sys.path.insert(0,str(TOOLS))
import manual_audio_origin_audit as origin

class AudioOriginAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.old=self.base/"old-run"
        self.new=self.base/"resumed-run"
        self.old.mkdir();self.new.mkdir()
        self.old_capture=self.old/"clip-a";self.old_capture.mkdir()
        self.new_capture=self.new/"clip-b";self.new_capture.mkdir()
        self.alias=self.new/"clip-a"
        self.alias.symlink_to(self.old_capture,target_is_directory=True)
        self.aliases={str(self.alias):str(self.old_capture)}

    def tearDown(self):
        self.temp.cleanup()

    def test_mixed_inventory_binds_reused_alias_and_fresh_run_separately(self):
        result=origin.resolve_capture_origins(
            [(self.alias,self.old_capture),(self.new_capture,self.new_capture)],
            self.aliases,self.old,self.new)
        self.assertEqual([(kind,root) for _,root,kind in result],
                         [("reused",self.old.resolve()),("fresh",self.new.resolve())])

    def test_unlisted_old_capture_cannot_be_relabelled_fresh(self):
        relabel=self.new/"unlisted-old"
        relabel.symlink_to(self.old_capture,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,"missing its exact provenance alias"):
            origin.resolve_capture_origins([(relabel,self.old_capture)],self.aliases,self.old,self.new)

    def test_alias_cannot_point_to_another_old_capture(self):
        other=self.old/"other";other.mkdir()
        bad_aliases={str(self.alias):str(other)}
        with self.assertRaisesRegex(ValueError,"does not bind to its exact original"):
            origin.resolve_capture_origins([(self.alias,self.old_capture)],bad_aliases,self.old,self.new)

    def test_capture_path_cannot_escape_both_declared_origins(self):
        outside=self.base/"outside";outside.mkdir()
        with self.assertRaisesRegex(ValueError,"escapes its declared resumed run"):
            origin.resolve_capture_origins([(outside,outside)],self.aliases,self.old,self.new)

    def test_reused_alias_must_be_a_direct_child_of_old_origin(self):
        nested_parent=self.old/"nested";nested_parent.mkdir()
        nested=nested_parent/"clip";nested.mkdir()
        alias=self.new/"nested-alias";alias.symlink_to(nested,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,"exact original capture"):
            origin.resolve_capture_origins([(alias,nested)],{str(alias):str(nested)},self.old,self.new)

    def test_original_baseline_absolute_paths_rewrite_only_through_aliases(self):
        source=self.old/"clip-a"/"results.json";source.write_text("{}")
        alias_file=self.alias/"results.json"
        row={"evidence":{"path":str(source)}}
        rewritten=origin.rewrite_origin_paths(row,{str(alias_file):str(source)})
        self.assertEqual(rewritten["evidence"]["path"],str(alias_file))
        with self.assertRaisesRegex(ValueError,"absent from verified aliases"):
            origin.rewrite_origin_paths({"path":str(self.old/"missing.json")},{})

    def complete_fixture(self):
        old=self.base/"origin-old";new=self.base/"origin-new";current=self.base/"current"
        old.mkdir();new.mkdir();current.mkdir()
        old_app=old/"application";new_app=new/"application";old_app.mkdir();new_app.mkdir()
        old_out=old/"clip-a";new_out=new/"clip-b";old_out.mkdir();new_out.mkdir()
        alias=new/"clip-a";alias.symlink_to(old_out,target_is_directory=True)
        for out,app in ((old_out,old_app),(new_out,new_app)):
            native=out/"native";native.mkdir()
            (native/"identity.json").write_text(json.dumps({
                "application_identity":{"code_root":str(app),"files":[]}
            }))
            (out/"results.json").write_text("[]")
            (out/"observations.json").write_text("[]")
        oldrow={"id":"reused","evidence":{"path":str(old_out)}}
        current_oldrow={"id":"reused","evidence":{"path":str(alias)}}
        freshrow={"id":"fresh","evidence":{"path":str(new_out)}}
        original=old/"report.json";original.write_text(json.dumps({"examples":[oldrow]}))
        (new/"audio-scenes.json").write_text(json.dumps({
            "passed":True,"source_sha256":"source-pin","examples":[freshrow]
        }))
        (new/"capture-tool.py").write_text("tool")
        (new/"capture-helpers.py").write_text("helper")
        (new/"capture-setups.py").write_text("setup")
        source_paths={}
        for rel,content in (("tools/manual_audio.py","tool"),("tools/manual_capture.py","helper"),
                            ("tools/manual_audio_setups.py","setup")):
            path=current/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
            source_paths[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
        module=SimpleNamespace(
            ROOT=current,
            check_audio_native_session=lambda *args: None,
            capture_application_root=lambda out: (old_app if Path(out)==old_out else new_app).resolve(),
            audio_scale_phase_rows=lambda example,results: [],
            check_scale_phase_frame=lambda *args: None,
            verify_cached_ui=lambda *args: None,
        )
        authored={"examples":[
            {"id":"reused","tracks":[{"channel":1,"voice":"v1"}]},
            {"id":"fresh","tracks":[{"channel":1,"voice":"v1"}]},
        ]}
        report={"source_sha256":"source-pin","examples":[current_oldrow,freshrow],
            "tool_sha256":source_paths["tools/manual_audio.py"],
            "helper_sha256":source_paths["tools/manual_capture.py"],
            "setups_sha256":source_paths["tools/manual_audio_setups.py"],
            "resume_provenance":{"kind":"strict-partial-audio-resume",
                "original_run":str(old),"original_report":str(original),
                "reused_ids":["reused"],"evidence_aliases":{str(alias):str(old_out)}}}
        sessions=[(old_out,"real-time",True),(new_out,"real-time",True)]
        return module,report,authored,sessions,{old_out:{},new_out:{}},new,old,alias,source_paths

    def test_partial_fixture_audits_each_origin_without_claiming_full_inventory(self):
        module,report,authored,sessions,by_session,new,old,alias,_=self.complete_fixture()
        result=origin.audit_resumed_audio_sessions(
            module,report,authored,sessions,by_session,new,{"passed":True})
        self.assertEqual(result["origin_sessions"],{"reused":1,"fresh":1})
        self.assertFalse(result["complete_regression_run"])
        self.assertFalse(result["all_audio_inventory_captured"])
        self.assertEqual(result["observed_examples"],2)
        self.assertEqual(result["expected_examples"],2)
        self.assertEqual(result["dsp_sessions"],2)

    def test_mixed_origin_requires_successful_strict_resume_audit(self):
        module,report,authored,sessions,by_session,new,*_=self.complete_fixture()
        with self.assertRaisesRegex(ValueError,"strict audio resume provenance"):
            origin.audit_resumed_audio_sessions(
                module,report,authored,sessions,by_session,new,{"passed":False})

    def test_publication_dispatch_runs_strict_resume_validator_before_origin_audit(self):
        verifier=importlib.import_module("manual_publication_verify")
        resume=importlib.import_module("manual_audio_resume")
        audio=importlib.import_module("manual_audio")
        fake_manual=self.base/"manual";fake_manual.mkdir()
        (fake_manual/"audio-scenes.yaml").write_text("{}")
        report_path=self.base/"report.json"
        report={"examples":[{"evidence":{"path":str(self.new/"capture")}}],
            "validation_scope":"controlled-manual-generation","realtime_qualification":"pending-ci",
            "clock_mode":"controlled-experimental","audio_capture_clock_mode":"real-time",
            "complete_regression_run":False,"controlled_lane":"inapplicable:no-controlled-audio"}
        report_path.write_text(json.dumps(report))
        order=[]
        with patch.object(verifier,"MANUAL",fake_manual), \
             patch.object(verifier,"check_canonical_audio_lessons"), \
             patch.object(verifier,"check_audio_capture_scope",return_value=[]), \
             patch.object(verifier,"audio_session_examples",return_value={}), \
             patch.object(resume,"require_resume_provenance",side_effect=lambda *a: True), \
             patch.object(resume,"audit_resume_provenance",side_effect=lambda *a,**k: order.append("strict") or {"passed":True}), \
             patch("manual_audio_origin_audit.audit_resumed_audio_sessions",side_effect=lambda *a: order.append("origin") or {"passed":True}):
            result=verifier.audit_audio_session_integrity(report_path,controlled_local=True)
        self.assertEqual(result,{"passed":True})
        self.assertEqual(order,["strict","origin"])

    def test_reused_row_cannot_be_relabelled_to_fresh_capture(self):
        module,report,authored,sessions,by_session,new,old,alias,_=self.complete_fixture()
        report["resume_provenance"]["reused_ids"]=["fresh"]
        with self.assertRaisesRegex(ValueError,"relabels reused/fresh"):
            origin.audit_resumed_audio_sessions(
                module,report,authored,sessions,by_session,new,{"passed":True})

    def test_fresh_capture_source_must_match_frozen_run(self):
        module,report,authored,sessions,by_session,new,old,alias,source_paths=self.complete_fixture()
        # All source pins are changed together in the report and frozen current run,
        # but not in the current producer tree.
        report.update(tool_sha256="wrong",helper_sha256="wrong",setups_sha256="wrong")
        with self.assertRaisesRegex(ValueError,"stale frozen source"):
            origin.audit_resumed_audio_sessions(
                module,report,authored,sessions,by_session,new,{"passed":True})

    def test_editorial_publication_audits_the_frozen_recording_tool_not_the_current_one(self):
        module,report,authored,sessions,by_session,new,old,alias,source_paths=self.complete_fixture()
        (module.ROOT/"tools/manual_audio.py").write_text("newer audit tooling")
        with self.assertRaisesRegex(ValueError,"stale frozen source"):
            origin.audit_resumed_audio_sessions(module,report,authored,sessions,by_session,new,{"passed":True})
        report["publication"]=dict(kind="editorial-refresh",native_source_sha256=report["source_sha256"])
        origin.audit_resumed_audio_sessions(module,report,authored,sessions,by_session,new,{"passed":True})
        (new/"capture-tool.py").write_text("tampered recording tool")
        with self.assertRaisesRegex(ValueError,"stale frozen source"):
            origin.audit_resumed_audio_sessions(module,report,authored,sessions,by_session,new,{"passed":True})
        
if __name__=="__main__":
    unittest.main()
