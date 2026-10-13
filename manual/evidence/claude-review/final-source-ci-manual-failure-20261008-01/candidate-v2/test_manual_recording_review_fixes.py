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
        import re
        feature = next(x for x in read_yaml("features/reference-locks.yaml")["features"] if x["id"] == "locks")
        recipe = feature["recipes"][4]
        text = re.sub(r"\s+", " ", recipe["text"]).casefold()
        self.assertRegex(text, r"select slot 1.{0,100}?32 steps with no parameter locks.{0,120}?copy slot 1 to slot 2.{0,100}?32 steps.{0,100}?tap slot 2 before editing.{0,120}?assign decay to slot 1")
        self.assertRegex(text, r"hold step 1.{0,120}?turn e3 clockwise by 200 detents.{0,100}?repeat.{0,60}?200-detent turn on step 9")
        self.assertRegex(text, r"hold step 5.{0,120}?turn e3 clockwise by 40 detents.{0,100}?repeat.{0,60}?40-detent turn on step 13")
        self.assertRegex(text, r"steps 1 and 9.{0,60}?longer-tail group")
        self.assertRegex(text, r"steps 5 and 13.{0,60}?shorter-tail group")
        self.assertRegex(text, r"the note pattern stays fixed")
        endpoint = re.search(r"displayed decay reaches its 0\.1 s minimum", text)
        self.assertIsNotNone(endpoint)
        first_gesture = text.index("turn e3 clockwise by 200 detents")
        last_relative_gesture = text.index("turn e3 clockwise by 40 detents")
        self.assertLess(first_gesture, endpoint.start())
        self.assertLess(last_relative_gesture, endpoint.start())
        self.assertRegex(text[endpoint.start():], r"0\.1 s minimum.{0,120}?3\.2 s maximum")
        self.assertRegex(text[endpoint.start():], r"3\.2 s setting on step 9")
        self.assertRegex(text[endpoint.start():], r"0\.1 s on steps 5 and 13")
        self.assertRegex(text, r"select slot 1 to restore the unmodified line")
        self.assertRegex(text, r"stop and return to the separate course project")
        self.assertNotRegex(text, r"2\.1\s*s")
        recording = next(x for x in read_yaml("recordings.yaml")["recordings"] if x["id"] == "param-lock-comparison")
        relation, = [r for r in recording["lesson_relations"] if r.get("recipe_index") == 5]
        self.assertEqual(relation["feature_id"], "locks")
        self.assertEqual(relation["recipe_title"], recipe["title"])
        self.assertEqual(relation["relationship"], "exact")
        self.assertRegex(relation["explanation"].casefold(), r"\+200/\+40-detent comparison from this recording")
        self.assertRegex(relation["explanation"].casefold(), r"separate.{0,40}endpoint[- ]practice")
        self.assertRegex(relation["explanation"].casefold(), r"does not (?:show|include|capture).{0,40}absolute decay values?")
        build = " ".join(recording["build_steps"]).casefold()
        self.assertRegex(build, r"step 1.{0,100}?\+200-detent e3 gesture.{0,100}?step 9")
        self.assertRegex(build, r"step 5.{0,100}?\+40-detent e3 gesture.{0,100}?step 13")
        self.assertRegex(build, r"select slot 1.{0,100}?restore the no-lock line")
        self.assertNotRegex(build, r"2\.1\s*s")
        limits = " ".join(recording["limits"]).casefold()
        self.assertRegex(limits, r"e3 event 126.{0,120}?\+200 and \+40 detents")
        self.assertRegex(limits, r"does not record.{0,80}?displayed decay values")
        self.assertRegex(limits, r"not a reconstruction of those unseen values")


if __name__ == "__main__":
    unittest.main()
