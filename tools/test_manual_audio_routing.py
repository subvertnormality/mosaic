"""Public MIDI-routing regression for the manual audio fixture.

route_track drives the Device screen (C05) through E2/E3/K3. The screen lists
Device, MIDI channel and MIDI port in the order Mosaic declares them, so the
fixture must set each row to the value that row names.
"""
import os
import re
import sys
import unittest
from pathlib import Path

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
TOOLS = Path(os.environ.get("MOSAIC_AUDIO_TOOLS", REPO / "tools"))
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(REPO / "tools"))
import manual_audio


class DeviceScreen:
    """C05 as Mosaic lays it out: rows in channel_edit_parameters.device_fields
    order, E2 selects a row, E3 scrolls its clamped value, K3 applies. The
    port list excludes Norns2sinfonion (m_midi.get_midi_outs), leaving two."""

    def __init__(self, ports=2):
        source = (REPO / "lib/pages/channel_edit_page/channel_edit_parameters.lua").read_text()
        block = source.split("device_fields = {", 1)[1].split("\n}", 1)[0]
        self.rows = re.findall(r'label = "([^"]+)"', block)
        self.sizes = {"Device": 8, "MIDI channel": 16, "MIDI port": ports}
        self.names = {"Device": "{}", "MIDI channel": "CC{}", "MIDI port": "OUT {}"}
        self.row = 0
        self.draft = {label: 0 for label in self.rows}
        self.applied = None

    def enc(self, number, delta):
        if number == 2:
            self.row = max(0, min(len(self.rows) - 1, self.row + delta))
        elif number == 3:
            label = self.rows[self.row]
            self.draft[label] = max(0, min(self.sizes[label] - 1, self.draft[label] + delta))

    def shown(self, label):
        return self.names[label].format(self.draft[label] + 1)


class ScreenUi:
    def __init__(self, screen):
        self.screen = screen

    def channel_editor(self):
        pass

    def select_channel(self, channel):
        pass

    def channel_page(self, page, channel=None):
        pass

    def press_key(self, number):
        if number == 3:
            self.screen.applied = {label: self.screen.shown(label) for label in ("MIDI channel", "MIDI port")}

    def expect_selected_field(self, layout, label=None, value=None, art=False):
        selected = self.screen.rows[self.screen.row]
        if (layout, label, value) != ("detail", selected, self.screen.shown(selected)):
            raise AssertionError(("selected field", layout, label, value, selected, self.screen.shown(selected)))


class ManualAudioMidiRouting(unittest.TestCase):
    # README.md#midi-config: a channel sends on its chosen MIDI channel and port.
    def route(self, channel, port):
        screen = DeviceScreen()
        driver = type("Driver", (), {})()
        driver.ui = ScreenUi(screen)
        driver.enc = screen.enc
        manual_audio.route_track(driver, {"voice": "unused"}, channel, midi=True, port=port)
        return screen.applied

    def test_witness_channel_15_sends_on_midi_channel_15_of_port_1(self):
        self.assertEqual(self.route(15, 1), {"MIDI channel": "CC15", "MIDI port": "OUT 1"})

    def test_equal_channel_and_port_route_unchanged(self):
        self.assertEqual(self.route(2, 2), {"MIDI channel": "CC2", "MIDI port": "OUT 2"})


if __name__ == "__main__":
    unittest.main()
