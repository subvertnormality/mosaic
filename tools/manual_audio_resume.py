"""External-only strict reuse qualification for one preserved partial audio run."""
from __future__ import annotations
import argparse, base64, copy, hashlib, json, os, shutil, subprocess, sys, traceback
from pathlib import Path

PIN = {
 "run":"57d9c7f4ab5d4ee8a0228b15aaacbc8d",
 "report":"f36318c05f2ec7ed0abc8293a683f0867f8a2eb0f394e0092501d770325ee9d0",
 "source":"ae599085b1e45e616da601c7cf0a579103f7e94ff6af885267eea7a99e0ebdea",
 "schema":"1722f08f8e7658a1c65a977089bfb351041e347e6e4e6bde93b81aae0023516d",
 "producer":"cb97c235125ea19cc21dda112e2ca38feeb930bc3239160a885d5f7a406bfc0a",
 "resume_producer":"de1471ed2b2e96015216b19ff18412d8daa7b4f32ee9691ff720b7e96bafa9ec",
 "capture_helper":"96cc9b6b3eccb88457f878654eab3201ba9319c1869ae6fc7cfe12394b229d80",
 "old_setup":"c62c34fc780de905b5e8f4df46dd6f5055f849adc49eb1a7fce08a31a858c58e",
 "new_setup":"c34d6adc634d4a49c805d8c565d31e6c0c9573a98ce1934cddeb70f82f698f93",
 "audio_runtime":"5407668e11d4dce6176a7909539f50440a6a162c8100545d3044c7ad804100fd",
 "midi_runtime":"64cf3f1b2fcaa19bdaa5c27cf1ae8e0d4dc3faa2fdb040100cd8be85888822e2",
 "harness":{
  "driver.py":"924cf69c0c32ce6e06657587585ed893ba72ce5af5ee288a5a3b4fbf81e47007",
  "ui.py":"1382109a56d940e3abae4ad6585b8c51d801b05b63665b41a432725072c56d8e",
  "ui_map.py":"8fb570618c8076b9f0ef1073f7599e170933ba108ad15fc486730af16116685f",
  "pcm_oracle.py":"f5ce34d7701440e964f26d984db21c2bc07a968d12195cb7dd242c31f9e55d15",
  "channel_gestures.py":"ea1b01c6477c301c7f06a50f6ca345e87d2df3760553c462d02e1420c232f707"},
 "ids":["oilcan-pocket","bass-and-intervals","three-voice-conversation","ghost-note-comparison","scale-slot-comparison","swing-comparison","note-merge-modes","polymeter"],
 "examples":21,"wavs":54,"audio_app":"5e1babd72fd1be2d7489264573321173e5462de30861d27a41022bff4af22810","midi_app":"f002b99e0cc5488761716f44fd2ee6a74d7587c86c818a7c7fb794e42292423a","audio_emu":"d1acf81b425fb367176b62a03f40a6a957be91c70d64cecd92f3584c78dd9682","midi_emu":"30ff229fb2dd8138cc9f8a43819650e7e5a64290bf79c11c0572c4e5e2359863","identity_receipt":"5525f92b88de545d0d96d9db5d00264ac5a1b1970e60495a553eeb810337cefc",
 "cleanup_receipt":"a76f0285f6acca24c16d3e4d36b45b24539d46730f18640486e1e2e4f0f0fbe7",
 "native_identity_files":{"bass-and-intervals-mix/native/identity.json":"30fce86f930995f94726c12a288c9f1c7467f6ec066c2bd0b84c063834706f36","bass-and-intervals-solo-1/native/identity.json":"f49f23f2fe87227ff9ab3ed7cd95de025e4a1d9e3ca08c0ee0c2d1fd68456ec2","bass-and-intervals-solo-2/native/identity.json":"45321d7ad6d92cbf4c969f0f702ee61548d368e6ade3047ae50050965bdd0a49","ghost-note-comparison-midi-controlled-experimental/native/identity.json":"6899725bdeb4b39c14dd9649246c7c5b12eeaaf960a910258daa0da3c69e6571","ghost-note-comparison-mix/native/identity.json":"5cc7812dc5b26aca6e8de67d89f9216e841f002ca549e9131d1881456fc4591b","ghost-note-comparison-solo-1/native/identity.json":"9cd1d4def4f49ae5c22d94d0d00d620d7dda52a8ecab2beb8c5054781c3da444","note-merge-modes-midi-controlled-experimental/native/identity.json":"ca2fab3e66dd30fcdd27796f7f033c6c169b4bc5f99f41727c6bc9f947335a68","note-merge-modes-mix/native/identity.json":"4f00a22b5dc2b57fb586f094a956b1a84f11f0aae6aa2591c79108e765c2bf79","note-merge-modes-solo-1/native/identity.json":"6dab5dda2e06d81ea647b5477fd93fc9de48d0f1ee6f77840e3879a40c3a02d8","oilcan-pocket-mix/native/identity.json":"70d55752b11175ee7a78eb7a9a436015a5c3048155a217e76ac72c853d1e458c","oilcan-pocket-solo-1/native/identity.json":"bc8d3c652343a982d675f307fc4ebf6f7ea4c81e409acca1a44d68f36be47bf0","polymeter-midi-controlled-experimental/native/identity.json":"dcb8189728e5b2cbcf915ef74a1097d0257033a5fd605991ddc9afb064d2746b","polymeter-mix/native/identity.json":"7e3fcad370d4666fbc1be2f619a3c14ae3a5ad45ec427729c8ad9db70b119738","polymeter-solo-1/native/identity.json":"6e9a63e20b8e7bf0a996bf5ea21233251ede6e34001a2b336c12a63304b86558","polymeter-solo-2/native/identity.json":"839ae2cbbbb1df08bf4a8e32ebdce6375ea7ec90ab4ca7e26d837e8a950e9ec3","scale-slot-comparison-midi-controlled-experimental/native/identity.json":"5482dee52750fdaa9eafb815cfc7e3d249b459064bc9b12aa718b5a3aaec53df","scale-slot-comparison-mix/native/identity.json":"e737c16c701bbda2e1dcccae254dd7a1f3e9f17d4971ff72cd93fcdc3b5b378d","scale-slot-comparison-solo-1/native/identity.json":"e1aaadc31a578a529b63aeab29fdf072ad6ab9acc25e58fc921d6e3cb365b9c4","scale-slot-comparison-solo-2/native/identity.json":"397134465b58f3c551e6d1d8000554b90cd294dfa56c0aea31b102bef72d7d00","song-sections-midi-controlled-experimental/native/identity.json":"db1935bd0f54d41ecbbe74c0e6394c811939dd1d4537c230f96fa49a58548751","song-sections-solo-1/native/identity.json":"b36fd66b20b7fb6c006ad04d4f9ea9947df49b1a2c1aab3566a3a96ccef0ffd0","swing-comparison-midi-controlled-experimental/native/identity.json":"b3149eb54c3db7abe71e2cc64c534bbf6676d0c52cb1d4cf4e1cc3aa0ec38cb8","swing-comparison-mix/native/identity.json":"5ab4795cc13723e295d1d6c748dd8a237f773ea5d2e65a60c35bc5154700c874","swing-comparison-solo-1/native/identity.json":"691ba3e4716c7d86996cd9b056a4d6adb7b559cf63a06824ee4871963d9f3afc","swing-comparison-solo-2/native/identity.json":"877538d7abb9c83c61a5a2b0c83cb8a17595496cd1cc4234da9fe62d7cd5c9e7","three-voice-conversation-mix/native/identity.json":"f493ffa550e8600e0652c4af9f16ff516b1cff0caa63f9c596fcad175ebe6f3c","three-voice-conversation-solo-1/native/identity.json":"732d63ec2ae8ba208a5cc7a7a4177a2093c70b3bcd879886ee1608f66594421a","three-voice-conversation-solo-2/native/identity.json":"a07dfa643b155777b8d51eee996be21c7a656a620400678f310da80ebb82359a","three-voice-conversation-solo-3/native/identity.json":"edeff5a5fd031495ce23024c1795c262102e1efcf6d20e4af58cde4c3ca4b9c4"}}
