"""Build orchestration contracts; characterisation outside the manual."""
import importlib.util,unittest,tempfile,sys,json,subprocess
from unittest import mock
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("manual_build",ROOT/"tools/manual_build.py")
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
class BuildPlan(unittest.TestCase):
 def test_completion_rejects_an_incomplete_book_even_with_all_plans_and_browser_checks(self):
  with self.assertRaisesRegex(ValueError,"incomplete"):
   build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml"],{"complete_manual":False})
 def test_completion_requires_browser_and_entire_required_plan_inventory(self):
  book={"complete_manual":True}
  self.assertFalse(build.complete_build(False,["scene-plans.yaml"],["scene-plans.yaml"],book))
  self.assertFalse(build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml","scene-plans-course.yaml"],book))
  with tempfile.TemporaryDirectory() as folder:
   records=self.qualification_records(Path(folder))
   self.assertTrue(build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml"],book,records))
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
  self.assertEqual(len([name for name in names if name.startswith("browser-")]),7)
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
  with self.assertRaisesRegex(ValueError,"Doctor qualification"):
   build.complete_build(True,["scene-plans.yaml"],["scene-plans.yaml"],{"complete_manual":True},stages=[])
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
  self.assertEqual(len(plan["scenes"][0]["steps"]),17)
if __name__=="__main__":unittest.main()
