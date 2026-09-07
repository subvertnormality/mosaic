# Campaign progress

2026-09-07: requested Paranoia plan critique plus focused follow-up returned and
were triaged. User confirms browser manual derives from repository docs; README
and cheat sheet hashes bind the inventory. No independent browser-source gate.

The Mosaic-owned runner boots this actual worktree through the generic emulator
Session API, drives real grid/keys/encoders, and records native screen/grid/MIDI
and cleanup evidence. Two initial cases are implemented. Pattern editing passed
on the baseline. The length collision case failed at approximately0.665 seconds
against an independent2-step expectation of0.333 seconds at90BPM, despite the grid
showing the shorter duration. The isolated pattern merge correction makes the
unchanged case pass; the unchanged editing case still passes. All474 upstream
units pass on baseline and corrected isolated copies with pinned runtime Lua and
a failing curl guard. Exact artifact paths and digests are in bugs.json.

The correction computes effective source-pattern lengths at the next source trig
without destroying the stored editing length; merge modes consume those lengths.
Tests for wrap/restoration/merge/mask interactions still need implementation.

Coverage remains incomplete:113 README headings plus the cheat sheet are indexed,
but only two requirements have partial-domain executable coverage. --require-all
fails explicitly. Controlled time has an inspected adapter design, no admitted
runtime implementation yet. T00/T01/T02 remain unfinished; no refactor starts.

## Continuation: length boundaries and repeated-pitch releases

Codex is the only permitted engine for future Paranoia reviews. No new review
checkpoint has been claimed in this continuation.

M-LEN-002 now verifies collision deletion/restoration/reinsertion with exact LEDs
and MIDI durations. M-LEN-003 verifies truncation across step64 using distinct
pitches over three complete64-step loops. The original same-pitch version failed
the stop/drain oracle and is retained as M-MIDI-001. Raw native emissions show
7 Note Ons but only4 Note Offs on the failing baseline; the minimal m_midi.lua
correction emits a release for each note lifetime and produces7/7. Both wrapped
duration cases, restoration and ordinary editing pass with both fixes applied.
All474 existing units pass on baseline and combined corrected isolated copies.
Exact manifests, digests and event counts are in bugs.json.

Five named Mosaic-owned cases now exist (M-LEN-001 is also executed inside the
restoration case). This remains partial coverage, not an exhaustive suite. The
emulator's isolated C scheduler seam passes original-versus-candidate boundary
checks, but controlled-time runtime integration and Codex P5 remain unfinished.
Next: coherent native time/internal clock/metro/event draining, complete atomic
manual reconciliation, runner fault probes and remaining workflow families.


## Experimental controlled-time diagnostics

The public Session candidate now runs the actual Mosaic worktree with controlled
time. This is explicitly unadmitted diagnostic evidence, pending C16/P5. Native
trace verification includes advances and logical-timestamp MIDI packets; normal
real-time mode remains the default. The four-note editing workflow passes in D.
The length case fails on its first note:328611113ns observed versus one third of
a second expected. Later notes agree within1ns. Both affected real-time cases
still pass, so the existing10ms jitter allowance hid this opening-interval issue.
All four source-bound manifests and digests are recorded under transport-start-phase
in bugs.json. No new Mosaic production-code fix has been applied.

A separate generic emulator probe (b7c813e19b8742bfa169161a0bd26dce) confirms
absolute clock.sync phase behaviour from independent120BPM calculations: notes
started at1ms/504ms end at250000001ns/750000001ns after48 native96PPQN syncs.
Mosaic's auto_pulse emits immediately then syncs to the absolute grid. This
supports a startup-phase diagnosis, not complete transport correctness or D
admission. Next: phase-swept transport start/restart, tempo/reset/external clock
contracts, mod/time-source audit and bounded Codex P5. Keep the failing duration
oracle; do not capture this shortened first note as a musical golden.
