"""Controlled manual capture metadata contracts."""
import importlib.util,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
spec=importlib.util.spec_from_file_location("manual_capture",ROOT/"tools/manual_capture.py")
capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
class ControlledLocalReport(unittest.TestCase):
 def test_scoped_report_marks_manual_generation_and_leaves_regression_pending(self):
  report={"passed":True,"complete_regression_run":False,"scene_build_complete":False,"pilot_complete":True}
  result=capture.mark_controlled_local_report(report)
  self.assertIs(result,report)
  self.assertEqual(report["validation_scope"],"controlled-manual-generation")
  self.assertEqual(report["realtime_qualification"],"pending-ci")
  self.assertEqual(report["clock_mode"],"controlled-experimental")
  self.assertFalse(report["complete_regression_run"])
  self.assertTrue(report["scene_build_complete"])
  self.assertFalse(report["pilot_complete"])
  self.assertNotIn("manual_generation_complete",report)
if __name__=="__main__":unittest.main()
