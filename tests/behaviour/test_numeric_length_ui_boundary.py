"""Raw/semantic LED parity for numeric length merge setup (README length ranges)."""
import unittest

from numeric_merging import fractional_length_mask_merge, numeric_length_merge
from ui_map import LED_LEVELS


class CapturedEnough(Exception):
    pass


class RecordingUi:
    def __init__(self, count):
        self.count = count
        self.steps = []

    def __getattr__(self, name):
        return lambda *args, **kwargs: None

    def expect_steps(self, states):
        self.steps.append(states)
        if len(self.steps) == self.count:
            raise CapturedEnough


class Driver:
    def __init__(self, count):
        self.ui = RecordingUi(count)


class NumericLengthLedParityTests(unittest.TestCase):
    def test_numeric_merge_step_levels_match_raw_oracle(self):
        sources = ([2, 4], [3, 4], [2, 2, 5], [1, 2], [1, 4], [2, 2, 8])
        for variant, lengths in enumerate(sources):
            with self.subTest(variant=variant):
                driver = Driver(len(lengths))
                with self.assertRaises(CapturedEnough):
                    numeric_length_merge(driver, variant=variant)
                width = 16 if variant >= 3 else 8
                for states, length in zip(driver.ui.steps, lengths):
                    self.assertEqual(
                        [LED_LEVELS[states[step]] for step in range(1, width + 1)],
                        [15] + [5] * (length - 1) + [2] * (width - length),
                    )

    def test_fractional_merge_step_levels_match_raw_oracle(self):
        sources = ([2, 4], [1, 4], [2, 4])
        for variant, lengths in enumerate(sources):
            with self.subTest(variant=variant):
                driver = Driver(len(lengths))
                with self.assertRaises(CapturedEnough):
                    fractional_length_mask_merge(driver, variant=variant)
                for states, length in zip(driver.ui.steps, lengths):
                    self.assertEqual(
                        [LED_LEVELS[states[step]] for step in range(1, 9)],
                        [15] + [5] * (length - 1) + [2] * (8 - length),
                    )


if __name__ == "__main__":
    unittest.main()
