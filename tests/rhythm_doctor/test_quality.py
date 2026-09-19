"""RD-02 evaluator characterisation outside the manual; PLAN.md acceptance gates."""
import unittest
from quality import onset_score, velocity_mae

class QualityTests(unittest.TestCase):
    def test_one_to_one(self):
        self.assertEqual(onset_score([1.0], [0.99, 1.01])["tp"], 1)
        self.assertAlmostEqual(onset_score([1.0], [0.99, 1.01])["f1"], 2 / 3)
    def test_maximum_cardinality(self):
        self.assertEqual(onset_score([0.0, 0.08], [0.04, 0.12])["tp"], 2)
    def test_boundary(self):
        self.assertEqual(onset_score([1.0, 0.0], [0.05, 1.05])["tp"], 2)
        self.assertEqual(onset_score([0.0], [0.05001])["tp"], 0)
    def test_silence(self):
        self.assertEqual(onset_score([], [1.0])["f1"], 0)
        self.assertEqual(onset_score([], [1.0])["fp"], 1)
        self.assertEqual(onset_score([], [])["f1"], 1)
    def test_invalid_times(self):
        for value in [float("nan"), float("inf"), -1.0, True]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                onset_score([value], [])
    def test_velocity(self):
        self.assertEqual(velocity_mae([(40, 48), (100, 84)]), 12)
        with self.assertRaises(ValueError):
            velocity_mae([])
        with self.assertRaises(ValueError):
            velocity_mae([(20, 128)])

if __name__ == "__main__":
    unittest.main()
