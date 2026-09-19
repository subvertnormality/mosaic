# External MIDI clock causal-bound closure review

Use Codex only. Read-only local shell commands are allowed for inspecting files, manifests, logs, and Git diffs. Do not edit files or launch tests or runtime processes.

Review the corrected external MIDI clock slice in `/home/andy/projects/mosaic-behaviour-tests` and `/home/andy/projects/monome-emulator-midi-clock`. The previous follow-up is `docs/testing/reviews/external-clock-review-followup.json`, session `01a0890a-adf0-7311-876a-0137f7a6b8e6`; it found only that scheduled deadlines were still used where actual transport delivery timestamps were required.

Confirm that this remaining finding is closed. Both runners now identify the unique delivered Stop or beat-zero Clock record by MIDI bytes and intended timestamp, take its `actual_logical_ns` or `actual_monotonic_ns`, and use that actual timestamp as the causal lower bound. Transport-specific upper tolerances remain separate. Mosaic has distinct mutations for release before actual Stop and release before actual restart Clock; the generic runner has lower- and upper-bound mutations.

Use `docs/testing/external-clock-fault-validation.json` for current immutable manifests and logs. Inspect the changed tests, relevant retained evidence, and both repository diffs. Report any remaining correctness blocker in this scoped slice. Clearly return either ACCEPTED or CHANGES REQUIRED, with concrete findings ordered by severity.
