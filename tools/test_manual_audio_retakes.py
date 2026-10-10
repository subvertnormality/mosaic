"""Real-time audio takes may be retaken only for a host-timing miss.

Regression for CI run 37483142544: a swing-comparison solo take missed the 10 ms
real-time gate tolerance on a shared runner, although the same example's controlled
MIDI lane passed and earlier takes passed. A miss is a bad take, not a different
result: the published take must still pass the unchanged strict check.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
import manual_audio


def miss(kind):
    return AssertionError((kind, {"monotonic_ns": 1}, {"step": 28, "length": 0.5}))


class Retakes(unittest.TestCase):
    def run_takes(self, outcomes):
        calls = []
        def take(out):
            calls.append(out)
            outcome = outcomes[len(calls) - 1]
            if isinstance(outcome, Exception):
                if isinstance(outcome, AssertionError) and outcome.args and isinstance(outcome.args[0], tuple) and len(outcome.args[0]) == 3:
                    kind, packet, row = outcome.args[0]
                    (out/"lesson-failure.json").write_text(__import__("json").dumps(dict(category="timing",clock_mode="real-time",kind=kind,packet=packet,row=row)))
                raise outcome
            return outcome
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            try:
                result, retakes = manual_audio.take_with_retakes(run, "swing-solo-2", take, "real-time")
            finally:
                folders = sorted(p.name for p in run.iterdir())
        return result, retakes, calls, folders

    def test_a_timing_miss_is_retaken_and_the_failed_take_is_kept(self):
        result, retakes, calls, folders = self.run_takes([miss("Musical gate"), {"take": 2}])
        self.assertEqual(result, {"take": 2})
        self.assertEqual(folders, ["swing-solo-2", "swing-solo-2-retake-1"])
        self.assertEqual(calls[1].name, "swing-solo-2-retake-1")
        self.assertEqual([Path(r["path"]).name for r in retakes], ["swing-solo-2"])
        self.assertIn("Musical gate", retakes[0]["error"])

    def test_an_onset_miss_is_also_a_timing_miss(self):
        result, retakes, _, _ = self.run_takes([miss("Musical onset"), {"take": 2}])
        self.assertEqual(len(retakes), 1)

    def test_a_wrong_note_or_other_failure_is_never_retaken(self):
        for error in (AssertionError(("Literal musical output", [], [])),
                      AssertionError("Unexpected or missing musical packets"),
                      ValueError("Native capture integrity")):
            with self.subTest(error=error), self.assertRaises(type(error)):
                self.run_takes([error, {"take": 2}])

    def test_three_timing_misses_fail(self):
        with self.assertRaises(AssertionError):
            self.run_takes([miss("Musical gate")] * 3)


if __name__ == "__main__":
    unittest.main()
