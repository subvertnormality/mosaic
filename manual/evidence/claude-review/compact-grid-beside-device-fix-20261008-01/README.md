# Compact grid/device layout evidence

This is an evidence archive for the installed CSS and registered browser-test change. The v2 adoption is represented by MANIFEST.json; the earlier v1 receipt is preserved byte-for-byte as MANIFEST-HISTORICAL-61f0be64676746a586c8fff0ed570186afa1bf1d5c33541ce4676e353043944b.json.

The final standalone focused harness is harness/layout_regression.cjs. It is an operator-workspace harness, not a portable repository test: it hard-codes /home/andy/mosaic-manual-tools/node_modules/playwright and the candidate/baseline trees below. It routes the local /manual/ origin to these files:

- Candidate: /home/andy/mosaic-manual-build-operators/compact-grid-beside-device-fix-20261008-02/manual
- c664 baseline: /home/andy/mosaic-manual-build-operators/compact-grid-beside-device-fix-20261008-02/baseline/manual

The archived invocations were node /home/andy/mosaic-manual-build-operators/compact-grid-beside-device-fix-20261008-02/layout_regression.cjs --baseline-copy and the same command with --candidate. Their final JSON reports are retained in proof/red-final.json and proof/green-final.json. The earlier report that omitted a viewport-edge assertion is retained as proof/green-v2-false-green.json and is not a passing result for clipping.

baseline/manual.css.c664 is the exact v2 RED baseline (SHA-256 c664709772996b542460a5c55a9c2eaf54e633170a29ce90685b78b10645cbcc). The history/ subfolder preserves the initial 123afe baseline, its first RED report and the first registered-test/source diffs, so the initial grid regression can be reconstructed without the original large external worktree. No fresh-clone portability is claimed.
