# R14 final qualification and external-Start timing

Updated 2026-09-13. This receipt closes the source-frozen base-MIDI qualification
without claiming physical-norns equivalence. Thresholds were not relaxed.

## Full qualification triage

The one planned full sweep at clean revision `fb780ac` ran 787 real-time and
791 controlled cases. It passed 1,560/1,578 case lanes and every included fast
check. Evidence: `/home/andy/projects/mosaic-behaviour-runs/r14-final-base-fb780ac-05/suite.json`.

`M-SYNC-022` failed both lanes because the integrated emulator branch lacked an
already-tested request-capacity change. Emulator commit `b672873` restored that
change, passed 120 generic contracts, passed `M-SYNC-022` in both lanes, and was
pushed to emulator `main`.

Of the remaining 16 real-time failures, 15 passed one-by-one on an idle host.
`M-SYNC-006` remained deterministic enough to fix: four serial runs missed the
unchanged 10 ms bound by 10.020543-11.494174 ms while scheduled input delivery
was below 0.22 ms. The controlled lane passed three fresh-process repeats,
showing correct logical ordering while leaving the real callback cost exposed.

## M-SYNC-006 diagnosis and correction

A repeated incoming MIDI Start synchronously called Stop. Stop rebuilt the
37-sprocket lattice and forced a full Lua collection; Start then destroyed the
fresh lattice and built it a second time before the coincident Clock could run.

The first experiment omitted only the forced collection during immediate
restart. It preserved normal Stop collection and passed all 1,547 Lua tests, but
was insufficient: six of eight real-time samples passed while allocation/host
pauses still produced 14-25 ms first-Start and up to 40 ms restart latency.
Those red runs are retained under `ec63a9c17f55492ab0643fd9fa8c32c4` and
`baf197ecc2c04a1087b520356d422a0a`.

The final correction also replaces the redundant Start-time construction with
in-place preparation of the clean lattice created by init/reset. Preparation
resets fractional carry, current step, transport and final stopped settings. It
retains constructor delay for end-of-step processors; the first attempt reused
song-transition realignment and was rejected by two recording unit regressions.
Normal Stop still performs its full collection, and an immediate external
restart still drains held voices and pending releases before step 1.

## Final evidence

Five consecutive real-time `M-SYNC-006` runs passed. Maximum absolute onset
phase was 3.429 ms and the restarted step-1 note was 2.834-3.429 ms from its
source deadline:

- `5a103fce2fd1461eb5fb01dd362cc5a7`
- `6ba99bbfcc0d453a9bbb71c79688cd74`
- `165c50be86a24235ae05b5683ecb8700`
- `9b52d004fead4eafb77de9812551b55f`
- `d75fd23f2cbc4bb5bf6a8a29379926e8`

Controlled fresh-process repeat evidence is
`repeat-784acbe6ffe7463da462bea68e0ebe91` (3/3, identical logical output).
All paths are beneath `/home/andy/projects/mosaic-behaviour-runs/`.

Collateral validation:

- 1,548/1,548 Lua unit and integration tests passed.
- Six inventory, unique-name and Lua-syntax guards passed.
- Real-time `M-SYNC-001/002/005/007/011/018/020` passed.
- `M-TIME-001` passed controlled time and an isolated real-time run
  (`fea1a7f833d347f3b5b32b160b32bf79`,
  `0adf41dfca1444a38c0fd26e680de8a6`). A preceding loaded serial run retained
  one 14-18 ms host phase step at `/15`; it did not accumulate and did not
  reproduce in isolation.
- `M-SHUFFLE-001` passed every Drunk basis and amount boundary in controlled and
  real-time lanes (`a9c579ce056a4b6db2c67c719a9a7b56`,
  `8d80ccc1159649a281995f33045745c8`).
- User-like live recording `M-REC-001` passed both lanes
  (`0c8a8876d9d24d39b464d5c9ace0a047`,
  `79abe6f6b4d14c3e9358b4ec6666d19e`).

The completed full sweep, exact controlled checks, focused collateral and
serial real-time clears are the final R14 evidence. Per the user's explicit
proportionality decision, no duplicate 1,578-lane sweep is required after this
isolated fix. Revision `fb780ac` is the rollback point for the timing change.
