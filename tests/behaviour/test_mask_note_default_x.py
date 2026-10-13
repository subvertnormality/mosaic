"""Pure check of the native case's public input recipe and exact MIDI oracles."""
import json
import sys
from pathlib import Path
import types
import unittest
from unittest.mock import patch

from mask_note_default_x import mask_note_default_unset


class FakeUI:
    def __init__(self):
        self.calls = []

    def configure(self):
        self.calls.append(('configure',))

    def channel_page(self, *args, **kwargs):
        self.calls.append(('channel_page', args, kwargs))

    def select_field(self, *args, **kwargs):
        self.calls.append(('select_field', args, kwargs))

    def expect_header(self, *args, **kwargs):
        self.calls.append(('expect_header', args, kwargs))

    def expect_field_value(self, *args, **kwargs):
        self.calls.append(('expect_field_value', args, kwargs))

    def set_value(self, delta):
        self.calls.append(('set_value', delta))


class FakeContext:
    def __init__(self):
        self.ui = FakeUI()
        self.results = []
        self.playback_calls = []

    def playback(self, phrase, cycles, timeout):
        self.playback_calls.append((phrase, cycles, timeout))
        return list(range(len(phrase) * cycles))


class ChannelNoteDefaultUnsetTests(unittest.TestCase):
    def test_public_workflow_and_exact_pattern_restoration_oracles(self):
        duration_calls = []
        fake_cases = types.ModuleType('cases')
        fake_cases.assert_durations = lambda c, notes, expected: duration_calls.append((len(notes), expected))
        context = FakeContext()
        with patch.dict(sys.modules, {'cases': fake_cases}):
            mask_note_default_unset(context)

        self.assertEqual(context.ui.calls, [
            ('configure',),
            ('channel_page', ('masks', 'midi_config'), {'channel': 1}),
            ('select_field', ('note',), {'offset': 0}),
            ('expect_header', ('masks',), {'channel': 1}),
            ('expect_field_value', ('note', 'X'), {}),
            ('set_value', 68),
            ('expect_field_value', ('note', 'G3'), {}),
            ('set_value', -68),
            ('expect_field_value', ('note', 'X'), {}),
        ])
        self.assertEqual(context.playback_calls, [
            ([(1, [144, 67, 127]), (1, [144, 67, 117]),
              (1, [144, 67, 107]), (1, [144, 67, 97])], 2, 5),
            ([(1, [144, 60, 127]), (1, [144, 62, 117]),
              (1, [144, 64, 107]), (1, [144, 65, 97])], 2, 5),
        ])
        self.assertEqual(duration_calls, [(8, [1] * 8), (8, [1] * 8)])
        self.assertEqual(context.results[0]['kind'], 'channel-note-default-unset-restores-pattern')
        self.assertEqual(context.results[0]['restored_pattern_phrase'], context.playback_calls[1][0])
        self.assertEqual(context.results[0]['citation'], 'manual:masks')



    def test_case_is_registered_under_both_manual_requirements(self):
        root = Path(__file__).resolve().parents[2]
        case_source = (root / 'tests/behaviour/cases.py').read_text()
        self.assertIn("'M-MASK-NOTE-X-001':dict", case_source)
        inventory = json.loads((root / 'tests/behaviour/manual-inventory.json').read_text())
        requirements = {item['id']: item for item in inventory['requirements']}
        for requirement_id in ('MASK-ATTRIBUTES', 'MASK-PRECEDENCE'):
            self.assertIn('M-MASK-NOTE-X-001', requirements[requirement_id]['cases'])
        feature = (root / 'manual/features/masks.yaml').read_text()
        self.assertIn('behaviour_case: M-MASK-NOTE-X-001', feature)
        self.assertIn('citation: manual:masks', feature)
if __name__ == '__main__':
    unittest.main()
