"""Invariant oracle for the voice-leading Revoice lesson.

README.md#harmony: "Revoice takes the actual root and enabled chord-mask voices after Mosaic's
pitch-class decisions, preserving their pitch classes and sounding count while choosing legal
octaves and assignments", and "Bass can be Root".
The lesson therefore does not pin the Revoice notes. Its midi_contract lists the literal Harmony Off
chords (slot 1) and one `revoice` invariant that the captured Revoice chords (slot 2) must satisfy.
Every rule has a counterexample here that must be rejected. The README does not state the Register
defaults, whether voices keep an identity, or what "economical movement" measures, and a run showed
Mosaic giving up a common pitch (G, bass of G to the root C) for a root bass, so no rule is made of
common tones, voices or movement (the literal Revoice notes are recorded as characterisation, never as the oracle).
"""
import copy
import os
import sys
import unittest
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path
import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(1, str(REPO / "tests/behaviour"))
import manual_audio
import manual_audio_setups
inv = manual_audio

REFERENCE = [[48, 52, 55], [45, 48, 52], [53, 57, 60], [55, 59, 62]]
# A Revoice that obeys every rule: C and E are held from C to A minor, A and C from A minor to F, and
# the G held on top of the next bar's C from the bar's last chord.
REVOICED = [[48, 52, 55], [45, 48, 52], [41, 45, 48], [55, 59, 62]]


def authored():
    return yaml.safe_load((REPO / "manual/audio-scenes.yaml").read_text())


def example(ident="voice-leading-revoice"):
    return copy.deepcopy(next(v for v in authored()["examples"] if v["id"] == ident))


class Rules(unittest.TestCase):
    def check(self, revoiced, reference=REFERENCE):
        return inv.check_revoice(reference, revoiced)

    def test_a_voicing_that_obeys_every_rule_passes(self):
        self.assertEqual(self.check(REVOICED)["chords"], 4)

    def rejects(self, revoiced, rule):
        with self.assertRaises(inv.InvariantViolation) as caught:
            self.check(revoiced)
        self.assertEqual(caught.exception.rule, rule)

    def test_sounding_count_is_preserved(self):
        self.rejects([[48, 52], *REVOICED[1:]], "sounding-count")
        self.rejects([REVOICED[0], [45, 48, 52, 57], *REVOICED[2:]], "sounding-count")

    def test_pitch_classes_are_preserved(self):
        bad = [list(v) for v in REVOICED]
        bad[1] = [45, 48, 53]                      # A, C, F: the E became an F
        self.rejects(bad, "pitch-classes")

    def test_a_dropped_and_doubled_pitch_class_is_not_the_same_harmony(self):
        bad = [list(v) for v in REVOICED]
        bad[0] = [48, 52, 60]                      # C, E, C: the G is missing, the count unchanged
        self.rejects(bad, "pitch-classes")

    def test_notes_may_move_to_other_octaves_if_the_rest_holds(self):
        self.assertEqual(self.check([[24, 40, 43], *REVOICED[1:]])["chords"], 4)

    def test_chord_count_must_match_the_reference(self):
        self.rejects(REVOICED[:3], "chord-count")

    def test_the_bass_is_the_chord_root(self):
        bad = [list(v) for v in REVOICED]
        bad[0] = [52, 55, 60]                      # first inversion: E is lowest
        self.rejects(bad, "bass-root")


