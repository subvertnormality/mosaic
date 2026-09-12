# R09 cooperative scheduler

## Preserved behavior

An update snapshots active IDs at the start of the pass and sorts them by increasing
ID. Each snapshot member gets one coroutine slice. Jobs started during the pass
wait for the next update. Completion and errors are retired after the pass; an
error is printed and does not prevent later jobs running. Compaction keeps IDs
unchanged and next IDs remain monotonic.

Cancellation during the pass does not recheck membership for a later snapshot
entry: that entry may still run once. This pre-existing behavior, including the
suspected double-decrement when cancellation and retirement overlap, is not fixed
by the extraction. A behavior-changing repair needs its own reproduced consequence.

## Snapshot and retirement extraction

`snapshot_active_ids` owns collection/order; `retire_snapshot_ids` owns retirement,
counts and compaction. `scheduler.update` retains dispatch/error policy. Existing
storage, callbacks, allocation reuse and public fields remain unchanged. This is
a structural change, not a measured performance improvement or cancellation fix.

All 1542 Lua tests pass (24.082 seconds); six guards pass. Existing tests pin start
order, one slice per pass, debounce replacement and error isolation. Native cases
pass with unchanged recipes and expected results:

| Case | Controlled | Real-time |
|---|---|---|
| M-PAT-BOUNDARY-001 | d1022301efa445fa807445d2b2945166 | Existing runtime limitation, not run |
| M-ALG-PAINT-RACE-001 | d2e39520619d48b4b331a94439842854 | f63730983e8042b5be053a740e845323 |

## Stable step-release refresh

The channel editor now reuses one module-local debouncer for memory, trig-lock,
mask and fader display refreshes. These callbacks read current selection when
executed. Every release still records its note-mask and trig-lock events and
requests its working-pattern rebuild individually, in the original order.
No musical event or history operation is coalesced.

The composed page/scheduler regression sends three releases before dispatch,
checks all six recorder calls and three rebuild requests, changes selection,
and checks one refresh of each display using the new selection. The first test
fixture collided with an existing local press helper; explicit global access
corrected that fixture isolation error. All 1543 Lua tests then passed (26.438s).
The six inventory/name/syntax guards pass.

Native regression receipts (unchanged production source throughout these runs):

| Case | Clock mode | Passing run |
|---|---|---|
| M-MEMORY-012 | real-time | c6a6bd52632a4afb89b6eb24e13735b9 |
| M-MEMORY-010 | real-time | 2deec6c4c8544bc5a7bea0407907e282 |
| M-MASK-031 | real-time | 9cfe4033dc0f4357a5e5df7f74075887 |
| M-MASK-030 | real-time | 0bac2185e3984f81b9c150ac9adcc960 |
| M-MEMORY-012 | controlled-experimental | d9a56f4667824d048d07144a95dc91cc |
| M-MEMORY-010 | controlled-experimental | 8e42b18ec4d6444e93be39b2cd77ca93 |
| M-MASK-031 | controlled-experimental | 24dc0d9241014a5783985974c43c5ab5 |
| M-MASK-030 | controlled-experimental | 074c4463726d42c8a1d652db0fc5c413 |

These are scoped regressions, not completion of R09 or final acceptance.
Cancellation/count semantics and backlog responsiveness remain to reconcile;
ordered storage is justified only by measurement.

## Cancellation and backlog reconciliation

Source audit at 9b13c0e finds no production reader of active_count outside the
scheduler. select_scales_quantizer_page queues refresh_quantiser before
refresh_romans; the first job queues refresh_romans again during dispatch.
The frozen snapshot still executes the cancelled job, and retirement may count
it twice. Both Romans callbacks read current selector state, so this demonstrates
redundant work and a bookkeeping defect, not a reproduced wrong display or MIDI
output. No cancellation behavior change is included without that evidence.
The channel refresh wrappers likewise read current selection when executed.

