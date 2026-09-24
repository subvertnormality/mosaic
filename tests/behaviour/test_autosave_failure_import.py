"""Harness regression: the failed-save case resolves its project-menu helpers."""
import unittest

from contract.autosave_failure import autosave_failure


class StopAfterImports(Exception):
    pass


class Driver:
    def configure(self):
        raise StopAfterImports


class AutosaveFailureImportTests(unittest.TestCase):
    def test_case_reaches_driver_after_importing_navigation_helpers(self):
        with self.assertRaises(StopAfterImports):
            autosave_failure(Driver())


if __name__ == "__main__":
    unittest.main()
