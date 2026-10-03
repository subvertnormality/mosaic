"""Replay YAML scenes through Mosaic's public behaviour driver; publish atomically."""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from pathlib import Path

from manual_model import ROOT, MANUAL, load, validate, validate_capture, source_hash
sys.path.insert(0, str(ROOT / "tests/behaviour"))
from driver import Driver, digest, write

def tracked_driver(*args, **kwargs):
    c=Driver(*args, **kwargs)
    c.manual_transport_on=False
    action=c.action
    def tracked(**value):
        result=action(**value)
        if value.get("type")=="grid" and (value.get("x"),value.get("y"),value.get("state"))==(1,8,1):
            c.manual_transport_on=not c.manual_transport_on
        return result
    c.action=tracked
    return c

def rle(values):
    result = []
    for value in values:
        if result and result[-1][0] == value:
            result[-1][1] += 1
        else: result.append([value, 1])
    return result

def frame(c, case, step):
    state = c.snapshot()
    rgba = base64.b64decode(state["frame"]["pixels_base64"])
    if len(rgba) != 32768 or any(v % 17 for v in rgba[::4]):
        raise ValueError("Framebuffer is not exact 16-level greyscale")
    levels = [v // 17 for v in rgba[::4]]
    grid = state["grid"]
    validate_capture(dict(levels=levels, grid=grid))
    stable = hashlib.sha256(rgba[:128*55*4]).hexdigest()
    record = dict(kind="documentation-frame", name="manual/"+case+"/"+step,
                  sha256=state["frame"]["sha256"], stable_rows=55,
                  stable_sha256=stable, grid_sha256=hashlib.sha256(bytes(grid)).hexdigest(),
                  semantic_assertions=len(c.results), passed=True)
    c.results.append(record)
    return dict(screen_rle=rle(levels), grid=grid, binding=record)

def inputs(c, actions, held):
    for action in actions:
        kind = action["type"]
        if kind == "enc": c.enc(action["n"], action["delta"])
        elif kind == "wait": c.elapse(action["seconds"])
        elif kind in ("play","stop"): c.tap(1,8)
        elif kind == "key" and "state" not in action: c.key(action["n"])
        else:
            c.action(**action)
            identity = (kind, action.get("n"), action.get("x"), action.get("y"))
            if action.get("state"): held[identity] = action
            else: held.pop(identity, None)
            c.elapse(.35 if kind=="key" and action.get("n")==1 and action.get("state")==1 else .08)

def verify(c, step, held):
    from cases import assert_durations
    c.ui.expect_header("masks", channel=1, held=sorted((a["y"]-4)*16+a["x"] for a in held.values() if a["type"]=="grid" and 4<=a["y"]<=7))
    for field, value in step["expect"].get("screen", []):
        c.ui.expect_field_value(field, str(value))
    expected = step["expect"].get("midi_phrase")
    if expected:
        notes = c.playback([(v["port"], v["bytes"]) for v in expected], cycles=2, timeout=8)
        if "durations" in step["expect"]:
            assert_durations(c, notes, step["expect"]["durations"]*2)
        # README channel clock: default90 BPM, /4 = six steps per second.
        positions = step["expect"].get("positions", list(range(len(expected))))
        period = step["expect"].get("cycle_steps", 4)
        field = "logical_ns" if c.clock_mode != "real-time" else "monotonic_ns"
        tolerance = 2e-9 if c.clock_mode != "real-time" else .01
        # Chord voices share an onset; ordinary phrases have one note per position.
        if len(positions) == len(expected) and not step["id"] in ("thirds","release","clear"):
            for i, note in enumerate(notes):
                target = ((i//len(expected))*period+positions[i%len(expected)]-positions[0])/6
                assert abs((note[field]-notes[0][field])/1e9-target) <= tolerance, (target,note)
    c.results.append(dict(kind="manual-semantic", citation=step["citation"],
                          step=step["id"], expected=step["expect"], passed=True))

def close(c, held):
    # Release every explicitly held input even on assertion failure.
    for value in list(held.values()):
        c.action(**dict(value, state=0))
    if c.manual_transport_on: c.tap(1,8)
    c.tap(15,8)  # public panic: bounded outstanding MIDI/audio release
    c.elapse(.2)
    state = c.snapshot()
    if state["midi_capture"]["outstanding"]:
        raise AssertionError("Outstanding MIDI notes after panic")
    c.finish()

def capture_scene(scene, out, options):
    c = tracked_driver(out, clock_mode=options.clock_mode, experimental_install=options.experimental_install, app_root=options.app_root)
    held = {}
    frames = []
    try:
        c.configure()
        if scene["setup"]["fixture"] == "four-note-eight-step": c.ui.set_range(1,8)
        for step in scene["steps"]:
            inputs(c, step["inputs"], held)
            verify(c, step, held)
            frames.append(dict(step, output=frame(c,scene["behaviour_case"],step["id"])))
    finally:
        try: close(c,held)
        finally:
            if not (c.out/"native").exists(): c.finish()
    return dict(scene, steps=frames, evidence=dict(path=str(out),
                results_sha256=digest(out/"results.json"), identity_sha256=digest(out/"native/identity.json")))

def check_cases(data, evidence, options):
    from cases import CASES
    records = []
    for name in dict.fromkeys(s["behaviour_case"] for s in data["scenes"]):
        out = evidence / name;out.mkdir()
        c = tracked_driver(out, clock_mode=options.clock_mode, experimental_install=options.experimental_install, app_root=options.app_root)
        try: CASES[name]["run"](c)
        finally: c.finish()
        records.append(dict(case=name,passed=True,path=str(out),
                            results_sha256=digest(out/"results.json")))
        print("Verified",name,flush=True)
    return records

def set_mask_field(c, index, detents):
    c.enc(2,-12)
    if index: c.enc(2,index)
    if detents: c.enc(3,detents)

def audio_capture(data, out, destination, options):
    from pcm_oracle import read_wav
    c = tracked_driver(out, profile=data["profile"], mod_code_root=options.mod_code_root, app_root=options.app_root, experimental_install=getattr(options,"audio_install",None))
    frames=[]
    job=None
    try:
        c.ui.tap_control("channel_editor")
        for track in data["tracks"]:
            ch=track["channel"]
            c.ui.select_channel(ch);c.ui.channel_page("midi_config",channel=ch)
            c.enc(3,-64)  # Picker clamps; start at its first item on every channel.
            c.ui.pick_device(track["voice"])
            c.ui.set_range(1,64)
            c.ui.channel_page("masks",channel=ch)
            set_mask_field(c,0,1)  # default Trig N
            set_mask_field(c,1,track["note"]+1)
            set_mask_field(c,2,track["velocity"]+1)
            set_mask_field(c,3,track["length_detents"])
            for slot,offset in enumerate(track.get("chords",[])):
                set_mask_field(c,4+slot,offset)
            for step,note in track["notes"]:
                set_mask_field(c,0,0)
                with c.ui.hold_step(step): c.enc(3,1)  # N → Y
                set_mask_field(c,1,0)
                if note != track["note"]:
                    with c.ui.hold_step(step): c.enc(3,note-track["note"])
            c.ui.expect_field_value("note", ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"][track["note"]%12]+str(track["note"]//12-2))
            c.ui.expect_field_value("velocity",str(track["velocity"]))
            c.results.append(dict(kind="manual-audio-track",citation="README.md#masks",
                                  channel=ch,voice=track["voice"],authored=track,passed=True))
        c.ui.select_channel(data["tracks"][-1]["channel"])
        c.elapse(13)  # Upstream Doubledecker startup tone lies outside capture.
        seconds = data["bars"]*4*60/data["bpm"]
        job = c.runtime.capture_start(seconds+2)
        started=time.monotonic()
        c.ui.play()
        while time.monotonic()-started < seconds:
            frames.append(dict(time=time.monotonic()-started,output=frame(c,"manual-audio","playhead")))
            c.elapse(.1)
        c.ui.stop();c.tap(15,8);c.elapse(2)
        status=c.runtime.capture_status(job["job_id"])
        deadline=time.monotonic()+10
        while status["status"]=="capturing":
            if time.monotonic()>deadline:raise TimeoutError("WAV capture")
            c.elapse(.1);status=c.runtime.capture_status(job["job_id"])
        if status["status"]!="complete":raise ValueError(status)
        wav=Path(status["output"])
        if digest(wav)!=status["sha256"]:raise ValueError("WAV hash mismatch")
        rate,channels=read_wav(wav)
        samples=[v for channel in channels for v in channel]
        peak=max(abs(v) for v in samples)
        rms=(sum(v*v for v in samples)/len(samples))**.5
        if not (.0001 < rms and peak < .98):raise ValueError(("silence or clipping",rms,peak))
        # Characterisation: lossless signal sanity; not a physical-norns equivalence claim.
        c.results.append(dict(kind="manual-audio-PCM",citation="characterisation: digital audio integrity",
                              peak=peak,rms=rms,sample_rate=rate,passed=True))
        for suffix,codec in (("ogg","libopus"),("mp3","libmp3lame")):
            target=destination/("masks-small-hours."+suffix)
            subprocess.run([options.ffmpeg,"-y","-loglevel","error","-i",str(wav),
                            "-af","afade=t=in:d=0.015,afade=t=out:st="+str(seconds+1.8)+":d=0.2",
                            "-c:a",codec,"-b:a","128k",str(target)],check=True)
        return dict(data,timeline=frames,metrics=dict(peak=peak,rms=rms),
                    evidence=dict(path=str(out),wav_sha256=digest(wav),job=status))
    finally:
        if job:
            try:
                status=c.runtime.capture_status(job["job_id"])
                if status["status"]=="capturing":c.runtime.capture_cancel(job["job_id"])
            except Exception:pass
        try:close(c,{})
        finally:
            if not getattr(c,"finished",False):c.finish()

def reuse_visuals(data, directory):
    old=json.loads((directory/"report.json").read_text())
    old_source=subprocess.check_output(["git","show",old["revision"]+":manual/features/masks.yaml"],cwd=ROOT,text=True)
    import yaml
    old_data=yaml.safe_load(old_source)
    if source_hash(old_data)!=old["source_sha256"] or old_data["scenes"]!=data["scenes"]:
        raise ValueError("Cannot reuse changed or unidentifiable scene authoring data")
    for case in old["behaviour_cases"]:
        if not case["passed"] or digest(Path(case["path"])/"results.json") != case["results_sha256"]:
            raise ValueError("Changed prerequisite evidence")
    scenes=[]
    for scene in data["scenes"]:
        out=directory/scene["id"]
        results=json.loads((out/"results.json").read_text())
        observations=json.loads((out/"observations.json").read_text())
        steps=[]
        for step in scene["steps"]:
            assertions=[v for v in results if v.get("kind")=="manual-semantic" and v.get("step")==step["id"] and v.get("passed")]
            if len(assertions)!=1 or assertions[0]["expected"]!=step["expect"]:
                raise ValueError("Missing exact scene semantics")
            name="manual/"+scene["behaviour_case"]+"/"+step["id"]
            records=[v for v in results if v.get("kind")=="documentation-frame" and v["name"]==name]
            if len(records)!=1:raise ValueError("Missing frame binding")
            record=records[0]
            states=[v["state"] for v in observations if v["state"]["frame"]["sha256"]==record["sha256"]
                    and hashlib.sha256(bytes(v["state"]["grid"])).hexdigest()==record["grid_sha256"]]
            if not states:raise ValueError("Missing exact captured frame and grid")
            state=states[-1]
            rgba=base64.b64decode(state["frame"]["pixels_base64"])
            levels=[v//17 for v in rgba[::4]]
            validate_capture(dict(levels=levels,grid=state["grid"]))
            steps.append(dict(step,output=dict(screen_rle=rle(levels),grid=state["grid"],binding=record)))
        scenes.append(dict(scene,steps=steps,evidence=dict(path=str(out),results_sha256=digest(out/"results.json"),
                           identity_sha256=digest(out/"native/identity.json"))))
    return scenes,old["behaviour_cases"]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,help="Alternate YAML for authoring regression checks")
    parser.add_argument("--mod-code-root")
    parser.add_argument("--audio-emulator",help="Optional independent emulator checkout for audio")
    parser.add_argument("--audio-worker",help=argparse.SUPPRESS)
    parser.add_argument("--application",help=argparse.SUPPRESS)
    parser.add_argument("--audio-output-dir",help=argparse.SUPPRESS)
    parser.add_argument("--reuse-visuals",type=Path,help="Reuse unchanged verified scenes; preserve the original report")
    parser.add_argument("--audio-install",help="Independent WAV-capable native installation")
    parser.add_argument("--verify-only",action="store_true",help="Preserve evidence without replacing published JSON")
    parser.add_argument("--scene",action="append",help="Development: capture only named scenes")
    parser.add_argument("--visuals-only",action="store_true")
    parser.add_argument("--skip-existing-cases",action="store_true",help="Development only; never complete acceptance")
    parser.add_argument("--clock-mode",choices=["real-time","controlled-experimental"],default="real-time")
    parser.add_argument("--experimental-install")
    parser.add_argument("--ffmpeg",default="ffmpeg")
    options=parser.parse_args()
    data=validate(load(options.source))
    if options.audio_worker:
        options.app_root=Path(options.application)
        result=audio_capture(data["audio"],Path(options.audio_worker),Path(options.audio_output_dir),options)
        write(Path(options.audio_worker)/"audio-output.json",result)
        return 0
    if options.clock_mode!="real-time" and not options.experimental_install:parser.error("Controlled lane requires explicit runtime")
    if not options.visuals_only and not options.mod_code_root:parser.error("Audio requires --mod-code-root")
    run_id=uuid.uuid4().hex
    evidence=ROOT.parent/"mosaic-manual-runs"/run_id;evidence.mkdir(parents=True)
    app=evidence/"application";app.mkdir()
    shutil.copyfile(ROOT/"mosaic.lua",app/"mosaic.lua")
    shutil.copytree(ROOT/"lib",app/"lib",ignore=shutil.ignore_patterns("tests",".git","__pycache__"))
    shutil.copytree(ROOT/"docs/ui-reimplementation/code",app/"docs/ui-reimplementation/code")
    options.app_root=app
    report=dict(run_id=run_id,source_sha256=source_hash(data),
                base_revision="54d7b871358fcc68b7166847603cc9fb1461d0b6",
                revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                clock_mode=options.clock_mode,complete_regression_run=False,passed=False,
                capture_tool_sha256=digest(Path(__file__)),
                driver_sha256=digest(ROOT/"tests/behaviour/driver.py"),
                voice_lock_sha256=digest(MANUAL/"voices.lock.json"))
    try:
        report["behaviour_cases"]=[] if options.skip_existing_cases or options.reuse_visuals else check_cases(data,evidence,options)
        result=dict(schema_version=1,feature=data["feature"],source_sha256=source_hash(data),scenes=[])
        if options.reuse_visuals:
            result["scenes"],report["behaviour_cases"]=reuse_visuals(data,options.reuse_visuals.resolve())
            report["reused_visual_evidence"]=str(options.reuse_visuals.resolve())
        for scene in ([] if options.reuse_visuals else data["scenes"]):
            if options.scene and scene["id"] not in options.scene:continue
            out=evidence/scene["id"];out.mkdir()
            result["scenes"].append(capture_scene(scene,out,options))
            print("Captured",scene["id"],flush=True)
        with tempfile.TemporaryDirectory(prefix="mosaic-manual-publish-") as scratch:
            staged=Path(scratch);(staged/"audio").mkdir()
            if not options.visuals_only:
                out=evidence/"audio";out.mkdir()
                if options.audio_emulator:
                    command=[sys.executable,str(Path(__file__).resolve()),"--audio-worker",str(out),
                             "--application",str(options.app_root),"--audio-output-dir",str(staged/"audio"),
                             "--mod-code-root",options.mod_code_root,"--ffmpeg",options.ffmpeg]
                    if options.audio_install:command+=["--audio-install",options.audio_install]
                    subprocess.run(command,env=dict(os.environ,MONOME_EMULATOR=options.audio_emulator),check=True)
                    result["audio"]=json.loads((out/"audio-output.json").read_text())
                else:result["audio"]=audio_capture(data["audio"],out,staged/"audio",options)
            report["passed"]=True
            report["pilot_complete"]=not options.visuals_only and not options.skip_existing_cases and not options.scene and options.clock_mode=="real-time"
            result["validation"]=report
            (staged/"pilot.json").write_text(json.dumps(result,separators=(",",":"))+"\n")
            # No source writes while an emulator session is live.
            (MANUAL/"generated").mkdir(exist_ok=True)
            write(evidence/"pilot.json",result)
            if options.verify_only:return 0
            shutil.copyfile(staged/"pilot.json",MANUAL/"generated/pilot.json")
            if not options.visuals_only:
                (MANUAL/"audio").mkdir(exist_ok=True)
                for audio in (staged/"audio").iterdir():shutil.copyfile(audio,MANUAL/"audio"/audio.name)
    except Exception:
        report["failure"]=traceback.format_exc()
        raise
    finally:
        write(evidence/"report.json",report)
        print("Evidence",evidence,flush=True)
    return 0

if __name__=="__main__":sys.exit(main())
