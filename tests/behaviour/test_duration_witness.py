import copy
import unittest

from duration_witness import (
    assert_duration_witness_observed,
    controlled_duration_witness_pair,
)


class ControlledDurationWitnessTests(unittest.TestCase):
    def setUp(self):
        self.on = {
            "device_id": 0,
            "port": 1,
            "port_name": "Emulator MIDI",
            "monotonic_ns": 430,
            "index": 18,
            "bytes": [144, 60, 127],
            "decoded": [{"type": "note_on", "channel": 1, "data": [60, 127]}],
            "logical_ns": 6_870_000_000,
        }
        self.off = {
            "device_id": 0,
            "port": 1,
            "port_name": "Emulator MIDI",
            "monotonic_ns": 586,
            "index": 31,
            "bytes": [128, 60, 127],
            "decoded": [{"type": "note_off", "channel": 1, "data": [60, 127]}],
            "logical_ns": 7_536_666_667,
        }

    def test_keeps_only_controlled_musical_evidence_in_result_projection(self):
        raw_on, raw_off = copy.deepcopy(self.on), copy.deepcopy(self.off)

        result = controlled_duration_witness_pair(self.on, self.off)

        self.assertEqual(result, {
            "first_on": {"index": 18, "logical_ns": 6_870_000_000, "bytes": [144, 60, 127]},
            "first_off": {"index": 31, "logical_ns": 7_536_666_667, "bytes": [128, 60, 127]},
        })
        self.assertEqual(self.on, raw_on)
        self.assertEqual(self.off, raw_off)
        self.assertLess(self.on["index"], self.off["index"])

    def test_raw_timestamps_remain_in_full_observation_rows(self):
        observations = [{"state": {"midi": [self.on, self.off]}}]

        assert_duration_witness_observed(observations, self.on, self.off)

        self.assertIn("monotonic_ns", observations[0]["state"]["midi"][0])
        self.assertIn("monotonic_ns", observations[0]["state"]["midi"][1])

    def test_host_timestamp_shifts_do_not_change_musical_result(self):
        shifted_on = dict(self.on, monotonic_ns=self.on["monotonic_ns"] + 9_000_000)
        shifted_off = dict(self.off, monotonic_ns=self.off["monotonic_ns"] + 9_000_000)

        before = controlled_duration_witness_pair(self.on, self.off)
        after = controlled_duration_witness_pair(shifted_on, shifted_off)

        self.assertEqual(before, after)
        self.assertNotEqual(shifted_on["monotonic_ns"], self.on["monotonic_ns"])

    def test_musical_time_and_payload_changes_remain_visible(self):
        later_on = dict(self.on, logical_ns=self.on["logical_ns"] + 1)
        later_on_result = controlled_duration_witness_pair(later_on, self.off)
        original_result = controlled_duration_witness_pair(self.on, self.off)
        self.assertNotEqual(original_result, later_on_result)

        transposed_on = dict(
            self.on,
            bytes=[144, 61, 127],
            decoded=[{"type": "note_on", "channel": 1, "data": [61, 127]}],
        )
        transposed_off = dict(
            self.off,
            bytes=[128, 61, 127],
            decoded=[{"type": "note_off", "channel": 1, "data": [61, 127]}],
        )
        self.assertNotEqual(original_result,
                            controlled_duration_witness_pair(transposed_on, transposed_off))

    def test_rejects_missing_raw_witness_fields(self):
        incomplete = dict(self.on)
        del incomplete["monotonic_ns"]

        with self.assertRaisesRegex(AssertionError, "monotonic_ns"):
            controlled_duration_witness_pair(incomplete, self.off)

    def test_rejects_wrong_payload_or_event_order(self):
        wrong_on = dict(self.on, bytes=[144, 61, 127],
                        decoded=[{"type": "note_on", "channel": 1, "data": [61, 127]}])
        with self.assertRaisesRegex(AssertionError, "note-on"):
            controlled_duration_witness_pair(wrong_on, self.off)

        reversed_off = dict(self.off, index=self.on["index"])
        with self.assertRaisesRegex(AssertionError, "order"):
            controlled_duration_witness_pair(self.on, reversed_off)


if __name__ == "__main__":
    unittest.main()
