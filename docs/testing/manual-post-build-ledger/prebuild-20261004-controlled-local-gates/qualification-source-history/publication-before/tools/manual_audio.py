"""Native musical guide assets. No synthetic audio or replacement framebuffer."""
import argparse, base64, fcntl, hashlib, json, math, os, shutil, subprocess, sys, tempfile, time, traceback, uuid
from pathlib import Path
from types import SimpleNamespace
import yaml
from manual_model import ROOT, MANUAL
from manual_capture import tracked_driver, set_mask_field, frame, close
sys.path.insert(0,str(ROOT/"tests/behaviour"))
from driver import digest, write
from pcm_oracle import read_wav

VOICES={"Oilcan 1","Polyperc 1","Doubledecker"}
def validate(data):
    if data.get("schema_version")!=1 or not data.get("examples"):raise ValueError("audio schema")
    ids=set()
    for example in data["examples"]:
        ident=example["id"]
        if ident in ids or not ident.replace("-","").isalnum():raise ValueError("example id")
        ids.add(ident)
        if example["bars"]!=4 or example["bpm"]!=90:raise ValueError("timing: fixture is four bars at 90 BPM")
        relative=example.get("mode")=="relative-scale-slots"
        channels=set();players=set()
        for track in example["tracks"]:
            if track["channel"] in channels:raise ValueError("duplicate channel")
            channels.add(track["channel"])
            if track["voice"] in players or track["voice"] not in VOICES:raise ValueError("duplicate or unsupported player")
            players.add(track["voice"])
            if not 1<=track["channel"]<=3 or not 1<=track["velocity"]<=127:raise ValueError("track range")
            if relative:
                if "note" in track:raise ValueError("Relative harmony must leave Note masks X")
                if not 1<=track.get("pattern",0)<=16 or track.get("octave",0) not in (-2,-1,0,1,2):raise ValueError("relative pattern")
            elif not 0<=track.get("note",-1)<=127:raise ValueError("absolute note mask")
            if not 1<=track["length_detents"]<=32:raise ValueError("length")
            phrases=[track["phrase"]]+([track["final_bar"]] if "final_bar" in track else [])+track.get("bar_phrases",[])
            if "bar_phrases" in track and len(track["bar_phrases"])!=example["bars"]:raise ValueError("bar phrase count")
            for values in phrases:
                if not values or len({v[0] for v in values})!=len(values):raise ValueError("phrase uniqueness")
                if any(not 1<=step<=16 or not 0<=note<=(6 if relative else 127) for step,note in values):raise ValueError("phrase bounds")
            limit=16 if relative else 64
            overrides=track.get("velocity_overrides",[])
            if len({row[0] for row in overrides})!=len(overrides) or any(not 1<=step<=limit or not 1<=value<=127 for step,value in overrides):
                raise ValueError("step velocity overrides")
            if any(not 0<=v<=14 for v in track.get("chords",[])) or len(track.get("chords",[]))>4:raise ValueError("chord offsets")
        if relative:
            if example.get("scale_slots")!=[dict(slot=1,root="C",root_detents=0),dict(slot=2,root="D",root_detents=2)]:raise ValueError("C and D scale slots")
            if example.get("phase_changes")!=[dict(at_step=32,scale_slot=2,root="D")]:raise ValueError("scale comparison phases")
        if example.get("purpose")=="lesson-comparison" and not example.get("midi_contract"):raise ValueError("lesson MIDI contract")
    import jsonschema
    try:jsonschema.Draft7Validator(json.loads((MANUAL/"audio.schema.json").read_text())).validate(data)
    except jsonschema.ValidationError as error:raise ValueError("audio schema: "+error.message) from error
    return data

def expand(track,bars):
    return [[bar*16+step,note] for bar in range(bars)
            for step,note in (track["bar_phrases"][bar] if "bar_phrases" in track else
                            track.get("final_bar",track["phrase"]) if bar==bars-1 else track["phrase"])]

def pin_check(root):
    lock=json.loads((MANUAL/"voices.lock.json").read_text())
    for name in ("oilcan","nb_polyperc","doubledecker"):
        head=subprocess.check_output(["git","-C",str(root/name),"rev-parse","HEAD"],text=True).strip()
        if head!=lock[name]["commit"]:raise ValueError("voice pin mismatch "+name)
        status=subprocess.check_output(["git","-C",str(root/name),"status","--porcelain"],text=True)
        if status.strip():raise ValueError("dirty upstream voice "+name)
    return {name:lock[name] for name in ("oilcan","nb_polyperc","doubledecker")}

def set_tempo(c):
    c.ui.song_editor();c.ui.open_task("Song","tempo_feel");c.ui.select_row("tempo",0)
    c.enc(3,-300);c.enc(3,60);c.ui.press_key(3)
    c.ui.expect_selected_field("vertical_list","Tempo","90")

def route_track(c,track,channel,midi=False,port=1):
    c.ui.channel_editor();c.ui.select_channel(channel);c.ui.channel_page("midi_config",channel=channel)
    c.enc(2,-12);c.enc(3,-64)
    if midi:
        c.enc(3,1);c.enc(2,1);c.enc(3,-64)
        if port>1:c.enc(3,port-1)
        c.enc(2,1);c.enc(3,-64)
        if channel>1:c.enc(3,channel-1)
        c.ui.press_key(3)
    else:c.ui.pick_device(track["voice"])

