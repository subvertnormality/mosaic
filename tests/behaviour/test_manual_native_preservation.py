"""Reader/native-capture preservation characterisation outside the manual."""
import pathlib
import subprocess
import unittest

class NativePreservationRegression(unittest.TestCase):
    def test_native_preservation_regressions(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        result = subprocess.run(
            ["node", str(root / "tests/behaviour/manual_native_preservation_test.cjs")],
            cwd=root, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
