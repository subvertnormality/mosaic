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

## Priority correction: Mosaic playback cost attribution

The user clarified that reducing Mosaic load is the performance objective. Native
clock accounting and residual JACK timing remain separate runtime findings; the
isolated clock fix is not a physical-norns or external-sync fix. Existing aggregate
timing measurements do not identify a measured Mosaic function hotspot. Next run
collects function CPU/call attribution on the dense-slide workload, followed by an
uninstrumented matched comparison for any selected optimization. Instrumented
timing is diagnostic only; overlapping inclusive costs must not be summed.

Diagnostic worktree: `/home/andy/projects/mosaic-profile-r13`, branch
`codex/r13-cost-profile`, based on839762a. No profiler instrumentation belongs in
production by default.

S55 is retained on local-only `codex/s55-discovery-candidate` at aab67ac, with both
lane passes, three controlled repeats,1546 units and custom-device collateral.
It is not accepted/merged: the old native S7 fixture depends on the listing bug.
The active midi-clock runtime lacks the proposed dataset-reopen API, and an
unverified newer runtime must not be substituted. This fixture dependency must
be resolved before S55 is merged; it does not block playback profiling.

## Stock parameter allocation optimization

3dc742b reuses resolver callbacks with explicit channel/step context and removes
redundant ID formatting. All1546 Lua units,6guards and M-PARAM-036 in both lanes
pass. Five alternating bridge benchmarks show37.1% lower CPU and about280 fewer
allocated bytes/call. Two native pairs show correct output and lower candidate
CPU; timing remains red on both candidate runs and one unchanged baseline run.
Retain as allocation/CPU reduction, not a timing fix. Details and exact evidence:
`stock-parameter-cost.md`. Full R13/R14 acceptance remains incomplete.

## Ten-minute endurance on9b61826

M-ENDURANCE-001 real-time failed: `b68ed9c99b524b329f4233c7ee4d4d6b/manifest.json`.
Port1 p99=85.372ms, maximum86.813ms, final84.202ms. The original assertion
stopped reporting at port1; retained-export analysis in the same run's
`two-port-timing-analysis.json` verifies both sequences and balanced releases
(4812/4812 and2406/2406). Port2 p99=85.524ms and final83.980ms. Both ports
show one roughly84ms phase jump at43.084seconds; no subsequent accumulating
lag of similar size. This is consistent with, but does not attribute the run to,
the previously identified native clock accounting issue: this run has no native
clock trace. Timing acceptance remains failed, with thresholds unchanged.

## Repeated lifecycle validation on e61c18b

M-LIFECYCLE-001 passed in the controlled-experimental lane:
`3432662804724ab185861a00c125a60b/manifest.json`. All manifest artifact hashes
were verified. Ten edit/autosave/shutdown/restart cycles restored cumulative
global transpose, with exact MIDI phrases checked before and after every restart.
This is functional persistence/lifecycle evidence; the manifest marks the lane
diagnostic-only, and this is not constrained storage-performance or real-time
timing acceptance. PERF-005 rendering-pressure evidence is next, reusing the
existing dense-slide setup and unchanged musical oracle.

## Rendering-pressure diagnostic

`r13-render-pressure-01` on e61c18b plus retained test-only patch delivered all
30 UI gestures (54 acknowledged physical events) inside8.0004seconds, alongside
16-channel slides. The unchanged step-count check failed:45steps versus48
expected (tolerance2). All720 note-ons had matching releases and correct channel,
pitch and velocity;32 complete slide cycles passed. Retained MIDI/resource
analysis reports p99 628.173ms, final624.531ms and870.197ms of playback-window
CPU throttling. This is a failed constrained run, not hardware evidence.

The recipe also requests60 full snapshots during playback. Their observer cost
is not yet isolated from Mosaic rendering cost. A same-gesture comparison without
per-gesture snapshots completed at `r13-render-pressure-no-observer-01`; setup
and final snapshots remain. Do not attribute the failure to Mosaic alone or
claim full PERF-005 coverage from this partial rendering-pressure recipe.

The action-only comparison delivered all30 gestures/54 events,49 steps,784
note-ons with matching releases and48 complete slide cycles. No CPU throttling
was recorded. P99 timing11.188ms still fails the unchanged10ms bound; maximum
12.866ms and final8.357ms. CPU was1.422seconds versus2.997seconds with snapshots.
Host load differed materially (action-only7.03/4.84/2.89 at start versus
0.81/0.87/1.19), so this is diagnostic separation, not a calibrated performance
improvement claim. The large collapse did not recur without explicit snapshots.

