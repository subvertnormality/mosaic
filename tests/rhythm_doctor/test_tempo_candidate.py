"""RD-02 candidate logic unit acceptance; known beat tables, no aubio oracle."""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUILD = ROOT / "tools" / "rhythm_doctor_tempo" / "build_local_aubio.sh"
DEFAULT_AUBIO = "/tmp/rd-tempo-aubio-0.4.9/extracted"


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        system_aubio = os.environ.get("RD_TEMPO_SYSTEM_AUBIO") == "1"
        if system_aubio:
            subprocess.run(["pkg-config", "--exists", "aubio"], check=True)
        elif not pathlib.Path(DEFAULT_AUBIO, "usr/include/aubio/aubio.h").exists():
            raise unittest.SkipTest("pinned local aubio extraction unavailable")
        cls.temp = tempfile.TemporaryDirectory(prefix="rd-tempo-candidate-")
        cls.binary = pathlib.Path(cls.temp.name) / "rd-tempo"
        environment = os.environ.copy()
        if not system_aubio:
            environment["RD_TEMPO_AUBIO_ROOT"] = os.environ.get("RD_TEMPO_AUBIO_ROOT", DEFAULT_AUBIO)
        subprocess.run(["sh", str(BUILD), str(cls.binary)], cwd=ROOT, env=environment, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def candidate(self, beats, rate=48000, frames=None):
        if frames is None: frames = beats[-1][0] + rate * 8
        with tempfile.NamedTemporaryFile(mode="w", suffix=".beats", delete=False) as table:
            for frame, bpm, confidence in beats:
                table.write(f"{frame} {bpm} {confidence}\n")
        try:
            payload = subprocess.check_output([str(self.binary), "--candidate-beats", table.name,
                                               str(rate), str(frames)], text=True)
        finally:
            os.unlink(table.name)
        return json.loads(payload)["candidate"]

    @staticmethod
    def regular(bpm, count=24, rate=48000, start=0):
        period = rate * 60 / bpm
        return [(round(start + index * period), bpm, 1.0) for index in range(count)]

    def test_regular_supported_envelope_reports_unresolvable_half_time(self):
        for bpm in (40, 60, 120, 180, 240):
            with self.subTest(bpm=bpm):
                candidate = self.candidate(self.regular(bpm))
                expected = "READY" if bpm < 80 else "UNCERTAIN"
                self.assertEqual(candidate["status"], expected)
                if bpm >= 80:
                    self.assertEqual(candidate["reason"], "half-double-ambiguous")
                self.assertGreaterEqual(candidate["beats_used"], 8)
                self.assertGreater(candidate["region_end_frame"], candidate["origin_frame"])

    def test_fifteen_buffered_intervals_are_not_four_bars_but_sixteen_are(self):
        beats = self.regular(120, count=10)
        period = 48000 * 60 // 120
        self.assertEqual(self.candidate(beats, frames=15 * period)["reason"], "no-complete-four-bars")
        complete = self.candidate(beats, frames=16 * period)
        self.assertEqual((complete["status"], complete["reason"]),
                         ("UNCERTAIN", "half-double-ambiguous"))

    def test_initial_transient_can_be_skipped_for_a_later_stable_span(self):
        transient = [(0, 90, 1.0), (32000, 98, 1.0), (62000, 104, 1.0)]
        stable = self.regular(120, count=24, start=100000)
        candidate = self.candidate(transient + stable, frames=stable[-1][0] + 48000 * 8)
        self.assertEqual((candidate["status"], candidate["reason"]),
                         ("UNCERTAIN", "half-double-ambiguous"))
        self.assertGreaterEqual(candidate["origin_frame"], 100000)

    def test_late_tempo_drift_invalidates_the_whole_retained_span(self):
        beats, frame = [], 0.0
        for index in range(32):
            bpm = 120 + index * 2
            beats.append((round(frame), bpm, 1.0))
            frame += 48000 * 60 / bpm
        candidate = self.candidate(beats, frames=round(frame + 48000 * 8))
        self.assertEqual(candidate["status"], "UNCERTAIN")
        self.assertEqual(candidate["reason"], "unstable-estimates")

    def test_half_double_table_remains_visible_candidate_data(self):
        beats = self.regular(120, count=24)
        candidate = self.candidate(beats)
        self.assertEqual((candidate["half_bpm"], candidate["double_bpm"]), (60, 240))

    def test_literal_syncopation_keeps_beat_grid_support_separate_from_offbeats(self):
        rate, bpm = 48000, 120
        period = rate * 60 / bpm
        beats = []
        for index in range(40):
            for fraction in (0, .25, .5, .75):
                beats.append((round((index + fraction) * period), bpm, 1.0))
        candidate = self.candidate(beats, frames=round(40 * period))
        self.assertEqual((candidate["status"], candidate["reason"]),
                         ("UNCERTAIN", "half-double-ambiguous"))
        self.assertGreaterEqual(candidate["grid_support"], 8)
        self.assertGreater(candidate["offbeat_residual"], 0)
        self.assertLessEqual(candidate["phase_error_ms"], 50)

    def test_literal_half_time_pulse_is_tempo_ambiguous_not_ready(self):
        candidate = self.candidate(self.regular(120, count=24))
        self.assertEqual((candidate["status"], candidate["reason"]),
                         ("UNCERTAIN", "half-double-ambiguous"))


if __name__ == "__main__":
    unittest.main()
