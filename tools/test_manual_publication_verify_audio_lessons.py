"""Reviewed canonical audio lessons in the publication audit (characterisation of
publication integrity outside README.md)."""
import copy
import importlib.util
import sys
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("manual_publication_verify", ROOT / "tools/manual_publication_verify.py")
audit = importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def authored():
    return yaml.safe_load((ROOT / "manual/audio-scenes.yaml").read_text())


def lesson_report(source):
    record = lambda path: dict(midi_witness=dict(passed=True), phase_observations=[dict()] * len(source.get("phase_changes", [])),
                               evidence=dict(path=path))
    solos = [dict(record("/native/solo-%d" % t["channel"]), channel=t["channel"], voice=t["voice"]) for t in source["tracks"]]
    example = dict(source, **record("/native/mix"), solo_contributions=solos,
                   musical_evidence=[dict(clock_mode=c, path="/native/" + c, passed=True) for c in ("real-time", "controlled-experimental")])
    return dict(examples=[example]), dict(examples=[source])


COURSE_CLIPS = {
    "course-first-sound-hear": "1a5b62c8005d3814c4ccbcc2267c0b9e8aa28a0d19a63df1cbe8a23b9554095d",
    "course-build-a-phrase-compare": "e9270efc530db0c38460a3510a90b1c9472c9555f98e9817cbdaf6b7d9f16461",
    "course-masks-listen": "25986edc83e58d4bb74f4833e04ce2681e1a5e47551173ac15d27d0f77160816",
    "course-masks-keep": "ce12437c3e822b57f5b2e800a5c6b74c9a808693c017daef93bce493a9bd01a2",
    "course-sequence-composition-both": "211361a734e7290a84f107eb27f1301ff8e7846419a29fcf8c30c5b48916ffcd",
    "course-harmony-design-apply": "50404544295da7a9e3fe215efe7d68916e27938595cde38c3af0efde72912348",
    "course-modulation-movement-and-interest-level": "b57298c2d4c7edbaa96d02c1a613f7b73d424c7a11ab287f49dffb6c21caffa0",
    "course-song-composition-transition": "ab7d62be1e3de3a20f5b6a7f307079c6f53b5ed56959bca1102353aefc52dd25",
    "course-keep-your-work-perform": "ab7d62be1e3de3a20f5b6a7f307079c6f53b5ed56959bca1102353aefc52dd25",
}