def origin_fixture(name):
 return Path(__file__).resolve().parents[1]/"tests/fixtures/manual-audio-resume-origin-v1"/name

class Rejected(ValueError): pass
def need(ok,msg):
 if not ok: raise Rejected(msg)
def check_hash(label, actual, expected):
 need(actual==expected,str(label)+" hash mismatch")
def check_current_producer(path):
 actual=sha(path)
 allowed={PIN["producer"]}
 if PIN.get("resume_producer"):allowed.add(PIN["resume_producer"])
 need(actual in allowed,"current manual_audio.py is neither pinned producer nor reviewed resume adapter")
 return actual
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()
def canon(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def inside(path,parent):
 path=Path(path).resolve(strict=True); parent=Path(parent).resolve(strict=True)
 need(path==parent or parent in path.parents,"path escapes run: "+str(path))
 return path
def appmap(root):
 out={}
 for name in ("mosaic.lua",):
  p=root/name; need(p.is_file(),"missing application "+name); out[name]=sha(p)
 for prefix in ("lib","docs/ui-reimplementation/code"):
  base=root/prefix; need(base.is_dir(),"missing application tree "+prefix)
  for p in sorted(base.rglob("*")):
   excluded=prefix=="lib" and any(part in ("tests",".git","__pycache__") for part in p.relative_to(base).parts)
   if p.is_file() and not excluded: out[p.relative_to(root).as_posix()]=sha(p)
 return out
def run_appmap(run):
 base=run/"application"; need(base.is_dir(),"missing frozen application")
 return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob("*")) if p.is_file()}
def helper_compatibility(example,old_hash,new_hash):
 need(old_hash==PIN["old_setup"],"unsupported old setup helper")
 need(new_hash==PIN["new_setup"],"unsupported current setup helper")
 need(example["id"] in PIN["ids"],"example outside fixed reuse inventory")
 need(example.get("setup") in (None,"swing-comparison","note-merge-modes"),"unsupported setup kind")
 changes=[c for s in example.get("sections",[]) for c in s.get("changes",[])]
 need(all("channel" not in c for c in changes),"helper delta could affect named channel")
 return {"old_sha256":old_hash,"current_sha256":new_hash,"id":example["id"],
         "basis":"exact hash pair and allowlist; no completed section change names a channel"}
def current_voice_pins(root):
 lock=json.loads((root/"manual/voices.lock.json").read_text())
 return {name:lock[name] for name in ("oilcan","nb_polyperc","doubledecker")}
def _identity_file_manifest(identity):
 files=identity.get("files")
 need(isinstance(files,list) and files,"identity has no file manifest")
 paths=[row.get("path") for row in files]
 need(all(isinstance(v,str) and v for v in paths) and len(paths)==len(set(paths)),"identity file path set invalid")
 need(paths==sorted(paths),"identity file manifest is not ordered")
 digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
 need(digest==identity.get("digest"),"identity digest does not bind its full file manifest")
 return digest
def verify_native_source_identities(run,receipt_path):
 expected_paths=set(PIN["native_identity_files"])
 actual_paths={p.relative_to(run).as_posix():p for p in run.glob("*/native/identity.json")}
 need(set(actual_paths)==expected_paths,"native identity file inventory changed")
 for rel,p in actual_paths.items():
  need(sha(p)==PIN["native_identity_files"][rel],"native identity JSON changed: "+rel)
 receipt_path=Path(receipt_path).resolve(strict=True)
 need(sha(receipt_path)==PIN["identity_receipt"],"independent runtime identity receipt changed")
 receipt=json.loads(receipt_path.read_text())
 need(receipt.get("original_report_sha256")==PIN["report"],"independent receipt names another report")
 checks={row["identity_path"]:row for row in receipt.get("session_identity_checks",[])}
 seen_audio=set(); audio_app=set(); midi_app=set(); audio_emu=set(); midi_emu=set()
 for p in run.glob("*/native/identity.json"):
  ident=json.loads(p.read_text()); is_midi="-midi-" in p.parent.parent.name
  app=ident.get("application_identity",{}); emu=ident.get("emulator_identity",{})
  app_hash=_identity_file_manifest(app); emu_hash=_identity_file_manifest(emu)
  app_pin=PIN["midi_app"] if is_midi else PIN["audio_app"]
  emu_pin=PIN["midi_emu"] if is_midi else PIN["audio_emu"]
  need(app_hash==app_pin and emu_hash==emu_pin,"native app/emulator digest mismatch")
  if not is_midi:
   code=Path(app["code_root"]).resolve(strict=True)
   for item in app["files"]:
    f=code/item["path"]
    need(f.is_file() and f.stat().st_size==item["size"] and sha(f)==item["sha256"],"native app source changed: "+item["path"])
   row=checks.get(str(p)); need(row is not None,"audio identity missing independent parity row")
   need(row.get("identity_file_sha256")==sha(p),"audio identity file hash differs from parity receipt")
   need(row.get("application_files_equal_current") is True and row.get("emulator_files_equal_current") is True
        and row.get("runtime_identity_equal_current_install") is True,"independent source parity failed")
   need(row.get("application_digest")==app_pin and row.get("emulator_digest")==emu_pin,"parity receipt digest mismatch")
   seen_audio.add(str(p))
  (midi_app if is_midi else audio_app).add(app_hash)
  (midi_emu if is_midi else audio_emu).add(emu_hash)
 need(seen_audio==set(checks),"audio identity set differs from independent parity receipt")
 need(audio_app=={PIN["audio_app"]} and midi_app=={PIN["midi_app"]},"application identity classes changed")
 need(audio_emu=={PIN["audio_emu"]} and midi_emu=={PIN["midi_emu"]},"emulator identity classes changed")
 return {"application_sha256":{"audio":PIN["audio_app"],"controlled_midi":PIN["midi_app"]},
         "emulator_sha256":{"audio":PIN["audio_emu"],"controlled_midi":PIN["midi_emu"]},
         "source_parity_receipt_sha256":PIN["identity_receipt"]}
