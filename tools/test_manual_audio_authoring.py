"""Authoring rules for new manual audio examples (characterisation outside README.md:
these guard the manual's audio fixtures, not instrument behaviour)."""
import copy
import os
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
import manual_audio
import manual_audio_setups
from manual_course_cases import CONTRACTS


def authored():
    return yaml.safe_load((REPO / "manual/audio-scenes.yaml").read_text())


def example(ident):
    return copy.deepcopy(next(v for v in authored()["examples"] if v["id"] == ident))


def check(*examples):
    return manual_audio.validate(dict(schema_version=1, examples=list(examples)))


def sectioned(bars=8, lengths=(64, 64)):
    """Ghost lesson re-authored as a song: slot 1 then slot 2 (each keeps its own settings)."""
    value = example("ghost-note-comparison")
    value.update(id="ghost-song", bars=bars)
    value["tracks"][0].pop("bar_phrases")
    value["sections"] = [dict(slot=n + 1, global_length=length, changes=[]) for n, length in enumerate(lengths)]
    notes = value["midi_contract"]["notes"]
    value["midi_contract"] = dict(cycle_steps=bars * 16,
                                  notes=[dict(row, step=row["step"] + 64 * k) for k in range(bars // 4) for row in notes])
    value["sections"][-1]["changes"] = [dict(kind="trig_merge", mode="all")]
    return value


class CycleLength(unittest.TestCase):
    def test_existing_authoring_still_validates(self):
        manual_audio.validate(authored())

    def test_cycle_steps_must_be_bars_times_sixteen(self):
        value = example("ghost-note-comparison");value["midi_contract"]["cycle_steps"] = 128
        with self.assertRaisesRegex(ValueError, "cycle_steps"):check(value)

    def test_eight_bar_song_with_sections_validates(self):
        check(sectioned())

    def test_eight_bars_without_sections_keep_the_four_bar_rule(self):
        value = sectioned();value.pop("sections")
        with self.assertRaisesRegex(ValueError, "four bars"):check(value)

    def test_other_bar_counts_are_rejected_even_with_sections(self):
        value = sectioned(bars=8);value["bars"] = 6
        with self.assertRaisesRegex(ValueError, "bars"):check(value)

    def test_tempo_stays_ninety(self):
        value = sectioned();value["bpm"] = 120
        with self.assertRaises(ValueError):check(value)

    def test_contract_cycle_steps_defaults_to_the_four_bar_cycle(self):
        self.assertEqual(manual_audio.contract_cycle_steps(example("oilcan-pocket")), 64)
        self.assertEqual(manual_audio.contract_cycle_steps(sectioned()), 128)


class FractionalSteps(unittest.TestCase):
    def with_note(self, **fields):
        value = example("ghost-note-comparison")
        value["midi_contract"]["notes"][-1].update(fields)
        return value

    def test_swing_offset_in_twenty_fourths_is_accepted(self):
        check(self.with_note(step=33.25, length=0.25))

    def test_third_of_a_step_written_as_a_float_is_accepted(self):
        check(self.with_note(step=float(Fraction(100, 3)), length=float(Fraction(1, 3))))

    def test_step_not_a_multiple_of_one_twenty_fourth_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "1/24"):check(self.with_note(step=33.1))

    def test_step_off_a_twenty_fourth_by_more_than_representation_error_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "1/24"):check(self.with_note(step=33.0417))

    def test_gate_not_a_multiple_of_one_twenty_fourth_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "1/24"):check(self.with_note(length=0.3))

    def test_step_must_lie_before_the_cycle_boundary(self):
        with self.assertRaisesRegex(ValueError, "step"):check(self.with_note(step=64))
        with self.assertRaises(ValueError):check(self.with_note(step=-1))

    def test_eight_bar_contract_may_use_steps_beyond_sixty_four(self):
        value = sectioned();value["midi_contract"]["notes"][-1]["step"] = 127.5
        check(value)


class Setups(unittest.TestCase):
    def test_registry_holds_exactly_the_reviewed_setups(self):
        self.assertEqual(set(manual_audio_setups.SETUPS), {"swing-comparison", "note-merge-modes", "song-sections", "harmony-strum-arp", "param-lock-comparison", "voice-leading-revoice", "course-stage"})
        self.assertIs(manual_audio.SETUPS, manual_audio_setups.SETUPS)

    def test_register_names_a_setup_once(self):
        with patch.dict(manual_audio_setups.SETUPS, clear=True):
            @manual_audio_setups.register("probe")
            def probe(*args):pass
            self.assertIs(manual_audio_setups.SETUPS["probe"], probe)
            with self.assertRaisesRegex(ValueError, "probe"):
                manual_audio_setups.register("probe")(lambda *args: None)

    def test_unknown_setup_is_rejected(self):
        value = example("oilcan-pocket");value["setup"] = "no-such-setup"
        with self.assertRaisesRegex(ValueError, "setup"):check(value)

    def test_registered_setup_is_accepted(self):
        value = example("oilcan-pocket");value["setup"] = "probe"
        with patch.dict(manual_audio_setups.SETUPS, {"probe": lambda *args: None}):check(value)


