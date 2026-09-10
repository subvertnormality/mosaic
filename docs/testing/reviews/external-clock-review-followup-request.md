# External MIDI clock follow-up review

Use Codex only. Read-only local shell commands are allowed for inspecting files, manifests, logs, and Git diffs. Do not edit files or launch tests or runtime processes.

Review the corrected external MIDI clock slice in `/home/andy/projects/mosaic-behaviour-tests` and its generic emulator support in `/home/andy/projects/monome-emulator-midi-clock`. The initial substantive review is `docs/testing/reviews/external-clock-review-02.json`, session `01a088f5-c6a7-7082-84b2-e95572ddef15`.

Confirm whether these five findings are closed:

1. Every active note owner must release before the next onset, including equal-deadline restart swaps.
2. Stop silence must be demonstrated while twelve further MIDI Clock pulses arrive.
3. The generic oracle must validate every captured output event, including port and full MIDI bytes, and reject unexpected traffic.
4. Transport-triggered releases must have causal lower bounds and an appropriate transport-specific upper tolerance.
5. Documentation must state that clock loss freewheels without inferred Stop, and that Start takes effect on the next Clock pulse.

Use `docs/testing/external-clock-fault-validation.json` for the current immutable evidence paths and hashes. Also inspect the changed tests, README/manual binding, generic probe/runner, mutation tests, and both repositories' diffs. Report any remaining correctness blocker in this scoped slice. Clearly return either ACCEPTED or CHANGES REQUIRED, with concrete findings ordered by severity.
