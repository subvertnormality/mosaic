"""Sensitivity checks for the native duration oracle's MIDI route matching."""
import ast
from pathlib import Path
import unittest
from types import SimpleNamespace

tree=ast.parse(Path(__file__).with_name('cases.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='assert_durations')
namespace={}
exec(compile(ast.Module(body=[node],type_ignores=[]),'duration-oracle','exec'),namespace)
check=namespace['assert_durations']

def event(index,port,status,time):
    return dict(index=index,port=port,bytes=[status,60,100],logical_ns=time)

class DurationRoutes(unittest.TestCase):
    def run_check(self,port,channel,offs):
        note=event(1,port,144+channel-1,0)
        c=SimpleNamespace(clock_mode='controlled-experimental',results=[],snapshot=lambda:dict(midi=offs))
        check(c,[note],[1])
    def test_existing_default_route(self):
        self.run_check(1,1,[event(2,1,128,166666667)])
    def test_reference_route_ignores_other_routes(self):
        self.run_check(2,2,[event(2,1,129,50000000),event(3,2,128,50000000),event(4,2,129,166666667)])
    def test_wrong_port_cannot_release(self):
        with self.assertRaises(StopIteration):self.run_check(2,2,[event(2,1,129,166666667)])
    def test_wrong_channel_cannot_release(self):
        with self.assertRaises(StopIteration):self.run_check(2,2,[event(2,2,128,166666667)])
    def test_right_route_wrong_time_fails(self):
        with self.assertRaises(AssertionError):self.run_check(2,2,[event(2,2,129,100000000)])

if __name__=='__main__':unittest.main()