The cleanup threshold compares active_count with the monotonically increasing
next_id. This can allocate/copy the coroutine map every update, including idle
updates. Measure before replacing storage or adding ordered queues; the source
mechanism alone does not establish a meaningful application performance gain.

Existing native regressions on 9b13c0e:

- M-EDIT-FLICKER-001 real-time passed: 6006ea760e0e4a4f9164c1e79b47474c.
- M-SYNC-023 real-time passed: bd8b3620b2ad4931a92449ae0b36ea51, using
  MONOME_EMULATOR=/home/andy/projects/monome-emulator-runtime-stall.
- The first M-SYNC-023 attempt, 98da2593672c4d5fb5ac3f55c33ebb63, used the
  midi-clock checkout and was rejected at runtime_stall action validation before
  the musical assertion. It is a failed setup, not a passing test or a Mosaic
  regression. Controlled mode does not model this wall-clock stall.

R09 remains open: reconcile its count contract against the existing defect policy
and measure cleanup cost before deciding the remaining storage work. Do not add
an unproven user-visible defect fix or claim full scheduler completion here.

## Measured cleanup optimization

Baseline: 6f13738. A cleanup_pending flag records cancellation/retirement and
retains the existing compaction threshold. Updates with no reclaimable entries
keep the current coroutine map. Snapshot order, callback execution, monotonic IDs
and the pre-existing cancellation/count defect are unchanged. No ordered queue,
tombstone structure or dispatch budget was added.

External reproducible experiment: /home/andy/projects/mosaic-behaviour-runs/r09-scheduler-cleanup/
contains frozen baseline.lua, candidate.lua, bench.lua, results.tsv and differential.lua.
Run `lua bench.lua DIRECTORY` and `lua differential.lua DIRECTORY`.
Five alternating samples, 10,000 updates each, GC stopped during each measurement
and restarted afterward. Callback counts and final active counts are asserted.
Host CPU/allocation measurements, not a physical-norns performance claim:

| Workload | Baseline median seconds | Candidate median seconds | Baseline allocated KiB | Candidate allocated KiB |
|---|---:|---:|---:|---:|
| Idle, mature IDs | 0.003448 | 0.002405 | 548.023 | 1.148 |
| 16 yielding jobs | 0.064014 | 0.050567 | 5550.307 | 3.432 |
| Three debounce calls per tick | 0.026406 | 0.025280 | 37891.807 | 37891.807 |

The idle and yielding allocation reduction justifies this small change. Churn
samples vary; no reliable churn speedup is claimed. GC-disabled timing isolates
allocation and does not establish end-to-end musical latency improvement.

Full Lua suite: 1545 passed, 25.256 seconds; six guards passed. Added focused
contracts for next-pass job creation and cancellation of a yielded job. External
differential checks compare same-pass cancellation with and without yielding,
including traces, counts and retained IDs, against baseline. Sol's scoped review
found no concrete correctness issue.

Native checks on the changed production source:

| Case | Mode | Passing run |
|---|---|---|
| M-ALG-PAINT-RACE-001 | controlled-experimental | f2af67285f7d4074be1db3ce53dbd187 |
| M-MEMORY-010 | controlled-experimental | c43bbaa6c82d4e91912fef5ddd230b67 |
| M-ALG-PAINT-RACE-001 | real-time | 0c1c5279276e41bbba7f1b0830e57ad1 |
| M-MEMORY-010 | real-time | 66106aa56c874602bb8e43d2544ce859 |
| M-SYNC-023 | real-time | 1533bd079d4d4bf39f14e7689ca9c7a1 |

Remaining cancellation/count repair is explicitly deferred pending a reproduced
user-visible consequence under the existing defect policy. This does not claim
R09's correct-count condition is satisfied. Playback ownership extraction can
proceed while preserving that scheduler behavior; no new scheduler algorithm is
needed for the next structural slice. Final acceptance remains outstanding.
