"""Scheduled v2 corpus asset selection stays evidence-backed."""
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

import mido
import yaml

sys.path.insert(0, str(Path(__file__).parents[2] / "tools" / "rhythm_doctor_corpus"))
from build_scheduled import (active_source_events, deterministic_tar,
                             serialized_relative_time, verified_open_hat_asset)


class ScheduledOpenHatAssets(unittest.TestCase):
    def test_frozen_source_archive_contains_open_hat_and_license(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            open_hat = root / "gm" / "HatOpen-Med.wav"
            license_path = root / "COPYING"
            open_hat.parent.mkdir(parents=True)
            open_hat.write_bytes(b"open hat")
            license_path.write_bytes(b"license")
            archive = root / "source.tar"
            deterministic_tar(archive, root, [open_hat, license_path])
            with tarfile.open(archive) as frozen:
                self.assertEqual(frozen.getnames(), ["gm/HatOpen-Med.wav", "COPYING"])
                self.assertEqual(frozen.extractfile("gm/HatOpen-Med.wav").read(), b"open hat")

    def test_serialized_crop_boundary_remains_half_open(self):
        self.assertIsNone(serialized_relative_time(9.6969759996, 0, 9.696976))

    def test_development_midi_keeps_closed_and_open_hats_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            track = "Track00001"
            metadata = root / "slakh" / "babyslakh-meta" / "babyslakh_16k" / track / "metadata.yaml"
            midi_root = root / "slakh" / "babyslakh-selected" / "babyslakh_16k" / track / "MIDI"
            metadata.parent.mkdir(parents=True)
            midi_root.mkdir(parents=True)
            metadata.write_text(yaml.safe_dump({"stems": {
                "S00": {"is_drum": True, "inst_class": "Drums", "plugin_name": "kit"},
                "S01": {"is_drum": False, "inst_class": "Bass"},
            }}), encoding="utf-8")
            drums = mido.MidiFile(ticks_per_beat=480)
            drum_track = mido.MidiTrack(); drums.tracks.append(drum_track)
            for note in (36, 38, 42, 44, 46, 48):
                drum_track.append(mido.Message("note_on", note=note, velocity=90, time=96))
            drums.save(midi_root / "S00.mid")
            bass = mido.MidiFile(ticks_per_beat=480)
            bass_track = mido.MidiTrack(); bass.tracks.append(bass_track)
            bass_track.append(mido.Message("note_on", note=40, velocity=80, time=96))
            bass.save(midi_root / "S01.mid")

            events, _metadata = active_source_events(root, track, 0, 2)
            self.assertEqual({lane: len(items) for lane, items in events.items()}, {
                "BD": 1, "SD": 1, "CHH": 1, "OHH": 1, "BASS": 1,
            })

    def test_uses_the_existing_open_hat_asset(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            asset = root / "hydrogen" / "gm" / "HatOpen-Med.wav"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"verified fixture")
            self.assertEqual(
                verified_open_hat_asset(root, "hydrogen/gm"),
                "hydrogen/gm/HatOpen-Med.wav",
            )

    def test_missing_open_hat_fails_without_guessing_a_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "hydrogen" / "gm").mkdir(parents=True)
            with self.assertRaisesRegex(FileNotFoundError, "Refusing to invent a path"):
                verified_open_hat_asset(root, "hydrogen/gm")

    def test_ambiguous_open_hat_assets_fail_without_selecting_one(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            directory = root / "hydrogen" / "gm"
            directory.mkdir(parents=True)
            (directory / "HatOpen-Med.wav").write_bytes(b"first")
            (directory / "OpenHat-Long.wav").write_bytes(b"second")
            with self.assertRaisesRegex(FileNotFoundError, "exactly one verified"):
                verified_open_hat_asset(root, "hydrogen/gm")


if __name__ == "__main__":
    unittest.main()