def configure(c,example,tracks,midi_only=False,witnesses=False):
    set_tempo(c)
    relative=example.get("mode")=="relative-scale-slots"
    if relative:
        for track in tracks:
            c.ui.channel_editor();c.ui.pattern_editor();c.ui.tap_control("pattern_select",track["pattern"])
            for step,degree in track["phrase"]:c.ui.tap_step(step)
            c.ui.pattern_editor(view="note",from_view="trigger")
            for step,degree in track["phrase"]:c.ui.tap_control("pattern_note_degree",(step,degree))
            c.ui.expect_header("note_editor",pattern=track["pattern"])
    targets=[(track,track["channel"],midi_only,track["channel"]) for track in tracks]
    if witnesses:targets += [(track,14+track["channel"],True,1) for track in tracks]
    for track,ch,midi,port in targets:
        route_track(c,track,ch,midi,port)
        if relative:
            c.ui.tap_control("pattern_slot",track["pattern"]);c.ui.set_range(1,16)
            c.ui.set_channel_octave(track.get("octave",0))
        else:c.ui.set_range(1,64)
        c.ui.channel_page("masks",channel=ch)
        if relative:
            set_mask_field(c,1,0);c.ui.expect_field_value("note","X")
            set_mask_field(c,0,0);c.ui.expect_field_value("trig","X")
        else:
            set_mask_field(c,0,1);set_mask_field(c,1,track["note"]+1)
        set_mask_field(c,2,track["velocity"]+1)
        set_mask_field(c,3,track["length_detents"])
        for slot,value in enumerate(track.get("chords",[])):set_mask_field(c,4+slot,value)
        if not relative:
            for step,note in expand(track,example["bars"]):
                set_mask_field(c,0,0)
                with c.ui.hold_step(step):c.enc(3,1)
                set_mask_field(c,1,0)
                if note!=track["note"]:
                    with c.ui.hold_step(step):c.enc(3,note-track["note"])
        for step,value in track.get("velocity_overrides",[]):
            set_mask_field(c,2,0)
            with c.ui.hold_step(step):
                c.enc(3,value-track["velocity"]);c.ui.expect_field_value("velocity",str(value))
                c.results.append(dict(kind="manual-audio-step-velocity",channel=ch,step=step,
                                      expected=value,citation="README.md#masks",passed=True))
        if not relative:
            set_mask_field(c,1,0)
            name=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"][track["note"]%12]+str(track["note"]//12-2)
            c.ui.expect_field_value("note",name)
        set_mask_field(c,2,0);c.ui.expect_field_value("velocity",str(track["velocity"]))
        c.results.append(dict(kind="manual-audio-routing",citation="README.md#masks",channel=ch,
                              voice="public MIDI witness" if midi else track["voice"],
                              authored_channel=track["channel"],relative_notes=relative,
                              phrase=expand(track,example["bars"]),passed=True))
    if relative:
        c.ui.scale_editor()
        for slot in example["scale_slots"]:
            c.ui.tap_control("scale_slot",slot["slot"]);c.enc(2,-12);c.enc(3,-64)
            if slot["root_detents"]:c.enc(3,slot["root_detents"])
            c.ui.expect_selected_field("vertical_list","Root",slot["root"])
            c.ui.select_row("scale",1);c.enc(3,-64)
            c.ui.expect_selected_field("vertical_list","Scale","Major");c.ui.press_key(3)
        c.ui.tap_control("scale_slot",1);c.enc(2,-12);c.ui.press_key(3)
        c.ui.expect_selected_field("vertical_list","Root","C")
    else:
        c.ui.select_channel(tracks[-1]["channel"]);c.ui.channel_page("masks",channel=tracks[-1]["channel"])

def mapped_score(example,tracks,witness=False):
    channels={track["channel"] for track in tracks}
    wanted=[dict(row) for row in example["midi_contract"]["notes"] if row["status"]-143 in channels]
    if witness:
        for row in wanted:row.update(port=1,status=row["status"]+14)
    return wanted

def verify_midi_packets(packets,expected,origin,clock_mode,allow_boundary=False):
    from collections import Counter
    key="logical_ns" if clock_mode=="controlled-experimental" else "monotonic_ns"
    tolerance=2e-9 if clock_mode=="controlled-experimental" else .01
    ons=[p for p in packets if 144<=p["bytes"][0]<=159 and p["bytes"][2]>0]
    if allow_boundary:
        if len(ons)<len(expected)+1:raise AssertionError("Missing closing cycle onset")
        closing=ons[len(expected)]
        if abs((closing[key]-origin)/1e9-64/6)>tolerance:raise AssertionError("Closing onset is not the declared 64-step boundary")
        boundary=closing["index"]
        packets=[p for p in packets if p["index"]<boundary]
        ons=ons[:len(expected)]
    else:
        if len(ons)!=len(expected):raise AssertionError(("Unexpected audio MIDI witness onset count",len(ons),len(expected)))
    for port,status in {(v["port"],v["status"]) for v in expected}:
        actual=[p for p in ons if p["port"]==port and p["bytes"][0]==status]
        literal=sorted([v for v in expected if v["port"]==port and v["status"]==status],key=lambda v:v["step"])
        if [p["bytes"] for p in actual]!=[[v["status"],v["note"],v["velocity"]] for v in literal]:raise AssertionError(("Literal musical output",actual,literal))
        for packet,row in zip(actual,literal):
            if abs((packet[key]-origin)/1e9-row["step"]/6)>tolerance:raise AssertionError(("Musical onset",packet,row))
            release=next(p for p in packets if p["index"]>packet["index"] and p["port"]==port and p["bytes"]==[status-16,row["note"],row["velocity"]])
            if abs((release[key]-packet[key])/1e9-row["length"]/6)>tolerance:raise AssertionError(("Musical gate",release,row))
    wanted=Counter((v["port"],v["status"],v["note"],v["velocity"]) for v in expected)
    wanted.update((v["port"],v["status"]-16,v["note"],v["velocity"]) for v in expected)
    if Counter((p["port"],*p["bytes"]) for p in packets if 128<=p["bytes"][0]<=159)!=wanted:raise AssertionError("Unexpected or missing musical packets")
    return dict(expected=expected,onsets=len(ons),timing_tolerance_seconds=tolerance,passed=True)

