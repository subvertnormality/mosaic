import unittest
from unittest.mock import patch

import driver


class DriverWaitTests(unittest.TestCase):
    def test_controlled_wait_can_finish_after_old_wall_cap_but_before_logical_deadline(self):
        clock = [0.0]
        d = object.__new__(driver.Driver)
        d.clock_mode = "controlled-experimental"
        d.logical_ns = 0
        d.observations = []
        d.snapshot = lambda: {"ready": d.logical_ns >= 38_000_000_000}

        def elapse(seconds):
            ns = round(seconds * 1e9)
            d.logical_ns += ns
            # Model slow observe/advance round trips under a loaded host.
            clock[0] += seconds * 5

        d.elapse = elapse
        with patch.object(driver.time, "monotonic", side_effect=lambda: clock[0]):
            self.assertTrue(d.wait(lambda state: state["ready"], timeout=40)["ready"])


    def test_controlled_wait_keeps_logical_deadline_when_host_is_ten_times_slower(self):
        clock = [0.0]
        d = object.__new__(driver.Driver)
        d.clock_mode = "controlled-experimental"
        d.logical_ns = 0
        d.observations = []
        d.snapshot = lambda: {"ready": d.logical_ns >= 21_400_000_000}

        def elapse(seconds):
            d.logical_ns += round(seconds * 1e9)
            clock[0] += seconds * 10

        d.elapse = elapse
        with patch.object(driver.time, "monotonic", side_effect=lambda: clock[0]):
            self.assertTrue(d.wait(lambda state: state["ready"], timeout=26)["ready"])
        self.assertLessEqual(d.logical_ns, 26_000_000_000)

    def test_controlled_wait_still_rejects_missing_output_at_logical_deadline(self):
        clock = [0.0]
        d = object.__new__(driver.Driver)
        d.clock_mode = "controlled-experimental"
        d.logical_ns = 0
        d.observations = []
        d.snapshot = lambda: {"ready": False}

        def elapse(seconds):
            d.logical_ns += round(seconds * 1e9)
            clock[0] += seconds * 10

        d.elapse = elapse
        with patch.object(driver.time, "monotonic", side_effect=lambda: clock[0]):
            with self.assertRaisesRegex(AssertionError, "Required observable output"):
                d.wait(lambda state: state["ready"], timeout=26)
        self.assertEqual(d.logical_ns, 26_000_000_000)


if __name__ == "__main__":
    unittest.main()


class DriverSnapshotRetentionTests(unittest.TestCase):
    def test_recorded_snapshots_leave_the_cyclic_collector(self):
        # Every observation keeps the whole MIDI capture for the evidence
        # record, so a long real-time case holds millions of Python objects.
        # A full collection over them paused the harness for 1.1 s between a
        # step's press and release in CI (M-PAT-003, length 57), turning a
        # tap into a long press. Recorded snapshots are retained for the run
        # anyway, so they are frozen out of later collections.
        import gc
        d = object.__new__(driver.Driver)
        d.observations = []
        state = {"midi": [{"index": i, "bytes": [144, 60, 127]} for i in range(1000)]}
        d.runtime = type("Runtime", (), {"observe": lambda self: {"state": state}})()
        gc.unfreeze()
        try:
            self.assertIs(d.snapshot(), state)
            self.assertGreater(gc.get_freeze_count(), 1000)
            self.assertEqual(d.observations, [{"state": state}])
        finally:
            gc.unfreeze()
