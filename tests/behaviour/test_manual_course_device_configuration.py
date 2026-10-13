import base64
import hashlib
import json
import os
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch


def repository_root():
    if os.environ.get('MOSAIC_ROOT'):
        return Path(os.environ['MOSAIC_ROOT']).resolve()
    for candidate in Path(__file__).resolve().parents:
        if (candidate / 'tests' / 'behaviour' / 'frame_oracle.py').is_file():
            return candidate
    candidate = Path.cwd().resolve()
    if (candidate / 'tests' / 'behaviour' / 'frame_oracle.py').is_file():
        return candidate
    raise RuntimeError('set MOSAIC_ROOT to the Mosaic checkout')


ROOT = repository_root()
CASE_SOURCE = Path(os.environ.get('MOSAIC_CASES_SOURCE', ROOT / 'tools')).resolve()
sys.path.insert(0, str(ROOT / 'tests' / 'behaviour'))
sys.path.insert(0, str(CASE_SOURCE))
import frame_oracle
from manual_course_cases import device_configuration_matches
REAL_RENDER = frame_oracle.render


def deterministic_text_raster(commands):
    pixels = bytearray(128 * 64 * 4)
    for command in commands:
        x0, y0, level, text = command[:4]
        label = str(text)
        if x0 is None:
            x0 = 127 - len(label) * 4
        elif isinstance(x0, tuple):
            x0 = x0[1] - len(label) * 4
        for char in label:
            code = ord(char)
            if char != ' ':
                for row in range(7):
                    for col in range(4):
                        if (code >> ((row + col) % 7)) & 1:
                            x, y = x0 + col, y0 - 6 + row
                            if 0 <= x < 128 and 0 <= y < 64:
                                i = (y * 128 + x) * 4
                                pixels[i:i+4] = bytes((level, level, level, 255))
            x0 += 4
    return bytes(pixels)


def fake_text_width(text, size=8, antialias=None):
    return len(str(text)) * 4


