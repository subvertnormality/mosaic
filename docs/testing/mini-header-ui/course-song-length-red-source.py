"""Course evidence promotion contracts; characterisation outside instrument manual."""
import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import yaml
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("manual_course_bind",ROOT/"tools/manual_course_bind.py")
binder=importlib.util.module_from_spec(spec);spec.loader.exec_module(binder)
class CourseBinding(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);(self.root/"manual").mkdir()
  for name in ("course.yaml","course.schema.json","scene-plans-course.yaml"):(self.root/"manual"/name).write_bytes((ROOT/"manual"/name).read_bytes())
  self.course=yaml.safe_load((self.root/"manual/course.yaml").read_text());self.plan=yaml.safe_load((self.root/"manual/scene-plans-course.yaml").read_text())
  self.documents=[]
  for clock in ("real-time","controlled-experimental"):
   context=dict(session_ordinal=0,clock_mode=clock,session_id=clock,finished=True,cleanup_verified=True,held_inputs=[])
   evidence=dict(path=str(self.root/clock),session_context=context,case_participants=[dict(path=str(self.root/clock),session_context=context)])
   scenes=[dict(id=s["id"],feature_id=s["feature_id"],behaviour_case=s["behaviour_case"],session_ordinal=0,evidence=copy.deepcopy(evidence),steps=[dict(id=st["id"],output=dict(binding=dict(passed=True,semantic_assertions=["native proof"],sha256="frame",grid_sha256="grid",assertion=st["assertion"]))) for st in s["steps"]]) for s in self.plan["scenes"]]
   doc=dict(clock_mode=clock,selected_scene_ids=[s["id"] for s in scenes],scenes=scenes,complete_regression_run=False)
   path=self.root/(clock+".json");path.write_text(json.dumps(doc));self.documents.append(path)
 def bind(self,verify=False):
  with patch.object(binder,"audit_reference",return_value=50):return binder.bind(*self.documents,self.root/"proof",root=self.root,verify_only=verify)
 def mutate(self,change):
  path=self.documents[0];data=json.loads(path.read_text());change(data);path.write_text(json.dumps(data))
 def test_missing_checkpoint_cannot_promote_or_mutate_course(self):
  before=(self.root/"manual/course.yaml").read_bytes();self.mutate(lambda d:d["scenes"][0]["steps"].pop())
  with self.assertRaisesRegex(ValueError,"checkpoint"):self.bind()
  self.assertEqual(before,(self.root/"manual/course.yaml").read_bytes());self.assertFalse((self.root/"proof").exists())
 def test_split_session_rejected(self):
  self.mutate(lambda d:d["scenes"][1]["evidence"]["session_context"].update(session_id="different"))
  with self.assertRaisesRegex(ValueError,"continuous"):self.bind()
 def test_wrong_lane_or_cleanup_rejected(self):
  self.mutate(lambda d:d.update(clock_mode="controlled-experimental"))
  with self.assertRaisesRegex(ValueError,"clock"):self.bind()
 def test_failed_independent_audit_keeps_pending(self):
  before=(self.root/"manual/course.yaml").read_bytes()
  with patch.object(binder,"audit_reference",side_effect=ValueError("native mismatch")):
   with self.assertRaisesRegex(ValueError,"native mismatch"):binder.bind(*self.documents,self.root/"proof",root=self.root)
  self.assertEqual(before,(self.root/"manual/course.yaml").read_bytes())
 def test_complete_audited_course_binds_exactly_and_records_evidence(self):
  result=self.bind();course=yaml.safe_load((self.root/"manual/course.yaml").read_text())
  self.assertEqual(course["project"]["capture_status"],"verified");self.assertEqual(len(result["mappings"]),38)
  for chapter in course["learning_path"]:
   for stage in chapter["stages"]:self.assertEqual(stage["binding"],dict(status="verified",scene="course-"+chapter["id"],step=stage["id"]))
  original=yaml.safe_load((self.root/"proof/course-before.yaml").read_text())
  for chapter in course["learning_path"]:
   for stage in chapter["stages"]:stage["binding"]=dict(status="pending",scene=None,step=None)
  course["project"]["capture_status"]="pending";self.assertEqual(course,original)
  self.assertNotEqual(result["course_before_sha256"],result["course_after_sha256"])
 def test_verified_binding_to_unrelated_scene_rejected(self):
  c=copy.deepcopy(self.course);c["learning_path"][0]["stages"][0]["binding"].update(status="verified",scene="unrelated",step="other")
  (self.root/"manual/course.yaml").write_text(yaml.safe_dump(c))
  with self.assertRaisesRegex(ValueError,"mapping"):self.bind(verify=True)
 def test_duplicate_scene_and_unverified_binding_rejected(self):
  self.mutate(lambda d:d["scenes"].append(copy.deepcopy(d["scenes"][0])))
  with self.assertRaisesRegex(ValueError,"scene"):self.bind()

 def test_missing_cleanup_or_semantic_proof_rejected(self):
  self.mutate(lambda d:d["scenes"][0]["evidence"]["session_context"].update(cleanup_verified=False))
  with self.assertRaisesRegex(ValueError,"cleanup"):self.bind()
 def test_wrong_case_owner_rejected(self):
  self.mutate(lambda d:d["scenes"][0].update(behaviour_case="M-OTHER-001"))
  with self.assertRaisesRegex(ValueError,"ownership"):self.bind()
 def test_wrong_checkpoint_selector_rejected(self):
  self.mutate(lambda d:d["scenes"][0]["steps"][0]["output"]["binding"]["assertion"].update(stage="other"))
  with self.assertRaisesRegex(ValueError,"selector"):self.bind()
 def test_failed_semantic_binding_rejected(self):
  self.mutate(lambda d:d["scenes"][0]["steps"][0]["output"]["binding"].update(passed=False))
  with self.assertRaisesRegex(ValueError,"semantic proof"):self.bind()
 def test_verify_only_requires_and_preserves_verified_course(self):
  self.bind();before=(self.root/"manual/course.yaml").read_bytes()
  with patch.object(binder,"audit_reference",return_value=50):
   result=binder.bind(*self.documents,self.root/"second-proof",root=self.root,verify_only=True)
  self.assertTrue(result["passed"]);self.assertFalse(result["course_written"])
  self.assertEqual(before,(self.root/"manual/course.yaml").read_bytes())
 def test_changed_inputs_during_audit_rejected(self):
  before=(self.root/"manual/course.yaml").read_bytes()
  def changed(document):
   (self.root/"manual/course.yaml").write_bytes(before+b"\n");return 48
  with patch.object(binder,"audit_reference",side_effect=changed):
   with self.assertRaisesRegex(ValueError,"inputs changed"):binder.bind(*self.documents,self.root/"proof",root=self.root)
  self.assertFalse((self.root/"proof").exists())
 def test_existing_evidence_directory_not_overwritten(self):
  proof=self.root/"proof";proof.mkdir();(proof/"original").write_text("keep")
  before=(self.root/"manual/course.yaml").read_bytes()
  with self.assertRaises(FileExistsError):self.bind()
  self.assertEqual(before,(self.root/"manual/course.yaml").read_bytes());self.assertEqual((proof/"original").read_text(),"keep")

 def test_durable_publication_verifies_without_artifact_writes(self):
  self.bind();publication=self.root/"manual/generated/course-binding.json"
  self.assertTrue(publication.exists())
  before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
  with patch.object(binder,"audit_reference",return_value=50):result=binder.verify_publication(root=self.root)
  self.assertTrue(result["passed"])
  after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
  self.assertEqual(before,after)
 def test_durable_publication_rejects_changed_report(self):
  self.bind();self.documents[1].write_bytes(self.documents[1].read_bytes()+b"\n")
  with patch.object(binder,"audit_reference",return_value=50):
   with self.assertRaisesRegex(ValueError,"report"):binder.verify_publication(root=self.root)
 def test_durable_publication_rejects_changed_course_or_receipt(self):
  self.bind();p=self.root/"manual/course.yaml";p.write_bytes(p.read_bytes()+b"\n")
  with patch.object(binder,"audit_reference",return_value=50):
   with self.assertRaisesRegex(ValueError,"course"):binder.verify_publication(root=self.root)
 def test_durable_publication_rejects_forged_mapping(self):
  self.bind();p=self.root/"manual/generated/course-binding.json";d=json.loads(p.read_text());d["mappings"][0]["scene"]="unrelated";p.write_text(json.dumps(d))
  with patch.object(binder,"audit_reference",return_value=50):
   with self.assertRaisesRegex(ValueError,"receipt|mapping"):binder.verify_publication(root=self.root)

 def test_durable_publication_reaudits_both_native_reports(self):
  self.bind()
  with patch.object(binder,"audit_reference",side_effect=[50,ValueError("controlled native failure")]) as audited:
   with self.assertRaisesRegex(ValueError,"controlled native failure"):binder.verify_publication(root=self.root)
  self.assertEqual(audited.call_count,2)
 def test_durable_publication_requires_full_independent_checkpoint_count(self):
  self.bind()
  with patch.object(binder,"audit_reference",return_value=49):
   with self.assertRaisesRegex(ValueError,"omitted"):binder.verify_publication(root=self.root)
 def test_verify_only_does_not_replace_durable_receipt(self):
  self.bind();p=self.root/"manual/generated/course-binding.json";before=p.read_bytes()
  with patch.object(binder,"audit_reference",return_value=50):binder.bind(*self.documents,self.root/"verify-proof",root=self.root,verify_only=True)
  self.assertEqual(before,p.read_bytes())

 def test_visible_tempo_stage_is_required_for_complete_course(self):
  course=copy.deepcopy(self.course);chapter=next(c for c in course["learning_path"] if c["id"]=="setup")
  chapter["stages"]=[s for s in chapter["stages"] if s["id"]!="setup-tempo"]
  (self.root/"manual/course.yaml").write_text(yaml.safe_dump(course))
  with self.assertRaisesRegex(ValueError,"38 distinct teaching stages"):self.bind()

