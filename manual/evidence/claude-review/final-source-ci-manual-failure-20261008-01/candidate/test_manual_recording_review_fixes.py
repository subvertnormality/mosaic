"""Characterisation outside the README: canonical manual recording links and review fixes."""
from pathlib import Path
import os
import unittest
import yaml

ROOT = Path(os.environ.get("MOSAIC_REPO_ROOT", Path(__file__).resolve().parents[2])).resolve()
MANUAL = ROOT / "manual"


def read_yaml(name):
    return yaml.safe_load((MANUAL / name).read_text())


def assert_decay_recipe_contract(testcase, recipe, recording):
    text = recipe["text"]
    relative = text.split("Relative-turn comparison —", 1)[1].split("Separate endpoint practice —", 1)[0]
    endpoint = text.split("Separate endpoint practice —", 1)[1].split("\n\nRestore:", 1)[0]
    testcase.assertIn("This recipe has two exercises", text)
    testcase.assertIn("Use a separate project so neither changes your course arrangement", text)
    testcase.assertIn("Separate endpoint practice — try the 0.1 s and 3.2 s endpoints", text)
    testcase.assertIn("Comparison purpose: keep the note pattern fixed while only the Decay envelope changes", text)
    copy = "Copy slot 1 to slot 2 and keep slot 2 at 32 steps."
    select = "Tap slot 2 before editing its locks."
    assign = "Open Channel tasks → Trig params and assign Decay to slot 1."
    straight = "In Song, select slot 1 and set its length to 32 steps with no parameter locks; this is the two-bar straight reference."
    testcase.assertIn(straight, relative)
    testcase.assertIn(copy, relative)
    testcase.assertIn(select, relative)
    testcase.assertIn(assign, relative)
    testcase.assertLess(relative.index(copy), relative.index(select))
    testcase.assertLess(relative.index(select), relative.index(assign))
    testcase.assertLess(relative.index(straight), relative.index(copy))
    for phrase in (
        "hold step 1 and turn E3 clockwise by 200 detents; release it",
        "Repeat the 200-detent turn on step 9 and release",
        "hold step 5 and turn E3 clockwise by 40 detents; release it",
        "Repeat the 40-detent turn on step 13 and release",
        "steps 1 and 9 form the longer-tail group",
        "steps 5 and 13 form the shorter-tail group",
        "the note pattern stays fixed",
        "These turns are relative to the current setting",
        "Select slot 1 before comparing the two slots",
    ):
        testcase.assertIn(phrase, relative)
    testcase.assertIn("In Song set slot 1 to 32 steps with no parameter locks. Copy slot 1 to slot 2 and set its length to 32.", endpoint)
    testcase.assertIn("hold step 1 and turn E3 anticlockwise until the displayed Decay reaches its 0.1 s minimum, then clockwise to the displayed 3.2 s maximum", endpoint)
    testcase.assertIn("Repeat the 3.2 s setting on step 9", endpoint)
    testcase.assertIn("Set Decay to 0.1 s on steps 5 and 13", endpoint)
    testcase.assertIn("long settings on 1 and 9 and short settings on 5 and 13", endpoint)
    testcase.assertIn("Select slot 1 before comparing the two slots", endpoint)
    testcase.assertIn("Play slots 1 and 2, then stop and select slot 1", endpoint)
    testcase.assertIn("Restore: Select slot 1 to restore the unmodified line", text)
    testcase.assertIn("return to the separate course project", text)
    relation, = [row for row in recording["lesson_relations"] if row.get("recipe_index") == 5]
    testcase.assertEqual(relation["feature_id"], "locks")
    testcase.assertEqual(relation["recipe_title"], recipe["title"])
    testcase.assertEqual(relation["relationship"], "exact")
    testcase.assertIn("+200/+40-detent comparison from this recording", relation["explanation"])
    testcase.assertIn("separate endpoint-practice contrast", relation["explanation"])
    testcase.assertIn("does not show absolute Decay values", relation["explanation"])
    testcase.assertIn("A parameter lock sets a device parameter for one trig only", recording["purpose"])
    testcase.assertIn("does not change the note pattern", recording["purpose"])
    builds = "\n".join(recording["build_steps"])
    testcase.assertIn("Copy slot 1 to slot 2", builds)
    testcase.assertIn("hold step 1 and replay the captured +200-detent E3 gesture", builds)
    testcase.assertIn("Hold step 5 and replay the captured +40-detent E3 gesture", builds)
    testcase.assertIn("steps 1 and 9 are the longer-tail group", builds)
    testcase.assertIn("steps 5 and 13 are the shorter-tail group", builds)
    testcase.assertIn("restore the no-lock line", builds)
    testcase.assertIn("E3 event 126", recording["limits"][0])
    testcase.assertIn("+200 and +40 detents while steps are held", recording["limits"][0])
    testcase.assertIn("does not record the displayed Decay values", recording["limits"][0])
    testcase.assertIn("not a reconstruction of those unseen values", recording["limits"][0])
    testcase.assertIn("Select slot 1 to restore the unmodified line", recording["restore_steps"][0])
    testcase.assertIn("return to the separate course project", recording["restore_steps"][0])
    testcase.assertNotIn("E3 event 126", text)
    testcase.assertNotIn("displayed Decay values", text)


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
        recording = next(x for x in read_yaml("recordings.yaml")["recordings"] if x["id"] == "param-lock-comparison")
        assert_decay_recipe_contract(self, recipe, recording)

    def test_decay_recipe_contract_rejects_control_and_provenance_mutations(self):
        from copy import deepcopy
        feature = next(x for x in read_yaml("features/reference-locks.yaml")["features"] if x["id"] == "locks")
        recording = next(x for x in read_yaml("recordings.yaml")["recordings"] if x["id"] == "param-lock-comparison")
        cases = [
            ("gesture size", lambda recipe, rec: recipe.__setitem__("text", recipe["text"].replace("clockwise by 200 detents", "clockwise by 20 detents", 1))),
            ("endpoint", lambda recipe, rec: recipe.__setitem__("text", recipe["text"].replace("0.1 s minimum", "0.2 s minimum", 1))),
            ("copy order", lambda recipe, rec: recipe.__setitem__("text", recipe["text"].replace("Copy slot 1 to slot 2 and keep slot 2 at 32 steps.", "Edit slot 2 before copying slot 1.", 1))),
            ("restore target", lambda recipe, rec: recipe.__setitem__("text", recipe["text"].replace("Restore: Select slot 1 to restore", "Restore: Select slot 2 to restore", 1))),
            ("recording linkage", lambda recipe, rec: rec["lesson_relations"][0].__setitem__("relationship", "contextual")),
            ("recording provenance", lambda recipe, rec: rec["limits"].__setitem__(0, rec["limits"][0].replace("does not record the displayed Decay values", "records the displayed Decay values", 1))),
        ]
        for label, mutate in cases:
            with self.subTest(mutation=label):
                changed_recipe = deepcopy(feature["recipes"][4])
                changed_recording = deepcopy(recording)
                mutate(changed_recipe, changed_recording)
                with self.assertRaises(AssertionError):
                    assert_decay_recipe_contract(self, changed_recipe, changed_recording)


if __name__ == "__main__":
    unittest.main()
