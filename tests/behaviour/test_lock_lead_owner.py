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


if __name__ == '__main__':
    unittest.main()
