"""Native musical guide assets. No synthetic audio or replacement framebuffer."""
import argparse, base64, fcntl, hashlib, json, math, os, shutil, subprocess, sys, tempfile, time, traceback, uuid
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
import yaml
from manual_model import ROOT, MANUAL
from manual_capture import tracked_driver, set_mask_field, frame, close
sys.path.insert(0,str(ROOT/"tests/behaviour"))
from driver import digest, write
from pcm_oracle import read_wav

VOICES={"Oilcan 1","Polyperc 1","Doubledecker"}
SECTION_CHANGE_KINDS={"note_merge","trig_merge","swing","octave","mute","harmony","merge_shape","trig_param","range","mask"}
from manual_audio_setups import SETUPS, WITNESS_OFFSET as WITNESS_CHANNEL_OFFSET

def twenty_fourths(value):
    """Exact count of 1/24-step ticks. YAML floats cannot spell k/3 exactly, so a
    value is accepted only when it lies within 1e-9 step of k/24 (about 0.17 ns)."""
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):return None
    ticks=round(Fraction(value)*24)
    return ticks if abs(Fraction(value)-Fraction(ticks,24))<=Fraction(1,10**9) else None

def contract_cycle_steps(example):
    return example.get("midi_contract",{}).get("cycle_steps",64)

