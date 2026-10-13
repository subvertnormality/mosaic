"""Every controlled-local builder invocation of the publication verifier parses.

Regression: the controlled raw-publication-audit stage passes
--raw-only --controlled-local, which the CLI rejected as mutually exclusive.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(REPO / "tools"), str(REPO / "tests/behaviour")]
import manual_publication_verify as verify


class PublicationVerifyCli(unittest.TestCase):
    def run_main(self, argv):
        with patch.object(sys, "argv", ["manual_publication_verify.py", *argv]), \
             patch.object(verify, "audit_raw_publications", return_value={"raw": True}) as raw, \
             patch.object(verify, "audit_controlled_manual_generation", return_value={"build": True}) as build, \
             patch.object(verify, "audit_publication", return_value={"full": True}) as full, \
             patch("builtins.print"):
            verify.main()
        return raw, build, full

    def test_controlled_raw_only_audits_raw_publications_in_controlled_scope(self):
        raw, build, full = self.run_main(["--raw-only", "--controlled-local"])
        raw.assert_called_once_with(controlled_local=True)
        build.assert_not_called(); full.assert_not_called()

    def test_controlled_build_audit_still_requires_evidence(self):
        with self.assertRaises(SystemExit):
            self.run_main(["--controlled-local"])

    def test_refresh_and_raw_only_remain_exclusive(self):
        with self.assertRaises(SystemExit):
            self.run_main(["--refresh-editorial", "--raw-only"])


if __name__ == "__main__":
    unittest.main()
