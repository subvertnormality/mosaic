"""RD-02 lane/stratum quality gates; characterisation outside README."""
import unittest
from quality_report import evaluate

LANES = ("BD", "SD", "CHH", "OHH", "BASS")
STRATA = ("isolated", "sparse", "full_mix")

def rows():
    return [dict(lane=lane, stratum=stratum, onset_tp=80, onset_fp=10, onset_fn=10,
                 cell_tp=90, cell_fp=5, cell_fn=5, negative_control_painted_events=0,
                 negative_control_clips=5, velocity_absolute_errors=[8, 12, 16],
                 velocity_monotonic=True) for lane in LANES for stratum in STRATA]

class QualityReportTests(unittest.TestCase):
    def test_schema_v2_requires_every_active_lane_and_names_scope(self):
        samples = rows()
        result = evaluate(samples)
        self.assertTrue(result['passed'])
        self.assertEqual(result['schema_version'], 2)
        self.assertEqual(result['required_lanes'], ['BD', 'SD', 'CHH', 'OHH', 'BASS'])
        for lane in LANES:
            result = evaluate([row for row in samples if row['lane'] != lane])
            self.assertFalse(result['passed'])
        samples[-1]['onset_tp'] = 0
        self.assertFalse(evaluate(samples)['passed'])

    def test_legacy_hat_and_tom_labels_are_rejected(self):
        samples = rows()
        samples[0]['lane'] = 'HH'
        self.assertFalse(evaluate(samples)['passed'])
        samples = rows()
        samples[0]['lane'] = 'TOM'
        self.assertFalse(evaluate(samples)['passed'])

    def test_unknown_profile_fails_closed(self):
        self.assertFalse(evaluate(rows(), profile='bd_only')['passed'])

    def test_all_fifteen_domains_must_pass(self):
        self.assertTrue(evaluate(rows())["passed"])
        samples = rows()
        samples[-1]["onset_tp"] = 0
        self.assertFalse(evaluate(samples)["passed"])
    def test_missing_domain_or_duplicate_cannot_pass(self):
        self.assertFalse(evaluate(rows()[:-1])["passed"])
        self.assertFalse(evaluate(rows() + [rows()[0]])["passed"])
    def test_absent_controls_missing_velocity_or_nonmonotonic_fail(self):
        for field, value in [("negative_control_clips", 0),
                             ("negative_control_painted_events", 1),
                             ("velocity_absolute_errors", []),
                             ("velocity_monotonic", False)]:
            samples = rows()
            for sample in samples[:3]:
                sample[field] = value
            self.assertFalse(evaluate(samples)["passed"])
    def test_no_positive_events_cannot_earn_perfect_f1(self):
        samples = rows()
        for field in ("onset_tp", "onset_fp", "onset_fn", "cell_tp", "cell_fp", "cell_fn"):
            samples[0][field] = 0
        self.assertFalse(evaluate(samples)["passed"])
    def test_invalid_numeric_evidence_is_rejected(self):
        for value in [-1, True, float("nan"), 1.5]:
            samples = rows()
            samples[0]["onset_tp"] = value
            self.assertFalse(evaluate(samples)["passed"])
        samples = rows()
        samples[0]["velocity_absolute_errors"] = [float("nan")]
        self.assertFalse(evaluate(samples)["passed"])

if __name__ == "__main__":
    unittest.main()
