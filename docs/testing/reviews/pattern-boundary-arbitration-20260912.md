# Arbitration: CONVERGED

unanimous, unblocked, substantiated

## Options (caller ids)
- **characterize_only**
  - as given:  Keep the current behavior as a documented scheduler-latency characteristic and exclude the exact sub-tick edit window from refactor guarantees. Add no Mosaic production fix; retain controlled and real-time measurements as limitations while allowing refactor work around this code.
- **controlled_exception**
  - as given:  Treat the 1 ms condition as a formally controlled-time boundary, record a narrowly justified real-time lane exception, retain a separate real-time practical-margin characterization, and permit the smallest Mosaic fix now. Require deterministic controlled red-to-green repeats, the observed valid real-time reproduction as supporting evidence, real-time no-regression at a stable margin, scheduler-specific unit/integration tests, focused behavior collateral, and full suites.
- **require_realtime_red**
  - as given:  Do not change Mosaic until the emulator can produce a deterministic complete real-time tap whose Lua callbacks both complete before the boundary and which fails repeatedly for the stale-note reason. Continue emulator/native runtime work even if it requires a deeper scheduling capability; only then apply the ordinary both-lane baseline rule and validate the isolated fix.

## Framing · cleaning: skipped
```
(cleaning skipped by caller — framing is the caller's own, un-de-biased)
```

## Shared research
Repository-only; no web research was performed.

## Round 1
### claude → `controlled_exception`
- risk: `MINOR` — The smallest fix still recomputes working patterns on the boundary pulse, the performance-sensitive path whose 16-channel event-timing gate already fails 2/3 canonical repeats; the required full-suite PERF layer must be read as a gate, not a formality.
- authority: `technical` (advisory)
- constraint: The debounced rebuild yields after each channel and the scheduler resumes once per 1/300 s, so the cancellable window for the edited channel is one ~3.33 ms tick — finer than the real-time lane's own 10 ms timing allowance, and the edit runs on the un-deadlined key-up callback.
- decisive citation: `lib/pattern.lua:232`
- supporting: `mosaic.lua:285`, `lib/m_grid.lua:261`, `tests/behaviour/suite.py:280`
- label map: `OPTION-0d1cbe85078e6f9d`→require_realtime_red, `OPTION-6b410a00009e45a7`→controlled_exception, `OPTION-d0a4780cd0a0082e`→characterize_only

### codex → `controlled_exception`
- risk: `NONE`
- authority: `technical` (advisory)
- constraint: Both the edit path and song-boundary path call a debounced rebuild whose later invocation deactivates the still-active prior rebuild.
- decisive citation: `lib/scheduler.lua:95`
- supporting: `lib/pattern.lua:229`, `lib/pages/note_edit_page/note_edit_page.lua:125`, `lib/step.lua:1006`
- label map: `OPTION-c33d86fc89a1f04c`→controlled_exception, `OPTION-efeb1caba1ac4bd9`→characterize_only, `OPTION-f70c9bf2e16c859e`→require_realtime_red

## Reconciliation
round 2 not run

## Record (paste verbatim)
```
DECISION: Mosaic pattern edit at song boundary
OUTCOME: CONVERGED
SELECTED: controlled_exception
PROVISIONAL-SELECTED: none
ADVISORY: none
ROUNDS RUN: 1
round 1 · claude: selected controlled_exception · risk MINOR · authority technical · decisive lib/pattern.lua:232
round 1 · codex: selected controlled_exception · risk NONE · authority technical · decisive lib/scheduler.lua:95
REASON: unanimous, unblocked, substantiated
```

ARBITRATION: CONVERGED
SELECTED: controlled_exception
PROVISIONAL-SELECTED: none
ADVISORY: none
AUTHORITY-POLICY: advisory — a Parallax CLASSIFICATION:B would escalate; this tool does not
CLEANING: skipped
SNAPSHOT: 28386ded04d2c412e82daba677d451017f1f40fa
ORDER-SEED: c3d70bbdb0724bfb9518f3c885873ccc
REFS-MOVED: yes
AUDIT: /tmp/mosaic-boundary-arbitration-20260912/20260912T081233-arbitrate-e9e29eef.json
ROUNDS: 1
RESEARCH: repository-only
RESEARCH-DIGEST: none