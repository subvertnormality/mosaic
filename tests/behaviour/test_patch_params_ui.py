"""UI-migration characterisation; musical contracts remain README 749, 952-963, 1167-1174."""
import unittest
from pathlib import Path


class PatchParamsUiTests(unittest.TestCase):
    def test_current_patch_seek_preserves_scan_without_added_label_or_setup(self):
        from unittest.mock import patch
        from test_ui import FakeDriver
        from ui import Ui
        driver = FakeDriver([{}, {}])
        ui = Ui(driver)
        with patch('frame_oracle.selected_line', side_effect=[False, True]) as selected:
            ui.seek_current_patch_parameter('cc_default', confirm=False)
        self.assertEqual(driver.calls, [('snapshot',), ('enc', 2, 1), ('snapshot',)])
        self.assertEqual([call.args[1] for call in selected.call_args_list], ['CCdefault'] * 2)

    def test_current_patch_seek_retains_original_failure(self):
        from unittest.mock import patch
        from test_ui import FakeDriver
        from ui import Ui
        driver = FakeDriver([{}, {}])
        with patch('frame_oracle.selected_line', return_value=False):
            with self.assertRaisesRegex(AssertionError, '^Sparse control not reachable$'):
                Ui(driver).seek_current_patch_parameter('sparse_high', attempts=2,
                                                        failure='Sparse control not reachable')
        self.assertEqual(driver.calls, [('snapshot',), ('enc', 2, 1)] * 2)

    def test_current_patch_seek_confirms_once_and_rejects_unknown_keys(self):
        from unittest.mock import patch
        from test_ui import FakeDriver
        from ui import Ui, UiMapError
        driver = FakeDriver([{}])
        ui = Ui(driver)
        with patch('frame_oracle.selected_line', return_value=True), \
                patch.object(ui, 'expect_menu_label') as label:
            ui.seek_current_patch_parameter('nrpn_legacy_6')
        label.assert_called_once_with('NL6')
        self.assertEqual(driver.calls, [('snapshot',)])
        with self.assertRaisesRegex(UiMapError, 'unknown patch parameter'):
            ui.seek_current_patch_parameter('not_a_parameter')
        self.assertEqual(driver.calls, [('snapshot',)])

    def test_patch_module_and_reachable_helpers_are_semantic(self):
        from cases import CASES
        from ui_layer_guard import raw_sites, callable_raw_dependencies
        self.assertEqual(raw_sites(Path(__file__).with_name('patch_params.py')), [])
        contracts = {'M-PATCH-004', 'M-PATCH-024', 'M-PATCH-025', 'M-PATCH-026', 'M-PATCH-031', 'M-PATCH-032'}
        for case_id, case in CASES.items():
            if case_id.startswith('M-PATCH-') and case_id not in contracts:
                self.assertEqual(callable_raw_dependencies(case['run']), [], case_id)

    def test_literal_patch_contracts_have_contract_owners(self):
        from cases import CASES
        from unittest.mock import patch, sentinel
        import contract.patch_params as owner
        from contract.patch_params import patch_slide_live_division, patch_slide_stop_restarts
        self.assertEqual(patch_slide_live_division.__module__, 'contract.patch_params')
        self.assertIs(CASES['M-PATCH-024']['run'], patch_slide_live_division)
        self.assertIs(CASES['M-PATCH-031']['run'], patch_slide_stop_restarts)
        for case_id, name, option in (
            ('M-PATCH-025', 'patch_slide_live_division_type_switch', 'type_switch'),
            ('M-PATCH-026', 'patch_slide_live_division_reset', 'reset'),
            ('M-PATCH-032', 'patch_slide_live_division_repeated_edits', 'repeated_edits'),
        ):
            with self.subTest(case_id=case_id):
                run = CASES[case_id]['run']
                self.assertIs(run, getattr(owner, name))
                self.assertEqual(run.__module__, 'contract.patch_params')
                self.assertIsNone(run.__closure__)
                with patch.object(owner, 'patch_slide_live_division', return_value=sentinel.result) as helper:
                    self.assertIs(run(sentinel.driver), sentinel.result)
                helper.assert_called_once_with(sentinel.driver, **{option: True})


if __name__ == '__main__':
    unittest.main()