# Course public recipe against the unchanged actual Lua Rate owner.
import ast
import subprocess
class CourseRateRecipe(unittest.TestCase):
    def test_bar_recipe_keeps_sixteenth_note_rate_through_actual_owner(self):
        tree = ast.parse((ROOT / 'tools/manual_course_cases.py').read_text())
        course = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'course')
        def stage(n, function, name):
            return isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) and n.value.func.id == function and len(n.value.args)>1 and isinstance(n.value.args[1], ast.Constant) and n.value.args[1].value == name
        start = next(i for i,n in enumerate(course.body) if stage(n,'musical','first-sound-hear'))
        stop = next(i for i,n in enumerate(course.body) if stage(n,'checkpoint','build-a-phrase-range'))
        detents = []
        for statement in course.body[start+1:stop]:
            for call in ast.walk(statement):
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id=='c' and call.func.attr=='enc' and ast.literal_eval(call.args[0])==3:
                    detents.append(ast.literal_eval(call.args[1]))
        owner = ROOT / 'lib/pages/channel_edit_page/channel_edit_clock_controls.lua'
        code = """
local selector={position=13};function selector:is_selected()return true end
function selector:increment()self.position=math.min(47,self.position+1)end
function selector:decrement()self.position=math.max(1,self.position-1)end
local off={is_selected=function()return false end}
local controls={clock_mod_list_selector=selector,swing_shuffle_type_selector=off,swing_selector=off,shuffle_feel_selector=off,shuffle_basis_selector=off,shuffle_amount_selector=off}
save_confirm={set_save=function()end,set_cancel=function()end}
local controller=dofile(%s).new(controls,{},{})
for _,steps in ipairs({%s})do for i=1,math.abs(steps)do
 if steps>0 then controller.handle_increment()else controller.handle_decrement()end
end end
print(selector.position)
""" % (json.dumps(str(owner)), ','.join(map(str,detents)))
        actual = subprocess.run(['lua5.3','-e',code],check=True,capture_output=True,text=True)
        self.assertEqual(int(actual.stdout.strip()),13,'four attacks at steps 1/5/9/13 require Rate /1, not /15 or /4')
        selected = next(k.value for k in course.body[stop].value.keywords if k.arg=='selected')
        self.assertEqual(next(ast.literal_eval(k.value) for k in selected.keywords if k.arg=='value'),'/1')



