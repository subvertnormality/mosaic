"""Characterisation outside the README: canonical manual recording links and review fixes."""
from pathlib import Path
import os
import unittest
import yaml

ROOT = Path(os.environ.get("MOSAIC_REPO_ROOT", Path(__file__).resolve().parents[2])).resolve()
MANUAL = ROOT / "manual"


def read_yaml(name):
    return yaml.safe_load((MANUAL / name).read_text())


class RecordingReviewFixes(unittest.TestCase):
    def test_course_recordings_keep_exact_stage_ownership_and_canonical_routes(self):
        authored = read_yaml("recordings.yaml")["recordings"]
        course = read_yaml("course.yaml")["learning_path"]
        stage_owners = {stage["id"]: chapter["id"] for chapter in course for stage in chapter["stages"]}
        rows = {row["id"]: row for row in authored}
        expected = {
            "course-first-sound-hear": ("first-sound", "first-sound-hear"),
            "course-build-a-phrase-compare": ("build-a-phrase", "build-a-phrase-compare"),
            "course-masks-listen": ("masks", "masks-listen"),
            "course-masks-keep": ("masks", "masks-keep"),
            "course-sequence-composition-both": ("sequence-composition", "sequence-composition-both"),
            "course-harmony-design-apply": ("harmony-design", "harmony-design-apply"),
            "course-modulation-movement-and-interest-level": ("modulation-movement-and-interest", "modulation-movement-and-interest-level"),
            "course-song-composition-transition": ("song-composition", "song-composition-transition"),
            "course-keep-your-work-perform": ("keep-your-work", "keep-your-work-perform"),
        }
        self.assertTrue(set(expected) <= rows.keys())
        for recording_id, (chapter, stage) in expected.items():
            relation, = [r for r in rows[recording_id]["lesson_relations"] if r["kind"] == "course-stage"]
            self.assertEqual(relation["course_stage_id"], stage)
            self.assertEqual(stage_owners[stage], chapter)
            self.assertEqual(f"#{stage_owners[relation['course_stage_id']]}/lesson/{relation['course_stage_id']}",
                             f"#{chapter}/lesson/{stage}")

    def test_bass_listening_text_describes_authored_notes_without_volume_claims(self):
        scene = next(x for x in read_yaml("audio-scenes.yaml")["examples"] if x["id"] == "bass-and-intervals")
        context = next(x for x in read_yaml("recordings.yaml")["recordings"] if x["id"] == "bass-and-intervals")
        expected = "C-E-G chords on step 1 and D-F-A chords on step 9; the bass plays C2 on steps 1, 5 and 13 and G2 on step 9."
        self.assertIn("C-E-G chord on step 1", scene["description"])
        self.assertNotIn("more prominent layer", scene["description"])
        self.assertNotIn("steady bass", scene["description"])
        self.assertEqual(context["listen_for"], [expected])
        self.assertNotRegex(scene["description"].lower(), r"loud|quiet|prominent|underneath|above")

    def test_param_lock_synopsis_keeps_words_and_step_numbers_separate(self):
        context = next(x for x in read_yaml("recordings.yaml")["recordings"] if x["id"] == "param-lock-comparison")
        description = context["purpose"]
        self.assertIn("on steps 1 and 9", description)
        self.assertIn("on steps 5 and 13", description)
        self.assertNotRegex(description, r"onsteps|and9|and13")

    def test_decay_recipe_replays_recorded_gestures_and_separates_endpoint_practice(self):
        feature = next(x for x in read_yaml("features/reference-locks.yaml")["features"] if x["id"] == "locks")
        recipe = feature["recipes"][4]
        text = recipe["text"]
        self.assertIn("Recorded comparison — replay the captured relative gestures", text)
        self.assertIn("hold step 1 and replay the captured +200-detent E3 gesture", text)
        self.assertIn("hold step 5 and replay the captured +40-detent gesture", text)
        self.assertIn("Separate endpoint practice — a contextual contrast, not a reconstruction", text)
        self.assertIn("until the displayed Decay reaches its 0.1 s minimum", text)
        self.assertIn("3.2 s maximum", text)
        self.assertIn("steps 1 and 9 form the longer-tail group", text)
        self.assertIn("steps 5 and 13 form the shorter-tail group", text)
        self.assertIn("The retained capture records these encoder gestures, not displayed Decay values", text)
        self.assertNotIn("E3 event 126", text)
        self.assertNotIn("at detent 126", text)
        self.assertNotRegex(text, r"Inslot|holdstep|untilDecay|onsteps|200 detents|2\.1 s")
        recording = next(x for x in read_yaml("recordings.yaml")["recordings"] if x["id"] == "param-lock-comparison")
        relation, = [r for r in recording["lesson_relations"] if r.get("recipe_index") == 5]
        self.assertEqual(relation["relationship"], "exact")
        self.assertIn("dedicated replay of this recorded +200/+40-detent comparison", relation["explanation"])
        self.assertIn("separate endpoint-practice contrast", relation["explanation"])
        self.assertTrue(any("E3 event 126" in limit and "+200 and +40 detents" in limit
                            and "displayed Decay values" in limit
                            for limit in recording["limits"]))
        self.assertTrue(any("+200-detent E3 gesture" in step for step in recording["build_steps"]))
        self.assertTrue(any("+40-detent E3 gesture" in step for step in recording["build_steps"]))
        self.assertFalse(any("2.1" in step for step in recording["build_steps"]))


if __name__ == "__main__":
    unittest.main()
