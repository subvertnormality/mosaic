"""Independent cached-evidence verification for the three native public-gap cases."""
import base64, hashlib, json
from pathlib import Path

def verify(step, observations, path, clock_mode, results):
    row=step["output"]["binding"]["assertion"]
    idx=step["output"]["binding"].get("assertion_index")
    if type(idx) is not int or not 0 <= idx < len(results) or results[idx] != row or row.get("passed") is not True:
        raise ValueError("public-gap result binding changed")
    kind=row.get("kind")
    citation={"manual-repeat-reset-public-midi":"manual:reset-at-pattern-repeat",
              "manual-snap-mask-public-midi":"manual:snap-note-masks-to-scale",
              "manual-ui-motion-public-frames":"manual:ui-motion",
              "manual-ui-motion-public-midi":"manual:ui-motion",
              "manual-ui-motion-midi-pair":"manual:ui-motion"}.get(kind)
    if not citation or row.get("citation") != citation:
        raise ValueError("public-gap citation changed")
    events=[json.loads(line) for line in (Path(path)/"native/native-events.jsonl").read_text().splitlines()]
    ek=11 if clock_mode=="controlled-experimental" else 3
    tk="logical_ns" if clock_mode=="controlled-experimental" else "monotonic_ns"

    def exact_stream(entries, relative=False):
        if not isinstance(entries,list) or not entries:
            raise ValueError("missing complete native MIDI stream")
        packets=[e for e in events if e.get("kind")==ek and e.get("port")==1 and e.get("bytes") and 0x80<=e["bytes"][0]<0xf0]
        if relative:
            notes=[e for e in packets if 0x90<=e["bytes"][0]<=0x9f and e["bytes"][2]>0]
            if not notes: raise ValueError("missing native MIDI onsets")
            origin=notes[0][tk]
            actual=[{"port":e["port"],"bytes":e["bytes"],"logical_ns":e[tk]-origin} for e in packets if e[tk]>=origin]
            if actual!=entries: raise ValueError("relative complete native MIDI differs")
            return actual
        indices=[r.get("index") for r in entries]
        if any(type(i) is not int for i in indices) or indices!=sorted(set(indices)):
            raise ValueError("native MIDI indexes are malformed")
        by_index={e.get("index"):e for e in events if e.get("kind")==ek}
        for r in entries:
            e=by_index.get(r["index"])
            if e is None or (e.get("port"),e.get("bytes"),e.get(tk))!=(r.get("port"),r.get("bytes"),r.get("logical_ns")):
                raise ValueError("cached MIDI differs from native packet")
        lo,hi=indices[0],indices[-1]
        actual=[e for e in events if e.get("kind")==ek and lo<=e.get("index",-1)<=hi and e.get("port")==1 and e.get("bytes") and 0x80<=e["bytes"][0]<0xf0]
        if [e["index"] for e in actual]!=indices: raise ValueError("cached MIDI omitted a native channel packet")
        return actual

    if kind=="manual-repeat-reset-public-midi":
        reset=row.get("repeat_reset")
        if type(reset) is not bool or row.get("timing_tolerance_ns")!=2 or row.get("complete_midi_stream") is not True or row.get("dropped")!=0:
            raise ValueError("repeat-reset contract changed")
        expected=[]
        for tick in range(1549):
            origin=(tick//1536)*1536 if reset else 0
            if (tick-origin)%216==0:
                n=(tick-origin)//216%3
                expected.append((tick,[144,[60,62,64][n],[127,117,107][n]]))
        notes=[e for e in exact_stream(row.get("complete_channel_midi")) if 0x90<=e["bytes"][0]<=0x9f and e["bytes"][2]>0]
        if row.get("expected_ticks")!=[t for t,_ in expected] or [(e["port"],e["bytes"]) for e in notes]!=[(1,b) for _,b in expected]:
            raise ValueError("repeat-reset native note schedule changed")
        if row.get("exact_note_ons")!=[{"port":1,"bytes":b} for _,b in expected] or row.get("note_on_count")!=len(expected) or row.get("complete_channel_midi_count")!=2*len(expected) or row.get("complete_note_pair_count")!=len(expected):
            raise ValueError("repeat-reset complete MIDI inventory changed")
        t0=notes[0][tk]
        if any(abs(e[tk]-t0-round(t*1e9/144))>2 for e,(t,_) in zip(notes,expected)):
            raise ValueError("repeat-reset exact controlled ticks changed")
        if not any(r.get("kind")=="selected-menu-option-row" and r.get("label")=="Reset on pattern repeat" and r.get("value")==row.get("option_value") and r.get("citation")==citation and r.get("matched") is True for r in results):
            raise ValueError("repeat-reset selected option row missing")
    elif kind=="manual-snap-mask-public-midi":
        pitches=[60,62,65,69] if row.get("snap") is True else [61,63,66,70]
        if row.get("authored_masks")!=["C#3","D#3","F#3","A#3"] or row.get("output_pitches")!=pitches or row.get("option_value")!=("On" if row.get("snap") else "Off"):
            raise ValueError("Snap authored/output pitch contract changed")
        notes=[e for e in exact_stream(row.get("complete_channel_midi")) if 0x90<=e["bytes"][0]<=0x9f and e["bytes"][2]>0]
        phrase=[(1,[144,p,v]) for p,v in zip(pitches,[127,117,107,97])]
        expected=phrase*2+[phrase[0]]
        if [(e["port"],e["bytes"]) for e in notes]!=expected or row.get("exact_note_ons")!=[{"port":p,"bytes":b} for p,b in expected]:
            raise ValueError("Snap exact native phrase changed")
        if row.get("dropped")!=0 or not any(r.get("kind")=="selected-menu-option-row" and r.get("label")=="Snap note masks to scale" and r.get("value")==row["option_value"] and r.get("citation")==citation and r.get("matched") is True for r in results):
            raise ValueError("Snap selected option evidence missing")
        if row.get("snap") is True:
            held=[r for r in results if r.get("kind")=="selected-mask" and r.get("citation")==citation and r.get("held_step") in (1,2,3,4)]
            if [r.get("value") for r in held]!=row["authored_masks"]: raise ValueError("Snap held-note public readouts missing")
    elif kind=="manual-ui-motion-public-frames":
        if row.get("screen")!="C04" or row.get("region")!={"x0":108,"y0":0,"x1":128,"y1":8} or row.get("sample_count")!=19 or row.get("clock_sample_period_ns")!=83333333 or row.get("source_clock_tempo_bpm")!=90:
            raise ValueError("C04 observation contract changed")
        repo=Path(__file__).resolve().parents[1]
        lua_source=repo/"lib/ui_mini_atlas.lua"
        atlas_source=repo/"tests/behaviour/contract/mini_header_atlas_v2.json"
        if hashlib.sha256(lua_source.read_bytes()).hexdigest()!="c3437a288ece5198726f77ef50d6335f7ee36ea914cb5e908ed9f6ffed60c871":
            raise ValueError("C04 Lua source identity changed")
        if hashlib.sha256(atlas_source.read_bytes()).hexdigest()!="4b1623dd87cabd4a98b3ed5d2e47b32455221c360054f1eb5dd8783eb5278c46":
            raise ValueError("C04 atlas contract identity changed")
        atlas=json.loads(atlas_source.read_text())
        spec=next(s for s in atlas["screens"] if s["id"]=="C04")
        if (spec.get("origin"),spec.get("width"),spec.get("height"),spec.get("pose_count"),spec.get("loop_quarter_beats"))!=([108,0],20,8,8,2):
            raise ValueError("C04 source geometry changed")
        levels={".":0,"a":119,"b":187,"c":255};rasters=[]
        for frame in spec["frames"]:
            if len(frame)!=8 or any(len(line)!=20 for line in frame): raise ValueError("malformed C04 atlas")
            rasters.append(tuple(levels[ch] for line in frame for ch in line))
        unique=[]
        for raster in rasters:
            if raster not in unique: unique.append(raster)
        hashes=[hashlib.sha256(bytes(r)).hexdigest() for r in unique]
        if row.get("atlas_frame_count")!=8 or row.get("atlas_loop_beats")!=2 or row.get("atlas_unique_pose_count")!=5 or row.get("atlas_pose_raster_sha256")!=hashes:
            raise ValueError("C04 literal raster identity changed")
        indices=row.get("observation_indices");times=row.get("clock_logical_ns")
        if not isinstance(indices,list) or len(indices)!=19 or indices!=sorted(set(indices)) or not isinstance(times,list) or len(times)!=19:
            raise ValueError("C04 observation list changed")
        rasters_seen=[];outside=[]
        for j,i in enumerate(indices):
            if type(i) is not int or not 0<=i<len(observations): raise ValueError("C04 observation index invalid")
            obs=observations[i];state=obs["state"];frame=state["frame"];pixels=base64.b64decode(frame["pixels_base64"])
            if obs.get("backend")!="native" or obs.get("fidelity")!="native-norns" or hashlib.sha256(pixels).hexdigest()!=frame.get("sha256") or frame.get("sha256")!=row["frame_sha256s"][j]:
                raise ValueError("C04 pixels are not the exact native framebuffer")
            if state.get("clock",{}).get("logical_ns")!=times[j] or (j and times[j]-times[j-1]!=83333333):
                raise ValueError("C04 sample logical time changed")
            rasters_seen.append(tuple(pixels[(y*128+x)*4] for y in range(8) for x in range(108,128)))
            other=bytearray()
            for y in range(64):
                for x in range(128):
                    if not (108<=x<128 and y<8):
                        p=(y*128+x)*4;other.extend(pixels[p:p+4])
            outside.append(hashlib.sha256(other).hexdigest())
        if [list(r) for r in rasters_seen]!=row.get("frames") or len(set(outside))!=1 or outside[0]!=row.get("outside_roi_sha256"):
            raise ValueError("C04 ROI pixels or unchanged controls differ")
        option="On" if row.get("enabled") is True else "Off"
        if not any(r.get("kind")=="selected-menu-option-row" and r.get("label")=="UI motion" and r.get("value")==option and r.get("citation")==citation and r.get("matched") is True for r in results):
            raise ValueError("C04 selected UI motion option row missing")
        paired=[r for r in results if r.get("kind")=="manual-ui-motion-public-frames" and r.get("citation")==citation]
        if len(paired)!=2 or {r.get("enabled") for r in paired}!={False,True} or paired[0].get("outside_roi_sha256")!=paired[1].get("outside_roi_sha256"):
            raise ValueError("C04 On/Off controls or outside-ROI state differ")
        if row.get("enabled") is False:
            if any(r!=rasters[0] for r in rasters_seen) or row.get("source_pose_coverage")!=[0]: raise ValueError("C04 Off pose is not exact/default/stable")
        elif row.get("enabled") is True:
            poses=row.get("source_pose_indices")
            if set(rasters_seen)!={rasters[i] for i in range(8)} or len(set(rasters_seen))!=5 or not isinstance(poses,list) or len(poses)!=19 or any(rasters_seen[j]!=rasters[p] for j,p in enumerate(poses)) or row.get("source_pose_coverage")!=list(range(8)):
                raise ValueError("C04 On misses source poses or exact rasters")
            if row.get("source_phase_consistent") is not True: raise ValueError("C04 source clock phase receipt missing")
            valid=False
            for milli in range(8000):
                anchor=milli/1000
                candidate=[int(anchor+(t-times[0])/1e9*6.0+1e-7)%8 for t in times]
                if candidate==poses: valid=True;break
            if not valid: raise ValueError("C04 frame phases do not follow the source clock")
        else: raise ValueError("C04 enabled state is not Boolean")
    elif kind=="manual-ui-motion-public-midi":
        if row.get("timing_tolerance_ns")!=2 or row.get("complete_midi_stream") is not True or row.get("dropped")!=0 or row.get("gate_ticks")!=[24]*8:
            raise ValueError("UI Motion MIDI contract changed")
        expected=[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]*2+[(60,127)]]
        if row.get("exact_note_ons")!=[{"port":p,"bytes":b} for p,b in expected] or row.get("note_on_count")!=9 or row.get("complete_note_pair_count")!=9 or row.get("natural_gate_count")!=8:
            raise ValueError("UI Motion exact musical expectation changed")
        actual=exact_stream(row.get("relative_channel_midi"),relative=True)
        if len(actual)!=18: raise ValueError("UI Motion complete channel event count changed")
        notes=[e for e in actual if 0x90<=e["bytes"][0]<=0x9f and e["bytes"][2]>0]
        if [(e["port"],e["bytes"]) for e in notes]!=expected: raise ValueError("UI Motion native note phrase differs")
        for i,(port,on) in enumerate(expected):
            attack=actual[2*i];release=actual[2*i+1]
            if release["bytes"]!=[128,on[1],on[2]]: raise ValueError("UI Motion native note release differs")
            if i<8:
                if abs(attack["logical_ns"]-round(i*24*1e9/144))>2 or abs(release["logical_ns"]-round((i+1)*24*1e9/144))>2:
                    raise ValueError("UI Motion natural sixteenth-note gate differs")
            elif release["logical_ns"]-attack["logical_ns"]<=0 or release["logical_ns"]-attack["logical_ns"]>=round(1e9/144):
                raise ValueError("UI Motion final gate is not shorter than one source tick")
        stops=[e for e in events if e.get("kind")==ek and e.get("port")==1 and e.get("bytes")==[252]]
        final_offs=[e for e in events if e.get("kind")==ek and e.get("port")==1 and e.get("bytes")==[128,60,127]]
        if len(stops)!=1 or not final_offs or max(e[tk] for e in final_offs)!=stops[0].get(tk):
            raise ValueError("UI Motion final gate does not end at native MIDI Stop")
        final_duration=actual[-1]["logical_ns"]-actual[-2]["logical_ns"]
        if row.get("final_gate_duration_ns")!=final_duration or row.get("final_gate_duration_less_than_one_tick") is not True:
            raise ValueError("UI Motion stop-truncated final gate duration changed")
        if row.get("final_gate_policy")!="stopped-after-extra-onset" or row.get("final_gate_matches_stop_logical_ns") is not True or row.get("stop_grid_press_count")!=2:
            raise ValueError("UI Motion stop-boundary receipt changed")
    elif kind=="manual-ui-motion-midi-pair":
        if row.get("option_values")!=["Off","On"] or any(row.get(k) is not True for k in ("same_exact_note_ons","same_complete_channel_midi","same_natural_gates","same_stop_truncated_gate","same_controlled_timing")):
            raise ValueError("UI Motion pair receipt changed")
        pair=[r for r in results if r.get("kind")=="manual-ui-motion-public-midi" and r.get("citation")==citation]
        if len(pair)!=2 or {r.get("enabled") for r in pair}!={False,True} or pair[0].get("relative_channel_midi")!=pair[1].get("relative_channel_midi"):
            raise ValueError("UI Motion Off/On full MIDI differs")
    else:
        raise ValueError("unsupported public-gap kind")