def apply_phase(c,change,origin_ns,key):
    selected=[c.ui.control_edge("scale_slot",True,change["scale_slot"]),
              c.ui.control_edge("scale_slot",False,change["scale_slot"])]
    c.elapse(.06)
    applied=[c.ui.key_edge(3,True),c.ui.key_edge(3,False)]
    receipt=applied[0]
    applied_ns=(receipt.get("native",{}).get("monotonic_ns",receipt.get("monotonic_ns"))
                if key=="monotonic_ns" else c.logical_ns)
    relative=(applied_ns-origin_ns)/1e9
    target=change["at_step"]/6
    if not target-.5<relative<target:raise AssertionError(("Scale apply outside quiet interval",relative,target))
    c.elapse(.06);c.ui.expect_header("scale",slot=change["scale_slot"])
    c.ui.expect_selected_field("vertical_list","Root",change["root"])
    row=dict(change,applied_time_from_first_note=relative,selected_receipts=selected,apply_receipts=applied,
             output=frame(c,"MA-AUDIO-SCALE-PHASE","RootD"),citation="README.md#scale-editor",passed=True)
    c.results.append(dict(kind="manual-audio-scale-phase",**row))
    return row

def midi_worker_command(run,ident,out,app,options,lane):
    if not options.midi_controlled_install:raise ValueError("MIDI witnesses require an explicit controlled installation")
    if not getattr(options,"controlled_local",False) and not options.midi_real_install:
        raise ValueError("Full MIDI qualification requires explicit real and controlled installations")
    command=[sys.executable,str(Path(__file__)),"--source",str(run/"source.yaml"),
        "--mod-code-root",str(options.mod_code_root),"--audio-install",str(options.audio_install),
        "--midi-worker",str(out),"--midi-example",ident,"--application",str(app),
        "--clock-mode",lane,"--midi-controlled-install",str(options.midi_controlled_install)]
    if options.midi_real_install:command += ["--midi-real-install",str(options.midi_real_install)]
    return command

def midi_acceptance(example,out,options,clock_mode):
    installation=options.midi_controlled_install if clock_mode!="real-time" else options.midi_real_install
    if not installation:raise ValueError("MIDI witness requires an explicit lane installation")
    c=tracked_driver(out,clock_mode=clock_mode,experimental_install=installation,app_root=options.app_root)
    try:
        configure(c,example,example["tracks"],midi_only=True)
        before=c.snapshot()["midi_count"];c.ui.play()
        def notes(state):return [v for v in state["midi"] if v["index"]>before and 144<=v["bytes"][0]<=159 and v["bytes"][2]>0]
        state=c.wait(lambda s:bool(notes(s)),timeout=3)
        key="logical_ns" if clock_mode!="real-time" else "monotonic_ns"
        origin=notes(state)[0][key];changes=[];pending=list(example.get("phase_changes",[]))
        expected=mapped_score(example,example["tracks"])
        deadline=time.monotonic()+max(30,64/6+5) if clock_mode=="real-time" else time.monotonic()+180
        while len(notes(state))<len(expected)+1:
            if time.monotonic()>deadline:raise TimeoutError("Lesson MIDI comparison")
            now=(c.logical_ns-origin)/1e9 if clock_mode!="real-time" else (time.monotonic()*1e9-origin)/1e9
            if pending and now>=pending[0]["at_step"]/6-.3:changes.append(apply_phase(c,pending.pop(0),origin,key))
            c.elapse(.01 if clock_mode!="real-time" else .03);state=c.snapshot()
        packets=[p for p in state["midi"] if p["index"]>before]
        verified=verify_midi_packets(packets,expected,origin,clock_mode,allow_boundary=True)
        c.ui.stop();c.wait(lambda s:not s["midi_capture"]["outstanding"])
        c.results.append(dict(kind="manual-audio-lesson-midi",case="MA-AUDIO-"+example["id"],clock_mode=clock_mode,
                              phases=changes,origin_ns=origin,midi_start_index=before,midi_end_index=state["midi_count"],
                              boundary_index=notes(state)[len(expected)]["index"],citation="README.md#typical-workflow",**verified))
    finally:close(c,{})
    return dict(clock_mode=clock_mode,path=str(out),results_sha256=digest(out/"results.json"),
                identity_sha256=digest(out/"native/identity.json"),passed=True)

