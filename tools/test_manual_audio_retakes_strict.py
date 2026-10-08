"""Strict boundaries and evidence retention for retake orchestration."""
import json
import tempfile
import unittest
import subprocess
from unittest.mock import patch
from pathlib import Path
import manual_audio

def timing(kind, field="monotonic_ns"):
    return AssertionError((kind,{field:1},{"step":28,"length":0.5}))

class StrictRetakes(unittest.TestCase):
    def test_only_real_time_onset_and_gate_misses_are_eligible(self):
        self.assertTrue(manual_audio.host_timing_miss(timing("Musical onset"),"real-time"))
        self.assertTrue(manual_audio.host_timing_miss(timing("Musical gate"),"real-time"))
        self.assertFalse(manual_audio.host_timing_miss(timing("Musical gate","logical_ns"),"real-time"))
        self.assertFalse(manual_audio.host_timing_miss(AssertionError(("Literal musical output",[],[])),"real-time"))
        self.assertFalse(manual_audio.host_timing_miss(AssertionError("Unexpected or missing musical packets"),"real-time"))
        self.assertFalse(manual_audio.host_timing_miss(ValueError("Native capture integrity"),"real-time"))

    def test_controlled_packet_with_both_timestamps_is_never_eligible(self):
        packet={"logical_ns":10,"monotonic_ns":20,"bytes":[144,60,100],"index":1}
        error=AssertionError(("Musical gate",packet,{"step":28,"length":0.5}))
        self.assertFalse(manual_audio.host_timing_miss(error,"controlled-experimental"))
        with tempfile.TemporaryDirectory() as directory:
            run=Path(directory);calls=[]
            def take(out):
                calls.append(out)
                raise error
            with self.assertRaises(AssertionError):
                manual_audio.take_with_retakes(run,"controlled",take,"controlled-experimental")
            self.assertEqual(len(calls),1)
            receipt=json.loads((calls[0]/"retake-receipt.json").read_text())
            self.assertFalse(receipt["retake_eligible"])
            self.assertEqual(receipt["clock_mode"],"controlled-experimental")

    def test_non_timing_failures_keep_receipt_and_never_start_another_take(self):
        errors=[AssertionError(("Literal musical output",[],[])),
                AssertionError("Unexpected or missing musical packets"),
                ValueError("Source integrity changed"),
                RuntimeError("worker failed"),
                timing("Musical gate","logical_ns")]
        for error in errors:
            with self.subTest(error=error), tempfile.TemporaryDirectory() as directory:
                run=Path(directory);calls=[]
                def take(out):
                    calls.append(out)
                    (out/"native-evidence.bin").write_bytes(b"preserve")
                    if isinstance(error, AssertionError) and error.args and isinstance(error.args[0], tuple) and len(error.args[0]) == 3:
                        kind, packet, row = error.args[0]
                        (out/"lesson-failure.json").write_text(json.dumps(dict(category="timing",clock_mode="real-time",kind=kind,packet=packet,row=row)))
                    raise error
                with self.assertRaises(type(error)):
                    manual_audio.take_with_retakes(run,"lane",take,"real-time")
                self.assertEqual(len(calls),1)
                self.assertEqual(sorted(p.name for p in run.iterdir()),["lane"])
                folder=run/"lane"
                self.assertEqual((folder/"native-evidence.bin").read_bytes(),b"preserve")
                receipt=json.loads((folder/"retake-receipt.json").read_text())
                self.assertFalse(receipt["retake_eligible"])
                self.assertEqual(receipt["attempt"],1)

    def test_worker_handoff_retries_only_serialized_realtime_timing_miss(self):
        for failure,lane,expected_calls in (
            (dict(category="timing",kind="Musical onset",clock_mode="real-time",packet={"monotonic_ns":1},row={"step":28}),"real-time",2),
            (dict(category="exception",clock_mode="real-time",exception_type="ValueError",message="Native capture integrity"),"real-time",1),
            (dict(category="exception",clock_mode="controlled-experimental",exception_type="AssertionError",message="controlled timing oracle"),"controlled-experimental",1),
        ):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                run=Path(directory);calls=[]
                def command(_run,_ident,out,_app,_options,_lane):
                    return [str(out)]
                def fake_run(args,**kwargs):
                    out=Path(args[0]);calls.append(out)
                    if len(calls)==1 and failure["category"]=="timing":
                        (out/"lesson-failure.json").write_text(json.dumps(failure))
                        return subprocess.CompletedProcess(args,1)
                    if len(calls)==1:
                        (out/"lesson-failure.json").write_text(json.dumps(failure))
                        return subprocess.CompletedProcess(args,1)
                    (out/"lesson-result.json").write_text(json.dumps({"passed":True}))
                    return subprocess.CompletedProcess(args,0)
                with patch.object(manual_audio,"midi_worker_command",side_effect=command), \
                     patch.object(manual_audio.subprocess,"run",side_effect=fake_run):
                    options=object()
                    if lane!="real-time":
                        with self.assertRaises(RuntimeError):
                            manual_audio.run_midi_lane(run,"lesson",None,options,lane,{})
                    elif expected_calls==1:
                        with self.assertRaises(RuntimeError):
                            manual_audio.run_midi_lane(run,"lesson",None,options,"real-time",{})
                    else:
                        result=manual_audio.run_midi_lane(run,"lesson",None,options,lane,{})
                        self.assertTrue(result["passed"])
                        self.assertEqual(len(result["retakes"]),1)
                        receipt=result["retakes"][0]
                        self.assertEqual(receipt["receipt_sha256"],manual_audio.digest(Path(receipt["path"])/"retake-receipt.json"))
                        self.assertEqual(receipt["worker_failure"]["clock_mode"],"real-time")
                        self.assertEqual(receipt["worker_failure_sha256"],manual_audio.digest(Path(receipt["path"])/"lesson-failure.json"))
                self.assertEqual(len(calls),expected_calls)
                self.assertTrue((calls[0]/"retake-receipt.json").is_file())

    def test_three_timing_misses_preserve_each_take_and_stop_at_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            run=Path(directory);calls=[]
            def take(out):
                calls.append(out)
                (out/"native-evidence.bin").write_bytes(("take-%d"%len(calls)).encode())
                error=timing("Musical gate")
                kind,packet,row=error.args[0]
                (out/"lesson-failure.json").write_text(json.dumps(dict(category="timing",clock_mode="real-time",kind=kind,packet=packet,row=row)))
                raise error
            with self.assertRaises(AssertionError):
                manual_audio.take_with_retakes(run,"lane",take,"real-time")
            self.assertEqual([p.name for p in calls],["lane","lane-retake-1","lane-retake-2"])
            self.assertEqual(sorted(p.name for p in run.iterdir()),
                             ["lane","lane-retake-1","lane-retake-2"])
            for attempt,folder in enumerate(calls,1):
                self.assertEqual((folder/"native-evidence.bin").read_bytes(),("take-%d"%attempt).encode())
                receipt=json.loads((folder/"retake-receipt.json").read_text())
                self.assertTrue(receipt["retake_eligible"])
                self.assertEqual(receipt["attempt"],attempt)
                self.assertEqual(receipt["max_attempts"],3)

if __name__=="__main__":unittest.main()
