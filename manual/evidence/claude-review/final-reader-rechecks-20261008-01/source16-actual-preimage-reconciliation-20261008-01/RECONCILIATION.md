# Actual-preimage reconciliation proposal

Read-only comparison of the authoritative current behaviour tests with the isolated final candidate. The attached unified diff is a proposal only; the actual checkout was not edited and no tests were run.

The exact current/candidate hashes for all scoped files are in RECONCILIATION.json. The source16 browser candidate carries the previously audited native output/input pins, full MIDI source checks, canonical alias checks and the final strict audio-frame wait. Current course-stage audio ownership checks are retained in manual_course_browser, whose separate 9-check green receipt is pinned in the course addendum.

Current manual_browser immediate audio seeking is race-prone; candidate adds seeked plus exact pixel/grid waiting with a 5-second bound, preserving the strict native oracle. Feature-default audio checks are replaced by canonical recording homes and exact source-linked route coverage. Technical MIDI/evidence DOM checks are updated to require the public reader to hide those developer-only panels, while event/source hashes and visible semantic MIDI assertions remain.

The actual checkout lacked 11 candidate remediation files; the proposal adds them rather than replacing existing files. The patch is reviewable but not self-authorizing; root should apply only after accepting this mapping.

Diff SHA-256: 2e5d28be906290ef0fdb842065f7c1f737ce12edc6dbfdbdf33afd67391c67e2