def metrics(wav,seconds):
    rate,channels=read_wav(wav)
    samples=[v for channel in channels for v in channel]
    rms=math.sqrt(sum(v*v for v in samples)/len(samples));peak=max(abs(v) for v in samples)
    window=round(.25*rate)
    tail=[v for channel in channels for v in channel[-window:]]
    tail_rms=math.sqrt(sum(v*v for v in tail)/len(tail))
    if rms<=.0001:raise ValueError("silent PCM "+str(rms))
    if peak>=.98:raise ValueError("insufficient headroom "+str(peak))
    if tail_rms>=max(.002,rms*.15):raise ValueError("tail not settled "+str((rms,tail_rms)))
    return dict(peak=peak,rms=rms,tail_rms=tail_rms,sample_rate=rate,
                duration=len(channels[0])/rate,clipped_samples=sum(abs(v)>=.98 for v in samples))

def lesson_pcm(example,tracks,wav,witness):
    """Fixed interiors measured from public MIDI receipts and native PCM epoch."""
    from pcm_oracle import analyse
    rate,channels=read_wav(wav)
    samples=[sum(v)/len(v) for v in zip(*channels)]
    offset=witness["origin_ns"]/1e9-witness["capture_epoch"]
    checked=[]
    if example["id"]=="ghost-note-comparison":
        for step in (11,27,43,59):
            section=samples[round((offset+step/6+.06)*rate):round((offset+step/6+.14)*rate)]
            if len(section)<round(.079*rate):raise ValueError("Missing ghost PCM interior")
            rms=math.sqrt(sum(v*v for v in section)/len(section))
            high=math.sqrt(sum((b-a)**2 for a,b in zip(section,section[1:]))/(len(section)-1))
            checked.append(dict(step=step,rms=rms,first_difference_rms=high))
        baseline=max(sum(v["first_difference_rms"] for v in checked[:2])/2,1e-5)
        if any(v["rms"]<=.001 or v["first_difference_rms"]<=baseline*1.5 for v in checked[2:]):
            raise ValueError(("Ghost note did not contribute audible PCM",checked))
        return dict(kind="ghost-note-interiors",windows=checked,minimum_difference_ratio=1.5,passed=True)
    if example["id"]=="scale-slot-comparison" and len(tracks)==1 and tracks[0]["voice"]=="Polyperc 1":
        for note in mapped_score(example,tracks):
            start=offset+note["step"]/6+.30;end=offset+note["step"]/6+.42
            section=samples[round(start*rate):round(end*rate)]
            frames,half,hop=analyse(section,rate)
            if len(frames)<6 or any(v["note"]!=note["note"] for v in frames):
                raise ValueError(("Relative scale PCM pitch",note,frames))
            checked.append(dict(step=note["step"],expected_note=note["note"],start=start,end=end,frames=frames))
        return dict(kind="relative-scale-pitch-interiors",windows=checked,
                    domain="dry monophonic Polyperc MIDI48..84",absolute_latency_verified=False,passed=True)
    return None

