"""Acceptance for explicit semantic checkpoint selection (README Norns Menu Navigation)."""
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("manual_case_capture",ROOT/"tools/manual_case_capture.py")
class Checkpoints(unittest.TestCase):
 def test_exact_subset_and_occurrence(self):
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  selector=module.Selector({"kind":"selected-field","label":"Trig mode","value":"ALL"},2)
  self.assertFalse(selector.accept({"kind":"selected-field","label":"Trig mode","value":"ONLY","matched":True}))
  self.assertFalse(selector.accept({"kind":"selected-field","label":"Trig mode","value":"ALL","matched":True}))
  self.assertTrue(selector.accept({"kind":"selected-field","label":"Trig mode","value":"ALL","matched":True}))
 def test_unverified_result_is_rejected(self):
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with self.assertRaises(ValueError):module.Selector({"kind":"midi"},1).accept({"kind":"midi","passed":False})
 def test_trace_identity_includes_waits(self):
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  self.assertNotEqual(module.trace_hash([{"type":"wait","seconds":.3}]),module.trace_hash([{"type":"wait","seconds":.4}]))
 def test_shared_case_keeps_independent_scene_traces(self):
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  traces=module.TraceCursors()
  self.assertEqual(traces.take("a",[1,2]),[1,2])
  self.assertEqual(traces.take("b",[1,2,3]),[1,2,3])
  self.assertEqual(traces.take("a",[1,2,3,4]),[3,4])
 def test_groups_share_case_but_keep_profiles_separate(self):
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  groups=module.group_plans([dict(id="a",behaviour_case="X"),dict(id="b",behaviour_case="X"),dict(id="c",behaviour_case="X",profile="midi-modulation")])
  self.assertEqual([[p["id"] for p in g] for g in groups],[["a","b"],["c"]])
 def test_child_sessions_inherit_frozen_application_and_restore_constructor(self):
  import types
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  def original(**kwargs):return kwargs
  case=types.SimpleNamespace(Driver=original)
  with module.freeze_child_drivers([case],original,"/frozen"):
   self.assertEqual(case.Driver(clock_mode="real-time"),dict(clock_mode="real-time",app_root="/frozen"))
   self.assertEqual(case.Driver(app_root="/explicit"),dict(app_root="/explicit"))
  self.assertIs(case.Driver,original)
 def test_yaml_sequences_match_native_json_sequences_exactly(self):
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  selector=module.Selector({"kind":"midi","notes":[[60,80],[62,70]]})
  self.assertTrue(selector.accept({"kind":"midi","notes":[(60,80),(62,70)],"passed":True}))
  different=module.Selector({"kind":"midi","notes":[[60,80],[62,70]]})
  self.assertFalse(different.accept({"kind":"midi","notes":[(60,80),(62,71)],"passed":True}))
 def test_final_frame_requires_successful_later_oracle_and_preserves_stage(self):
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  frames=module.DeferredFrames();frames.store("cc",{"grid":[1],"binding":{"sha256":"native"}},[{"type":"enc","n":3,"delta":2}])
  with self.assertRaises(ValueError):frames.bind("cc",{"kind":"cc","passed":False},9)
  output,trace=frames.bind("cc",{"kind":"cc","passed":True,"value":64},10)
  self.assertEqual(output["binding"]["capture_stage"],"before-finish")
  self.assertEqual(output["binding"]["assertion_index"],10)
  self.assertEqual(output["binding"]["sha256"],"native")
  self.assertEqual(trace,[{"type":"enc","n":3,"delta":2}])
 def test_completed_case_is_durable_before_later_failure_and_cannot_be_relabelled(self):
  import tempfile,json
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  scenes=[dict(id="cc",steps=[dict(inputs=[dict(type="wait",seconds=.3333333333333333)])],evidence=dict(identity_sha256="original"))]
  with tempfile.TemporaryDirectory() as folder:
   out=pathlib.Path(folder)
   module.persist_case_scenes(out,scenes)
   self.assertEqual(json.loads((out/"captured-scenes.json").read_text()),scenes)
   with self.assertRaises(FileExistsError):module.persist_case_scenes(out,[dict(id="replacement")])
   self.assertEqual(json.loads((out/"captured-scenes.json").read_text()),scenes)
 def test_controlled_local_report_scope_stays_distinct_from_realtime_qualification(self):
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  report=module.report_document({},"controlled-experimental",[],"/evidence",["scene"],controlled_local=True)
  self.assertEqual(report["validation_scope"],"controlled-manual-generation")
  self.assertEqual(report["realtime_qualification"],"pending-ci")
  self.assertEqual(report["clock_mode"],"controlled-experimental")
  self.assertIs(report["complete_regression_run"],False)
  self.assertNotIn("manual_generation_complete",report)
  with self.assertRaisesRegex(ValueError,"controlled-experimental"):
   module.report_document({},"real-time",[],"/evidence",["scene"],controlled_local=True)
 def test_authored_strategy_checkpoints_bind_actual_native_result_fields(self):
  import ast,yaml
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  plan=yaml.safe_load((ROOT/"manual/scene-plans.yaml").read_text())
  scene=next(s for s in plan["scenes"] if s["id"]=="merge-overlap-and-union")
  tree=ast.parse((ROOT/"tests/behaviour/contract/live_ui_feedback.py").read_text())
  callback=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="live_ui_merge_modes")
  producer=next(n for n in ast.walk(callback) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=="dict" and any(k.arg=="kind" and isinstance(k.value,ast.Constant) and k.value.value=="merge-mode" for k in n.keywords))
  fields={k.arg:ast.literal_eval(k.value) for k in producer.keywords if k.arg!="value"}
  checkpoints=[s for s in scene["steps"] if s["assertion"].get("kind")=="merge-mode"]
  self.assertEqual([s["assertion"]["value"] for s in checkpoints],["SKIP","ONLY","ALL"])
  for step in checkpoints:
   with self.subTest(step=step["id"]):
    actual=dict(fields,value=step["assertion"]["value"])
    self.assertTrue(module.Selector(step["assertion"],step.get("occurrence",1)).accept(actual),"authored checkpoint must match the actual shared Strategy result, preserving its value")
