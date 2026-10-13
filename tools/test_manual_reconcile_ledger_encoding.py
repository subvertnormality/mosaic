"""Reconciled ledgers use the same byte encoding as the deterministic replay.

Regression: build d4e5a27970ca44a9be100843ed971d0a reconciliation failed
("reconciled file differs from deterministic output") because the review ledger
was written with ASCII escapes (\\u2013) while the ledgers, the approved overlay
and manual_metadata_transition.dumps use raw UTF-8.
"""
import os
import sys
import unittest
from pathlib import Path

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(REPO / "tools"), str(REPO / "tests/behaviour")]
import manual_metadata_transition
import manual_reconcile_build


class LedgerEncoding(unittest.TestCase):
    def test_all_three_payloads_match_the_replay_encoding(self):
        review = {"meaning": "integer BPM 40–240"}
        out = {"files": ["café"]}
        receipt = {"note": "→"}
        payloads = manual_reconcile_build.ledger_payloads(review, out, receipt)
        self.assertEqual([p.encode() for p in payloads],
                         [manual_metadata_transition.dumps(v) for v in (review, out, receipt)])


if __name__ == "__main__":
    unittest.main()