def verify_harness_lineage(root,run,report):
 root=Path(root).resolve(strict=True);run=Path(run).resolve(strict=True)
 need(report.get("harness_sha256")==PIN["harness"],"historical harness map changed")
 driver_lineage=None
 for name,h in PIN["harness"].items():
  if name=="driver.py":
   need(sha(run/name)==h,"historical run Driver identity mismatch")
   from manual_audio_driver_lineage import verify_driver_lineage
   driver_lineage=verify_driver_lineage(root,run,report)
  else:
   need(sha(run/name)==h and sha(root/"tests/behaviour"/name)==h,"harness identity mismatch: "+name)
 need(driver_lineage is not None,"historical/current Driver lineage proof missing")
 return driver_lineage

def verify_identity(root,run,report,adapter=None,identity_receipt=None):
 root=Path(root).resolve(strict=True); run=Path(run).resolve(strict=True)
 need(run.name==PIN["run"],"wrong resume run")
 need(sha(run/"report.json")==PIN["report"],"failed report changed")
 need(report.get("passed") is False and report.get("complete_regression_run") is False,"resume requires original failed partial report")
 for key,pin in (("source_sha256","source"),("schema_sha256","schema"),("tool_sha256","producer"),("helper_sha256","capture_helper"),("setups_sha256","old_setup")):
  check_hash("historical "+key,report.get(key),PIN[pin])
 need(report.get("clock_mode")=="controlled-experimental","unexpected clock scope")
 need(tuple(x.get("id") for x in report.get("examples",[]))==tuple(PIN["ids"]),"partial report ID/order mismatch")
 for name,pin in (("source.yaml","source"),("audio.schema.json","schema"),("capture-tool.py","producer"),("capture-helpers.py","capture_helper"),("capture-setups.py","old_setup")):
  need(sha(run/name)==PIN[pin],"frozen run file changed: "+name)
 checks=[
  (root/"manual/audio-scenes.yaml","source"),(root/"manual/audio.schema.json","schema"),
  (root/"tools/manual_audio.py","producer"),(root/"tools/manual_capture.py","capture_helper"),
  (root/"tools/manual_audio_setups.py","new_setup")]
 for p,pin in checks:
  if pin=="producer":check_current_producer(p)
  else:check_hash("current source "+str(p),sha(p),PIN[pin])
 driver_lineage=verify_harness_lineage(root,run,report)
 need(appmap(root)==run_appmap(run),"application source tree changed")
 voices=current_voice_pins(root); need(voices==report.get("voice_pins"),"voice pins changed")
 audio=set(); midi=set()
 for p in run.glob("*/native/identity.json"):
  ident=json.loads(p.read_text()).get("runtime_identity")
  need(isinstance(ident,dict),"missing native runtime identity")
  target=midi if "-midi-" in p.parent.parent.name else audio
  target.add(canon(ident))
 need(audio=={PIN["audio_runtime"]},"native audio runtime identity mismatch")
 need(midi=={PIN["midi_runtime"]},"controlled MIDI runtime identity mismatch")
 need(identity_receipt is not None,"identity parity receipt required")
 native=verify_native_source_identities(run,identity_receipt)
 return {"original_report_sha256":PIN["report"],"historical_producer_sha256":PIN["producer"],
  "resume_adapter_sha256":sha(adapter) if adapter else None,"source_sha256":PIN["source"],
  "schema_sha256":PIN["schema"],"capture_helper_sha256":PIN["capture_helper"],
  "old_setups_sha256":PIN["old_setup"],"current_setups_sha256":PIN["new_setup"],
  "harness_sha256":PIN["harness"],"runtime_identity_sha256":{"audio":PIN["audio_runtime"],"controlled_midi":PIN["midi_runtime"]},
  "application_source_sha256":canon(appmap(root)),"native_source_identity":native,"voice_pins":voices,"clock_mode":report["clock_mode"],
  "driver_lineage":driver_lineage}
def verify_capture(run,record,label,cleanup_receipt_path=None):
 ev=record.get("evidence"); need(isinstance(ev,dict),"missing evidence "+label)
 out=inside(ev.get("path",""),run); job=ev.get("job")
 need(isinstance(job,dict) and job.get("job_id"),"missing job "+label)
 cap=out/"native/audio-captures"/job["job_id"]; result=cap/"result.json"; wav=cap/"output.wav"
 need(result.is_file() and wav.is_file(),"missing raw job/WAV "+label)
 actual=json.loads(result.read_text()); need(actual==job,"job receipt mismatch "+label)
 cleanup_receipt=Path(cleanup_receipt_path or origin_fixture("campaign-cleanup-verification-v2.json"))
 need(sha(cleanup_receipt)==PIN["cleanup_receipt"],"campaign cleanup receipt changed")
 global_receipt=json.loads(cleanup_receipt.read_text())
 need(global_receipt.get("campaign_report_sha256")==PIN["report"] and global_receipt.get("campaign_uuid")==PIN["run"],"cleanup receipt origin mismatch")
 ident=json.loads((out/"native/identity.json").read_text())
 rows=[v for v in global_receipt.get("sessions",[]) if v.get("session_id")==ident.get("session_id")]
 need(len(rows)==1,"capture missing unique cleanup receipt row")
 cleanup_row=rows[0]
 actions_path=out/"native/actions.jsonl";native_cleanup_path=out/"native/cleanup.json"
 need(sha(actions_path)==cleanup_row.get("actions_jsonl_sha256"),"action log differs from pinned cleanup receipt")
 need(sha(native_cleanup_path)==cleanup_row.get("native_cleanup_sha256")==cleanup_row.get("session_cleanup_sha256"),"cleanup log differs from pinned cleanup receipt")
 need(cleanup_row.get("lane") in ("main","solo") and cleanup_row.get("action_acks_all_applied_and_identity_matched") is True
      and cleanup_row.get("action_sequences_from_one_contiguous") is True
      and cleanup_row.get("stop_follows_last_ack") is True and cleanup_row.get("stopped_marker_matches_id") is True
      and not cleanup_row.get("final_grid_keys_down") and not cleanup_row.get("final_norns_keys_down")
      and not cleanup_row.get("active_midi_notes_after_log") and cleanup_row.get("orphan_note_offs")==0
      and cleanup_row.get("session_pid_present_at_check") is False
      and all(not v.get("present_at_check") and v.get("returncode") is not None for v in cleanup_row.get("cleanup_processes",[])),
      "pinned cleanup semantic verdict failed")
 need(actual.get("status")=="complete" and actual.get("input_sha256") is None,"invalid job status/input "+label)
 finished=actual.get("finished",{})
 need(finished.get("frames")==finished.get("expected_frames"),"frame count "+label)
 need(not any(finished.get(k) for k in ("xruns","nonfinite","server_dead")),"capture integrity flags "+label)
 wh=sha(wav); need(wh==ev.get("wav_sha256"),"WAV hash "+label)
 files={}
 for name in ("results.json","recipe.json","observations.json","native/actions.jsonl","native/cleanup.json","native/identity.json"):
  p=out/name; need(p.is_file(),"missing "+name+" "+label); files[name]=sha(p)
 cleanup=json.loads((out/"native/cleanup.json").read_text())
 need(bool(cleanup) and all(row.get("returncode") is not None for row in cleanup),"cleanup incomplete "+label)
 return {"label":label,"path":str(out),"job_id":job["job_id"],"job_result_sha256":sha(result),
  "wav_sha256":wh,"files_sha256":files,"frames":finished["frames"]}
