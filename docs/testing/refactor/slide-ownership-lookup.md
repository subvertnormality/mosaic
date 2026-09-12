# Slide ownership lookup — first refactor slice

Base: `2adcf11`; production change: `lib/clock/m_clock.lua`.

The execution ring retains ordering and interpolation. A channel/parameter index
now answers `channel_is_sliding` directly, removing a scan of up to 1023 ring slots
from each lookup. All retirement paths clear ownership before callbacks; ring
compaction preserves slot references. Cancellation and handoff still traverse the
ring in their existing order, including callback reentrancy semantics.

Validation on the changed source:

- Full Lua suite: 1514 collected, 1513 passed. The sole failure was the existing
  wall-clock slide-admission budget: 2.104 ms against 2 ms. A focused rerun passed
  (1 collected). This does not erase the full-run failure or prove native speedup.
- Six inventory, naming and Lua syntax guards passed.
- M-PATCH-064 passed controlled and real-time: independent CC/NRPN ownership,
  endpoints, event encoding, timing and note gates.
  Manifests under `/home/andy/projects/mosaic-behaviour-runs/`:
  `dee3241bc49d4b8c917e6b568b58a52f/manifest.json` and
  `e00a2fe4803a4ae3b3fa85d512843fd6/manifest.json`.
- M-SLIDE-RESET-001 passed controlled:
  `f1751514fa1446bcb029321a8637152b/manifest.json`.
- `git diff --check` passed.

Setup failures before collection (Windows expansion of ROOT; missing emulator
environment for Python guards) were corrected, not counted as passes.

No claim that PERF-003/004/008 is fixed. Compare constrained native measurements
when the host is suitable; retain unchanged thresholds and the previous baselines.
