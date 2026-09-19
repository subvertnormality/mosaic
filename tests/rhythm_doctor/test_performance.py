"""RD-02/RD-06 performance gate characterisation outside the current manual.
Contract: docs/rhythm-doctor/PLAN.md, Performance and acceptance.
"""
import unittest
from performance import evaluate


def windows():
    return [dict(profile="norns", temperature="warm" if i % 35 < 30 else "cold",
                 bpm=[40, 60, 120, 180, 240][i % 5], duration_seconds=960 / [40, 60, 120, 180, 240][i % 5] if i < 35 else 45,
                 analysis_tail_ms=1000, peak_incremental_rss_bytes=1000000,
                 ui_response_ms=20, scroll_response_ms=20, capture_start_ms=5,
                 xruns=0, routing_changed=False, transport_start_delayed=False,
                 playback_regressed=False, all_five_lanes_ready=True,
                 source_sha256="a" * 64, device_id="fixture-device",
                 raw_evidence_sha256=str(i).zfill(64)) for i in range(70)]

class PerformanceTests(unittest.TestCase):
    def test_complete_device_evidence(self):
        self.assertTrue(evaluate(windows())["passed"])
    def test_desktop_is_never_hardware_evidence(self):
        rows = windows()
        for row in rows:
            row["profile"] = "desktop"
        self.assertFalse(evaluate(rows)["passed"])
    def test_missing_observation_cannot_default_to_success(self):
        rows = windows()
        del rows[0]["xruns"]
        self.assertFalse(evaluate(rows)["passed"])
    def test_any_audio_or_transport_failure_is_fatal(self):
        for field, value in [("xruns", 1), ("routing_changed", True),
                             ("transport_start_delayed", True),
                             ("playback_regressed", True),
                             ("all_five_lanes_ready", False)]:
            rows = windows()
            rows[0][field] = value
            with self.subTest(field=field):
                self.assertFalse(evaluate(rows)["passed"])
    def test_warm_p95_and_cold_max_are_separate(self):
        rows = windows()
        rows[34]["analysis_tail_ms"] = 5001
        self.assertFalse(evaluate(rows)["passed"])
        rows = windows()
        for row in rows[:3]:
            row["analysis_tail_ms"] = 2001
        self.assertFalse(evaluate(rows)["passed"])
    def test_forty_five_second_limits(self):
        rows = windows()
        for row in rows:
            if row["duration_seconds"] == 45:
                row["analysis_tail_ms"] = 4900
        self.assertTrue(evaluate(rows)["passed"])
        rows[-1]["analysis_tail_ms"] = 10001
        self.assertFalse(evaluate(rows)["passed"])
    def test_missing_repeats_tempo_coverage_and_duplicate_evidence(self):
        self.assertFalse(evaluate(windows()[:34])["passed"])
        rows = windows()
        for row in rows:
            row["bpm"] = 120
        self.assertFalse(evaluate(rows)["passed"])
        rows = windows()
        rows[1]["raw_evidence_sha256"] = rows[0]["raw_evidence_sha256"]
        self.assertFalse(evaluate(rows)["passed"])
    def test_both_duration_classes_need_measurements(self):
        for full in (False, True):
            samples = windows()
            for row in samples:
                row["duration_seconds"] = 45 if full else 960 / row["bpm"]
            self.assertFalse(evaluate(samples)["passed"])

    def test_short_buffer_cannot_claim_all_five_lanes_ready(self):
        rows = windows()
        rows[0]["duration_seconds"] = 23.9  # Four bars at 40 BPM need 24 seconds.
        self.assertFalse(evaluate(rows)["passed"])

    def test_duration_classes_cannot_hide_each_others_tail_failures(self):
        rows = windows()
        # Only one long warm sample: its failure cannot hide under the other 29.
        rows = rows[:35] + rows[-5:]
        rows[0]["duration_seconds"] = 45
        rows[0]["analysis_tail_ms"] = 5001
        self.assertFalse(evaluate(rows)["passed"])

    def test_nonfinite_numbers_are_not_measurements(self):
        for value in [float("nan"), float("inf"), -1, True]:
            rows = windows()
            rows[0]["analysis_tail_ms"] = value
            self.assertFalse(evaluate(rows)["passed"])

if __name__ == "__main__":
    unittest.main()
