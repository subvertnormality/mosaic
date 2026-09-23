"""Characterisation: the live CC follows the applied public encoder input."""
import unittest

from trig_parameter_interactions import recorded_edit_receipt, assert_immediate_cc_on_edit


class FakeDriver:
    def __init__(self):
        from ui import Ui
        self.ui = Ui(self)
        self.calls = []
        self.receipt = {'status': 'applied', 'native': {'monotonic_ns': 1_000_000_000}}

    def elapse(self, seconds):
        self.calls.append(('elapse', seconds))

    def action(self, **action):
        self.calls.append(('action', action))
        return self.receipt


class RecordedEditInputTiming(unittest.TestCase):
    def test_receipt_preserves_single_encoder_step_recipe(self):
        driver = FakeDriver()
        self.assertIs(recorded_edit_receipt(driver), driver.receipt)
        self.assertEqual(driver.calls, [
            ('elapse', .05),
            ('action', {'type': 'enc', 'n': 3, 'delta': 2}),
            ('elapse', .15),
        ])

    def test_immediate_cc_accepts_prompt_emission_on_either_side_of_ack(self):
        receipt = FakeDriver().receipt
        for delta in (-10_000_000, 0, 10_000_000):
            with self.subTest(delta=delta):
                self.assertEqual(assert_immediate_cc_on_edit(
                    {'monotonic_ns': 1_000_000_000 + delta}, receipt), delta)

    def test_immediate_cc_rejects_late_or_early_emission(self):
        receipt = FakeDriver().receipt
        for delta in (-10_000_001, 10_000_001, 32_000_000):
            with self.subTest(delta=delta):
                with self.assertRaises(AssertionError):
                    assert_immediate_cc_on_edit(
                        {'monotonic_ns': 1_000_000_000 + delta}, receipt)

    def test_immediate_cc_requires_applied_native_receipt(self):
        for receipt in ({'status': 'accepted', 'native': {'monotonic_ns': 1_000_000_000}},
                        {'status': 'applied', 'native': {}},
                        {}):
            with self.subTest(receipt=receipt):
                with self.assertRaises(AssertionError):
                    assert_immediate_cc_on_edit({'monotonic_ns': 1_000_000_000}, receipt)