class CanonicalLessons(unittest.TestCase):
    def test_table_holds_exactly_the_reviewed_lessons(self):
        self.assertEqual(audit.CANONICAL_AUDIO_LESSONS, {
            "ghost-note-comparison": dict(setup=None, pcm_kind="ghost-note-interiors", pcm_solo_voice=None,
                                          contract_sha256="aec0ea3979f584d5dfb9764b707858808c9861072b3a373f0e3fa3a37d49f34c"),
            "scale-slot-comparison": dict(setup=None, pcm_kind="relative-scale-pitch-interiors", pcm_solo_voice="Polyperc 1",
                                          contract_sha256="4561961c69a54d7acbfdf9ad68acc46379d062e330599bdc44126e8d2bcaedde"),
            "swing-comparison": dict(setup="swing-comparison", pcm_kind=None, pcm_solo_voice=None,
                                     contract_sha256="526b650233ea32ecdc4ecf8384eeeaab8ed417ff86c32cb6f974da5f01a14bdf"),
            "note-merge-modes": dict(setup="note-merge-modes", pcm_kind=None, pcm_solo_voice=None,
                                     contract_sha256="bc9c51c9651332d4a59c639f9ab64326b75747f6caeb3ab3a4a4edac50261ff0"),
            "polymeter": dict(setup=None, pcm_kind=None, pcm_solo_voice=None,
                              contract_sha256="507203d0d95546d20263e22db8cf129b32da0c1bada55030b88ef8431bd2be7e"),
            "song-sections": dict(setup="song-sections", pcm_kind=None, pcm_solo_voice=None,
                                  contract_sha256="93f4d125d8e7cd298479cbb127977675f08b25b957ab2f1734fbc065649dda05"),
            "harmony-strum-arp": dict(setup="harmony-strum-arp", pcm_kind=None, pcm_solo_voice=None,
                                      contract_sha256="6638a7ef7f50a289b57fcdcb17ca5ed47eb9b5642989ce7e79c4d6f8135d6e48"),
            "param-lock-comparison": dict(setup="param-lock-comparison", pcm_kind=None, pcm_solo_voice=None,
                                          contract_sha256="41e49730507f030869244fc2425b0aa4f39ab57ed2822ce0243d55bbd5bbaadf"),
            "voice-leading-revoice": dict(setup="voice-leading-revoice", pcm_kind=None, pcm_solo_voice=None,
                                          contract_sha256="13d0eebb1203b2c336f1fb072a57681a2d80dbb21845d5fbac7fca8ce5fafcbd"),
            **{ident: dict(setup="course-stage", pcm_kind=None, pcm_solo_voice=None, contract_sha256=sha) for ident, sha in COURSE_CLIPS.items()}})

    def test_current_authored_lessons_match_the_table(self):
        self.assertEqual(audit.check_canonical_audio_lessons(authored()),
                         {"ghost-note-comparison", "scale-slot-comparison", "swing-comparison", "note-merge-modes",
                          "polymeter", "song-sections", "harmony-strum-arp", "param-lock-comparison", "voice-leading-revoice", *COURSE_CLIPS})

    def test_tampered_invariants_are_rejected(self):
        data = authored()
        lesson = next(v for v in data["examples"] if v["id"] == "voice-leading-revoice")
        lesson["midi_contract"]["invariants"][0]["length_steps"] -= 4
        with self.assertRaisesRegex(ValueError, "canonical audio lesson contract"):audit.check_canonical_audio_lessons(data)

    def test_tampered_lesson_contract_is_rejected(self):
        for ident in ("ghost-note-comparison", "scale-slot-comparison", "swing-comparison", "note-merge-modes",
                      "polymeter", "song-sections", "harmony-strum-arp", "param-lock-comparison", "voice-leading-revoice", *COURSE_CLIPS):
            data = authored()
            lesson = next(v for v in data["examples"] if v["id"] == ident)
            lesson["midi_contract"]["notes"][0]["velocity"] -= 1
            with self.assertRaisesRegex(ValueError, "canonical audio lesson contract"):audit.check_canonical_audio_lessons(data)

    def test_tampered_lesson_controller_is_rejected(self):
        data = authored()
        lesson = next(v for v in data["examples"] if v["id"] == "param-lock-comparison")
        lesson["midi_contract"]["controls"][0]["value"] += 1
        with self.assertRaisesRegex(ValueError, "canonical audio lesson contract"):audit.check_canonical_audio_lessons(data)
        lesson["midi_contract"]["controls"][0]["value"] -= 1
        lesson["midi_contract"]["controls"].pop()
        with self.assertRaisesRegex(ValueError, "canonical audio lesson contract"):audit.check_canonical_audio_lessons(data)

    def test_unreviewed_lesson_is_rejected(self):
        data = authored()
        data["examples"].append(dict(copy.deepcopy(data["examples"][3]), id="invented-lesson"))
        with self.assertRaisesRegex(ValueError, "Unsupported new audio lesson"):audit.check_canonical_audio_lessons(data)

    def test_lesson_setup_must_match_the_table(self):
        source = next(v for v in authored()["examples"] if v["id"] == "ghost-note-comparison")
        report, wanted = lesson_report(source)
        for record in [report["examples"][0]] + report["examples"][0]["solo_contributions"]:
            record["lesson_pcm"] = dict(kind="ghost-note-interiors", passed=True)
        self.assertEqual(len(audit.check_audio_capture_scope(report, wanted)), 4)
        report["examples"][0]["setup"] = wanted["examples"][0]["setup"] = "song-sections"
        with self.assertRaisesRegex(ValueError, "setup"):audit.check_audio_capture_scope(report, wanted)