class Sections(unittest.TestCase):
    def test_four_bar_song_of_two_slots_is_accepted(self):
        check(sectioned(bars=4, lengths=(32, 32)))

    def test_every_change_kind_in_the_vocabulary_is_accepted(self):
        value = sectioned()
        value["sections"][1]["changes"] = [dict(kind=kind) for kind in sorted(manual_audio.SECTION_CHANGE_KINDS)]
        self.assertEqual(manual_audio.SECTION_CHANGE_KINDS, {"note_merge", "trig_merge", "swing", "octave", "mute",
                                                             "harmony", "merge_shape", "trig_param", "range", "mask"})
        check(value)

    def test_unknown_change_kind_is_rejected(self):
        value = sectioned();value["sections"][1]["changes"] = [dict(kind="tempo")]
        with self.assertRaisesRegex(ValueError, "section change"):check(value)

    def test_change_without_kind_is_rejected(self):
        value = sectioned();value["sections"][1]["changes"] = [dict(mode="all")]
        with self.assertRaisesRegex(ValueError, "section change"):check(value)

    def test_lengths_must_cover_the_whole_recording(self):
        with self.assertRaisesRegex(ValueError, "global_length"):check(sectioned(bars=8, lengths=(64, 32)))

    def test_global_length_must_be_whole_bars_between_one_and_four(self):
        for lengths in ((24, 40), (8, 56)):
            with self.assertRaisesRegex(ValueError, "global_length"):check(sectioned(bars=4, lengths=lengths))
        with self.assertRaisesRegex(ValueError, "global_length"):check(sectioned(bars=8, lengths=(80, 48)))

    def test_slots_ascend_from_one_without_gaps(self):
        for slots in ((2, 3), (1, 1), (2, 1), (1, 3)):
            value = sectioned()
            for section, slot in zip(value["sections"], slots):section["slot"] = slot
            with self.assertRaisesRegex(ValueError, "section slots"):check(value)

    def test_at_most_four_song_slots(self):
        with self.assertRaises(ValueError):check(sectioned(bars=8, lengths=(16, 16, 16, 16, 64)))

    def test_sections_cannot_be_combined_with_timed_phase_changes(self):
        value = example("scale-slot-comparison");value.update(sections=[dict(slot=1, global_length=64, changes=[])])
        with self.assertRaisesRegex(ValueError, "phase_changes"):check(value)


class Course(unittest.TestCase):
    def test_course_contract_tiles_the_stage_cycle(self):
        period, rows = CONTRACTS["masks-quiet"]
        tiled = manual_audio.course_contract("masks-quiet", 64)
        self.assertEqual(tiled["cycle_steps"], 64)
        self.assertEqual(tiled["notes"], [dict(row, step=row["step"] + period * k) for k in range(4) for row in rows])

    def test_course_contract_requires_whole_cycles(self):
        with self.assertRaisesRegex(ValueError, "cycle"):manual_audio.course_contract("song-composition-transition", 48)
        with self.assertRaisesRegex(ValueError, "contract_key"):manual_audio.course_contract("masks-unknown", 64)

    def course_example(self, stage="masks", key="masks-quiet"):
        value = example("oilcan-pocket")
        value.update(course=dict(stage=stage, contract_key=key), midi_contract=manual_audio.course_contract("masks-quiet", 64))
        return value

    def test_course_example_with_matching_contract_validates(self):
        check(self.course_example())

    def test_unknown_course_stage_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "course stage"):check(self.course_example(stage="no-stage"))

    def test_contract_key_must_belong_to_the_stage(self):
        with self.assertRaisesRegex(ValueError, "contract_key"):check(self.course_example(stage="first-sound"))

    def test_a_real_stage_id_names_its_chapter(self):
        check(self.course_example(stage="masks-quiet", key="masks-quiet"))

    def test_contract_key_must_belong_to_the_chapter_of_a_stage_id(self):
        with self.assertRaisesRegex(ValueError, "contract_key"):check(self.course_example(stage="masks-listen", key="first-sound-hear"))

    def test_changed_course_contract_is_rejected(self):
        value = self.course_example();value["midi_contract"]["notes"][0]["velocity"] = 81
        with self.assertRaisesRegex(ValueError, "course contract"):check(value)

    def test_reordered_course_contract_is_the_same_score(self):
        value = self.course_example();value["midi_contract"]["notes"].reverse()
        check(value)


