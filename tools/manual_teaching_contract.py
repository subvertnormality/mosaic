"""Pure source-bound teaching transition validation helpers."""
import hashlib, json

def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def native_transition_hash(native):
    return hashlib.sha256(canonical_json(native)).hexdigest()

def replay_held_controls(native):
    held=set()
    for step in native["scene_input_prefix"]:
        for action in step["inputs"]:
            kind=action.get("type")
            if kind not in ("grid", "key") or "state" not in action: continue
            identity=("grid", action["x"], action["y"]) if kind=="grid" else ("key", action["n"])
            if action["state"]==1: held.add(identity)
            elif action["state"]==0: held.discard(identity)
    return held

def validate_semantics(native, requirements):
    target=native["to_step"]
    actual_screen=target["expect"].get("screen", [])
    if any(item not in actual_screen for item in requirements.get("screen_contains", [])): return False
    actual_midi=target["expect"].get("midi_phrase", [])
    if any(item not in actual_midi for item in requirements.get("midi_phrase_contains", [])): return False
    expected={tuple(("grid",x["x"],x["y"]) if x["type"]=="grid" else ("key",x["n"])) for x in requirements.get("held_controls_at_target", [])}
    return replay_held_controls(native)==expected

def validate_binding(binding, native, candidates):
    key=(binding.get("scene_id"),binding.get("from_step_id"),binding.get("to_step_id"))
    matching=[x for x in candidates if (x.get("scene_id"),x.get("from_step_id"),x.get("to_step_id"))==key]
    prefix=native.get("scene_input_prefix",[])
    native_key=(native.get("scene",{}).get("id"),native.get("from_step",{}).get("id"),native.get("to_step",{}).get("id"))
    adjacent=(len(prefix)>=2 and prefix[-1].get("step_id")==key[2] and prefix[-2].get("step_id")==key[1])
    return (len(matching)==1 and matching[0]==binding and native_key==key and adjacent
            and native_transition_hash(native)==binding.get("native_transition_contract_sha256")
            and validate_semantics(native,binding.get("semantic_requires",{})))