class NestedSessions(unittest.TestCase):
 def module(self):
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def test_nested_launch_defaults_and_explicit_mismatch_rejected_before_launch(self):
  m=self.module();contract=dict(clock_mode="controlled-experimental",experimental_install="/runtime/install.json",profile="base-midi",app_root="/frozen")
  self.assertEqual(m.participant_options({},contract),contract)
  for field,value in (("clock_mode","real-time"),("experimental_install",None),("profile","midi-modulation"),("app_root","/live")):
   with self.subTest(field=field),self.assertRaises(ValueError):m.participant_options({field:value},contract)
 def test_nested_results_and_traces_are_isolated_even_for_identical_assertions(self):
  m=self.module();a=m.ParticipantState(0);b=m.ParticipantState(1)
  a.record(dict(type="enc",n=3,delta=2));b.record(dict(type="midi",port=1,bytes=[176,20,65]))
  self.assertEqual(a.cursors.take("same",a.trace),[dict(type="enc",n=3,delta=2)])
  self.assertEqual(b.cursors.take("same",b.trace),[dict(type="midi",port=1,bytes=[176,20,65])])
  self.assertIsNot(a.deferred,b.deferred)
  a.record(dict(type="key",n=1,state=1));self.assertEqual(len(a.held),1);self.assertFalse(b.held)
 def test_stop_safety_observation_overrides_ignored_stop_tap_guess(self):
  import types
  m=self.module();c=types.SimpleNamespace(manual_transport_on=True)
  m.reconcile_transport(c,dict(kind="stop-safety",transport="stopped",passed=True))
  self.assertFalse(c.manual_transport_on)
  m.reconcile_transport(c,dict(kind="stop-safety",transport="playing",passed=False))
  self.assertFalse(c.manual_transport_on)
 def test_failed_child_cleanup_still_finishes_outer_and_preserves_each_trace(self):
  import types,tempfile
  m=self.module();closed=[];written=[]
  def child_finish():closed.append("child");raise RuntimeError("child cleanup failed")
  def parent_finish():closed.append("outer")
  child=types.SimpleNamespace(finished=False,out=pathlib.Path("child"),results=[],finish=child_finish)
  outer=types.SimpleNamespace(finished=False,out=pathlib.Path("outer"),results=[],finish=parent_finish)
  def close(c,held):c.finish();c.finished=True
  with self.assertRaises(RuntimeError):m.finish_participants([(outer,m.ParticipantState(0),[]),(child,m.ParticipantState(1),[])],close,lambda path,value:written.append(str(path)))
  self.assertIn("outer",closed);self.assertIn("child/capture-trace.json",written);self.assertIn("outer/capture-trace.json",written)
 def test_step_session_ordinal_owns_entire_scene_and_mixed_owners_rejected(self):
  m=self.module()
  self.assertEqual(m.scene_session_ordinal(dict(steps=[dict(session_ordinal=1),dict(session_ordinal=1)])),1)
  self.assertEqual(m.scene_session_ordinal(dict(steps=[dict()])),0)
  with self.assertRaises(ValueError):m.scene_session_ordinal(dict(steps=[dict(session_ordinal=1),dict()]))
 def test_actual_authored_nested_plan_selects_child_without_parent_assertions(self):
  import yaml
  m=self.module();plans=yaml.safe_load((ROOT/"manual/scene-plans-nested.yaml").read_text())["scenes"]
  self.assertTrue(plans);self.assertEqual([m.scene_session_ordinal(p) for p in plans],[1]*len(plans))
  with self.assertRaises(ValueError):m.scene_session_ordinal(dict(session_ordinal=0,steps=[dict(session_ordinal=1)]))
 def test_session_ordinal_schema_rejects_negative_and_fractional(self):
  import json,jsonschema
  m=self.module();schema=json.loads((ROOT/"manual/case-scenes.schema.json").read_text())
  scene=dict(id="child",feature_id="mapping",title="Mapping",behaviour_case="M-MAP001",citation="README.md#midi-controller-mapping",steps=[dict(id="cc",title="CC",caption="CC changes velocity",assertion=dict(kind="midi-mapping"))])
  for ordinal in (-1,.5):
   with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(dict(schema_version=1,scenes=[dict(scene,session_ordinal=ordinal)]),schema)
