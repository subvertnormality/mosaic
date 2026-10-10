"""The physical-Norns core bundle must contain every isolated test dependency."""
import unittest

from tests.rhythm_doctor import run_hardware_core


class HardwareCoreRunnerTests(unittest.TestCase):
    def test_runtime_and_app_surface_dependencies_are_deployed(self):
        for relative in ("lib/rhythm_doctor/bank_persistence.lua",
                         "lib/rhythm_doctor/analysis_worker_host.lua",
                         "lib/ui.lua"):
            self.assertIn(relative, run_hardware_core.FILES)

    def test_norns_global_include_is_disabled_for_isolated_component_tests(self):
        command = run_hardware_core.isolated_lua_command("/tmp/rd bundle", "tests/rhythm_doctor/test_runtime.lua")
        self.assertEqual(command, "cd '/tmp/rd bundle' && lua -e 'include=nil' tests/rhythm_doctor/test_runtime.lua")


if __name__ == "__main__":
    unittest.main()
