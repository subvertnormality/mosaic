"""The Doctor setup UI is a normal, distinct manual-cited behaviour case."""
import unittest
from cases import CASES

class DoctorSetupOptionsGlobalRegistrationTests(unittest.TestCase):
    def test_global_setup_case_is_distinct_from_specialized_native_qualification(self):
        global_id = "M-DOCTOR-SETUP-001"
        specialized_id = "MA-DOCTOR-SETUP-OPTIONS-001"
        case = CASES.get(global_id)
        self.assertIsNotNone(case, "M-DOCTOR-SETUP-001 missing from global CASES registry")
        self.assertNotIn(specialized_id, CASES)
        self.assertEqual(case["case_id"], global_id)
        self.assertEqual(case["citation"], "manual:rhythm-doctor")
        self.assertEqual(case["requirements"], [])
        self.assertEqual(case["run"].__name__, "run_doctor_setup_options")
        for observable in ("AUTO/MANUAL", "clamps", "discard/reopen", "apply/reopen", "playing-state refusal"):
            self.assertIn(observable.lower(), case["description"].lower())

if __name__ == "__main__":
    unittest.main()
