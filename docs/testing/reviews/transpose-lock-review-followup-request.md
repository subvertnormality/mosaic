# Transpose-lock explicit-zero follow-up

Use Codex only. Read-only local shell commands are allowed; do not edit files or launch tests or runtime processes.

Review only the low-severity qualification from `docs/testing/reviews/transpose-lock-review.json`, session `01a08931-fa99-7441-b097-636bd7524745`. The accepted -12..+12 production fix is unchanged.

M-TRANS-001 now authors global transpose +4 before the locks. Step1 walks every -12..+12 value; step2 has an explicit-zero lock. After K2 clears step1, the required phrase is `[64, 62, 64, 65]`: step1 must inherit global +4, while step2 must remain explicit zero and keep later steps untransposed. Both final controlled and real-time manifests and the refreshed 527/21 logs are recorded in `docs/testing/transpose-lock-validation.json`.

Confirm whether this distinguishes deletion from replacement with zero and proves that clearing step1 leaves step2's explicit-zero lock intact. Return ACCEPTED or CHANGES REQUIRED and identify any remaining blocker in this scoped assertion. Do not broaden the acceptance claim to the remaining transpose interaction domain.
