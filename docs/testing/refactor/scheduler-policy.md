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