def fake_fit(text, width):
    return str(text)[:max(0, width // 4)]


def detail_snapshot(device='CC Device', channel='CC2', port='OUT 2', selected='Device'):
    values = [('Device', device, 27), ('MIDI channel', channel, 36), ('MIDI port', port, 45)]
    commands = []
    for label, value, y in values:
        active = label == selected
        if active:
            commands.append((0, y, 15, '>'))
        commands.append((7, y, 15 if active else 6, label))
        commands.append(((None, 126), y, 15 if active else 8, value))
    return {'frame': {'pixels_base64': base64.b64encode(deterministic_text_raster(commands)).decode('ascii')}}


class DeviceConfigurationOracleTests(TestCase):
    def setUp(self):
        self.patches = [patch.object(frame_oracle, 'render', side_effect=deterministic_text_raster),
                        patch.object(frame_oracle, 'text_width', side_effect=fake_text_width),
                        patch.object(frame_oracle, 'fit', side_effect=fake_fit)]
        for item in self.patches: item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def test_matches_exact_preselection_device_value(self):
        self.assertTrue(device_configuration_matches(detail_snapshot('None', None, None), device='None'))
        self.assertFalse(device_configuration_matches(detail_snapshot('CC Device', None, None), device='None'))

    def test_matches_three_visible_detail_rows_and_rejects_each_wrong_value_or_selection(self):
        state = detail_snapshot()
        self.assertTrue(device_configuration_matches(state, 'CC Device', 'CC2', 'OUT 2', selected_label='Device'))
        self.assertTrue(device_configuration_matches(detail_snapshot(selected='MIDI channel'), 'CC Device', 'CC2', 'OUT 2', selected_label='MIDI channel'))
        self.assertTrue(device_configuration_matches(detail_snapshot(selected='MIDI port'), 'CC Device', 'CC2', 'OUT 2', selected_label='MIDI port'))
        self.assertFalse(device_configuration_matches(state, 'CC Device', 'CC2', 'OUT 2', selected_label='MIDI channel'))
        self.assertFalse(device_configuration_matches(detail_snapshot('Doubledecker'), 'CC Device', 'CC2', 'OUT 2'))
        self.assertFalse(device_configuration_matches(detail_snapshot(channel='CC1'), 'CC Device', 'CC2', 'OUT 2'))
        self.assertFalse(device_configuration_matches(detail_snapshot(port='OUT 1'), 'CC Device', 'CC2', 'OUT 2'))

    def test_rejects_shifted_or_corrupt_framebuffers(self):
        shifted = {'frame': {'pixels_base64': base64.b64encode(deterministic_text_raster([(10, 35, 15, 'CC Device'), (70, 35, 15, 'CC2'), (95, 35, 15, 'OUT 2')])).decode('ascii')}}
        self.assertFalse(device_configuration_matches(shifted, 'CC Device', 'CC2', 'OUT 2'))
        self.assertFalse(device_configuration_matches({'frame': {'pixels_base64': 'not-base64'}}, 'CC Device', 'CC2', 'OUT 2'))
        self.assertFalse(device_configuration_matches({'frame': {'pixels_base64': base64.b64encode(bytes(12)).decode('ascii')}}, 'CC Device', 'CC2', 'OUT 2'))

    def test_rejects_partial_selected_route(self):
        self.assertFalse(device_configuration_matches(detail_snapshot(), 'CC Device', 'CC2', None))


class PreservedNativeVerticalListRegression(TestCase):
    def test_native_device_none_frame_matches_active_vertical_row(self):
        fixture = Path(__file__).resolve().parent / 'fixtures' / 'native-device-none.json'
        evidence = json.loads(fixture.read_text())
        state = evidence['state']
        pixels = base64.b64decode(state['frame']['pixels_base64'], validate=True)
        self.assertEqual(hashlib.sha256(pixels).hexdigest(), evidence['capture']['frame_sha256'])
        self.assertEqual(state['frame']['sha256'], evidence['capture']['frame_sha256'])
        self.assertEqual(evidence['capture']['backend'], 'native')
        self.assertEqual(evidence['capture']['fidelity'], 'native-norns')
        with patch.object(frame_oracle, 'render', side_effect=REAL_RENDER):
            self.assertTrue(device_configuration_matches(state, device='None'))
            self.assertFalse(device_configuration_matches(state, device='CC Device'))



class PreservedNativeDeviceDraftRegression(TestCase):
    def test_native_draft_frame_matches_all_three_detail_rows_and_rejects_mutations(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "device-draft-native.json"
        evidence = json.loads(fixture.read_text())
        state = evidence["state"]
        pixels = base64.b64decode(state["frame"]["pixels_base64"], validate=True)
        digest = hashlib.sha256(pixels).hexdigest()
        self.assertEqual(digest, evidence["capture"]["frame_sha256"])
        self.assertEqual(state["frame"]["sha256"], digest)
        self.assertEqual(evidence["capture"]["backend"], "native")
        self.assertEqual(evidence["capture"]["fidelity"], "native-norns")
        with patch.object(frame_oracle, "render", side_effect=REAL_RENDER):
            self.assertTrue(device_configuration_matches(state, "CC Device", "CC1", "OUT 1"))
            self.assertFalse(device_configuration_matches(state, "None", "CC1", "OUT 1", selected_label="Device"))
            self.assertFalse(device_configuration_matches(state, "CC Device", "CC2", "OUT 1", selected_label="Device"))
            self.assertFalse(device_configuration_matches(state, "CC Device", "CC1", "OUT 2", selected_label="Device"))
            self.assertFalse(device_configuration_matches(state, "CC Device", "CC1", "OUT 1", selected_label="MIDI channel"))
            corrupt = {"frame": {"pixels_base64": "not-base64"}}
            self.assertFalse(device_configuration_matches(corrupt, "CC Device", "CC1", "OUT 1", selected_label="Device"))


if __name__ == '__main__':
    main(verbosity=2)
