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


class DriverWaitFrameRetentionTests(unittest.TestCase):
    """Harness storage only; native pose acceptance is checked separately."""
    def fixture(self, count=6):
        d=object.__new__(driver.Driver)
        d.clock_mode="controlled-experimental";d.logical_ns=0
        import json,base64,hashlib
        from pathlib import Path
        fixture=Path(__file__).with_name("fixtures")/"mini-retention-native-frames.json"
        raw=fixture.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),"853994bd9ebe16c9bc4931f0bce72d5f0e8d03e1dbd713cd096be2d2b57355ef")
        frames=json.loads(raw)["frames"][:count]
        for row in frames:
            pixels=base64.b64decode(row["state"]["frame"]["pixels_base64"])
            self.assertEqual(hashlib.sha256(pixels).hexdigest(),row["state"]["frame"]["sha256"])
        prefix=frames[0];d.observations=[prefix];d.observed_count=0
        def snapshot():
            row=frames[d.observed_count];d.observed_count+=1;d.observations.append(row);return row["state"]
        d.snapshot=snapshot
        d.elapse=lambda seconds:setattr(d,"logical_ns",d.logical_ns+round(seconds*1e9))
        return d,prefix,frames

    def test_default_keeps_original_first_and_last_pruning(self):
        d,prefix,frames=self.fixture()
        d.wait(lambda state:d.observed_count==len(frames))
        self.assertEqual(d.observations,[prefix,frames[0],frames[-1]])

    def test_opt_in_retains_original_intermediate_revision_objects(self):
        d,prefix,frames=self.fixture();d.wait_observation_limit=6
        d.wait(lambda state:d.observed_count==len(frames))
        self.assertEqual(d.observations,[prefix]+frames)
        self.assertTrue(all(actual is expected for actual,expected in zip(d.observations[1:],frames)))
        self.assertEqual([row["frame_revision"] for row in d.observations[1:]],[row["frame_revision"] for row in frames])
        self.assertGreater(len({row["state"]["frame"]["sha256"] for row in d.observations[1:]}),1)
        from mini_phase_oracle import observed_phases
        from contract.mini_header_animation_ui import atlas
        spec=atlas()["C09"]
        self.assertGreater(len({tuple(observed_phases(row["state"],spec)) for row in d.observations[1:]}),1)

    def test_opt_in_limit_fails_closed_without_unbounded_storage(self):
        d,prefix,frames=self.fixture();d.wait_observation_limit=2
        with self.assertRaisesRegex(AssertionError,"Wait observation retention limit"):
            d.wait(lambda state:d.observed_count==len(frames))
        self.assertEqual(d.observations,[prefix]+frames[:2])

    def test_retention_setting_rejects_unbounded_and_noninteger_limits(self):
        for limit in (0,2049,True,1.5):
            with self.subTest(limit=limit):
                d,_,frames=self.fixture();d.wait_observation_limit=limit
                with self.assertRaisesRegex(ValueError,"bounded"):
                    d.wait(lambda state:d.observed_count==len(frames))


if __name__ == "__main__":
    unittest.main()
