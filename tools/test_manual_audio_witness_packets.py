"""Witness MIDI packets may carry several messages; each is checked literally.

Regression for rehearsal ghost-witness-routing-20261004/update2/rehearsal-1:
the scale-slot mix routes both witnesses to port 1, and simultaneous onsets
arrive as one 6-byte packet such as [159, 48, 60, 158, 60, 80].
"""
import os
import sys
import unittest
from pathlib import Path

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
import manual_audio

STEP = int(1e9 / 6)


def packet(index, step, data):
    return dict(index=index, port=1, logical_ns=step * STEP, monotonic_ns=step * STEP, bytes=data)


EXPECTED = [dict(port=1, status=158, note=60, velocity=80, step=0, length=1),
            dict(port=1, status=159, note=48, velocity=60, step=0, length=2)]


class WitnessPackets(unittest.TestCase):
    def test_simultaneous_onsets_in_one_packet_are_both_verified(self):
        packets = [packet(1, 0, [159, 48, 60, 158, 60, 80]),
                   packet(2, 1, [142, 60, 80]),
                   packet(3, 2, [143, 48, 60])]
        result = manual_audio.verify_midi_packets(packets, EXPECTED, 0, "controlled-experimental")
        self.assertEqual(result["onsets"], 2)

    def test_a_wrong_note_inside_a_combined_packet_is_still_rejected(self):
        packets = [packet(1, 0, [159, 47, 60, 158, 60, 80]),
                   packet(2, 1, [142, 60, 80]),
                   packet(3, 2, [143, 47, 60])]
        with self.assertRaisesRegex(AssertionError, "Literal musical output"):
            manual_audio.verify_midi_packets(packets, EXPECTED, 0, "controlled-experimental")

    def test_stray_data_bytes_are_rejected(self):
        packets = [packet(1, 0, [159, 48, 60, 60, 80])]
        with self.assertRaisesRegex(AssertionError, "MIDI packet"):
            manual_audio.verify_midi_packets(packets, EXPECTED, 0, "controlled-experimental")


if __name__ == "__main__":
    unittest.main()


class WitnessOrigin(unittest.TestCase):
    """Regression for full build 20261006-02: the song-sections Polyperc solo enters on step 18,
    but the capture took its first heard onset as step 0, so every onset read 3 s late."""

    def example(self, ident):
        import yaml
        source = yaml.safe_load((REPO / "manual/audio-scenes.yaml").read_text())
        return next(v for v in manual_audio.validate(source)["examples"] if v["id"] == ident)

    def take(self, example, tracks, start_ns):
        score = manual_audio.mapped_score(example, tracks, witness=True)
        packets, index = [], 0
        for row in sorted(score, key=lambda v: v["step"]):
            on = start_ns + row["step"] * 1e9 / 6
            index += 1; packets.append(dict(index=index, port=row["port"], monotonic_ns=on, bytes=[row["status"], row["note"], row["velocity"]]))
            index += 1; packets.append(dict(index=index, port=row["port"], monotonic_ns=on + row["length"] * 1e9 / 6, bytes=[row["status"] - 16, row["note"], row["velocity"]]))
        packets.sort(key=lambda p: (p["monotonic_ns"], p["index"]))
        return score, packets

    def test_a_part_entering_after_step_zero_is_timed_from_play_start(self):
        example = self.example("song-sections")
        tracks = [t for t in example["tracks"] if t["channel"] == 2]
        score, packets = self.take(example, tracks, start_ns=5e9)
        first = next(p["monotonic_ns"] for p in packets if p["bytes"][0] >= 144)
        self.assertEqual(min(v["step"] for v in score), 18)
        self.assertEqual(manual_audio.witness_origin(example, tracks, first), 5e9)
        self.assertTrue(manual_audio.verify_witness_packets(example, tracks, packets, 5e9)["passed"])
        with self.assertRaisesRegex(AssertionError, "Musical onset"):
            manual_audio.verify_witness_packets(example, tracks, packets, first)

    def test_a_part_starting_on_step_zero_keeps_its_first_onset_origin(self):
        example = self.example("song-sections")
        tracks = [t for t in example["tracks"] if t["channel"] != 2][:1]
        score, packets = self.take(example, tracks, start_ns=5e9)
        self.assertEqual(min(v["step"] for v in score), 0)
        self.assertEqual(manual_audio.witness_origin(example, tracks, 5e9), 5e9)
