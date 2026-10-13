"""The lesson MIDI audit reads each lane's own native emission records.

Regression for the controlled-local raw publication audit (StopIteration in
audit_lesson_midi): the controlled runtime logs emitted MIDI as native kind 11
with logical time, the real-time runtime as kind 3. Only kind 3 was read.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
import manual_audio


def events(path, rows):
    (path / "native").mkdir()
    (path / "native/native-events.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


class LanePackets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.out = Path(self.tmp.name)
        events(self.out, [dict(kind=11, index=1, port=1, bytes=[144, 36, 90], logical_ns=0),
                          dict(kind=3, index=2, port=1, bytes=[144, 37, 90], monotonic_ns=0),
                          dict(kind=11, index=3, port=1, bytes=[128, 36, 90], logical_ns=5)])

    def test_controlled_lane_reads_kind_11_emissions(self):
        rows = manual_audio.native_midi_packets(self.out, 0, 3, "controlled-experimental")
        self.assertEqual([r["index"] for r in rows], [1, 3])

    def test_real_time_lane_reads_kind_3_emissions(self):
        rows = manual_audio.native_midi_packets(self.out, 0, 3, "real-time")
        self.assertEqual([r["index"] for r in rows], [2])


if __name__ == "__main__":
    unittest.main()
