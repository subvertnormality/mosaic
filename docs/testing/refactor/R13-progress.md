# R13 progress — 2026-09-13

Status: in progress; refactor and emulator release acceptance are not complete.
Production Mosaic remains at the R12 structural result. Subsequent changes have
improved diagnostic retention and corrected two performance-test oracles.

## Measured outcomes

Evidence paths below are relative to `/home/andy/projects/mosaic-behaviour-runs`.

- `r13-6735b9e-perf004-run1`: constrained interactive input passed once.
- `r13-6735b9e-perf002-run1`: 11/12 dense-note runs passed; 8-channel repeat1
  exceeded timing. No measured sustained channel-scaling bottleneck was found.
- `r13-6735b9e-perf003-run1`: 1/4/8-channel slide runs passed; all three
  16-channel runs failed correctness/runtime checks. One duplicated MIDI16 and
  omitted MIDI9; another omitted MIDI12. A selector-refresh race is unproven:
  normal driver pacing exceeds the usual refresh duration. Do not fix on suspicion.
- `r13-6735b9e-perf003-diagnostic1`: all16 channels and48 slide cycles correct;
  p99 timing13.033ms failed. Evidence now survives failed assertions.
- `r13-14e57fe-perf008-run1`: overload lost roughly three steps of musical
  position. Short-term recovery timing alone masked that displacement.
- `r13-e28234b-perf008-trace1`: native clock skips accounted for722ms of744ms
  persistent lag. Complete observation-only trace retained.

## Confirmed test corrections

`ca5bb99` corrects M-TIM-005's forced-overlap oracle: only the deliberately blocked
onset is assessed from native stall completion; every other note retains its
original timeline and10ms bound. Native run25497ea108aa47deb4b9a1a1439f09f4 passed.

`1eea997` closes a demonstrated false pass in PERF-008: a repeating four-note
fingerprint could hide an entire lost cycle. Recovery now checks absolute emitted
position as well as pitch. Four oracle unit tests pass. Both retained overload
runs also fail position when replayed through the corrected oracle; originals
remain unchanged.

## Isolated native-clock candidate — not default runtime

Worktree `/home/andy/projects/monome-emulator-native-clock-recovery`, commit
`72e2ece69323339ec29a76ea6a7614397a51a3b6`. Patch0015 advances the native tick
counter by the same skipped-deadline count as the scheduling cursor. It does not
change Mosaic. The original real C loop fails the beat invariant; candidate
N2/N4/threshold/tempo/restart tests pass. Full patch-stack application and five
focused generic checks pass.

Image `sha256:2ca1cdab86408a261ba25b7bf584df35472798e0bddccde5d8b5636ace5e914e`.
Receipt: `native-clock-recovery-193963d/receipt.json`.

`r13-1eea997-perf008-recovery1` and `...-recovery-untraced1` preserve musical
position and note ownership but still fail timing at24–28ms. Tracing is not
necessary for the residual. The traced JACK-to-monotonic offset shifts25.639ms;
local clock-domain shifts explain recovered MIDI errors within0.8ms. Underlying
JACK behavior remains to diagnose; do not relax the wall-clock oracle or claim
hardware equivalence. Comparison: `native-clock-recovery-comparison.json`.

## Next work

1. Generic-only clock reproduction completed: see findings below. Retain the
   remaining runtime timing failure; no default clock-domain substitution.
2. Resolve or precisely isolate the16-channel configuration/output failure with
   retained input/output evidence. No speculative Mosaic fix.
3. Complete remaining planned R13 performance matrix, endurance, lifecycle and
   history checks. Reuse existing coverage; optimize only measured bottlenecks.
4. R14 final cleanup and the single final required lane/profile sweep after
   implementation is stable. Preserve failures and source identities.
5. Complete the separately authorized UI abstraction plan after refactor acceptance.

Do not promote the experimental clock candidate or treat these measurements as
whole-refactor acceptance. Emulator delivery/release obligations remain separate.

## Latest retained diagnostics

`r13-a02fed8-perf003-acks1` completed on the original baseline runtime. All16
channels,784 note-ons and48 slide cycles passed correctness checks. Timing remains
red: p99 13.112ms, maximum18.220ms, final phase10.622ms; no workload throttling.
All3780 recipe inputs have retained action acknowledgements. Acknowledgements
confirm application, not the selected parameter or device state; this run does
not establish why the earlier routing failures happened. Two diagnostic runs
have now failed to reproduce those routing failures. No device fix is justified
by that evidence alone.

`generic-clock-domain-20260913-061739-a371a515` reproduced the clock-domain
shift without Mosaic:64 CC messages,2686 native trace records; wall/JACK median
offset shifted11.239ms and CC residual shifted12.031ms. This is diagnostic
evidence, not passing timing acceptance. The earlier generic run without retained
trace is incomplete. A global wall-clock replacement is not being promoted: it
could decouple MIDI timing from audio/softcut.

## Device/parameter lifecycle audit follow-up

At df3e0bf, existing controlled behaviour M-PATCH-047 passed: removing the middle
assignment during ten active slides stops that CC while preserving nine curves
and note timing. Manifest: `84cdf35bda2b4b0fa4ce6f66d7668835/manifest.json`.
This is a focused lifetime regression, not full device-switch qualification.

Review findings must be reconciled with `suspected-defects.md`: S5 (hidden Slew)
was explicitly rejected as a defect by the user; preserve that decision. S3
(Braids leading-none slot mismatch) is already recorded as unvalidated, and its
unit characterisation does not satisfy the two-lane behaviour baseline requirement.
Do not flip either test merely because an audit calls the current code defective.
S55 (directory discovery) and S56 (hidden parameter values) are existing approved
refactor follow-ups; check their implementation and existing coverage next.
