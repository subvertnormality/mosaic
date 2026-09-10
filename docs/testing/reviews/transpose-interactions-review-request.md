# Transpose composition and live-clear review

Use Codex only. Read-only local shell commands are allowed; do not edit files or launch tests or runtime processes.

Review M-TRANS-002 and M-TRANS-003 in `/home/andy/projects/mosaic-behaviour-tests` as a scoped extension of the already accepted full-range transpose fix. Evidence is in `docs/testing/transpose-lock-validation.json`.

Challenge whether M-TRANS-002 independently and correctly computes the literal MIDI phrase for step locks -12, explicit zero and +12 (persistent through step4 and reset at wrap), saved scale transpose +3, overridden song transpose +4, and channel octave +1. Check that repeated wraps and release/timing assertions establish the claimed composition rather than merely mirroring implementation.

Challenge whether M-TRANS-003 really clears step1 during playback while step2 is sounding, proves that note's release ownership and one-step duration, observes global +4 at the next step1, retains step2's explicit-zero behavior, and checks complete MIDI accounting and phase. Look for race-prone waits, partial traces, ambiguous note matching, or stale capture.

Assess the retained 527-test performance-threshold failure and immediate 527/527 rerun honestly: decide whether it is a blocker for these Python-only behavior additions or an appropriately retained timing flake. Return ACCEPTED or CHANGES REQUIRED with findings ordered by severity. Do not claim the remaining transpose or manual domains complete.
