"""Portable setup regression for literal-pitch manual audio examples."""
import os
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
TOOLS = Path(os.environ.get("MOSAIC_AUDIO_TOOLS", REPO / "tools"))
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(REPO / "tools"))
import manual_audio

class PublicUi:
    def __init__(self):
        self.option_sets = []
    def set_mosaic_options(self, options):
        self.option_sets.append(list(options))
    def __getattr__(self, name):
        if name == "hold_step":
            @contextmanager
            def hold_step(*args):
                yield
            return hold_step
        return lambda *args, **kwargs: None

class ManualAudioConfiguration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = yaml.safe_load((REPO / "manual/audio-scenes.yaml").read_text())
        cls.examples = {value["id"]: value for value in data["examples"]}

    def configure_without_unrelated_ui(self, example):
        ui = PublicUi()
        driver = type("Driver", (), {})()
        driver.ui = ui
        driver.results = []
        driver.enc = lambda *args: None
        with patch.object(manual_audio, "set_tempo"), \
             patch.object(manual_audio, "route_track"), \
             patch.object(manual_audio, "set_mask_field"):
            manual_audio.configure(driver, example, example["tracks"], midi_only=True)
        return ui

    def test_absolute_pitch_example_publicly_disables_scale_snap(self):
        ui = self.configure_without_unrelated_ui(self.examples["ghost-note-comparison"])
        self.assertEqual(ui.option_sets, [[("Snap note masks to scale", False)]])

    def test_relative_scale_example_keeps_its_existing_scale_setup(self):
        ui = self.configure_without_unrelated_ui(self.examples["scale-slot-comparison"])
        self.assertEqual(ui.option_sets, [])

if __name__ == "__main__":
    unittest.main()
