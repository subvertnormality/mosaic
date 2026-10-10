"""UI-migration characterisation of the documented device-config picker scenarios."""
import unittest
from unittest.mock import patch, sentinel


class DeviceConfigOwnerTests(unittest.TestCase):
    def test_invalid_config_cases_have_named_contract_owners(self):
        from cases import CASES
        import contract.device_configs as owner

        for case_id, name, scenario in (
            ('M-SETUP-001', 'malformed_device_configs', 'malformed'),
            ('M-SETUP-002', 'missing_id_device_configs', 'missing-id'),
        ):
            with self.subTest(case_id=case_id):
                run = CASES[case_id]['run']
                self.assertIs(run, getattr(owner, name))
                self.assertEqual(run.__module__, 'contract.device_configs')
                self.assertIsNone(run.__closure__)
                with patch.object(owner, 'invalid_device_configs', return_value=sentinel.result) as helper:
                    self.assertIs(run(sentinel.driver), sentinel.result)
                helper.assert_called_once_with(sentinel.driver, scenario)


if __name__ == '__main__':
    unittest.main()