class CourseOctaveRouteRecipe(unittest.TestCase):
    def test_bass_checkpoint_follows_actual_public_octave_route(self):
        import ui_map
        tree=ast.parse((ROOT/'tools/manual_course_cases.py').read_text())
        course=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='course')
        stop=next(i for i,n in enumerate(course.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='checkpoint' and ast.literal_eval(n.value.args[1])=='sequence-composition-bass-route')
        gestures=[n for statement in course.body[:stop] for n in ast.walk(statement) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='tap_control']
        final=gestures[-1];control=ast.literal_eval(final.args[0]);octave=ast.literal_eval(final.args[1])
        self.assertEqual((control,octave),('channel_octave',-1))
        self.assertEqual(ui_map.control_cell(control,octave),(9,8))
        actual_route=json.loads((ROOT/'docs/ui-reimplementation/spec.json').read_text())['flows']['G14']['new']['screen']
        checkpoint=course.body[stop].value
        page=ast.literal_eval(checkpoint.args[2]);params=ast.literal_eval(checkpoint.args[3])
        self.assertEqual(ui_map.LIVE_SCREENS[page]['screen'],actual_route,'G14 octave feedback is C01 Masks, not C09 Merge')
        self.assertEqual(params,{'channel':2,'octave':-1})
        leds=next(ast.literal_eval(k.value) for k in checkpoint.keywords if k.arg=='leds')
        self.assertEqual(leds,[(9,8,15)])

class CourseScaleDraftLifetimeRecipe(unittest.TestCase):
    def test_actual_grid_press_preserves_the_course_draft_until_apply(self):
        tree=ast.parse((ROOT/'tools/manual_course_cases.py').read_text())
        course=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='course')
        def named(n,fn,stage):
            return isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id==fn and len(n.value.args)>1 and isinstance(n.value.args[1],ast.Constant) and n.value.args[1].value==stage
        end=next(i for i,n in enumerate(course.body) if named(n,'musical','harmony-design-apply-d'))
        start=next(i for i,n in enumerate(course.body) if named(n,'musical','harmony-design-relative'))
        commands=[]
        for statement in course.body[start+1:end]:
            if named(statement,'musical','harmony-design-draft'):
                commands.append('press:handle(1,1,8);press:handle(1,1,8)')
            for call in ast.walk(statement):
                if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Attribute):continue
                owner=call.func.value
                if isinstance(owner,ast.Name) and owner.id=='c' and call.func.attr=='enc' and ast.literal_eval(call.args[0])==3:
                    self.assertEqual(ast.literal_eval(call.args[1]),2)
                    commands.append('draft=2;save_confirm.set_cancel(function()draft=stored end);save_confirm.set_save(function()stored=draft end)')
                elif isinstance(owner,ast.Name) and owner.id=='ui' and call.func.attr=='press_key' and ast.literal_eval(call.args[0])==3:
                    commands.append('save_confirm.confirm()')
        code="""
fn={find_key=function()return 'scale' end};pages={pages={}};tooltip={show=function()end};autosave_reset=function()end
save_confirm=dofile(%s);local press=dofile(%s);press:register('menu',function()end);press:register('scale',function()end)
local stored=0;local draft=0
%s
print(stored)
""" % (json.dumps(str(ROOT/'lib/ui_components/save_confirm.lua')),json.dumps(str(ROOT/'lib/press.lua')),';'.join(commands))
        actual=subprocess.run(['lua5.3','-e',code],check=True,capture_output=True,text=True)
        self.assertEqual(int(actual.stdout.strip()),2,'listen to the stored C scale before staging D; grid transport cancels an unapplied draft')

