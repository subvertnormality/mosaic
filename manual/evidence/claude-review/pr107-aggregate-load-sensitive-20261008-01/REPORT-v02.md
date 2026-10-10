# PR 107 aggregate coverage failure diagnosis (corrected source identity)

This corrected report supersedes only the textual PR head SHA in REPORT.md. The original remains preserved unchanged for provenance.

Verified PR and workflow identity:
- PR: https://github.com/subvertnormality/mosaic/pull/107
- Run 37778845187, event pull_request, branch codex/main-pages-promotion-v03
- Exact PR/run head: e05cf0d7c8e9be44259c3dad5a7c66dcd5dc5bb3
- Base: 5384d0babb01fd5004bdcd6a95eaa8609aa72915
- Failed aggregate job 113368333661; shard 7 job 113316510426
- Run checkout revision: synthetic merge commit 25d760e7a6782b5fdd5d389564555ef5dfed12de; tree 25f4adedae55974c3ffa56b69c22a9e8315f663c.

The aggregate failed because shard 7 recorded load_sensitive=[M-PATCH-059, real-time]. First real-time run failed after 15.8 seconds when a three-second Driver.wait did not observe selected menu label LEVELS > while opening Patch Control. Controlled-experimental lane passed; serial retry passed in 171.5 seconds. The verifier correctly rejects recovery on retry. This is consistent with timing variance, but host load is unproven and the first failure remains valid evidence. The PR changes ten publisher/documentation files and does not modify cases.py, patch_params.py, or driver.py.

The raw shard ZIP, both job logs, suite-effective report and failed/retry manifests remain preserved beside this report in this directory. See REPORT.md for the initial detailed diagnosis and all preserved evidence SHA256 values. Only its textual head SHA was wrong; the correction receipt records the exact correction and the authoritative PR/run API verification. No workflow dispatch, retry, source edit, or oracle change was performed.
