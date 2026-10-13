"""Control-flow guard only; musical acceptance remains native and literal."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from contract import merge_strategy_ui as merge

class ChannelSelectionGuardTests(unittest.TestCase):
    def test_fresh_channel_and_return_are_explicit_public_selections(self):
        calls=[]
        class Ui:
            selected=1
            def select_channel(self,number):
                calls.append(("select",number));self.selected=number
            def channel_page(self,page,channel=1):
                calls.append(("page",page,channel))
                # The real Ui.channel_page's channel argument checks scope;
                # it does not select the channel for the caller.
                if self.selected!=channel:raise AssertionError("scope argument does not select the channel")
            def __getattr__(self,name):return lambda *a,**k:None
        state={"midi":[],"midi_count":0,"midi_capture":{"outstanding":[]}}
        c=SimpleNamespace(ui=Ui(),results=[],snapshot=lambda:state,elapse=lambda _:None,
                          wait=lambda predicate:state,led_values=lambda *a:None)
        names=("foundation_selection","actual","checkpoint","loop_leds","music","saved_numeric_modes","strategy","queued_cycle")
        patches={name:(lambda *a,**k:None) for name in names}
        patches["witness"]=lambda *a,**k:{"midi_count":0}
        with patch.multiple(merge,**patches):merge.selector_workflow(c)
        second=calls.index(("page","merge_shape",2))
        self.assertEqual(calls[second-1],("select",2))
        returned=next(i for i in range(second+1,len(calls)) if calls[i]==("page","merge_shape",1))
        self.assertEqual(calls[returned-1],("select",1))
        self.assertEqual(c.ui.selected,1)

class QueuedDetentGuardTests(unittest.TestCase):
    def test_queue_request_uses_complete_detents_and_paced_row_navigation(self):
        actions=[]
        class PendingObserved(Exception):pass
        class Ui:
            def play(self):pass
            def turn(self,n,steps):actions.append(("paced-turn",n,steps))
            def expect_selected_field(self,layout,label,value):
                if label=="Pending":
                    self_test.assertEqual(actions,[dict(type="enc",n=3,delta=2),("paced-turn",2,2)])
                elif label=="Boundary":
                    self_test.assertEqual(actions[-1],("paced-turn",2,4))
                    raise PendingObserved()
        self_test=self
        c=SimpleNamespace(ui=Ui(),action=lambda **kw:actions.append(kw),wait=lambda predicate: {},results=[])
        with patch.object(merge,"strategy"),patch.object(merge,"witness",return_value={"midi_count":0}),self.assertRaises(PendingObserved):
            merge.queued_cycle(c)

class ReadabilityRouteGuardTests(unittest.TestCase):
    def test_all_readability_channel_pages_use_registered_public_route_keys(self):
        import ast,inspect
        from contract import ui_readability
        from ui_map import LIVE_SCREENS
        calls=[node for node in ast.walk(ast.parse(inspect.getsource(ui_readability)))
               if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
               and node.func.attr=="channel_page"]
        self.assertGreaterEqual(len(calls),4)
        for call in calls:
            page=ast.literal_eval(call.args[0])
            self.assertIn(page,LIVE_SCREENS,"Public route key is not a task name")
            self.assertIn("task",LIVE_SCREENS[page])

class HelperIdentifierPreflightTests(unittest.TestCase):
    def test_public_identifiers_are_registered_for_both_new_cases(self):
        import ast,inspect
        from contract import ui_readability
        from ui import Ui
        from ui_map import LIVE_SCREENS,control_cell,NATIVE_MENU_VALUES,NATIVE_MENU,NATIVE_PARAMETER_ROOTS
        for module in (merge,ui_readability):
            for node in ast.walk(ast.parse(inspect.getsource(module))):
                if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute):continue
                owner=node.func.value
                if not (isinstance(owner,ast.Attribute) and isinstance(owner.value,ast.Name) and owner.value.id=="c" and owner.attr=="ui"):continue
                name=node.func.attr
                self.assertTrue(hasattr(Ui,name),(module.__name__,name))
                if not node.args or not isinstance(node.args[0],ast.Constant):continue
                key=node.args[0].value
                if name in ("channel_page","expect_header"):
                    self.assertIn(key,LIVE_SCREENS)
                elif name=="tap_control":
                    args=[ast.literal_eval(arg) for arg in node.args]
                    control_cell(*args)
                elif name=="expect_native_menu_value":
                    self.assertIn(key,NATIVE_MENU_VALUES)
                    self.assertIn(ast.literal_eval(node.args[1]),NATIVE_MENU_VALUES[key])
                elif name=="expect_native_menu_label":self.assertIn(key,NATIVE_MENU)
                elif name=="select_native_parameter_group":self.assertIn(key,NATIVE_PARAMETER_ROOTS)

class NativeClockExitGuardTests(unittest.TestCase):
    def test_both_clock_editors_use_the_normalized_exit(self):
        import ast,inspect
        from contract import ui_readability
        for fn in (ui_readability.internal_tempo,ui_readability.enable_master_clock_output):
            tree=ast.parse(inspect.getsource(fn))
            exits=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=="leave_clock_menu"]
            self.assertEqual(len(exits),1,fn.__name__)
            bare_close=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="press_key" and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value==1]
            self.assertEqual(bare_close,[],fn.__name__)

    def test_tempo_fixture_restores_levels_cursor_before_closing(self):
        from contract import ui_readability
        calls=[]
        class Ui:
            def __getattr__(self,name):return lambda *args:calls.append((name,args))
        c=SimpleNamespace(ui=Ui(),action=lambda **kw:None,elapse=lambda value:None)
        ui_readability.internal_tempo(c,90)
        self.assertEqual(calls[-5:],[("press_key",(2,)),("turn",(2,-60)),("expect_native_menu_label",("levels_root",)),("press_key",(2,)),("press_key",(1,))])

class ScaleContextExitGuardTests(unittest.TestCase):
    def test_scale_sample_returns_through_grid_channel_editor_before_channel_task(self):
        from contract import ui_readability
        import base64
        class RouteObserved(Exception):pass
        class Ui:
            context="channel"
            def channel_page(self,page,channel=1):
                self_test.assertEqual(self.context,"channel","Channel Tasks cannot be entered from Scale context")
                if page=="masks":raise RouteObserved()
            def tap_control(self,key,*args):
                if key=="channel_editor":self.context="channel"
            def __getattr__(self,name):return lambda *args:None
        self_test=self
        state={"frame":{"pixels_base64":base64.b64encode(bytes(32768)).decode()}}
        c=SimpleNamespace(ui=Ui(),configure=lambda:None,snapshot=lambda:state)
        def fitting(driver,page,*args):
            if page=="scale":driver.ui.context="scale"
        with patch.multiple(ui_readability,internal_tempo=lambda *a:None,assignment_marquee=lambda *a:None,sample=lambda *a,**k:None,witness=lambda *a:{},fitting_vertical=fitting),self.assertRaises(RouteObserved):
            ui_readability.readability_workflow(c)

class TempoBoundaryClampGuardTests(unittest.TestCase):
    def test_reset_clamp_covers_the_authored_240bpm_boundary_with_legal_events(self):
        from contract import ui_readability
        actions=[]
        class Ui:
            def expect_menu_value(self,value):
                if value=="1":
                    clamps=[a for a in actions if a.get("n")==3 and a.get("delta",0)<0]
                    self_test.assertEqual(clamps,[dict(type="enc",n=3,delta=-126)]*4)
            def __getattr__(self,name):return lambda *args:None
        self_test=self
        c=SimpleNamespace(ui=Ui(),action=lambda **kw:actions.append(kw),elapse=lambda value:None)
        ui_readability.internal_tempo(c,90)


class StrategyFooterTemporalGuardTests(unittest.TestCase):
    def context(self, refuse_strategy=False):
        calls=[]; clock={'now':0.0,'applied':None,'verified':False}
        class Ui:
            def open_channel_task(self,key):calls.append(('task',key))
            def expect_header(self,*a,**kw):calls.append(('header',a,kw))
            def select_row(self,field,index):clock['now']+=1.7;calls.append(('row',field,index))
            def turn(self,n,delta):clock['now']+=.02;clock['applied']=clock['now'];calls.append(('turn',n,delta))
            def expect_selected_field(self,layout,label,value):
                calls.append(('field',label,value))
                if label=='Strategy':
                    if refuse_strategy:raise AssertionError('Strategy not yet visible')
                    clock['verified']=True
        c=SimpleNamespace(ui=Ui())
        def footer(driver,text):
            self.assertIs(driver,c);self.assertEqual(text,'SKIP APPLIED')
            self.assertTrue(clock['verified'],'feedback observer must follow the exact selected-field proof')
            self.assertLess(clock['now']-clock['applied'],3.0,'transient footer expired during later field navigation')
            calls.append(('footer',text))
        return c,calls,clock,footer

    def test_native_footer_recipe_observes_before_later_row_navigation(self):
        import ast,inspect
        from contract import live_ui_feedback
        from merge_strategy_routes import select_strategy
        c,calls,clock,footer=self.context()
        tree=ast.parse(inspect.getsource(live_ui_feedback.live_ui_merge_shape_trig_mode))
        namespace=dict(c=c,select_strategy=select_strategy,_expect_footer=footer)
        selected=False
        for statement in tree.body[0].body:
            if not isinstance(statement,ast.Expr) or not isinstance(statement.value,ast.Call):continue
            call=statement.value
            if isinstance(call.func,ast.Name) and call.func.id=='select_strategy' and ast.literal_eval(call.args[1])=='SKIP':selected=True
            if selected and isinstance(call.func,ast.Name) and call.func.id in ('select_strategy','_expect_footer'):
                exec(compile(ast.Module(body=[statement],type_ignores=[]),'actual-feedback-recipe','exec'),namespace)
        self.assertTrue(selected)
        self.assertLess(calls.index(('footer','SKIP APPLIED')),calls.index(('row','active_strategy',2)))
        self.assertIn(('field','Active','SKIP'),calls)
        self.assertEqual(calls[-1],('row','trig_mode',1))

    def test_observer_never_runs_before_exact_selected_field_is_verified(self):
        from merge_strategy_routes import select_strategy
        c,calls,clock,footer=self.context(refuse_strategy=True)
        with self.assertRaisesRegex(AssertionError,'Strategy not yet visible'):
            select_strategy(c,'SKIP',after_edit=lambda:footer(c,'SKIP APPLIED'))
        self.assertNotIn(('footer','SKIP APPLIED'),calls)

    def test_default_route_preserves_all_public_selection_operations(self):
        from merge_strategy_routes import select_strategy
        c,calls,clock,footer=self.context();select_strategy(c,'ALL')
        self.assertEqual([x for x in calls if x[0]=='turn'],[('turn',3,-1)]*5+[('turn',3,1)]*2)
        self.assertIn(('field','Strategy','ALL'),calls);self.assertIn(('field','Active','ALL'),calls)
        self.assertEqual(calls[-1],('row','trig_mode',1))


class SharedStrategyExampleCheckpointGuardTests(unittest.TestCase):
    def test_every_authored_step_has_native_case_and_exact_public_checkpoint(self):
        from pathlib import Path
        import yaml
        from cases import CASES
        from contract import live_ui_feedback
        rows=[];active={"value":"FOUNDATION"};playbacks=[];self_test=self
        class Ui:
            def open_channel_task(self,*a):pass
            def expect_header(self,*a,**k):pass
            def select_row(self,*a):pass
            def expect_selected_field(self,layout,label,value):
                self_test.assertEqual(value,active["value"])
                rows.append(dict(kind="selected-field",layout=layout,label=label,value=value))
        def choose(c,value,after_edit=None):
            active["value"]=value
            if after_edit:after_edit()
        def leds(cells,values):
            self.assertEqual((cells,values), ([(14,8)],[{"FOUNDATION":11,"ALL":8,"SKIP":2}[active["value"]]]))
        def playback(phrase,cycles):
            playbacks.append((phrase,cycles));rows.append(dict(kind="midi",phrase=phrase,cycles=cycles,passed=True))
        c=SimpleNamespace(ui=Ui(),results=rows,led_values=leds,playback=playback)
        with patch("contract.foundation_workflow.setup_foundation") as setup, \
             patch("merge_strategy_routes.select_strategy",side_effect=choose), \
             patch.object(live_ui_feedback,"_expect_footer"):
            live_ui_feedback.live_ui_merge_shape_trig_mode(c)
        setup.assert_called_once_with(c)
        root=Path(__file__).resolve().parents[2]
        scene=next(s for s in yaml.safe_load((root/"manual/scene-plans-extra.yaml").read_text())["scenes"] if s["id"]=="merge-shape-owns-trigs")
        self.assertEqual([s["id"] for s in scene["steps"]],["start","merge-modes-open","shape-only","foundation-phrase","shape-all","all-phrase","legacy-return"])
        self.assertEqual(scene["behaviour_case"],"M-LIVEUI-SHAPETRIG-001")
        start=scene["steps"][0]["assertion"]
        self.assertEqual(start["kind"],"grid")
        self.assertEqual(start["cells"],[[1,4],[2,4],[3,4],[4,4],[5,4],[7,4]])
        self.assertEqual(start["expected"],[15]*6)
        self.assertEqual(start["actual"],[15]*6)
        self.assertIs(CASES[scene["behaviour_case"]]["run"],live_ui_feedback.live_ui_merge_shape_trig_mode)
        for step in scene["steps"][1:]:
            selector=step["assertion"]
            self.assertTrue(any(all(row.get(k)==v for k,v in selector.items()) for row in rows),"Missing authored semantic checkpoint: "+step["id"])
        self.assertEqual([r["value"] for r in rows if r.get("kind")=="shape-trig-mode"],["FOUNDATION","ALL"])
        self.assertEqual(playbacks,[(live_ui_feedback._SHAPE_PHRASE,2),(live_ui_feedback._ALL_PHRASE,2)])
        mids=[step for step in scene["steps"] if step["assertion"].get("kind")=="midi"]
        self.assertEqual([step.get("occurrence") for step in mids],[1,2])
        self.assertEqual([row["phrase"] for row in rows if row.get("kind")=="midi"],[live_ui_feedback._SHAPE_PHRASE,live_ui_feedback._ALL_PHRASE])

if __name__=="__main__":unittest.main()