class MidiContractLessonScope(unittest.TestCase):
    """The 1.4.0 comparisons carry no PCM proof: their witness is the literal MIDI contract."""

    def test_each_new_lesson_needs_its_mix_and_every_solo_and_no_pcm_proof(self):
        for ident in ("swing-comparison", "note-merge-modes", "polymeter", "song-sections", "harmony-strum-arp", "param-lock-comparison"):
            source = next(v for v in authored()["examples"] if v["id"] == ident)
            report, wanted = lesson_report(source)
            self.assertEqual(len(audit.check_audio_capture_scope(report, wanted)), 1 + len(source["tracks"]) + 2)
            bad = copy.deepcopy(report);bad["examples"][0]["lesson_pcm"] = dict(kind="ghost-note-interiors", passed=True)
            with self.assertRaisesRegex(ValueError, "Unsupported new audio lesson PCM proof"):audit.check_audio_capture_scope(bad, wanted)

    def test_changed_setup_is_rejected_for_each_new_lesson(self):
        for ident in ("swing-comparison", "note-merge-modes", "polymeter", "song-sections", "harmony-strum-arp", "param-lock-comparison"):
            source = next(v for v in authored()["examples"] if v["id"] == ident)
            report, wanted = lesson_report(source)
            report["examples"][0]["setup"] = wanted["examples"][0]["setup"] = "scale-sections"
            with self.assertRaisesRegex(ValueError, "setup"):audit.check_audio_capture_scope(report, wanted)

    def test_each_lesson_still_needs_both_midi_lanes(self):
        source = next(v for v in authored()["examples"] if v["id"] == "polymeter")
        report, wanted = lesson_report(source)
        report["examples"][0]["musical_evidence"] = report["examples"][0]["musical_evidence"][:1]
        with self.assertRaisesRegex(ValueError, "both MIDI lanes"):audit.check_audio_capture_scope(report, wanted)
        report, wanted = lesson_report(source)
        report["examples"][0]["musical_evidence"] = report["examples"][0]["musical_evidence"][1:]
        self.assertEqual(len(audit.check_audio_capture_scope(report, wanted, controlled_local=True)), 1 + len(source["tracks"]) + 1)


class CourseBeforeAfterScope(unittest.TestCase):
    """Course clips are voice-routed: a before/after MIDI check takes the place of the witness lanes."""
    PARTS = ("before", "route_to_voices", "take", "route_to_midi", "after")

    def course(self, ident="course-sequence-composition-both"):
        source = next(v for v in authored()["examples"] if v["id"] == ident)
        row = dict(kind="manual-audio-course-before-after", passed=True, **{k: dict() for k in self.PARTS})
        record = lambda path: dict(course_before_after=copy.deepcopy(row), phase_observations=[], evidence=dict(path=path))
        solos = [dict(record("/native/solo-%d" % t["channel"]), channel=t["channel"], voice=t["voice"]) for t in source["tracks"]]
        example = dict(source, **record("/native/mix"), solo_contributions=solos,
                       musical_evidence=[dict(clock_mode=c, path="/native/" + c, passed=True) for c in ("real-time", "controlled-experimental")])
        return dict(examples=[example]), dict(examples=[source])

    def test_mix_and_every_solo_with_both_proofs_are_accepted_without_witnesses(self):
        for ident in COURSE_CLIPS:
            ident = ident
            report, wanted = self.course(ident)
            self.assertEqual(len(audit.check_audio_capture_scope(report, wanted)), 1 + len(wanted["examples"][0]["tracks"]) + 2, ident)

    def test_a_missing_check_is_rejected_for_the_mix_and_for_each_solo(self):
        report, wanted = self.course()
        for record in [report["examples"][0]] + report["examples"][0]["solo_contributions"]:
            bad = copy.deepcopy(report)
            target = bad["examples"][0] if record is report["examples"][0] else next(s for s in bad["examples"][0]["solo_contributions"] if s["channel"] == record["channel"])
            del target["course_before_after"]
            with self.assertRaisesRegex(ValueError, "before/after"):audit.check_audio_capture_scope(bad, wanted)

    def test_a_missing_proof_or_phase_in_the_row_is_rejected(self):
        report, wanted = self.course()
        for part in self.PARTS:
            bad = copy.deepcopy(report)
            del bad["examples"][0]["course_before_after"][part]
            with self.assertRaisesRegex(ValueError, "before/after"):audit.check_audio_capture_scope(bad, wanted)

    def test_a_failed_or_foreign_row_is_rejected(self):
        report, wanted = self.course()
        for change in (dict(passed=False), dict(kind="manual-audio-MIDI-witness")):
            bad = copy.deepcopy(report)
            bad["examples"][0]["course_before_after"].update(change)
            with self.assertRaisesRegex(ValueError, "before/after"):audit.check_audio_capture_scope(bad, wanted)

    def test_a_midi_port_rehearsal_row_is_rejected(self):
        report, wanted = self.course()
        report["examples"][0]["course_before_after"]["stand_in_port"] = 2
        with self.assertRaisesRegex(ValueError, "rehearsal"):audit.check_audio_capture_scope(report, wanted)

    def test_witness_evidence_may_not_stand_in_for_the_check(self):
        report, wanted = self.course()
        report["examples"][0]["midi_witness"] = dict(passed=True)
        with self.assertRaisesRegex(ValueError, "not witness evidence"):audit.check_audio_capture_scope(report, wanted)


