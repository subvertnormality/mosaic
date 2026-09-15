# Transpose live-clear oracle closure

Use Codex only. Read-only local shell commands are allowed; do not edit files or launch tests or runtime processes.

Review the findings from `docs/testing/reviews/transpose-interactions-review.json`, session `01a08943-1a4e-7972-807c-38949db9c307`. M-TRANS-003 now:

- locates the sounding sixth note's ownership pair by onset event index rather than release order;
- asserts `onset <= clear_lower <= clear_upper < release` and its one-step duration;
- requires a bounded complete onset count and validates every captured onset's port and exact MIDI bytes;
- validates every release's port, pitch and velocity against its owner;
- attributes unlocked wrap fallback to this case, while M-TRANS-002 claims repeated composition and step4 persistence only.

Corrected controlled and real-time manifests are recorded in `docs/testing/transpose-lock-validation.json`. Confirm whether all findings are closed and report any remaining blocker in these two scoped interaction cases. Return ACCEPTED or CHANGES REQUIRED. Do not broaden the completion claim.
