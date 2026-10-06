import hashlib, json, tempfile, unittest, wave
from pathlib import Path
import manual_audio_resume as resume

class ResumeCandidateTests(unittest.TestCase):
    def test_current_producer_accepts_only_original_or_exact_resume_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"manual_audio.py"
            path.write_bytes(b"original producer")
            old=resume.PIN["producer"];adapter=resume.PIN.get("resume_producer")
            resume.PIN["producer"]=resume.sha(path)
            self.assertEqual(resume.check_current_producer(path),resume.PIN["producer"])
            path.write_bytes(b"reviewed exact adapter")
            resume.PIN["resume_producer"]=resume.sha(path)
            self.assertEqual(resume.check_current_producer(path),resume.PIN["resume_producer"])
            path.write_bytes(b"unreviewed edit")
            with self.assertRaisesRegex(resume.Rejected,"neither pinned producer"):
                resume.check_current_producer(path)
            resume.PIN["producer"]=old
            if adapter is None:resume.PIN.pop("resume_producer",None)
            else:resume.PIN["resume_producer"]=adapter

    def test_source_hash_mismatch_is_rejected(self):
        resume.check_hash("source", resume.PIN["source"], resume.PIN["source"])
        with self.assertRaisesRegex(resume.Rejected, "hash mismatch"):
            resume.check_hash("source", "0" * 64, resume.PIN["source"])

    def test_helper_compatibility_is_exact_and_narrow(self):
        example={"id":"swing-comparison","setup":"swing-comparison","sections":[{"changes":[{"kind":"swing"}]}]}
        accepted=resume.helper_compatibility(example,resume.PIN["old_setup"],resume.PIN["new_setup"])
        self.assertEqual(accepted["id"],"swing-comparison")
        with self.assertRaisesRegex(resume.Rejected,"current setup helper"):
            resume.helper_compatibility(example,resume.PIN["old_setup"],"f"*64)
        with self.assertRaisesRegex(resume.Rejected,"fixed reuse inventory"):
            resume.helper_compatibility(dict(example,id="song-sections"),resume.PIN["old_setup"],resume.PIN["new_setup"])
        with self.assertRaisesRegex(resume.Rejected,"named channel"):
            resume.helper_compatibility({"id":"swing-comparison","setup":"swing-comparison",
                "sections":[{"changes":[{"kind":"mute","channel":2}]}]},
                resume.PIN["old_setup"],resume.PIN["new_setup"])

    def make_capture(self, root):
        out=root/"example-mix"; capture=out/"native/audio-captures"/"job-123"
        capture.mkdir(parents=True)
        wav=capture/"output.wav"
        with wave.open(str(wav),"wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b"\x01\x00"*100)
        job={"job_id":"job-123","status":"complete","input_sha256":None,
             "finished":{"frames":100,"expected_frames":100,"xruns":0,"nonfinite":0,"server_dead":False,"sample_rate":8000}}
        (capture/"result.json").write_text(json.dumps(job))
        for name,content in (("results.json","[]"),("recipe.json","[]"),("observations.json","[]"),
                             ("native/actions.jsonl","{}\\n"),("native/cleanup.json",'[{"returncode":0}]'),
                             ("native/identity.json",'{"runtime_identity":{},"session_id":"session-1"}')):
            target=out/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(content)
        receipt=root/"cleanup-receipt.json"
        receipt.write_text(json.dumps({"campaign_report_sha256":resume.PIN["report"],"campaign_uuid":resume.PIN["run"],
          "sessions":[{"session_id":"session-1","lane":"main","actions_jsonl_sha256":resume.sha(out/"native/actions.jsonl"),
           "native_cleanup_sha256":resume.sha(out/"native/cleanup.json"),"session_cleanup_sha256":resume.sha(out/"native/cleanup.json"),
           "action_acks_all_applied_and_identity_matched":True,"action_sequences_from_one_contiguous":True,
           "stop_follows_last_ack":True,"stopped_marker_matches_id":True,"final_grid_keys_down":[],"final_norns_keys_down":[],
           "active_midi_notes_after_log":{},"orphan_note_offs":0,"session_pid_present_at_check":False,
           "cleanup_processes":[{"present_at_check":False,"returncode":0}]}]}))
        return out, wav, job, receipt

    def test_corrupt_wav_or_job_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); out,wav,job,receipt=self.make_capture(root)
            record={"evidence":{"path":str(out),"job":job,"wav_sha256":resume.sha(wav)}}
            old_pin=resume.PIN["cleanup_receipt"];resume.PIN["cleanup_receipt"]=resume.sha(receipt)
            try:resume.verify_capture(root,record,"fixture",receipt)
            finally:resume.PIN["cleanup_receipt"]=old_pin
            wav.write_bytes(wav.read_bytes()+b"x")
            old_pin=resume.PIN["cleanup_receipt"];resume.PIN["cleanup_receipt"]=resume.sha(receipt)
            try:
                with self.assertRaisesRegex(resume.Rejected,"WAV hash"):
                    resume.verify_capture(root,record,"corrupt-wav",receipt)
            finally:resume.PIN["cleanup_receipt"]=old_pin
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); out,wav,job,receipt=self.make_capture(root)
            record={"evidence":{"path":str(out),"job":job,"wav_sha256":resume.sha(wav)}}
            stored=out/"native/audio-captures"/"job-123"/"result.json"
            changed=dict(job,status="failed"); stored.write_text(json.dumps(changed))
            old_pin=resume.PIN["cleanup_receipt"];resume.PIN["cleanup_receipt"]=resume.sha(receipt)
            try:
                with self.assertRaisesRegex(resume.Rejected,"job receipt"):
                    resume.verify_capture(root,record,"corrupt-job",receipt)
            finally:resume.PIN["cleanup_receipt"]=old_pin

    def test_resume_alias_map_is_rederived_from_origin_and_symlink_targets(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);old=root/"old";new=root/"new";old.mkdir();new.mkdir()
            rows={};aliases={}
            for ident in resume.PIN["ids"]:
                source=old/(ident+"-mix");source.mkdir()
                link=new/source.name;link.symlink_to(source,target_is_directory=True)
                rows[ident]={"evidence":{"path":str(source)}}
                aliases[str(link)]=str(source)
            provenance={"evidence_aliases":aliases}
            self.assertEqual(resume.verify_resume_aliases(provenance,rows,old,new),aliases)
            broken=dict(provenance,evidence_aliases={**aliases,str(new/"extra"):str(old/"extra")})
            with self.assertRaisesRegex(resume.Rejected,"alias manifest differs"):
                resume.verify_resume_aliases(broken,rows,old,new)
            link=new/(resume.PIN["ids"][0]+"-mix")
            link.unlink();wrong=old/(resume.PIN["ids"][0]+"-other");wrong.mkdir()
            link.symlink_to(wrong,target_is_directory=True)
            with self.assertRaisesRegex(resume.Rejected,"alias changed"):
                resume.verify_resume_aliases(provenance,rows,old,new)

    def test_missing_provenance_is_rejected_when_durable_marker_is_reachable(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/"resume-run";run.mkdir()
            marker=run/"resume-provenance.required.json"
            marker.write_text('{"required":true}')
            report={"examples":[{"id":"oilcan-pocket","evidence":{"path":str(run/"oilcan-pocket-mix")}}]}
            with self.assertRaisesRegex(resume.Rejected,"requires report provenance"):
                resume.require_resume_provenance(report,run)
            report["resume_provenance"]={"kind":"strict-partial-audio-resume"}
            self.assertTrue(resume.require_resume_provenance(report,run))
            marker.unlink()
            with self.assertRaisesRegex(resume.Rejected,"no durable run marker"):
                resume.require_resume_provenance(report,run)

    def test_current_reused_evidence_paths_must_match_origin_alias_map(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);old=root/"old";new=root/"new";old.mkdir();new.mkdir()
            original={};current=[];aliases={};assets=[]
            for ident in resume.PIN["ids"]:
                mix=old/(ident+"-mix");solo=old/(ident+"-solo");midi=old/(ident+"-midi");mix.mkdir();solo.mkdir();midi.mkdir()
                (new/mix.name).symlink_to(mix,target_is_directory=True)
                (new/solo.name).symlink_to(solo,target_is_directory=True)
                (new/midi.name).symlink_to(midi,target_is_directory=True)
                original[ident]={"id":ident,"evidence":{"path":str(mix),"job":{"job_id":"mix-"+ident}},
                    "solo_contributions":[{"channel":1,"evidence":{"path":str(solo),"job":{"job_id":"solo-"+ident}}}],
                    "musical_evidence":[{"path":str(midi),"identity_sha256":"c"*64}]}
                aliases[str(new/mix.name)]=str(mix);aliases[str(new/solo.name)]=str(solo);aliases[str(new/midi.name)]=str(midi)
                assets.append({"id":ident,"assets":[{"path":"audio/"+ident+".ogg","sha256":"a"*64},
                                                     {"path":"audio/"+ident+".mp3","sha256":"b"*64}]})
            provenance={"evidence_aliases":aliases}
            for ident in resume.PIN["ids"]:
                row=json.loads(json.dumps(original[ident]))
                row["evidence"]["path"]=str(new/(ident+"-mix"))
                row["solo_contributions"][0]["evidence"]["path"]=str(new/(ident+"-solo"))
                row["musical_evidence"][0]["path"]=str(new/(ident+"-midi"))
                row["files"]=[v["path"] for v in next(x["assets"] for x in assets if x["id"]==ident)]
                row["file_sha256"]={v["path"]:v["sha256"] for v in next(x["assets"] for x in assets if x["id"]==ident)}
                current.append(row)
            self.assertTrue(resume.verify_current_reused_rows(original,current,provenance,assets,old,new))
            current[0]["solo_contributions"][0]["evidence"]["path"]=str(old/(resume.PIN["ids"][0]+"-solo"))
            with self.assertRaisesRegex(resume.Rejected,"current reused report row differs"):
                resume.verify_current_reused_rows(original,current,provenance,assets,old,new)
            current[0]["solo_contributions"][0]["evidence"]["path"]=str(new/(resume.PIN["ids"][0]+"-solo"))
            current[0]["musical_evidence"][0]["path"]=str(old/(resume.PIN["ids"][0]+"-midi"))
            with self.assertRaisesRegex(resume.Rejected,"current reused report row differs"):
                resume.verify_current_reused_rows(original,current,provenance,assets,old,new)
            current[0]["musical_evidence"][0]["path"]=str(new/(resume.PIN["ids"][0]+"-midi"))
            current[0]["evidence"]["job"]["job_id"]="swapped-job"
            with self.assertRaisesRegex(resume.Rejected,"current reused report row differs"):
                resume.verify_current_reused_rows(original,current,provenance,assets,old,new)

    def test_cleanup_or_action_log_tampering_is_rejected_against_fixed_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);out,wav,job,receipt=self.make_capture(root)
            record={"evidence":{"path":str(out),"job":job,"wav_sha256":resume.sha(wav)}}
            old_pin=resume.PIN["cleanup_receipt"];resume.PIN["cleanup_receipt"]=resume.sha(receipt)
            try:
                action_path=out/"native/actions.jsonl";original_action=action_path.read_bytes()
                action_path.write_text("tampered\n")
                with self.assertRaisesRegex(resume.Rejected,"action log differs"):
                    resume.verify_capture(root,record,"tampered-actions",receipt)
                action_path.write_bytes(original_action)
                (out/"native/cleanup.json").write_text('[{"returncode":0},{"returncode":0}]')
                with self.assertRaisesRegex(resume.Rejected,"cleanup log differs"):
                    resume.verify_capture(root,record,"tampered-cleanup",receipt)
            finally:resume.PIN["cleanup_receipt"]=old_pin

    def test_successful_reuse_reencodes_and_binds_fresh_hashes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); out,wav,job,receipt=self.make_capture(root)
            source_hash=resume.sha(wav)
            manifest={"passed":False,"complete_regression_run":False,
                      "examples":[{"id":"oilcan-pocket","captures":[
                          {"label":"mix","path":str(out),"job_id":job["job_id"],"wav_sha256":source_hash}]}]}
            report={"examples":[{"id":"oilcan-pocket","bars":4,"bpm":90}]}
            def fake_encoder(ffmpeg, source, target, seconds, codec):
                self.assertEqual(seconds,4*4*60/90)
                target.write_bytes(codec.encode()+b":" + source.read_bytes())
            staged=resume.stage(manifest,root,report,root/"staged","ignored",fake_encoder)
            result=json.loads(staged.read_text())
            self.assertFalse(result["passed"])
            self.assertFalse(result["complete_regression_run"])
            assets=result["staged_encoded_assets"][0]["assets"]
            self.assertEqual([a["codec"] for a in assets],["libopus","libmp3lame"])
            for asset in assets:
                target=staged.parent/asset["path"]
                self.assertEqual(resume.sha(target),asset["sha256"])
                self.assertEqual(asset["source_raw_wav_sha256"],source_hash)
    def test_identity_manifest_rejects_tampered_file_even_if_claimed_digest_is_retained(self):
        files=[{"path":"app.lua","size":4,"sha256":"a"*64}]
        identity={"files":files,"digest":hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}
        self.assertEqual(resume._identity_file_manifest(identity),identity["digest"])
        identity["files"][0]["sha256"]="b"*64
        with self.assertRaisesRegex(resume.Rejected,"does not bind its full file manifest"):
            resume._identity_file_manifest(identity)

    def test_identity_manifest_rejects_truncated_or_reordered_inventory(self):
        files=[{"path":"a.lua","size":1,"sha256":"a"*64},{"path":"b.lua","size":1,"sha256":"b"*64}]
        digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
        with self.assertRaisesRegex(resume.Rejected,"does not bind its full file manifest"):
            resume._identity_file_manifest({"files":files[:1],"digest":digest})
        with self.assertRaisesRegex(resume.Rejected,"not ordered"):
            resume._identity_file_manifest({"files":list(reversed(files)),"digest":digest})

if __name__=="__main__": unittest.main(verbosity=2)
