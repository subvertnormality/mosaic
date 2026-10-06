"""The four 1.4.0 lesson comparisons: swing, note merge modes, polymeter and song sections.

Each authored midi_contract is checked against an independent hand model of the
README behaviour it demonstrates (the models below are written from the manual,
never read back from a run). Setup functions are checked against a recording
double of the public input path. Anything not stated in README.md is labelled
"characterisation" with its source.
"""
import copy
import math
import os
import sys
import unittest
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(1, str(REPO / "tests/behaviour"))
import manual_audio
import manual_audio_setups
import channel_gestures

LESSONS = ("swing-comparison", "note-merge-modes", "polymeter", "song-sections", "harmony-strum-arp", "param-lock-comparison")


def authored():
    return yaml.safe_load((REPO / "manual/audio-scenes.yaml").read_text())


def example(ident):
    return copy.deepcopy(next(v for v in authored()["examples"] if v["id"] == ident))


def row(channel, note, velocity, step, length):
    return dict(port=channel, status=143 + channel, note=note, velocity=velocity, step=step, length=length)


def literal(rows):
    """Contract rows as exact (channel, note, velocity, step, length) 1/24-step tuples."""
    return sorted((v["port"], v["status"], v["note"], v["velocity"],
                   manual_audio.twenty_fourths(v["step"]), manual_audio.twenty_fourths(v["length"])) for v in rows)


def modelled(rows):
    return sorted((v["port"], v["status"], v["note"], v["velocity"],
                   manual_audio.twenty_fourths(v["step"]), manual_audio.twenty_fourths(v["length"])) for v in rows)


def track(value, channel):
    return next(t for t in value["tracks"] if t["channel"] == channel)


class Recorder:
    """Public-input double: every ui/driver call is logged in order."""

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
                self.calls.append((name + ":release", args))
            return held

        def call(*args, **kwargs):
            self.calls.append((name, args))
        return call

    def named(self, *names):
        return [(n, a) for n, a in self.calls if n in names]


def run_setup(ident, witnesses=False, midi_only=True):
    value = example(ident)
    driver = Recorder()
    manual_audio_setups.SETUPS[value["setup"]](driver, value, value["tracks"], witnesses, midi_only)
    return driver, value


class AuthoredLessons(unittest.TestCase):
    def test_all_four_validate_as_lesson_comparisons_at_ninety_bpm_for_four_bars(self):
        data = authored()
        manual_audio.validate(data)
        for ident in LESSONS:
            value = example(ident)
            self.assertEqual((value["bpm"], value["bars"], value["purpose"]), (90, 4, "lesson-comparison"))
            self.assertTrue(1 <= len(value["tracks"]) <= 3)
            self.assertEqual(value["midi_contract"]["cycle_steps"], 64)
            self.assertTrue(all(1 <= t["channel"] <= 3 for t in value["tracks"]))
            self.assertTrue(all(t["voice"] in manual_audio.VOICES for t in value["tracks"]))

    def test_each_lesson_names_its_reviewed_setup(self):
        self.assertEqual({i: example(i).get("setup") for i in LESSONS},
                         {"swing-comparison": "swing-comparison", "note-merge-modes": "note-merge-modes",
                          "polymeter": None, "song-sections": "song-sections",
                          "harmony-strum-arp": "harmony-strum-arp", "param-lock-comparison": "param-lock-comparison"})
        for setup in ("swing-comparison", "note-merge-modes", "song-sections", "harmony-strum-arp", "param-lock-comparison"):
            self.assertIn(setup, manual_audio_setups.SETUPS)