class ScaleLessonPcmScope(unittest.TestCase):
    def scale(self):
        source = next(v for v in authored()["examples"] if v["id"] == "scale-slot-comparison")
        report, wanted = lesson_report(source)
        for solo in report["examples"][0]["solo_contributions"]:
            if solo["voice"] == "Polyperc 1":solo["lesson_pcm"] = dict(kind="relative-scale-pitch-interiors", passed=True)
        return report, wanted

    def test_only_the_polyperc_solo_carries_pitch_proof(self):
        report, wanted = self.scale()
        self.assertEqual(len(audit.check_audio_capture_scope(report, wanted)), 5)
        bad = copy.deepcopy(report);next(s for s in bad["examples"][0]["solo_contributions"] if s["voice"] == "Polyperc 1").pop("lesson_pcm")
        with self.assertRaisesRegex(ValueError, "lesson PCM proof"):audit.check_audio_capture_scope(bad, wanted)
        bad = copy.deepcopy(report);bad["examples"][0]["lesson_pcm"] = dict(kind="relative-scale-pitch-interiors", passed=True)
        with self.assertRaisesRegex(ValueError, "Unsupported new audio lesson PCM proof"):audit.check_audio_capture_scope(bad, wanted)


class ScalePhaseRows(unittest.TestCase):
    row = dict(kind="manual-audio-scale-phase", at_step=32, scale_slot=2, root="D", output=dict(binding={}))

    def test_scale_lesson_keeps_the_literal_root_d_phase(self):
        self.assertEqual(audit.audio_scale_phase_rows("scale-slot-comparison", [dict(passed=True), self.row]), [self.row])
        for change in (dict(at_step=16), dict(scale_slot=3), dict(root="E"), dict(output=None)):
            with self.assertRaisesRegex(ValueError, "Root D phase"):
                audit.audio_scale_phase_rows("scale-slot-comparison", [dict(self.row, **change)])

    def test_other_examples_may_not_carry_scale_phase_rows(self):
        self.assertEqual(audit.audio_scale_phase_rows("ghost-note-comparison", [dict(passed=True)]), [])
        for ident in ("ghost-note-comparison", "oilcan-pocket"):
            with self.assertRaisesRegex(ValueError, "scale phase"):audit.audio_scale_phase_rows(ident, [self.row])

    def test_sessions_map_to_their_examples(self):
        report = dict(examples=[dict(id="a", evidence=dict(path="/run/a-mix"), solo_contributions=[dict(evidence=dict(path="/run/a-solo-1"))],
                                     musical_evidence=[dict(path="/run/a-midi")])])
        self.assertEqual(audit.audio_session_examples(report),
                         {Path("/run/a-mix").resolve(): "a", Path("/run/a-solo-1").resolve(): "a", Path("/run/a-midi").resolve(): "a"})


if __name__ == "__main__":
    unittest.main()
