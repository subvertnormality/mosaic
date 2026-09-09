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

## Overnight autonomy and SEM-007 arbitration

The latest user requests continued delivery to completion, Paranoia arbitration
for decisions, no escalation, and standing approval for usual tool calls.
The installed arbitrate interface uses Codex and Claude. SEM-007 was submitted
with two neutral options and pinned repository evidence; the default Claude
model hit its usage limit and the tool returned FAILED, with no selection.
A supported alternative-model retry was rejected by automatic approval review,
which cited the earlier Codex-only restriction on external repository context.
The authorization-evidence reconsideration was also rejected. Do not work around
that denial or represent a single-provider query as arbitration. SEM-007 remains
pending; no semantic choice or implementation change follows from a failed tool.
Continue independent work. Raw failed arbitration and approval-rejection summary
are referenced in state.json; ordinary planned reviews remain Codex-only.

## Velocity-page numeric correction

The manual's first velocity-page lower value was 67; it is 68. The existing 14-value
mapping evenly divides 127..0 and floors each value: the seventh value is
floor(127 - 6*127/13) =68. M-EDIT-002 confirms every displayed value, including 68,
through actual grid input and emitted MIDI in both clock modes. Corrected the
one-number documentation error and reconciled its exact inventory source hashes.
No velocity behavior or test oracle changed. The preceding native run identities
retain the pre-correction manual hash; they prove the same unchanged implementation,
not a fresh run against the edited documentation. Full campaign acceptance remains
pending and will bind the final manual. No coverage requirement was removed.

## Arp timing and replacement (2026-09-08)

Codex decision01a07f21-248b-7013-99e8-ee8dd26fe412 establishes a full initial
zero-spread interval, individual onset-relative releases capped by the root
gate, and generation-local replacement ownership. README now gives the concrete
half-step/two-step example and explains preserved tails and Stop. Native tests
cover ordinary, fractional-final-gate, replacement, reset overlap and one-pulse
boundary cases. This does not establish complete arp coverage. Nonzero spread
and acceleration recurrence still require a separate documented decision and
finite-domain/interaction tests; existing implementation is preserved there.

## Spread/acceleration target contract (2026-09-08)

Codex arbitration01a07f50-06ce-76f2-86f5-76414bd23074 chooses
gap_k=d+s*(1+(k-1)*a), in channel steps, with off a=0. The first gap is d+s;
every later gap changes by s*a. Rest slots consume ordinals, including trailing
slots; a new trigger resets acceleration, an arp wrap does not. A nonpositive
next gap ends scheduling without a final collapsed note. Existing releases,
replacement ownership, Stop and live scale evaluation remain mandatory.

This is an intentional semantic amendment, not historical compatibility.
Full ascending+1 strums retain their old spacing. Off, other signed values,
nonzero arp startup and trailing-empty-slot behavior change. The documented
no-mask ratchet remains a one-root-slot special case; all-empty muted arps
are silent and bounded. README now describes the target before implementation.
Baseline tests must retain current outputs and distinguish a new-contract pass
from a compatibility control. No nonzero implementation has changed yet.

## Spacing/rest implementation checkpoint

The earlier target-only statement is historical: candidates0037/0039/0038 now
implement the recurrence and arp rest semantics. A positive arp gap occupies
at least one scheduler pulse after swing; clamping before rounding/carry avoids
zero-length cycles without inventing an extra onset at a nonpositive nominal gap.
Codex reviews and source-bound evidence are in spacing-rest-validation.json.
Strum shape/rest combinations and full timing acceptance remain pending.

## Panic and transport

Codex arbitration 01a080f4-f7fd-7b00-b1ed-73d95c9d081e: preserve existing panic as an all-note/all-channel Note Off sweep, with transport and scheduled voices continuing. The manual's earlier “stop signal” wording was ambiguous; Play/Stop is the separate transport control. M-PANIC-007 through010 verify the musical schedule, complete sweep and transport-message boundaries. Hot reconnect remains pending emulator support.

## SEM-009 — Quantised Fixed Note uses an absolute MIDI pitch

Codex arbitration `01a083c2-e074-7af0-ad2a-4cf60ee1eac3` inspected history:
`6f1fa13` introduced degree indexing; `0d4e23d` explicitly changed to pitch
snapping in 2024 while leaving the manual wording stale. Preserve that established
contract, without repitching saved projects or migrating their numeric values.
Use nearest legal scale pitch with lower ties, configured root and root fallback;
ordinary root voice only. Octave/transpose/degree/rotation/pentatonic switches do
not modify this override. Fixed Note wins. An Off step lock inherits the channel
value; Off is not a muted trig. Separate chord/arp paths require their own tests.

The proposed upper-bound correction filters scale candidates to MIDI0..127,
rather than emitting128 or clamping to an out-of-scale pitch. M-PARAM-014 reproduced raw128 before candidate0069; the unchanged oracle now
passes both native lanes. See quantised-fixed-validation.json for scoped evidence.
Independent native expectations are literal musical tables, not recorded output.
Review: `reviews/quantised-fixed-semantics-review.json`. Broader precedence,
modulation, held locks and lifecycle tests remain required. Manual update follows
the boundary reproduction/fix so it can distinguish established from corrected behavior.


SEM-009 oracle correction: the review's D-major input127 ->126 example was
arithmetically wrong. MIDI127 is G (pitch class7), the fourth of D major:
D/E/F#/G/A/B/C# = pitch classes2/4/6/7/9/11/1. Therefore127 stays127.
The independent 15,360-case interval test already required this. Native failure
`294a062779374590890cba69531739eb` is retained as a test-table defect, not a
Mosaic defect. Only this literal expectation changes; no timing tolerance changes.
The A harmonic-minor malformed128 baseline and candidate0069 remain valid.


## SEM-010 — Parameter recording boundaries

Codex review01a08404-8475-7c82-be93-02d19cf99aa6 inspected history726b0d29
and confirmed future-step recording and selected-channel-wrap clearing predate
this fix. Editing records only edited parameters on subsequent eligible selected
channel steps; it does not rewrite a step that already sounded. Clarify the manual
rather than change that behavior. The note first-press/final-release decision is
separate. Stop/disarm clears pending parameter recording. Switch-away/return,
retained dirty values, wrap/restart, trigless, slide and persistence need further
native coverage and are not certified by candidate0070.

Review accepted the narrow guard. Its channel/slot/disarm test uses a fake
recorder and proves suppression policy, not clock-driven switch recording.
Strengthen native replay by changing default64 to65 before playback: continued64
on steps2..4 must then be stored locks. Preserve all failed baseline artifacts.
