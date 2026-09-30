import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).parent / "artifacts" / "bass-rf-precision-operating-point-v4-20260919" / "run_precision_operating_point.py"
SPEC = importlib.util.spec_from_file_location("bass_precision_operating_point", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PrecisionOperatingPoint(unittest.TestCase):
    def test_choice_maximizes_recall_only_among_precision_and_absent_safe_rows(self):
        grid = [
            {"threshold": .10, "validation_aggregate_50ms_one_to_one": {"recall": .99, "f1": .75}, "constraint": {"aggregate_precision_at_least_0_90": False, "zero_predictions_on_known_development_absent_bass": True}},
            {"threshold": .20, "validation_aggregate_50ms_one_to_one": {"recall": .80, "f1": .84}, "constraint": {"aggregate_precision_at_least_0_90": True, "zero_predictions_on_known_development_absent_bass": True}},
            {"threshold": .30, "validation_aggregate_50ms_one_to_one": {"recall": .90, "f1": .82}, "constraint": {"aggregate_precision_at_least_0_90": True, "zero_predictions_on_known_development_absent_bass": False}},
        ]
        self.assertEqual(MODULE.choose_constrained(grid)["threshold"], .20)

    def test_choice_rejects_when_no_row_meets_both_constraints(self):
        grid = [{"threshold": .5, "validation_aggregate_50ms_one_to_one": {"recall": .7, "f1": .7}, "constraint": {"aggregate_precision_at_least_0_90": False, "zero_predictions_on_known_development_absent_bass": True}}]
        with self.assertRaisesRegex(RuntimeError, "no operating point"):
            MODULE.choose_constrained(grid)


if __name__ == "__main__":
    unittest.main()
