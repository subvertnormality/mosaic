# Full-range transpose-lock candidate review

Use Codex only. Read-only local shell commands are allowed to inspect the Mosaic worktree, retained manifests/logs, Git diff and pinned manual. Do not edit files or launch tests or runtime processes.

Review the isolated Mosaic candidate in `/home/andy/projects/mosaic-behaviour-tests`. The scale-page fader publicly exposes transpose values -12..+12, and the manual says a held step accepts the desired transpose value. The retained stock-baseline run in `docs/testing/transpose-lock-validation.json` shows selecting -12 emits MIDI53 rather than independently expected MIDI48 because `program.add_step_transpose_trig_lock` clamps to -7. The candidate changes that clamp to -12..+12, adds a 25-value native behavior case and a focused unit regression.

Challenge these points:

1. Does the manual/UI/source evidence justify -12..+12 for step locks, including endpoint behavior?
2. Is changing only the model clamp the smallest correct production fix, without changing global or scale transpose semantics?
3. Does M-TRANS-001 genuinely exercise user-like held-step input for every value, distinguish explicit zero from absence, assert literal pitches and note timing, and prove K2 restoration?
4. Are the unit regression and retained controlled/real-time evidence adequate for this scoped defect?
5. Are any false positives, stale-state paths, pitch-accounting mistakes, or material regressions left in the scoped slice?

Return ACCEPTED or CHANGES REQUIRED with findings ordered by severity. This review concerns the scoped full-range defect only; it must not claim the broader transpose interaction domain or manual campaign complete.