class Capture(unittest.TestCase):
    """Packets to chords: notes that start on one step are one chord; lengths pair each note on with its off."""

    def packets(self, rows, status=144, port=1, key="logical_ns"):
        out, index = [], 0
        for step, note, velocity, length in rows:
            for kind, at in ((status, step), (status - 16, step + length)):
                index += 1
                out.append(dict(index=index, port=port, bytes=[kind, note, velocity if kind == status else 0], **{key: int(Fraction(at) * 10**9 / 6)}))
        return sorted(out, key=lambda p: (p[key], p["index"]))

    def test_notes_pair_with_their_release_and_group_by_onset_step(self):
        packets = self.packets([(0, 60, 80, 2), (0, 64, 80, 2), (4, 57, 80, 2)])
        notes = inv.captured_notes(packets, origin=0, clock_mode="controlled-experimental", port=1, status=144)
        self.assertEqual([(v["step"], v["note"], v["length"]) for v in notes], [(0, 60, 2), (0, 64, 2), (4, 57, 2)])
        chords = inv.chords_by_onset(notes)
        self.assertEqual([(step, pitches) for step, pitches in chords], [(0, [60, 64]), (4, [57])])

    def test_other_channels_are_ignored(self):
        packets = self.packets([(0, 60, 80, 2)]) + self.packets([(0, 99, 80, 2)], status=145)
        notes = inv.captured_notes(packets, origin=0, clock_mode="controlled-experimental", port=1, status=144)
        self.assertEqual([v["note"] for v in notes], [60])

    def test_a_note_never_released_is_refused(self):
        packets = [p for p in self.packets([(0, 60, 80, 2)]) if p["bytes"][0] == 144]
        with self.assertRaises(AssertionError):
            inv.captured_notes(packets, origin=0, clock_mode="controlled-experimental", port=1, status=144)

    def test_onset_off_the_authored_grid_is_refused(self):
        packets = self.packets([(Fraction(1, 7), 60, 80, 2)])
        with self.assertRaises(AssertionError):
            inv.captured_notes(packets, origin=0, clock_mode="controlled-experimental", port=1, status=144)


class Contract(unittest.TestCase):
    """The authored lesson is valid, literal for slot 1 and invariant-checked for slot 2."""

    def run_lesson(self, mutate=None, revoiced=REVOICED, steps=(0, 4, 8, 12), offset=32, key="logical_ns"):
        value = example()
        if mutate:
            mutate(value)
        contract = value["midi_contract"]
        rows = []
        for step, notes in zip(steps, REFERENCE):                      # slot 1: literal
            rows += [(step + 16 * bar, n, 80, 2) for bar in range(2) for n in notes]
        for step, notes in zip(steps, revoiced):                       # slot 2: chosen by Mosaic
            rows += [(step + offset + 16 * bar, n, 80, 2) for bar in range(2) for n in notes]
        packets = Capture().packets(rows, key=key)
        return manual_audio_invariants_verify(contract, packets, key)

    def test_authored_example_validates(self):
        manual_audio.validate(dict(schema_version=1, examples=[example()]))

    def test_a_conforming_capture_passes_and_records_the_literal_revoice_as_characterisation(self):
        result = self.run_lesson()
        self.assertTrue(result["passed"])
        self.assertEqual(result["characterisation"]["revoiced_chords"][0], dict(step=32, notes=[48, 52, 55]))
        self.assertEqual(len(result["characterisation"]["revoiced_chords"]), 8)

    def test_slot_one_must_stay_literal(self):
        def altered(value):
            value["midi_contract"]["notes"][0]["note"] += 1
        with self.assertRaises(AssertionError):
            self.run_lesson(altered)

    def test_each_invariant_failure_surfaces_through_the_lesson_verifier(self):
        bad = [list(v) for v in REVOICED]
        bad[0] = [52, 55, 60]
        with self.assertRaises(inv.InvariantViolation):
            self.run_lesson(revoiced=bad)

    def test_revoice_may_not_move_a_chord_to_another_step(self):
        with self.assertRaises(AssertionError):
            self.run_lesson(steps=(0, 4, 8, 12), revoiced=REVOICED, offset=33)

    def test_unknown_invariant_kind_is_refused(self):
        def altered(value):
            value["midi_contract"]["invariants"][0]["kind"] = "lead"
        with self.assertRaisesRegex(ValueError, "invariant"):
            manual_audio.validate(dict(schema_version=1, examples=[self.altered(altered)]))

    def altered(self, mutate):
        value = example()
        mutate(value)
        return value

    def test_literal_notes_may_not_reach_the_revoiced_section(self):
        def altered(value):
            value["midi_contract"]["notes"].append(dict(port=1, status=144, note=60, velocity=80, step=32, length=2))
        with self.assertRaisesRegex(ValueError, "invariant"):
            manual_audio.validate(dict(schema_version=1, examples=[self.altered(altered)]))

    def test_the_revoiced_window_must_follow_the_literal_one(self):
        def altered(value):
            value["midi_contract"]["invariants"][0]["revoiced_start_step"] = 0
        with self.assertRaisesRegex(ValueError, "invariant"):
            manual_audio.validate(dict(schema_version=1, examples=[self.altered(altered)]))


