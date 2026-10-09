"""Build orchestration contracts; characterisation outside the manual."""
import importlib.util,unittest,tempfile,sys,json,subprocess,ast,hashlib,os
from unittest import mock
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
spec=importlib.util.spec_from_file_location("manual_build",ROOT/"tools/manual_build.py")
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
# The 2026-10-06 root installs add six named stages to the frozen 73-full/44-local baseline.
# Receipts: /home/andy/mosaic-manual-build-operators/{core-portable,player-publication,public-gap-build,
# modest-matrix-v10,native-public-gaps-v03}.
# Committed source 9efbd8ad7fe3ae96e36db7386e3a3d0fa5be5ca0 adds a full-only fresh-target producer and
# the real/controlled Save Dialog pair; only the controlled Save Dialog stage is in controlled-local.
BASELINE_FULL_STAGES,BASELINE_LOCAL_STAGES,BASELINE_LOCAL_REFERENCE_CONTROLLED=73,44,19
STAGES_ADDED_20261006_FULL=(
 "reference-real-scene-plans-modulation-macro-midi-modulation","reference-controlled-scene-plans-modulation-macro-midi-modulation",
 "reference-real-scene-plans-native-public-gaps-base-midi","reference-controlled-scene-plans-native-public-gaps-base-midi",
 "reference-controlled-scene-plans-player-apply-manual-player-ui","reader-projection")
STAGES_ADDED_20261008_FULL=("fresh-target-midi-producer","reference-real-scene-plans-save-dialog-base-midi","reference-controlled-scene-plans-save-dialog-base-midi")
STAGES_ADDED_FULL=STAGES_ADDED_20261006_FULL+STAGES_ADDED_20261008_FULL
STAGES_ADDED_LOCAL=tuple(name for name in STAGES_ADDED_FULL if not name.startswith("reference-real-") and name!="fresh-target-midi-producer")
def reader_projection_record(**changes):
 """Terminal receipt shape written by run_build_stages for the reader-projection stage."""
 record=dict(name="reader-projection",passed=True,returncode=0,reader_projection=dict(passed=True))
 record.update(changes);return record
