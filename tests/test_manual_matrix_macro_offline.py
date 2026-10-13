"""Offline regressions for the exact MIDI oracle of the modest Macro 1 lesson."""
import importlib
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
case = importlib.import_module("manual_extra_matrix_macro_modest")


def events_for(cc_value=38, pitches=None, spacing_ns=None, cc_after_note=False):
    phrase = list(case.PHRASE if pitches is None else pitches)
    events = []
    for i, (pitch, velocity) in enumerate(phrase):
        at = round(i * 1_000_000_000 / 6) if spacing_ns is None else spacing_ns[i]
        cc = dict(port=1, bytes=[176, 1, cc_value], index=2 * i, logical_ns=at)
        note = dict(port=1, bytes=[144, pitch, velocity], index=2 * i + 1, logical_ns=at)
        if cc_after_note:
            cc["index"], note["index"] = note["index"], cc["index"]
        events.extend((cc, note))
    notes = [event for event in events if event["bytes"][0] == 144]
    return events, notes


class ModestMatrixMacroOfflineTests(unittest.TestCase):
    def check_phase(self, cc, pitches=None, spacing_ns=None, cc_after_note=False, expected=None):
        events, notes = events_for(cc, pitches, spacing_ns, cc_after_note)
        case.assert_phase(events, notes, cc if expected is None else expected, "controlled-experimental")

    def test_source_scale_maps_zero_half_and_full_to_documented_cc_values(self):
        self.assertEqual(case.expected_cc(32, .10, 0), 32)
        self.assertEqual(case.expected_cc(32, .10, .50), 38)
        self.assertEqual(case.expected_cc(32, .10, 1), 45)

    def test_zero_source_and_modest_move_have_exact_cc_per_onset(self):
        self.check_phase(32)
        self.check_phase(38)

    def test_rejects_wrong_cc_value(self):
        with self.assertRaises(AssertionError):
            self.check_phase(39, expected=38)

    def test_rejects_changed_pitch_or_velocity(self):
        phrase = list(case.PHRASE)
        phrase[1] = (63, 117)
        with self.assertRaises(AssertionError):
            self.check_phase(38, phrase)
        phrase = list(case.PHRASE)
        phrase[1] = (62, 116)
        with self.assertRaises(AssertionError):
            self.check_phase(38, phrase)

    def test_rejects_wrong_sixth_second_spacing(self):
        spacing = [round(i * 1_000_000_000 / 6) for i in range(4)]
        spacing[2] += 3
        with self.assertRaises(AssertionError):
            self.check_phase(38, spacing_ns=spacing)

    def test_rejects_cc_after_note_on(self):
        with self.assertRaises(AssertionError):
            self.check_phase(38, cc_after_note=True)


if __name__ == "__main__":
    unittest.main()