def capture(example,tracks,out,options,case):
    c=tracked_driver(out,profile=example["profile"],mod_code_root=options.mod_code_root,
                     app_root=options.app_root,experimental_install=options.audio_install)
    job=None;timeline=[];lesson=example.get("purpose")=="lesson-comparison"
    try:
        configure(c,example,tracks,witnesses=lesson)
        c.elapse(13)
        seconds=example["bars"]*4*60/example["bpm"]
        before=c.snapshot()["midi_count"]
        job=c.runtime.capture_start(seconds+3)
        epoch=job["started"]["start_monotonic"]
        c.ui.play();origin=time.monotonic()*1e9;changes=[]
        def packets(state):return [p for p in state["midi"] if p["index"]>before]
        if lesson:
            state=c.wait(lambda s:any(144<=p["bytes"][0]<=159 and p["bytes"][2]>0 for p in packets(s)),timeout=3)
            origin=next(p["monotonic_ns"] for p in packets(state) if 144<=p["bytes"][0]<=159 and p["bytes"][2]>0)
        pending=list(example.get("phase_changes",[]))
        stop_at=origin/1e9+seconds-.03
        while time.monotonic()<stop_at:
            if pending and time.monotonic()-origin/1e9>=pending[0]["at_step"]/6-.3:
                changes.append(apply_phase(c,pending.pop(0),origin,"monotonic_ns"))
            timeline.append(dict(time=time.monotonic()-epoch,output=frame(c,case,"playhead")))
            c.elapse(max(.001,min(.10,stop_at-time.monotonic())))
        c.ui.stop();musical_state=c.snapshot();c.tap(15,8);c.elapse(3)
        status=c.runtime.capture_status(job["job_id"])
        deadline=time.monotonic()+10
        while status["status"]=="capturing":
            if time.monotonic()>deadline:raise TimeoutError("WAV capture")
            c.elapse(.1);status=c.runtime.capture_status(job["job_id"])
        if status["status"]!="complete":raise ValueError(status)
        wav=Path(status["output"])
        if digest(wav)!=status["sha256"]:raise ValueError("native WAV integrity")
        finished=status["finished"]
        if finished["frames"]!=finished["expected_frames"] or any(finished[k] for k in ("xruns","nonfinite","server_dead")):raise ValueError("Native capture integrity")
        observed=metrics(wav,seconds)
        if abs(observed["duration"]-(seconds+3))>1/observed["sample_rate"]:raise ValueError("Native WAV duration")
        c.results.append(dict(kind="manual-audio-PCM",citation="characterisation: digital audio integrity",
                              case=case,metrics=observed,passed=True))
        result=dict(timeline=timeline,metrics=observed,wav=str(wav),
                    evidence=dict(path=str(out),wav_sha256=digest(wav),job=status))
        if lesson:
            verified=verify_midi_packets(packets(musical_state),mapped_score(example,tracks,witness=True),origin,"real-time")
            witness=dict(verified,origin_ns=origin,capture_epoch=epoch,midi_start_index=before,midi_end_index=musical_state["midi_count"])
            c.results.append(dict(kind="manual-audio-MIDI-witness",citation="README.md#masks",**witness))
            result.update(midi_witness=witness,phase_observations=changes)
            pcm=lesson_pcm(example,tracks,wav,witness)
            if pcm:
                result["lesson_pcm"]=pcm
                c.results.append(dict(kind="manual-audio-lesson-PCM",citation="characterisation: declared PCM interiors",**pcm))
        return result
    finally:
        if job:
            try:
                if c.runtime.capture_status(job["job_id"])["status"]=="capturing":c.runtime.capture_cancel(job["job_id"])
            except Exception:pass
        try:close(c,{})
        finally:
            if not getattr(c,"finished",False):c.finish()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=MANUAL/"audio-scenes.yaml")
    parser.add_argument("--mod-code-root",type=Path,required=True)
    parser.add_argument("--audio-install",required=True)
    parser.add_argument("--ffmpeg",default="ffmpeg")
    parser.add_argument("--midi-emulator",type=Path)
    parser.add_argument("--midi-real-install")
    parser.add_argument("--midi-controlled-install")
    parser.add_argument("--midi-worker",type=Path,help=argparse.SUPPRESS)
    parser.add_argument("--midi-example",help=argparse.SUPPRESS)
    parser.add_argument("--application",type=Path,help=argparse.SUPPRESS)
    parser.add_argument("--clock-mode",default="real-time",help=argparse.SUPPRESS)
    parser.add_argument("--example",action="append")
    parser.add_argument("--validate-only",action="store_true")
    parser.add_argument("--controlled-local",action="store_true",
                        help="Generate all audio assets and controlled MIDI comparisons; realtime qualification remains pending CI")
    options=parser.parse_args()
    source_text=options.source.read_text()
    data=validate(yaml.safe_load(source_text))
    pins=pin_check(options.mod_code_root)
    if options.validate_only:return 0
    if options.midi_worker:
        options.app_root=options.application
        example=next(v for v in data["examples"] if v["id"]==options.midi_example)
        options.midi_worker.mkdir(parents=True)
        result=midi_acceptance(example,options.midi_worker,options,options.clock_mode)
        write(options.midi_worker/"lesson-result.json",result)
        return 0
    if options.controlled_local and options.example:
        parser.error("--controlled-local requires the complete authored audio inventory; do not select a subset")
    if any(v.get("purpose")=="lesson-comparison" for v in data["examples"]):
        if options.controlled_local:
            if not (options.midi_emulator and options.midi_controlled_install):
                parser.error("Controlled lesson comparisons require --midi-emulator and --midi-controlled-install")
        elif not (options.midi_emulator and options.midi_real_install and options.midi_controlled_install):
            parser.error("Lesson comparisons require --midi-emulator, --midi-real-install and --midi-controlled-install")
    run=ROOT.parent/"mosaic-manual-audio-runs"/uuid.uuid4().hex;run.mkdir(parents=True)
    (run/"source.yaml").write_text(source_text)
    shutil.copyfile(Path(__file__),run/"capture-tool.py")
    shutil.copyfile(ROOT/"tools/manual_capture.py",run/"capture-helpers.py")
    shutil.copyfile(MANUAL/"audio.schema.json",run/"audio.schema.json")
    harness_sources={}
    for name in ("driver.py","ui.py","ui_map.py","pcm_oracle.py"):
        source=ROOT/"tests/behaviour"/name
        if source.is_file():
            shutil.copyfile(source,run/name);harness_sources[name]=digest(source)
    app=run/"application";app.mkdir()
    shutil.copyfile(ROOT/"mosaic.lua",app/"mosaic.lua")
    shutil.copytree(ROOT/"lib",app/"lib",ignore=shutil.ignore_patterns("tests",".git","__pycache__"))
    shutil.copytree(ROOT/"docs/ui-reimplementation/code",app/"docs/ui-reimplementation/code")
    options.app_root=app
    report=dict(schema_version=1,source_sha256=digest(options.source),tool_sha256=digest(Path(__file__)),
                helper_sha256=digest(ROOT/"tools/manual_capture.py"),schema_sha256=digest(MANUAL/"audio.schema.json"),
                revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                harness_sha256=harness_sources,voice_pins=pins,
                clock_mode="controlled-experimental" if options.controlled_local else "real-time",
                complete_regression_run=False,passed=False,
                controlled_lane="inapplicable: native DSP audio depends on real host time",examples=[])
    if options.controlled_local:
        report.update(validation_scope="controlled-manual-generation",realtime_qualification="pending-ci",
                      audio_capture_clock_mode="real-time")
    try:
        with open("/tmp/mosaic-manual-native.lock","a") as lock,tempfile.TemporaryDirectory(prefix="mosaic-manual-audio-") as scratch:
            print("Waiting for exclusive native runtime",flush=True)
            fcntl.flock(lock,fcntl.LOCK_EX)
            destination=Path(scratch)
            for example in data["examples"]:
                if options.example and example["id"] not in options.example:continue
                ident=example["id"];solos=[];musical=[]
                if example.get("purpose")=="lesson-comparison":
                    lanes=("controlled-experimental",) if options.controlled_local else ("real-time","controlled-experimental")
                    for lane in lanes:
                        out=run/(ident+"-midi-"+lane)
                        env=dict(os.environ,MONOME_EMULATOR=str(options.midi_emulator))
                        subprocess.run(midi_worker_command(run,ident,out,app,options,lane),env=env,check=True)
                        musical.append(json.loads((out/"lesson-result.json").read_text()))
                        print("Literal lesson MIDI passed",ident,lane,flush=True)
                for track in example["tracks"]:
                    out=run/(ident+"-solo-"+str(track["channel"]));out.mkdir()
                    result=capture(example,[track],out,options,"MA-AUDIO-"+ident+"-SOLO-"+str(track["channel"]))
                    solos.append(dict(channel=track["channel"],voice=track["voice"],metrics=result["metrics"],evidence=result["evidence"],
                        **{key:result[key] for key in ("midi_witness","lesson_pcm","phase_observations") if key in result}))
                    print("Audible independent player",ident,track["voice"],flush=True)
                out=run/(ident+"-mix");out.mkdir()
                result=capture(example,example["tracks"],out,options,"MA-AUDIO-"+ident)
                seconds=example["bars"]*4*60/example["bpm"]
                files=[]
                for suffix,codec in (("ogg","libopus"),("mp3","libmp3lame")):
                    target=destination/(ident+"."+suffix)
                    subprocess.run([options.ffmpeg,"-y","-loglevel","error","-i",result["wav"],"-af",
                       "afade=t=in:d=0.015,afade=t=out:st="+str(seconds+2.8)+":d=0.2",
                       "-c:a",codec,"-b:a","128k",str(target)],check=True)
                    files.append("audio/"+target.name)
                result.pop("wav")
                if musical:result["musical_evidence"]=musical
                report["examples"].append(dict(example,**result,files=files,file_sha256={value:digest(destination/Path(value).name) for value in files},solo_contributions=solos,
                       acceptance_case="MA-AUDIO-"+ident,
                       synchronization="Observed framebuffer/grid sampled against host monotonic recording time; not sample-exact or physical-norns calibration."))
                print("Captured mix",ident,flush=True)
            report["passed"]=True
            write(run/"audio-scenes.json",report)
            (MANUAL/"audio").mkdir(exist_ok=True)
            for path in destination.iterdir():shutil.copyfile(path,MANUAL/"audio"/path.name)
            write(MANUAL/"generated/audio-scenes.json",report)
    except Exception:
        report["failure"]=traceback.format_exc();raise
    finally:
        write(run/"report.json",report)
        print("Preserved audio evidence",run,flush=True)
    return 0

