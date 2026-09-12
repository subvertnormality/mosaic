# M-ENDURANCE-001 real-time phase diagnosis

This note analyses the retained failed real-time run
`/home/andy/projects/mosaic-behaviour-runs/h15-endurance-realtime-eb25847/a355e2a8e8684e12b120ba35dbcb47ea`.
It is host/runtime attribution evidence, not physical-norns equivalence.

## Independent schedule and first observable discontinuity

The typical-workflow song is 120 BPM, with port 1 on every quarter-step
(125 ms) and port 2 on alternate steps (250 ms). The oracle derives both
schedules from `composition_workflow.expected_stream`, rather than reading
Mosaic state.

The first error over 5 ms is one shared event time:

| Port | First affected onset | Relative time | Phase step |
| --- | --- | ---: | ---: |
| 1 | native MIDI index 7091, `[144,69,107]` | 126.291921924 s | +41.160211 ms |
| 2 | native MIDI index 7089, `[145,76,90]` | 126.291887 s | +41.188728 ms |

Both remain roughly 42 ms late through the final phrase. The port-1 failure
is cycle 126, song slot 1, step 3: it is not a song boundary. The immediately
preceding port-1 onset is index 7084 at `289097454110602`; the affected shared
clock batch starts with port-3 transport output at index 7085,
`289097619695523`, then port 2, the old port-1 release, and port 1 index 7091.

There are no input actions during this interval, no injected `runtime_stall`,
and no receiver backlog: the affected note reached the native event reader
38 microseconds after its native timestamp, with a 4.8 microsecond reader-lock
wait. Frame/grid updates continue between the prior onset and the late batch.
The evidence therefore excludes MIDI-device delivery, user input, event-log
drain, and a complete native-process stop. It identifies a delayed shared
internal-clock resume/pulse as the first observable causal event, but does not
identify why the pinned norns scheduler/host missed it.

The apparent 3.327-second port-2 offset is not an endurance transport fault.
It is the recorded setup note at native MIDI index 11. The endurance marker is
12, so the actual oracle excludes it (`index > marker`) before comparing
playback output.

## Deterministic attribution guard

`M-TIM-005` uses the generic runtime-stall candidate to block only the Lua
event thread for 42 ms while the same internal 120 BPM song plays. It is
separate from `M-SYNC-023`, which tests external-MIDI Stop pre-emption after a
one-second backlog. The new case passed at
`/home/andy/projects/mosaic-behaviour-runs/3eba6ff5921340e1a2e4a4c9e5fc25f2`:
a 45.319052 ms stall had a 1.570304 ms maximum port-1 phase error, below the
unchanged 10 ms musical bound. A Lua event-thread backlog therefore does not
reproduce the retained persistent phase shift.

## Comparison with PERF-004 input-pressure failures

The similar 40--50 ms magnitudes have different causal boundaries. A
deterministic trace join pairs each PERF-004 note with the scheduled external
MIDI clock pulse at the same independently declared deadline. In retained run
07, its only late note was 49.556 ms late and its trigger was 48.884 ms late
(0.671 ms residual). In retained run 08, all seven late notes had late triggers;
the output-minus-trigger residual stayed between -2.888 and 2.366 ms. Run 06
had no note over 10 ms.

A fresh source-bound run at
`/home/andy/projects/mosaic-behaviour-runs/timing-spike-isolation-perf-03`
retained the diagnostic even though the unchanged performance gate failed.
All three late notes followed late external-clock deliveries within 10 ms and
all three deliveries were within 2.9 ms of an observed cgroup throttle-counter
edge. The 0.5-CPU container accumulated 22 throttled periods and the note p99
was 12.229 ms. An earlier diagnostic run 02 had eight late notes; all eight
trigger deliveries were within 4.1 ms of throttle-counter edges, while
Mosaic's residual processing delay stayed within 5.312 ms.

PERF-004 therefore remains a valid constrained end-to-end failure, but its
retained misses are late external-clock delivery under cgroup pressure rather
than evidence that Mosaic computed a timely pulse late. The new oracle stores
the input/output join, cgroup correlation, recorder samples and timing vectors
before enforcing the gate so future failures cannot discard attribution data.

The endurance discontinuity instead begins in the common port-3 program-change
batch before the port-1 and port-2 notes. Relative to the first playback batch,
that stream's first >5 ms error is native index 7085 at 126.291815 s. Its phase
then remains 41.635--44.521 ms late for every one of the remaining 3,801 steps,
including after ordinary screen and grid work. The last transport press was
126.291 seconds before the jump, so the discontinuity is also 6.291 seconds
after the second 60-second while-playing autosave check; it is not coincident
with that timer boundary. Together with M-TIM-005, this excludes the observed
PERF-004 input-throttling mechanism, a generic Lua backlog, and the autosave
timer as explanations for the persistent shift. It does not yet distinguish a
host/JACK time discontinuity from the pinned native clock scheduler's sync
deadline/resume behavior.

## Next target

Do not change Mosaic from this evidence. Instrument the pinned runtime's
`EVENT_CLOCK_RESUME` path and the clock scheduler around each sync deadline:
record scheduled beat/time, scheduler-post time, Lua-resume time, and the next
rescheduled deadline. Re-run the real-time endurance workload on an otherwise
idle WSL host. That distinguishes a late scheduler poll, delayed event-loop
dispatch, and a phase-rebasing bug; only a reproducible runtime finding can
justify an emulator/runtime candidate change.