class Polymeter(unittest.TestCase):
    def test_range_last_repeats_the_phrase_with_its_own_period(self):
        track = dict(phrase=[[1, 36], [7, 38]], range_last=12)
        self.assertEqual(manual_audio.expand(track, 4),
                         [[12 * k + step, note] for k in range(6) for step, note in [[1, 36], [7, 38]] if 12 * k + step <= 64])

    def test_expand_without_range_last_is_unchanged(self):
        track = example("three-voice-conversation")["tracks"][2]
        self.assertEqual(manual_audio.expand(track, 4),
                         [[b * 16 + s, n] for b in range(3) for s, n in track["phrase"]] +
                         [[48 + s, n] for s, n in track["final_bar"]])

    def test_range_last_accepted_and_bounds_phrase(self):
        value = example("oilcan-pocket");value["tracks"][0]["range_last"] = 15
        check(value)
        value["tracks"][0]["range_last"] = 14
        with self.assertRaisesRegex(ValueError, "phrase bounds"):check(value)

    def test_relative_phrase_may_reach_range_last_beyond_sixteen(self):
        value = example("scale-slot-comparison");value["tracks"][1]["range_last"] = 20
        value["tracks"][1]["phrase"].append([19, 2])
        check(value)

    def test_range_last_limits(self):
        for last in (0, 65):
            value = example("oilcan-pocket");value["tracks"][0]["range_last"] = last
            with self.assertRaisesRegex(ValueError, "range_last"):check(value)

    def test_range_last_cannot_be_combined_with_bar_specific_phrases(self):
        value = example("ghost-note-comparison");value["tracks"][0]["range_last"] = 16
        with self.assertRaisesRegex(ValueError, "range_last"):check(value)


class MergedPatterns(unittest.TestCase):
    def merged(self):
        value = example("scale-slot-comparison")
        track = value["tracks"][0]
        track.pop("pattern");phrase = track.pop("phrase");track.pop("velocity_overrides")
        track["patterns"] = [dict(pattern=1, phrase=phrase), dict(pattern=3, phrase=[[3, 2], [11, 4]])]
        return value

    def test_several_patterns_may_feed_one_relative_channel(self):
        check(self.merged())

    def test_patterns_replace_pattern_and_phrase(self):
        value = self.merged();value["tracks"][0]["pattern"] = 1
        with self.assertRaisesRegex(ValueError, "patterns"):check(value)
        value = self.merged();value["tracks"][0]["phrase"] = [[1, 0]]
        with self.assertRaisesRegex(ValueError, "patterns"):check(value)

    def test_patterns_require_relative_mode(self):
        value = example("oilcan-pocket");track = value["tracks"][0]
        track["patterns"] = [dict(pattern=1, phrase=track.pop("phrase")), dict(pattern=2, phrase=[[3, 36]])]
        with self.assertRaisesRegex(ValueError, "patterns"):check(value)

    def test_pattern_numbers_are_unique_across_the_example(self):
        value = self.merged();value["tracks"][0]["patterns"][1]["pattern"] = 2
        with self.assertRaisesRegex(ValueError, "pattern"):check(value)
        value = self.merged();value["tracks"][0]["patterns"][1]["pattern"] = 1
        with self.assertRaisesRegex(ValueError, "pattern"):check(value)

    def test_each_assigned_phrase_is_bounded(self):
        value = self.merged();value["tracks"][0]["patterns"][1]["phrase"] = [[3, 7]]
        with self.assertRaisesRegex(ValueError, "phrase bounds"):check(value)
        value = self.merged();value["tracks"][0]["patterns"][1]["pattern"] = 17
        with self.assertRaisesRegex(ValueError, "pattern"):check(value)


class RelativeWithoutPhases(unittest.TestCase):
    def test_relative_song_without_timed_phase_changes_validates(self):
        value = example("scale-slot-comparison");value.pop("phase_changes")
        value.update(bars=8, sections=[dict(slot=1, global_length=64, changes=[]),
                                       dict(slot=2, global_length=64, changes=[dict(kind="harmony", scale_slot=2)])])
        notes = value["midi_contract"]["notes"]
        value["midi_contract"] = dict(cycle_steps=128, notes=notes + [dict(row, step=row["step"] + 64) for row in notes])
        check(value)

    def test_declared_phase_changes_still_require_the_c_and_d_comparison(self):
        value = example("scale-slot-comparison");value["scale_slots"][1]["root_detents"] = 0
        with self.assertRaisesRegex(ValueError, "C and D"):check(value)


class LessonPcmDispatch(unittest.TestCase):
    def test_proofs_are_keyed_by_pcm_kind(self):
        self.assertEqual(set(manual_audio.LESSON_PCM_PROOFS), {"ghost-note-interiors", "relative-scale-pitch-interiors"})

    def test_kind_selection_matches_the_reviewed_sessions(self):
        ghost = example("ghost-note-comparison");scale = example("scale-slot-comparison")
        self.assertEqual(manual_audio.lesson_pcm_kind(ghost, ghost["tracks"]), "ghost-note-interiors")
        self.assertEqual(manual_audio.lesson_pcm_kind(scale, scale["tracks"][1:]), "relative-scale-pitch-interiors")
        self.assertIsNone(manual_audio.lesson_pcm_kind(scale, scale["tracks"]))
        self.assertIsNone(manual_audio.lesson_pcm_kind(scale, scale["tracks"][:1]))
        self.assertIsNone(manual_audio.lesson_pcm_kind(example("oilcan-pocket"), example("oilcan-pocket")["tracks"]))


if __name__ == "__main__":
    unittest.main()
