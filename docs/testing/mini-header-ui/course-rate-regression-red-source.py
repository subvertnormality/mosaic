"""Course quarter-note phrase recipe: README typical workflow; actual Rate owner."""
import ast
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]

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

if __name__=='__main__': unittest.main()
