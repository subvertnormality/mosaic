"""Bounded regression for real-time revoice onset tolerance in verify_invariants."""
import importlib.util
import os
import sys
import unittest
from pathlib import Path

# Characterisation: validator timing and MIDI invariant evidence.
import manual_audio

NS_PER_STEP = 1_000_000_000 / 6
ORIGIN = 5_000_000_000
CONTRACT = {
    "cycle_steps": 8,
    "notes": [dict(step=0, note=60, velocity=80, length=1)],
    "invariants": [dict(kind="revoice", reference_start_step=0,
                         length_steps=1, revoiced_start_step=4)],
}


def packets(revoice_offset_seconds=0.0, revoice_note=60, clock="real-time"):
    key = "monotonic_ns" if clock == "real-time" else "logical_ns"
    rows = []
    index = 0
    for step, note in ((0, 60), (4, revoice_note)):
        shift = revoice_offset_seconds if step == 4 else 0.0
        onset = int(ORIGIN + step * NS_PER_STEP + shift * 1_000_000_000)
        release = int(onset + NS_PER_STEP)
        for timestamp, data in ((onset, [144, note, 80]), (release, [128, note, 80])):
            index += 1
            row = dict(index=index, port=1, bytes=data)
            row[key] = timestamp
            rows.append(row)
    return rows


class RevoiceOnsetTolerance(unittest.TestCase):
    def test_real_time_one_1_over_24_tick_within_existing_10ms_tolerance_passes(self):
        # 1/24 of a six-step/second step is 6.944... ms; packet rows stay literal.
        result = manual_audio.verify_invariants(
            packets(1 / 144), CONTRACT, ORIGIN, "real-time", 1, 144)
        self.assertTrue(result["passed"])
        self.assertEqual(result["characterisation"]["revoiced_chords"][0]["step"], 97 / 24)

    def test_chord_packets_straddling_quantisation_boundary_keep_one_tolerant_onset(self):
        contract = {
            "cycle_steps": 8,
            "notes": [dict(step=0, note=n, velocity=80, length=1)
                      for n in (60, 64, 67)],
            "invariants": [dict(kind="revoice", reference_start_step=0,
                                 length_steps=1, revoiced_start_step=4)],
        }
        rows = []
        index = 0
        for step, note, shift in (
            (0, 60, 0.0), (0, 64, 0.0), (0, 67, 0.0),
            (4, 60, 0.002), (4, 64, 0.005), (4, 67, 0.005),
        ):
            onset = int(ORIGIN + step * NS_PER_STEP + shift * 1_000_000_000)
            release = int(onset + NS_PER_STEP)
            for timestamp, data in ((onset, [144, note, 80]), (release, [128, note, 80])):
                index += 1
                rows.append(dict(index=index, port=1, monotonic_ns=timestamp, bytes=data))
        result = manual_audio.verify_invariants(rows, contract, ORIGIN, "real-time", 1, 144)
        self.assertTrue(result["passed"])
    def test_real_time_onset_over_10ms_fails_without_becoming_retryable(self):
        with self.assertRaises(AssertionError) as caught:
            manual_audio.verify_invariants(
                packets(0.010001), CONTRACT, ORIGIN, "real-time", 1, 144)
        self.assertEqual(caught.exception.args[0][0], "Revoice changed the onset steps")
        self.assertFalse(manual_audio.host_timing_miss(caught.exception, "real-time"))

    def test_controlled_lane_remains_exact(self):
        with self.assertRaisesRegex(AssertionError, "Revoice changed the onset steps"):
            manual_audio.verify_invariants(
                packets(1 / 144, clock="controlled-experimental"), CONTRACT,
                ORIGIN, "controlled-experimental", 1, 144)

    def test_wrong_revoiced_chord_still_fails_the_manual_invariant(self):
        with self.assertRaises(AssertionError) as caught:
            manual_audio.verify_invariants(
                packets(0.0, revoice_note=61), CONTRACT, ORIGIN, "real-time", 1, 144)
        self.assertIn("pitch-classes", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
