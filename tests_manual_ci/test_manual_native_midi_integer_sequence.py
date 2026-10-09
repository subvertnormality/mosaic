"""Strict JSON integer guards for native MIDI index/sequence fields."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

OVERLAY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OVERLAY / "tools"))
import manual_fresh_target_midi
from manual_fresh_target_midi import FreshMidiError, _native
if Path(manual_fresh_target_midi.__file__).resolve() != (OVERLAY / "tools" / "manual_fresh_target_midi.py").resolve():
    raise RuntimeError("strict integer regression did not import the isolated overlay producer")


def fixture(testcase, index_override=None, sequence_override=None):
    packets = []
    for n in (1, 2, 3):
        packets.append({
            "kind": 3,
            "index": n,
            "sequence": n,
            "monotonic_ns": n * 100,
            "port": 1,
            "bytes": [144, 59 + n, 90],
            "logical_ns": n * 100,
            "device_id": "fixture-device",
            "port_name": "fixture-port",
        })
    if index_override is not None:
        packets[0]["index"] = index_override
    if sequence_override is not None:
        packets[0]["sequence"] = sequence_override
    temporary = tempfile.TemporaryDirectory()
    testcase.addCleanup(temporary.cleanup)
    root = Path(temporary.name)
    (root / "native").mkdir()
    (root / "results.json").write_text("[]")
    (root / "native/identity.json").write_text(json.dumps({"session_id": "fixture-session"}))
    (root / "native/native-events.jsonl").write_text("".join(json.dumps(p) + "\n" for p in packets))
    observation = {
        "session_id": "fixture-session",
        "state": {
            "midi_capture": {"dropped": 0, "count": 3},
            "midi_count": 3,
            "midi": [dict(p) for p in packets],
        },
    }
    (root / "observations.json").write_text(json.dumps([observation]))
    return root


class NativeMidiIntegerSequenceTests(unittest.TestCase):
    def test_integer_one_based_triplet_is_valid(self):
        root = fixture(self)
        self.assertEqual(len(_native(root, {}, False)[4]), 3)

    def test_boolean_index_is_invalid(self):
        root = fixture(self, index_override=True)
        with self.assertRaises(FreshMidiError):
            _native(root, {}, False)

    def test_boolean_sequence_is_invalid(self):
        root = fixture(self, sequence_override=True)
        with self.assertRaises(FreshMidiError):
            _native(root, {}, False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