class CourseSongSelectionRouteRecipe(unittest.TestCase):
    def test_stopped_song_selection_checkpoint_uses_slot_setup_and_selected_led(self):
        import ui_map
        tree=ast.parse((ROOT/'tools/manual_course_cases.py').read_text())
        course=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='course')
        stop=next(i for i,n in enumerate(course.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='checkpoint' and ast.literal_eval(n.value.args[1])=='song-composition-copy')
        calls=[n for n in ast.walk(course.body[stop-1]) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='tap_control']
        last=calls[-1];self.assertEqual(tuple(ast.literal_eval(a)for a in last.args),('song_pattern_slot',2))
        self.assertEqual(ui_map.control_cell('song_pattern_slot',2),(2,1))
        route=json.loads((ROOT/'docs/ui-reimplementation/spec.json').read_text())['flows']['G36']['new']
        self.assertEqual(next(a['screen']for a in route['alternatives']if a['when']=={'outcome':'selected_stopped'}),'A01')
        call=course.body[stop].value
        self.assertEqual(ast.literal_eval(call.args[2]),'song_setup','stopped slot selection follows G36 to Slot Setup, not Song Playback')
        self.assertEqual(ast.literal_eval(call.args[3]),{'song_slot':2})
        self.assertEqual(next(ast.literal_eval(k.value)for k in call.keywords if k.arg=='leds'),[(2,1,15)])

class CourseSongLengthRecipe(unittest.TestCase):
    def test_public_song_length_recipe_sets_one_bar_through_actual_fader(self):
        import ui_map
        tree=ast.parse((ROOT/'tools/manual_course_cases.py').read_text())
        course=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='course')
        loop=next(n for n in course.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='slot')
        positions=[]
        def visit(statements):
            for n in statements:
                if isinstance(n,ast.For):
                    for _ in range(*[ast.literal_eval(a)for a in n.iter.args]):visit(n.body)
                else:
                    for c in ast.walk(n):
                        if isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and c.func.attr=='tap_control' and c.args and isinstance(c.args[0],ast.Constant) and c.args[0].value=='global_pattern_length':positions.append(ui_map.control_cell('global_pattern_length',ast.literal_eval(c.args[1])))
        visit(loop.body)
        code='local f=dofile(%s):new(1,7,8,64);f:set_value(64);%s;print(f:get_value())' % (json.dumps(str(ROOT/'lib/controls/fader.lua')),';'.join('f:press(%d,%d)' % cell for cell in positions))
        actual=subprocess.run(['lua5.3','-e',code],check=True,capture_output=True,text=True)
        self.assertEqual(int(actual.stdout.strip()),16,'physical column2 sets one step; a section needs16')