class NestedCaptureIntegration(unittest.TestCase):
 # Characterisation: adapter provenance must follow the actual native session.
 def test_publication_uses_child_frame_indices_and_evidence_and_preserves_outer_summary(self):
  import tempfile,types,sys,json,hashlib
  from unittest.mock import patch
  m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  created=[]
  def write(path,value):path.write_text(json.dumps(value))
  def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
  class FakeDriver:
   def __init__(self,out,**kwargs):
    self.out=out;self.out.mkdir(exist_ok=True);self.clock_mode=kwargs["clock_mode"];self.profile=kwargs["profile"];self.app_root=pathlib.Path(kwargs["app_root"]);self.launch_options=kwargs;self.recipe=[];self.results=[];self.finished=False;self.manual_transport_on=False;created.append(self)
   def action(self,**value):self.recipe.append(value)
   def elapse(self,seconds):pass
   def finish(self):
    if self.finished:return
    native=self.out/"native";native.mkdir()
    write(native/"identity.json",dict(session_id=str(len(created)) if self is created[-1] else "outer",runtime_identity=dict(lock="same"),application_identity=dict(files=[dict(path="mosaic/mosaic.lua",sha256="same")])) )
    write(native/"native-config.json",dict(clock_mode=self.clock_mode));write(native/"cleanup.json",[])
    (native/"native-events.jsonl").write_text("[]")
    write(self.out/"recipe.json",self.recipe);write(self.out/"results.json",self.results);self.finished=True
  childmodule=types.ModuleType("nested_fixture");childmodule.__file__=str(ROOT/"tests/behaviour/nested_fixture.py");childmodule.Driver=FakeDriver
  def run(c):
   c.action(type="enc",n=2,delta=2);c.results.append(dict(kind="accepted",passed=True));c.finish()
   child=childmodule.Driver(c.out/"child",**c.launch_options)
   child.action(type="midi",port=1,bytes=[176,20,65]);child.elapse(.2);child.results.append(dict(kind="accepted",passed=True));child.finish()
   c.results.append(dict(kind="child-summary",passed=True))
  def frame(c,case,key):
   record=dict(kind="documentation-frame",sha256="child-pixels" if c is created[-1] and len(created)>1 else "outer-pixels",passed=True)
   c.results.append(record);return dict(screen_rle=[],grid=[],binding=record)
  def close(c,held):self.assertFalse(held);c.finish()
  driver=types.SimpleNamespace(Driver=FakeDriver,digest=digest,write=write)
  manual=types.SimpleNamespace(tracked_driver=FakeDriver,frame=frame,close=close)
  cases=types.SimpleNamespace(CASES={"M-TEST001":dict(run=run,requirements=[])})
  def plan(id,ordinal):return dict(id=id,session_ordinal=ordinal,behaviour_case="M-TEST001",feature_id="mapping",title=id,citation="README.md#midi-controller-mapping",steps=[dict(id="accepted",title="Accepted",caption="Observed",assertion=dict(kind="accepted"))])
  with tempfile.TemporaryDirectory() as directory,patch.dict(sys.modules,dict(driver=driver,manual_capture=manual,cases=cases,nested_fixture=childmodule)):
   out=pathlib.Path(directory);options=types.SimpleNamespace(clock_mode="real-time",experimental_install=None,app_root=out/"application",mod_code_root=None,mod_patches=False)
   captures=m.capture_group([plan("parent",0),plan("child",1)],out,options)
   parent,child=captures
   self.assertEqual(child["steps"][0]["output"]["binding"]["sha256"],"child-pixels")
   self.assertEqual(child["steps"][0]["output"]["binding"]["assertion_index"],0)
   self.assertEqual(child["steps"][0]["inputs"],[dict(type="midi",port=1,bytes=[176,20,65]),dict(type="wait",seconds=.2)])
   self.assertEqual(parent["steps"][0]["inputs"],[dict(type="enc",n=2,delta=2)])
   self.assertEqual(child["evidence"]["path"],str(out/"child"))
   self.assertEqual(len(child["evidence"]["case_participants"]),2)
   self.assertEqual(json.loads((out/"results.json").read_text())[-1]["kind"],"child-summary")
   self.assertTrue(all(c.finished for c in created));self.assertIs(childmodule.Driver,FakeDriver)
 def test_exact_record_interval_alternatives_reject_short_or_wrong_spacing(self):
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  primary=dict(kind="recorded-replay-spacing",expected_seconds=[1/3]*6)
  alternative=dict(kind="recorded-replay-spacing",expected_seconds=[1/3]*7)
  for count in (6,7):
   selector=module.Selector(primary,alternatives=[alternative])
   self.assertTrue(selector.accept(dict(kind="recorded-replay-spacing",expected_seconds=[1/3]*count)))
   self.assertEqual(selector.matched["expected_seconds"],[1/3]*count)
  self.assertFalse(module.Selector(primary,alternatives=[alternative]).accept(dict(kind="recorded-replay-spacing",expected_seconds=[1/3]*5)))
  self.assertFalse(module.Selector(primary,alternatives=[alternative]).accept(dict(kind="recorded-replay-spacing",expected_seconds=[1/3]*6+[.34])))
