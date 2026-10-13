"""Synthetic fresh-projection regressions over the frozen full native fixtures.

The derived-unit-fixture label is intentional: this suite is not CI or real-time
qualification.
"""
import copy
import gzip
import hashlib
import json
import sys
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

OVERLAY=Path(__file__).resolve().parents[1]
CANDIDATE=Path("/home/andy/mosaic-manual-build-operators/round4-fix-integration-20261007-03/scratch")
sys.path.insert(0,str(OVERLAY/"tools"))
sys.path.insert(1,str(CANDIDATE/"tools"))
from manual_fresh_target_midi import build_fresh_target_midi_manifest, validate_fresh_target_midi_manifest
from manual_reader_projection import build_projection, write_projection, _canonical_bytes, ProjectionError
import manual_publication_verify as verifier

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

class FreshTargetProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        with gzip.open(CANDIDATE/"test-fixtures/retained-target-midi-v1/fixture.json.gz","rb") as f:
            self.fixtures=json.load(f)

    def load(self,dialect):
        item=copy.deepcopy(self.fixtures[dialect])
        scene=item["scene"]
        source=self.root/dialect
        for name,text in item["files"].items():
            path=source/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text)
        if dialect=="doctor":
            pub=item["publication"]
            run=pub["evidence"]["runs"][0]
            run["report"]=str(source/"report.json")
            run["report_sha256"]=sha((source/"report.json").read_bytes())
            pub_path=self.root/"manual"/scene["data_path"]
            pub_path.parent.mkdir(parents=True,exist_ok=True)
            pub_path.write_text(json.dumps(pub))
        else:
            scene["evidence"]["path"]=str(source)
            for name,key in (
                ("results.json","results_sha256"),
                ("native/identity.json","identity_sha256"),
                ("native/native-events.jsonl","native_events_sha256"),
                ("capture-trace.json","capture_trace_sha256"),
                ("session-context.json","session_context_sha256"),
            ):
                scene["evidence"][key]=sha((source/name).read_bytes())
        return scene,source

    def manifest(self,scene):
        return build_fresh_target_midi_manifest([scene],self.root,self.root,"derived-unit-fixture")

    def projected(self,scene,manifest):
        raw=_canonical_bytes(manifest)
        book={"features":[],"scenes":{scene["id"]:scene}}
        index,chunks=build_projection(book,{"examples":[]},project_root=self.root,
            fresh_target_midi_manifest=raw,fresh_target_midi_sha256=sha(raw),fresh_build_root=self.root)
        ref=index["scene_chunks"][scene["id"]]
        return index,json.loads(chunks[ref["path"]]),raw

    def test_frozen_full_panic_journal_reaches_projected_chunk_and_independent_audit(self):
        scene,source=self.load("panic")
        manifest=self.manifest(scene)
        index,projected,raw=self.projected(scene,manifest)
        receipt=projected["steps"][-1]["output"]["midi"]
        journal=[json.loads(x) for x in (source/"native/native-events.jsonl").read_text().splitlines() if x]
        native=[row for row in journal if row.get("kind") in (3,11)]
        self.assertEqual(receipt["events"],native[-6144:])
        self.assertEqual(receipt["total"],6144)
        self.assertEqual(receipt["provenance"]["window_start_index"],native[-6144]["index"])
        self.assertEqual(receipt["provenance"]["window_end_index"],native[-1]["index"])
        self.assertEqual(receipt["provenance"]["complete_native_event_count"],len(native))
        self.assertFalse(receipt["truncated"])
        release=[row for row in receipt["events"] if row.get("port")==1 and row.get("bytes")==[128,60,0]]
        self.assertEqual(len(release),1,"sounding-note target release must come from the actual native journal")
        self.assertEqual(index["canonical_inputs"]["fresh_target_midi_qualification"],"derived-unit-fixture")

        generated=self.root/"manual/generated"
        generated.mkdir(parents=True,exist_ok=True)
        book={"features":[],"scenes":{scene["id"]:scene}}
        (generated/"book.json").write_text(json.dumps(book))
        (generated/"audio-scenes.json").write_text(json.dumps({"examples":[]}))
        manifest_path=self.root/"fresh-target-midi-manifest.json"
        manifest_path.write_bytes(raw)
        projection_book=generated/"book.json"
        projection_audio=generated/"audio-scenes.json"
        write_projection(projection_book,projection_audio,generated,project_root=self.root,
            fresh_target_midi_manifest=manifest_path,fresh_target_midi_sha256=sha(raw),fresh_build_root=self.root)
        log=self.root/"fresh-target-midi-producer.log"
        log.write_text('{"passed":true,"qualification":"derived-unit-fixture"}\n')
        (self.root/"fresh-target-midi-producer.json").write_text(json.dumps({
            "name":"fresh-target-midi-producer","passed":True,"returncode":0,
            "log_sha256":sha(log.read_bytes()),
            "fresh_target_midi_manifest":{"path":str(manifest_path.resolve()),"sha256":sha(raw),
                "qualification":"derived-unit-fixture"},
            "fresh_target_midi_producer_sha256":sha((OVERLAY/"tools/manual_fresh_target_midi.py").read_bytes()),
        }))
        tool_copy=self.root/'tools'
        tool_copy.mkdir(exist_ok=True)
        for name in ('manual_reader_projection.py','manual_fresh_target_midi.py'):
            shutil.copyfile(OVERLAY/'tools'/name,tool_copy/name)
        old_root,old_manual=verifier.ROOT,verifier.MANUAL
        verifier.ROOT=self.root
        verifier.MANUAL=self.root/"manual"
        self.addCleanup(setattr,verifier,"ROOT",old_root)
        self.addCleanup(setattr,verifier,"MANUAL",old_manual)
        report=verifier.audit_reader_projection(fresh_target_midi_manifest=manifest_path,
            fresh_target_midi_sha256=sha(raw),fresh_build_root=self.root)
        self.assertEqual(report["fresh_target_midi_qualification"],"derived-unit-fixture")
        self.assertEqual(report["fresh_target_midi_manifest_sha256"],sha(raw))

    def test_build_plan_wires_fresh_producer_before_projection_and_audit(self):
        from types import SimpleNamespace
        sys.path.insert(0,str(OVERLAY/"tools"))
        import manual_build as builder
        old_root=builder.ROOT
        builder.ROOT=CANDIDATE
        self.addCleanup(setattr,builder,"ROOT",old_root)
        options=SimpleNamespace(real_install="/real",emulator="/emu",audio_emulator="/audio-emu",
            audio_install="/audio-install",mod_code_root="/mods",ffmpeg="ffmpeg",
            controlled_install="/controlled",modulation_code_root="/mod-code",
            modulation_emulator="/mod-emu",modulation_controlled_install="/mod-controlled",
            readability_real_install="/readability-real",browser_tests=False,python="python3",
            node="node",quick_output="manual/generated/quick-reference.html",
            resume_from=None,retained_midi_admissions=None,retained_midi_admissions_sha256=None)
        stages=builder.plan(options,["scene-plans-lead-panic.yaml"],controlled_local=False)
        names=[row["name"] for row in stages]
        self.assertLess(names.index("fresh-target-midi-producer"),names.index("reader-projection"))
        self.assertLess(names.index("reader-projection"),names.index("publication-audit"))
        for name in ("reader-projection","publication-audit"):
            command=next(row["command"] for row in stages if row["name"]==name)
            self.assertIn("--fresh-target-midi-manifest",command)
            self.assertIn("{fresh-midi-sha256}",command)
            self.assertIn("--fresh-build-root",command)
            self.assertNotIn("--retained-midi-admissions",command)
        capture=next(row["command"] for row in stages if row["name"]=="reference-real-scene-plans-lead-panic-base-midi")
        self.assertEqual(capture[capture.index("--output-root")+1],"{evidence}/scene-captures")
        controlled=builder.plan(options,["scene-plans-lead-panic.yaml"],controlled_local=True)
        self.assertFalse(any(row["name"]=="fresh-target-midi-producer" for row in controlled))
        self.assertFalse(any("--fresh-target-midi-manifest" in row["command"] for row in controlled))

    def test_producer_cli_writes_manifest_from_argparse_paths(self):
        scene,source=self.load("panic")
        book=self.root/"book.json"
        book.write_text(json.dumps({"scenes":{scene["id"]:scene}}))
        output=self.root/"build"/"fresh"/"manifest.json"
        result=subprocess.run([
            sys.executable,str(OVERLAY/"tools/manual_fresh_target_midi.py"),
            "--book",str(book),"--project-root",str(self.root),
            "--build-root",str(self.root),"--output",str(output),
            "--qualification","derived-unit-fixture",
        ],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(output.is_file())
        manifest=json.loads(output.read_text())
        records=validate_fresh_target_midi_manifest([scene],self.root,self.root,manifest)
        self.assertEqual(manifest["qualification"],"derived-unit-fixture")
        self.assertEqual(records[scene["id"]]["source_root"],str(source.resolve()))
        self.assertEqual(manifest["realtime_qualification"],"pending-ci")

    def test_frozen_kind3_doctor_journal_rejects_sequence_and_timestamp_corruption(self):
        for mode in ("sequence-swapped","sequence-duplicate","timestamp-swapped","timestamp-duplicate","timestamp-backwards"):
            with self.subTest(mode=mode):
                scene,source=self.load("doctor")
                journal=source/"native/native-events.jsonl"
                rows=[json.loads(line) for line in journal.read_text().splitlines() if line]
                midi=[row for row in rows if row.get("kind")==3]
                a,b=midi[20],midi[21]
                if mode=="sequence-swapped":
                    a["sequence"],b["sequence"]=b["sequence"],a["sequence"]
                elif mode=="sequence-duplicate":
                    b["sequence"]=a["sequence"]
                elif mode=="timestamp-swapped":
                    a["monotonic_ns"],b["monotonic_ns"]=b["monotonic_ns"],a["monotonic_ns"]
                elif mode=="timestamp-duplicate":
                    b["monotonic_ns"]=a["monotonic_ns"]
                else:
                    b["monotonic_ns"]=a["monotonic_ns"]-1
                journal.write_text("".join(json.dumps(row,separators=(",",":"))+"\n" for row in rows))
                manifest=self.manifest(scene)
                with self.assertRaisesRegex(ValueError,"native MIDI (sequence changed|timestamps are duplicate or out of order)"):
                    self.projected(scene,manifest)

    def test_frozen_doctor_native_window_reaches_chunk_from_current_manifest(self):
        scene,source=self.load("doctor")
        manifest=self.manifest(scene)
        _,projected,_=self.projected(scene,manifest)
        midi=projected["steps"][-1]["output"]["midi"]
        native=[json.loads(x) for x in (source/"native/native-events.jsonl").read_text().splitlines() if x]
        midi_rows=[row for row in native if row.get("kind") in (3,11)]
        self.assertEqual(midi["events"],midi_rows[10:98])
        self.assertEqual(midi["total"],88)
        self.assertEqual(midi["provenance"]["kind"],"fresh-native-doctor-play-window-v1")

    def test_rejects_truncated_or_malformed_journal_after_resealing_fixture_manifest(self):
        for mode in ("truncated","malformed"):
            with self.subTest(mode=mode):
                scene,source=self.load("panic")
                journal=source/"native/native-events.jsonl"
                rows=journal.read_text().splitlines()
                if mode=="truncated":
                    rows.pop(100)
                    journal.write_text("\n".join(rows)+"\n")
                else:
                    rows[100]="{bad json"
                    journal.write_text("\n".join(rows)+"\n")
                manifest=self.manifest(scene)
                with self.assertRaises((ValueError,KeyError,json.JSONDecodeError)):
                    self.projected(scene,manifest)

    def test_rejects_snapshot_tail_mismatch_even_when_fixture_manifest_is_resealed(self):
        scene,source=self.load("panic")
        path=source/"observations.json"
        observations=json.loads(path.read_text())
        found=None
        for observation in observations:
            for packet in observation["state"]["midi"]:
                if packet["index"]==5000:
                    packet["monotonic_ns"]+=1
                    found=packet
                    break
            if found:break
        self.assertIsNotNone(found,"frozen fixture must retain a snapshot for packet 5000")
        path.write_text(json.dumps(observations))
        manifest=self.manifest(scene)
        with self.assertRaisesRegex(ValueError,"differs from snapshot"):
            self.projected(scene,manifest)

    def test_rejects_source_tamper_after_fresh_manifest_creation(self):
        scene,source=self.load("panic")
        manifest=self.manifest(scene)
        path=source/"native/native-events.jsonl"
        path.write_text(path.read_text()+" ")
        with self.assertRaisesRegex(ValueError,"fresh source changed"):
            self.projected(scene,manifest)

    def test_rejects_current_target_frame_or_expectation_mutation(self):
        scene,source=self.load("panic")
        manifest=self.manifest(scene)
        scene["steps"][-1]["expect"]["assertion"]["passed"]=False
        with self.assertRaisesRegex(ValueError,"fresh scene target changed"):
            self.projected(scene,manifest)

    def test_rejects_foreign_run_root_and_wrong_manifest_pin(self):
        scene,source=self.load("panic")
        manifest=self.manifest(scene)
        manifest["build_root"]=str(source)
        raw=_canonical_bytes(manifest)
        with self.assertRaisesRegex(ValueError,"foreign fresh build root"):
            build_projection({"features":[],"scenes":{scene["id"]:scene}},{"examples":[]},
                project_root=self.root,fresh_target_midi_manifest=raw,
                fresh_target_midi_sha256=sha(raw),fresh_build_root=self.root)
        manifest=self.manifest(scene)
        raw=_canonical_bytes(manifest)
        with self.assertRaisesRegex(ProjectionError,"caller pin"):
            build_projection({"features":[],"scenes":{scene["id"]:scene}},{"examples":[]},
                project_root=self.root,fresh_target_midi_manifest=raw,
                fresh_target_midi_sha256="0"*64,fresh_build_root=self.root)

if __name__=="__main__":
    unittest.main()
