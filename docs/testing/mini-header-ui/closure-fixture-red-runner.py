import runpy,sys,unittest,importlib.util
from pathlib import Path
ROOT=Path('/home/andy/mosaic-manual-1.4.0')
ARCHIVE=Path('/home/andy/mosaic-manual-runs/b37d0e99daad449d8244b763a6f92f29/capture-source/tools/manual_closure_cases.py')
sys.path.insert(0,str(ROOT/'tests/behaviour'));sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('manual_closure_cases',ARCHIVE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
sys.modules['manual_closure_cases']=module
from test_manual_closure_cases import MotionClosureOracleTests
class ArchivedRealBlinkTests(unittest.TestCase):
    def test_300ms_real_dwell_below_source_bound_is_rejected(self):
        rows=[dict(levels=[v,15,2],monotonic_ns=i*300000000,logical_ns=None) for i,v in enumerate([1,7,1,7,1,7,1])]
        with self.assertRaises(AssertionError):module.queued_blink_levels(rows,False)
suite=unittest.TestSuite([ArchivedRealBlinkTests('test_300ms_real_dwell_below_source_bound_is_rejected'),MotionClosureOracleTests('test_clock_full_authored_motif_moves_outside_obsolete_corner')])
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