class BuildPlan(unittest.TestCase):
 def test_controlled_local_plan_publishes_controlled_captures_without_realtime_qualification(self):
  options=self.options();options.modulation_code_root="/mods";options.modulation_controlled_install="/native/mod-control.json"
  stages=build.plan(options,["scene-plans-course.yaml"],controlled_local=True)
  names=[stage["name"] for stage in stages]
  self.assertFalse(any(name in ("masks-real","first-sound-real") or name.startswith("reference-real-") for name in names))
  self.assertNotIn("doctor-options-setup-real",names);self.assertNotIn("doctor-options-ready-real",names)
  controlled=next(stage for stage in stages if stage["name"]=="reference-controlled-scene-plans-course-base-midi")
  self.assertIn("--publish",controlled["command"])
  self.assertIn("--controlled-local",controlled["command"])
  self.assertEqual(controlled["command"][controlled["command"].index("--clock-mode")+1],"controlled-experimental")
  audio=next(stage for stage in stages if stage["name"]=="musical-audio-assets")
  self.assertNotIn("--midi-real-install",audio["command"])
  self.assertIn("--controlled-local",audio["command"])
  self.assertNotIn("musical-audio",names)
  self.assertFalse(any(name.startswith("doctor-options-") for name in names))
  bind=next(stage for stage in stages if stage["name"]=="course-bind")
  self.assertTrue(bind["action"]["controlled_local"])
 def test_current_plan_inventory_matches_named_full_and_controlled_stages(self):
  options=self.options();options.modulation_code_root="/mods";options.modulation_controlled_install="/native/mod-control.json";options.browser_tests=True
  plans=[path.name for path in sorted((ROOT/"manual").glob("scene-plans*.yaml"))]
  full=build.plan(options,plans,controlled_local=False);local=build.plan(options,plans,controlled_local=True)
  self.assertEqual(len(full),BASELINE_FULL_STAGES+len(STAGES_ADDED_FULL));self.assertEqual(len(local),BASELINE_LOCAL_STAGES+len(STAGES_ADDED_LOCAL))
  full_names=[row["name"] for row in full];local_names=[row["name"] for row in local]
  self.assertEqual(len(set(full_names)),len(full_names));self.assertEqual(len(set(local_names)),len(local_names))
  for name in STAGES_ADDED_FULL:self.assertEqual(full_names.count(name),1,name)
  for name in STAGES_ADDED_LOCAL:self.assertEqual(local_names.count(name),1,name)
  for name in STAGES_ADDED_FULL:
   if name.startswith("reference-real-") or name=="fresh-target-midi-producer":self.assertNotIn(name,local_names)
  self.assertLess(full_names.index("compile-book"),full_names.index("fresh-target-midi-producer"));self.assertLess(full_names.index("fresh-target-midi-producer"),full_names.index("reader-projection"))
  self.assertLess(full_names.index("reference-real-scene-plans-save-dialog-base-midi"),full_names.index("reference-controlled-scene-plans-save-dialog-base-midi"))
  self.assertLess(full_names.index("reader-projection"),full_names.index("quick-reference"));self.assertGreater(full_names.index("reader-projection"),full_names.index("compile-book"))
  controlled_refs=[row for row in local if row["name"].startswith("reference-controlled-")]
  self.assertEqual(len(controlled_refs),BASELINE_LOCAL_REFERENCE_CONTROLLED+sum(n.startswith("reference-controlled-") for n in STAGES_ADDED_LOCAL))
  self.assertIn("reference-controlled-scene-plans-save-dialog-base-midi",local_names)
  self.assertNotIn("reference-real-scene-plans-save-dialog-base-midi",local_names)
  self.assertNotIn("fresh-target-midi-producer",local_names)
  self.assertFalse(any(row["name"].startswith("reference-real-") or row["name"].startswith("doctor-options-") for row in local))
 def test_launch_mode_requires_real_install_only_for_full_paired_generation(self):
  with self.assertRaisesRegex(ValueError,"explicit qualified real installation"):
   build.validate_launch_mode(False,None)
  self.assertIsNone(build.validate_launch_mode(True,None))
 def test_explicit_full_plan_mode_keeps_original_paired_plan(self):
  options=self.options();options.modulation_code_root="/mods";options.modulation_controlled_install="/native/mod-control.json"
  plans=[path.name for path in sorted((ROOT/"manual").glob("scene-plans*.yaml"))]
  self.assertEqual(build.plan(options,plans),build.plan(options,plans,controlled_local=False))
  names=[stage["name"] for stage in build.plan(options,plans,controlled_local=False)]
  self.assertTrue(any(name.startswith("reference-real-") for name in names))
  self.assertTrue(any(name.startswith("reference-controlled-") for name in names))
 def test_completion_rejects_an_incomplete_book_even_with_all_plans_and_browser_checks(self):
  with self.assertRaisesRegex(ValueError,"incomplete"):
   build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml"],{"complete_manual":False})
 def test_completion_requires_browser_and_entire_required_plan_inventory(self):
  book={"complete_manual":True}
  self.assertFalse(build.complete_build(False,["scene-plans.yaml"],["scene-plans.yaml"],book))
  self.assertFalse(build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml","scene-plans-course.yaml"],book))
  with tempfile.TemporaryDirectory() as folder:
   records=self.qualification_records(Path(folder))
   with_projection=records+[reader_projection_record()]
   self.assertTrue(build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml"],book,with_projection))
   # A passed reader projection is now part of completion (reader-shell install, 2026-10-06): missing, failed or duplicated rejects.
   self.assertFalse(build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml"],book,records))
   self.assertFalse(build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml"],book,records+[reader_projection_record(passed=False)]))
   self.assertFalse(build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml"],book,records+[reader_projection_record(reader_projection=dict(passed=False))]))
   self.assertFalse(build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml"],book,records+[reader_projection_record(),reader_projection_record()]))
 def test_case_capture_report_rejects_a_controlled_scope_or_clock_mismatch(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);run=root/"run";run.mkdir();report=run/"reference-scenes.json"
   report.write_text(json.dumps({"schema_version":1,"scenes":[{"id":"course"}],"clock_mode":"controlled-experimental","validation_scope":"controlled-manual-generation","realtime_qualification":"pending-ci","complete_regression_run":False}))
   log=root/"stage.log";log.write_text(str(run)+"\n")
   self.assertEqual(build.case_capture_result(log,root,"controlled-manual-generation")["path"],str(report))
   data=json.loads(report.read_text());data["clock_mode"]="real-time";report.write_text(json.dumps(data))
   with self.assertRaisesRegex(ValueError,"scope"):build.case_capture_result(log,root,"controlled-manual-generation")
 def test_generation_context_pins_selected_required_scenes_and_sources(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/"manual").mkdir();(root/"manual/a.yaml").write_text("scenes: [{id: z}, {id: a}]\n");evidence=root/"evidence";evidence.mkdir()
   with mock.patch.object(build,"ROOT",root):context=build.write_generation_context(evidence,["a.yaml"],["a.yaml"],{"manual/a.yaml":"source-sha"})
   saved=json.loads((evidence/"generation-context.json").read_text())
   self.assertEqual(saved["selected_scene_ids"],["a","z"])
   self.assertEqual(saved["required_scene_ids"],["a","z"])
   self.assertEqual(saved["source_files_before"],{"manual/a.yaml":"source-sha"})
   self.assertEqual(context["validation_scope"],"controlled-manual-generation")
   self.assertEqual(saved["clock_mode"],"controlled-experimental")
   self.assertEqual(context["clock_mode"],"controlled-experimental")
 def test_manual_generation_requires_full_inventory_browser_and_finished_assembly(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/"manual").mkdir();(root/"manual/a.yaml").write_text("scenes: [{profile: base-midi}]\n")
   book={"complete_manual":True};capture={"name":"reference-controlled-x","passed":True,"native_report":{"path":"report.json"}};records=[capture,reader_projection_record()]
   with mock.patch.object(build,"ROOT",root):
    self.assertFalse(build.complete_manual_generation(False,["a.yaml"],["a.yaml"],book,records))
    self.assertFalse(build.complete_manual_generation(True,["a.yaml"],["a.yaml","b.yaml"],book,records))
    self.assertFalse(build.complete_manual_generation(True,["a.yaml"],["a.yaml"],{"complete_manual":False},records))
    self.assertTrue(build.complete_manual_generation(True,["a.yaml"],["a.yaml"],book,records))
    # Reader projection must be present, unique and passed (reader-shell install, 2026-10-06).
    self.assertFalse(build.complete_manual_generation(True,["a.yaml"],["a.yaml"],book,[capture]))
    self.assertFalse(build.complete_manual_generation(True,["a.yaml"],["a.yaml"],book,[capture,reader_projection_record(reader_projection=dict(passed=False))]))
    self.assertFalse(build.complete_manual_generation(True,["a.yaml"],["a.yaml"],book,[capture,reader_projection_record(),reader_projection_record()]))
 def test_case_capture_report_requires_exact_terminal_stdout_and_valid_document(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);run=root/"run";run.mkdir()
   report=run/"reference-scenes.json";report.write_text(json.dumps({"schema_version":1,"scenes":[{"id":"course-first-sound"}]}))
   log=root/"stage.log";log.write_text("Verified M-MANUAL-COURSE-001\n"+str(run)+"\n")
   result=build.case_capture_result(log,root)
   self.assertEqual(result,{"path":str(report),"sha256":build.digest(report)})
   log.write_text("Verified M-MANUAL-COURSE-001\n")
   with self.assertRaisesRegex(ValueError,"report"):build.case_capture_result(log,root)
 def test_post_capture_teaching_stages_precede_compilation(self):
  stages=build.plan(self.options(),["scene-plans-course.yaml"])
  names=[s["name"] for s in stages]
  for name in ["raw-publication-audit","caption-rebind","course-bind","feature-bind"]:
   self.assertIn(name,names)
   self.assertLess(names.index(name),names.index("compile-book"))
  self.assertLess(names.index("raw-publication-audit"),names.index("caption-rebind"))
 def test_complete_browser_plan_checks_course_context_and_primary_teaching_sequence(self):
  options=self.options();options.browser_tests=True
  names=[row["name"] for row in build.plan(options,["scene-plans-course.yaml"])]
  self.assertIn("browser-manual_course_browser",names)
 def test_complete_browser_plan_includes_pictured_control_navigation(self):
  options=self.options();options.browser_tests=True
  names=[row["name"] for row in build.plan(options,["scene-plans-course.yaml"])]
  self.assertIn("browser-manual_controls_browser",names)
  self.assertEqual(len([name for name in names if name.startswith("browser-")]),8)
 def test_feature_binding_supplies_audio_runtime_for_canonical_player_frame_audit(self):
  row=next(row for row in build.plan(self.options(),["scene-plans-course.yaml"]) if row['name']=='feature-bind')
  self.assertEqual(row['emulator'],'/native/audio')
 def test_real_readability_requires_explicit_output_boundary_installation(self):
  options=self.options();options.readability_real_install=None
  with self.assertRaisesRegex(ValueError,'readability.*installation'):build.plan(options,['scene-plans-readability.yaml'])
 def test_only_real_readability_uses_the_explicit_installation(self):
  stages=build.plan(self.options(),['scene-plans-readability.yaml','scene-plans.yaml'])
  rows=[s for s in stages if s['name'].startswith('reference-')]
  real=next(s for s in rows if s['name']=='reference-real-scene-plans-readability-base-midi')
  self.assertEqual(real['command'][real['command'].index('--experimental-install')+1],'/native/qualified-real-output-boundary.json')
  self.assertEqual(real['command'][real['command'].index('--clock-mode')+1],'real-time')
  ordinary=next(s for s in rows if s['name']=='reference-real-scene-plans-base-midi')
  self.assertEqual(ordinary['command'][ordinary['command'].index('--experimental-install')+1],'/native/qualified-real.json')
  controlled=next(s for s in rows if s['name']=='reference-controlled-scene-plans-readability-base-midi')
  self.assertEqual(controlled['command'][controlled['command'].index('--experimental-install')+1],'/native/control.json')
 def test_generic_real_captures_require_explicit_qualified_installation(self):
  options=self.options();options.real_install=None
  with self.assertRaisesRegex(ValueError,'real.*installation'):build.plan(options,['scene-plans.yaml'])
 def test_all_generic_real_profiles_use_qualified_install_but_audio_stays_separate(self):
  options=self.options();options.modulation_code_root='/mods'
  stages=build.plan(options,['scene-plans.yaml','scene-plans-options.yaml','scene-plans-readability.yaml'])
  for row in stages:
   if row['name'] in ('masks-real','first-sound-real') or row['name'].startswith('reference-real-'):
    expected='/native/qualified-real-output-boundary.json' if 'readability' in row['name'] else '/native/qualified-real.json'
    self.assertEqual(row['command'][row['command'].index('--experimental-install')+1],expected)
  audio=next(row for row in stages if row['name']=='musical-audio')
  self.assertEqual(audio['command'][audio['command'].index('--midi-real-install')+1],'/native/qualified-real.json')
  self.assertEqual(audio['command'][audio['command'].index('--audio-install')+1],'/native/audio.json')
 def options(self):return SimpleNamespace(emulator="/native/base",audio_emulator="/native/audio",controlled_install="/native/control.json",audio_install="/native/audio.json",mod_code_root="/voices",ffmpeg="/ffmpeg",readability_real_install="/native/qualified-real-output-boundary.json",real_install="/native/qualified-real.json",browser_tests=False)
 def test_real_and_controlled_are_independent_and_audio_uses_matching_checkout(self):
  stages=build.plan(self.options(),["scene-plans.yaml","scene-plans-extra.yaml"])
  self.assertTrue(any(s["name"]=="masks-real" for s in stages))
  self.assertTrue(any(s["name"]=="masks-controlled" for s in stages))
  audio=next(s for s in stages if s["name"]=="musical-audio")
  self.assertEqual(audio["emulator"],"/native/audio")
  real=[s for s in stages if s["name"].startswith("reference-real")]
  controlled=[s for s in stages if s["name"].startswith("reference-controlled")]
  self.assertEqual(len(real),2);self.assertEqual(len(controlled),2)
  self.assertTrue(all("--publish" in s["command"] for s in real))
  self.assertTrue(all("--publish" not in s["command"] for s in controlled))
 def test_musical_comparisons_receive_independent_midi_runtimes(self):
  stages=build.plan(self.options(),["scene-plans-course.yaml"])
  audio=next(s for s in stages if s["name"]=="musical-audio")
  command=audio["command"]
  self.assertIn("--midi-emulator",command)
  self.assertEqual(command[command.index("--midi-emulator")+1],"/native/base")
  self.assertIn("--midi-controlled-install",command)
  self.assertEqual(command[command.index("--midi-controlled-install")+1],"/native/control.json")
 def test_unsafe_plan_cannot_be_sent_to_a_process(self):
  with self.assertRaisesRegex(ValueError,"Unsafe"):build.plan(self.options(),["../private.yaml"])
 def test_external_lock_only_wraps_generic_capture(self):
  stages=build.plan(self.options(),["scene-plans.yaml"])
  self.assertTrue(next(s for s in stages if s["name"]=="masks-real")["exclusive_lock"])
  self.assertFalse(next(s for s in stages if s["name"]=="musical-audio")["exclusive_lock"])
 def test_publication_refresh_indexes_all_emitted_scene_authoring(self):
  entries=build.scene_sources(["scene-plans.yaml"],["scenes-reference-scenes.yaml"])
  self.assertEqual(entries,["scene-plans.yaml","features/scenes-reference-scenes.yaml"])
 def test_modulation_sources_and_profile_outputs_are_independent(self):
  opts=self.options();opts.modulation_code_root="/matrix";opts.modulation_emulator="/native/mod";opts.modulation_controlled_install="/native/mod-control.json"
  stages=build.plan(opts,["scene-plans-options.yaml"])
  real=[s for s in stages if s["name"].startswith("reference-real")]
  self.assertEqual(len(real),2)
  mod=next(s for s in real if "--mod-patches" in s["command"])
  self.assertEqual(mod["emulator"],"/native/mod")
  self.assertIn("/matrix",mod["command"])
  self.assertNotIn("/voices",mod["command"])
  self.assertEqual(len({s["command"][s["command"].index("--output")+1] for s in real}),2)
 def test_duplicate_plan_files_are_rejected(self):
  with self.assertRaisesRegex(ValueError,"unique"):build.plan(self.options(),["scene-plans.yaml","scene-plans.yaml"])
 def test_refresh_archives_obsolete_publication_without_changing_native_evidence(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/"manual/generated").mkdir(parents=True);(root/"manual/features").mkdir()
   (root/"manual/book.yaml").write_text("scene_sources: [old.yaml, features/first-sound-capture.yaml]\n")
   old=root/"manual/generated/reference-old-scenes.json";old.write_text("original native publication")
   expected=root/"manual/generated/reference-scenes.json";expected.write_text("new native publication")
   (root/"manual/features/scenes-reference-old-scenes.yaml").write_text("old authored scene")
   (root/"manual/features/scenes-reference-scenes.yaml").write_text("new authored scene")
   evidence=root/"evidence";evidence.mkdir()
   with mock.patch.object(build,"ROOT",root):build.refresh_index({"outputs":["reference-scenes.json"],"plans":["scene-plans.yaml"]},evidence)
   self.assertFalse(old.exists())
   self.assertEqual((evidence/"previous-publication/manual/generated/reference-old-scenes.json").read_text(),"original native publication")
   self.assertEqual(expected.read_text(),"new native publication")
   self.assertIn("features/scenes-reference-scenes.yaml",(root/"manual/book.yaml").read_text())
   self.assertIn("features/first-sound-capture.yaml",(root/"manual/book.yaml").read_text())
 def test_stage_evidence_records_failures_and_preserves_existing_log(self):
  with tempfile.TemporaryDirectory() as folder:
   evidence=Path(folder);opts=self.options();opts.node_path=None
   stage={"name":"controlled-unit","command":[sys.executable,"-c","raise SystemExit(7)"],"emulator":None,"exclusive_lock":False,"action":None}
   with self.assertRaises(subprocess.CalledProcessError):build.run_stage(stage,evidence,opts,None)
   before=(evidence/"controlled-unit.json").read_bytes()
   result=json.loads(before);self.assertFalse(result["passed"]);self.assertEqual(result["returncode"],7)
   with self.assertRaises(FileExistsError):build.run_stage(stage,evidence,opts,None)
   self.assertEqual((evidence/"controlled-unit.json").read_bytes(),before)
 def test_first_sound_has_independent_semantic_lanes_with_baseline_cases(self):
  stages=build.plan(self.options(),["scene-plans.yaml"])
  real=next(s for s in stages if s["name"]=="first-sound-real")
  controlled=next(s for s in stages if s["name"]=="first-sound-controlled")
  for stage in [real,controlled]:
   self.assertTrue(stage["exclusive_lock"])
   self.assertIn("--visuals-only",stage["command"])
   self.assertIn(str(ROOT/"manual/features/first-sound-capture.yaml"),stage["command"])
   self.assertNotIn("--skip-existing-cases",stage["command"])
  self.assertNotIn("--verify-only",real["command"])
  self.assertIn("--verify-only",controlled["command"])
 def test_editorial_refresher_uses_the_explicit_encoding_tool(self):
  stages=build.plan(self.options(),["scene-plans.yaml"])
  refresh=next(s for s in stages if s["name"]=="refresh-editorial")
  self.assertEqual(refresh["command"][refresh["command"].index("--ffmpeg")+1],"/ffmpeg")
  self.assertLess(stages.index(refresh),next(n for n,s in enumerate(stages) if s["name"]=="compile-book"))
 def test_reason_and_swing_pin_the_additive_case_source_in_both_lanes(self):
  stages=build.plan(self.options(),["scene-plans-reason-swing.yaml"])
  rows=[s for s in stages if s["name"].startswith("reference-")]
  self.assertEqual(len(rows),2)
  for row in rows:
   command=row["command"]
   self.assertIn("--extra-cases",command)
   self.assertEqual(command[command.index("--extra-cases")+1],str(ROOT/"tools/manual_reason_swing_cases.py"))
 def test_vertical_list_capture_uses_the_canonical_native_registry(self):
  stages=build.plan(self.options(),["scene-plans-vertical-list.yaml"])
  rows=[s for s in stages if s["name"].startswith("reference-")]
  self.assertEqual(len(rows),2)
  for row in rows:
   command=row["command"]
   self.assertNotIn("--extra-cases",command)
 def test_save_dialog_capture_loads_its_existing_additive_case(self):
  stages=build.plan(self.options(),["scene-plans-save-dialog.yaml"])
  rows=[s for s in stages if s["name"].startswith("reference-")]
  self.assertEqual([s["name"] for s in rows],[
   "reference-real-scene-plans-save-dialog-base-midi",
   "reference-controlled-scene-plans-save-dialog-base-midi",
  ])
  for row in rows:
   command=row["command"]
   self.assertIn("--extra-cases",command)
   self.assertEqual(command[command.index("--extra-cases")+1],str(ROOT/"tools/manual_save_dialog_cases.py"))
 def test_every_authored_scene_case_resolves_through_its_planned_registry(self):
  import importlib, yaml
  behaviour=str(ROOT/"tests/behaviour")
  sys.path.insert(0,behaviour)
  try:
   cases=importlib.import_module("cases")
   from manual_case_capture import load_extra_cases
   options=self.options()
   options.modulation_code_root="/mods"
   options.modulation_controlled_install="/native/mod-control.json"
   options.modulation_emulator="/native/mod-emulator"
   plans=sorted(path.name for path in (ROOT/"manual").glob("scene-plans*.yaml"))
   stages=build.plan(options,plans)
   registry_cache={}
   checked=set()
   capture_stages=[stage for stage in stages if any("manual_case_capture.py" in arg for arg in stage["command"])]
   for stage in capture_stages:
    command=stage["command"]
    plan_path=Path(command[command.index("--plans")+1])
    profile=command[command.index("--profile")+1]
    scenes=yaml.safe_load(plan_path.read_text())["scenes"]
    selected=[scene for scene in scenes if scene.get("profile","base-midi")==profile]
    extra=[Path(command[n+1]) for n,arg in enumerate(command) if arg=="--extra-cases"]
    key=tuple(sorted(str(path) for path in extra))
    if key not in registry_cache:
     registry_cache[key]=load_extra_cases(extra,cases.CASES,ROOT)[0]
    registry=registry_cache[key]
    missing=sorted({scene["behaviour_case"] for scene in selected}-set(registry))
    self.assertFalse(missing,"%s does not load cases %s"%(stage["name"],missing))
    checked.update((plan_path.name,scene["id"]) for scene in selected)
   declared={(path.name,scene["id"])
     for path in (ROOT/"manual").glob("scene-plans*.yaml")
     for scene in yaml.safe_load(path.read_text())["scenes"]}
   self.assertEqual(checked,declared,"every authored manual scene must have a planned capture stage")
  finally:
   if sys.path and sys.path[0]==behaviour:sys.path.pop(0)
 def test_multiple_additive_helpers_are_retained_for_mixed_plans(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/"manual").mkdir()
   (root/"manual/scene-plans-mixed.yaml").write_text("scenes: [{behaviour_case: M-UI-VERTICAL-001}, {behaviour_case: M-MANUAL-COURSE-001}]\n")
   with mock.patch.object(build,"ROOT",root):stages=build.plan(self.options(),["scene-plans-mixed.yaml"])
   for row in [s for s in stages if s["name"].startswith("reference-")]:
    c=row["command"];helpers=[c[n+1] for n,a in enumerate(c) if a=="--extra-cases"]
    self.assertEqual(set(helpers),{str(root/"tools/manual_course_cases.py")})
 def test_doctor_real_audio_lanes_are_audited_before_publication(self):
  stages=build.plan(self.options(),["scene-plans.yaml"])
  manual=next(s for s in stages if s["name"]=="doctor-manual-real")
  auto=next(s for s in stages if s["name"]=="doctor-auto-real")
  publish=next(s for s in stages if s["name"]=="doctor-publish")
  for row in (manual,auto):
   self.assertEqual(row["emulator"],"/native/audio")
   self.assertIn("/native/audio.json",row["command"])
   self.assertNotIn("--publish",row["command"])
  self.assertIn(str(ROOT/"manual/doctor-auto-probe.yaml"),auto["command"])
  self.assertLess(stages.index(manual),stages.index(auto))
  self.assertLess(stages.index(auto),stages.index(publish))
  self.assertTrue(publish["action"]["doctor_publish"])
  self.assertFalse(any(s.get("doctor_capture") and "controlled" in s["name"] for s in stages))
  refresh=next(s for s in stages if s["name"]=="refresh-scene-index")
  self.assertIn("doctor-scenes.json",refresh["action"]["outputs"])
 def test_doctor_stdout_report_must_be_successful_and_confined(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);out=root/"native";out.mkdir();run=out/"uuid";run.mkdir()
   report=run/"report.json";report.write_text('{"passed":true}')
   log=root/"capture.log";log.write_text("native output\n"+json.dumps({"passed":True,"report":str(report)})+"\n")
   accepted=build.doctor_capture_result(log,out)
   self.assertEqual(accepted["path"],str(report.resolve()))
   self.assertEqual(accepted["sha256"],build.digest(report))
   log.write_text(json.dumps({"passed":True,"report":str(root/"outside.json")})+"\n")
   with self.assertRaisesRegex(ValueError,"outside"):build.doctor_capture_result(log,out)
   report.write_text('{"passed":false}')
   log.write_text(json.dumps({"passed":True,"report":str(report)})+"\n")
   with self.assertRaisesRegex(ValueError,"failed"):build.doctor_capture_result(log,out)
 def test_player_routes_regenerate_after_audio_and_remain_indexed(self):
  stages=build.plan(self.options(),["scene-plans.yaml"])
  route=next(s for s in stages if s["name"]=="player-routes")
  audio=next(s for s in stages if s["name"]=="musical-audio")
  refresh=next(s for s in stages if s["name"]=="refresh-scene-index")
  self.assertEqual(route["emulator"],"/native/audio")
  self.assertLess(stages.index(audio),stages.index(route))
  self.assertLess(stages.index(route),stages.index(refresh))
  self.assertIn("player-routes.json",refresh["action"]["outputs"])
 def test_doctor_options_are_seven_mandatory_independent_qualification_stages(self):
  rows=build.plan(self.options(),["scene-plans.yaml"]);names=[s["name"] for s in rows]
  expected={"doctor-options-manual-stereo-real","doctor-options-auto-left-real","doctor-options-manual-right-real","doctor-options-setup-real","doctor-options-setup-controlled","doctor-options-ready-real","doctor-options-ready-controlled"}
  self.assertTrue(expected<=set(names));self.assertIn("doctor-options-audit",names)
  self.assertLess(names.index("doctor-options-manual-right-real"),names.index("doctor-options-ready-real"))
  self.assertLess(names.index("doctor-options-audit"),names.index("compile-book"))
  self.assertEqual(sum(bool(s.get("doctor_options")) for s in rows),7)
 def test_ready_stage_requires_exact_successful_manual_right_fixture_receipt(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);out=root/"doctor-options-manual-right";run=out/"uuid";run.mkdir(parents=True)
   report=run/"report.json";report.write_text(json.dumps(dict(passed=True,publication_kind="doctor-options-qualification",case="manual_right",clock_mode="real-time",complete_regression_run=False)))
   fixture=run/"ready-fixture/fixture.json";fixture.parent.mkdir();fixture.write_text(json.dumps(dict(acquisition_report=str(report),acquisition_report_sha256=build.digest(report))))
   name="doctor-options-manual-right-real";log=root/(name+".log");log.write_text(json.dumps(dict(passed=True,report=str(report),fixture=str(fixture)))+"\n")
   record=dict(name=name,passed=True,returncode=0,log_sha256=build.digest(log),native_report=dict(path=str(report),sha256=build.digest(report)),ready_fixture=dict(path=str(fixture),sha256=build.digest(fixture)))
   (root/(name+".json")).write_text(json.dumps(record))
   with mock.patch.object(build,"qualify_ready_fixture",return_value=None):
    result=build.doctor_ready_arguments(root)
   self.assertEqual(result,["--ready-fixture",str(fixture),"--ready-fixture-sha256",build.digest(fixture)])
   fixture.write_text(fixture.read_text()+"\n")
   with mock.patch.object(build,"qualify_ready_fixture",return_value=None):
    with self.assertRaisesRegex(ValueError,"fixture|receipt"):build.doctor_ready_arguments(root)
 def test_completion_rejects_missing_doctor_option_qualification_gates(self):
  # With a passed reader projection the Doctor qualification gates are still mandatory.
  with self.assertRaisesRegex(ValueError,"Doctor qualification"):
   build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml"],{"complete_manual":True},stages=[reader_projection_record()])
  self.assertFalse(build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml"],{"complete_manual":True},stages=[]))
 def qualification_records(self,root):
  records=[]
  for name in list(build.DOCTOR_OPTION_STAGES)+["doctor-options-audit"]:
   data=dict(passed=True,complete_regression_run=False)
   if name in build.DOCTOR_OPTION_STAGES:
    case,clock,suffix=build.DOCTOR_OPTION_STAGES[name];data.update(case=case,clock_mode=clock,publication_kind="doctor-options-qualification")
   path=root/(name+"-proof.json");path.write_text(json.dumps(data))
   field="qualification_audit" if name=="doctor-options-audit" else "native_report"
   records.append(dict(name=name,passed=True,returncode=0,**{field:dict(path=str(path),sha256=build.digest(path))}))
  return records
 def test_doctor_option_audio_and_ui_installations_are_separate(self):
  rows=[r for r in build.plan(self.options(),["scene-plans.yaml"]) if r.get("doctor_options")]
  for row in rows:
   contract=row["doctor_options"];command=row["command"]
   expected="/native/audio.json" if contract["clock_mode"]=="real-time" else "/native/control.json"
   self.assertEqual(command[command.index("--installation")+1],expected)
   self.assertEqual(row["emulator"],"/native/audio");self.assertFalse(row["exclusive_lock"])
   if contract["case"] not in ("setup_options","ready_options"):self.assertEqual(contract["clock_mode"],"real-time")
   if contract["case"]=="manual_right":self.assertIn("--save-ready-fixture",command)
   if contract["case"]=="ready_options":self.assertTrue(row["action"]["doctor_ready"])
 def test_doctor_option_completion_rejects_failed_or_relabelled_gate(self):
  with tempfile.TemporaryDirectory() as folder:
   records=self.qualification_records(Path(folder));records[0]["passed"]=False
   with self.assertRaisesRegex(ValueError,"Doctor qualification"):build.verify_doctor_completion(records)
   records=self.qualification_records(Path(folder));path=Path(records[0]["native_report"]["path"])
   data=json.loads(path.read_text());data["publication_kind"]="doctor-native-audio";path.write_text(json.dumps(data));records[0]["native_report"]["sha256"]=build.digest(path)
   with self.assertRaisesRegex(ValueError,"role"):build.verify_doctor_completion(records)
 def test_doctor_options_result_cannot_be_an_ordinary_doctor_publication(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);run=root/"uuid";run.mkdir();report=run/"report.json"
   report.write_text(json.dumps(dict(passed=True,publication_kind="doctor-native-audio",case="manual_stereo",clock_mode="real-time",complete_regression_run=False)))
   log=root/"capture.log";log.write_text(json.dumps(dict(passed=True,report=str(report),fixture=None))+"\n")
   with self.assertRaisesRegex(ValueError,"role"):build.doctor_options_result(log,root,"manual_stereo","real-time")
 def doctor_option_records(self,evidence):
  fixture=None
  for name,(case,clock,suffix) in build.DOCTOR_OPTION_STAGES.items():
   run=evidence/suffix/"uuid";run.mkdir(parents=True);report=run/"report.json"
   doc=dict(passed=True,publication_kind="doctor-options-qualification",case=case,clock_mode=clock,complete_regression_run=False)
   if case=="ready_options":doc["ready_fixture"]={"path":str(fixture),"sha256":build.digest(fixture)}
   report.write_text(json.dumps(doc))
   exported=None
   if case=="manual_right":
    fixture=run/"ready-fixture/fixture.json";fixture.parent.mkdir();fixture.write_text(json.dumps(dict(acquisition_report=str(report),acquisition_report_sha256=build.digest(report))));exported=str(fixture)
   log=evidence/(name+".log");log.write_text(json.dumps(dict(passed=True,report=str(report),fixture=exported))+"\n")
   record=dict(name=name,passed=True,returncode=0,log_sha256=build.digest(log),native_report=dict(path=str(report),sha256=build.digest(report)))
   if case in ("manual_right","ready_options"):record["ready_fixture"]={"path":str(fixture),"sha256":build.digest(fixture)}
   (evidence/(name+".json")).write_text(json.dumps(record))
  return fixture
 def test_doctor_audit_command_requires_all_exact_stage_report_paths(self):
  with tempfile.TemporaryDirectory() as folder:
   evidence=Path(folder);fixture=self.doctor_option_records(evidence)
   with mock.patch.object(build,"qualify_ready_fixture",return_value=None):command=build.doctor_options_audit_command(evidence,"python3")
   flags=dict(zip(command[2::2],command[3::2]))
   for role,name in build.DOCTOR_AUDIT_ROLES.items():
    record=json.loads((evidence/(name+".json")).read_text())
    self.assertEqual(flags["--"+role.replace("_","-")+"-report"],record["native_report"]["path"])
   self.assertEqual(flags["--fixture"],str(fixture));self.assertEqual(flags["--fixture-sha256"],build.digest(fixture))
   (evidence/"doctor-options-setup-controlled.json").unlink()
   with mock.patch.object(build,"qualify_ready_fixture",return_value=None):
    with self.assertRaises(FileNotFoundError):build.doctor_options_audit_command(evidence,"python3")
 def test_ready_process_arguments_resolve_only_manual_right_current_stage(self):
  with tempfile.TemporaryDirectory() as folder:
   evidence=Path(folder);fixture=self.doctor_option_records(evidence)
   stage=next(s for s in build.plan(self.options(),["scene-plans.yaml"]) if s["name"]=="doctor-options-ready-controlled")
   with mock.patch.object(build,"qualify_ready_fixture",return_value=None):command=build.stage_command(stage,evidence)
   self.assertEqual(command[command.index("--ready-fixture")+1],str(fixture));self.assertEqual(command[command.index("--ready-fixture-sha256")+1],build.digest(fixture))
   record_path=evidence/"doctor-options-manual-right-real.json";record=json.loads(record_path.read_text());record["passed"]=False;record_path.write_text(json.dumps(record))
   with mock.patch.object(build,"qualify_ready_fixture",return_value=None):
    with self.assertRaisesRegex(ValueError,"stage receipt"):build.stage_command(stage,evidence)
 def test_ordinary_doctor_success_cannot_complete_option_qualification(self):
  with tempfile.TemporaryDirectory() as folder:
   records=self.qualification_records(Path(folder));records[-1]["name"]="doctor-publish"
   with self.assertRaisesRegex(ValueError,"seven gates"):build.verify_doctor_completion(records)
 def test_readability_plan_replays_the_same_canonical_case_in_both_lanes(self):
  stages=build.plan(self.options(),["scene-plans-readability.yaml"])
  rows=[s for s in stages if s["name"].startswith("reference-")]
  self.assertEqual(len(rows),2)
  for row in rows:
   command=row["command"];self.assertNotIn("--extra-cases",command)
   self.assertIn(str(ROOT/"manual/scene-plans-readability.yaml"),command)
  plan=__import__("yaml").safe_load((ROOT/"manual/scene-plans-readability.yaml").read_text())
  self.assertEqual(plan["scenes"][0]["behaviour_case"],"M-UI-READABILITY-001")
  # All seventeen reviewed acceptance checkpoints stay; teaching steps (e.g. the prepared start) may be added.
  import manual_feature_bind
  ids=[s["id"] for s in plan["scenes"][0]["steps"]]
  self.assertEqual(len(manual_feature_bind.READABILITY_CHECKPOINTS),17);self.assertLessEqual(set(manual_feature_bind.READABILITY_CHECKPOINTS),set(ids));self.assertEqual(len(ids),len(set(ids)))

# Between-stage coordination; characterisation outside the instrument manual.
MODULE=ROOT/"tools/manual_build.py"
class StageGates(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.evidence=self.root/"evidence";self.evidence.mkdir()
  self.options=SimpleNamespace(stage_gate_dir=self.root/"gates")
  self.stage=dict(name="capture-real",command=["python","capture.py"],emulator="native",exclusive_lock=False,action=None)
 def setup_gate(self):build.prepare_stage_gate(self.options,self.evidence)
 def answer(self,mutation=None):
  requests=list(self.options.stage_gate_dir.glob("*.request.json"));self.assertEqual(len(requests),1)
  request=requests[0];value=json.loads(request.read_text());blob=request.read_bytes()
  expected=dict(request_sha256=hashlib.sha256(blob).hexdigest(),**build.gate_owner(self.evidence),stage_index=value["stage_index"],stage_name=value["stage_name"],argv_sha256=value["argv_sha256"],nonce=value["nonce"])
  if mutation:mutation(expected)
  request.with_name(request.name.replace(".request.json",".resume.json")).write_text(json.dumps(expected))
 def wait(self,answer=None,index=1,completed=None):
  with mock.patch.object(build.time,"sleep",side_effect=lambda _: self.answer(answer)):
   build.await_stage_gate(self.stage,index,self.evidence,self.options,completed or [])
 def test_cli_exposes_opt_in_without_launching_native(self):
  result=subprocess.run([sys.executable,str(MODULE),"--help"],capture_output=True,text=True)
  self.assertEqual(result.returncode,0);self.assertIn("--stage-gate-dir",result.stdout)
 def test_default_off_creates_no_files_and_resolves_no_commands(self):
  options=SimpleNamespace()
  with mock.patch.object(build,"stage_command",side_effect=AssertionError("default resolved command")):
   build.prepare_stage_gate(options,self.evidence);build.await_stage_gate(self.stage,1,self.evidence,options,[])
  self.assertEqual(list(self.evidence.iterdir()),[])
 def test_unique_directory_rejects_reusing_previous_build(self):
  self.setup_gate()
  with self.assertRaises(FileExistsError):self.setup_gate()
 def test_matching_resume_archives_exact_request_and_release(self):
  self.setup_gate();self.wait()
  proof=json.loads(next((self.evidence/"stage-gates").glob("*.json")).read_text())
  self.assertEqual(proof["request"]["stage_index"],1)
  self.assertEqual(proof["request"]["stage_name"],"capture-real")
  self.assertEqual(proof["request"]["argv_sha256"],hashlib.sha256(build.gate_blob(self.stage["command"])).hexdigest())
  self.assertEqual(proof["request"]["pid"],os.getpid())
 def test_wrong_resume_fields_never_release(self):
  for field in ["pid","proc_starttime","evidence_dir","stage_index","stage_name","argv_sha256","nonce","request_sha256"]:
   with self.subTest(field=field),tempfile.TemporaryDirectory() as directory:
    self.options.stage_gate_dir=Path(directory)/"gates";self.setup_gate()
    with self.assertRaisesRegex(ValueError,"identity mismatch"):self.wait(lambda value:value.__setitem__(field,"wrong"))
 def test_stale_release_does_not_match_fresh_random_request(self):
  self.setup_gate();(self.options.stage_gate_dir/"001-stale.resume.json").write_text('{}')
  self.wait();self.assertEqual(len(list(self.options.stage_gate_dir.glob("*.request.json"))),1)
 def test_failed_prior_stage_never_requests_next(self):
  self.setup_gate()
  with self.assertRaisesRegex(ValueError,"preceding stage"):
   self.wait(index=2,completed=[dict(name="prior",passed=False)])
  self.assertEqual(list(self.options.stage_gate_dir.glob("*.request.json")),[])
 def test_missing_prior_stage_never_allows_skip(self):
  self.setup_gate()
  with self.assertRaisesRegex(ValueError,"preceding stage"):self.wait(index=2)
  self.assertEqual(list(self.options.stage_gate_dir.glob("*.request.json")),[])
 def test_prior_terminal_receipt_must_match_before_request(self):
  self.setup_gate();previous=dict(name="prior",passed=True,returncode=0)
  path=self.evidence/"prior.json";path.write_text(json.dumps(dict(previous,passed=False)))
  with self.assertRaisesRegex(ValueError,"receipt changed"):self.wait(index=2,completed=[previous])
  path.write_text(json.dumps(previous));self.wait(index=2,completed=[previous])
  request=json.loads(next(self.options.stage_gate_dir.glob("*.request.json")).read_text())
  self.assertEqual(request["previous_receipt"]["sha256"],build.digest(path))
 def test_owner_change_rejected_before_request(self):
  self.setup_gate();(self.options.stage_gate_dir/"owner.json").write_text('{}')
  with self.assertRaisesRegex(ValueError,"owner changed"):self.wait()
  self.assertEqual(list(self.options.stage_gate_dir.glob("*.request.json")),[])
 def test_gate_is_outside_native_stdout_drain_and_before_stage_launch(self):
  source=MODULE.read_text();tree=ast.parse(source)
  stage=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="run_stage")
  self.assertNotIn("await_stage_gate",ast.get_source_segment(source,stage))
  # The stage loop lives in run_build_stages (called from main); the gate must still precede each launch there.
  loop=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="run_build_stages")
  calls=[n for n in ast.walk(loop) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
  gate=next(n for n in calls if n.func.id=="await_stage_gate");launch=next(n for n in calls if n.func.id=="run_stage")
  self.assertLess(gate.lineno,launch.lineno)
 def test_planning_and_native_pipe_drain_are_unchanged(self):
  # Frozen original AST identities avoid importing a second fixture module.
  # The planner has an intentional additive case-route change. Pin its exact
  # source segment so this assertion is identical under every supported Python.
  # stage_command and run_stage retain their reviewed per-version AST pins.
  expected={'plan_source': '5256b12ac835374d4e819b2a7aa387edf7252acbb6a20a1e1e7009b3d3116566', 'stage_command': {(3,8): '22493e17bf42d6d3f55b23e5dd811ae88b11e2c294d1d9157511f5113b405ca6', (3,11): '33bf4501400164ff560fcaeac4d116b7498ba94f6e35f36bcd439cc68738f5e0'}, 'run_stage': {(3,8): '1e9e336208e2984f2398337a64016ec12d3f3b78cee671a992905480c654bd4e', (3,11): '45e39ed119b3eafc264bf891046f380f6fcac75d7cfd015e2f9f641e32f7289c'}}
  source=MODULE.read_text();candidate=ast.parse(source)
  function=next(n for n in candidate.body if isinstance(n,ast.FunctionDef) and n.name=="plan")
  self.assertEqual(hashlib.sha256(ast.get_source_segment(source,function).encode()).hexdigest(),expected["plan_source"])
  for name in ("stage_command","run_stage"):
   value=expected[name]
   self.assertIn(sys.version_info[:2],value,"No frozen %s AST pin for this Python; freeze one from the reviewed source"%name);value=value[sys.version_info[:2]]
   function=next(n for n in candidate.body if isinstance(n,ast.FunctionDef) and n.name==name)
   self.assertEqual(hashlib.sha256(ast.dump(function,include_attributes=False).encode()).hexdigest(),value)
 def test_failed_child_in_main_never_requests_following_stage(self):
  root=self.root/"app";(root/"manual/generated").mkdir(parents=True)
  options=SimpleNamespace(stage_gate_dir=None,resume_from=None,resume_manifest_sha256=None,artifacts=self.root/"runs",plans=["scene-plans.yaml"],plan_only=False,browser_tests=False,real_install="/native/qualified-real.json",adopt_audio_report=None,adopt_audio_report_sha256=None,retained_midi_admissions=None,retained_midi_admissions_sha256=None)
  second=dict(self.stage,name="next-capture")
  def fail(stage,evidence,*args):
   (evidence/(stage["name"]+".json")).write_text(json.dumps(dict(stage,passed=False,returncode=1)))
   raise RuntimeError("native failed")
  import contextlib
  with mock.patch.object(build,"ROOT",root),mock.patch.object(build.argparse.ArgumentParser,"parse_args",return_value=options),mock.patch.object(build,"plan",return_value=[self.stage,second]),mock.patch.object(build,"preview",return_value=contextlib.nullcontext(None)),mock.patch.object(build.subprocess,"check_output",return_value="revision"),mock.patch.object(build,"await_stage_gate") as gate,mock.patch.object(build,"run_stage",side_effect=fail):
   with self.assertRaisesRegex(RuntimeError,"native failed"):build.main()
  self.assertEqual(gate.call_count,1);self.assertEqual(gate.call_args.args[1],1)
  manifest=json.loads(next(options.artifacts.glob("*/manifest.json")).read_text())
  self.assertFalse(manifest["passed"]);self.assertEqual([x["name"] for x in manifest["stages"]],[self.stage["name"]])
 def test_default_off_main_runs_every_stage_in_order(self):
  root=self.root/"app";(root/"manual/generated").mkdir(parents=True)
  (root/"manual/generated/book.json").write_text('{}')
  options=SimpleNamespace(stage_gate_dir=None,resume_from=None,resume_manifest_sha256=None,artifacts=self.root/"runs",plans=["scene-plans.yaml"],plan_only=False,browser_tests=False,real_install="/native/qualified-real.json",adopt_audio_report=None,adopt_audio_report_sha256=None,retained_midi_admissions=None,retained_midi_admissions_sha256=None)
  stages=[dict(self.stage,name=f"capture-{index}") for index in range(72)]
  seen=[]
  def finish(stage,evidence,*args):
   seen.append(stage["name"]);record=dict(stage,passed=True,returncode=0)
   (evidence/(stage["name"]+".json")).write_text(json.dumps(record));return record
  import contextlib
  with mock.patch.object(build,"ROOT",root),mock.patch.object(build.argparse.ArgumentParser,"parse_args",return_value=options),mock.patch.object(build,"plan",return_value=stages),mock.patch.object(build,"preview",return_value=contextlib.nullcontext(None)),mock.patch.object(build.subprocess,"check_output",return_value="revision"),mock.patch.object(build,"run_stage",side_effect=finish),mock.patch.object(build,"complete_build",return_value=True):
   self.assertEqual(build.main(),0)
  self.assertEqual(seen,[stage["name"] for stage in stages]);self.assertFalse((self.root/"gates").exists())
 def test_prior_receipt_mutated_during_wait_rejects_resume(self):
  self.setup_gate();previous=dict(name="prior",passed=True,returncode=0)
  path=self.evidence/"prior.json";path.write_text(json.dumps(previous))
  def mutate(value):path.write_text(json.dumps(dict(previous,returncode=1)))
  with self.assertRaisesRegex(ValueError,"Prior stage receipt changed"):
   self.wait(mutate,index=2,completed=[previous])
  self.assertFalse((self.evidence/"stage-gates").exists())
 def test_equivalent_numeric_resume_types_are_rejected(self):
  for field,value in [("stage_index",True),("stage_index",1.0),("pid",float(os.getpid()))]:
   with self.subTest(field=field,value=value),tempfile.TemporaryDirectory() as directory:
    self.options.stage_gate_dir=Path(directory)/"gates";self.setup_gate()
    with self.assertRaisesRegex(ValueError,"identity mismatch"):
     self.wait(lambda resume:resume.__setitem__(field,value))

class ControlledLocalAssets(unittest.TestCase):
 def module(self):
  sys.path.insert(0,str(ROOT/"tools"))
  spec=importlib.util.spec_from_file_location("manual_capture",ROOT/"tools/manual_capture.py")
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def test_audio_is_carried_forward_only_with_matching_source_and_file_hashes(self):
  module=self.module()
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/"manual/generated").mkdir(parents=True);(root/"manual/audio").mkdir()
   asset=root/"manual/audio/lesson.ogg";asset.write_bytes(b"verified audio")
   publication=root/"manual/generated/pilot.json";audio={"files":["audio/lesson.ogg"],"title":"existing source-bound audio"}
   publication.write_text(json.dumps({"source_sha256":"source-pin","audio":audio}))
   result={};proof=module.preserve_published_audio(result,"source-pin",publication,root/"manual")
   self.assertEqual(result["audio"],audio)
   self.assertEqual(proof["file_sha256"]["audio/lesson.ogg"],hashlib.sha256(b"verified audio").hexdigest())
   with self.assertRaisesRegex(ValueError,"different authored source"):
    module.preserve_published_audio({},"different-source",publication,root/"manual")

if __name__=="__main__":unittest.main()
