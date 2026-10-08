"""Repository-discoverable fake-public-driver regression for M-EDIT-005."""
import ast
import time
import unittest
from pathlib import Path
from unittest.mock import patch


class StopAfterFirstSample(Exception):
    pass


class FakePublicUI:
    def __init__(self, driver, stop_after_degree=1):
        self.driver=driver
        self.stop_after_degree=stop_after_degree
        self.degree_taps=0
        self.input_edges=[]
    def configure(self,*args,**kwargs):
        pass
    def pattern_editor(self,*args,**kwargs):
        pass
    def control_edge(self,control,down):
        d=self.driver
        if down:
            self.input_edges.append((control,True,d.now_ns))
            d.now_ns+=d.press_call_ns
        else:
            self.input_edges.append((control,False,d.now_ns+d.release_event_offset_ns))
            d.now_ns+=d.release_call_ns
    def control_cell(self,control):
        return (14,8)
    def tap_control(self,control,*args):
        if control=='pattern_note_degree':
            self.degree_taps+=1
            if self.degree_taps>=self.stop_after_degree:
                raise StopAfterFirstSample
    def expect_leds(self,*args,**kwargs):
        pass


class FakePublicDriver:
    def __init__(self,extra_hold_ns=0):
        self.clock_mode='real-time'
        self.logical_ns=0
        self.now_ns=0
        self.press_call_ns=25_000_000
        self.release_call_ns=26_289_198
        self.release_event_offset_ns=969_870
        self.sleep_overshoot_ns=982_538
        self.extra_hold_ns=extra_hold_ns
        self.hold_count=0
        self.results=[]
        self.observations=[]
        self.ui=FakePublicUI(self)
    def now(self):
        return self.now_ns
    def elapse(self,seconds):
        elapsed=round(seconds*1e9)
        if seconds>=.5:
            self.hold_count+=1
            elapsed+=self.sleep_overshoot_ns
            if self.hold_count==1:
                elapsed+=self.extra_hold_ns
        self.now_ns+=elapsed
    def playback(self,*args,**kwargs):
        pass


def load_current_hold_case():
    """Compile only the current case function; do not import the whole cases module."""
    source=Path(__file__).with_name('cases.py')
    tree=ast.parse(source.read_text(encoding='utf-8'),filename=str(source))
    function=next(node for node in tree.body
                  if isinstance(node,ast.FunctionDef) and node.name=='editor_hold_boundaries')
    namespace={}
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),namespace)
    return namespace['editor_hold_boundaries']


class MEdit005HoldBoundRegression(unittest.TestCase):
    def run_case(self,driver):
        case=load_current_hold_case()
        with patch.object(time,'monotonic_ns',driver.now):
            return case(driver)

    def test_candidate_short_receipt_passes_and_is_recorded(self):
        driver=FakePublicDriver()
        with self.assertRaises(StopAfterFirstSample):
            self.run_case(driver)
        self.assertEqual(len(driver.observations),1)
        self.assertEqual(len(driver.results),1)
        sample=driver.observations[0]
        self.assertEqual(sample['kind'],'hold-input-bounds-sample')
        self.assertFalse(sample['expected_long'])
        self.assertLess(sample['wall_upper_seconds'],1.0)
        self.assertEqual(driver.results[0]['kind'],'hold-input-bounds')

    def test_overlong_short_receipt_is_recorded_before_strict_failure(self):
        driver=FakePublicDriver(extra_hold_ns=150_000_000)
        with self.assertRaisesRegex(AssertionError,'one-second hold boundary'):
            self.run_case(driver)
        self.assertEqual(len(driver.observations),1)
        self.assertEqual(len(driver.results),1)
        sample=driver.observations[0]
        self.assertEqual(sample['kind'],'hold-input-bounds-sample')
        self.assertFalse(sample['expected_long'])
        self.assertGreater(sample['wall_upper_seconds'],1.0)
        self.assertEqual(driver.results[0]['wall_upper_seconds'],sample['wall_upper_seconds'])
        press,release=driver.ui.input_edges
        self.assertGreater((release[2]-press[2])/1e9,1.0)


if __name__=='__main__':
    unittest.main()
