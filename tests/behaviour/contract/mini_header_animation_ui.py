"""Exact v2 mini poses; v1 resting-icon baseline remains separate."""
import base64,json,hashlib,math
from pathlib import Path
from contract.mini_header_ui import literal_pixels,band
ATLAS_SHA256="4b1623dd87cabd4a98b3ed5d2e47b32455221c360054f1eb5dd8783eb5278c46"
def atlas():
    raw=Path(__file__).with_name("mini_header_atlas_v2.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ATLAS_SHA256,"Frozen v2 animation contract changed"
    a=json.loads(raw);assert a["palette"]=={".":0,"a":7,"b":11,"c":15}
    assert a["v1_atlas_sha256"]=="ed4d8972b1012b7570d402b6ba997c6c78c6c0926e577f974e03758782ed3c54"
    return {x["id"]:x for x in a["screens"]}
def left_edge(spec):return 121 if spec["layout"] in ("overview_masks","overview_params","dashboard") else 96
def poses(state,page):
    spec=atlas()[page];actual=base64.b64decode(state["frame"]["pixels_base64"]);left=left_edge(spec)
    assert spec["origin"][0]>=left
    return [i for i,f in enumerate(spec["frames"]) if band(actual,left)==band(literal_pixels(spec,f),left)]
def require_icon(state,page,enabled):
    found=poses(state,page)
    assert found and (enabled or 0 in found),dict(page=page,enabled=enabled,expected="exact v2 authored mini pose",actual_matching_poses=found)
    return found
def expected_pose(beat,page,enabled=True):
    spec=atlas()[page]
    if not enabled or not isinstance(beat,(int,float)) or isinstance(beat,bool) or not math.isfinite(beat) or beat<0:return 0
    return math.floor((beat%spec["loop_quarter_beats"])*len(spec["frames"])/spec["loop_quarter_beats"])
def overlay(expected,spec,frame):
    data=bytearray(expected);sprite=literal_pixels(spec,frame);x,y=spec["origin"]
    for yy in range(y,y+8):
        first=(yy*128+x)*4;last=(yy*128+128)*4;data[first:last]=sprite[first:last]
    return bytes(data)
def exact_header_matches(state,title,scope,layout,expected,rows):
    from frame_oracle import _region_matches,text_width,fit
    actual=base64.b64decode(state["frame"]["pixels_base64"])
    scenes=[s for s in atlas().values() if s["title"]==title and s["layout"]==layout];variants=[]
    for s in scenes:
        room=78 if layout in ("overview_masks","overview_params","dashboard") else (118 if layout=="vertical_list" else 126)
        if 1+text_width(fit(title,room))+2<=s["origin"][0]:variants.extend(overlay(expected,s,f) for f in s["frames"])
        else:variants.append(expected)
    if not scenes:variants=[expected]
    for target in variants:
        if layout=="vertical_list":
            if _region_matches(actual,target,0,8,0,128) and _region_matches(actual,target,8,19,0,min(118,3+int(text_width(scope)))):return True
        elif _region_matches(actual,target,0,rows,0,128):return True
    return False
def outside_icon(data,spec):
    left=left_edge(spec)
    return bytes(data[(y*128+x)*4+k] for y in range(64) for x in range(128) for k in range(3) if not(y<8 and x>=left))
def native_events(c):
    # Read only the same native evidence exported by the installed public
    # Session.close client. No application state or credentials are consulted.
    from driver import EMULATOR_ROOT
    raw=(EMULATOR_ROOT/".runtime/sessions"/c.runtime.id/"native-events.jsonl").read_text()
    lines=raw.splitlines()
    if raw and not raw.endswith("\n"):lines=lines[:-1]
    return [json.loads(line) for line in lines]

def wait_normal_footer(c,page):
    """Do not confuse a public navigation toast expiry with animation movement."""
    from contract.live_ui_sweep import footer_render,hints
    from frame_oracle import _region_matches
    expected=footer_render(hints(page))
    c.wait(lambda state:_region_matches(base64.b64decode(state["frame"]["pixels_base64"]),expected,57,64),timeout=5)


def sample(c,page,enabled,seconds,require_all=False,tempo=None):
    wait_normal_footer(c,page)
    spec=atlas()[page];samples=[];seen=set();fixed=None;grid=None;count=None
    for _ in range(math.ceil(seconds/.125)):
        before=c.snapshot();before_index=len(c.observations)-1
        before_clock=before.get("diagnostics",{})
        c.elapse(.125);s=c.snapshot();found=require_icon(s,page,enabled)
        data=base64.b64decode(s["frame"]["pixels_base64"]);body=outside_icon(data,spec)
        if fixed is None:fixed=body;grid=s["grid"];count=s["midi_count"]
        assert body==fixed,"Title, scope, selection, labels, values or footer changed during header animation"
        assert s["grid"]==grid and s["midi_count"]==count,"Stopped mini animation changed grid or MIDI"
        seen.update(found)
        image_index=len(c.observations)-1;envelope=c.observations[image_index];diagnostics=s.get("diagnostics",{})
        after=s
        if enabled:
            events=native_events(c)
            frame_events=[e for e in events if e.get("kind")==1 and e.get("revision")==envelope["frame_revision"] and e.get("sha256")==s["frame"]["sha256"]]
            assert frame_events,"Selected native frame has no retained revision/SHA event"
            draw_ns=frame_events[-1]["monotonic_ns"]
            if diagnostics.get("monotonic_ns",-1)<draw_ns:
                # Acquire a newer public clock receipt for this already chosen
                # image; never extrapolate beats from host elapsed time.
                after=c.wait(lambda state:state.get("diagnostics",{}).get("monotonic_ns",-1)>=draw_ns,timeout=1)
        after_clock=after.get("diagnostics",{})
        samples.append(dict(observation_index=image_index,frame_sha256=s["frame"]["sha256"],matching_poses=found,
                            frame_revision=envelope.get("frame_revision"),monotonic_ns=envelope.get("monotonic_ns"),
                            clock_before_observation_index=before_index,clock_after_observation_index=len(c.observations)-1,
                            clock_before=dict(beats=before_clock.get("beats"),tempo=before_clock.get("tempo"),monotonic_ns=before_clock.get("monotonic_ns"),clock_epoch=before_clock.get("clock_epoch")),
                            clock_after=dict(beats=after_clock.get("beats"),tempo=after_clock.get("tempo"),monotonic_ns=after_clock.get("monotonic_ns"),clock_epoch=after_clock.get("clock_epoch")),
                            native_clock=dict(beats=diagnostics.get("beats"),tempo=diagnostics.get("tempo"),monotonic_ns=diagnostics.get("monotonic_ns"),clock_epoch=diagnostics.get("clock_epoch"))))
        from mini_phase_oracle import check_stopped_phase
        samples[-1]["phase_check"]=check_stopped_phase(samples[-1],c.observations,native_events(c),spec,enabled,tempo,c.clock_mode)
    unique={tuple(f) for f in spec["frames"]};observed={tuple(spec["frames"][i]) for i in seen}
    if enabled:
        assert len(observed)>1,"Motion On did not animate literal motif"
        if require_all:assert observed==unique,"Slow-clock loop must expose every distinct authored v2 pose"
    else:assert observed=={tuple(spec["frames"][0])},"Motion Off changed resting motif"
    c.results.append(dict(kind="public-mini-header",page=page,enabled=enabled,tempo=tempo,pose_count=len(spec["frames"]),loop_quarter_beats=spec["loop_quarter_beats"],clock_source="native-selected-norns-clock",transport="stopped",samples=samples,observed_poses=sorted(seen),all_distinct_poses_required=require_all,atlas_sha256=ATLAS_SHA256,passed=True,citation="README.md#ui-motion",characterization="Exact native v2 bitmap, bounded stationary controls and independently checked native musical phase brackets. At240BPM the two-beat eight-pose sequence exceeds the12FPS redraw cap; skipped poses are allowed and complete-loop coverage is not claimed. No hardware scheduling equivalence"))