def manual_audio_invariants_verify(contract, packets, key):
    return inv.verify_invariants(packets, contract, origin=0, clock_mode="controlled-experimental",
                                 port=1, status=144)


class Authoring(unittest.TestCase):
    MAJOR = [0, 2, 4, 5, 7, 9, 11]

    def triad(self, root):
        index = [v for v in range(7 * 11) if 12 * (v // 7) + self.MAJOR[v % 7] == root][0]
        return [12 * ((index + k) // 7) + self.MAJOR[(index + k) % 7] for k in (0, 2, 4)]

    def test_lesson_is_a_single_chord_channel_with_a_four_chord_progression(self):
        value = example()
        self.assertEqual(value["purpose"], "lesson-comparison")
        self.assertEqual([t["channel"] for t in value["tracks"]], [1])
        self.assertEqual(value["tracks"][0]["voice"], "Doubledecker")
        self.assertEqual(value["tracks"][0]["chords"], [2, 4])
        self.assertEqual(value["setup"], "voice-leading-revoice")
        self.assertEqual([(s["slot"], s["global_length"]) for s in value["sections"]], [(1, 32), (2, 32)])

    def test_slot_one_literal_chords_are_the_hand_derived_triads_and_nothing_else(self):
        value = example()
        roots = dict(value["tracks"][0]["phrase"])
        self.assertEqual(sorted(roots.items()), [(1, 48), (5, 45), (9, 53), (13, 55)])
        expected = sorted((n, 80, step + 16 * bar, 2) for bar in range(2) for s, r in roots.items()
                          for step in [s - 1] for n in self.triad(r))
        rows = value["midi_contract"]["notes"]
        self.assertEqual(sorted((v["note"], v["velocity"], v["step"], v["length"]) for v in rows), expected)
        self.assertTrue(all(v["step"] < 32 for v in rows))

    def test_invariant_window(self):
        spec = example()["midi_contract"]["invariants"]
        self.assertEqual(spec, [dict(kind="revoice", channel=1, reference_start_step=0, revoiced_start_step=32,
                                     length_steps=32)])

    def test_setup_leaves_slot_one_off_and_revokes_nothing(self):
        driver, value = run_setup()
        names = [n for n, a in driver.calls]
        self.assertEqual(driver.named("copy_slot"), [("copy_slot", (1, 2))])
        self.assertLess(names.index("copy_slot"), names.index("set_value"))
        self.assertEqual([a for n, a in driver.calls if n == "set_value"], [(1,)])
        self.assertIn(("expect_selected_field", ("detail", "Mode", "REVOICE")), driver.calls)
        after = driver.calls[names.index("set_value"):]
        self.assertIn(("press_key", (3,)), after)                  # K3 applies the draft

    def test_setup_reads_the_bass_setting_before_the_bass_rule_is_claimed(self):
        driver, value = run_setup()
        fields = [a[1:] for n, a in driver.calls if n == "expect_selected_field"]
        self.assertIn(("Mode", "ROOT"), fields)              # Bass: Root
        self.assertNotIn(("Common tones", "ON"), fields)     # no common-tone rule is made

    def test_witness_channel_is_revoiced_too(self):
        driver, value = run_setup(witnesses=True)
        self.assertEqual([a for n, a in driver.calls if n == "set_value"], [(1,), (1,)])


class Recorder:
    def __init__(self):
        self.calls = []
        self.results = []
        self.ui = self
        self.logical_ns = 0

    def __getattr__(self, name):
        if name in ("hold_step", "hold_keys", "hold_control"):
            @contextmanager
            def held(*args):
                self.calls.append((name, args))
                yield
            return held

        def call(*args, **kwargs):
            self.calls.append((name, args))
        return call

    def named(self, *names):
        return [(n, a) for n, a in self.calls if n in names]


def run_setup(witnesses=False, midi_only=True):
    value = example()
    driver = Recorder()
    manual_audio_setups.SETUPS[value["setup"]](driver, value, value["tracks"], witnesses, midi_only)
    return driver, value


if __name__ == "__main__":
    unittest.main()