def native_midi_packets(out,start,end):
    return [row for row in (json.loads(v) for v in (out/"native/native-events.jsonl").read_text().splitlines())
            if row.get("kind")==3 and start<row["index"]<=end]

def audit_phases(example,out,phases,origin,clock_mode):
    from ui_map import control_cell
    actions=[json.loads(v) for v in (out/"native/actions.jsonl").read_text().splitlines()]
    acks={v["ack"]["sequence"]:v for v in actions}
    changes=example.get("phase_changes",[])
    if len(phases)!=len(changes):raise ValueError("Missing public scale apply")
    results=json.loads((out/"results.json").read_text())
    for phase,authored in zip(phases,changes):
        if any(phase.get(k)!=v for k,v in authored.items()):raise ValueError("Changed authored scale phase")
        x,y=control_cell("scale_slot",phase["scale_slot"])
        expected=[dict(type="grid",x=x,y=y,state=v) for v in (1,0)]+[dict(type="key",n=3,state=v) for v in (1,0)]
        receipts=phase["selected_receipts"]+phase["apply_receipts"]
        if len(receipts)!=4 or [v["sequence"] for v in receipts]!=sorted(v["sequence"] for v in receipts):raise ValueError("Unordered public apply receipts")
        for receipt,action in zip(receipts,expected):
            native=acks.get(receipt["sequence"])
            if native is None or native["ack"]!=receipt or native["request"]["action"]!=action or receipt["status"]!="applied":raise ValueError("Changed native scale apply")
        if clock_mode=="real-time":
            actual=(receipts[2]["native"]["monotonic_ns"]-origin)/1e9
        else:
            advances=[v["request"]["action"]["nanoseconds"] for v in actions if v["ack"]["sequence"]<receipts[2]["sequence"] and v["request"]["action"]["type"]=="advance"]
            actual=(sum(advances)-origin)/1e9
        if abs(actual-phase["applied_time_from_first_note"])>1e-9 or not authored["at_step"]/6-.5<actual<authored["at_step"]/6:raise ValueError("Scale apply interval")
        if not any(v.get("kind")=="manual-audio-scale-phase" and all(v.get(k)==value for k,value in phase.items()) for v in results):raise ValueError("Unbound scale apply")
        from frame_oracle import selected_field_matches,live_header_matches
        from ui_map import header_parts
        output=phase["output"];binding=output["binding"]
        observations=json.loads((out/"observations.json").read_text())
        state=next((v["state"] for v in observations if v["state"]["frame"]["sha256"]==binding["sha256"] and hashlib.sha256(bytes(v["state"]["grid"])).hexdigest()==binding["grid_sha256"]),None)
        if state is None or binding not in results or not selected_field_matches(state,"vertical_list","Root",authored["root"]) or not live_header_matches(state,*header_parts("scale",slot=authored["scale_slot"])):raise ValueError("Missing actual applied Root frame")
        levels=[v for v,n in output["screen_rle"] for _ in range(n)]
        if levels!=[v//17 for v in base64.b64decode(state["frame"]["pixels_base64"])[::4]] or output["grid"]!=state["grid"]:raise ValueError("Changed applied Root frame")
    return True

def audit_lesson_capture(example,tracks,record):
    out=Path(record["evidence"]["path"])
    results=json.loads((out/"results.json").read_text())
    observations=json.loads((out/"observations.json").read_text())
    witness=record["midi_witness"]
    if not any(v.get("kind")=="manual-audio-MIDI-witness" and all(v.get(k)==value for k,value in witness.items()) for v in results):raise ValueError("Native MIDI witness binding")
    state=max((row["state"] for row in observations),key=lambda v:v["midi_count"])
    packets=native_midi_packets(out,witness["midi_start_index"],witness["midi_end_index"])
    first=next(p for p in packets if 144<=p["bytes"][0]<=159 and p["bytes"][2]>0)
    if first["monotonic_ns"]!=witness["origin_ns"]:raise ValueError("Changed first witness onset")
    verified=verify_midi_packets(packets,mapped_score(example,tracks,witness=True),witness["origin_ns"],"real-time")
    if any(witness.get(k)!=v for k,v in verified.items()):raise ValueError("Changed MIDI witness")
    if witness["capture_epoch"]!=record["evidence"]["job"]["started"]["start_monotonic"]:raise ValueError("Changed native PCM epoch")
    wav=out/"native/audio-captures"/record["evidence"]["job"]["job_id"]/"output.wav"
    if lesson_pcm(example,tracks,wav,witness)!=record.get("lesson_pcm"):raise ValueError("Changed lesson PCM oracle")
    audit_phases(example,out,record.get("phase_observations",[]),witness["origin_ns"],"real-time")
    return True

def audit_lesson_midi(example,lanes,controlled_local=False):
    expected={"controlled-experimental"} if controlled_local else {"real-time","controlled-experimental"}
    if {v["clock_mode"] for v in lanes}!=expected or len(lanes)!=len(expected):
        raise ValueError("Controlled generation requires only its controlled MIDI comparison" if controlled_local else "Both musical MIDI lanes required")
    for lane in lanes:
        out=Path(lane["path"])
        if digest(out/"results.json")!=lane["results_sha256"] or digest(out/"native/identity.json")!=lane["identity_sha256"]:raise ValueError("Changed musical MIDI identity")
        rows=json.loads((out/"results.json").read_text())
        acceptance=[v for v in rows if v.get("kind")=="manual-audio-lesson-midi"]
        if len(acceptance)!=1 or not acceptance[0]["passed"]:raise ValueError("Missing musical MIDI acceptance")
        proof_row=acceptance[0]
        packets=native_midi_packets(out,proof_row["midi_start_index"],proof_row["midi_end_index"])
        expected=mapped_score(example,example["tracks"])
        first=next(p for p in packets if 144<=p["bytes"][0]<=159 and p["bytes"][2]>0)
        key="logical_ns" if lane["clock_mode"]!="real-time" else "monotonic_ns"
        if first[key]!=proof_row["origin_ns"]:raise ValueError("Changed first lesson onset")
        closing=[p for p in packets if 144<=p["bytes"][0]<=159 and p["bytes"][2]>0][len(expected)]
        if closing["index"]!=proof_row["boundary_index"]:raise ValueError("Changed lesson closing boundary")
        proof=verify_midi_packets(packets,expected,first[key],lane["clock_mode"],allow_boundary=True)
        audit_phases(example,out,proof_row["phases"],first[key],lane["clock_mode"])
        if any(acceptance[0].get(k)!=v for k,v in proof.items()):raise ValueError("Changed literal MIDI score")
        cleanup=json.loads((out/"native/cleanup.json").read_text())
        if not cleanup or any(v.get("returncode") is None for v in cleanup):raise ValueError("MIDI lesson cleanup")
    return True

def audit_publication(path=MANUAL/"generated/audio-scenes.json",controlled_local=False):
    """Independently audit authoring, native observations, PCM and encoded assets."""
    report=json.loads(Path(path).read_text())
    if controlled_local:
        if report.get("validation_scope")!="controlled-manual-generation" or report.get("realtime_qualification")!="pending-ci":raise ValueError("controlled audio publication scope")
        if report.get("clock_mode")!="controlled-experimental" or report.get("audio_capture_clock_mode")!="real-time":raise ValueError("controlled audio clock identity")
        if report.get("complete_regression_run") is not False:raise ValueError("controlled audio cannot claim complete regression")
    elif report.get("validation_scope")=="controlled-manual-generation":
        raise ValueError("Controlled audio publication requires the explicit controlled audit")
    authored=validate(yaml.safe_load((MANUAL/"audio-scenes.yaml").read_text()))
    if report["source_sha256"]!=digest(MANUAL/"audio-scenes.yaml"):raise ValueError("stale audio authoring")
    if not report["passed"] or report.get("complete_regression_run"):raise ValueError("audio evidence scope")
    expected={v["id"]:v for v in authored["examples"]}
    if set(expected)!={v["id"] for v in report["examples"]}:raise ValueError("audio inventory")
    checked=0
    native_run=Path(report["examples"][0]["evidence"]["path"]).parent
    native_source=report.get("publication",{}).get("native_source_sha256",report["source_sha256"])
    if digest(native_run/"source.yaml")!=native_source:raise ValueError("native source identity")
    if digest(native_run/"capture-tool.py")!=report["tool_sha256"]:raise ValueError("native tool identity")
    if report.get("schema_sha256") and (digest(native_run/"audio.schema.json")!=report["schema_sha256"] or digest(MANUAL/"audio.schema.json")!=report["schema_sha256"]):raise ValueError("Audio schema identity")
    for name,value in report.get("harness_sha256",{}).items():
        if digest(native_run/name)!=value or digest(ROOT/"tests/behaviour"/name)!=value:raise ValueError("Audio harness identity "+name)
    if "publication" in report:
        baseline=json.loads((native_run/"audio-scenes.json").read_text())
        if not baseline["passed"] or baseline["source_sha256"]!=native_source:raise ValueError("native publication baseline")
        originals={v["id"]:v for v in baseline["examples"]}
        for example in report["examples"]:
            for key in ("timeline","metrics","evidence","solo_contributions","tracks","bars","bpm","profile","musical_evidence","midi_witness","phase_observations","lesson_pcm"):
                if example.get(key)!=originals[example["id"]].get(key):raise ValueError("publication changed native evidence")
    for example in report["examples"]:
        if example.get("purpose")=="lesson-comparison":
            audit_lesson_midi(example,example["musical_evidence"],controlled_local=controlled_local)
            audit_lesson_capture(example,example["tracks"],example)
            for solo in example["solo_contributions"]:
                audit_lesson_capture(example,[next(t for t in example["tracks"] if t["channel"]==solo["channel"])],solo)
        for key,value in expected[example["id"]].items():
            if example.get(key)!=value:raise ValueError("authored audio mismatch "+key)
        voices=[]
        for evidence,observed in [(example["evidence"],example["metrics"])]+[(v["evidence"],v["metrics"]) for v in example["solo_contributions"]]:
            out=Path(evidence["path"])
            wav=out/"native/audio-captures"/evidence["job"]["job_id"]/"output.wav"
            job=json.loads((wav.parent/"result.json").read_text())
            if job!=evidence["job"] or job["status"]!="complete" or job.get("input_sha256") is not None:raise ValueError("Changed native capture job")
            finished=job["finished"]
            if finished["frames"]!=finished["expected_frames"] or any(finished[k] for k in ("xruns","nonfinite","server_dead")):raise ValueError("Native capture quality")
            if digest(wav)!=evidence["wav_sha256"]:raise ValueError("native PCM hash")
            if metrics(wav,example["bars"]*4*60/example["bpm"])!=observed:raise ValueError("PCM metrics changed")
            cleanup=json.loads((out/"native/cleanup.json").read_text())
            if not cleanup or any(v.get("returncode") is None for v in cleanup):raise ValueError("native session cleanup")
            results=json.loads((out/"results.json").read_text())
            if not any(v.get("kind")=="manual-audio-PCM" and v.get("passed") and v.get("metrics")==observed for v in results):
                raise ValueError("missing PCM acceptance")
        if {v["voice"] for v in example["solo_contributions"]}!={v["voice"] for v in example["tracks"]}:raise ValueError("solo voice inventory")
        out=Path(example["evidence"]["path"])
        results=json.loads((out/"results.json").read_text())
        observations=json.loads((out/"observations.json").read_text())
        frames={}
        for row in observations:
            state=row["state"]
            frames[(state["frame"]["sha256"],hashlib.sha256(bytes(state["grid"])).hexdigest())]=state
        for row in example["timeline"]:
            output=row["output"];binding=output["binding"]
            if binding not in results or not binding["passed"]:raise ValueError("unbound audio timeline")
            state=frames.get((binding["sha256"],binding["grid_sha256"]))
            if state is None:raise ValueError("missing native audio frame")
            levels=[value for value,count in output["screen_rle"] for _ in range(count)]
            pixels=base64.b64decode(state["frame"]["pixels_base64"])
            if levels!=[v//17 for v in pixels[::4]] or output["grid"]!=state["grid"]:raise ValueError("changed audio framebuffer/grid")
            checked+=1
        files=example["files"] if isinstance(example["files"],list) else list(example["files"].values())
        for value in files:
            if not value.startswith("audio/") or not (MANUAL/value).is_file():raise ValueError("missing audio file")
        if example.get("file_sha256"):
            for value in files:
                if digest(MANUAL/value)!=example["file_sha256"][value]:raise ValueError("encoded audio hash")
    return dict(examples=len(expected),native_sessions=sum(len(v["solo_contributions"])+1 for v in report["examples"]),midi_sessions=sum(len(v.get("musical_evidence",[])) for v in report["examples"]),frames=checked,passed=True)

def audit_controlled_publication(path=MANUAL/"generated/audio-scenes.json"):
    """Audit a complete controlled-manual audio generation without REAL MIDI qualification."""
    return audit_publication(path,controlled_local=True)

if __name__=="__main__":sys.exit(main())
