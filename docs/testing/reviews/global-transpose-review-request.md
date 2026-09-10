# Global transpose full-domain review

Use Codex only. Read-only local commands are allowed; do not edit or launch tests/runtime processes.

Review M-TRANS-006 and `docs/testing/global-transpose-validation.json`. The case selects -12 at the scale-page fader's left inner cell, then advances one value with each of 24 physical right-endpoint taps. For every displayed value it expects literal base MIDI 60/62/64/65 plus that semitone value. It runs at least two complete phrases in controlled and real time.

Challenge the physical fader mapping, whether this actually tests global rather than step transpose, all25 values and pitch arithmetic, the 9..10 real-time observation bound, complete onset/release/Stop ownership, duration and accumulated phase, program/transport classification and event-count identity. Check source/manifests/artifacts and that the retained failed strict oracle is described only as an oracle correction. Production is unchanged from accepted d18f3fc, whose checkpoint passes530 Lua and21 focused Python tests.

Return ACCEPTED or CHANGES REQUIRED with findings ordered by severity. Keep song persistence/live-edit and other pending domains out of this scoped verdict.
