"""Staged differential recipe tests against the unchanged legacy helper.

Characterisation outside the manual: migration must retain the exact existing
input recipe, verification records, scan boundary and returned cached offset.
Copy this into tests/behaviour/test_ui_assign_trig_parameter.py before adding
Ui.assign_trig_parameter: it is expected to fail on the missing method.
"""

import unittest

from cases import assign_trig_parameter as legacy_assign
from ui import Ui


class FakeDriver:
    def __init__(self, visible_after=2, label_matches=True):
        self.events = []
        self.results = []
        self.ui = StubUi(self, visible_after, label_matches)

    def key(self, number):
        self.events.append(('key', number))

    def enc(self, number, delta):
        self.events.append(('enc', number, delta))


class StubUi(Ui):
    def __init__(self, driver, visible_after, label_matches):
        super().__init__(driver)
        self.visible_after = visible_after
        self.label_matches = label_matches
        self.probes = 0

    def expect_list_label(self, label, wait=True):
        self.driver.events.append(('label', label, wait))
        if not wait:
            self.probes += 1
            return self.probes > self.visible_after
        if not self.label_matches:
            raise AssertionError('label mismatch')
        self.driver.results.append(
            dict(kind='parameter-list-label', label=label, passed=True))
        return True


class AssignTrigParameterParity(unittest.TestCase):
    def compare(self, offset=None, visible_after=2, label_matches=True, fails=False):
        before = FakeDriver(visible_after, label_matches)
        after = FakeDriver(visible_after, label_matches)
        if fails:
            with self.assertRaises(AssertionError):
                legacy_assign(before, 'CC 1', offset=offset)
            with self.assertRaises(AssertionError):
                after.ui.assign_trig_parameter('CC 1', offset=offset)
        else:
            expected = legacy_assign(before, 'CC 1', offset=offset)
            self.assertEqual(after.ui.assign_trig_parameter('CC 1', offset=offset), expected)
        self.assertEqual(after.events, before.events)
        self.assertEqual(after.results, before.results)
        return after

    def test_scan_first_middle_last(self):
        for position in (0, 2, 49):
            with self.subTest(position=position):
                self.compare(visible_after=position)

    def test_cached_offsets_preserve_single_jump_and_no_scan(self):
        for offset in (0, 2, 49, -1):
            with self.subTest(offset=offset):
                after = self.compare(offset=offset)
                self.assertEqual(after.ui.probes, 0)

    def test_missing_label_preserves_fifty_failed_scan_steps(self):
        after = self.compare(visible_after=50, fails=True)
        self.assertEqual(after.events.count(('enc', 3, 1)), 50)
        self.assertEqual(after.results, [])
        self.assertNotIn(('key', 3), after.events)

    def test_bad_cached_offset_cannot_confirm_wrong_parameter(self):
        after = self.compare(offset=2, label_matches=False, fails=True)
        self.assertNotIn(('key', 3), after.events)
        self.assertEqual(after.results, [])


if __name__ == '__main__':
    unittest.main()
