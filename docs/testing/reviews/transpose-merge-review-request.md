# Transpose, merge and scale-lock interaction review

Use Codex only. Read-only local shell commands are allowed; do not edit files or launch tests or runtime processes.

Review M-TRANS-004 in `/home/andy/projects/mosaic-behaviour-tests` and its evidence in `docs/testing/transpose-merge-validation.json`.

Challenge the user recipe, independent arithmetic and complete MIDI oracle. The case authors two pattern degree streams, selects All trig merge and Average note merge, fixes velocity ownership to pattern1, edits scale slot2 to D natural minor/root D/transpose+3, shortens the independent global scale track to four steps, places its scale lock at step3, and authors step transpose locks -12/zero/+12. It expects three complete repetitions of MIDI pitches 50/65/85/82 with original velocities, owned one-step releases and one-sixth-second phase.

Check especially that the UI controls actually select the claimed modes, the averaging formula and scale-degree tables are independent and correct, scale and transpose persistence/reset points are genuinely exercised, every output is accounted for, and the adjacent M-MERGE-009/M-SCALE-002 reruns are relevant. The first failed recipe is described honestly but is not positive evidence.

Return ACCEPTED or CHANGES REQUIRED with findings ordered by severity. Do not broaden this checkpoint to other merge modes or remaining transpose/manual requirements.
