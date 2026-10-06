"""Course listening clips: audio examples that reproduce a course stage and play it (controlled MIDI lane).

Characterisation outside README.md: these guard the manual's course audio fixtures. The expected music is
the course's own independent contract (tools/manual_course_cases.CONTRACTS, derived from the README
walk-through); an example only names it, the validator checks the tiled copy, and a run proves it on the
emitted MIDI. The state is reproduced by replaying the course itself through the public inputs.
"""
import copy
import os
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(1, str(REPO / "tests/behaviour"))
import manual_audio
import manual_audio_setups
import manual_course_cases as cases

# The listening ("hear") stages of the course and the CONTRACTS key each one plays.
CLIPS = {
    "first-sound-hear": "first-sound-hear",
    "build-a-phrase-compare": "build-a-phrase-compare",
    "masks-listen": "masks-listen",
    "masks-keep": "masks-keep",
    "sequence-composition-both": "sequence-composition-both",
    "harmony-design-apply": "harmony-design-apply-d",
    "modulation-movement-and-interest-level": "modulation-movement-and-interest-level",
    "song-composition-transition": "song-composition-transition",
    "keep-your-work-perform": "keep-your-work-perform",
}


def authored():
    return yaml.safe_load((REPO / "manual/audio-scenes.yaml").read_text())


def clips():
    return {v["course"]["stage"]: copy.deepcopy(v) for v in authored()["examples"] if "course" in v}


class Recorder:
    def __init__(self):
        self.calls = []
        self.results = []
        self.ui = self

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args))
        return call


class Authored(unittest.TestCase):
    def test_every_listening_stage_has_one_clip(self):
        self.assertEqual({k: v["course"]["contract_key"] for k, v in clips().items()}, CLIPS)

    def test_the_file_validates(self):
        manual_audio.validate(authored())

    def test_each_clip_is_a_lesson_comparison_that_replays_the_course(self):
        course = yaml.safe_load((REPO / "manual/course.yaml").read_text())["learning_path"]
        chapter_of = {s["id"]: c["id"] for c in course for s in c["stages"]}
        for stage, value in clips().items():
            self.assertEqual((value["purpose"], value["setup"], value["bpm"], value["bars"]), ("lesson-comparison", "course-stage", 90, 4), stage)
            self.assertIn(stage, chapter_of)
            self.assertIn(chapter_of[stage], value["feature_ids"])
            self.assertEqual(value["midi_contract"], manual_audio.course_contract(CLIPS[stage], 64), stage)
            self.assertNotIn("sections", value)

    def test_channels_are_the_channels_the_stage_sounds_on(self):
        for stage, value in clips().items():
            period, rows = cases.CONTRACTS[CLIPS[stage]]
            self.assertEqual(sorted(t["channel"] for t in value["tracks"]), sorted({r["status"] - 143 for r in rows}), stage)

    def test_descriptions_are_in_a_musicians_voice_and_name_what_to_listen_for(self):
        for stage, value in clips().items():
            self.assertIn("90 BPM", value["description"], stage)
            self.assertIn("Listen for", value["description"], stage)


class Setup(unittest.TestCase):
    def run_setup(self, target, course_function, witnesses=False):
        value = dict(clips().get("masks-listen"), course=dict(stage="masks-listen", contract_key=target))
        driver = Recorder()
        with patch.object(cases, "course", course_function):
            manual_audio_setups.SETUPS["course-stage"](driver, value, value["tracks"], witnesses, True)
        return driver

    def test_the_course_is_replayed_to_the_stage_and_its_listening_is_left_to_the_example(self):
        seen = []

        def course(c):
            seen.append("start")
            cases.musical(c, "first-sound-hear")
            seen.append("after-first")
            cases.musical(c, "masks-listen")
            seen.append("never")
        self.run_setup("masks-listen", course)
        self.assertEqual(seen, ["start", "after-first"])

    def test_earlier_listening_is_not_played_again(self):
        played = []

        def course(c):
            cases.musical(c, "first-sound-hear")
            cases.musical(c, "masks-listen")
        driver = self.run_setup("masks-listen", course)
        self.assertEqual(driver.calls, [])

    def test_a_course_that_never_reaches_the_stage_is_refused(self):
        with self.assertRaisesRegex(AssertionError, "never reached"):
            self.run_setup("masks-listen", lambda c: cases.musical(c, "first-sound-hear"))

    def test_the_real_musical_helper_is_restored_afterwards(self):
        before = cases.musical
        self.run_setup("masks-listen", lambda c: cases.musical(c, "masks-listen"))
        self.assertIs(cases.musical, before)

    def test_witness_channels_are_refused_because_the_before_after_check_replaces_them(self):
        with self.assertRaisesRegex(ValueError, "before/after MIDI check, not witness channels"):
            self.run_setup("masks-listen", lambda c: cases.musical(c, "masks-listen"), witnesses=True)

    def test_a_target_that_is_not_a_course_contract_is_refused(self):
        with self.assertRaisesRegex(ValueError, "contract_key"):
            self.run_setup("masks-nothing", lambda c: None)


class Configure(unittest.TestCase):
    def test_a_course_clip_starts_from_the_empty_project_not_from_track_masks(self):
        value = clips()["masks-listen"]
        driver = Recorder()
        stub = lambda c: (driver.calls.append(("course", ())), cases.musical(c, "masks-listen"))
        with patch.object(cases, "course", stub):
            manual_audio.configure(driver, value, value["tracks"], midi_only=True)
        self.assertEqual([n for n, a in driver.calls], ["course"])


if __name__ == "__main__":
    unittest.main()
