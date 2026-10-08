"""Case-derived manual scenes: explicit semantic checkpoints, never arbitrary screenshots."""
import argparse, base64, contextlib, copy, hashlib, json, os, sys, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def trace_hash(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def persist_case_scenes(out,scenes):
 # A later case failure must not discard completed frames or exact requested waits.
 with (out/"captured-scenes.json").open("x") as target:
  target.write(json.dumps(scenes,indent=2)+"\n")
def validate_derived_inputs(root,selected_ids):
 import yaml
 for path in (root/"manual/features").glob("scenes-*.yaml"):
  derived=yaml.safe_load(path.read_text())
  if derived.get("fixture_kind")!="behaviour-case":continue
  relevant=[scene for scene in derived.get("scenes",[]) if scene["id"] in selected_ids]
  if not relevant:continue
  raw=root/"manual/generated"/(path.stem[len("scenes-"):]+".json")
  if not raw.is_file():raise ValueError("Derived inputs lack their captured publication: "+str(path))
  originals={scene["id"]:scene for scene in json.loads(raw.read_text())["scenes"]}
  for scene in relevant:
   original=originals.get(scene["id"])
   if original is None:raise ValueError("Derived inputs lack their captured scene: "+scene["id"])
   expected={step["id"]:step["inputs"] for step in original["steps"]}
   actual={step["id"]:step["inputs"] for step in scene["steps"]}
   if trace_hash(actual)!=trace_hash(expected):raise ValueError("Derived inputs changed: "+str(path)+" / "+scene["id"]+"; edit canonical case inputs or an independent replay recipe, then explicitly regenerate the capture.")
def reconcile_transport(c,row):
 # Protected stop gestures can be ignored: successful player-visible oracles
 # supersede the convenience tap-toggle estimate before cleanup.
 if row.get("kind")=="stop-safety" and row.get("passed") is True and row.get("transport") in ("playing","stopped"):
  c.manual_transport_on=row["transport"]=="playing"
class Selector:
 def __init__(self,match,occurrence=1,alternatives=None):self.match=match;self.matches=[match]+list(alternatives or []);self.matched=None;self.occurrence=occurrence;self.seen=0
 def accept(self,row):
  matches=[match for match in self.matches if all(json.loads(json.dumps(row.get(k)))==json.loads(json.dumps(v)) for k,v in match.items())]
  if not matches:return False
  self.matched=matches[0]
  if row.get("passed") is False or row.get("matched") is False:raise ValueError("Checkpoint failed")
  self.seen+=1
  return self.seen==self.occurrence
def step_midi(midi,previous_index,clock_mode):
 """Channel messages emitted after previous_index, with ms relative to the first one.
 Clock/realtime bytes (>=0xF8) are omitted; truncated is True when the observed tail
 no longer reaches back to previous_index."""
 key="logical_ns" if clock_mode=="controlled-experimental" else "monotonic_ns"
 rows=[m for m in midi if m["index"]>previous_index]
 truncated=bool(rows) and rows[0]["index"]>previous_index+1
 last=max([m["index"] for m in midi]+[previous_index])
 channel=[m for m in rows if m["bytes"] and 0x80<=m["bytes"][0]<0xF0]
 start=channel[0][key] if channel else 0
 return [dict(port=m["port"],bytes=list(m["bytes"]),ms=round((m[key]-start)/1e6,3)) for m in channel],last,truncated
class DeferredFrames:
 def __init__(self):self.saved={}
 def store(self,key,output,trace):self.saved[key]=(copy.deepcopy(output),copy.deepcopy(trace))
 def bind(self,key,assertion,index):
  if assertion.get("passed") is False or assertion.get("matched") is False:raise ValueError("Final oracle failed")
  if key not in self.saved:raise ValueError("No explicitly captured live final frame")
  output,trace=copy.deepcopy(self.saved[key])
  output["binding"].update(capture_stage="before-finish",assertion_index=index,assertion=assertion,assertion_sha256=trace_hash(assertion),trace_sha256=trace_hash(trace))
  return output,trace
class TraceCursors:
 def __init__(self):self.positions={}
 def take(self,owner,trace):
  start=self.positions.get(owner,0);self.positions[owner]=len(trace)
  return trace[start:]
def group_plans(plans):
 groups={}
 for plan in plans:groups.setdefault((plan["behaviour_case"],plan.get("profile","base-midi")),[]).append(plan)
 return list(groups.values())
@contextlib.contextmanager
def freeze_child_drivers(modules,original,app_root,factory=None):
 affected=[m for m in modules if getattr(m,"Driver",None) is original]
 def frozen(*args,**kwargs):
  kwargs.setdefault("app_root",app_root)
  return (factory or original)(*args,**kwargs)
 for module in affected:module.Driver=frozen
 try:yield
 finally:
  for module in affected:module.Driver=original
def participant_options(kwargs,contract):
 result=dict(kwargs)
 for field,expected in contract.items():
  actual=result.setdefault(field,expected)
  equivalent=(Path(actual).resolve()==Path(expected).resolve()) if field in ("app_root","experimental_install") and actual is not None and expected is not None else actual==expected
  if not equivalent:raise ValueError("Nested participant differs in "+field)
 return result
def scene_session_ordinal(plan):
 if "session_ordinal" in plan and any(step.get("session_ordinal",plan["session_ordinal"])!=plan["session_ordinal"] for step in plan["steps"]):raise ValueError("Ambiguous scene and step participant")
 values={step.get("session_ordinal",plan.get("session_ordinal",0)) for step in plan["steps"]}
 if len(values)!=1:raise ValueError("A scene must bind one participant")
 return values.pop()
class ParticipantState:
 def __init__(self,ordinal):
  self.ordinal=ordinal;self.trace=[];self.held={};self.cursors=TraceCursors();self.deferred=DeferredFrames()
 def record(self,value):
  if value["type"]!="advance":self.trace.append(dict(value))
  if value["type"] in ("grid","key"):
   ident=(value["type"],value.get("n"),value.get("x"),value.get("y"))
   if value.get("state"):self.held[ident]=value
   else:self.held.pop(ident,None)
def finish_participants(participants,close,write):
 errors=[]
 for participant,state,selectors in reversed(participants):
  try:
   if not getattr(participant,"finished",False):close(participant,state.held)
   elif state.held:raise AssertionError("Participant finished with held inputs")
  except Exception as error:errors.append(error)
  finally:
   try:
    if not getattr(participant,"finished",False):participant.finish()
   except Exception as error:errors.append(error)
   finally:
    # Preserve late outer summaries without touching child result provenance.
    write(participant.out/"results.json",participant.results)
    write(participant.out/"capture-trace.json",state.trace)
 if errors:raise errors[0]
def load_extra_cases(paths,base,root=ROOT):
 import re,types
 registry=dict(base);blobs={};modules=[]
 tools=(root/"tools").resolve();resolved=[]
 for value in paths:
  path=Path(value);path=path if path.is_absolute() else root/path;path=path.resolve()
  try:path.relative_to(tools)
  except ValueError:raise ValueError("Extra cases must be Python source under ROOT/tools")
  if path.suffix!=".py":raise ValueError("Extra cases must be Python source under ROOT/tools")
  relative=str(path.relative_to(root.resolve()))
  if relative in resolved:raise ValueError("Duplicate extra-case source")
  resolved.append(relative);blob=path.read_bytes();blobs[relative]=blob
 for relative,blob in blobs.items():
  module=types.ModuleType("manual_extra_"+hashlib.sha256(blob).hexdigest());module.__file__=str(root/relative)
  exec(compile(blob,module.__file__,"exec"),module.__dict__)
  entries=getattr(module,"CASES",None)
  if not isinstance(entries,dict) or not entries:raise ValueError("Extra source must export nonempty CASES")
  for key,entry in entries.items():
   if not isinstance(key,str) or not re.fullmatch(r"M-[A-Z0-9]+(?:-[A-Z0-9]+)*",key):raise ValueError("Invalid extra-case ID")
   if key in registry:raise ValueError("Duplicate case ID: "+key)
   if not isinstance(entry,dict) or not callable(entry.get("run")) or not isinstance(entry.get("requirements"),list) or not entry["requirements"] or any(not isinstance(v,str) or not v for v in entry["requirements"]) or not isinstance(entry.get("description"),str) or not entry["description"]:raise ValueError("Invalid extra-case entry: "+key)
   registry[key]=dict(entry)
  modules.append(module)
 for module in modules:sys.modules[module.__name__]=module
 return registry,blobs
def case_source_paths(root,plans):
 paths=[v for v in (root/"tests/behaviour").rglob("*.py") if not v.name.startswith("test_") and v.name not in ("suite.py","run.py")]
 # Stock Lua canonical oracle is selected only for the supplementary save case.
 if any(v["behaviour_case"]=="M-MANUAL-SAVE-DIALOG-001" for v in plans):paths.append(root/"tests/behaviour/persisted_digest.lua")
 return paths
def persist_start_sources(run,blobs,metadata=None):
 # Reserve the receipt before writing any source, preventing a failed retry from
 # replacing a run's original identity. Every map is derived from these bytes.
 receipt=dict(metadata or {},**{kind:{name:hashlib.sha256(blob).hexdigest() for name,blob in entries.items()} for kind,entries in blobs.items()})
 for entries in blobs.values():
  for name in entries:
   relative=Path(name)
   if relative.is_absolute() or ".." in relative.parts:raise ValueError("Source path must stay inside its snapshot")
 with (run/"start-source-identity.json").open("x") as target:
  target.write(json.dumps(receipt,indent=2)+"\n");target.flush()
  for kind,folder in (("case_sources","case-source"),("fixture_sources","fixture-source"),("capture_sources","capture-source"),("plan_files","plan-source")):
   for name,blob in blobs[kind].items():
    relative=Path(name)
    if relative.is_absolute() or ".." in relative.parts:raise ValueError("Source path must stay inside its snapshot")
    frozen=run/folder/relative;frozen.parent.mkdir(parents=True,exist_ok=True)
    with frozen.open("xb") as source:source.write(blob)
 return receipt
def capture_group(plans,out,options):
 sys.path.insert(0,str(ROOT/"tools"));sys.path.insert(0,str(ROOT/"tests/behaviour"))
 from manual_capture import tracked_driver,frame,close
 from manual_screen_codec import encode_native_frame
 from driver import digest,Driver,write
 from cases import CASES
 CASES=getattr(options,"case_registry",CASES)
 case=plans[0]["behaviour_case"];profile=plans[0].get("profile","base-midi")
 frames={plan["id"]:[] for plan in plans};participants=[]
 def capture_plan_frame(c,plan,key):
  if plan.get("screen_format")!="gray8-rle":return frame(c,case,key)
  state=c.snapshot();rgba=base64.b64decode(state["frame"]["pixels_base64"],validate=True)
  payload=encode_native_frame(rgba);grid=state["grid"]
  from manual_model import validate_capture
  validate_capture(dict(levels=[0]*8192,grid=grid))
  frame_sha=hashlib.sha256(rgba).hexdigest()
  if frame_sha!=state["frame"]["sha256"]:raise ValueError("Native framebuffer hash mismatch")
  record=dict(kind="documentation-frame",name="manual/"+case+"/"+key,sha256=frame_sha,stable_rows=55,
      stable_sha256=hashlib.sha256(rgba[:128*55*4]).hexdigest(),grid_sha256=hashlib.sha256(bytes(grid)).hexdigest(),
      semantic_assertions=len(c.results),passed=True)
  c.results.append(record)
  return dict(payload,grid=grid,binding=record)
 contract=dict(clock_mode=options.clock_mode,experimental_install=options.experimental_install,app_root=options.app_root,profile=profile)
 def install(c,ordinal):
  selectors=[(plan,step,Selector(step["assertion"],step.get("occurrence",1),step.get("assertion_alternatives"))) for plan in plans if scene_session_ordinal(plan)==ordinal for step in plan["steps"]]
  state=ParticipantState(ordinal);trace=state.trace;held=state.held;cursors=state.cursors;deferred=state.deferred;busy=False;saved_rows={};final_captured=False
  midi_cursor={};before_midi=0
  participants.append((c,state,selectors))
  action=c.action;elapse=c.elapse
  def tracked_action(**value):
   state.record(value)
   return action(**value)
  def tracked_elapse(seconds):
   if seconds:trace.append(dict(type="wait",seconds=seconds))
   return elapse(seconds)
  c.action=tracked_action;c.elapse=tracked_elapse
  class Results(list):
   def append(self,row):
    nonlocal busy
    super().append(row)
    reconcile_transport(c,row)
    if busy:return
    assertion_index=len(self)-1
    for plan,step,selector in selectors:
     if selector.accept(row):
      # Steps bind in plan order; an earlier unbound step means identical selectors lack occurrence: ordinals.
      earlier=[s["id"] for s in plan["steps"][:plan["steps"].index(step)] if s.get("capture_stage")!="before-finish" and not any(v["id"]==s["id"] for v in frames[plan["id"]])]
      if step.get("capture_stage")!="before-finish" and earlier:raise ValueError("Checkpoint order: %s/%s bound before %s; check occurrence: on repeated selectors (tools/manual_plan_lint.py)"%(plan["id"],step["id"],earlier))
      busy=True
      try:
       key=plan["id"]+"/"+step["id"]
       if step.get("capture_stage")=="before-finish":
        output,delta=deferred.bind(key,row,assertion_index)
       else:
        delta=cursors.take(plan["id"],trace)
        output=capture_plan_frame(c,plan,key)
        events,midi_cursor[plan["id"]],truncated=step_midi(c.observations[-1]["state"].get("midi",[]),midi_cursor.get(plan["id"],before_midi),c.clock_mode)
        output["midi"]=dict(events=events[:512],total=len(events),truncated=truncated or len(events)>512)
       binding=dict(assertion_index=assertion_index,assertion=row,assertion_sha256=trace_hash(row),trace_sha256=trace_hash(delta))
       output["binding"].update(binding,session_ordinal=ordinal)
       if step.get("capture_stage")=="before-finish":saved_rows[key].update(output["binding"])
       frames[plan["id"]].append(dict(id=step["id"],title=step["title"],caption=step["caption"],citation=plan["citation"],inputs=delta,expect=dict(assertion=selector.matched,**({"pre_finish_expect":step["pre_finish_expect"]} if step.get("capture_stage")=="before-finish" else {})),output=output))
      finally:busy=False
  c.results=Results(c.results)
  original_finish=c.finish
  def finish_with_final_frames():
   nonlocal busy,final_captured
   if final_captured or getattr(c,"finished",False):return original_finish()
   final_captured=True;busy=True
   try:
    for plan,step,selector in selectors:
     if step.get("capture_stage")!="before-finish":continue
     key=plan["id"]+"/"+step["id"];expected=step["pre_finish_expect"];pre_start=len(c.results)
     if "header" in expected:c.ui.expect_header(expected["header"]["page"],**expected["header"].get("params",{}))
     if "field" in expected:c.ui.expect_selected_field(**expected["field"])
     if "menu" in expected:c.ui.expect_menu_option_row(**expected["menu"])
     if "menu_label" in expected:c.ui.expect_menu_label(**expected["menu_label"])
     if "menu_value" in expected:c.ui.expect_menu_value(**expected["menu_value"])
     pre_indices=list(range(pre_start,len(c.results)))
     output=capture_plan_frame(c,plan,key);output["binding"].update(capture_stage="before-finish",pre_finish_expect=copy.deepcopy(expected),pre_finish_assertion_indices=pre_indices);saved_rows[key]=output["binding"]
     deferred.store(key,output,cursors.take(plan["id"],trace))
   finally:
    busy=False;original_finish()
  c.finish=finish_with_final_frames
  return c
 def child_factory(*args,**kwargs):
  kwargs=participant_options(kwargs,contract)
  child=tracked_driver(*args,**kwargs)
  try:
   participant_options(dict(clock_mode=child.clock_mode,experimental_install=child.launch_options.get("experimental_install"),app_root=child.app_root,profile=child.profile),contract)
   return install(child,len(participants))
  except Exception:
   child.finish();raise
 c=install(tracked_driver(out,**contract,mod_code_root=options.mod_code_root,mod_patches=options.mod_patches and profile=="midi-modulation"),0)
 try:
  case_modules=[m for m in tuple(sys.modules.values()) if m and getattr(m,"__file__",None) and str(getattr(m,"__file__")).startswith(str(ROOT/"tests/behaviour")) and getattr(m,"__name__",None)!="driver"]
  case_modules.extend(m for m in tuple(sys.modules.values()) if m and getattr(m,"__file__",None) in getattr(options,"extra_case_files",[]))
  with freeze_child_drivers(case_modules,Driver,options.app_root,child_factory):CASES[case]["run"](c)
  missing=[plan["id"]+"/"+step["id"] for plan in plans for step in plan["steps"] if not any(v["id"]==step["id"] for v in frames[plan["id"]])]
  if missing:
   # A row changed after append never reached the binding hook; name that cause.
   rows=[row for participant,_,_ in participants for row in participant.results if row.get("passed") is not False and row.get("matched") is not False]
   late=[plan["id"]+"/"+step["id"] for plan in plans for step in plan["steps"] if plan["id"]+"/"+step["id"] in missing and any(Selector(step["assertion"],1,step.get("assertion_alternatives")).accept(row) for row in rows)]
   raise ValueError("Missing checkpoints: "+str(missing)+("; rows matching %s exist only after being changed post-append"%late if late else ""))
 finally:
  finish_participants(participants,close,write)
 evidence=[]
 outer_identity=json.loads((out/"native/identity.json").read_text())
 for participant,state,selectors in participants:
  folder=participant.out;identity=json.loads((folder/"native/identity.json").read_text());config=json.loads((folder/"native/native-config.json").read_text())
  if config["clock_mode"]!=options.clock_mode:raise ValueError("Native participant clock mismatch")
  if identity["runtime_identity"]!=outer_identity["runtime_identity"]:raise ValueError("Native participant runtime identity mismatch")
  files=lambda value:{v["path"]:v["sha256"] for v in value["application_identity"]["files"] if v["path"].startswith("mosaic/")}
  if files(identity)!=files(outer_identity):raise ValueError("Native participant application identity mismatch")
  context=dict(session_ordinal=state.ordinal,clock_mode=participant.clock_mode,profile=participant.profile,app_root=str(participant.app_root),experimental_install=participant.launch_options.get("experimental_install"),installation_sha256=digest(Path(options.experimental_install)) if options.experimental_install else None,session_id=identity["session_id"],runtime_identity_sha256=trace_hash(identity["runtime_identity"]),application_identity_sha256=trace_hash(files(identity)),finished=participant.finished,held_inputs=[],cleanup_verified=True)
  write(folder/"session-context.json",context)
  evidence.append(dict(path=str(folder),session_context=context,**{name.replace("-","_")+"_sha256":digest(folder/relative) for name,relative in (("results","results.json"),("identity","native/identity.json"),("recipe","recipe.json"),("native-events","native/native-events.jsonl"),("capture-trace","capture-trace.json"),("session-context","session-context.json"),("native-config","native/native-config.json"),("cleanup","native/cleanup.json"))}))
 write(out/"case-participants.json",evidence)
 return [dict(id=plan["id"],feature_id=plan["feature_id"],title=plan["title"],behaviour_case=case,requirements=CASES[case]["requirements"],profile=profile,session_ordinal=scene_session_ordinal(plan),**({"screen_format":plan["screen_format"]} if plan.get("screen_format") else {}),setup=dict(fixture="behaviour-case",case=case,input_units="native; encoder units are twice the detents"),steps=frames[plan["id"]],evidence=dict(evidence[scene_session_ordinal(plan)],case_participants=evidence,case_participants_path=str(out/"case-participants.json"),case_participants_sha256=digest(out/"case-participants.json"))) for plan in plans]

def report_document(source,clock_mode,scenes,evidence,selected_scene_ids,controlled_local=False):
 if controlled_local and clock_mode!="controlled-experimental":raise ValueError("Controlled-local report requires controlled-experimental time")
 document=dict(schema_version=1,source=source,clock_mode=clock_mode,scenes=scenes,evidence=str(evidence),complete_regression_run=False,selected_scene_ids=selected_scene_ids)
 if controlled_local:document.update(validation_scope="controlled-manual-generation",realtime_qualification="pending-ci")
 return document

def main():
 import fcntl,shutil,yaml
 p=argparse.ArgumentParser()
 p.add_argument("--extra-cases",action="append",default=[]);p.add_argument("--plans",action="append");p.add_argument("--clock-mode",default="controlled-experimental");p.add_argument("--experimental-install")
 p.add_argument("--scene",action="append");p.add_argument("--profile",action="append");p.add_argument("--mod-code-root");p.add_argument("--mod-patches",action="store_true")
 p.add_argument("--publish",action="store_true");p.add_argument("--controlled-local",action="store_true",help="Mark controlled captures as manual-generation evidence pending REAL qualification in CI");p.add_argument("--output",default="reference-scenes.json");p.add_argument("--output-root",type=Path,default=Path("/home/andy/mosaic-manual-runs"));a=p.parse_args()
 if Path(a.output).name!=a.output or not a.output.endswith(".json"):raise ValueError("Output must be a local JSON filename")
 plan_paths=[Path(v).resolve() for v in a.plans] if a.plans else sorted((ROOT/"manual").glob("scene-plans*.yaml"))
 plan_blobs={str(v.relative_to(ROOT)):v.read_bytes() for v in plan_paths}
 import jsonschema
 schema=json.loads((ROOT/"manual/case-scenes.schema.json").read_text())
 for blob in plan_blobs.values():jsonschema.Draft7Validator(schema).validate(yaml.safe_load(blob))
 plan_files={relative:hashlib.sha256(blob).hexdigest() for relative,blob in plan_blobs.items()}
 plan_sha=next(iter(plan_files.values())) if len(plan_files)==1 else trace_hash(plan_files)
 plans=[v for blob in plan_blobs.values() for v in yaml.safe_load(blob)["scenes"]]
 plans=[v for v in plans if (not a.scene or v["id"] in a.scene) and (not a.profile or v.get("profile","base-midi") in a.profile)]
 if not plans or len({v["id"] for v in plans})!=len(plans):raise ValueError("Empty selection or duplicate scene IDs")
 validate_derived_inputs(ROOT,{v["id"] for v in plans})
 for plan in plans:scene_session_ordinal(plan)
 if any(v.get("profile","base-midi")!="base-midi" for v in plans) and not a.mod_code_root:raise ValueError("Selected modulation scenes require explicit --mod-code-root")
 sys.path.insert(0,str(ROOT/"tools"));sys.path.insert(0,str(ROOT/"tests/behaviour"))
 import manual_capture,manual_model,cases
 a.case_registry,extra_blobs=load_extra_cases(a.extra_cases,cases.CASES)
 a.extra_case_files=[str(ROOT/relative) for relative in extra_blobs]
 if any(plan["behaviour_case"] not in a.case_registry for plan in plans):raise ValueError("Unknown selected case")
 source_paths=case_source_paths(ROOT,plans)
 case_blobs={str(v.relative_to(ROOT)):v.read_bytes() for v in source_paths}
 fixture_blobs={str(v.relative_to(ROOT)):v.read_bytes() for v in (ROOT/"tests/behaviour/config").rglob("*") if v.is_file()}
 helper_blobs={str(v.relative_to(ROOT)):v.read_bytes() for v in [ROOT/"tools/manual_capture.py",ROOT/"tools/manual_model.py",ROOT/"tools/manual_screen_codec.py",ROOT/"manual/case-scenes.schema.json",ROOT/"manual/screen-output.schema.json",Path(__file__).resolve()]}
 helper_blobs.update(extra_blobs)
 output_root=a.output_root.resolve();output_root.mkdir(parents=True,exist_ok=True);run=output_root/uuid.uuid4().hex;run.mkdir();a.app_root=run/"application"
 start=persist_start_sources(run,dict(plan_files=plan_blobs,case_sources=case_blobs,fixture_sources=fixture_blobs,capture_sources=helper_blobs),dict(schema_version=1,plans_sha256=plan_sha,adapter_sha256=hashlib.sha256(helper_blobs["tools/manual_case_capture.py"]).hexdigest(),clock_mode=a.clock_mode,selected_scene_ids=[v["id"] for v in plans],extra_case_files=list(extra_blobs)))
 source_hashes=start["case_sources"];fixture_sources=start["fixture_sources"];helper_sources=start["capture_sources"]
 source={key:start[key] for key in ("plans_sha256","plan_files","adapter_sha256","case_sources","capture_sources","fixture_sources")}
 source.update(start_source_identity_path=str(run/"start-source-identity.json"),start_source_identity_sha256=hashlib.sha256((run/"start-source-identity.json").read_bytes()).hexdigest(),extra_case_files=start["extra_case_files"])
 shutil.copytree(ROOT/"lib",a.app_root/"lib",ignore=shutil.ignore_patterns(".git","tests","__pycache__"))
 shutil.copytree(ROOT/"docs/ui-reimplementation",a.app_root/"docs/ui-reimplementation");shutil.copy(ROOT/"mosaic.lua",a.app_root/"mosaic.lua")
 lock=open("/tmp/mosaic-manual-native.lock","a")
 with lock:
  fcntl.flock(lock,fcntl.LOCK_EX);results=[]
  for group in group_plans(plans):
   case=group[0]["behaviour_case"];out=run/(case+"-"+group[0].get("profile","base-midi"));out.mkdir()
   try:
    captured=capture_group(group,out,a);persist_case_scenes(out,captured);results.extend(captured)
   except Exception as error:
    (run/"failure.json").write_text(json.dumps(dict(scenes=[v["id"] for v in group],clock_mode=a.clock_mode,passed=False,error=repr(error),source=source,**{key:start[key] for key in ("plans_sha256","plan_files","case_sources","capture_sources","fixture_sources")}),indent=2)+"\n");print("Failure evidence",run,flush=True);raise
   print("Verified",case,"/"," ".join(v["id"] for v in group),flush=True)
 if any(hashlib.sha256(v.read_bytes()).hexdigest()!=source_hashes[str(v.relative_to(ROOT))] for v in source_paths):raise ValueError("Behaviour source changed during capture")
 document=report_document(source,a.clock_mode,results,run,[v["id"] for v in plans],controlled_local=a.controlled_local)
 (run/"reference-scenes.json").write_text(json.dumps(document,indent=2)+"\n")
 if a.publish:
  target=ROOT/"manual/generated"/a.output;temp=target.with_suffix(".json.tmp");temp.write_text(json.dumps(document,indent=2)+"\n");temp.replace(target)
  authored=dict(schema_version=1,fixture_kind="behaviour-case",trace_contract="The original pinned case replays public inputs and verifies every authored semantic selector; per-scene deltas include native encoder units and waits.",scenes=[{k:v for k,v in s.items() if k not in ("evidence",)} for s in results])
  for scene in authored["scenes"]:
   for step in scene["steps"]:step.pop("output")
  (ROOT/"manual/features"/("scenes-"+Path(a.output).stem+".yaml")).write_text(yaml.safe_dump(authored,sort_keys=False))
 print(run,flush=True)
if __name__=="__main__":main()
