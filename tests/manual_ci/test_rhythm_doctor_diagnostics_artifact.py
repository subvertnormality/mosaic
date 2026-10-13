"""Keep per-role child output when a Doctor matrix capture fails."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "behaviour.yml"


class DoctorFailureDiagnosticsArtifact(unittest.TestCase):
    def test_upload_includes_per_role_orchestrator_logs(self):
        source = WORKFLOW.read_text()
        start = re.search(
            r"(?m)^      - name: Upload Rhythm Doctor option qualification\s*$",
            source,
        )
        self.assertIsNotNone(start, "Doctor diagnostics artifact step is missing")
        next_step = re.search(r"(?m)^      - name: ", source[start.end():])
        end = start.end() + next_step.start() if next_step else len(source)
        upload_step = source[start.start():end]
        self.assertRegex(
            upload_step,
            r"(?m)^[ \t]*/tmp/rd-options/\*\*/orchestrator\.log[ \t]*$",
            "failed per-role child output is written but omitted from the artifact",
        )


if __name__ == "__main__":
    unittest.main()
