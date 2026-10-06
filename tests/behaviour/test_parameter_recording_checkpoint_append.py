"""Portable regression for the parameter-recording publication checkpoint."""
import copy
import importlib.util
import os
from pathlib import Path
import sys
import unittest
import yaml

ROOT=Path(os.environ.get('MOSAIC_REPO_ROOT',Path(__file__).resolve().parents[2])).resolve()
CASE_SOURCE=Path(os.environ.get('MOSAIC_PARAMETER_RECORDING_CASE',ROOT/'tests/behaviour/trig_parameter_interactions.py')).resolve()
PLAN_SOURCE=Path(os.environ.get('MOSAIC_PARAMETER_RECORDING_PLAN',ROOT/'manual/scene-plans-options.yaml')).resolve()
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(CASE_SOURCE.parent))
from manual_case_capture import Selector

spec=importlib.util.spec_from_file_location('parameter_recording_case_under_test',CASE_SOURCE)
case_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(case_module)

RAW_LOCK={'kind':'selected-param','slot':1,'value':'64','marker':'L','passed':True}
RAW_DEFAULT={'kind':'selected-param','slot':1,'value':'63','marker':None,'passed':True}
CITATION='manual:arm-live-record'
CHARACTERISATION='Current Trig Params screen marks the recorded step value with L.'

class CallbackResults(list):
    """The capture adapter's relevant ordering: append first, then select."""
    def __init__(self,selector):super().__init__();self.selector=selector;self.accepted=[]
    def append(self,row):
        super().append(row)
        if self.selector.accept(row):self.accepted.append(len(self)-1)

class FakeUi:
    def __init__(self,results,row,mode='ok'):
        self.driver=type('DriverRef',(),{})();self.driver.results=results;self.row=copy.deepcopy(row);self.mode=mode
    def expect_selected_param(self,slot,value,marker=None,label=None):
        if self.mode=='raises':raise RuntimeError('simulated UI assertion failure')
        row=copy.deepcopy(self.row)
        if self.mode=='invalid':row['value']='62'
        self.driver.results.append(row)
        if self.mode=='duplicate':self.driver.results.append(copy.deepcopy(row))

class Case:
    def __init__(self,results,row,mode='ok'):
        self.results=results;self.ui=FakeUi(results,row,mode)

def recorded_lock_selector():
    plan=yaml.safe_load(PLAN_SOURCE.read_text())
    scene=next(item for item in plan['scenes'] if item['id']=='record-parameter-lock')
    step=next(item for item in scene['steps'] if item['id']=='recorded-lock')
    assertion=step['assertion']
    assert assertion['kind']=='parameter-recording-selected-value'
    assert assertion['slot']==1 and assertion['value']=='64' and assertion['marker']=='L'
    assert assertion['citation']==CITATION
    return assertion

class ParameterRecordingCheckpointAppendTests(unittest.TestCase):
    def test_frozen_append_then_late_metadata_is_red(self):
        selector=Selector(recorded_lock_selector())
        results=CallbackResults(selector)
        results.append(copy.deepcopy(RAW_LOCK))
        results[-1].update(citation=CITATION,characterisation=CHARACTERISATION)
        self.assertEqual(results.accepted,[])
        self.assertEqual(selector.seen,0)

    def test_followup_row_works_with_builtin_list_and_preserves_raw_source(self):
        selector=Selector(recorded_lock_selector())
        results=[]  # Matches the normal Driver.results type.
        case=Case(results,RAW_LOCK)
        case_module.append_selected_param_checkpoint(case,1,64,'L',CITATION,CHARACTERISATION)
        self.assertIs(type(results),list)
        self.assertEqual(results,[RAW_LOCK,{
            'kind':'parameter-recording-selected-value','slot':1,'value':'64','marker':'L','passed':True,
            'citation':CITATION,'characterisation':CHARACTERISATION,
            'source_assertion_index':0,'source_assertion':RAW_LOCK,
        }])
        self.assertTrue(selector.accept(results[1]))

    def test_followup_row_is_seen_by_actual_capture_selector_callback(self):
        selector=Selector(recorded_lock_selector())
        results=CallbackResults(selector)
        case=Case(results,RAW_LOCK)
        case_module.append_selected_param_checkpoint(case,1,64,'L',CITATION,CHARACTERISATION)
        self.assertEqual(results.accepted,[1])
        self.assertEqual(results[0],RAW_LOCK)
        self.assertEqual(results[1]['source_assertion_index'],0)
        self.assertEqual(results[1]['source_assertion'],RAW_LOCK)
        self.assertEqual(selector.seen,1)

    def test_armed_default_uses_same_raw_then_followup_shape(self):
        results=[];case=Case(results,RAW_DEFAULT)
        case_module.append_selected_param_checkpoint(case,1,63,None,CITATION,
            'Current Trig Params screen shows the assigned channel default while armed.')
        self.assertEqual(results[0],RAW_DEFAULT)
        self.assertEqual(results[1]['kind'],'parameter-recording-selected-value')
        self.assertEqual(results[1]['value'],'63')
        self.assertIsNone(results[1]['marker'])
        self.assertEqual(results[1]['source_assertion_index'],0)

    def test_bad_or_duplicate_raw_rows_never_create_followup_checkpoint(self):
        for mode in ('invalid','duplicate'):
            with self.subTest(mode=mode):
                results=[];case=Case(results,RAW_LOCK,mode)
                with self.assertRaises(AssertionError):
                    case_module.append_selected_param_checkpoint(case,1,64,'L',CITATION,CHARACTERISATION)
                self.assertTrue(all(row['kind']=='selected-param' for row in results))
                self.assertNotIn('parameter-recording-selected-value',[row['kind'] for row in results])

    def test_ui_exception_leaves_builtin_list_unchanged(self):
        results=[];case=Case(results,RAW_LOCK,'raises')
        with self.assertRaisesRegex(RuntimeError,'simulated UI assertion failure'):
            case_module.append_selected_param_checkpoint(case,1,64,'L',CITATION,CHARACTERISATION)
        self.assertEqual(results,[])

    def test_armed_led_selector_is_unchanged(self):
        plan=yaml.safe_load(PLAN_SOURCE.read_text())
        scene=next(item for item in plan['scenes'] if item['id']=='record-parameter-lock')
        armed=next(item for item in scene['steps'] if item['id']=='armed')['assertion']
        self.assertEqual(armed,{'kind':'parameter-recording-arm-led','cell':[2,8],'expected':12,
                                'passed':True,'citation':CITATION,
                                'characterisation':'The captured armed blink phase is grid level 12; the renderer test marks its blink output as -4.'})

if __name__=='__main__':unittest.main()