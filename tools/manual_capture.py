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
            c.elapse(.08)

def verify(c, step):
    from cases import assert_durations
    c.ui.expect_header("masks", channel=1)
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
    c.tap(15,8)  # public panic: bounded outstanding MIDI/audio release
    c.elapse(.2)
    state = c.snapshot()
    if state["midi_capture"]["outstanding"]:
        raise AssertionError("Outstanding MIDI notes after panic")
    c.finish()

def capture_scene(scene, out, options):
    c = Driver(out, clock_mode=options.clock_mode, experimental_install=options.experimental_install)
    held = {}
    frames = []
    try:
        c.configure()
        if scene["setup"]["fixture"] == "four-note-eight-step": c.ui.set_range(1,8)
        for step in scene["steps"]:
            inputs(c, step["inputs"], held)
            verify(c, step)
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
        c = Driver(out, clock_mode=options.clock_mode, experimental_install=options.experimental_install)
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
    c = Driver(out, profile=data["profile"], mod_code_root=options.mod_code_root)
    frames=[]
    job=None
    try:
        c.ui.tap_control("channel_editor")
        for track in data["tracks"]:
            ch=track["channel"]
            c.ui.select_channel(ch);c.ui.channel_page("midi_config",channel=ch)
            c.ui.pick_device(track["voice"])
            c.ui.set_range(1,16)
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
            c.results.append(dict(kind="manual-audio-track",citation="README.md#masks",
                                  channel=ch,voice=track["voice"],authored=track,passed=True))
        c.ui.select_channel(3)
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

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mod-code-root")
    parser.add_argument("--visuals-only",action="store_true")
    parser.add_argument("--skip-existing-cases",action="store_true",help="Development only; never complete acceptance")
    parser.add_argument("--clock-mode",choices=["real-time","controlled-experimental"],default="real-time")
    parser.add_argument("--experimental-install")
    parser.add_argument("--ffmpeg",default="ffmpeg")
    options=parser.parse_args()
    data=validate(load())
    if options.clock_mode!="real-time" and not options.experimental_install:parser.error("Controlled lane requires explicit runtime")
    if not options.visuals_only and not options.mod_code_root:parser.error("Audio requires --mod-code-root")
    run_id=uuid.uuid4().hex
    evidence=ROOT.parent/"mosaic-manual-runs"/run_id;evidence.mkdir(parents=True)
    report=dict(run_id=run_id,source_sha256=source_hash(data),
                base_revision="54d7b871358fcc68b7166847603cc9fb1461d0b6",
                revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                clock_mode=options.clock_mode,complete_regression_run=False,passed=False)
    try:
        report["behaviour_cases"]=[] if options.skip_existing_cases else check_cases(data,evidence,options)
        result=dict(schema_version=1,feature=data["feature"],source_sha256=source_hash(data),scenes=[])
        for scene in data["scenes"]:
            out=evidence/scene["id"];out.mkdir()
            result["scenes"].append(capture_scene(scene,out,options))
            print("Captured",scene["id"],flush=True)
        with tempfile.TemporaryDirectory(prefix="mosaic-manual-publish-") as scratch:
            staged=Path(scratch);(staged/"audio").mkdir()
            if not options.visuals_only:
                out=evidence/"audio";out.mkdir()
                result["audio"]=audio_capture(data["audio"],out,staged/"audio",options)
            report["passed"]=True
            report["pilot_complete"]=not options.visuals_only and not options.skip_existing_cases and options.clock_mode=="real-time"
            result["validation"]=report
            (staged/"pilot.json").write_text(json.dumps(result,separators=(",",":"))+"\n")
            # No source writes while an emulator session is live.
            (MANUAL/"generated").mkdir(exist_ok=True)
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
