"""Strict v8 reader teaching contracts over captured public output."""
import re
import hashlib
import json
import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from manual_teaching_errors import TeachingContractError as Error
from manual_teaching_contract import native_transition_hash, replay_held_controls, validate_binding, validate_semantics
from manual_teaching_v8_contract import native_transition_hash_v8, native_transition_hash_prelude
PATHS = {"page":("page",), "header.title":("header","title"), "header.scope":("header","scope"),
 "header.layout":("header","layout"), "selected_field.label":("selected_field","label"),
 "selected_field.value":("selected_field","value"), "selected_field.layout":("selected_field","layout"),
 "mask_fields":("mask_fields",), "device_configuration":("device_configuration",)}
READOUT = set(PATHS) | {"dashboard_rows","selected_menu_text"}
SEMANTICS = {"screen_contains","midi_phrase_contains","held_controls_at_target","public_readout_equals",
 "grid_cells","leds_at_target","midi_events_at_target","midi_silence_at_target","project_files_at_target",
 "parameter_readout_equals","play_note_silence_at_target"}
ACTION_FIELDS = {
 "tap-grid":{"x","y","label"}, "tap-key":{"n","label"},
 "select-value":{"control","field_label","label","value"}, "choose-menu":{"label","trigger"},
 "play-phrase":{"label","trigger"}, "hold-grid":{"x","y","label"}, "release-grid":{"x","y","label"},
 "hold-key":{"n","label"}, "release-key":{"n","label"},
 "preview-recorded-result":{"target_step_id","label"},
 "play-keyboard-phrase":{"port","notes","label"},
 "play-note-silence":{"play_step_id","stop_step_id","window_result_id","window_duration_s","label"}}
MISSING=object()
_SAFE_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
def _int(x): return isinstance(x,int) and not isinstance(x,bool)
def _path(obj, path):
 for p in path:
  if not isinstance(obj,dict) or p not in obj: return MISSING
  obj=obj[p]
 return obj
def _assertion(native):
 out=native.get("to_step",{}).get("output",{})
 binding=out.get("binding") if isinstance(out,dict) else None
 return binding.get("assertion") if isinstance(binding,dict) else None
def _public_path(a, key):
 if key.startswith("selected_field.") and isinstance(a,dict) and a.get("kind")=="selected-field":
  return a.get(key.split(".",1)[1], MISSING)
 return _path(a, PATHS[key])
def _matches_field_value(assertion,label,value):
 if _public_path(assertion,"selected_field.label")==label and _public_path(assertion,"selected_field.value")==value: return True
 rows=assertion.get("mask_fields") if isinstance(assertion,dict) else None
 if isinstance(rows,list) and any(isinstance(row,dict) and row.get("field")==label and row.get("value")==value for row in rows): return True
 device=assertion.get("device_configuration") if isinstance(assertion,dict) else None
 return isinstance(device,dict) and label in ("device","midi_channel","midi_port") and device.get(label)==value
def _dashboard(a):
 if not isinstance(a,dict): return None
 if a.get("kind")=="dashboard-row": return [{"row":a.get("row"),"label":a.get("label"),"value":a.get("value")}]
 if a.get("kind")=="dashboard":
  rows=a.get("rows")
  if not isinstance(rows,list) or not rows or len(rows)>56: return None
  if any(not isinstance(row,list) or len(row)!=2 or any(not isinstance(cell,str) or not cell.strip() for cell in row) for row in rows): return None
  return [{"row":index,"label":row[0],"value":row[1]} for index,row in enumerate(rows)]
 return a.get("dashboard_rows")
def _valid_rows(rows):
 if not isinstance(rows,list) or not rows: return False
 seen=set()
 for r in rows:
  if not isinstance(r,dict) or set(r)!={"row","label","value"} or not _int(r["row"]) or not 0<=r["row"]<=55: return False
  if any(not isinstance(r[k],str) or not r[k].strip() for k in ("label","value")) or r["row"] in seen: return False
  seen.add(r["row"])
 return True
def _valid_masks(rows):
 return (isinstance(rows,list) and bool(rows) and all(
  isinstance(r,dict) and not (set(r)-{"field","value","layout"})
  and isinstance(r.get("field"),str) and bool(r["field"].strip())
  and isinstance(r.get("value"),str) and bool(r["value"].strip())
  and ("layout" not in r or isinstance(r["layout"],str) and bool(r["layout"].strip()))
  for r in rows))
def _valid_controls(items):
 if not isinstance(items,list): return False
 seen=set()
 for c in items:
  if not isinstance(c,dict): return False
  if c.get("type")=="grid" and set(c)=={"type","x","y"} and _int(c["x"]) and _int(c["y"]) and 1<=c["x"]<=16 and 1<=c["y"]<=8: ident=("grid",c["x"],c["y"])
  elif c.get("type")=="key" and set(c)=={"type","n"} and _int(c["n"]) and 1<=c["n"]<=3: ident=("key",c["n"])
  else: return False
  if ident in seen: return False
  seen.add(ident)
 return True
def _valid_cells(cells):
 if not isinstance(cells,list) or not cells: return False
 seen=set()
 for c in cells:
  if not isinstance(c,dict) or set(c)!={"x","y","level"}: return False
  x,y,l=c["x"],c["y"],c["level"]
  if not all(_int(z) for z in (x,y,l)) or not (1<=x<=16 and 1<=y<=8 and 0<=l<=15) or (x,y) in seen: return False
  seen.add((x,y))
 return True
def _validate_semantics(req):
 if not isinstance(req,dict) or not req or set(req)-SEMANTICS: raise Error("semantic_requires has unknown or missing supported predicates")
 readout=req.get("public_readout_equals")
 if readout is not None:
  if not isinstance(readout,dict) or not readout or set(readout)-READOUT: raise Error("public_readout_equals has unknown public fields")
  for k,v in readout.items():
   if k in PATHS and k not in ("mask_fields","device_configuration"):
    if not isinstance(v,str) or not v.strip(): raise Error("public readout strings must be concrete")
   elif k=="mask_fields" and not _valid_masks(v): raise Error("mask_fields must contain public field/value rows")
   elif k=="device_configuration" and (not isinstance(v,dict) or set(v) not in ({"device"},{"device","midi_channel","midi_port"}) or any(not isinstance(value,str) or not value.strip() for value in v.values())): raise Error("device_configuration must contain exact public device, MIDI channel, and port values")
   elif k=="dashboard_rows" and not _valid_rows(v): raise Error("dashboard_rows must contain public row/label/value")
   elif k=="selected_menu_text" and (not isinstance(v,str) or not v.strip()): raise Error("selected menu text must be concrete")
 for k in ("grid_cells","leds_at_target"):
  if k in req and not _valid_cells(req[k]): raise Error(k+" needs unique in-bounds x/y/level entries")
 if "held_controls_at_target" in req and not _valid_controls(req["held_controls_at_target"]): raise Error("held controls must be valid grid coordinates or norns keys")
 if "midi_events_at_target" in req:
  events=req["midi_events_at_target"]
  if not isinstance(events,list) or not events: raise Error("midi_events_at_target must be nonempty")
  for e in events:
   if not isinstance(e,dict) or set(e)!={"port","bytes"} or not _int(e["port"]) or e["port"]<1 or not isinstance(e["bytes"],list) or not e["bytes"] or any(not _int(b) or not 0<=b<=255 for b in e["bytes"]): raise Error("MIDI predicate needs exact port and bytes")
 if "midi_silence_at_target" in req and req["midi_silence_at_target"] is not True: raise Error("midi_silence_at_target may only be true")
 if "play_note_silence_at_target" in req and req["play_note_silence_at_target"] is not True: raise Error("play_note_silence_at_target may only be true")
 if "project_files_at_target" in req:
  names=req["project_files_at_target"]
  if not isinstance(names,list) or not names or any(not isinstance(n,str) or not n or n in (".","..") or "/" in n or "\\" in n for n in names) or len(set(names))!=len(names):
   raise Error("project_files_at_target must be unique safe basenames")

 if "parameter_readout_equals" in req:
  try:
   from manual_parameter_readout import validate_request
   validate_request(req["parameter_readout_equals"])
  except Exception as exc:
   raise Error("parameter_readout_equals is not a strict native readout request") from exc

 if not any(k in req for k in ("screen_contains","midi_phrase_contains","public_readout_equals","grid_cells","leds_at_target","midi_events_at_target","midi_silence_at_target","project_files_at_target","parameter_readout_equals","play_note_silence_at_target")): raise Error("semantic_requires needs a concrete observable outcome")
