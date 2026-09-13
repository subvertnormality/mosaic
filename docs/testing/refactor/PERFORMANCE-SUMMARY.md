# Refactor performance: delivered changes and experiments

Updated2026-09-13. The structural refactor is largely implemented. Performance
investigation is now paused after the current overload experiment, per user
priority: finish the refactor. This report does not declare final acceptance or
physical-norns equivalence. Timings below are scoped to their actual workloads.

## Shipped Mosaic changes

| Change | Demonstrated benefit and limits | Detailed evidence |
|---|---|---|
| Slide ownership index | Replaces scans of up to1023 execution-ring slots with direct ownership lookup. Preserves ordering/retirement; no isolated whole-app speedup claimed. | [Slide lookup](slide-ownership-lookup.md) |
| Linear effective-length resolver | Long-note complete merges improved2-13%; dense-short samples ranged0.978-1.006x. Keeps sorted accumulation and musical results. | [Pattern rebuilds](pattern-rebuild-measurements.md) |
| Targeted dirty rebuilds and request-local source reuse | Rebuilds affected consumers and checks publication ownership. Actual cache implementation measured1.078x dense16-source and1.277x sustained16-source speedups; cache bounded to16sources per request. | [Pattern rebuilds](pattern-rebuild-measurements.md) |
| Stock parameter callback reuse | Five alternating helper benchmarks:37.1% lower CPU and about280fewer allocated bytes/call. Native pairs preserved output but did not establish a timing improvement. Commit3dc742b. | [Stock parameter cost](stock-parameter-cost.md) |
| External transport Start preparation | Removes a forced full collection from immediate restart and reuses the clean reset lattice instead of rebuilding 37 sprockets twice. Five real-time repeated-Start runs passed the unchanged 10 ms bound with 3.429 ms maximum phase; controlled repeat passed 3/3. | [R14 qualification](R14-qualification.md) |
| Clearer ownership and bounded history | Project lifecycle, history ring, musical resolution, playback lifetime, device descriptors/slots/output, and page controls now have explicit module boundaries. This is maintainability work, not a percentage speedup. | Respective refactor receipts |

Existing unit/integration and targeted native cases validate these changes; the
final combined qualification remains outstanding. Do not add percentages across
benchmarks or apply helper speedups to the whole sequencer.

## Rejected or unpromoted work

- FIFO scale-cache replacement:8.8% slower on cyclic240-key workloads despite a
 10.3% gain on a small hot set with scans. Not shipped; existing policy retained.
 See [quantisation cache](quantisation-cache.md).
- Startup first-sync hypothesis: deterministic model skips a pulse when initial
 callback work crosses its first deadline, but the targeted native sparse/dense
 trace did not reproduce the defect. No Mosaic clock fix made.
- Native norns skipped-tick accounting candidate: isolated image2ca1cdab retains
 musical position after skipped deadlines. Not promoted; upstream hardware/PR
 obligations remain separate. It does not itself fix JACK clock-domain shifts.
- Generic ACK-only actions and exported-display observations remove avoidable
 observer work.118generic contracts plus native grid/display checks pass on the
 isolated emulator branch. Not a Mosaic change or promoted default runtime.
- No global replacement of JACK frame time with wall time: audio/softcut semantics
 would need separate justification and validation.

## Representative constrained results

The established diagnostic container uses50% of one CPU and768MiB memory. It is a
resource proxy, not a calibrated physical norns. Unless explicitly noted, the
CPU quota period is100ms. Failed original runs remain evidence.

| Workload | Result | Evidence directory under mosaic-behaviour-runs |
|---|---|---|
| Dense notes,1/4/8/16channels |11/12runs passed; one8-channel timing failure | r13-6735b9e-perf002-run1 |
| Dense slides | Subsequent16-channel runs preserved784notes and48slide cycles, but several timing results remained above10ms. Initial routing failures did not reproduce in targeted runs; no speculative device fix. | r13-a02fed8-perf003-acks1; stock-parameter-cost.md |
| Rendering with full snapshots |45steps; p99628ms; substantial container throttling. Observer cost confounds app attribution. | r13-render-pressure-01 |
| Rendering with exported display |49steps,784balanced notes,48slide cycles; p9911.377ms failed10ms; no playback throttling. CPU1.273s. Not a calibrated cross-run speedup. | r13-render-pressure-display-01 |
| Ten-minute two-route song | Exact balanced streams, but persistent~84ms phase jump; timing failed. No same-run clock trace establishes its cause. | b68ed9c99b524b329f4233c7ee4d4d6b |
| Ten edit/autosave/restart cycles | Controlled-time functional pass; no storage-speed claim. |3432662804724ab185861a00c125a60b |
| Normal-storage save/load | Existing named-save recipe passed in98.594s; CPU8.349s, peakRSS399216640B,42.572ms throttling. No continuous timing or slow-storage oracle added. | r13-storage-normal-01 |

## Completed quota-period experiment

A generic320-event probe, with Mosaic absent, distinguished native tick loss
from a persistent JACK-to-monotonic offset. After1.5s of four-worker shared-quota
load, MIDI/JACK remained~10.6ms displaced30seconds later. Exact events survived;
JACK logged xruns. Separate same-core worker quota avoided container throttling
and left~0.76ms relative phase shift. This is diagnostic separation, not a
replacement workload or proof of device equivalence.

Changing only quota granularity from50ms/100ms to5ms/10ms keeps the50%CPU budget
but avoids long forced pauses of the whole audio/runtime process group. Two
generic repeats had no native clock skips or JACK xruns and sub0.5ms recovery
median displacement. The second retains asserted actual limits. No JACK or
Mosaic code changed for this experiment.

The existing Mosaic16-channel PERF-008 then passed unchanged under this
**diagnostic-only** short-period profile and isolated native recovery image:
51onset groups,1634MIDI messages, correct absolute event positions/releases,
visible grid/screen recovery, post-recovery p99/max0.874ms and final0.607ms.
It still recorded785.093ms of CPU throttling across158periods. PeakRSS418193408B.
This is recovery timing, not a claim that every event during deliberate overload
met10ms. Evidence: `r13-perf008-short-quota-01/diagnostic-report.json`.

The wrapper marks the profile diagnostic even though the reused inner test report
has its original `diagnostic_only=false` (that inner flag denotes native tracing).
Interpret the outer report. Default profile/runtime and thresholds are unchanged.
The current experiment is finished; no further performance tuning is scheduled
before final structural cleanup. Profile promotion is a separate explicit decision,
not a way to erase the original100ms-profile failures.

## Remaining and priority

Finish bounded R14 structural cleanup and final source-frozen validation next.
Keep unresolved performance, omitted required profiles/lanes and runtime issues
visible in the final report; do not call them green. Slow-storage faults, fuller
mixed sustained pressure and default runtime/profile promotion are not established
by the partial measurements above. Do not expand them into new campaigns before
finishing the refactor. The already-requested UI test abstraction follows the
code-refactor handoff as its own test-side phase.