class StartSourcesAndExtraCases(unittest.TestCase):
 def module(self):
  m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_extra_case_exact_bytes_are_executed_and_base_registry_not_mutated(self):
  import tempfile
  m=self.module();base={"M-BASE-001":dict(run=lambda c:None,requirements=["README"],description="Base")}
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory);(root/"tools").mkdir();source=root/"tools/extra.py"
   blob=b"# coding: latin-1\nVALUE='caf\xe9'\ndef run(c): c.append(VALUE)\nCASES={'M-EXTRA-001':dict(run=run,requirements=['README'],description='Extra')}\n"
   source.write_bytes(blob);registry,blobs=m.load_extra_cases([source],base,root)
   output=[];registry["M-EXTRA-001"]["run"](output)
   self.assertEqual(output,["caf\u00e9"]);self.assertEqual(blobs,{"tools/extra.py":blob});self.assertEqual(list(base),["M-BASE-001"])
 def test_extra_case_paths_duplicates_and_invalid_entries_rejected(self):
  import tempfile
  m=self.module()
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory);(root/"tools").mkdir();source=root/"tools/extra.py";outside=root/"outside.py";outside.write_text("raise AssertionError('must not execute')")
   with self.assertRaises(ValueError):m.load_extra_cases([outside],{},root)
   source.write_text("CASES={'M-BASE-001':dict(run=lambda c:None,requirements=['R'],description='duplicate')}")
   with self.assertRaises(ValueError):m.load_extra_cases([source],{'M-BASE-001':{}},root)
   source.write_text("CASES={'bad-id':dict(run=3,requirements='bad',description='bad')}")
   with self.assertRaises(ValueError):m.load_extra_cases([source],{},root)
   source.write_text("CASES={'M-EXTRA-001':dict(run=lambda c:None,requirements=['R'],description='valid')}")
   with self.assertRaises(ValueError):m.load_extra_cases([source,source],{},root)
 def test_start_receipt_pins_all_bytes_and_is_immutable(self):
  import tempfile,json,hashlib
  m=self.module()
  with tempfile.TemporaryDirectory() as directory:
   run=pathlib.Path(directory);blobs={'case_sources':{'tests/behaviour/case.py':b'case'},'fixture_sources':{'tests/behaviour/config/a.json':b'fixture'},'capture_sources':{'tools/helper.py':b'helper'},'plan_files':{'manual/plan.yaml':b'plan'}}
   receipt=m.persist_start_sources(run,blobs)
   for kind,entries in blobs.items():
    for name,blob in entries.items():self.assertEqual(receipt[kind][name],hashlib.sha256(blob).hexdigest())
   self.assertEqual((run/'case-source/tests/behaviour/case.py').read_bytes(),b'case')
   self.assertEqual((run/'fixture-source/tests/behaviour/config/a.json').read_bytes(),b'fixture')
   self.assertEqual(json.loads((run/'start-source-identity.json').read_text()),receipt)
   with self.assertRaises(FileExistsError):m.persist_start_sources(run,blobs)
 def test_edited_derived_inputs_are_rejected_before_regeneration(self):
  import tempfile,json,yaml
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder);(root/"manual/features").mkdir(parents=True);(root/"manual/generated").mkdir()
   scene=dict(id="route",steps=[dict(id="select",inputs=[dict(type="enc",n=3,delta=2)])])
   raw=root/"manual/generated/example.json";raw.write_text(json.dumps(dict(scenes=[scene])))
   derived=root/"manual/features/scenes-example.yaml";derived.write_text(yaml.safe_dump(dict(fixture_kind="behaviour-case",scenes=[scene])))
   module.validate_derived_inputs(root,{"route"})
   scene["steps"][0]["inputs"][0]["delta"]=4
   derived.write_text(yaml.safe_dump(dict(fixture_kind="behaviour-case",scenes=[scene])))
   with self.assertRaisesRegex(ValueError,"Derived inputs changed"):module.validate_derived_inputs(root,{"route"})
 def test_real_time_participant_retains_explicit_installation_without_clock_relabel(self):
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  contract=dict(clock_mode='real-time',experimental_install='/qualified/output-boundary.json',app_root='/frozen',profile='base-midi')
  self.assertEqual(module.participant_options({},contract),contract)
  with self.assertRaisesRegex(ValueError,'experimental_install'):
   module.participant_options({'experimental_install':None},contract)
if __name__=="__main__":unittest.main()