def timeline_check(record,out):
 results=json.loads((out/"results.json").read_text()); obs=json.loads((out/"observations.json").read_text()); frames={}
 for row in obs:
  state=row["state"]; frames[(state["frame"]["sha256"],hashlib.sha256(bytes(state["grid"])).hexdigest())]=state
 for row in record.get("timeline",[]):
  output=row["output"]; binding=output["binding"]
  need(binding in results and binding["passed"],"unbound timeline frame")
  state=frames.get((binding["sha256"],binding["grid_sha256"])); need(state is not None,"missing timeline framebuffer")
  levels=[v for v,n in output["screen_rle"] for _ in range(n)]
  pixels=base64.b64decode(state["frame"]["pixels_base64"],validate=True)
  need(levels==[v//17 for v in pixels[::4]],"timeline pixels changed")
  need(output["grid"]==state["grid"],"timeline grid changed")
 return len(record.get("timeline",[]))
def verify_example(ma,authored,record,run):
 need(record.get("id")==authored["id"],"example identity")
 for k,v in authored.items(): need(record.get(k)==v,"authored field changed "+authored["id"]+"."+k)
 helper=helper_compatibility(authored,PIN["old_setup"],PIN["new_setup"])
 solos=record.get("solo_contributions",[])
 need(len(solos)==len(authored["tracks"]),"solo count "+authored["id"])
 need(sorted((s.get("channel"),s.get("voice")) for s in solos)==sorted((t["channel"],t["voice"]) for t in authored["tracks"]),"solo inventory "+authored["id"])
 captures=[("mix",authored["tracks"],record)]+[("solo-"+str(s["channel"]),[next(t for t in authored["tracks"] if t["channel"]==s["channel"])],s) for s in solos]
 receipts=[];seconds=authored["bars"]*4*60/authored["bpm"];frames=0
 for label,tracks,capture in captures:
  rec=verify_capture(run,capture,authored["id"]+"-"+label); out=Path(rec["path"])
  rec["label"]=label
  metrics=ma.metrics(out/"native/audio-captures"/rec["job_id"]/"output.wav",seconds)
  need(metrics==capture.get("metrics"),"PCM metrics changed "+rec["label"])
  rec["metrics"]=metrics; frames+=rec["frames"];receipts.append(rec)
  if authored.get("purpose")=="lesson-comparison":ma.audit_lesson_capture(authored,tracks,capture)
 pixels=timeline_check(record,Path(receipts[0]["path"]))
 lanes=record.get("musical_evidence",[])
 if authored.get("purpose")=="lesson-comparison": ma.audit_lesson_midi(authored,lanes,controlled_local=True)
 else: need(not lanes,"unexpected MIDI lane")
 return {"id":authored["id"],"helper_compatibility":helper,"captures":receipts,
  "timeline_frames_revalidated":pixels,"midi_lanes_revalidated":len(lanes),"pcm_frames_revalidated":frames}
def qualify(ma,root,run,report,adapter=None,identity_receipt=None):
 identity=verify_identity(root,run,report,adapter,identity_receipt)
 import yaml
 authored=ma.validate(yaml.safe_load((Path(root)/"manual/audio-scenes.yaml").read_text()))
 need(len(authored["examples"])==PIN["examples"],"authored example inventory changed")
 need(sum(len(v["tracks"])+1 for v in authored["examples"])==PIN["wavs"],"authored raw-WAV inventory changed")
 by={v["id"]:v for v in authored["examples"]}; rows={v["id"]:v for v in report["examples"]}
 need(set(rows)==set(PIN["ids"]) and set(PIN["ids"])<=set(by),"partial report ID set")
 examples=[verify_example(ma,by[i],rows[i],Path(run)) for i in PIN["ids"]]
 n=sum(len(v["captures"]) for v in examples);need(n==22,"expected 22 valid WAVs")
 return {"schema_version":1,"qualification":"stored-evidence-only partial reuse candidate",
  "passed":False,"all_pass":False,"complete_regression_run":False,"all_inventory_captured":False,
  "inventory":{"examples_expected":21,"raw_wavs_expected":54,"examples_reused":8,"raw_wavs_reused":n,
   "examples_deferred":13,"raw_wavs_deferred":32},"original_run":str(Path(run).resolve()),
  "original_failed_report_sha256":PIN["report"],"identity":identity,"examples":examples}
def encoder_identity(ffmpeg):
 exe=shutil.which(ffmpeg) if os.path.sep not in ffmpeg else ffmpeg
 need(exe and Path(exe).is_file(),"ffmpeg unavailable: "+ffmpeg)
 version=subprocess.run([exe,"-version"],check=True,capture_output=True,text=True).stdout.splitlines()[0]
 return {"path":str(Path(exe).resolve()),"version":version}
def ffmpeg_convert(ffmpeg,wav,target,seconds,codec):
 exe=shutil.which(ffmpeg) if os.path.sep not in ffmpeg else ffmpeg
 need(exe and Path(exe).is_file(),"ffmpeg unavailable: "+ffmpeg)
 subprocess.run([exe,"-y","-nostdin","-hide_banner","-loglevel","error","-i",str(wav),"-af",
  "afade=t=in:d=0.015,afade=t=out:st="+str(seconds+2.8)+":d=0.2","-c:a",codec,"-b:a","128k",str(target)],check=True)
def stage(manifest,run,report,output,ffmpeg,converter=None):
 output=Path(output); need(not output.exists(),"output path must be new")
 output.mkdir(parents=True); (output/"audio").mkdir()
 rows={v["id"]:v for v in report["examples"]}; assets=[]
 for ex in manifest["examples"]:
  mix=next(c for c in ex["captures"] if c["label"]=="mix")
  wav=Path(mix["path"])/"native/audio-captures"/mix["job_id"]/"output.wav"
  sec=rows[ex["id"]]["bars"]*4*60/rows[ex["id"]]["bpm"]; encoded=[]
  for suffix,codec in (("ogg","libopus"),("mp3","libmp3lame")):
   target=output/"audio"/(ex["id"]+"."+suffix)
   (converter or ffmpeg_convert)(ffmpeg,wav,target,sec,codec)
   need(target.is_file() and target.stat().st_size>0,"encoder omitted "+str(target))
   encoded.append({"path":"audio/"+target.name,"sha256":sha(target),"codec":codec,
    "source_raw_wav_sha256":mix["wav_sha256"],"source_raw_wav_job_id":mix["job_id"]})
  assets.append({"id":ex["id"],"assets":encoded})
 result=dict(manifest);result["staged_encoded_assets"]=assets
 result["ffmpeg"]=encoder_identity(ffmpeg) if converter is None else {"test_converter":True}
 result["staging"]="fresh encoded files derived from revalidated original PCM"
 result["passed"]=False;result["all_pass"]=False;result["complete_regression_run"]=False;result["all_inventory_captured"]=False
 dest=output/"resume-reuse-manifest.json";dest.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 return dest
def _absolute_paths(value):
 out=[]
 if isinstance(value,dict):
  for key,item in value.items():
   if key=="path" and isinstance(item,str) and os.path.isabs(item):out.append(item)
   else:out.extend(_absolute_paths(item))
 elif isinstance(value,list):
  for item in value:out.extend(_absolute_paths(item))
 return out

def verify_resume_aliases(provenance,original_rows,old_run,native_run,ids=None):
 old_run=Path(old_run).resolve(strict=True);native_run=Path(native_run).resolve(strict=True)
 expected={}
 for ident in ids or PIN["ids"]:
  for source_text in _absolute_paths(original_rows[ident]):
   source=Path(source_text).resolve(strict=True)
   try:rel=source.relative_to(old_run)
   except ValueError:raise Rejected("origin evidence path escapes original run")
   alias=native_run/rel; expected[str(alias)]=str(source)
   link=native_run/rel.parts[0];target=old_run/rel.parts[0]
   need(link.is_symlink() and link.resolve(strict=True)==target.resolve(strict=True),"reused evidence alias changed")
 need(provenance.get("evidence_aliases")==expected,"resume alias manifest differs from original evidence paths")
 return expected

def resume_marker_roots(report):
 roots=set()
 for source_text in _absolute_paths(report.get("examples",[])):
  source=Path(source_text)
  for parent in (source,*source.parents):
   marker=parent/"resume-provenance.required.json"
   if marker.is_file():roots.add(marker.resolve(strict=True).parent)
 return roots

def require_resume_provenance(report,native_run):
 native=Path(native_run).resolve(strict=True)
 roots=resume_marker_roots(report)
 provenance=report.get("resume_provenance")
 if roots:
  need(roots=={native},"resumed evidence points to inconsistent run roots")
  need(isinstance(provenance,dict),"resume marker requires report provenance")
 elif provenance:
  raise Rejected("report provenance has no durable run marker")
 return bool(roots)

def verify_current_reused_rows(original_rows,current_rows,provenance,staged_assets,old_run,native_run,ids=None):
 ids=list(ids or PIN["ids"])
 current_list=list(current_rows)
 current={}
 for row in current_list:
  need(isinstance(row,dict) and isinstance(row.get("id"),str),"invalid current report row")
  need(row["id"] not in current,"duplicate current report row")
  current[row["id"]]=row
 expected_ids=set(ids)
 need(expected_ids<=set(current),"missing reused current report row")
 aliases=provenance.get("evidence_aliases",{})
 old_to_alias={source:alias for alias,source in aliases.items()}
 asset_map={entry["id"]:entry["assets"] for entry in staged_assets}
 for ident in ids:
  expected=copy.deepcopy(original_rows[ident])
  def rewrite(value):
   if isinstance(value,dict):
    for key,item in list(value.items()):
     if key=="path" and isinstance(item,str) and os.path.isabs(item):
      source=str(Path(item).resolve(strict=True))
      need(source in old_to_alias,"origin report path is not covered by alias map")
      value[key]=old_to_alias[source]
     else:rewrite(item)
   elif isinstance(value,list):
    for item in value:rewrite(item)
  rewrite(expected)
  assets=asset_map.get(ident)
  need(isinstance(assets,list) and len(assets)==2,"reused asset inventory incomplete")
  expected["files"]=[asset["path"] for asset in assets]
  expected["file_sha256"]={asset["path"]:asset["sha256"] for asset in assets}
  need(canon(current[ident])==canon(expected),"current reused report row differs from exact origin/alias/asset record: "+ident)
 return True

def prepare_continuation(ma,root,old_run,old_report,new_run,ffmpeg,identity_receipt,adapter=None):
 """Build truthful seed rows and symlinked provenance for a future complete capture run."""
 old_run=Path(old_run).resolve(strict=True);new_run=Path(new_run).resolve(strict=True)
 need(not old_report.get("resume_provenance"),"nested resume is not supported")
 manifest=qualify(ma,root,old_run,old_report,adapter,identity_receipt)
 stage_dir=new_run/"resume-reuse"
 staged_path=stage(manifest,old_run,old_report,stage_dir,ffmpeg)
 staged=json.loads(staged_path.read_text())
 old_rows={v["id"]:v for v in old_report["examples"]}
 assets={v["id"]:v["assets"] for v in staged["staged_encoded_assets"]}
 rows=[];aliases={}
 for ident in PIN["ids"]:
  row=copy.deepcopy(old_rows[ident])
  def rewrite(value):
   if isinstance(value,dict):
    for key,item in list(value.items()):
     if key=="path" and isinstance(item,str) and os.path.isabs(item):
      source=Path(item).resolve(strict=True)
      try: rel=source.relative_to(old_run)
      except ValueError: raise Rejected("reused evidence path escapes original run")
      alias=new_run/rel
      top=alias.parts[len(new_run.parts)]
      link=new_run/top;target=old_run/top
      if not link.exists() and not link.is_symlink():link.symlink_to(target,target_is_directory=True)
      need(link.is_symlink() and link.resolve(strict=True)==target.resolve(strict=True),"unexpected evidence alias")
      value[key]=str(alias);aliases[str(alias)]=str(source)
     else: rewrite(item)
   elif isinstance(value,list):
    for item in value:rewrite(item)
  rewrite(row)
  row["files"]=[asset["path"] for asset in assets[ident]]
  row["file_sha256"]={asset["path"]:asset["sha256"] for asset in assets[ident]}
  rows.append(row)
 provenance={"schema_version":1,"kind":"strict-partial-audio-resume",
  "original_run":str(old_run),"original_report":str(old_run/"report.json"),
  "original_report_sha256":PIN["report"],"original_producer_sha256":PIN["producer"],
  "qualification_manifest":str(staged_path),"qualification_manifest_sha256":sha(staged_path),
  "original_record_sha256":{ident:canon(old_rows[ident]) for ident in PIN["ids"]},
  "evidence_aliases":aliases,"driver_lineage":manifest["identity"]["driver_lineage"],
  "reused_ids":PIN["ids"],"reused_raw_wavs":22,
  "deferred_ids":sorted(set(v["id"] for v in ma.validate(__import__("yaml").safe_load((Path(root)/"manual/audio-scenes.yaml").read_text()))["examples"])-set(PIN["ids"])),
  "staged_encoded_assets":staged["staged_encoded_assets"],"passed":False,"complete_regression_run":False}
 marker={"schema":"mosaic-audio-resume-required-v1","required":True,
  "original_report_sha256":PIN["report"],"original_record_sha256":provenance["original_record_sha256"],
  "evidence_aliases":provenance["evidence_aliases"],"qualification_manifest_sha256":provenance["qualification_manifest_sha256"],
  "driver_lineage":provenance["driver_lineage"],
  "reused_ids":PIN["ids"],"staged_encoded_assets":provenance["staged_encoded_assets"]}
 marker_path=new_run/"resume-provenance.required.json"
 marker_path.write_text(json.dumps(marker,indent=2,sort_keys=True)+"\n")
 provenance["marker_path"]=str(marker_path);provenance["marker_sha256"]=sha(marker_path)
 return rows,provenance,stage_dir

def audit_resume_provenance(ma,report,native_run,root,asset_root=None):
 provenance=report.get("resume_provenance")
 if isinstance(provenance,dict) and provenance.get("kind")==SAME:return audit_same_lineage_provenance(ma,report,native_run,root,asset_root)
 need(isinstance(provenance,dict) and provenance.get("kind")=="strict-partial-audio-resume","missing strict resume provenance")
 need(provenance.get("passed") is False and provenance.get("complete_regression_run") is False,"resume provenance falsely claims completion")
 marker_path=Path(native_run).resolve(strict=True)/"resume-provenance.required.json"
 need(provenance.get("marker_path")==str(marker_path) and marker_path.is_file() and sha(marker_path)==provenance.get("marker_sha256"),"durable resume marker missing or changed")
 marker=json.loads(marker_path.read_text())
 need(marker.get("required") is True and marker.get("original_report_sha256")==PIN["report"]
      and marker.get("original_record_sha256")==provenance.get("original_record_sha256")
      and marker.get("evidence_aliases")==provenance.get("evidence_aliases")
      and marker.get("driver_lineage")==provenance.get("driver_lineage")
      and marker.get("qualification_manifest_sha256")==provenance.get("qualification_manifest_sha256")
      and marker.get("reused_ids")==PIN["ids"]
      and marker.get("staged_encoded_assets")==provenance.get("staged_encoded_assets"),"durable resume marker binding mismatch")
 old_run=Path(provenance["original_run"]).resolve(strict=True)
 old_report_path=Path(provenance["original_report"]).resolve(strict=True)
 need(old_report_path==old_run/"report.json" and sha(old_report_path)==PIN["report"]==provenance.get("original_report_sha256"),"original failed report changed")
 original=json.loads(old_report_path.read_text())
 need(original.get("passed") is False and original.get("complete_regression_run") is False,"origin is not the pinned failed partial run")
 rows={v["id"]:v for v in original["examples"]}
 need(provenance.get("original_record_sha256")=={ident:canon(rows[ident]) for ident in PIN["ids"]},"origin record hashes changed")
 verify_resume_aliases(provenance,rows,old_run,native_run)
 manifest=Path(provenance["qualification_manifest"]).resolve(strict=True)
 need(manifest.parent==Path(native_run).resolve(strict=True)/"resume-reuse","qualification manifest escaped current run")
 need(sha(manifest)==provenance.get("qualification_manifest_sha256"),"qualification manifest changed")
 qualified=json.loads(manifest.read_text())
 need(qualified.get("original_failed_report_sha256")==PIN["report"] and qualified.get("passed") is False and qualified.get("complete_regression_run") is False,"invalid partial qualification manifest")
 need(qualified.get("inventory")=={"examples_expected":21,"raw_wavs_expected":54,"examples_reused":8,"raw_wavs_reused":22,"examples_deferred":13,"raw_wavs_deferred":32},"partial inventory was relabelled")
 identity_receipt=origin_fixture("runtime-identity-reuse-check.json")
 fresh=qualify(ma,root,old_run,original,__file__,identity_receipt)
 need(fresh.get("inventory")==qualified.get("inventory"),"revalidated reuse inventory differs")
 from manual_audio_driver_lineage import verify_lineage_binding
 verify_lineage_binding(provenance.get("driver_lineage"),marker.get("driver_lineage"),fresh["identity"].get("driver_lineage"))
 verify_current_reused_rows(rows,report.get("examples",[]),provenance,qualified["staged_encoded_assets"],old_run,native_run)
 current={v["id"]:v for v in report.get("examples",[])}
 for ident in PIN["ids"]:
  expected_assets=next(v["assets"] for v in qualified["staged_encoded_assets"] if v["id"]==ident)
  for asset in expected_assets:
   p=Path(asset_root or root)/"manual"/asset["path"]
   need(p.is_file() and sha(p)==asset["sha256"],"reused encoded asset hash changed: "+asset["path"])
 return {"reused_examples":8,"reused_raw_wavs":22,"deferred_examples":13,"deferred_raw_wavs":32,"passed":True}

# --- Same-lineage continuation: any failed run whose recording identity is identical to the current one. ---
SAME="strict-same-lineage-audio-resume"
LINEAGE_KEYS=("schema_version","source_sha256","tool_sha256","helper_sha256","setups_sha256","schema_sha256","harness_sha256","voice_pins",
 "clock_mode","validation_scope","realtime_qualification","audio_capture_clock_mode","controlled_lane")
FROZEN_FILES={"source.yaml":"source_sha256","capture-tool.py":"tool_sha256","capture-helpers.py":"helper_sha256","capture-setups.py":"setups_sha256","audio.schema.json":"schema_sha256"}
def _default_session_check(path,clock_mode,voices):
 from manual_publication_verify import check_audio_native_session
 return check_audio_native_session(path,clock_mode,voices)
def _sessions(rows):
 audio=[];midi=[]
 for row in rows:
  for rec in [row]+list(row.get("solo_contributions",[])):audio.append(Path(rec["evidence"]["path"]))
  for lane in row.get("musical_evidence",[]):midi.append(Path(lane["path"]))
 return audio,midi
def native_identity_classes(rows):
 """{audio|midi:{runtime|application|emulator:digest or None}}; every session of a class must carry the same identity."""
 out={}
 for kind,paths in zip(("audio","midi"),_sessions(rows)):
  seen={"runtime":set(),"application":set(),"emulator":set()}
  for p in paths:
   ident=json.loads((p/"native/identity.json").read_text()); runtime=ident.get("runtime_identity")
   need(isinstance(runtime,dict),"missing native runtime identity")
   seen["runtime"].add(canon(runtime));seen["application"].add(_identity_file_manifest(ident.get("application_identity",{})));seen["emulator"].add(_identity_file_manifest(ident.get("emulator_identity",{})))
  for what,values in seen.items():need(len(values)<=1,"native "+kind+" "+what+" identity is not uniform")
  out[kind]={what:next(iter(values)) if values else None for what,values in seen.items()}
 return out
def _verify_current_runtime(rows,installs,emulators):
 """The recorded runtime/emulator identity of the old sessions must equal the installations this invocation will record with."""
 for kind,paths in zip(("audio","midi"),_sessions(rows)):
  if not paths:continue
  need(installs.get(kind) and emulators.get(kind),kind+" installation and emulator root are required for same-lineage resume")
  ident=json.loads((paths[0]/"native/identity.json").read_text())
  need(canon(ident["runtime_identity"])==canon(json.loads(Path(installs[kind]).read_text())),kind+" runtime identity differs from the current installation")
  root=Path(emulators[kind]).resolve(strict=True)
  for item in ident["emulator_identity"]["files"]:
   f=root/item["path"];need(f.is_file() and sha(f)==item["sha256"],kind+" emulator source changed: "+item["path"])
def verify_same_lineage(root,old_run,old_report,current,new_run,installs,emulators):
 """Fail closed unless the failed run and this invocation share one recording identity; returns the identity record."""
 root=Path(root).resolve(strict=True);old_run=Path(old_run).resolve(strict=True)
 need(not old_report.get("resume_provenance") and not (old_run/"resume-provenance.required.json").exists(),"nested resume is not supported")
 need(old_report.get("passed") is False and old_report.get("complete_regression_run") is False,"same-lineage resume requires a failed partial report")
 need(old_report.get("examples"),"no completed example to reuse")
 bad=[k for k in LINEAGE_KEYS if old_report.get(k)!=current.get(k)]
 need(not bad,"identity mismatch between the failed run and this invocation: "+", ".join(bad))
 for run in [old_run]+([Path(new_run).resolve(strict=True)] if new_run else []):
  for name,key in FROZEN_FILES.items():need((run/name).is_file() and sha(run/name)==old_report[key],"frozen run file changed: "+name)
  for name,value in old_report["harness_sha256"].items():need((run/name).is_file() and sha(run/name)==value,"frozen run file changed: "+name)
 for name,value in old_report["harness_sha256"].items():need((root/"tests/behaviour"/name).is_file() and sha(root/"tests/behaviour"/name)==value,"harness identity mismatch: "+name)
 old_app=run_appmap(old_run)
 need(appmap(root)==old_app and (not new_run or run_appmap(Path(new_run))==old_app),"application source tree changed")
 _verify_current_runtime(old_report["examples"],installs,emulators)
 return {"fields":{k:old_report.get(k) for k in LINEAGE_KEYS},"application_source_sha256":canon(old_app),"native_identity":native_identity_classes(old_report["examples"])}
def _alias_rows(rows,old_run,new_run):
 aliases={};out=[]
 for row in rows:
  row=copy.deepcopy(row)
  def rewrite(value):
   if isinstance(value,dict):
    for key,item in list(value.items()):
     if key=="path" and isinstance(item,str) and os.path.isabs(item):
      source=Path(item).resolve(strict=True)
      try:rel=source.relative_to(old_run)
      except ValueError:raise Rejected("reused evidence path escapes original run")
      alias=new_run/rel;link=new_run/rel.parts[0];target=old_run/rel.parts[0]
      if not link.exists() and not link.is_symlink():link.symlink_to(target,target_is_directory=True)
      need(link.is_symlink() and link.resolve(strict=True)==target.resolve(strict=True),"unexpected evidence alias")
      value[key]=str(alias);aliases[str(alias)]=str(source)
     else:rewrite(item)
   elif isinstance(value,list):
    for item in value:rewrite(item)
  rewrite(row);out.append(row)
 return out,aliases
def prepare_same_lineage(ma,root,old_run,old_report,new_run,current,authored,ffmpeg,audio_install=None,midi_install=None,audio_emulator=None,midi_emulator=None,converter=None,session_check=None):
 """Reuse every completed example of a failed run with an identical recording identity; returns rows, provenance and the staged-asset directory."""
 old_run=Path(old_run).resolve(strict=True);new_run=Path(new_run).resolve(strict=True);session_check=session_check or _default_session_check
 lineage=verify_same_lineage(root,old_run,old_report,current,new_run,{"audio":audio_install,"midi":midi_install},{"audio":audio_emulator,"midi":midi_emulator})
 by={v["id"]:v for v in authored["examples"]};old_rows=list(old_report["examples"]);ids=[v.get("id") for v in old_rows]
 need(len(set(ids))==len(ids),"duplicate example in the failed report")
 captures=[]
 for row in old_rows:
  ident=row["id"];need(ident in by,"example outside the authored inventory: "+ident)
  for k,v in by[ident].items():need(row.get(k)==v,"authored field changed "+ident+"."+k)
  for path in _absolute_paths(row):inside(path,old_run)
  try:
   ma.audit_example_native(row,by[ident],True)
   for lane in row.get("musical_evidence",[]):session_check(Path(lane["path"]),lane["clock_mode"],False)
   for rec in [row]+list(row.get("solo_contributions",[])):session_check(Path(rec["evidence"]["path"]),"real-time",True)
  except Exception as error:raise Rejected("reused example failed its audit: "+ident+": "+str(error)) from error
  ev=row["evidence"];wav=Path(ev["path"])/"native/audio-captures"/ev["job"]["job_id"]/"output.wav"
  need(wav.is_file() and sha(wav)==ev["wav_sha256"],"raw WAV changed: "+ident)
  captures.append({"id":ident,"captures":[{"label":"mix","path":ev["path"],"job_id":ev["job"]["job_id"],"wav_sha256":ev["wav_sha256"]}]})
 report_hash=sha(old_run/"report.json")
 stage_dir=new_run/"resume-reuse"
 staged_path=stage({"kind":SAME,"original_report_sha256":report_hash,"examples":captures,"lineage":lineage,
  "inventory":{"examples_reused":len(ids),"examples_deferred":len(by)-len(ids)}},old_run,old_report,stage_dir,ffmpeg,converter)
 staged=json.loads(staged_path.read_text());assets={v["id"]:v["assets"] for v in staged["staged_encoded_assets"]}
 rows,aliases=_alias_rows(old_rows,old_run,new_run)
 for row in rows:
  row["files"]=[a["path"] for a in assets[row["id"]]];row["file_sha256"]={a["path"]:a["sha256"] for a in assets[row["id"]]}
 provenance={"schema_version":1,"kind":SAME,"original_run":str(old_run),"original_report":str(old_run/"report.json"),"original_report_sha256":report_hash,
  "qualification_manifest":str(staged_path),"qualification_manifest_sha256":sha(staged_path),
  "original_record_sha256":{v["id"]:canon(v) for v in old_rows},"evidence_aliases":aliases,"lineage":lineage,
  "reused_ids":ids,"deferred_ids":sorted(set(by)-set(ids)),"staged_encoded_assets":staged["staged_encoded_assets"],"passed":False,"complete_regression_run":False}
 marker={"schema":"mosaic-audio-resume-required-v1","kind":SAME,"required":True,"original_report_sha256":report_hash,
  "original_record_sha256":provenance["original_record_sha256"],"evidence_aliases":aliases,"qualification_manifest_sha256":provenance["qualification_manifest_sha256"],
  "lineage":lineage,"reused_ids":ids,"staged_encoded_assets":provenance["staged_encoded_assets"]}
 marker_path=new_run/"resume-provenance.required.json";marker_path.write_text(json.dumps(marker,indent=2,sort_keys=True)+"\n")
 provenance["marker_path"]=str(marker_path);provenance["marker_sha256"]=sha(marker_path)
 return rows,provenance,stage_dir
def audit_same_lineage_provenance(ma,report,native_run,root,asset_root=None):
 """Strict publication-time verification of a same-lineage continuation; every reused byte is re-hashed."""
 native_run=Path(native_run).resolve(strict=True);prov=report.get("resume_provenance")
 need(isinstance(prov,dict) and prov.get("kind")==SAME,"missing same-lineage resume provenance")
 need(prov.get("passed") is False and prov.get("complete_regression_run") is False,"resume provenance falsely claims completion")
 marker_path=native_run/"resume-provenance.required.json"
 need(prov.get("marker_path")==str(marker_path) and marker_path.is_file() and sha(marker_path)==prov.get("marker_sha256"),"durable resume marker missing or changed")
 marker=json.loads(marker_path.read_text())
 need(marker.get("required") is True and marker.get("kind")==SAME and all(marker.get(k)==prov.get(k) for k in
  ("original_report_sha256","original_record_sha256","evidence_aliases","qualification_manifest_sha256","lineage","reused_ids","staged_encoded_assets")),"durable resume marker binding mismatch")
 old_run=Path(prov["original_run"]).resolve(strict=True);old_path=Path(prov["original_report"]).resolve(strict=True)
 need(old_run!=native_run and old_path==old_run/"report.json" and sha(old_path)==prov.get("original_report_sha256"),"original report changed")
 original=json.loads(old_path.read_text())
 need(original.get("passed") is False and original.get("complete_regression_run") is False and not original.get("resume_provenance"),"origin is not a failed non-resumed partial run")
 rows={v["id"]:v for v in original["examples"]};ids=[v["id"] for v in original["examples"]]
 need(prov.get("reused_ids")==ids and marker.get("reused_ids")==ids and ids,"reused ids are not every completed original example")
 need(prov.get("original_record_sha256")=={i:canon(rows[i]) for i in ids},"origin record hashes changed")
 bad=[k for k in LINEAGE_KEYS if original.get(k)!=report.get(k)]
 need(not bad,"identity mismatch between the failed run and the resumed report: "+", ".join(bad))
 for run in (old_run,native_run):
  for name,key in FROZEN_FILES.items():need((run/name).is_file() and sha(run/name)==original[key],"frozen run file changed: "+name)
  for name,value in original["harness_sha256"].items():need((run/name).is_file() and sha(run/name)==value,"frozen run file changed: "+name)
 verify_resume_aliases(prov,rows,old_run,native_run,ids)
 old_app=run_appmap(old_run);need(run_appmap(native_run)==old_app,"application source tree changed")
 lineage=prov.get("lineage")
 need(lineage=={"fields":{k:original.get(k) for k in LINEAGE_KEYS},"application_source_sha256":canon(old_app),"native_identity":native_identity_classes(original["examples"])},"recorded lineage identity changed")
 need(native_identity_classes(report.get("examples",[]))==lineage["native_identity"],"native session identity differs between reused and fresh sessions")
 manifest=Path(prov["qualification_manifest"]).resolve(strict=True)
 need(manifest.parent==native_run/"resume-reuse","qualification manifest escaped current run")
 need(sha(manifest)==prov.get("qualification_manifest_sha256"),"qualification manifest changed")
 qualified=json.loads(manifest.read_text())
 need(qualified.get("kind")==SAME and qualified.get("original_report_sha256")==prov["original_report_sha256"] and qualified.get("lineage")==lineage
      and qualified.get("passed") is False and qualified.get("complete_regression_run") is False and qualified.get("staged_encoded_assets")==prov.get("staged_encoded_assets"),"invalid same-lineage qualification manifest")
 verify_current_reused_rows(rows,report.get("examples",[]),prov,qualified["staged_encoded_assets"],old_run,native_run,ids)
 for entry in qualified["staged_encoded_assets"]:
  ev=rows[entry["id"]]["evidence"];wav=Path(ev["path"])/"native/audio-captures"/ev["job"]["job_id"]/"output.wav"
  need(wav.is_file() and sha(wav)==ev["wav_sha256"],"raw WAV changed: "+entry["id"])
  for asset in entry["assets"]:
   p=Path(asset_root or root)/"manual"/asset["path"]
   need(asset["source_raw_wav_sha256"]==ev["wav_sha256"],"staged asset names another source WAV: "+asset["path"])
   need(p.is_file() and sha(p)==asset["sha256"],"reused encoded asset hash changed: "+asset["path"])
 deferred=prov.get("deferred_ids")
 need(isinstance(deferred,list) and not set(deferred)&set(ids) and {v.get("id") for v in report.get("examples",[])}==set(ids)|set(deferred),"deferred ids do not complete the reported inventory")
 return {"reused_examples":len(ids),"deferred_examples":len(deferred),"reused_raw_wavs":sum(len(v.get("solo_contributions",[]))+1 for v in original["examples"]),"passed":True}

def load_audio(candidate):
 sys.path.insert(0,str(candidate/"tools"));sys.path.insert(0,str(candidate/"tests/behaviour"))
 import manual_audio
 return manual_audio
def main(argv=None):
 p=argparse.ArgumentParser(description="Qualify/stage the exact preserved partial capture set.")
 p.add_argument("--resume-from",type=Path,required=True);p.add_argument("--root",type=Path,required=True)
 p.add_argument("--output",type=Path,required=True);p.add_argument("--ffmpeg",default="ffmpeg")
 p.add_argument("--candidate-root",type=Path,default=Path(__file__).resolve().parents[1])
 a=p.parse_args(argv)
 try:
  ma=load_audio(a.candidate_root);run=a.resume_from.resolve(strict=True);report=json.loads((run/"report.json").read_text())
  receipt=origin_fixture("runtime-identity-reuse-check.json")
  result=qualify(ma,a.root,run,report,Path(__file__),receipt); dest=stage(result,run,report,a.output,a.ffmpeg)
  print(json.dumps({"manifest":str(dest),"passed":False,"complete_regression_run":False,"examples_reused":8,"raw_wavs_reused":22,"examples_deferred":13,"raw_wavs_deferred":32},indent=2));return 0
 except (Rejected,OSError,ValueError,KeyError,TypeError,AssertionError,subprocess.CalledProcessError) as e:
  traceback.print_exc();print("resume rejected: "+str(e),file=sys.stderr);return 2
if __name__=="__main__": raise SystemExit(main())
