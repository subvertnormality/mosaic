"""UI-migration characterisation of documented lock-lead clock scenarios."""
import unittest
from unittest.mock import patch, sentinel


class LockLeadOwnerTests(unittest.TestCase):
    def test_clock_matrix_scenarios_have_named_contract_owners(self):
        from cases import CASES
        import contract.lock_lead_clock_matrix as owner

        recipes = (
            (2, 'normal'), (3, 'fast'), (4, 'x4-130'), (5, 'x4-200'),
            (6, 'x16-130'), (7, 'swing'), (8, 'swing-negative'),
            (9, 'shuffle'),
            (10, 'swing-toggle'), (11, 'shuffle-toggle'), (12, 'slides'),
            (13, 'tempo-change'), (14, 'resend-off'),
            (15, 'resend-off-x4-200'), (16, 'range-late'),
            (17, 'range-wrap-slide'), (18, 'global-cap'),
            (19, 'range-live'), (20, 'range-live-off'),
        )
        for number, scenario in recipes:
            case_id = 'M-SYNC-LEAD-%03d' % number
            name = 'lock_lead_clock_%03d_%s' % (
                number, scenario.replace('-', '_'))
            with self.subTest(case_id=case_id):
                run = CASES[case_id]['run']
                self.assertIs(run, getattr(owner, name))
                self.assertEqual(run.__module__, 'contract.lock_lead_clock_matrix')
                self.assertIsNone(run.__closure__)
                self.assertIs(run.__globals__['lock_lead_clock_matrix'],
                              owner.lock_lead_clock_matrix)
                with patch.object(owner, 'lock_lead_clock_matrix',
                                  return_value=sentinel.result) as helper:
                    self.assertIs(run(sentinel.driver), sentinel.result)
                helper.assert_called_once_with(sentinel.driver, scenario)


    def test_clock_matrix_selects_each_public_menu_checkpoint_before_play(self):
        import tempfile
        from pathlib import Path
        import contract.lock_lead_clock_matrix as owner

        class Driver:
            def __init__(self, out):
                self.out = Path(out)
                self.results = []
                self.trace = []
                self.current_lead = None

            def finish(self):
                pass

            def _set_midi_lead_time(self, lead):
                self.current_lead = lead
                self.trace.append(('menu-checkpoint', lead))
                self.results.append(dict(kind='selected-menu-option-row', lead_ms=lead, passed=True))

        class Context:
            def __init__(self, out):
                self.out = Path(out)
                self.results = []
                self.clock_mode = 'controlled-experimental'

            def finish(self):
                pass

        with tempfile.TemporaryDirectory() as temp:
            driver = Driver(temp)
            context = Context(temp)

            def play(e, condition):
                e.trace.append(('play', e.current_lead))
                return [], None, 0

            with patch.object(owner, 'boot_with', return_value=driver), \
                 patch.object(owner, 'set_tempo'), \
                 patch.object(owner, 'build'), \
                 patch.object(owner, 'play', side_effect=play), \
                 patch.object(owner, 'timeline', return_value={'notes': [{'monotonic_ns': 0, 'logical_ns': 0}], 'values': [], 'steps': []}), \
                 patch.object(owner, 'compare', return_value={'passed': True}):
                owner.lock_lead_clock_matrix(context, 'normal')

            self.assertEqual(
                [row['lead_ms'] for row in driver.results if row['kind'] == 'selected-menu-option-row'],
                [0, 25, 50],
            )
            self.assertEqual(driver.trace, [
                ('menu-checkpoint', 0), ('play', 0),
                ('menu-checkpoint', 25), ('play', 25),
                ('menu-checkpoint', 50), ('play', 50),
            ])


if __name__ == '__main__':
    unittest.main()
