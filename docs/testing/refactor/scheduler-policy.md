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

Next: examine the channel step-release display refresh that creates a new debouncer
per call. Share it only if those operations are display-only and can be coalesced;
keep musical inputs, recorder/history commits and rebuild requests outside that
coalescing. Consider ordered storage only after measurement justifies the change.
