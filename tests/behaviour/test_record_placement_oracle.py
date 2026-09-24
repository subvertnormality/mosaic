import unittest

from record_placement_oracle import derive_boundary_recorded_step


class BoundaryRecordedStepTests(unittest.TestCase):
    def test_equal_deadline_witness_selects_the_step_active_at_processing(self):
        self.assertEqual(derive_boundary_recorded_step(60, 62, (1, 2)), 1)
        self.assertEqual(derive_boundary_recorded_step(62, 64, (1, 2)), 2)
        self.assertEqual(derive_boundary_recorded_step(64, 65, (3, 4)), 3)
        self.assertEqual(derive_boundary_recorded_step(65, 60, (3, 4)), 4)

    def test_nonadjacent_or_out_of_range_witness_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'adjacent'):
            derive_boundary_recorded_step(60, 64, (1, 2))
        with self.assertRaisesRegex(AssertionError, 'candidate'):
            derive_boundary_recorded_step(60, 62, (2, 3))