def _records(native):
 if native.get("contract_schema")=="mosaic-native-transition-v3": return native["step_interval"][1:]
 return [native["to_step"]]
def _step_inputs(native):
 return [e for r in _records(native) for e in r.get("inputs",[])]

def _midi_bytes(event):
 value=event.get("bytes") if isinstance(event,dict) else None
 if isinstance(value,list): return value
 if isinstance(value,str):
  try: result=[int(part) for part in value.split()]
  except ValueError: return None
  if not value.strip() or any(not 0<=part<=255 for part in result): return None
  return result
 return None


def _zero_note_window_receipt(native, assertion, start, end, action, play, stop, play_input_refs, stop_input_refs):
 evidence=native.get("scene",{}).get("evidence",{})
 session=evidence.get("session_context") if isinstance(evidence,dict) else None
 if not isinstance(session,dict) or not isinstance(session.get("session_id"),str) or not session["session_id"] or session.get("finished") is not True or session.get("cleanup_verified") is not True or session.get("held_inputs")!=[]:
  raise Error("zero-note proof requires a finished, cleaned native session")
 path=evidence.get("path")
 pinned=evidence.get("native_events_sha256")
 if not isinstance(path,str) or not path or not isinstance(pinned,str) or not re.fullmatch(r"[0-9a-f]{64}",pinned):
  raise Error("zero-note proof lacks the pinned native event file")
 try:
  from manual_publication_verify import evidence as audit_native_evidence
  audit_native_evidence(native["scene"])
  identity=json.loads((Path(path)/"native"/"identity.json").read_text(encoding="utf-8"))
  context_path=Path(path)/"session-context.json"
  context_raw=context_path.read_bytes()
  if hashlib.sha256(context_raw).hexdigest()!=evidence.get("session_context_sha256"):
   raise ValueError("session context digest differs")
  captured_context=json.loads(context_raw)
  if captured_context!=session or identity.get("session_id")!=session["session_id"]:
   raise ValueError("native identity and session context differ")
 except Exception as exc:
  raise Error("zero-note source identity audit failed") from exc
 event_path=Path(path)/"native-events.jsonl"
 try:
  raw=event_path.read_bytes()
 except OSError as exc:
  raise Error("pinned native event file is unavailable") from exc
 file_sha=hashlib.sha256(raw).hexdigest()
 if file_sha!=pinned:
  raise Error("native event file differs from its captured source identity")
 try:
  rows=[json.loads(line) for line in raw.splitlines() if line.strip()]
 except Exception as exc:
  raise Error("native event file is malformed") from exc
 midi_rows=[row for row in rows if isinstance(row,dict) and row.get("kind")==11]
 indices=[row.get("index") for row in midi_rows]
 if indices!=list(range(1,len(midi_rows)+1)) or any(row.get("sequence")!=row.get("index") for row in midi_rows):
  raise Error("native MIDI event indices are not the complete ordered stream")
 if end>len(midi_rows) or end<=start:
  raise Error("zero-note window bounds are outside the captured native MIDI stream")
 window=midi_rows[start:end]
 if len(window)!=end-start or [row.get("index") for row in window]!=list(range(start+1,end+1)):
  raise Error("zero-note window is not a contiguous native event interval")
 for row in window:
  data=row.get("bytes")
  if not isinstance(data,list) or not data or any(not _int(byte) or not 0<=byte<=255 for byte in data):
   raise Error("zero-note window contains malformed native MIDI bytes")
 positive=[row for row in window if len(row["bytes"])>=3 and row["bytes"][0]&240==144 and row["bytes"][2]>0]
 if positive or assertion.get("note_ons")!=[]:
  raise Error("zero-probability Play window emitted a positive-velocity note-on")
 def delta(step):
  midi=step.get("output",{}).get("midi")
  if not isinstance(midi,dict) or midi.get("truncated") is not False or not isinstance(midi.get("events"),list) or midi.get("total")!=len(midi["events"]):
   raise Error("Play/Stop checkpoint lacks its complete per-step MIDI delta")
  normalized=[]
  for event in midi["events"]:
   data=_midi_bytes(event)
   if not isinstance(event,dict) or not _int(event.get("port")) or not isinstance(data,list):
    raise Error("Play/Stop MIDI delta contains malformed events")
   normalized.append((event["port"],data))
  return normalized
 def native_pair(row):
  return (row.get("port"),row.get("bytes"))
 play_delta=delta(play); stop_delta=delta(stop)
 normalized_window=[native_pair(row) for row in window]
 after=[native_pair(row) for row in midi_rows[end:]]
 if not play_delta or normalized_window[:len(play_delta)]!=play_delta:
  raise Error("native window does not begin with the captured Play-step MIDI delta")
 if not stop_delta or after[:len(stop_delta)]!=stop_delta:
  raise Error("native window boundary does not precede the captured Stop-step MIDI delta")
 canonical=json.dumps(window,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
 return {"kind":"zero-note-play-window","session_id":session["session_id"],
  "native_events_sha256":pinned,"native_event_file_sha256":file_sha,"native_event_count":len(midi_rows),
  "window_start_index":start,"window_end_index":end,"window_event_count":len(window),
  "window_native_events_sha256":hashlib.sha256(canonical).hexdigest(),
  "positive_velocity_note_on_count":len(positive),"logical_duration_s":action["window_duration_s"],
  "play_step_id":action["play_step_id"],"stop_step_id":action["stop_step_id"],
  "window_result_id":action["window_result_id"],"play_input_refs":play_input_refs,
  "stop_input_refs":stop_input_refs,"play_led_cell":{"x":1,"y":8,"level":12},
  "stop_led_cell":{"x":1,"y":8,"level":2}}

def _export_native_receipts(native,binding):
 for key in ("mask_readout_receipts","parameter_readout_receipts","play_note_silence_receipts"):
  value=native.get(key)
  if isinstance(value,list) and value:
   binding[key]=value
 return binding

def _midi_phrase_matches(midi, phrase):
 if not isinstance(midi,dict) or midi.get("truncated") is not False or not isinstance(midi.get("events"),list) or not isinstance(phrase,list) or not phrase: return False
 pos=0
 for wanted in phrase:
  while pos<len(midi["events"]):
   event=midi["events"][pos]; pos+=1
   if isinstance(event,dict) and event.get("port")==wanted.get("port") and _midi_bytes(event)==wanted.get("bytes"): break
  else: return False
 return True

def _validate_actions(authored,native,target_id,req,mask_readouts=None):
 actions=authored.get("actions")
 if not isinstance(actions,list) or len(actions)<2: raise Error("teaching actions need a practical action and final preview")
 ids=set()
 for i,a in enumerate(actions):
  if not isinstance(a,dict) or a.get("kind") not in ACTION_FIELDS: raise Error("unsupported teaching action kind")
  kind=a["kind"]; fields={"id","kind"}|ACTION_FIELDS[kind]|({"direction","field_direction","field_control","between_trigger","between_hold","field_slot","expected_marker","mask_field","while_held_grid"} & set(a) if kind=="select-value" else set())
  if kind=="choose-menu":
   proof_fields={"menu_text","destination"} & set(a)
   if len(proof_fields)!=1: raise Error("choose-menu needs exactly one exact menu_text or destination proof")
   fields |= proof_fields
  if set(a)!=fields or not isinstance(a.get("id"),str) or not a["id"].strip() or a["id"] in ids or not isinstance(a.get("label"),str) or not a["label"].strip(): raise Error("teaching action fields/IDs/labels are invalid")
  ids.add(a["id"])
  if kind in ("tap-grid","hold-grid","release-grid") and (not _int(a.get("x")) or not _int(a.get("y")) or not (1<=a["x"]<=16 and 1<=a["y"]<=8)): raise Error("grid action coordinates out of bounds")
  if kind in ("tap-key","hold-key","release-key") and (not _int(a.get("n")) or not 1<=a["n"]<=3): raise Error("key action must identify K1/K2/K3")
  if kind=="select-value" and (a.get("control") not in ("E2","E3") or not isinstance(a.get("field_label"),str) or not a["field_label"].strip() or not isinstance(a.get("value"),str) or not a["value"].strip() or ("direction" in a and a["direction"] not in ("clockwise","anticlockwise")) or ("field_control" in a and (a["field_control"]!="E2" or a.get("control")!="E3")) or ("field_direction" in a and ("field_control" not in a or a["field_direction"] not in ("clockwise","anticlockwise"))) or ("between_trigger" in a and "between_hold" in a) or ("between_trigger" in a and ("field_control" not in a or not isinstance(a["between_trigger"],dict) or set(a["between_trigger"])!={"type","x","y","gesture"} or a["between_trigger"].get("type")!="grid" or a["between_trigger"].get("gesture")!="tap" or not _int(a["between_trigger"].get("x")) or not _int(a["between_trigger"].get("y")) or not 1<=a["between_trigger"]["x"]<=16 or not 1<=a["between_trigger"]["y"]<=8)) or ("between_hold" in a and ("field_control" not in a or not isinstance(a["between_hold"],dict) or set(a["between_hold"])!={"type","x","y","gesture"} or a["between_hold"].get("type")!="grid" or a["between_hold"].get("gesture")!="hold" or not _int(a["between_hold"].get("x")) or not _int(a["between_hold"].get("y")) or not 1<=a["between_hold"]["x"]<=16 or not 1<=a["between_hold"]["y"]<=8)) or ("while_held_grid" in a and (not isinstance(a["while_held_grid"],dict) or set(a["while_held_grid"])!={"x","y"} or not _int(a["while_held_grid"].get("x")) or not _int(a["while_held_grid"].get("y")) or not 1<=a["while_held_grid"]["x"]<=16 or not 1<=a["while_held_grid"]["y"]<=8 or a.get("expected_marker")!="L")) or ("field_slot" in a and (not _int(a["field_slot"]) or a["field_slot"]<1)) or ("expected_marker" in a and a["expected_marker"] not in (None,"L","S")) or ("field_slot" in a) != ("expected_marker" in a) or ("mask_field" in a and (not isinstance(a["mask_field"],str) or not a["mask_field"].strip()))): raise Error("select-value needs exact public field/value and valid captured controls")
  if kind in ("choose-menu","play-phrase"):
   tr=a.get("trigger")
   if not isinstance(tr,dict): raise Error(kind+" needs an exact raw-input trigger")
   if tr.get("type")=="grid" and set(tr)=={"type","x","y","gesture"} and tr.get("gesture")=="tap" and _int(tr.get("x")) and _int(tr.get("y")) and 1<=tr["x"]<=16 and 1<=tr["y"]<=8: pass
   elif tr.get("type")=="key" and set(tr)=={"type","n","gesture"} and tr.get("gesture")=="tap" and _int(tr.get("n")) and 1<=tr["n"]<=3: pass
   elif tr.get("type")=="enc" and set(tr)=={"type","n","direction"} and tr.get("n") in ((1,2,3) if kind=="choose-menu" else (2,3)) and tr.get("direction") in ("clockwise","anticlockwise"): pass
   else: raise Error(kind+" trigger is not a valid captured grid/key tap or encoder direction")
  if kind=="play-keyboard-phrase":
   if not _int(a.get("port")) or not 0<=a["port"]<=255 or not isinstance(a.get("notes"),list) or not a["notes"]: raise Error("play-keyboard-phrase needs a MIDI port and notes")
   for note in a["notes"]:
    if not isinstance(note,dict) or set(note)!={"note","velocity"} or not _int(note.get("note")) or not 0<=note["note"]<=127 or not _int(note.get("velocity")) or not 1<=note["velocity"]<=127: raise Error("keyboard phrase note rows are invalid")
  if kind=="play-note-silence" and (not isinstance(a.get("play_step_id"),str) or not a["play_step_id"].strip() or not isinstance(a.get("stop_step_id"),str) or not a["stop_step_id"].strip() or not isinstance(a.get("window_result_id"),str) or not a["window_result_id"].strip() or isinstance(a.get("window_duration_s"),bool) or not isinstance(a.get("window_duration_s"),(int,float)) or a["window_duration_s"]<=0): raise Error("play-note-silence needs exact captured Play/Stop steps and a positive logical window")
  if kind=="choose-menu":
   if "menu_text" in a and (not isinstance(a["menu_text"],str) or not a["menu_text"].strip()): raise Error("choose-menu menu_text must be exact public text")
   if "destination" in a and (not isinstance(a["destination"],dict) or len(a["destination"])!=1 or set(a["destination"])-{"page","header_title"} or not isinstance(next(iter(a["destination"].values()),None),str) or not next(iter(a["destination"].values()),"").strip()): raise Error("choose-menu destination must be exact public page or header title")
  if kind=="preview-recorded-result" and (i!=len(actions)-1 or a.get("target_step_id")!=target_id): raise Error("recorded preview must be final and target the bound step")
 if actions[-1]["kind"]!="preview-recorded-result": raise Error("practical actions must end in recorded-result preview")
 raw=_step_inputs(native); final_held=replay_held_controls(native); assertion=_assertion(native)
 prefix=native.get("scene_input_prefix",[])
 if native.get("transition_scope")=="prelude":
  held=set()
 else:
  from_id=native.get("from_step_id") or native.get("from_step",{}).get("id")
  from_index=next((i for i,row in enumerate(prefix) if row.get("step_id")==from_id),None)
  if from_index is None: raise Error("transition lacks a real captured starting checkpoint")
  held=replay_held_controls({"scene_input_prefix":prefix[:from_index+1]})
 learner_held=set(held)
 out=native["to_step"].get("output",{}); midi=out.get("midi") if isinstance(out,dict) else None
 cursor=[0]
 def consume(predicate):
  for index in range(cursor[0],len(raw)):
   if predicate(raw[index]):
    cursor[0]=index+1
    return index
  return None
 def tap(typ,identity):
  control=(typ,identity.get("x"),identity.get("y")) if typ=="grid" else (typ,identity.get("n"))
  if control in learner_held: return None
  for index in range(cursor[0],len(raw)):
   e=raw[index]
   if e.get("type")==typ and e.get("state")==1 and all(e.get(k)==v for k,v in identity.items()):
    for end in range(index+1,len(raw)):
     r=raw[end]
     if r.get("type")==typ and r.get("state")==0 and all(r.get(k)==v for k,v in identity.items()):
      cursor[0]=end+1
      last_tap[0]=(index,end)
      return index
  return None
 checkpoints=_records(native); checkpoint_cursor=0; action_proofs=[]
 def input_ref(index):
  offset=0
  for checkpoint in checkpoints:
   size=len(checkpoint.get("inputs",[]))
   if offset<=index<offset+size:
    return {"step_id":checkpoint.get("id"),"index":index-offset}
   offset+=size
  raise Error("action evidence input index is outside the captured interval")
 last_tap=[None]
 for a in actions[:-1]:
  action_input_indices=[]; checkpoint_step_id=None; proof={"kind":"raw-input"}
  k=a["kind"]
  if k=="tap-grid":
   if tap("grid",{"x":a["x"],"y":a["y"]}) is None: raise Error("tap-grid has no ordered captured press/release")
   action_input_indices.extend(last_tap[0]); proof={"kind":"grid-tap","x":a["x"],"y":a["y"]}
  if k=="tap-key":
   if tap("key",{"n":a["n"]}) is None: raise Error("tap-key has no ordered captured press/release")
   action_input_indices.extend(last_tap[0]); proof={"kind":"key-tap","n":a["n"]}
  if k=="hold-grid":
   control=("grid",a["x"],a["y"])
   press=consume(lambda e:e.get("type")=="grid" and e.get("x")==a["x"] and e.get("y")==a["y"] and e.get("state")==1)
   if control in learner_held or press is None: raise Error("hold-grid lacks an ordered captured press")
   action_input_indices.append(press); learner_held.add(control); proof={"kind":"grid-hold","x":a["x"],"y":a["y"]}
  if k=="hold-key":
   control=("key",a["n"])
   press=consume(lambda e:e.get("type")=="key" and e.get("n")==a["n"] and e.get("state")==1)
   if control in learner_held or press is None: raise Error("hold-key lacks an ordered captured press")
   action_input_indices.append(press); learner_held.add(control); proof={"kind":"key-hold","n":a["n"]}
  if k=="release-grid":
   control=("grid",a["x"],a["y"])
   release=consume(lambda e:e.get("type")=="grid" and e.get("x")==a["x"] and e.get("y")==a["y"] and e.get("state")==0)
   if control not in learner_held or release is None: raise Error("release-grid lacks an ordered prior hold and captured release")
   action_input_indices.append(release); learner_held.remove(control); proof={"kind":"grid-release","x":a["x"],"y":a["y"]}
  if k=="release-key":
   control=("key",a["n"])
   release=consume(lambda e:e.get("type")=="key" and e.get("n")==a["n"] and e.get("state")==0)
   if control not in learner_held or release is None: raise Error("release-key lacks an ordered prior hold and captured release")
   action_input_indices.append(release); learner_held.remove(control); proof={"kind":"key-release","n":a["n"]}
  if k=="select-value":
   if "field_control" in a:
    field_event=consume(lambda e:e.get("type")=="enc" and e.get("n")==2 and _int(e.get("delta")) and e["delta"]!=0 and ("field_direction" not in a or (e["delta"]>0)==(a["field_direction"]=="clockwise")))
    if field_event is None: raise Error("select-value field selection lacks ordered E2 input")
    action_input_indices.append(field_event)
    if "between_trigger" in a:
     bt=a["between_trigger"]
     if tap("grid",{"x":bt["x"],"y":bt["y"]}) is None: raise Error("select-value between_trigger lacks ordered captured grid tap")
     action_input_indices.extend(last_tap[0])
    if "between_hold" in a:
     bh=a["between_hold"]
     control=("grid",bh["x"],bh["y"])
     press=consume(lambda e:e.get("type")=="grid" and e.get("x")==bh["x"] and e.get("y")==bh["y"] and e.get("state")==1)
     if control in learner_held or press is None: raise Error("select-value between_hold lacks ordered captured press of the exact released-state cell")
     learner_held.add(control); action_input_indices.append(press)
   n=2 if a["control"]=="E2" else 3
   event_index=consume(lambda e:e.get("type")=="enc" and e.get("n")==n and _int(e.get("delta")) and e["delta"]!=0 and ("direction" not in a or (e["delta"]>0)==(a["direction"]=="clockwise")))
   if event_index is None: raise Error("select-value lacks ordered matching encoder input")
   action_input_indices.append(event_index)
   proof={"kind":"field-value","field_label":a["field_label"],"value":a["value"]}
   if "between_hold" in a:
    proof={"kind":"field-value-with-held-grid","field_label":a["field_label"],"value":a["value"],
     "held_grid":{"x":a["between_hold"]["x"],"y":a["between_hold"]["y"]}}
   record_input_start=0
   event_record=0
   for ri,record in enumerate(checkpoints):
    if event_index < record_input_start+len(record.get("inputs",[])):
     event_record=ri; break
    record_input_start+=len(record.get("inputs",[]))
   found=False
   parameter_request=req.get("parameter_readout_equals")
   for ci in range(max(checkpoint_cursor,event_record),len(checkpoints)):
    checkpoint=checkpoints[ci]
    ca=checkpoint.get("output",{}).get("binding",{}).get("assertion") if isinstance(checkpoint.get("output"),dict) else None
    parameter_match=(isinstance(parameter_request,dict)
     and checkpoint.get("id")==parameter_request.get("readout_step_id")
     and isinstance(ca,dict) and ca.get("kind")=="selected-param"
     and ca.get("slot")==parameter_request.get("slot")
     and ca.get("value")==parameter_request.get("value")
     and a.get("field_label")==parameter_request.get("parameter_label")
     and a.get("value")==parameter_request.get("value")
     and ("field_slot" not in a or a.get("field_slot")==parameter_request.get("slot"))
     and ("expected_marker" not in a or a.get("expected_marker")==parameter_request.get("marker")))
    selected_param_match=(isinstance(ca,dict) and ca.get("kind")=="selected-param"
     and ca.get("passed") is True
     and a.get("field_label")==ca.get("field_label")
     and a.get("field_slot")==ca.get("field_slot")
     and a.get("value")==ca.get("value")
     and a.get("expected_marker")==ca.get("field_marker"))
    verified_mask_step=(mask_readouts or {}).get(a.get("id"))
    direct_mask_match=(isinstance(ca,dict) and isinstance(ca.get("mask_fields"),list)
     and any(isinstance(row,dict) and row.get("field")==a.get("mask_field") and row.get("value")==a.get("value") for row in ca["mask_fields"]))
    mask_match=(isinstance(ca,dict) and checkpoint.get("id")==verified_mask_step
     and isinstance(a.get("mask_field"),str) and isinstance(a.get("value"),str)) or direct_mask_match
    field_match=("field_slot" not in a and "mask_field" not in a and isinstance(ca,dict) and _matches_field_value(ca,a["field_label"],a["value"]))
    if parameter_match or selected_param_match or mask_match or field_match:
     if (selected_param_match or parameter_match) and a.get("expected_marker")=="L":
      held_grids=[control for control in learner_held if control[0]=="grid"]
      if len(held_grids)!=1: raise Error("a selected parameter lock readout must follow exactly one held grid step")
      if "while_held_grid" in a and held_grids[0]!=("grid",a["while_held_grid"]["x"],a["while_held_grid"]["y"]):
       raise Error("selected parameter readout is not from the exact authored held step")
     found=True; checkpoint_step_id=checkpoint.get("id"); checkpoint_cursor=ci+1
     if selected_param_match: proof={"kind":"selected-parameter-value","field_label":a["field_label"],"field_slot":a["field_slot"],"value":a["value"],"field_marker":a["expected_marker"]}
     if mask_match: proof={"kind":"mask-field-value","field":a["mask_field"],"value":a["value"]}
     cursor[0]=max(cursor[0],sum(len(row.get("inputs",[])) for row in checkpoints[:ci+1]))
     break
   if not found: raise Error("select-value label/value lack an ordered exact public checkpoint")
  if k=="play-keyboard-phrase":
   from manual_keyboard_phrase import validate, KeyboardPhraseError
   try: phrase_receipt=validate(checkpoints,target_id,a["port"],a["notes"],midi,req.get("midi_events_at_target"))
   except KeyboardPhraseError as exc: raise Error(str(exc)) from exc
   action_input_indices=[i for i,e in enumerate(raw) if e.get("type")=="midi"]
   if not action_input_indices: raise Error("keyboard phrase has no captured MIDI inputs")
   checkpoint_step_id=target_id
   proof={"kind":"keyboard-midi-phrase","port":a["port"],"notes":a["notes"],"input_sha256":phrase_receipt["input_sha256"],"output_sha256":phrase_receipt["output_sha256"]}
  if k=="play-note-silence":
   if req.get("play_note_silence_at_target") is not True or a.get("window_result_id")!=target_id:
    raise Error("play-note-silence must bind the exact silent target and its semantic predicate")
   if native.get("contract_schema")!="mosaic-native-transition-v3":
    raise Error("play-note-silence requires a complete captured interval")
   by_id={row.get("id"):row for row in checkpoints}
   play=by_id.get(a["play_step_id"]); stop=by_id.get(a["stop_step_id"])
   if play is None or stop is None or checkpoints.index(play)>=checkpoints.index(stop) or checkpoints.index(stop)>=len(checkpoints)-1:
    raise Error("Play and Stop checkpoints must be ordered before the target result")
   def tap_indices(step):
    rows=step.get("inputs",[])
    controls=[(i,row) for i,row in enumerate(rows) if isinstance(row,dict) and row.get("type") in ("grid","key","enc")]
    if len(controls)!=2:
     raise Error("Play/Stop checkpoints must contain one exact public tap")
    first,last=controls[0][1],controls[1][1]
    if not (first.get("type")=="grid" and first.get("x")==1 and first.get("y")==8 and first.get("state")==1
            and last.get("type")=="grid" and last.get("x")==1 and last.get("y")==8 and last.get("state")==0):
     raise Error("Play/Stop checkpoint is not the exact public Play/Stop tap")
    offsets=[]; offset=0
    for row in checkpoints:
     if row is step:
      return [offset+controls[0][0],offset+controls[1][0]]
     offset+=len(row.get("inputs",[]))
    raise Error("Play/Stop input reference is outside the captured interval")
   play_grid=play.get("output",{}).get("grid"); stop_grid=stop.get("output",{}).get("grid")
   cell=(8-1)*16+(1-1)
   if not isinstance(play_grid,list) or len(play_grid)!=128 or play_grid[cell]!=12:
    raise Error("Play checkpoint does not show the mapped active LED level")
   if not isinstance(stop_grid,list) or len(stop_grid)!=128 or stop_grid[cell]!=2:
    raise Error("Stop checkpoint does not show the mapped off LED level")
   for row,phase,state in ((play,"active","active"),(stop,"stopped","off")):
    led=_assertion({"to_step":row})
    if not isinstance(led,dict) or led.get("kind")!="probability-play-led" or led.get("phase")!=phase or led.get("control")!="play_stop" or led.get("state")!=state or led.get("passed") is not True:
     raise Error("Play window is missing its exact public active/off LED assertion")
   assertion=_assertion(native)
   expected_result={"kind":"probability-zero-silence","passed":True,"play_step_id":a["play_step_id"],
    "stop_step_id":a["stop_step_id"],"window_result_id":a["window_result_id"],
    "seconds":a["window_duration_s"],"logical_duration_s":a["window_duration_s"],
    "positive_velocity_note_on_count":0,"note_ons":[]}
   if not isinstance(assertion,dict) or any(assertion.get(key)!=value for key,value in expected_result.items()):
    raise Error("target lacks the exact passed zero-probability window assertion")
   start,end=assertion.get("window_start_index"),assertion.get("window_end_index")
   if not _int(start) or not _int(end) or not 0<=start<=end:
    raise Error("zero-note window lacks exact ordered native event indices")
   if assertion.get("play_led_during")!="active" or assertion.get("stop_led_after")!="off":
    raise Error("zero-note window lacks active and stopped Play LED assertions")
   action_input_indices=tap_indices(play)+tap_indices(stop)
   receipt=_zero_note_window_receipt(native,assertion,start,end,a,play,stop,
    [input_ref(index) for index in tap_indices(play)],[input_ref(index) for index in tap_indices(stop)])
   native["play_note_silence_receipts"]=[receipt]
   advances=[]
   ordered=checkpoints[checkpoints.index(play):checkpoints.index(stop)+1]
   for row in ordered:
    for event in row.get("inputs",[]):
     if isinstance(event,dict) and event.get("type")=="advance":
      nanoseconds=event.get("nanoseconds")
      if _int(nanoseconds): advances.append(nanoseconds)
   expected_ns=round(a["window_duration_s"]*1_000_000_000)
   if not advances or any(value<0 or value>expected_ns for value in advances) or sum(advances)!=expected_ns:
    raise Error("captured controlled-time inputs do not contain the exact bounded Play window")
   checkpoint_step_id=target_id
   proof=receipt
  if k in ("choose-menu","play-phrase"):
   tr=a["trigger"]
   if tr["type"]=="grid": event_index=tap("grid",{"x":tr["x"],"y":tr["y"]})
   elif tr["type"]=="key": event_index=tap("key",{"n":tr["n"]})
   else:
    n=tr["n"]
    event_index=consume(lambda e:e.get("type")=="enc" and e.get("n")==n and _int(e.get("delta")) and e["delta"]!=0 and ((e["delta"]>0)==(tr["direction"]=="clockwise")))
   if event_index is None: raise Error(kind+" trigger has no ordered captured raw input")
   action_input_indices.extend(last_tap[0] if tr["type"] in ("grid","key") else [event_index])
   record_input_start=0; event_record=0
   for ri,record in enumerate(checkpoints):
    if event_index < record_input_start+len(record.get("inputs",[])):
     event_record=ri; break
    record_input_start+=len(record.get("inputs",[]))
   found=False
   for ci in range(max(checkpoint_cursor,event_record),len(checkpoints)):
    checkpoint=checkpoints[ci]; cpout=checkpoint.get("output",{})
    ca=cpout.get("binding",{}).get("assertion") if isinstance(cpout,dict) else None
    if k=="choose-menu":
     if "menu_text" in a:
      match=isinstance(ca,dict) and ca.get("kind")=="selected-menu-label" and ca.get("text")==a["menu_text"]
     else:
      dest=a["destination"]
      match=(isinstance(ca,dict) and (dest.get("page")==ca.get("page") if "page" in dest else dest.get("header_title")==_path(ca,("header","title"))))
    else:
     cp_midi=cpout.get("midi") if isinstance(cpout,dict) else None
     phrase=checkpoint.get("expect",{}).get("midi_phrase")
     if not phrase and checkpoint.get("id")==native.get("to_step",{}).get("id"):
      phrase=req.get("midi_events_at_target") or req.get("midi_phrase_contains")
     match=_midi_phrase_matches(cp_midi,phrase)
    if match:
     found=True; checkpoint_step_id=checkpoint.get("id"); checkpoint_cursor=ci+1
     if k=="choose-menu":
      if "menu_text" in a: proof={"kind":"menu-text","text":a["menu_text"]}
      else: proof={"kind":"destination",**a["destination"]}
     else: proof={"kind":"midi-phrase","events":phrase}
     cursor[0]=max(cursor[0],sum(len(row.get("inputs",[])) for row in checkpoints[:ci+1]))
     break
   if not found: raise Error(kind+" trigger lacks its exact later public/MIDI checkpoint")
  if not action_input_indices: raise Error("teaching action lacks exact captured input evidence")
  if checkpoint_step_id is None:
   last_index=action_input_indices[-1]; offset=0
   for checkpoint in checkpoints:
    size=len(checkpoint.get("inputs",[]))
    if offset<=last_index<offset+size: checkpoint_step_id=checkpoint.get("id"); break
    offset+=size
  action_proofs.append({"action_id":a["id"],"raw_inputs":[input_ref(i) for i in action_input_indices],
   "checkpoint_step_id":checkpoint_step_id,"proof":proof})
 if learner_held!=final_held: raise Error("authored held-control lifecycle differs from captured final held state")
 action_proofs.append({"action_id":actions[-1]["id"],"raw_inputs":[],
  "checkpoint_step_id":target_id,"proof":{"kind":"recorded-target","to_step_id":target_id}})
 return action_proofs
def _validate_output(native,req,mask_fields_at_target=None):
 target=native["to_step"]; out=target.get("output",{}); a=_assertion(native); readout=req.get("public_readout_equals",{})
 if not isinstance(out,dict): raise Error("target lacks captured output")
 for k,want in readout.items():
  if k=="parameter_readout_equals":
   # This predicate is independently resolved against raw case rows and
   # native frame pixels in _derive_parameter_receipt below.
   continue
  elif k=="mask_fields":
   # A Mask readout is admitted only after the current source row, bound native
   # frame, and independent overview_masks pixel oracle produce this projection.
   # Existing typed mask_fields assertions remain the original strict path.
   direct=a.get("mask_fields") if isinstance(a,dict) else None
   got=direct if isinstance(direct,list) else mask_fields_at_target
   if got!=want: raise Error("Mask public readout differs from its typed assertion or verified native field/frame evidence")
  elif k=="selected_menu_text":
   if not isinstance(a,dict) or a.get("kind")!="selected-menu-label" or a.get("text")!=want: raise Error("selected menu text differs from audited assertion")
  elif k=="dashboard_rows":
   if not isinstance(a,dict) or _dashboard(a)!=want: raise Error("dashboard row differs from audited assertion")
  else:
   got=_public_path(a,k) if isinstance(a,dict) else MISSING
   if got is MISSING or got!=want: raise Error("public readout differs from audited assertion: "+k)
 cells=req.get("grid_cells",[]); leds=req.get("leds_at_target",[])
 if cells or leds:
  grid=out.get("grid")
  if not isinstance(grid,list) or len(grid)!=128: raise Error("captured target grid must contain exactly 128 levels")
  for c in cells+leds:
   if grid[(c["y"]-1)*16+c["x"]-1]!=c["level"]: raise Error("target grid cell differs from authored level")
 if leds and (not isinstance(a,dict) or a.get("leds")!=leds): raise Error("LEDs differ from audited assertion")
 if "project_files_at_target" in req:
  binding=out.get("binding",{})
  files=a.get("files") if isinstance(a,dict) else None
  if (not isinstance(a,dict) or a.get("kind")!="manual-course-persistence"
      or not isinstance(a.get("name"),str) or not a["name"].strip()
      or not isinstance(files,dict) or set(files)!=set(req["project_files_at_target"])):
   raise Error("saved-project filenames differ from audited persistence assertion")
  if any(not isinstance(h,str) or not re.fullmatch(r"[0-9a-f]{64}",h) for h in files.values()):
   raise Error("saved-project assertion lacks exact file SHA-256 evidence")
  raw=json.dumps(a,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
  if not isinstance(binding,dict) or binding.get("assertion_sha256")!=hashlib.sha256(raw).hexdigest():
   raise Error("saved-project assertion provenance digest is invalid")
 midi=out.get("midi")
 if "midi_events_at_target" in req:
  if not isinstance(midi,dict) or midi.get("truncated") is not False or not isinstance(midi.get("events"),list): raise Error("target MIDI missing or truncated")
  pos=0
  for w in req["midi_events_at_target"]:
   while pos<len(midi["events"]) and not (midi["events"][pos].get("port")==w["port"] and _midi_bytes(midi["events"][pos])==w["bytes"]): pos+=1
   if pos==len(midi["events"]): raise Error("MIDI events differ from captured sequence")
   pos+=1
 if req.get("midi_silence_at_target") is True and (not isinstance(midi,dict) or midi.get("truncated") is not False or midi.get("events")!=[] or midi.get("total")!=0): raise Error("target is not explicitly MIDI-silent")
def _native(scene,from_id,to_id,scope):
 steps=scene.get("steps"); ids=[s.get("id") if isinstance(s,dict) else None for s in steps] if isinstance(steps,list) else []
 if not steps or len(ids)!=len(set(ids)): raise Error("native scene has missing/duplicate step IDs")
 try: i,j=ids.index(from_id),ids.index(to_id)
 except ValueError as e: raise Error("transition endpoints absent from native scene") from e
 if i>=j: raise Error("transition requires real ordered captured endpoints")
 if scope=="adjacent":
  if i+1!=j: raise Error("adjacent endpoints must be adjacent; declare interval explicitly")
  from manual_teaching import build_native_transition
  return build_native_transition(scene,from_id,to_id)
 if scope!="interval": raise Error("transition_scope must be adjacent or interval")
 if not isinstance(scene.get("evidence"),dict) or not {"identity_sha256","results_sha256"}<=set(scene["evidence"]): raise Error("scene lacks native identity/results evidence")
 interval=[]
 for s in steps[i:j+1]:
  if not all(k in s for k in ("id","inputs","expect","output")) or not isinstance(s["inputs"],list): raise Error("interval contains incomplete native checkpoint")
  interval.append({k:s[k] for k in ("id","inputs","expect","output")})
 sr={"id":scene["id"]}
 for k in ("behaviour_case","evidence"):
  if k in scene: sr[k]=scene[k]
 prefix=[{"step_id":s["id"],"inputs":s["inputs"]} for s in steps[:j+1]]
 return {"contract_schema":"mosaic-native-transition-v3","transition_scope":"interval","scene":sr,
  "from_step_id":from_id,"to_step_id":to_id,"step_interval":interval,"scene_input_prefix":prefix,
  "from_step":{k:steps[i][k] for k in ("id","inputs","expect","output")},
  "to_step":{k:steps[j][k] for k in ("id","inputs","expect","output")}}
def _native_prelude(scene,to_id,admission):
 summary=admission.get("admission_summary"); snapshot=admission.get("display_snapshot")
 if not isinstance(summary,dict) or summary.get("passed") is not True or summary.get("kind")!="native-prelude" or summary.get("assertion_created") is not False: raise Error("prelude admission is not a verified native baseline")
 alias=summary.get("runtime_alias")
 if alias!="getting-started-start" or summary.get("selector")!={"from_prelude_receipt_id":alias}: raise Error("prelude selector differs from sealed receipt")
 if summary.get("scene_id")!=scene.get("id") or summary.get("target_step_id")!=to_id: raise Error("prelude scene/target differs from bound transition")
 receipt_sha=admission.get("receipt_sha256"); chunk_sha=admission.get("chunk_sha256")
 if not isinstance(receipt_sha,str) or not re.fullmatch(r"[0-9a-f]{64}",receipt_sha) or not isinstance(chunk_sha,str) or not re.fullmatch(r"[0-9a-f]{64}",chunk_sha): raise Error("prelude original/chunk digests are required")
 steps=scene.get("steps",[])
 ids=[step.get("id") for step in steps if isinstance(step,dict)]
 if not ids or ids[0]!=to_id or len(ids)!=len(steps) or len(ids)!=len(set(ids)): raise Error("prelude may bind only the scene's real first captured step")
 if not isinstance(snapshot,dict) or snapshot.get("grid")!=steps[0].get("output",{}).get("grid") or not isinstance(snapshot.get("grid"),list) or len(snapshot["grid"])!=128: raise Error("prelude grid differs from first captured target")
 frame=snapshot.get("frame")
 if not isinstance(frame,dict) or frame.get("width")!=128 or frame.get("height")!=64 or not isinstance(frame.get("pixels_base64"),str): raise Error("prelude frame snapshot is incomplete")
 try: pixels=__import__("base64").b64decode(frame["pixels_base64"],validate=True)
 except Exception as exc: raise Error("prelude frame snapshot is invalid") from exc
 if len(pixels)!=32768 or hashlib.sha256(pixels).hexdigest()!=snapshot.get("frame_sha256") or frame.get("sha256")!=snapshot.get("frame_sha256"): raise Error("prelude frame digest differs")
 grid=snapshot["grid"]
 if any(not _int(level) or not 0<=level<=15 for level in grid) or hashlib.sha256(bytes(grid)).hexdigest()!=snapshot.get("grid_sha256"): raise Error("prelude grid digest differs")
 rle=snapshot.get("screen_rle")
 if not isinstance(rle,list) or any(not isinstance(row,list) or len(row)!=2 or not _int(row[0]) or not 0<=row[0]<=15 or not _int(row[1]) or row[1]<1 for row in rle) or sum(row[1] for row in rle)!=8192: raise Error("prelude screen RLE is invalid")
 if summary.get("source_identity_sha256") is None: raise Error("prelude source identity digest is missing")
 step=steps[0]
 sr={"id":scene["id"]}
 for k in ("behaviour_case","evidence"):
  if k in scene: sr[k]=scene[k]
 prefix=[{"step_id":step["id"],"inputs":step["inputs"]}]
 return {"contract_schema":"mosaic-native-transition-v4","transition_scope":"prelude","scene":sr,
  "from_prelude_receipt_id":alias,"prelude_receipt_sha256":receipt_sha,
  "prelude_chunk_sha256":chunk_sha,"prelude_frame_sha256":snapshot["frame_sha256"],
  "prelude_grid_sha256":snapshot["grid_sha256"],"prelude_source_identity_sha256":summary["source_identity_sha256"],
  "scene_input_prefix":prefix,"to_step":{k:step[k] for k in ("id","inputs","expect","output")}},summary

def _parameter_readout_context(project_root,scene):
 if not project_root: raise Error("parameter readout requires the source project root")
 evidence=scene.get("evidence",{})
 evidence_root=evidence.get("path")
 install=evidence.get("session_context",{}).get("experimental_install")
 install_sha=evidence.get("session_context",{}).get("installation_sha256")
 if not isinstance(evidence_root,str) or not evidence_root or not isinstance(install,str) or not isinstance(install_sha,str):
  raise Error("parameter readout lacks bound evidence and runtime installation identity")
 try:
  install_path=Path(install)
  raw_install=install_path.read_bytes()
  if hashlib.sha256(raw_install).hexdigest()!=install_sha: raise Error("parameter runtime installation digest differs")
  runtime=json.loads(raw_install.decode("utf-8"))
  source=runtime.get("source")
  if not isinstance(source,str) or not source: raise Error("parameter runtime source is missing")
  oracle_path=Path(project_root)/"tests"/"behaviour"/"frame_oracle.py"
  if not oracle_path.is_file(): raise Error("parameter pixel oracle is missing")
  behavior_dir=str(oracle_path.parent)
  sys.path.insert(0,behavior_dir)
  try:
   spec=importlib.util.spec_from_file_location("manual_parameter_frame_oracle",oracle_path)
   if spec is None or spec.loader is None: raise Error("parameter pixel oracle cannot be loaded")
   oracle=importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)
  finally:
   if sys.path and sys.path[0]==behavior_dir: sys.path.pop(0)
  return evidence_root,source,oracle
 except Error: raise
 except Exception as exc: raise Error("parameter pixel evidence context is unavailable") from exc

def _derive_parameter_receipt(native,req,actions,action_checkpoints,project_root):
 request=req.get("parameter_readout_equals")
 if request is None: return None
 from manual_parameter_readout import derive_parameter_readout_receipt,verify_action_link
 matches=[a for a in actions if a.get("kind")=="select-value" and a.get("field_label")==request.get("parameter_label") and a.get("value")==request.get("value")]
 if len(matches)!=1: raise Error("parameter readout request must bind exactly one authored select-value action")
 action=matches[0]
 checkpoint=next((row for row in action_checkpoints if row.get("action_id")==action.get("id")),None)
 if checkpoint is None: raise Error("parameter readout action lacks an ordered captured checkpoint")
 evidence_root,source,oracle=_parameter_readout_context(project_root,native.get("scene",{}))
 old_root=oracle.ROOT
 try:
  with tempfile.TemporaryDirectory(prefix="mosaic-parameter-readout-") as directory:
   root=Path(directory); (root/".runtime").mkdir()
   (root/".runtime"/"current.json").write_text(json.dumps({"source":source}),encoding="utf-8")
   oracle.ROOT=root
   oracle._font_state=None
   derived=derive_parameter_readout_receipt(native,request,action["id"],evidence_root=evidence_root,
     project_root=project_root,frame_oracle=oracle)
  verify_action_link(action,derived,checkpoint)
 finally:
  oracle.ROOT=old_root
  oracle._font_state=None
 receipt=derived["receipt"]
 checkpoint["parameter_readout_receipt"]=receipt
 return receipt

def _derive_mask_readout_receipts(native,source_scene,req,actions,project_root):
 masked=[action for action in actions if action.get("kind")=="select-value" and "mask_field" in action]
 target_masks=req.get("public_readout_equals",{}).get("mask_fields",[])
 target_assertion=_assertion(native)
 needs_target=target_masks if not (isinstance(target_assertion,dict) and isinstance(target_assertion.get("mask_fields"),list)) else []
 if not masked and not needs_target: return {"receipts":[],"by_step":{},"action_steps":{},"by_action":{}}
 scene=source_scene
 evidence_path=scene.get("evidence",{}).get("path")
 receipts=[]; by_step={}; action_steps={}
 steps=scene.get("steps",[])
 ids=[row.get("id") for row in steps if isinstance(row,dict)]
 from_id=native.get("from_step_id") or native.get("from_step",{}).get("id")
 to_id=native.get("to_step_id") or native.get("to_step",{}).get("id")
 if from_id not in ids or to_id not in ids or ids.index(from_id)>=ids.index(to_id):
  raise Error("Mask readout source scene does not contain the bound transition")
 interval=steps[ids.index(from_id)+1:ids.index(to_id)+1]
 wanted=[]
 for action in masked:
  wanted.append((action.get("id"),action.get("mask_field"),action.get("value")))
 for row in needs_target:
  if isinstance(row,dict): wanted.append((None,row.get("field"),row.get("value")))
 verified=[]
 for action_id,field,value in wanted:
  candidates=[]
  typed=[step for step in interval
         if isinstance(step.get("output",{}).get("binding",{}).get("assertion"),dict)
         and any(isinstance(item,dict) and item.get("field")==field and item.get("value")==value
                 for item in step["output"]["binding"]["assertion"].get("mask_fields",[]))]
  for step in interval:
   output=step.get("output",{}); binding=output.get("binding",{}) if isinstance(output,dict) else {}
   assertion=binding.get("assertion") if isinstance(binding,dict) else None
   expected=assertion.get("expected",{}) if isinstance(assertion,dict) else {}
   screen=expected.get("screen") if isinstance(expected,dict) else None
   if screen==[[field,value]] or (isinstance(assertion,dict) and assertion.get("screen")==[[field,value]]): candidates.append(step)
  if not candidates and action_id is not None and len(typed)==1:
   action_steps[action_id]=typed[0].get("id")
   continue
  if len(candidates)!=1:
   raise Error("Mask readout must resolve to one exact source-authored checkpoint in the transition")
  step_id=candidates[0].get("id")
  if (step_id,field,value) not in verified:
   if not project_root: raise Error("native Mask readout receipts require the source project root")
   if not isinstance(evidence_path,str) or not evidence_path: raise Error("native Mask readout requires the pinned scene evidence path")
   from manual_mask_public_readout import validate_current_scene
   from manual_publication_verify import verify_cached_ui
   pixel_verifier=lambda state,expected: verify_cached_ui(state,expected,Path(evidence_path))
   try:
    receipt=validate_current_scene(scene,step_id,field,value,pixel_verifier)
   except Exception as exc:
    raise Error("native Mask value/frame receipt failed: "+str(exc)) from exc
   receipt={**receipt,"purpose":"target-readout" if action_id is None else "select-value-action"}
   if action_id is not None: receipt["action_id"]=action_id
   receipts.append(receipt); verified.append((step_id,field,value))
   by_step.setdefault(step_id,[]).append({"field":field,"value":value,"layout":"overview_masks"})
  if action_id is not None: action_steps[action_id]=step_id
 by_action={receipt["action_id"]:receipt for receipt in receipts if "action_id" in receipt}
 return {"receipts":receipts,"by_step":by_step,"action_steps":action_steps,"by_action":by_action}

def build_teaching_contracts(book,scene_chunks,prelude_admissions=None,project_root=None):
 scenes,chapters,features=book.get("scenes"),book.get("learning_path",[]),book.get("features",[])
 if not isinstance(scenes,dict) or not isinstance(chapters,list) or not isinstance(features,list): raise Error("book scene/course/feature shape invalid")
 records=[]; ids=set()
 def add(cid,target,authored,allowed=None):
  if not isinstance(cid,str) or not cid or cid in ids: raise Error("teaching IDs must be unique and nonempty")
  if cid.startswith("feature:"):
   parts=cid.split(":")
   if len(parts)!=3 or any(not _SAFE_SLUG.fullmatch(part) for part in parts[1:]): raise Error("feature contract IDs must use safe route slugs")
  elif not _SAFE_SLUG.fullmatch(cid): raise Error("course stage IDs must use safe route slugs")
  if not isinstance(authored,dict) or set(authored)-{"from_step_id","from_prelude_receipt_id","transition_scope","actions","semantic_requires","human_outcome","practice_prompt","preserve_holds_at_target"} or not isinstance(target,dict) or target.get("status") not in ("verified","controlled-verified"): raise Error("teaching target/binding invalid")
  sid,to=target.get("scene"),target.get("step")
  if not isinstance(sid,str) or sid not in scenes or (allowed is not None and sid not in allowed): raise Error("target outside explicit scene scope")
  prelude_id=authored.get("from_prelude_receipt_id")
  if prelude_id is not None:
   if set(authored)&{"from_step_id","transition_scope"} or prelude_id!="getting-started-start" or not isinstance(prelude_admissions,dict) or prelude_id not in prelude_admissions: raise Error("prelude needs the separately admitted native receipt and no synthetic from-step")
   native,prelude_summary=_native_prelude(scenes[sid],to,prelude_admissions[prelude_id]); scope="prelude"; fr=None
  else:
   fr=authored.get("from_step_id")
   if not isinstance(fr,str) or not fr: raise Error("teaching needs a real captured from_step_id")
   scope=authored.get("transition_scope","adjacent"); native=_native(scenes[sid],fr,to,scope); prelude_summary=None
  req=authored.get("semantic_requires"); _validate_semantics(req)
  mask_data=_derive_mask_readout_receipts(native,scenes[sid],req,authored["actions"],project_root)
  _validate_output(native,req,mask_data["by_step"].get(to))
  if not validate_semantics(native,req): raise Error("v7 screen/MIDI/held semantics mismatch")
  held= replay_held_controls(native)
  if held and ("held_controls_at_target" not in req or authored.get("preserve_holds_at_target") is not True): raise Error("held target must declare exact held controls and preserve_holds_at_target")
  if not held and authored.get("preserve_holds_at_target",False) is not False: raise Error("empty final held state requires preserve_holds_at_target:false or omission")
  action_checkpoints=_validate_actions(authored,native,to,req,mask_data["action_steps"])
  for checkpoint in action_checkpoints:
   receipt=mask_data["by_action"].get(checkpoint.get("action_id"))
   if receipt is not None:
    checkpoint["mask_readout_receipt"]=receipt
    checkpoint["proof"]["receipt_kind"]=receipt["kind"]
  parameter_receipt=_derive_parameter_receipt(native,req,authored["actions"],action_checkpoints,project_root)
  if parameter_receipt is not None:
   native["parameter_readout_receipts"]=[parameter_receipt]
  if mask_data["receipts"]: native["mask_readout_receipts"]=mask_data["receipts"]
  outcome=authored.get("human_outcome")
  if "project_files_at_target" in req:
   assertion=_assertion(native)
   if not isinstance(assertion,dict) or not isinstance(outcome,str) or not outcome.startswith("Saved "+assertion.get("name","")):
    raise Error("saved-project human outcome must name the captured project")
  if not isinstance(outcome,str) or not outcome.strip() or outcome.strip().casefold() in {"ok","success","passed","done","completed","it works"}: raise Error("human_outcome must be concrete")
  prompt=authored.get("practice_prompt")
  if prompt is not None and (not isinstance(prompt,str) or not prompt.strip()): raise Error("practice_prompt must be nonempty supporting prose")
  ref=scene_chunks.get(sid); sha=ref.get("sha256") if isinstance(ref,dict) else None
  if not isinstance(sha,str) or not re.fullmatch(r"[0-9a-f]{64}",sha): raise Error("scene chunk digest is missing or invalid")
  digest=(native_transition_hash_prelude(native) if scope=="prelude" else native_transition_hash_v8(native) if scope=="interval" else native_transition_hash(native))
  binding={"contract_id":cid,"owner_type":("feature" if cid.startswith("feature:") else "course-stage"),
   "scene_id":sid,"to_step_id":to,"transition_scope":scope,
   "native_transition_contract_sha256":digest,"scene_chunk_sha256":sha,
   "semantic_verified":True,"semantic_requires":req,"actions":authored["actions"],
   "action_checkpoints":action_checkpoints,"human_outcome":outcome}
  _export_native_receipts(native,binding)
  if scope=="prelude":
   binding["from_prelude_receipt_id"]=prelude_id
   binding["prelude_receipt_sha256"]=native["prelude_receipt_sha256"]
   binding["prelude_chunk_sha256"]=native["prelude_chunk_sha256"]
  else:
   binding["from_step_id"]=fr
  if cid.startswith("feature:"):
   _,feature_id,lesson_id=cid.split(":",2); binding["feature_id"]=feature_id; binding["lesson_id"]=lesson_id
  else: binding["course_stage_id"]=cid
  binding["preserve_holds_at_target"]=bool(held)
  if prompt is not None: binding["practice_prompt"]=prompt
  ids.add(cid); records.append((cid,sid,native,binding))
 for ch in chapters:
  if not isinstance(ch,dict) or not isinstance(ch.get("stages",[]),list): raise Error("course stages malformed")
  for st in ch.get("stages",[]):
   if not isinstance(st,dict): raise Error("course stage malformed")
   if st.get("teaching_binding") is not None: add(st.get("id"),st.get("binding"),st["teaching_binding"])
 for f in features:
  if not isinstance(f,dict): raise Error("feature malformed")
  fid,lessons,refs=f.get("id"),f.get("teaching_bindings",[]),f.get("scene_refs",[])
  if not isinstance(fid,str) or not fid or not isinstance(lessons,list) or not isinstance(refs,list): raise Error("feature teaching scope malformed")
  allowed=set()
  for ref in refs:
   sid=ref if isinstance(ref,str) else ref.get("id") if isinstance(ref,dict) else None
   if not isinstance(sid,str) or sid not in scenes: raise Error("feature has invalid scene_refs")
   allowed.add(sid)
  lids=set()
  for lesson in lessons:
   if not isinstance(lesson,dict) or not isinstance(lesson.get("id"),str) or not _SAFE_SLUG.fullmatch(lesson["id"]) or lesson["id"] in lids: raise Error("feature lesson IDs must be unique safe route slugs")
   lids.add(lesson["id"]); add("feature:{}:{}".format(fid,lesson["id"]),lesson.get("binding"),lesson.get("teaching_binding"),allowed)
 result={}; groups={}
 for cid,sid,native,b in records:
  group=("feature:"+cid.split(":",2)[1]) if cid.startswith("feature:") else "course"
  groups.setdefault(group,[]).append((cid,sid,native,b))
 for group in groups.values():
  for cid,sid,native,b in group:
   if b["transition_scope"]=="adjacent":
    candidates=[x[3] for x in group if x[1]==sid]
    if not validate_binding(b,native,candidates): raise Error("native adjacent binding stale/ambiguous: "+cid)
   elif b["transition_scope"]=="interval":
    if native_transition_hash_v8(native)!=b["native_transition_contract_sha256"] or native["transition_scope"]!="interval" or native["from_step_id"]!=b["from_step_id"] or native["to_step_id"]!=b["to_step_id"]: raise Error("native interval binding stale: "+cid)
   elif native_transition_hash_prelude(native)!=b["native_transition_contract_sha256"] or native["transition_scope"]!="prelude" or native["from_prelude_receipt_id"]!=b["from_prelude_receipt_id"] or native["prelude_receipt_sha256"]!=b["prelude_receipt_sha256"]: raise Error("native prelude binding stale: "+cid)
   result[cid]=b
 return result
def validate_teaching_contracts(book,scene_chunks,supplied,project_root=None):
 expected=build_teaching_contracts(book,scene_chunks,project_root=project_root)
 if supplied!=expected: raise Error("teaching contract map stale, missing, extra or altered")
 return expected