class SwingComparison(unittest.TestCase):
    """README #clocks-swing-and-shuffle: swing moves notes off the grid, -50..50. Swing 25 moves
    each even step of a pair 25 percent of a step later (literal pulse table 0/30/48/78 of case
    M-MANUAL-SWING-001). Gate under swing is characterisation: lib/clock/m_lattice.lua times a
    gate below one step as a fraction of the step's own swung interval (1.25 / 0.75 steps)."""

    def model(self, value):
        rows = []
        for t in value["tracks"]:
            for global_step in range(64):
                slot_swing = Fraction(25, 100) if global_step >= 32 else 0
                step = global_step % 16 + 1
                note = dict(t["phrase"]).get(step)
                if note is None:
                    continue
                leader = step % 2 == 1
                onset = Fraction(global_step) + (0 if leader else slot_swing)
                gate = Fraction(1, 2) * ((1 + slot_swing) if leader else (1 - slot_swing))
                rows.append(row(t["channel"], note, t["velocity"], float(onset), float(gate)))
        return rows

    def test_contract_matches_the_hand_model(self):
        value = example("swing-comparison")
        self.assertEqual(literal(value["midi_contract"]["notes"]), modelled(self.model(value)))

    def test_literal_anchors(self):
        value = example("swing-comparison")
        notes = {(v["port"], v["step"]): v for v in value["midi_contract"]["notes"]}
        drums = track(value, 1)["phrase"]
        self.assertEqual(drums[:2], [[1, 36], [2, 37]])
        self.assertEqual((notes[(1, 1)]["note"], notes[(1, 1)]["length"]), (37, 0.5))      # slot 1 is straight
        self.assertEqual((notes[(1, 33.25)]["note"], notes[(1, 33.25)]["length"]), (37, 0.375))  # slot 2 even step: +6/24, gate 9/24
        self.assertEqual(notes[(1, 32)]["length"], 0.625)                                    # slot 2 pair leader: gate 15/24
        self.assertNotIn((1, 33), notes)

    def test_slot_one_straight_slot_two_swung_sections(self):
        value = example("swing-comparison")
        self.assertEqual([(s["slot"], s["global_length"], [(c["kind"], c.get("amount")) for c in s["changes"]])
                          for s in value["sections"]],
                         [(1, 32, []), (2, 32, [("swing", 25)])])

    def test_setup_swings_every_channel_in_slot_two_only_after_copying_slot_one(self):
        driver, value = run_setup("swing-comparison")
        names = [n for n, a in driver.calls]
        self.assertEqual(driver.named("copy_slot"), [("copy_slot", (1, 2))])
        self.assertLess(names.index("copy_slot"), names.index("channel_page"))
        taps = [a for n, a in driver.calls if n == "tap_control" and a[0] == "song_pattern_slot"]
        self.assertEqual(taps, [("song_pattern_slot", 2), ("song_pattern_slot", 1)])
        swung = [a[0] for n, a in driver.calls if n == "select_channel"]
        self.assertEqual(swung, [1, 2])
        self.assertEqual(sum(1 for n, a in driver.calls if n == "set_value" and a == (76,)), 2)

    def test_setup_with_witnesses_swings_the_witness_channels_too(self):
        driver, value = run_setup("swing-comparison", witnesses=True)
        self.assertEqual([a[0] for n, a in driver.calls if n == "select_channel"], [1, 2, 15, 16])


