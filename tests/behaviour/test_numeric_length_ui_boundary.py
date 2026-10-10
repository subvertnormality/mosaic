"""Raw/semantic LED parity for numeric length merge setup (README length ranges)."""
import unittest

from numeric_merging import (
    fractional_length_mask_merge,
    midi_events_in_snapshot_window,
    numeric_length_merge,
)
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
    def test_delayed_witness_strum_voice_is_after_playback_snapshot_boundary(self):
        # playback() returns after its third-cycle onset witness. The staggered
        # second voice for that witness can arrive during the later drain, so
        # compare MIDI only through the captured playback boundary.
        notes = [60, 64, 60, 64, 60]
        events = [
            event
            for offset, note in enumerate(notes)
            for event in (
                {"index": 21 + 2 * offset, "bytes": [144, note, 127]},
                {"index": 22 + 2 * offset, "bytes": [128, note, 127]},
            )
        ] + [
            {"index": 31, "bytes": [144, 64, 127]},
            {"index": 32, "bytes": [128, 64, 127]},
        ]
        state = {"midi": events}

        selected = midi_events_in_snapshot_window(state, marker=20, cutoff=30)

        self.assertEqual([event["index"] for event in selected], list(range(21, 31)))
        self.assertEqual(
            [event["bytes"] for event in selected],
            [
                message
                for note in notes
                for message in ([144, note, 127], [128, note, 127])
            ],
        )

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