Source inspection confirms each snapshot builds and serializes full growing MIDI
history and framebuffer in the same CPU-limited container. The action path also
builds full state internally before returning only its ACK. Keep these emulator
costs separate from Mosaic cost. No runtime or Mosaic production fix was made.
The test-only runner now exposes both observation modes, retains setup/final
snapshots, and preserves calculated metrics even if the step-count check fails.

## Display-only rendering-pressure result

`r13-render-pressure-display-01` uses the isolated generic display endpoint in
imagefeab2bb7 (full digest and exact patch in `ack-only-candidate/build-display/`).
Full snapshots remain before/after playback. All30 gestures,54 action ACKs and
60 display reads completed;49steps,784balanced notes and48complete slide cycles
passed. No playback CPU throttling. P99 11.377ms still fails10ms; max13.711ms,
final9.764ms. CPU1.273seconds, peakRSS545792000bytes. Host start load3.34/4.16/5.36.
The authorized R10 archive-folder removal completed132.8seconds before the timed
playback began; it did not overlap that window. This is one diagnostic run, not
a matched speedup claim or passing timing acceptance.

The display endpoint samples already-exported frame/grid without native type5
Lua diagnostics.118generic contracts and native grid/display checks pass in the
isolated emulator candidate; default runtime promotion remains separate. The
runner keeps full-snapshot and no-observation modes to retain the comparison.
No Mosaic production code or musical oracle changed.

## First sync registration diagnostic

On ba46a50, retained `startup-sync-registration-probe/{probe.lua,output.txt,receipt.json}`
runs actual `Lattice.auto_pulse` against the official scheduler boundary formula.
With first callback cost0 or0.5pulse intervals, observed pulse positions are0,1,2,3.
With cost1.073246544intervals they are0,2,3,4; with cost2.1 they are0,3,4,5.
This confirms an application first-registration mechanism in a deterministic
model, not a native behaviour reproduction or physical hardware claim. Later
sync registrations advance from the stored scheduler deadline; this is distinct
from the native internal-clock deadline-skip issue.

The retained display-pressure run has first-group service7.453101ms, exceeding
the90BPM/96PPQN interval6.944444ms, and later first-onset median phase error
7.444077ms. Those MIDI measurements do not measure the entire Lua callback or
exclude a concurrent native clock-source skip. Production remains unchanged.
Next: reuse generic opt-in clock-phase tracing with a minimal real-input startup
recipe to separate these causes. Controlled logical time does not charge Lua CPU
cost; do not claim this wall-time stimulus reproduces there or waive the standing
pre-fix baseline requirement implicitly. Existing M-TIM-005 covers a mid-run
stall, not this first-registration boundary.

## Native startup trace: not reproduced

`startup-sync-native-trace-02/report.json` on719a247 records serial4second
1-channel and16-channel slide workloads in existing diagnostic image
`sha256:acd56af26785db16c5f54e03c7c5a11f5241187e40648afac224e4940d2f5eba`.
Both pass unchanged timing checks. Sparse:25notes, p990.606ms. Dense:400notes
with matching releases,16complete slide cycles, p996.614ms, max8.033ms,
final2.496ms. Both traces have contiguous ordinals and no internal clock skips
from20ms before first note through the last note. Dense first-group service
3.011ms is below the6.944ms pulse interval; median later first-onset error
0.556ms. The startup fault is **not reproduced** in this native diagnostic.
No Mosaic production correction is justified by this run. The deterministic
probe remains a mechanism demonstration; earlier rendering/endurance timing
failures are not cleared. Trace instrumentation and the different native image
preclude treating this as a matched comparison with the display-pressure run.

Raw exports, input ACKs, recipes, resource samples, image/runtime identity in
container logs and per-channel startup-analysis.json are retained with
evidence-hashes.json. Initial trace-01 setup failures were caused by a missing
host screen-oracle installation manifest; the separate diagnostic traceback
identified it. A second host choice lacked a performance helper and failed
before launch. Final wrapper uses performance-integration host helpers and a
font verified identical to the trace image. No application/runtime substitution
was made during a running case. Native runner is terminal; no active jobs remain.

Keep startup correction parked pending a causal native reproduction; do not
spend repeated full UI-setup runs chasing a non-reproduced hypothesis. Next
resume the remaining R13 performance coverage reconciliation, then the single
R14 qualification when the candidate is stable.