class NoteMergeModes(unittest.TestCase):
    """README #note-merge-modes: Average rounds half up; Higher = rounded average + (max - min);
    one contributor passes through. Trig merge All (README #merge-modes) plays a union of trigs.
    'Lock merged to pent.' is off, so degrees map through plain C major (60 62 64 65 67 69 71, +12 per 7)."""

    MAJOR = [0, 2, 4, 5, 7, 9, 11]

    def pitch(self, degree):
        return 60 + 12 * (degree // 7) + self.MAJOR[degree % 7]

    def merge(self, degrees, mode):
        mean = Fraction(sum(degrees), len(degrees))
        average = math.floor(mean + Fraction(1, 2))
        if len(degrees) == 1:
            return degrees[0]
        return average if mode == "average" else average + max(degrees) - min(degrees)

    def model(self, value):
        melody = value["tracks"][0]
        by_step = {}
        for assigned in melody["patterns"]:
            for step, degree in assigned["phrase"]:
                by_step.setdefault(step, []).append(degree)
        rows = []
        for bar in range(4):
            mode = "average" if bar < 2 else "higher"
            for step in sorted(by_step):
                rows.append(row(melody["channel"], self.pitch(self.merge(by_step[step], mode)),
                                melody["velocity"], bar * 16 + step - 1, 0.5))
        return rows

    def test_contract_matches_the_hand_model(self):
        value = example("note-merge-modes")
        self.assertEqual(literal(value["midi_contract"]["notes"]), modelled(self.model(value)))

    def test_one_melody_channel_fed_by_two_patterns_in_relative_mode(self):
        value = example("note-merge-modes")
        self.assertEqual(value["mode"], "relative-scale-slots")
        self.assertEqual(len(value["tracks"]), 1)
        self.assertEqual([p["pattern"] for p in value["tracks"][0]["patterns"]], [1, 2])

    def test_literal_anchors(self):
        notes = {v["step"]: v["note"] for v in example("note-merge-modes")["midi_contract"]["notes"]}
        # step 9: degrees 0 and 3 average to 1.5, which rounds up to 2 (E4 64); Higher gives 2 + 3 = 5 (A4 69)
        self.assertEqual((notes[8], notes[40]), (64, 69))
        # step 5: degrees 4 and 6 -> Average 5 (A4 69); Higher 5 + 2 = 7, an octave above the root (C5 72)
        self.assertEqual((notes[4], notes[36]), (69, 72))
        # step 3 has one contributor and is unchanged in both halves
        self.assertEqual((notes[2], notes[34]), (64, 64))

    def test_sections_set_all_trigs_then_higher(self):
        value = example("note-merge-modes")
        self.assertEqual([(s["slot"], s["global_length"], [(c["kind"], c.get("mode")) for c in s["changes"]])
                          for s in value["sections"]],
                         [(1, 32, [("trig_merge", "all")]), (2, 32, [("note_merge", "higher")])])

    def test_setup_turns_off_pentatonic_lock_before_building_slots(self):
        driver, value = run_setup("note-merge-modes")
        self.assertEqual(driver.named("set_mosaic_options"), [("set_mosaic_options", ([("Lock merged to pent.", False)],))])
        self.assertLess(driver.calls.index(driver.named("set_mosaic_options")[0]), driver.calls.index(driver.named("copy_slot")[0]))

    def test_setup_all_trigs_in_slot_one_then_higher_in_slot_two(self):
        driver, value = run_setup("note-merge-modes")
        names = [(n, a) for n, a in driver.calls if n in ("copy_slot",) or (n == "tap_control" and a[0] in ("trig_merge_mode", "note_merge_mode"))]
        self.assertEqual([n if n == "copy_slot" else a[0] for n, a in names],
                         ["trig_merge_mode", "trig_merge_mode", "copy_slot", "note_merge_mode"])

    def test_setup_with_witnesses_repeats_the_merge_settings_on_witness_channel(self):
        driver, value = run_setup("note-merge-modes", witnesses=True)
        self.assertEqual([a[0] for n, a in driver.calls if n == "select_channel"], [1, 15, 1, 15])


class Polymeter(unittest.TestCase):
    """README #channel-length: a channel plays its own start..end range and loops; ranges cannot
    exceed the global length (64). Drums range 16 and bass range 12 first start together again
    after lcm(16, 12) = 48 steps. Reset at Pattern Repeat is off by default (#reset-at-pattern-repeat),
    so only the first 64-step pass is asserted and the closing onset is the drums' step 1."""

    def model(self, value):
        rows = []
        for t in value["tracks"]:
            period = t["range_last"]
            for global_step in range(64):
                note = dict(t["phrase"]).get(global_step % period + 1)
                if note is not None:
                    rows.append(row(t["channel"], note, t["velocity"], global_step, 0.5))
        return rows

    def test_contract_matches_the_hand_model(self):
        value = example("polymeter")
        self.assertEqual(literal(value["midi_contract"]["notes"]), modelled(self.model(value)))

    def test_ranges_are_sixteen_and_twelve_and_realign_at_forty_eight(self):
        value = example("polymeter")
        self.assertEqual([t["range_last"] for t in value["tracks"]], [16, 12])
        self.assertEqual(16 * 12 // math.gcd(16, 12), 48)  # math.lcm needs Python 3.9; CI runs 3.8
        starts = {(v["port"], v["step"]) for v in value["midi_contract"]["notes"]}
        self.assertIn((1, 48), starts)
        self.assertIn((2, 48), starts)
        self.assertNotIn((2, 64), starts)

    def test_bass_ends_mid_cycle_inside_the_recording(self):
        value = example("polymeter")
        bass = [v["step"] for v in value["midi_contract"]["notes"] if v["port"] == 2]
        self.assertEqual([s for s in bass if s >= 60], [60, 63])

    def test_no_setup_and_no_sections(self):
        value = example("polymeter")
        self.assertNotIn("setup", value)
        self.assertNotIn("sections", value)

    def configured(self, ident):
        value = example(ident)
        ranges = []
        driver = Recorder()
        driver.ui.set_range = lambda first, last: ranges.append((first, last))
        driver.enc = lambda *a: None
        with patch.object(manual_audio, "set_tempo"), patch.object(manual_audio, "route_track"), \
                patch.object(manual_audio, "set_mask_field"):
            manual_audio.configure(driver, value, value["tracks"], midi_only=True)
        return driver, ranges

    def test_configure_gives_each_channel_its_own_range_and_programs_only_that_range(self):
        driver, ranges = self.configured("polymeter")
        self.assertEqual(ranges, [(1, 16), (1, 12)])
        held = [a[0] for n, a in driver.calls if n == "hold_step"]
        value = example("polymeter")
        drums = {s for s, _ in value["tracks"][0]["phrase"]}
        bass = {s for s, _ in value["tracks"][1]["phrase"]}
        self.assertTrue(held)
        self.assertLessEqual(max(held), 16)       # nothing is programmed beyond the longer range
        self.assertEqual(set(held), drums | bass)

    def test_configure_without_range_last_still_uses_the_whole_sequence(self):
        value = example("ghost-note-comparison")
        ranges = []
        driver = Recorder()
        driver.ui.set_range = lambda first, last: ranges.append((first, last))
        driver.enc = lambda *a: None
        with patch.object(manual_audio, "set_tempo"), patch.object(manual_audio, "route_track"), \
                patch.object(manual_audio, "set_mask_field"):
            manual_audio.configure(driver, value, value["tracks"], midi_only=True)
        self.assertEqual(ranges, [(1, 64)])


class SongSections(unittest.TestCase):
    """README #song-mode-operations (slots advance in turn and loop), #adjusting-song-sequence-length
    (global length 1..64), #muting-channels (per sequence), channel octave (+12 per octave, case
    M-UIACC / composition_workflow) and #masks (velocity mask). Each slot is a copy of the previous
    slot plus its listed changes."""

    MAJOR = [0, 2, 4, 5, 7, 9, 11]

    def pitch(self, degree, octave):
        return 60 + 12 * (degree // 7 + octave) + self.MAJOR[degree % 7]

    def model(self, value):
        bass, lead = track(value, 1), track(value, 2)
        layout = [(0, 16, dict(lead_muted=True, lead_octave=0, bass_velocity=70)),
                  (16, 48, dict(lead_muted=False, lead_octave=0, bass_velocity=70)),
                  (48, 64, dict(lead_muted=False, lead_octave=1, bass_velocity=40))]
        rows = []
        for first, last, state in layout:
            for global_step in range(first, last):
                step = global_step % 16 + 1
                for t, octave, velocity, muted in ((bass, bass["octave"], state["bass_velocity"], False),
                                                   (lead, state["lead_octave"], lead["velocity"], state["lead_muted"])):
                    degree = dict(t["phrase"]).get(step)
                    if degree is not None and not muted:
                        rows.append(row(t["channel"], self.pitch(degree, octave), velocity, global_step, 0.5))
        return rows

    def test_contract_matches_the_hand_model(self):
        value = example("song-sections")
        self.assertEqual(literal(value["midi_contract"]["notes"]), modelled(self.model(value)))

    def test_sections_are_sixteen_thirty_two_sixteen(self):
        value = example("song-sections")
        self.assertEqual([s["global_length"] for s in value["sections"]], [16, 32, 16])
        self.assertEqual(sum(s["global_length"] for s in value["sections"]), 64)
        kinds = [[c["kind"] for c in s["changes"]] for s in value["sections"]]
        self.assertEqual(kinds, [["mute"], ["mute"], ["octave", "mask"]])

    def test_literal_anchors(self):
        notes = [(v["port"], v["step"], v["note"], v["velocity"]) for v in example("song-sections")["midi_contract"]["notes"]]
        self.assertNotIn(2, {p for p, s, n, v in notes if s < 16})              # lead sits out the intro
        self.assertIn((2, 18, 67, 60), notes)                                    # lead enters in slot 2 at step 3 of the bar
        self.assertIn((2, 50, 79, 60), notes)                                    # slot 3: an octave higher (67 + 12)
        self.assertIn((1, 52, 48, 40), notes)                                    # slot 3: bass velocity mask 40
        self.assertIn((1, 36, 48, 70), notes)                                    # slot 2: bass unchanged

    def test_mask_change_kind_is_part_of_the_vocabulary(self):
        self.assertIn("mask", manual_audio.SECTION_CHANGE_KINDS)

    def test_setup_builds_slots_in_order_from_the_previous_slot(self):
        driver, value = run_setup("song-sections")
        self.assertEqual(driver.named("copy_slot"), [("copy_slot", (1, 2)), ("copy_slot", (2, 3))])
        slots = [a[1] for n, a in driver.calls if n == "tap_control" and a[0] == "song_pattern_slot"]
        self.assertEqual(slots, [2, 3, 1])
        lengths = [a[1] for n, a in driver.calls if n == "tap_control" and a[0] == "global_pattern_length"]
        taps = [channel_gestures.global_length_taps(n) for n in (16, 32, 16)]
        self.assertEqual(lengths, [c for group in taps for c in group])
        rows = [a for n, a in driver.calls if n == "expect_dashboard_row"]
        self.assertEqual(rows, [("Global length", "16"), ("Global length", "32"), ("Global length", "16")])

    def test_setup_applies_mute_octave_and_mask_through_public_inputs(self):
        driver, value = run_setup("song-sections")
        held = [a for n, a in driver.calls if n == "hold_keys"]
        self.assertEqual(held, [(1,), (1,)])
        mutes = [a for n, a in driver.calls if n == "tap_control" and a[0] == "channel" and len(a) == 2]
        self.assertTrue({2}.issubset({a[1] for a in mutes}))
        self.assertEqual(driver.named("set_channel_octave"), [("set_channel_octave", (1,))] * 1)
        self.assertIn(("expect_field_value", ("velocity", "40")), [(n, a) for n, a in driver.calls])

    def test_setup_with_witnesses_applies_each_change_to_the_witness_channel(self):
        driver, value = run_setup("song-sections", witnesses=True)
        muted = [a[1] for n, a in driver.calls if n == "tap_control" and a[0] == "channel" and len(a) == 2]
        self.assertIn(16, muted)
        self.assertEqual(driver.named("set_channel_octave"), [("set_channel_octave", (1,))] * 2)


class HarmonyStrumArp(unittest.TestCase):
    """README #adding-chords (up to four chord masks on a root), #chord-strum, #chord-arpeggio,
    #chord-acceleration and #chord-spread. The gap before chord slot k (first gap k=1) is
    d + s*(1 + (k-1)*a) channel steps; the first slot sounds at the trigger. Strum d = 1, Spread
    s = 1, Acceleration a = -1: gap 1 = 2 steps, gap 2 = 1 step, so the three slots (root, Chd1, Chd2)
    sound at 0, 2 and 3. A strummed note keeps the selected note length from its own onset
    (README #chord-spread: spacing modifiers 'do not change the selected note length'); every strum
    onset here is a whole step. An arp overrules a strum. Arp d = 1/2 with the same Spread and
    Acceleration: gaps 3/2 and 1/2 put the slots at 0 and 3/2, and the third would start at the
    original endpoint (step 2), where README #chord-arpeggio says no further note starts; each arp
    note lasts one division from its onset, shortened to finish at the endpoint. The values are step
    trig locks on the four chord steps (README #trig-param-locks), made in the slot they belong to.
    Chord masks 2 and 4 are the 3rd and 5th scale degrees above the root in C major
    (characterisation: the manual's own bass-and-intervals recipe, 'Chd1 set to 3rd, Chd2 to 5th')."""

    MAJOR = [0, 2, 4, 5, 7, 9, 11]
    LENGTH = Fraction(2)

    def triad(self, root):
        index = [v for v in range(7 * 11) if 12 * (v // 7) + self.MAJOR[v % 7] == root][0]
        return [12 * ((index + k) // 7) + self.MAJOR[(index + k) % 7] for k in (0, 2, 4)]

    def slot_times(self, d, s, a):
        """Onsets of root, Chd1, Chd2 from the README gap formula; a gap of zero or less ends the chord."""
        times, at = [Fraction(0)], Fraction(0)
        for k in (1, 2):
            gap = d + s * (1 + (k - 1) * a)
            if gap <= 0:
                break
            at += gap
            times.append(at)
        return times

    def model(self, value):
        lead, rows = track(value, 1), []
        strum = self.slot_times(Fraction(1), Fraction(1), -1)
        arp = self.slot_times(Fraction(1, 2), Fraction(1), -1)
        for global_step in range(64):
            root = dict(lead["phrase"]).get(global_step % 16 + 1)
            if root is None:
                continue
            for note, offset in zip(self.triad(root), strum if 16 <= global_step < 48 else arp if global_step >= 48 else [Fraction(0)] * 3):
                onset = global_step + offset
                if global_step >= 48:
                    if offset >= self.LENGTH:
                        continue                                   # no note starts at the original endpoint
                    length = min(Fraction(1, 2), global_step + self.LENGTH - onset)
                else:
                    length = self.LENGTH
                rows.append(row(1, note, lead["velocity"], float(onset), float(length)))
        return rows

    def test_contract_matches_the_hand_model(self):
        value = example("harmony-strum-arp")
        self.assertEqual(literal(value["midi_contract"]["notes"]), modelled(self.model(value)))

    def test_literal_anchors(self):
        notes = {(v["step"], v["note"]): v for v in example("harmony-strum-arp")["midi_contract"]["notes"]}
        for note in (60, 64, 67):                                  # slot 1: C block chord, all together
            self.assertEqual((notes[(0, note)]["length"], notes[(0, note)]["velocity"]), (2, 80))
        self.assertEqual(notes[(18, 64)]["length"], 2)             # slot 2 strum: Chd1 two steps after the root
        self.assertEqual(notes[(19, 67)]["length"], 2)             # Chd2 one step after that
        self.assertEqual(notes[(49.5, 64)]["length"], 0.5)         # slot 3 arp: second note at 3/2, one division
        self.assertNotIn((50, 67), notes)                          # nothing starts at the endpoint
        self.assertEqual(notes[(48, 60)]["length"], 0.5)

    def test_three_sections_block_then_strum_then_arp(self):
        value = example("harmony-strum-arp")
        self.assertEqual([(s["slot"], s["global_length"]) for s in value["sections"]], [(1, 16), (2, 32), (3, 16)])
        params = [[(c["param"], c["slot"], sorted({tuple(l[1:]) for l in c["locks"]}), [l[0] for l in c["locks"]])
                   for c in s["changes"]] for s in value["sections"]]
        steps = [1, 5, 9, 13]
        self.assertEqual(params, [[], [("chord_note_strum", 1, [(14, "1")], steps), ("chord_spread", 2, [(14, "1")], steps),
                                       ("chord_accel_mod", 3, [(4, "-1")], steps)],
                                  [("chord_note_arpeggio", 4, [(8, "1/2")], steps)]])

    def test_setup_locks_each_parameter_on_the_chord_steps_after_copying_the_previous_slot(self):
        driver, value = run_setup("harmony-strum-arp")
        assigned = [a[0] for n, a in driver.calls if n == "assign_trig_parameter_key"]
        self.assertEqual(assigned, ["chord_note_strum", "chord_spread", "chord_accel_mod", "chord_note_arpeggio"])
        names = [n for n, a in driver.calls]
        self.assertLess(names.index("copy_slot"), names.index("assign_trig_parameter_key"))
        self.assertEqual(driver.named("copy_slot"), [("copy_slot", (1, 2)), ("copy_slot", (2, 3))])
        self.assertEqual([a[0] for n, a in driver.calls if n == "hold_step"], [1, 5, 9, 13] * 4)
        self.assertEqual([a for n, a in driver.calls if n == "turn" and a[0] == 3],
                         [(3, d) for d in (14, 14, 14, 14, 14, 14, 14, 14, 4, 4, 4, 4, 8, 8, 8, 8)])
        shown = [a[1:] for n, a in driver.calls if n == "expect_selected_param"]
        self.assertEqual([a[0] for a in shown], ["1"] * 8 + ["-1"] * 4 + ["1/2"] * 4)
        self.assertEqual({a[1] for a in shown}, {"L"})
        self.assertEqual([a for n, a in driver.calls if n == "set_value"], [])         # channel values stay Off

    def test_setup_with_witnesses_repeats_each_parameter_on_the_witness_channel(self):
        driver, value = run_setup("harmony-strum-arp", witnesses=True)
        self.assertEqual([a[0] for n, a in driver.calls if n == "assign_trig_parameter_key"],
                         ["chord_note_strum"] * 2 + ["chord_spread"] * 2 + ["chord_accel_mod"] * 2 + ["chord_note_arpeggio"] * 2)

    def test_chords_are_the_third_and_fifth(self):
        self.assertEqual(track(example("harmony-strum-arp"), 1)["chords"], [2, 4])


class ParamLockComparison(unittest.TestCase):
    """README #trig-param-locks: hold a step and adjust a parameter to lock its value to that step.
    Slot 1 has no locks; slot 2 locks steps 1, 5, 9 and 13 of the 16-step phrase. A voice parameter
    lock does not change any MIDI note, so the MIDI witness also locks CC 1 on the same steps: the
    controller values prove lock timing on a CC (not the voice parameter). With the lock lead at the
    harness default of 0 a value leaves at its own step (README Lock lead time: 'Set it to 0 to send
    each value at its own step')."""

    CC_VALUES = {1: 10, 5: 40, 9: 70, 13: 100}

    def model_notes(self, value):
        lead, rows = track(value, 1), []
        for global_step in range(64):
            note = dict(lead["phrase"]).get(global_step % 16 + 1)
            if note is not None:
                rows.append(row(1, note, lead["velocity"], global_step, 0.5))
        return rows

    def model_controls(self):
        return sorted((1, 176, 1, self.CC_VALUES[step], 24 * (32 + 16 * bar + step - 1))
                      for bar in (0, 1) for step in self.CC_VALUES)

    def test_notes_match_the_hand_model_and_ignore_the_lock(self):
        value = example("param-lock-comparison")
        self.assertEqual(literal(value["midi_contract"]["notes"]), modelled(self.model_notes(value)))

    def test_controllers_sit_on_the_locked_steps_of_slot_two_only(self):
        controls = example("param-lock-comparison")["midi_contract"]["controls"]
        self.assertEqual(sorted((v["port"], v["status"], v["controller"], v["value"],
                                 manual_audio.twenty_fourths(v["step"])) for v in controls), self.model_controls())
        self.assertTrue(all(v["step"] >= 32 for v in controls))

    def test_literal_anchors(self):
        value = example("param-lock-comparison")
        notes = {(v["step"]): v for v in value["midi_contract"]["notes"]}
        self.assertEqual((notes[0]["note"], notes[32]["note"], notes[32]["length"]), (48, 48, 0.5))   # same note locked or not
        self.assertEqual(notes[2]["note"], 55)
        self.assertEqual(value["midi_contract"]["controls"][0], dict(port=1, status=176, controller=1, value=10, step=32))

    def test_two_sections_unlocked_then_locked(self):
        value = example("param-lock-comparison")
        self.assertEqual([(s["slot"], s["global_length"], [(c["target"], c.get("param", c.get("label"))) for c in s["changes"]])
                          for s in value["sections"]],
                         [(1, 32, []), (2, 32, [("voice", "Decay"), ("midi", "stored_patch_cc1")])])

    def lock_calls(self, driver):
        return [(n, a) for n, a in driver.calls if n in ("hold_step", "encoder_event", "turn", "expect_selected_param", "select_channel",
                                                       "assign_trig_parameter_key", "assign_trig_parameter")]

    def test_midi_lane_locks_cc_one_on_the_authored_channel_only(self):
        driver, value = run_setup("param-lock-comparison", midi_only=True)
        calls = self.lock_calls(driver)
        self.assertEqual([a for n, a in calls if n == "assign_trig_parameter_key"], [("stored_patch_cc1",)])
        self.assertEqual([a for n, a in calls if n == "assign_trig_parameter"], [])
        self.assertEqual([a[0] for n, a in calls if n == "hold_step"], [1, 5, 9, 13])
        self.assertEqual([a for n, a in calls if n == "encoder_event"], [(3, -126)] * 4)
        self.assertEqual([a for n, a in calls if n == "turn" and a[0] == 3], [(3, v + 1) for v in (10, 40, 70, 100)])   # Off, then v up
        self.assertEqual([a[:2] for n, a in calls if n == "expect_selected_param"], [(1, "10"), (1, "40"), (1, "70"), (1, "100")])
        self.assertEqual({a[2] for n, a in calls if n == "expect_selected_param"}, {"L"})

    def test_locks_are_made_only_after_slot_one_is_copied(self):
        driver, value = run_setup("param-lock-comparison", midi_only=True)
        names = [n for n, a in driver.calls]
        self.assertLess(names.index("copy_slot"), names.index("hold_step"))
        self.assertEqual(driver.named("copy_slot"), [("copy_slot", (1, 2))])

    def test_audio_session_locks_the_voice_on_the_voice_channel_and_cc_on_the_witness(self):
        driver, value = run_setup("param-lock-comparison", witnesses=True, midi_only=False)
        calls = self.lock_calls(driver)
        self.assertEqual([a[0] for n, a in calls if n == "select_channel"], [1, 15])
        self.assertEqual([a for n, a in calls if n == "assign_trig_parameter"], [("Decay",)])
        self.assertEqual([a for n, a in calls if n == "assign_trig_parameter_key"], [("stored_patch_cc1",)])
        self.assertEqual(len([1 for n, a in calls if n == "hold_step"]), 8)
        # the voice-parameter lock's value display is not asserted (unverified without an audio session)
        self.assertEqual(len([1 for n, a in calls if n == "expect_selected_param"]), 4)


class SectionDriver(unittest.TestCase):
    def test_mask_change_is_a_known_section_kind_and_validates(self):
        value = example("song-sections")
        manual_audio.validate(dict(schema_version=1, examples=[value]))

    def test_unknown_change_kind_is_refused_when_applied(self):
        value = example("song-sections")
        value["sections"][0]["changes"] = [dict(kind="swing", amount=10)]
        value["sections"][2]["changes"] = []
        driver = Recorder()
        manual_audio_setups.apply_sections(driver, value, value["tracks"], False)
        value["sections"][0]["changes"] = [dict(kind="merge_shape")]
        with self.assertRaisesRegex(ValueError, "section change"):
            manual_audio_setups.apply_sections(Recorder(), value, value["tracks"], False)


class GlobalLengthFader(unittest.TestCase):
    """README #adjusting-song-sequence-length. Characterisation: the grid fader is eight cells, cell 1
    and 8 step down/up by one and cells 2-7 jump proportionally (lib/controls/fader.lua)."""

    def press(self, value, cell, size=64, length=8):
        middle_cell = (length + 1) // 2
        if cell == 1 and value > 1:
            return value - 1
        if cell == length and value < size:
            return value + 1
        if cell - 1 == middle_cell - 1:
            return (size + 1) // 2
        if cell not in (1, length):
            positions = length - 2
            return (cell - 2) * (size - 1) // (positions - 1) + 1
        return value

    def test_taps_reach_every_whole_bar_length(self):
        for length in (16, 32, 48, 64):
            value = 64
            for cell in channel_gestures.global_length_taps(length):
                value = self.press(value, cell)
            self.assertEqual(value, length)

    def test_taps_reach_any_length(self):
        for length in range(1, 65):
            value = 64
            for cell in channel_gestures.global_length_taps(length):
                value = self.press(value, cell)
            self.assertEqual(value, length)

    def test_out_of_range_lengths_are_refused(self):
        for length in (0, 65):
            with self.assertRaises(ValueError):
                channel_gestures.global_length_taps(length)


class SwingGesture(unittest.TestCase):
    def test_swing_amount_is_selected_from_the_unset_position(self):
        driver = Recorder()
        channel_gestures.set_channel_swing(driver.ui, 2, 25)
        self.assertEqual(driver.calls[0][0], "channel_page")
        self.assertEqual(driver.calls[0][1], ("clock_mods",))
        self.assertEqual(driver.named("set_value"), [("set_value", (1,)), ("set_value", (76,))])
        self.assertEqual(driver.named("press_key"), [("press_key", (3,)), ("press_key", (3,))])
        self.assertEqual(driver.named("select_field"), [("select_field", ("swing",)), ("select_field", ("swing_x",))])

    def test_reopened_clock_screen_returns_to_its_first_row_when_asked(self):
        driver = Recorder()
        channel_gestures.set_channel_swing(driver.ui, 2, 25, from_top=True)
        self.assertEqual(driver.named("select_field")[0], ("select_field", ("clock_first_row",)))
        self.assertEqual(driver.named("set_value"), [("set_value", (1,)), ("set_value", (76,))])


class MergedPatternConfiguration(unittest.TestCase):
    def test_expand_describes_every_assigned_pattern_for_a_merged_track(self):
        value = example("note-merge-modes")
        expanded = manual_audio.expand(value["tracks"][0], 4)
        self.assertEqual(len(expanded), 4 * sum(len(p["phrase"]) for p in value["tracks"][0]["patterns"]))

    def test_configure_builds_every_assigned_pattern_and_assigns_each_to_the_channel(self):
        value = example("note-merge-modes")
        driver = Recorder()
        driver.enc = lambda *a: None
        with patch.object(manual_audio, "set_tempo"), patch.object(manual_audio, "route_track"), \
                patch.object(manual_audio, "set_mask_field"):
            manual_audio.configure(driver, value, value["tracks"], midi_only=True)
        selects = [a[1] for n, a in driver.calls if n == "tap_control" and a[0] == "pattern_select"]
        assigns = [a[1] for n, a in driver.calls if n == "tap_control" and a[0] == "pattern_slot"]
        degrees = [a[1] for n, a in driver.calls if n == "tap_control" and a[0] == "pattern_note_degree"]
        self.assertEqual(selects, [1, 2])
        self.assertEqual(assigns, [1, 2])
        self.assertEqual(len(degrees), sum(len(p["phrase"]) for p in value["tracks"][0]["patterns"]))
        self.assertEqual(driver.named("set_range"), [("set_range", (1, 16))])


class TextRules(unittest.TestCase):
    def test_descriptions_are_in_a_musicians_voice_and_name_what_to_listen_for(self):
        for ident in LESSONS:
            text = example(ident)["description"]
            self.assertIn("90 BPM", text)
            self.assertIn("Listen for", text)
            self.assertNotIn("TODO", text)


class SoloSectionDriver(unittest.TestCase):
    def solo_song(self):
        value = example("song-sections")
        value["sections"] = [
            dict(slot=1, global_length=16, changes=[dict(kind="mute", channel=2)]),
            dict(slot=2, global_length=32, changes=[dict(kind="mute", channel=2)]),
            dict(slot=3, global_length=16, changes=[
                dict(kind="octave", channel=2, value=1),
                dict(kind="mask", channel=1, field="velocity", value=40),
            ]),
        ]
        return value

    def test_authored_inactive_channel_changes_are_skipped_without_losing_song_slots(self):
        value = self.solo_song()
        active = [track(value, 1)]
        driver = Recorder()

        manual_audio_setups.apply_sections(driver, value, active, witnesses=True)

        self.assertEqual(driver.named("copy_slot"), [
            ("copy_slot", (1, 2)),
            ("copy_slot", (2, 3)),
        ])
        self.assertEqual(
            [args for name, args in driver.named("expect_dashboard_row") if args[0] == "Global length"],
            [("Global length", "16"), ("Global length", "32"), ("Global length", "16")],
        )
        self.assertEqual([args[0] for name, args in driver.named("select_channel")], [1, 15])
        self.assertNotIn(("select_channel", (2,)), driver.calls)
        self.assertNotIn(("select_channel", (16,)), driver.calls)
        self.assertEqual(len([1 for name, args in driver.named("expect_field_value")
                              if args == ("velocity", "40")]), 2)

    def test_unknown_inactive_authored_channel_fails_before_public_input(self):
        value = self.solo_song()
        value["sections"][0]["changes"] = [dict(kind="mute", channel=99)]
        driver = Recorder()

        with self.assertRaisesRegex(ValueError, "unknown channel 99"):
            manual_audio_setups.apply_sections(driver, value, [track(value, 1)], witnesses=True)

        self.assertEqual(driver.calls, [])

if __name__ == "__main__":
    unittest.main()