def course_contract(contract_key,cycle_steps):
    """Course stage contract tiled to cycle_steps. CONTRACTS[key] is (period,rows)
    with steps relative to one period; whole periods only."""
    from manual_course_cases import CONTRACTS
    if contract_key not in CONTRACTS:raise ValueError("course contract_key "+str(contract_key))
    period,rows=CONTRACTS[contract_key]
    if cycle_steps%period:raise ValueError(("course contract needs whole cycles",period,cycle_steps))
    return dict(cycle_steps=cycle_steps,notes=[dict(row,step=row["step"]+period*k) for k in range(cycle_steps//period) for row in rows])

def score_order(notes):
    return sorted((v["port"],v["status"],v["note"],v["velocity"],Fraction(v["step"]),Fraction(v["length"])) for v in notes)

def validate_sections(example):
    sections=example["sections"]
    if not isinstance(sections,list) or not 1<=len(sections)<=4:raise ValueError("section slots")
    if [v.get("slot") for v in sections]!=list(range(1,len(sections)+1)):raise ValueError("section slots ascend from 1")
    for section in sections:
        length=section.get("global_length")
        if isinstance(length,bool) or not isinstance(length,int) or length%16 or not 16<=length<=64:raise ValueError("section global_length")
        changes=section.get("changes")
        if not isinstance(changes,list) or any(not isinstance(v,dict) or v.get("kind") not in SECTION_CHANGE_KINDS for v in changes):raise ValueError("section change kind")
    if sum(v["global_length"] for v in sections)!=example["bars"]*16:raise ValueError("section global_length must cover bars*16")
    if "phase_changes" in example:raise ValueError("sections cannot declare timed phase_changes")

def validate_course(example):
    """`stage` is a course stage id (or its chapter id); `contract_key` names the CONTRACTS entry of that
    chapter the example plays. The tiled contract must equal the example's own midi_contract."""
    course=example["course"];stage=course.get("stage");key=course.get("contract_key")
    path=yaml.safe_load((MANUAL/"course.yaml").read_text())["learning_path"]
    chapter=stage if stage in {v["id"] for v in path} else {s["id"]:v["id"] for v in path for s in v["stages"]}.get(stage)
    if chapter is None:raise ValueError("course stage "+str(stage))
    if not isinstance(key,str) or not key.startswith(chapter+"-"):raise ValueError("course contract_key must belong to its stage")
    contract=course_contract(key,example["bars"]*16)
    if "midi_contract" in example and score_order(example["midi_contract"]["notes"])!=score_order(contract["notes"]):raise ValueError("course contract differs from "+key)
    if example.get("setup")=="course-stage" and sorted(t["channel"] for t in example["tracks"])!=sorted({v["status"]-143 for v in contract["notes"]}):
        raise ValueError("course-stage tracks must be the channels its contract sounds on")

def validate_invariants(example):
    """An invariant window is checked on captured MIDI instead of literal notes: its literal
    reference window precedes it, same length, and the literal notes never reach the revoiced window."""
    contract=example["midi_contract"];specs=contract.get("invariants")
    if specs is None:return
    cycle=contract["cycle_steps"];channels={t["channel"] for t in example["tracks"]};windows=[]
    for spec in specs:
        if spec.get("kind") not in INVARIANT_KINDS:raise ValueError("invariant kind "+str(spec.get("kind")))
        a,c,n=spec["reference_start_step"],spec["revoiced_start_step"],spec["length_steps"]
        if spec["channel"] not in channels or not a+n<=c or c+n>cycle:raise ValueError("invariant window must follow its literal reference inside the cycle")
        windows.append((c,c+n))
        if any(note["status"]-143!=spec["channel"] for note in contract["notes"]):raise ValueError("invariant lessons are single channel")
    for note in contract["notes"]:
        if any(lo<=note["step"]<hi for lo,hi in windows):raise ValueError("invariant window cannot also hold literal notes")

def validate_contract(example):
    contract=example["midi_contract"];cycle=contract.get("cycle_steps")
    if cycle!=example["bars"]*16:raise ValueError("midi_contract cycle_steps must be bars*16")
    for note in contract.get("notes",[]):
        step=twenty_fourths(note.get("step"));length=twenty_fourths(note.get("length"))
        if step is None or length is None:raise ValueError("score step and length must be multiples of 1/24 step")
        if not 0<=step<cycle*24:raise ValueError("score step outside the cycle")
        if not 0<length<=cycle*24:raise ValueError("score length outside the cycle")
    validate_invariants(example)
    for control in contract.get("controls",[]):
        step=twenty_fourths(control.get("step"))
        if step is None:raise ValueError("control step must be a multiple of 1/24 step")
        if not 0<=step<cycle*24:raise ValueError("control step outside the cycle")

def validate(data):
    if data.get("schema_version")!=1 or not data.get("examples"):raise ValueError("audio schema")
    ids=set()
    for example in data["examples"]:
        ident=example["id"]
        if ident in ids or not ident.replace("-","").isalnum():raise ValueError("example id")
        ids.add(ident)
        sectioned="sections" in example
        if example["bpm"]!=90 or example["bars"]!=4 and not (sectioned and example["bars"] in (4,8)):
            raise ValueError("timing: fixture is four bars at 90 BPM (eight bars only for sectioned songs)")
        if sectioned:validate_sections(example)
        if "setup" in example and example["setup"] not in SETUPS:raise ValueError("unknown audio setup "+str(example["setup"]))
        if "midi_contract" in example:validate_contract(example)
        if "course" in example:validate_course(example)
        relative=example.get("mode")=="relative-scale-slots"
        channels=set();players=set();patterns=[]
        for track in example["tracks"]:
            if track["channel"] in channels:raise ValueError("duplicate channel")
            channels.add(track["channel"])
            if track["voice"] in players or track["voice"] not in VOICES:raise ValueError("duplicate or unsupported player")
            players.add(track["voice"])
            if not 1<=track["channel"]<=3 or not 1<=track["velocity"]<=127:raise ValueError("track range")
            merged="patterns" in track
            if merged:
                if not relative or any(k in track for k in ("pattern","phrase","final_bar","bar_phrases")):raise ValueError("patterns replace pattern and phrase in relative mode")
                if not isinstance(track["patterns"],list) or len(track["patterns"])<2:raise ValueError("patterns need several assigned patterns")
            last=track.get("range_last",16)
            if "range_last" in track:
                if isinstance(last,bool) or not isinstance(last,int) or not 1<=last<=64:raise ValueError("range_last")
                if "final_bar" in track or "bar_phrases" in track:raise ValueError("range_last repeats one phrase; no bar-specific phrases")
            assigned=track["patterns"] if merged else [dict(pattern=track["pattern"],phrase=track["phrase"])] if "pattern" in track else []
            patterns += [v.get("pattern") for v in assigned]
            if relative:
                if "note" in track:raise ValueError("Relative harmony must leave Note masks X")
                if not assigned or any(not 1<=v.get("pattern",0)<=16 for v in assigned) or track.get("octave",0) not in (-2,-1,0,1,2):raise ValueError("relative pattern")
            elif not 0<=track.get("note",-1)<=127:raise ValueError("absolute note mask")
            if not 1<=track["length_detents"]<=32:raise ValueError("length")
            phrases=[v["phrase"] for v in assigned] if merged else [track["phrase"]]+([track["final_bar"]] if "final_bar" in track else [])+track.get("bar_phrases",[])
            if "bar_phrases" in track and len(track["bar_phrases"])!=example["bars"]:raise ValueError("bar phrase count")
            for values in phrases:
                if not values or len({v[0] for v in values})!=len(values):raise ValueError("phrase uniqueness")
                if any(not 1<=step<=last or not 0<=note<=(6 if relative else 127) for step,note in values):raise ValueError("phrase bounds")
            limit=last if relative else 64
            overrides=track.get("velocity_overrides",[])
            if len({row[0] for row in overrides})!=len(overrides) or any(not 1<=step<=limit or not 1<=value<=127 for step,value in overrides):
                raise ValueError("step velocity overrides")
            if any(not 0<=v<=14 for v in track.get("chords",[])) or len(track.get("chords",[]))>4:raise ValueError("chord offsets")
        if len(set(patterns))!=len(patterns):raise ValueError("pattern numbers must be unique in an example")
        if relative and "phase_changes" in example:
            if example.get("scale_slots")!=[dict(slot=1,root="C",root_detents=0),dict(slot=2,root="D",root_detents=2)]:raise ValueError("C and D scale slots")
            if example.get("phase_changes")!=[dict(at_step=32,scale_slot=2,root="D")]:raise ValueError("scale comparison phases")
        if example.get("purpose")=="lesson-comparison" and not example.get("midi_contract"):raise ValueError("lesson MIDI contract")
    import jsonschema
    try:jsonschema.Draft7Validator(json.loads((MANUAL/"audio.schema.json").read_text())).validate(data)
    except jsonschema.ValidationError as error:raise ValueError("audio schema: "+error.message) from error
    return data

def assigned_patterns(track):
    """The relative-mode patterns that feed one channel, in assignment order."""
    return track["patterns"] if "patterns" in track else [dict(pattern=track["pattern"],phrase=track["phrase"])]

def expand(track,bars):
    if "patterns" in track:
        return [[bar*16+step,degree] for bar in range(bars) for assigned in track["patterns"] for step,degree in assigned["phrase"]]
    if "range_last" in track:
        period=track["range_last"]
        return [[k*period+step,note] for k in range(-(-bars*16//period)) for step,note in track["phrase"] if k*period+step<=bars*16]
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
        # C05 rows follow channel_edit_parameters.device_fields: Device, MIDI channel, MIDI port.
        c.enc(3,1);c.enc(2,1);c.enc(3,-64)
        if channel>1:c.enc(3,channel-1)
        c.ui.expect_selected_field("detail","MIDI channel","CC%d"%channel)
        c.enc(2,1);c.enc(3,-64)
        if port>1:c.enc(3,port-1)
        c.ui.expect_selected_field("detail","MIDI port","OUT %d"%port)
        c.ui.press_key(3)
    else:c.ui.pick_device(track["voice"])

def configure(c,example,tracks,midi_only=False,witnesses=False):
    if example.get("setup")=="course-stage":
        # The course builds its own project from an empty one; track masks would pre-empt its steps.
        return SETUPS["course-stage"](c,example,tracks,witnesses,midi_only)
    relative=example.get("mode")=="relative-scale-slots"
    if not relative:
        # Literal MIDI note masks in the authored audio examples are chromatic.
        # The public setting defaults On and snaps C#1 (37) to C1 (36).
        c.ui.set_mosaic_options([("Snap note masks to scale",False)])
    set_tempo(c)
    if relative:
        for track in tracks:
            for assigned in assigned_patterns(track):
                c.ui.channel_editor();c.ui.pattern_editor();c.ui.tap_control("pattern_select",assigned["pattern"])
                for step,degree in assigned["phrase"]:c.ui.tap_step(step)
                c.ui.pattern_editor(view="note",from_view="trigger")
                for step,degree in assigned["phrase"]:c.ui.tap_control("pattern_note_degree",(step,degree))
                c.ui.expect_header("note_editor",pattern=assigned["pattern"])
    targets=[(track,track["channel"],midi_only,track["channel"]) for track in tracks]
    if witnesses:targets += [(track,14+track["channel"],True,1) for track in tracks]
    for track,ch,midi,port in targets:
        route_track(c,track,ch,midi,port)
        if relative:
            for assigned in assigned_patterns(track):c.ui.tap_control("pattern_slot",assigned["pattern"])
            c.ui.set_range(1,16)
            c.ui.set_channel_octave(track.get("octave",0))
        else:c.ui.set_range(1,track.get("range_last",64))
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
            # One period of a polymetric channel: its range repeats the phrase by itself.
            for step,note in (track["phrase"] if "range_last" in track else expand(track,example["bars"])):
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
    if "setup" in example:SETUPS[example["setup"]](c,example,tracks,witnesses,midi_only)

def mapped_score(example,tracks,witness=False):
    channels={track["channel"] for track in tracks}
    wanted=[dict(row) for row in example["midi_contract"]["notes"] if row["status"]-143 in channels]
    if witness:
        for row in wanted:row.update(port=1,status=row["status"]+14)
    return wanted

def mapped_controls(example,tracks,witness=False):
    """Authored controller rows for the channels being played; a witness copy sits 14 MIDI channels up."""
    channels={track["channel"] for track in tracks}
    wanted=[dict(row) for row in example["midi_contract"].get("controls",[]) if row["status"]-175 in channels]
    if witness:
        for row in wanted:row.update(port=1,status=row["status"]+14)
    return wanted

def midi_messages(packets):
    """Split each captured packet into its channel messages; simultaneous events on
    one port can share a packet. Each message keeps the packet's port, index and time."""
    messages=[]
    for p in packets:
        data=p["bytes"];at=0
        while at<len(data):
            status=data[at];size=1 if status>=0xF8 else 2 if 0xC0<=status<=0xDF else 3
            if status<0x80 or 0xF0<=status<0xF8 or at+size>len(data) or any(v>=0x80 for v in data[at+1:at+size]):
                raise AssertionError(("Unsupported MIDI packet",p))
            messages.append(dict(p,bytes=data[at:at+size]));at+=size
    return messages

def verify_midi_packets(packets,expected,origin,clock_mode,allow_boundary=False,cycle_steps=64):
    from collections import Counter
    packets=midi_messages(packets)
    key="logical_ns" if clock_mode=="controlled-experimental" else "monotonic_ns"
    tolerance=2e-9 if clock_mode=="controlled-experimental" else .01
    ons=[p for p in packets if 144<=p["bytes"][0]<=159 and p["bytes"][2]>0]
    if allow_boundary:
        if len(ons)<len(expected)+1:raise AssertionError("Missing closing cycle onset")
        closing=ons[len(expected)]
        if abs((closing[key]-origin)/1e9-cycle_steps/6)>tolerance:raise AssertionError("Closing onset is not the declared %d-step boundary"%cycle_steps)
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


# --- Invariant lessons (README.md#harmony Revoice): Mosaic chooses the notes, the contract states rules. ---
# midi_contract.invariants keeps slot 1 literal and checks a later window against README-stated rules; the
# literal notes captured there are characterisation only. Kept in this tool so its identity is frozen with it.
INVARIANT_KINDS={"revoice"}

class InvariantViolation(AssertionError):
    def __init__(self,rule,detail):
        super().__init__("%s: %s"%(rule,detail))
        self.rule=rule;self.detail=detail

def pitch_classes(chord):return sorted(n%12 for n in chord)

def check_revoice(reference,revoiced):
    """README.md#harmony: Revoice preserves the pitch classes and sounding count of the root and
    chord-mask voices, and Bass Root puts the chord root lowest. `reference` and `revoiced` are the Harmony
    Off and Revoice chords in time order, each a list of MIDI pitches; the root of a reference chord is its
    lowest note. Smooth "prioritises literal common tones and economical movement": the README defines
    neither a voice identity nor a measure of movement, and Mosaic's own voicing gives up a common
    pitch for a root bass, so no rule is made of them."""
    if len(reference)!=len(revoiced):raise InvariantViolation("chord-count",(len(reference),len(revoiced)))
    for index,(before,after) in enumerate(zip(reference,revoiced)):
        if len(before)!=len(after):raise InvariantViolation("sounding-count",(index,before,after))
        if pitch_classes(before)!=pitch_classes(after):raise InvariantViolation("pitch-classes",(index,before,after))
        if min(after)%12!=min(before)%12:raise InvariantViolation("bass-root",(index,before,after))
    return dict(chords=len(revoiced))

def captured_notes(packets,origin,clock_mode,port,status,before_step=None):
    """Note rows (step, note, velocity, length) of one port and channel: each note on paired with its
    release. Every onset and release must lie on the 1/24-step grid."""
    key="logical_ns" if clock_mode=="controlled-experimental" else "monotonic_ns"
    tolerance=2e-9 if clock_mode=="controlled-experimental" else .01
    messages=[m for m in midi_messages(packets) if m["port"]==port and m["bytes"][0] in (status,status-16)]
    messages.sort(key=lambda m:m["index"])
    rows=[]
    for position,message in enumerate(messages):
        data=message["bytes"]
        if data[0]!=status or data[2]==0:continue
        if before_step is not None and (message[key]-origin)/1e9*6>=before_step-.01:continue
        release=next((m for m in messages[position+1:] if m["bytes"][0]==status-16 and m["bytes"][1]==data[1]),None)
        if release is None:raise AssertionError(("Note never released",message))
        step=Fraction(round((message[key]-origin)/1e9*6*24),24)
        length=Fraction(round((release[key]-message[key])/1e9*6*24),24)
        if abs((message[key]-origin)/1e9-float(step)/6)>tolerance:raise AssertionError(("Onset off the 1/24-step grid",message))
        if abs((release[key]-message[key])/1e9-float(length)/6)>tolerance:raise AssertionError(("Release off the 1/24-step grid",release))
        rows.append(dict(step=step,note=data[1],velocity=data[2],length=length))
    return rows

def chords_by_onset(rows):
    """Notes that start on one step are one chord: [(step, [pitches ascending])] in time order."""
    steps=sorted({v["step"] for v in rows})
    return [(step,sorted(v["note"] for v in rows if v["step"]==step)) for step in steps]

def verify_invariants(packets,contract,origin,clock_mode,port,status):
    """Slot 1 notes equal the contract's literal notes; every `revoice` window obeys check_revoice and
    sounds on the same onset steps as its reference window. The closing onset at cycle_steps is not part of the cycle."""
    cycle=contract["cycle_steps"];notes=captured_notes(packets,origin,clock_mode,port,status,before_step=cycle)
    results=[];claimed=set()
    for spec in contract["invariants"]:
        if spec["kind"]!="revoice":raise ValueError("invariant kind "+str(spec["kind"]))
        a=spec["reference_start_step"];b=a+spec["length_steps"];c=spec["revoiced_start_step"];d=c+spec["length_steps"]
        reference=[v for v in notes if a<=v["step"]<b];revoiced=[v for v in notes if c<=v["step"]<d]
        claimed.update((a,c))
        literal=[dict(port=port,status=status,note=v["note"],velocity=v["velocity"],step=float(v["step"]),length=float(v["length"])) for v in reference]
        wanted=[dict(v,port=port,status=status) for v in contract["notes"] if a<=v["step"]<b]
        if score_order(literal)!=score_order(wanted):raise AssertionError(("Literal slot 1 output",literal,wanted))
        before=chords_by_onset(reference);after=chords_by_onset(revoiced)
        if [s+(c-a) for s,_ in before]!=[s for s,_ in after]:raise AssertionError(("Revoice changed the onset steps",before,after))
        verdict=check_revoice([p for _,p in before],[p for _,p in after])
        results.append(dict(spec,**verdict,characterisation=dict(revoiced_chords=[dict(step=int(s) if s==int(s) else float(s),notes=p) for s,p in after])))
    covered=[v for v in notes if not any(spec["reference_start_step"]<=v["step"]<spec["reference_start_step"]+spec["length_steps"]
                                         or spec["revoiced_start_step"]<=v["step"]<spec["revoiced_start_step"]+spec["length_steps"]
                                         for spec in contract["invariants"])]
    if covered:raise AssertionError(("Notes outside every invariant window",covered))
    return dict(passed=True,invariants=results,
                characterisation=dict(revoiced_chords=[c for r in results for c in r["characterisation"]["revoiced_chords"]]))

def invariant_boundary(onsets,origin,key,cycle):
    """The first onset of the next cycle: where the lesson's cycle ends, as no onset count is authored."""
    closing=next((v for v in onsets if (v[key]-origin)/1e9>=cycle/6-.01),None)
    if closing is None:raise AssertionError("Missing closing cycle onset")
    return closing

def witness_origin(example,tracks,first_onset_ns):
    """Play-start origin of a witnessed take: the first heard onset less its authored step.
    A part may enter after step 0 (song-sections Polyperc enters on step 18)."""
    return first_onset_ns-min(v["step"] for v in mapped_score(example,tracks,witness=True))*1e9/6

def verify_witness_packets(example,tracks,packets,origin):
    """Audio-session MIDI witness: the contract's literal score, or its invariants, on the witness channel."""
    invariants=example["midi_contract"].get("invariants")
    if invariants:
        return verify_invariants(packets,example["midi_contract"],origin,"real-time",port=1,status=143+WITNESS_CHANNEL_OFFSET+invariants[0]["channel"])
    return verify_midi_packets(packets,mapped_score(example,tracks,witness=True),origin,"real-time")

def verify_midi_controls(packets,expected,origin,clock_mode,boundary_index=None):
    """Controller (CC) messages are exactly the authored rows, each at its step and ahead of the note on
    the same port and channel (characterisation, M-PARAM lock cases: a lock value precedes the attack).
    A CC lock proves lock timing on a controller, not the voice parameter it stands beside."""
    key="logical_ns" if clock_mode=="controlled-experimental" else "monotonic_ns"
    tolerance=2e-9 if clock_mode=="controlled-experimental" else .01
    messages=midi_messages(packets)
    if boundary_index is not None:messages=[m for m in messages if m["index"]<boundary_index]
    actual=[m for m in messages if 176<=m["bytes"][0]<=191]
    literal=sorted(expected,key=lambda v:(Fraction(v["step"]),v["port"],v["status"],v["controller"]))
    if sorted((v["port"],v["status"],v["controller"],v["value"]) for v in literal)!=sorted((m["port"],*m["bytes"]) for m in actual):
        raise AssertionError(("Literal controller output",[(m["port"],m["bytes"]) for m in actual],literal))
    ordered=sorted(actual,key=lambda m:m["index"])
    for message,row in zip(ordered,sorted(literal,key=lambda v:(Fraction(v["step"]),v["controller"],v["port"]))):
        if (message["port"],message["bytes"])!=(row["port"],[row["status"],row["controller"],row["value"]]):
            raise AssertionError(("Literal controller output",message,row))
        if abs((message[key]-origin)/1e9-row["step"]/6)>tolerance:raise AssertionError(("Controller onset",message,row))
        note=next((m for m in messages if m["port"]==row["port"] and m["bytes"][0]==row["status"]-32 and m["bytes"][2]>0
                   and abs(m[key]-message[key])<=tolerance*1e9),None)
        if note is None:raise AssertionError(("Controller has no note on its step",message))
        if note["index"]<message["index"]:raise AssertionError(("Controller must come before the note",message,note))
    return dict(controls=len(literal),timing_tolerance_seconds=tolerance,passed=True)

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
        cycle=contract_cycle_steps(example)
        deadline=time.monotonic()+max(30,cycle/6+5) if clock_mode=="real-time" else time.monotonic()+180
        invariants=example["midi_contract"].get("invariants")
        # Invariant lessons wait on the clock: Mosaic chooses their notes, so no count is authored.
        def finished(state):
            if not invariants:return len(notes(state))>=len(expected)+1
            now=(c.logical_ns if clock_mode!="real-time" else time.monotonic()*1e9)-origin
            return now/1e9>cycle/6+.2
        while not finished(state):
            if time.monotonic()>deadline:raise TimeoutError("Lesson MIDI comparison")
            now=(c.logical_ns-origin)/1e9 if clock_mode!="real-time" else (time.monotonic()*1e9-origin)/1e9
            if pending and now>=pending[0]["at_step"]/6-.3:changes.append(apply_phase(c,pending.pop(0),origin,key))
            c.elapse(.01 if clock_mode!="real-time" else .03);state=c.snapshot()
        packets=[p for p in state["midi"] if p["index"]>before]
        if invariants:
            verified=verify_invariants(packets,example["midi_contract"],origin,clock_mode,port=1,status=143+invariants[0]["channel"])
            boundary=invariant_boundary(notes(state),origin,key,cycle)["index"]
        else:
            verified=verify_midi_packets(packets,expected,origin,clock_mode,allow_boundary=True,cycle_steps=cycle)
            boundary=notes(state)[len(expected)]["index"]
        wanted_controls=mapped_controls(example,example["tracks"]);controls={}
        if wanted_controls:
            controls=dict(controls=verify_midi_controls(packets,wanted_controls,origin,clock_mode,boundary_index=boundary)["controls"],
                          controls_citation="README.md#trig-param-locks")
        c.ui.stop();c.wait(lambda s:not s["midi_capture"]["outstanding"])
        c.results.append(dict(kind="manual-audio-lesson-midi",case="MA-AUDIO-"+example["id"],clock_mode=clock_mode,
                              phases=changes,origin_ns=origin,midi_start_index=before,midi_end_index=state["midi_count"],
                              boundary_index=boundary,citation="README.md#typical-workflow",**controls,**verified))
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

def ghost_note_interiors(example,tracks,samples,rate,offset):
    checked=[]
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

def relative_scale_pitch_interiors(example,tracks,samples,rate,offset):
    from pcm_oracle import analyse
    checked=[]
    for note in mapped_score(example,tracks):
        start=offset+note["step"]/6+.30;end=offset+note["step"]/6+.42
        section=samples[round(start*rate):round(end*rate)]
        frames,half,hop=analyse(section,rate)
        if len(frames)<6 or any(v["note"]!=note["note"] for v in frames):
            raise ValueError(("Relative scale PCM pitch",note,frames))
        checked.append(dict(step=note["step"],expected_note=note["note"],start=start,end=end,frames=frames))
    return dict(kind="relative-scale-pitch-interiors",windows=checked,
                domain="dry monophonic Polyperc MIDI48..84",absolute_latency_verified=False,passed=True)

LESSON_PCM_PROOFS={"ghost-note-interiors":ghost_note_interiors,
                   "relative-scale-pitch-interiors":relative_scale_pitch_interiors}
# Reviewed lesson -> (PCM proof kind, solo voice the proof is limited to or None for every session).
LESSON_PCM_KINDS={"ghost-note-comparison":("ghost-note-interiors",None),
                  "scale-slot-comparison":("relative-scale-pitch-interiors","Polyperc 1")}

# --- Course clips: the before/after MIDI check (see manual_audio_setups.course_stage) ---
# The audio take routes the stage's channels to voices, so MIDI cannot witness it. The same session proves the
# stage's tiled course contract on MIDI BEFORE the take and again AFTER it; the take is accepted only when both
# pass and nothing but routing inputs came between them. Characterisation: tooling, not a README behaviour.
ROUTING_UI_CALLS=("channel_editor","select_channel","channel_page","pick_device","press_key","expect_selected_field")
def course_cells():
    from ui_map import control_cell
    return dict(play=control_cell("play_stop"),panic=control_cell("panic"),editor=control_cell("channel_editor"),channel=lambda n:control_cell("channel",n))
COURSE_PHASES=("route_to_voices","take","route_to_midi")
COURSE_CITATION="characterisation: course stage contract (tools/manual_course_cases.CONTRACTS, derived from README.md)"

class RoutingGuard:
    """Wraps the public UI while channels are rerouted: only routing calls pass, each is logged."""
    def __init__(self,ui,calls):self._ui=ui;self._calls=calls
    def __getattr__(self,name):
        if name not in ROUTING_UI_CALLS:raise AssertionError("Non-routing public input while rerouting: "+name)
        self._calls.append(name)
        return getattr(self._ui,name)

def course_expected(example):
    """The whole stage's contract (every channel it sounds on), whichever tracks a session routes to voices."""
    return mapped_score(example,example["tracks"])

def course_midi_proof(c,example,clock_mode):
    """Play the stage from stopped on MIDI and verify the exact tiled contract and its closing cycle boundary."""
    expected=course_expected(example);cycle=contract_cycle_steps(example)
    key="logical_ns" if clock_mode!="real-time" else "monotonic_ns"
    action_start=len(c.recipe);start=c.snapshot()["midi_count"];c.ui.play()
    def notes(state):return [v for v in state["midi"] if v["index"]>start and 144<=v["bytes"][0]<=159 and v["bytes"][2]>0]
    state=c.wait(lambda s:bool(notes(s)),timeout=3)
    origin=notes(state)[0][key]
    deadline=time.monotonic()+(max(30,cycle/6+5) if clock_mode=="real-time" else 180)
    while len(notes(state))<len(expected)+1:
        if time.monotonic()>deadline:raise TimeoutError("Course MIDI proof")
        c.elapse(.01 if clock_mode!="real-time" else .03);state=c.snapshot()
    packets=[p for p in state["midi"] if p["index"]>start]
    verified=verify_midi_packets(packets,expected,origin,clock_mode,allow_boundary=True,cycle_steps=cycle)
    boundary=notes(state)[len(expected)]["index"]
    c.ui.stop();c.wait(lambda s:not s["midi_capture"]["outstanding"])
    return dict(origin_ns=origin,midi_start_index=start,midi_end_index=state["midi_count"],boundary_index=boundary,
                action_start=action_start,action_end=len(c.recipe),**verified)

def course_routing(c,tracks,label,midi,expected,port=None):
    """Reroute each track's channel (to its voice, or back to its MIDI port) using routing inputs only."""
    ports={v["status"]-143:v["port"] for v in expected}
    calls=[];real=c.ui;action_start=len(c.recipe);c.ui=RoutingGuard(real,calls)
    try:
        for track in tracks:route_track(c,track,track["channel"],midi=midi,port=port or ports.get(track["channel"],1))
    finally:c.ui=real
    return dict(phase=label,channels=[t["channel"] for t in tracks],calls=sorted(set(calls)),action_start=action_start,action_end=len(c.recipe))

def course_before_after(c,example,tracks,clock_mode,take,stand_in_port=None):
    """BEFORE proof, route to the declared voices, `take()`, route back to MIDI, AFTER proof; returns the results row.

    `stand_in_port` is for the controlled-time rehearsal only (DSP voices need real time): the channels are routed
    to that MIDI port instead of their voices, and the row says so, so it can never pass as a recorded take."""
    expected=course_expected(example)
    before=course_midi_proof(c,example,clock_mode)
    to_voices=course_routing(c,tracks,"route_to_voices",stand_in_port is not None,expected,port=stand_in_port)
    start=len(c.recipe);take();taken=dict(action_start=start,action_end=len(c.recipe))
    to_midi=course_routing(c,tracks,"route_to_midi",True,expected)
    after=course_midi_proof(c,example,clock_mode)
    return course_row(clock_mode,before,to_voices,taken,to_midi,after,stand_in_port)

def course_row(clock_mode,before,to_voices,taken,to_midi,after,stand_in_port=None):
    for part in (to_voices,to_midi):part.pop("phase",None)
    row=dict(kind="manual-audio-course-before-after",citation=COURSE_CITATION,clock_mode=clock_mode,
             before=before,route_to_voices=to_voices,take=taken,route_to_midi=to_midi,after=after,passed=True)
    if stand_in_port is not None:row["stand_in_port"]=stand_in_port
    return row

def check_course_before_after(example,row,recipe,packets_for,allow_stand_in=False):
    """Independent check of a before/after row against the session's recipe and native MIDI packets."""
    if row.get("kind")!="manual-audio-course-before-after" or row.get("passed") is not True:raise ValueError("Missing course before/after MIDI check")
    parts=("before","route_to_voices","take","route_to_midi","after")
    if any(not isinstance(row.get(k),dict) for k in parts):raise ValueError("Incomplete course before/after MIDI check: "+", ".join(k for k in parts if not isinstance(row.get(k),dict)))
    if "stand_in_port" in row and not allow_stand_in:raise ValueError("Course before/after row is a MIDI-port rehearsal, not a voice take")
    if "stand_in_port" not in row and "pick_device" not in row["route_to_voices"].get("calls",[]):raise ValueError("Course before/after row never routed the channels to voices")
    clock=row.get("clock_mode");key="logical_ns" if clock=="controlled-experimental" else "monotonic_ns"
    if clock not in ("controlled-experimental","real-time"):raise ValueError("Course before/after clock mode")
    expected=course_expected(example);cycle=contract_cycle_steps(example)
    for name in ("before","after"):
        proof=row[name];packets=packets_for(proof["midi_start_index"],proof["midi_end_index"],clock)
        onsets=[p for p in midi_messages(packets) if 144<=p["bytes"][0]<=159 and p["bytes"][2]>0]
        if not onsets or onsets[0][key]!=proof["origin_ns"]:raise ValueError("Changed course "+name+" first onset")
        verified=verify_midi_packets(packets,expected,proof["origin_ns"],clock,allow_boundary=True,cycle_steps=cycle)
        if len(onsets)<len(expected)+1 or onsets[len(expected)]["index"]!=proof["boundary_index"]:raise ValueError("Changed course "+name+" closing boundary")
        if any(proof.get(k)!=v for k,v in verified.items()):raise ValueError("Changed course "+name+" MIDI proof")
    if row["before"]["midi_end_index"]>row["after"]["midi_start_index"]:raise ValueError("Course before/after MIDI windows overlap")
    chain=[row["before"]["action_end"],*[v for part in COURSE_PHASES for v in (row[part]["action_start"],row[part]["action_end"])],row["after"]["action_start"]]
    if chain[0]!=chain[1] or chain[2]!=chain[3] or chain[4]!=chain[5] or chain[6]!=chain[7]:raise ValueError("Course before/after actions are not contiguous")
    if chain!=sorted(chain):raise ValueError("Course before/after actions are not contiguous")
    wanted=sorted(t["channel"] for t in example["tracks"])
    for part in ("route_to_voices","route_to_midi"):
        if not row[part].get("calls") or any(v not in ROUTING_UI_CALLS for v in row[part]["calls"]):raise ValueError("Non-routing call in "+part)
        if sorted(row[part].get("channels",[]))!=sorted(row["route_to_voices"]["channels"]) or not set(row[part]["channels"])<=set(wanted):raise ValueError("Course before/after routed channels differ")
    def cell(action):return (action.get("x"),action.get("y"))
    def inputs(first,last,allowed,label):
        for action in recipe[first:last]:
            if action["type"]=="advance":continue
            if allowed(action):continue
            raise ValueError("Non-routing input between course MIDI proofs ("+label+"): "+str(action))
    cells=course_cells();routing_cells={cells["editor"],*[cells["channel"](n) for n in row["route_to_voices"]["channels"]]}
    for part in ("route_to_voices","route_to_midi"):
        inputs(row[part]["action_start"],row[part]["action_end"],lambda a:a["type"] in ("key","enc") or (a["type"]=="grid" and cell(a) in routing_cells),part)
    inputs(row["take"]["action_start"],row["take"]["action_end"],lambda a:a["type"]=="grid" and cell(a) in (cells["play"],cells["panic"]),"take")
    for name in ("before","after"):
        inputs(row[name]["action_start"],row[name]["action_end"],lambda a:a["type"]=="grid" and cell(a)==cells["play"],name)
    return True

def audit_course_before_after(example,record,allow_stand_in=False):
    """Bind a record's before/after row to its own session: results row, recipe and native MIDI."""
    out=Path(record["evidence"]["path"]);row=record.get("course_before_after")
    if not isinstance(row,dict):raise ValueError("Missing course before/after MIDI check")
    results=json.loads((out/"results.json").read_text())
    if not any(v==row for v in results):raise ValueError("Course before/after MIDI check is not bound to its session")
    recipe=json.loads((out/"recipe.json").read_text())
    return check_course_before_after(example,row,recipe,lambda start,end,clock:native_midi_packets(out,start,end,clock),allow_stand_in=allow_stand_in)

def lesson_pcm_kind(example,tracks):
    kind,voice=LESSON_PCM_KINDS.get(example["id"],(None,None))
    if voice is not None and not (len(tracks)==1 and tracks[0]["voice"]==voice):return None
    return kind

def lesson_pcm(example,tracks,wav,witness):
    """Fixed interiors measured from public MIDI receipts and native PCM epoch."""
    rate,channels=read_wav(wav)
    samples=[sum(v)/len(v) for v in zip(*channels)]
    offset=witness["origin_ns"]/1e9-witness["capture_epoch"]
    kind=lesson_pcm_kind(example,tracks)
    return LESSON_PCM_PROOFS[kind](example,tracks,samples,rate,offset) if kind else None

def lesson_pcm_receipt(pcm):
    # The proof's own kind (e.g. ghost-note-interiors) is kept as pcm_kind.
    return dict(pcm,kind="manual-audio-lesson-PCM",pcm_kind=pcm["kind"],citation="characterisation: declared PCM interiors")

def capture(example,tracks,out,options,case):
    c=tracked_driver(out,profile=example["profile"],mod_code_root=options.mod_code_root,
                     app_root=options.app_root,experimental_install=options.audio_install)
    job=None;timeline=[];lesson=example.get("purpose")=="lesson-comparison"
    course=example.get("setup")=="course-stage"
    witnessed=lesson and not course  # a course stage is proved on MIDI before and after its voice take instead
    try:
        configure(c,example,tracks,witnesses=witnessed,midi_only=course)
        if course:
            before_proof=course_midi_proof(c,example,"real-time")
            to_voices=course_routing(c,tracks,"route_to_voices",False,course_expected(example))
        take_start=len(c.recipe)
        c.elapse(13)
        seconds=example["bars"]*4*60/example["bpm"]
        before=c.snapshot()["midi_count"]
        job=c.runtime.capture_start(seconds+3)
        epoch=job["started"]["start_monotonic"]
        c.ui.play();origin=time.monotonic()*1e9;changes=[]
        def packets(state):return [p for p in state["midi"] if p["index"]>before]
        if witnessed:
            state=c.wait(lambda s:any(144<=p["bytes"][0]<=159 and p["bytes"][2]>0 for p in packets(s)),timeout=3)
            origin=witness_origin(example,tracks,next(p["monotonic_ns"] for p in packets(state) if 144<=p["bytes"][0]<=159 and p["bytes"][2]>0))
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
        if course:
            taken=dict(action_start=take_start,action_end=len(c.recipe))
            to_midi=course_routing(c,tracks,"route_to_midi",True,course_expected(example))
            after_proof=course_midi_proof(c,example,"real-time")
            row=course_row("real-time",before_proof,to_voices,taken,to_midi,after_proof)
            c.results.append(row);result.update(course_before_after=row)
        if witnessed:
            verified=verify_witness_packets(example,tracks,packets(musical_state),origin)
            witness=dict(verified,origin_ns=origin,capture_epoch=epoch,midi_start_index=before,midi_end_index=musical_state["midi_count"])
            wanted_controls=mapped_controls(example,tracks,witness=True)
            if wanted_controls:witness["controls"]=verify_midi_controls(packets(musical_state),wanted_controls,origin,"real-time")["controls"]
            c.results.append(dict(kind="manual-audio-MIDI-witness",citation="README.md#masks",**witness))
            result.update(midi_witness=witness,phase_observations=changes)
            pcm=lesson_pcm(example,tracks,wav,witness)
            if pcm:
                result["lesson_pcm"]=pcm
                c.results.append(lesson_pcm_receipt(pcm))
        return result
    finally:
        if job:
            try:
                if c.runtime.capture_status(job["job_id"])["status"]=="capturing":c.runtime.capture_cancel(job["job_id"])
            except Exception:pass
        try:close(c,{})
        finally:
            if not getattr(c,"finished",False):c.finish()

def course_dry_take(c,example):
    """An unrecorded stand-in for the audio take: the same public Play, a stage's length of time, Stop and panic."""
    c.ui.play();c.elapse(contract_cycle_steps(example)/6);c.ui.stop();c.tap(*course_cells()["panic"])

def course_dry_run(example,out,options,clock_mode="controlled-experimental"):
    """The before/after check in a controlled-time MIDI session, ending in the same audit the publication runs."""
    installation=options.midi_controlled_install
    if not installation:raise ValueError("Course dry run requires --midi-controlled-install")
    Path(out).mkdir()
    c=tracked_driver(out,clock_mode=clock_mode,experimental_install=installation,app_root=options.app_root)
    try:
        configure(c,example,example["tracks"],midi_only=True)
        row=course_before_after(c,example,example["tracks"],clock_mode,lambda:course_dry_take(c,example),stand_in_port=2)
        c.results.append(row)
    finally:close(c,{})
    audit_course_before_after(example,dict(evidence=dict(path=str(out)),course_before_after=row),allow_stand_in=True)
    return row

def course_dry_run_main(options,data,source_text):
    if not options.example:raise SystemExit("--course-dry-run needs at least one --example")
    chosen=[v for v in data["examples"] if v["id"] in options.example]
    if sorted(v["id"] for v in chosen)!=sorted(options.example) or any(v.get("setup")!="course-stage" for v in chosen):raise SystemExit("--course-dry-run examples must be course-stage ids")
    if not options.midi_emulator:raise SystemExit("--course-dry-run needs --midi-emulator and --midi-controlled-install")
    if os.environ.get("MONOME_EMULATOR")!=str(options.midi_emulator):  # the driver reads it at import time
        os.execve(sys.executable,[sys.executable,*sys.argv],dict(os.environ,MONOME_EMULATOR=str(options.midi_emulator)))
    run=ROOT.parent/"mosaic-manual-audio-runs"/("course-dry-"+uuid.uuid4().hex);run.mkdir(parents=True)
    app=run/"application";app.mkdir()
    shutil.copyfile(ROOT/"mosaic.lua",app/"mosaic.lua")
    shutil.copytree(ROOT/"lib",app/"lib",ignore=shutil.ignore_patterns("tests",".git","__pycache__"))
    shutil.copytree(ROOT/"docs/ui-reimplementation/code",app/"docs/ui-reimplementation/code")
    options.app_root=app
    with open("/tmp/mosaic-manual-native.lock","a") as lock:
        print("Waiting for exclusive native runtime",flush=True)
        fcntl.flock(lock,fcntl.LOCK_EX)
        for example in chosen:
            row=course_dry_run(example,run/(example["id"]+"-course-dry"),options)
            print("Course before/after MIDI check passed",example["id"],"onsets",row["before"]["onsets"],row["after"]["onsets"],flush=True)
    return 0

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
    parser.add_argument("--resume-from",type=Path,help="Continue a failed run: reuse every completed example of a failed --controlled-local run with an identical recording identity (re-audited, fail closed on any difference) and record only the missing ones. The fixed historical partial run keeps its own pinned qualification.")
    parser.add_argument("--validate-only",action="store_true")
    parser.add_argument("--course-dry-run",action="store_true",
                        help="Controlled-time rehearsal of the course before/after MIDI check for the selected --example ids: "
                             "replay, BEFORE proof, voice routing, an unrecorded take, routing back, AFTER proof, then the independent audit. No audio is recorded.")
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
    if options.course_dry_run:return course_dry_run_main(options,data,source_text)
    if options.controlled_local and options.example:
        parser.error("--controlled-local requires the complete authored audio inventory; do not select a subset")
    if options.resume_from and (not options.controlled_local or options.example):
        parser.error("--resume-from requires the complete --controlled-local inventory; subsets are not resumable")
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
    setups_sha256=freeze_setups(run)
    shutil.copyfile(MANUAL/"audio.schema.json",run/"audio.schema.json")
    harness_sources={}
    for name in ("driver.py","ui.py","ui_map.py","pcm_oracle.py","channel_gestures.py"):
        source=ROOT/"tests/behaviour"/name
        if source.is_file():
            shutil.copyfile(source,run/name);harness_sources[name]=digest(source)
    app=run/"application";app.mkdir()
    shutil.copyfile(ROOT/"mosaic.lua",app/"mosaic.lua")
    shutil.copytree(ROOT/"lib",app/"lib",ignore=shutil.ignore_patterns("tests",".git","__pycache__"))
    shutil.copytree(ROOT/"docs/ui-reimplementation/code",app/"docs/ui-reimplementation/code")
    options.app_root=app
    report=dict(schema_version=1,source_sha256=digest(options.source),tool_sha256=digest(Path(__file__)),
                helper_sha256=digest(ROOT/"tools/manual_capture.py"),setups_sha256=setups_sha256,schema_sha256=digest(MANUAL/"audio.schema.json"),
                revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                harness_sha256=harness_sources,voice_pins=pins,
                clock_mode="controlled-experimental" if options.controlled_local else "real-time",
                complete_regression_run=False,passed=False,
                controlled_lane="inapplicable: native DSP audio depends on real host time",examples=[])
    if options.controlled_local:
        report.update(validation_scope="controlled-manual-generation",realtime_qualification="pending-ci",
                      audio_capture_clock_mode="real-time")
    resume_stage=None
    if options.resume_from:
        import manual_audio_resume
        old_run=options.resume_from.resolve(strict=True)
        old_report=json.loads((old_run/"report.json").read_text())
        if old_run.name==manual_audio_resume.PIN["run"]:
            parity_receipt=Path("/home/andy/mosaic-manual-build-operators/luna-audio-batch-preflight-20261005-01/recording-f36a766fd2-fc66abb9a71c4de2bef51de71bdc5d75/runtime-identity-reuse-check.json")
            reused,resume_provenance,resume_stage=manual_audio_resume.prepare_continuation(
                sys.modules[__name__],ROOT,old_run,old_report,run,options.ffmpeg,parity_receipt,Path(__file__))
        else:
            try:
                reused,resume_provenance,resume_stage=manual_audio_resume.prepare_same_lineage(
                    sys.modules[__name__],ROOT,old_run,old_report,run,report,data,options.ffmpeg,
                    audio_install=options.audio_install,midi_install=options.midi_controlled_install,
                    audio_emulator=os.environ.get("MONOME_EMULATOR"),midi_emulator=options.midi_emulator)
            except manual_audio_resume.Rejected as error:
                shutil.rmtree(run)
                print("resume rejected: "+str(error),file=sys.stderr,flush=True)
                return 2
        report["examples"].extend(reused)
        report["resume_provenance"]=resume_provenance
    try:
        with open("/tmp/mosaic-manual-native.lock","a") as lock,tempfile.TemporaryDirectory(prefix="mosaic-manual-audio-") as scratch:
            print("Waiting for exclusive native runtime",flush=True)
            fcntl.flock(lock,fcntl.LOCK_EX)
            destination=Path(scratch)
            resumed_ids={v["id"] for v in report["examples"]}
            if resume_stage:
                for asset in (resume_stage/"audio").iterdir():
                    shutil.copyfile(asset,destination/asset.name)
            for example in data["examples"]:
                if options.example and example["id"] not in options.example:continue
                ident=example["id"]
                if ident in resumed_ids:
                    print("Reused independently audited original captures",ident,flush=True)
                    continue
                solos=[];musical=[]
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
                        **{key:result[key] for key in ("midi_witness","lesson_pcm","phase_observations","course_before_after") if key in result}))
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

def native_midi_packets(out,start,end,clock_mode="real-time"):
    # Native MIDI emissions: kind 11 (logical time) in the controlled runtime, kind 3 in real time.
    kind=11 if clock_mode=="controlled-experimental" else 3
    return [row for row in (json.loads(v) for v in (out/"native/native-events.jsonl").read_text().splitlines())
            if row.get("kind")==kind and start<row["index"]<=end]

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
    if example.get("setup")=="course-stage":
        if "midi_witness" in record or "lesson_pcm" in record or record.get("phase_observations"):raise ValueError("Course audio carries before/after MIDI proofs, not witness evidence")
        return audit_course_before_after(example,record)
    results=json.loads((out/"results.json").read_text())
    observations=json.loads((out/"observations.json").read_text())
    witness=record["midi_witness"]
    if not any(v.get("kind")=="manual-audio-MIDI-witness" and all(v.get(k)==value for k,value in witness.items()) for v in results):raise ValueError("Native MIDI witness binding")
    state=max((row["state"] for row in observations),key=lambda v:v["midi_count"])
    packets=native_midi_packets(out,witness["midi_start_index"],witness["midi_end_index"])
    first=next(p for p in packets if 144<=p["bytes"][0]<=159 and p["bytes"][2]>0)
    if witness_origin(example,tracks,first["monotonic_ns"])!=witness["origin_ns"]:raise ValueError("Changed first witness onset")
    verified=verify_witness_packets(example,tracks,packets,witness["origin_ns"])
    if any(witness.get(k)!=v for k,v in verified.items()):raise ValueError("Changed MIDI witness")
    wanted_controls=mapped_controls(example,tracks,witness=True)
    if wanted_controls or "controls" in witness:
        if witness.get("controls")!=verify_midi_controls(packets,wanted_controls,witness["origin_ns"],"real-time")["controls"]:raise ValueError("Changed MIDI witness controllers")
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
        packets=native_midi_packets(out,proof_row["midi_start_index"],proof_row["midi_end_index"],lane["clock_mode"])
        expected=mapped_score(example,example["tracks"])
        first=next(p for p in packets if 144<=p["bytes"][0]<=159 and p["bytes"][2]>0)
        key="logical_ns" if lane["clock_mode"]!="real-time" else "monotonic_ns"
        if first[key]!=proof_row["origin_ns"]:raise ValueError("Changed first lesson onset")
        onsets=[p for p in packets if 144<=p["bytes"][0]<=159 and p["bytes"][2]>0]
        invariants=example["midi_contract"].get("invariants")
        closing=invariant_boundary(onsets,first[key],key,contract_cycle_steps(example)) if invariants else onsets[len(expected)]
        if closing["index"]!=proof_row["boundary_index"]:raise ValueError("Changed lesson closing boundary")
        proof=(verify_invariants(packets,example["midi_contract"],first[key],lane["clock_mode"],port=1,status=143+invariants[0]["channel"]) if invariants
               else verify_midi_packets(packets,expected,first[key],lane["clock_mode"],allow_boundary=True,cycle_steps=contract_cycle_steps(example)))
        audit_phases(example,out,proof_row["phases"],first[key],lane["clock_mode"])
        if any(acceptance[0].get(k)!=v for k,v in proof.items()):raise ValueError("Changed literal MIDI score")
        wanted_controls=mapped_controls(example,example["tracks"])
        if wanted_controls or "controls" in acceptance[0]:
            proven=verify_midi_controls(packets,wanted_controls,first[key],lane["clock_mode"],boundary_index=closing["index"])
            if acceptance[0].get("controls")!=proven["controls"]:raise ValueError("Changed literal controller proof")
        cleanup=json.loads((out/"native/cleanup.json").read_text())
        if not cleanup or any(v.get("returncode") is None for v in cleanup):raise ValueError("MIDI lesson cleanup")
    return True

def audit_setups_identity(report,native_run):
    """The reviewed setup driver the run executed must be the current file, the run's frozen copy and the report's hash."""
    frozen=Path(native_run)/"capture-setups.py";recorded=report.get("setups_sha256")
    if not recorded or not frozen.is_file() or digest(frozen)!=recorded or digest(ROOT/"tools/manual_audio_setups.py")!=recorded:
        raise ValueError("Audio setups identity")
    return True

def freeze_setups(run):
    """Copy the setup driver into the run and return its hash for the report."""
    source=ROOT/"tools/manual_audio_setups.py"
    shutil.copyfile(source,Path(run)/"capture-setups.py")
    return digest(source)

def audit_example_native(example,expected_example,controlled_local=False):
    """The native-evidence audit of one example (MIDI lanes, solos, PCM, timeline); returns its audited frame count."""
    checked=0
    if example.get("purpose")=="lesson-comparison":
        audit_lesson_midi(example,example["musical_evidence"],controlled_local=controlled_local)
        audit_lesson_capture(example,example["tracks"],example)
        for solo in example["solo_contributions"]:
            audit_lesson_capture(example,[next(t for t in example["tracks"] if t["channel"]==solo["channel"])],solo)
    for key,value in expected_example.items():
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
    return checked

# Editorial-only authoring fields: they describe which features an example belongs to and cannot change a recording.
EDITORIAL_FIELDS=("feature_ids",)

def editorial_view(row):
    """A row without its editorial-only fields (for recording-identity comparisons)."""
    return {k:v for k,v in row.items() if k not in EDITORIAL_FIELDS}

def native_source_sha256(report):
    """The source identity the recording was made from: a refreshed publication keeps the native one."""
    return report.get("publication",{}).get("native_source_sha256",report["source_sha256"])

def verify_editorial_publication(report,native_run,authored):
    """A refreshed publication may differ from its native recording's authoring only in EDITORIAL_FIELDS."""
    publication=report["publication"]
    if publication.get("kind")!="editorial-refresh" or publication.get("editorial_fields")!=list(EDITORIAL_FIELDS):raise ValueError("unknown audio publication kind")
    baseline_path=native_run/"audio-scenes.json"
    if digest(baseline_path)!=publication.get("native_report_sha256"):raise ValueError("native audio baseline changed")
    native=validate(yaml.safe_load((native_run/"source.yaml").read_text()))
    if {k:v for k,v in native.items() if k!="examples"}!={k:v for k,v in authored.items() if k!="examples"}:raise ValueError("editorial publication changed non-example authoring")
    if [v["id"] for v in native["examples"]]!=[v["id"] for v in authored["examples"]]:raise ValueError("editorial publication changed the example inventory")
    for old,new in zip(native["examples"],authored["examples"]):
        if editorial_view(old)!=editorial_view(new):raise ValueError("editorial publication changed a recorded field of "+old["id"])

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
    native_source=native_source_sha256(report)
    if "publication" in report:verify_editorial_publication(report,Path(report["examples"][0]["evidence"]["path"]).parent,authored)
    if digest(native_run/"source.yaml")!=native_source:raise ValueError("native source identity")
    if digest(native_run/"capture-tool.py")!=report["tool_sha256"]:raise ValueError("native tool identity")
    if report.get("schema_sha256") and (digest(native_run/"audio.schema.json")!=report["schema_sha256"] or digest(MANUAL/"audio.schema.json")!=report["schema_sha256"]):raise ValueError("Audio schema identity")
    for name,value in report.get("harness_sha256",{}).items():
        if digest(native_run/name)!=value or digest(ROOT/"tests/behaviour"/name)!=value:raise ValueError("Audio harness identity "+name)
    audit_setups_identity(report,native_run)
    import manual_audio_resume
    has_resume_marker=manual_audio_resume.require_resume_provenance(report,native_run)
    if has_resume_marker:
        manual_audio_resume.audit_resume_provenance(sys.modules[__name__],report,native_run,ROOT)
    if "publication" in report:
        baseline=json.loads((native_run/"audio-scenes.json").read_text())
        if not baseline["passed"] or baseline["source_sha256"]!=native_source:raise ValueError("native publication baseline")
        originals={v["id"]:v for v in baseline["examples"]}
        for example in report["examples"]:
            for key in ("timeline","metrics","evidence","solo_contributions","tracks","bars","bpm","profile","musical_evidence","midi_witness","phase_observations","lesson_pcm","course_before_after"):
                if example.get(key)!=originals[example["id"]].get(key):raise ValueError("publication changed native evidence")
    for example in report["examples"]:
        checked+=audit_example_native(example,expected[example["id"]],controlled_local)
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
