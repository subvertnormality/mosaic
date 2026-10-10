"""A controlled-local build's caption rebind audits raw publications in controlled scope.

Regression from the isolated dry run of build f718168dd9644747b9042e57a1c9b0d6's
remaining stages: caption-rebind ran the real-time raw audit, which rejects the
controlled Masks publication ("Fresh pilot incomplete").
"""
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(REPO / "tools"), str(REPO / "tests/behaviour")]
import manual_build
import manual_caption_rebind
import manual_publication_verify


class ControlledCaptionRebind(unittest.TestCase):
    def test_controlled_audit_uses_controlled_raw_publication_scope(self):
        with patch.object(manual_publication_verify, "audit_raw_publications", return_value={"passed": True}) as audit:
            manual_caption_rebind.audit_raw_publications(controlled_local=True)
        audit.assert_called_once_with(controlled_local=True)

    def test_cli_forwards_controlled_local(self):
        with patch.object(sys, "argv", ["manual_caption_rebind.py", "--evidence", "/tmp/x", "--controlled-local"]), \
             patch.object(manual_caption_rebind, "rebind", return_value={}) as rebind, patch("builtins.print"):
            manual_caption_rebind.main()
        self.assertIs(rebind.call_args.kwargs.get("controlled_local"), True)

    def test_controlled_local_plan_runs_caption_rebind_in_controlled_scope(self):
        options = types.SimpleNamespace(emulator="/e", real_install=None, controlled_install="/c", readability_real_install=None,
            audio_emulator="/a", audio_install="/ai", mod_code_root="/m", modulation_code_root="/mm", ffmpeg="/f",
            quick_output="cheat_sheet.html", browser_tests=False, python="/usr/bin/python3")
        plans = [p.name for p in sorted((manual_build.ROOT / "manual").glob("scene-plans*.yaml"))]
        stage = next(s for s in manual_build.plan(options, plans, controlled_local=True) if s["name"] == "caption-rebind")
        self.assertIn("--controlled-local", stage["command"])


if __name__ == "__main__":
    unittest.main()
