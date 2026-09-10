# Final MIDI pitch-domain defect review

Use Codex only. Read-only local shell commands are allowed; do not edit files or launch tests/runtime processes.

Review the isolated M-TRANS-005 Mosaic defect fix and `docs/testing/midi-pitch-boundary-validation.json`. The physical recipe composes validated extreme Higher/Lower note merging with channel octave +/-2, saved scale transpose +/-12, a global scale lock and step transpose +/-12. Its independently derived unbounded phrases are 148/148/96/96 and -17/-17/0/0. MIDI must emit 127/127/96/96 and 0/0/0/0.

The exact c0e7c87 baseline with the finalized recipe fails because an out-of-range data byte corrupts the MIDI stream (`Status interrupted an incomplete message`). The candidate clamps note numbers in `m_midi.note_on` and `m_midi.note_off`, at the final MIDI-only boundary before ownership accounting and output. It intentionally does not alter non-MIDI `device.player` notes, NRPN/CC policies, merge arithmetic, quantiser values, or upstream norns.

Challenge whether clamping rather than wrapping/dropping is the correct musical/API behavior; whether the location covers ordinary, chord, arp and safety-release paths without stranded notes or regressions; whether onset/release collisions at 0/127 remain owned; whether the behavior arithmetic and UI controls are accurate; and whether every event and accumulated timing is actually checked. Verify source/manifests/artifact/log hashes and relevance of fresh M-TRANS-002, M-TRANS-004 and M-MERGE-016 adjacent runs.

Return ACCEPTED or CHANGES REQUIRED with findings ordered by severity. Keep the review scoped to this defect and its guards; remaining manual coverage stays pending.
