# Behaviour decisions

User authorises dedicated worktree changes and pushing codex/behaviour-validation.
Real input / MIDI-grid-screen outputs are mandatory; controlled time is brought forward.

| ID | Question | Status / treatment |
|---|---|---|
| SEM-001 | Lower note/velocity/length merge formulas disagree or are ambiguous | User clarification previously requested; only dependent cases blocked |
| SEM-002 | Independent one-step channel selection gesture | Resolved 2026-09-07: user requires unsupported one-step selection; a lone long hold stays inactive so held-step combinations remain safe. Do not substitute global clamp |
| SEM-003 | Input MIDI channels beyond channel1 | Manual silent; source handles channel1; characterise before deciding support contract |
| MAN-001 | Source-header manual short link |Resolved 2026-09-07: user confirms browser page derives from repository documentation; README and cheat sheet remain mandatory |
| TIME-001 | Fractional note-off phase and rounding | Independent musical intent required; existing phase-minus-two observations are not correctness goldens |

REV-001 (2026-09-07): user requires Codex only for all future Paranoia reviews. Completed historical reviews remain valid; do not rerun just to change engines.

## Confirmed manual semantics (2026-09-07)

The user confirmed preserving current implementation for these three cases and
requested corresponding manual clarifications. These are intended behaviour
decisions from source inspection, not completed behaviour-test coverage.

- SEM-004: An explicit MIDI off lock sends nothing for that step; it does not
  resend the last lock or cancel an already-running slide.
- SEM-005: K1+press selects scale editing only. Long press selects a different
  editing slot, but long-pressing the already selected editing slot disables
  the global scale and clears editing selection.
- SEM-006: Channel scale persistence follows the hold-until-end option. With
  it off, only an active trig passing probability clears prior persistence.
  Global scale locks persist until replacement/global wrap independently.

README and cheat sheet now state these rules. Add their edge regressions during
full manual reconciliation; do not mark requirements complete from this edit.


SEM-007 (pending user clarification): K1+K3 currently redoes all history and then
clears the entire history while preserving the resulting music. K1+K2 undoes all
history and then clears it. The manual's “subsequent memory” wording is ambiguous.
The user has been asked whether to preserve these behaviors and clarify the
manual. Only these shifted-key expectations wait; ordinary navigation and
new-edit-after-undo behavior have native regression coverage.


SEM-008 resolved: the user explicitly chose to keep current-active-step recording.
A note targets the step active when its note-on is processed, not the nearest
step and not automatically the new step at a MIDI pulse's requested deadline.
The prior new-step hypothesis was never accepted. Native strict clock.sync and
serial event dispatch explain the original steps1/3 result. The synchronized
channel MIDI witness, complete phrase timing, native input delivery, full grid
and disarmed replay now pass before/on/after the pulse boundary in both modes.
Codex review and original failed manifests are retained in state.json and
reviews/boundary-oracle-triage.md. No Mosaic scheduling change was needed.
