# Mosaic broad refactor and performance plan

Planning assessment: 2026-09-12. Status: **planned; implementation not started**.

Correctness is established by executable, source-bound evidence. Prior reviews are
historical design input; reviewer identity, availability, receipts and convergence
are not admission requirements. Validate any reproducible review finding through
the same tests as any other defect.

Validation-cadence amendment, 2026-09-12 user direction: use the quick controlled
behaviour lane for routine feedback; run the slow real-time lane only for targeted
affected cases during development; run the complete slow lane only at the final
qualification of each separately delivered phase. This amendment postdates P0 and
overrides earlier milestone wording that requested intermediate full behaviour runs.

### Proportional remaining-work scope

This section overrides broader or duplicative requirements later in this planning
record. Completed evidence remains valid while its bound sources and contracts are
unchanged.

- Freeze one concise baseline manifest. Do not recursively inventory historical
  artifacts or require separate campaign, audio/Crow and refactor admission loops.
- Preserve existing high-value tests. Add coverage only for a documented workflow,
  a changed branch, a known defect or a material refactor seam. Cheap pure-function
  tables may enumerate finite domains; native tests use representative boundaries
  and named high-risk interactions instead of Cartesian products.
- R01 may make bounded performance repairs in the existing structure. Current red
  performance tests are inputs to that work and do not prohibit R00/R01. Broad
  extraction waits only for known functional failures and for the timing paths in
  the selected slice to have measured, owned treatment.
- During development run affected unit/integration tests, affected controlled cases,
  and real-time cases whose timing, lifecycle or native boundary can change. Run one
  complete frozen-candidate qualification at R14.
- Audio/Crow coverage is representative and limited to supported Mosaic routes,
  ownership, persistence and failure propagation. Generic engine, capture, Crow,
  ii and browser protocol matrices belong to emulator conformance. Matrix/Toolkit
  performance work remains deferred.
- R03-R13 are a menu of measured refactor slices, not an obligation to relocate every
  module or introduce every proposed abstraction. R15 and R16 are separate follow-up
  projects and do not block the code/performance refactor.
- Use a short completion note plus retained run manifests. Per-card governance
  receipts, recurring reviewer checkpoints and provider-specific review policy are
  removed from upcoming work.

Authoritative destination: Mosaic `docs/testing/refactor/REFACTOR-PERFORMANCE-PLAN.md`.
The Windows emulator-workspace copy is a planning delivery mirror, not emulator scope.

## 1. Target, authority and how to use this document

Target the existing Mosaic worktree `/home/andy/projects/mosaic-behaviour-tests`, branch
`codex/behaviour-validation`. Inspected HEAD: `d91d1eb` (Refresh PERF-008 review evidence).
During assessment, other work consolidated the staged fixes in `347d80c`, qualified
clock-attribution wording in `0b67a01`, and recorded consolidation in `90979ce`.
Initial detailed inspection recorded HEAD `90979ce44e5f3d775bd57ea388ec1ead70b8f9d4`; the worktree was
clean at that check. Source findings describe the originally inspected dirty tree;
R00 must reconcile these commits and any subsequent changes before execution.
Final metadata refresh during P0: the branch advanced through five reapplied fixes
and their receipt to `300e93a85e6a7de41c1f3e9f4c2badb9fa57a13d` (ahead six of remote).
Those commits were made by other work, not this planning task. R00 must use the
current bug ledger and not reapply fixes already present; the review does not
re-certify the newer source's runtime behavior.
This is the branch containing the application behaviour tests. The emulator support
worktree is `/home/andy/projects/monome-emulator-behaviour-audio-crow`, branch
`codex/behaviour-audio-crow`, inspected HEAD `801fcdc`, two commits ahead of its remote.
Selection means working in the existing Mosaic worktree; do not switch the dirty
Windows emulator checkout or forcibly check out an already occupied branch.

The initially inspected Mosaic index contained staged memory, vertical-fader and channel-editor
fixes, changed unit tests, and new behaviour regressions/candidate patches. They are
now committed in `347d80c`; do not recreate their patches or treat them as staged work.
Preserve any *new* unrelated edits found at execution time: do not reset, stash,
commit, push or absorb those edits into refactor commits as a convenience. Record
the exact tree again before execution; this plan does not freeze other ongoing work.

The user requested a plan, not refactor implementation. This document authorizes no
runtime edits by itself. Once execution is requested, follow the cards in order
without routine approval questions. Existing campaign prerequisites still apply.

Read first, from the actual selected trees:

1. Applicable `AGENTS.md`, including the emulator's delivery instructions.
2. Emulator `docs/delivery/{PLAN,RUNBOOK,ACCEPTANCE,UPSTREAM}.md` and `state.json`.
3. Mosaic `docs/testing/{BEHAVIOUR_PLAN,AUDIO_CROW_REFACTOR_SCOPE,UNIT-INTEGRATION-HARDENING,EXTERNAL-MIDI-SYNC,NATIVE-MIDI-BOUNDARY}.md`.
4. Mosaic `docs/testing/{state.json,bugs.json,decisions.md,refactor-gap-scan.md}`,
   hardening matrix, manual inventory, current performance receipts and their raw artifacts.
5. Performance support tree `/home/andy/projects/monome-emulator-performance-integration`:
   `docs/delivery/PERFORMANCE.md`, `src/automation/performance.py`, current branch/HEAD,
   runtime/image/patch identities and its capability/completion records. This is an
   explicit read/bind dependency, not permission to refactor emulator code. Record
   separately which emulator tree each runner imports and which runtime it launches.

Review-policy precedence for this Mosaic plan: the Mosaic decision dated 2026-09-10
in `BEHAVIOUR_PLAN.md` and `decisions.md` supersedes older Codex-only wording with
Claude Opus for future reviews. The user's 2026-09-12 instruction explicitly selects
Claude Fable (`claude-fable-5-1`) for this P0 review and its focused follow-up. This
exception does not silently change the engine for R14/R16 or unrelated work. Use
the local runbook's bounded review cadence with the applicable latest model policy.

Those contracts retain precedence for required behaviour, performance thresholds,
lane applicability and existing defect decisions. Older README examples and stale
progress paragraphs do not override current executable gates or later amendments.
If these disagree, record the exact disagreement and resolve it before accepting
dependent work. Do not edit the oracle to match a refactor.

This is a Mosaic application refactor. Keep norns official and pinned; keep emulator
adapters small and generic. No Mosaic name, model, parameter or timing workaround
belongs in emulator core. An emulator or upstream clock defect gets a separate
reproducer, candidate patch and generic conformance gate, never a hidden Mosaic fix.
A documented isolated patch set on a pinned official norns revision is an admissible
candidate runtime after its applicable generic and Mosaic gates pass. R00/R14 must
bind the full installation, official revision and patch hashes explicitly. Do not
overwrite the user's/default installation or substitute an unrecorded runtime. Such
candidate selection is distinct from application-mod patch flags.

## 2. Assessed baseline and evidence limits

This assessment read the actual working-tree source, runner code and tracked evidence.
It did not execute the native campaign or performance workloads. Recorded passes are
historical evidence, not new results for the staged tree. No speedup is claimed.

| Finding | Inspected evidence | Consequence |
|---|---|---|
| Refactor prerequisites remain open | `docs/testing/state.json` next action; hardening card says in progress | R00/R01 are admission gates, not optional cleanup |
| Integrated Lua suite reportedly passed 1513/1513 before current staged edits | Current state record | Revalidate; count alone neither proves coverage nor applies to this tree |
| Dense sequencing PERF-002 has a canonical pass | `perf-dense-canonical.json` | Preserve as a performance and output guard |
| Dense slide PERF-003 fails at 16 channels in two of three recorded repeats | Same receipt: p99 about 10.06/10.56 ms; functional checks passed | Diagnose before refactor admission; never discard failed repeats |
| PERF-004 and M-ENDURANCE-001 retain constrained timing failures | State next action | Obtain current source-bound runs and causal traces |
| PERF-008 overload recovers its queue but not musical phase | `perf-overload-recovery.json`: final phase about 67.76 ms, queue recovery about 7.06 ms; event timing false | Queue-empty and balanced notes do not establish timing recovery |
| Generic clock probe shows a possible runtime mechanism | State cites emulator `2223a23` and a 41.6666666667 ms displacement after two missed deadlines | Hypothesis for untraced endurance failure; attribution remains open |
| PERF-005..007 and full hardening need reconciliation | State and hardening card | Inventory all workloads; don't certify only available scripts |

Source sizes below describe this snapshot; they are navigation aids, not mandatory
line-count targets. `step.lua` 1150 lines, `m_clock.lua` 983, `program.lua` 974,
`m_lattice.lua` 726, `m_midi.lua` 745, `device_map.lua` 638, `memory.lua` 633,
and channel-editor UI 1863. Splitting a file alone is not a benefit.

### Concrete architecture findings

| Area and source anchors | Observed issue / risk | Proposed response |
|---|---|---|
| `lib/models/program.lua`: `get`, `set`, mask setters, `prepare_for_save`; `lib/memory.lua`: module-local `state`, `record_event` | Mutable model tables escape throughout the app; memory retains a separate reference; selection and persistent data are intertwined | Explicit state ownership, project generation and stable facades before changing representation |
| `lib/step.lua`: `handle`, `process_params`, `handle_note`, song methods | Resolution, random draws, parameter output, voice construction, clock work and song transitions are mixed | Extract in existing execution order; pure resolution only after inputs and mutation points are explicit |
| `lib/clock/m_clock.lua`: delayed-ID tables, slide ring, arps, start/stop; `m_lattice.lua` | Several overlapping ownership/cancellation structures, persistent callbacks and distinct timing domains | Document release/onset/slide ownership; extract lifetimes and transitions without replacing the clock algorithm |
| `lib/scheduler.lua`: `update`, `debounce` | Sorts active IDs each update; iterates a snapshot without rechecking active status; cleanup criterion uses lifetime `next_id` | Characterize cancellation and same-tick scheduling; separately fix demonstrated defects before optimizing iteration |
| `m_clock.lua` end-of-clock callback around line 466 | Creates and immediately invokes a new debounce wrapper on each refresh | Persistent, keyed UI invalidation after preserving observable refresh semantics |
| `lib/pattern.lua`: `get_and_merge_patterns`, `effective_lengths`, `update_working_patterns` | Recreates per-step lists, sorts for min/max/mean; computes effective lengths repeatedly; yields across 16-channel rebuild | Measure rebuild cost, use equivalent aggregate arithmetic, then dependency-aware invalidation with safe publication |
| `lib/quantiser.lua`: cache key/cleanup/process methods | Per-key scale hashing/string creation, copied scales and sorted eviction; `scale_hash` assignment is non-local | Immutable derived scale data and complete identity keys after mutation ownership; localize accidental global only after checking callers |
| `lib/memory.lua`: `record_event` | Backward scan to find prior same-key event; history snapshots and aliasing requirements | Preserve exact undo floors, then benchmark indexed lookup and bounded storage |
| `lib/devices/{device_map,param_manager}.lua`, `step.lua` parameter lookups | Configuration, slot numbering, norns params and output encoding overlap; magic slots 2/3 in note resolution | Stable parameter descriptors with legacy IDs and dedicated protocol codecs |
| `lib/m_midi.lua`, `step.lua`, delayed callbacks | Input chord state and delayed note release can outlive selection, routing or device lifetime | Capture originating owner; distinguish Stop, Panic, disconnect and project replacement |
| `lib/pages/*`, controls, UI components | Repeated gesture and mutation logic; large channel-editor construction; pages rely on globals | Extract controllers, edit commands and view models incrementally, preserving gestures and visible states |
| `mosaic.lua` tests, test helpers | Some tests reach locals through `debug.getupvalue`; broad mocks obscure interactions | Replace internal-coupling tests with stable seam tests and real composed Lua modules |

The gap scan includes suspected defects and characterized quirks. It is a lead list,
not proof that each issue still exists. Reproduce each before fixing. In particular,
do not quietly change release-order gestures, MIDI startup messages, Off/nil/-1/0
semantics, selector behavior or transport behavior under the label “cleanup.”

## 3. Non-negotiable acceptance rules

1. Every required behaviour and performance test must pass on the final candidate.
   A result that was already red cannot remain red at final acceptance. Missing,
   uncollected, unsupported, skipped or xfailed required cases are not passes.
2. Preserve existing behaviour/performance IDs, recipes, expected outputs, masks,
   tolerances, durations, repeats, resource limits and coverage. Freeze their content
   hashes and enumerated selections at R00. Allow only path/import/helper-lookup
   plumbing where a contract directly reaches a moved private function, under R03's
   explicit migration rule below; never change its stimulus or oracle. Added tests
   increase the obligation. Never replace a test with a weaker equivalent-looking one.
3. Unit tests may be reorganized or replaced. For each removed test map its contract
   to the new test or explain that it tested only a removed internal representation.
   Preserve meaningful boundary, fault and integration checks; don't edit expected
   musical results merely because implementation changed. No required-test count loss
   hidden behind a renamed suite; count changes need a coverage mapping.
4. Run the actual application entry point with `testing = false` through public
   emulator input APIs. Assert complete MIDI/grid/frame output and PCM/CV/ii for
   applicable profiles. Internal state and mock traces are diagnostic supplements.
5. Controlled time supplements real-time evidence. Audio/Crow are real-time. Keep
   declared controlled-only applicability; do not invent exclusions after a failure.
6. Preserve MIDI ordering, random draw order/seed semantics, first-note phase,
   pending releases, parameter-before-note order, delayed pitch application rules,
   slot/channel isolation and legacy project compatibility. Do not sort away races.
7. A confirmed baseline defect requires a minimal real-input failure, classification,
   isolated fix and before/after evidence. Keep it separate from structural changes.
   Runtime fixes require generic tests with Mosaic and its dependencies absent.
8. Protect user projects: disposable data roots, copied fixtures, failure-safe save
   tests, explicit process ownership and cleanup. No manual or hardware acceptance.

## 4. Intended architecture and extension boundaries

Retain Lua, norns include semantics, current public module entrypoints and saved
project layout during the refactor. Use plain modules/functions and explicit
arguments. No framework, service locator, message bus, universal plugin registry,
new language, custom norns clone or wholesale immutable-model rewrite.

Proposed directories are destinations, not existing modules or an obligation to
create empty abstractions. Introduce a module when a card moves a cohesive behavior.

| Boundary | Owns | Must not own |
|---|---|---|
| `lib/app/` | composition, project lifecycle, runtime dependencies | musical formulas or generic emulator behavior |
| `lib/model/` behind existing `lib/models/program.lua` | defaults, validated project data, explicit edits/revisions | screen drawing, MIDI I/O, clock callbacks |
| `lib/music/` behind `pattern.lua`/`quantiser.lua` | merge/scale/step resolution with explicit inputs | mutable selected page, wall-clock I/O, device lifetime |
| `lib/playback/` behind `step.lua`/`m_clock.lua` | ordered dispatch, owned voices, slides, song/transport transitions | project serialization, UI widgets |
| `lib/devices/` | descriptors, encoding, MIDI/n.b./Crow output boundaries | page state or independent musical expectations |
| `lib/edit/` | explicit edit transactions and undo integration | timer-driven playback or rendering |
| `lib/persistence/` | validation, migrations, serialization and safe file operations | live callbacks or device objects in saved data |
| existing pages/controls + small view models | gesture interpretation and rendering from state | direct unrelated model mutation or synthesis policy |

Dependency direction: application composition wires controllers, state and output
boundaries; controllers submit edits; music reads explicit state; playback emits
ordered output through adapters; views read state. Avoid adding cyclic includes.
Keep compatibility wrappers until all callers are migrated, then delete wrappers
only when no caller or external saved representation needs them.

Three ownership categories must be written down before extraction: persisted project
data; derived/cached data; transient runtime/UI state. Distinguish selected editing
song/channel from playback target, and channel 17's global-scale role from channels
1–16. Define cloning and lifetime per table; never deep-copy callback/device handles.

New features are unspecified. The deliverable is cheaper, safer feature addition,
not a new musical mode invented during a refactor. R15 supplies worked extension
recipes and a test-only extension proof. Any user-facing feature gets its own
specified behavior card and additive tests after this baseline is green.

## 5. Execution protocol for every card

Use one card and one coherent change at a time. Do not combine formatting, renames,
algorithm changes and defect fixes. No parallel agents are required by this plan.

1. Read the selected slice and relevant evidence. Check branch, status, HEAD and source
   digests. Reconcile newer user edits; never assume this assessment is current.
2. Record planned file changes, preserved contracts and exact focused test selection.
3. For a nontrivial boundary change, record the intended ownership and callers.
   For a performance change record the measured bottleneck and target metric.
4. Implement the smallest extraction behind the existing API. Run focused checks
   after each slice. Keep the old implementation until comparison is meaningful.
5. Run affected unit/contracts, controlled behaviour and targeted real-time checks.
   If a failure appears, retain evidence, minimize and classify it.
   From suite start until `suite.json` says `status: finished`, do not write any file
   in the tested tree, including this plan, completion notes and state. Use sibling
   run storage for live logs. Require `summary.sources_stable: true`; source drift
   invalidates the run even when individual cases passed.

### Required feedback cadence

“Quick lane” means `controlled-experimental` behaviour cases plus the suite's fast
Lua contracts, Python oracle tests and isolated Lua units. It is the default feedback
path even though the runner retains its historical `experimental` name. It proves
deterministic actions, output and logical timing; it does not certify wall-clock,
audio or Crow behaviour. “Slow lane” means `real-time`, including real-time-only
audio/Crow cases and constrained performance/endurance jobs where applicable.

Use this order for every production slice:

1. Run the directly affected unit/contract tests.
2. Run directly affected behaviour IDs in the quick lane. During implementation,
   use an anchored `--case-pattern` that names those IDs and keep fast layers enabled.
3. Run the complete quick lane at the end of a cohesive multi-commit phase, rather
   than after every small extraction.
4. Run only the slow cases selected by the card's impact map: the same user workflows,
   every previously failing real-time case in that area, and timing/lifecycle/output
   anchors whose contract cannot be proved in controlled time. Include the exact
   applicable PERF rows only when the change touches their measured path. Record why
   each slow case was selected. Use `--case-pattern` or a generated exact-ID regex;
   do not use a broad real-time sweep as a convenience.
5. At R14, after the candidate is frozen and no further production edits are planned,
   run one unfiltered full suite across both lanes and all required profiles, plus the
   complete standalone constrained performance/endurance matrix. This is the only
   full slow-lane sweep during the code-refactor phase. Any resulting fix invalidates
   that final run: apply the fix, use quick plus targeted slow feedback, freeze a new
   candidate, then repeat the single final qualification sweep.

R00 does not manufacture a new full slow baseline. Bind reusable source-matched
evidence and run only the current quick baseline plus prior-red or attribution-critical
slow cases. R01 closes functional blockers and measures the performance failures that
motivate the selected refactor. The consolidated unfiltered slow sweep is deferred to
R14.
6. On failure restore only the card's changes (or revert its isolated commit in the
   execution branch), never reset the whole worktree. Re-run the affected baseline
   case if the host may be at fault. After two same-cause failures inspect the cause;
   do not retry until green or silently increase timeouts/resources.
7. Retain the machine-readable test manifests and add a concise completion note only
   when it helps the next slice or reviewer understand a material decision.

Commit only card-owned files when execution authorization permits. Never `git add .`
in this worktree. Publication/merge is separate from this planning task.

## 6. Ordered cards

### R00 — Freeze and reconcile the acceptance baseline

**Depends:** execution authorization. **Change:** evidence/docs and collection checks only.

1. Record full Mosaic/emulator commits, staged/unstaged patch hashes, relevant
   untracked files, submodule state, official runtime lock/build/patch identities,
   Lua version, mods/players, installation identity and host/container facts.
2. Record the current test collection and map each user-visible workflow, critical
   interaction and performance workload to its strongest existing guard. Do not
   atomize repeated prose or re-inventory historical receipts.
3. Verify only evidence proposed for reuse against its source identity. Mark stale,
   missing and currently failing evidence explicitly.
4. Preserve any new unrelated edits separately; the initially staged fixes are
   already committed. When a clean baseline is available, create an
   isolated executor worktree from its actual accepted commit. If preserving dirty
   changes in a snapshot is necessary, use an explicit patch manifest; do not silently
   commit another task's edits or use an old HEAD as the tested tree.
5. Run the complete quick baseline and only the slow cases needed to reproduce known
   failures or establish the timing/lifecycle paths selected for early work. Record
   failures without changing thresholds.

**Output:** `baseline-inventory.json`, `baseline-status.md`, reproducible command matrix,
immutable baseline report/artifacts. **Done:** all obligations classified with owners;
not a claim that baseline is green. **Stop:** missing source identity or moving tree.

**Missing performance-workload reconciliation (bounded R00 output):**
Use the existing performance ledger. Record each workload's purpose, executable
recipe, output oracle, constrained envelope and current result.
At assessment, dedicated Mosaic entry scripts exist for PERF-002/003/004/008;
dedicated PERF-001/005/006/007 commands have not been established. Do not search for
them indefinitely or label them implemented. Within one inventory pass, classify
each obligation as `implemented`, `equivalent-covered`, `missing`, or explicitly
deferred by a dated user decision. Add a missing recipe only when it measures a risk
in the selected refactor or a documented release requirement that no existing
workload covers. Preserve the existing Toolkit/Matrix performance deferral.

### R01 — Close existing blockers before structural refactoring

**Depends:** R00. **Change:** minimal isolated repairs in the existing campaign only.

1. Verify the consolidated fixes and the critical workflow anchors: locks, trig
   parameters, scale merging, external sync, persistence and affected output routes.
2. Diagnose PERF-003/004/008 and endurance with native timestamps: intended deadline,
   callback start/end, queued input completion, actual emission and overload interval.
   Correlate clocks through existing mappings; don't rebase expected phase on output.
3. Use a minimal independent runtime probe to separate host contention, runtime
   skip-ahead and Mosaic work. The earlier clock probe is not proof about every failure.
4. Fix confirmed defects in isolated candidates. A runtime change first passes generic
   app-free conformance, then composed Mosaic cases; record new runtime identity and
   regenerate the baseline for downstream cards. Do not patch official code in place.
5. Add only performance recipes whose distinct risk remains uncovered after R00.
   Retain constrained host limits and real-time error budgets. Use the quick lane and
   targeted slow evidence; defer the one unfiltered slow sweep to R14.

**Done:** the complete quick lane and critical workflow anchors pass; no known
functional failure remains; each red timing/performance result relevant to the first
selected structural slice has a passing bounded repair or a measured treatment owned
by that slice. One source-bound baseline exists. Final all-pass qualification remains
at R14.
**Recovery:** blocked ownership goes to the
responsible original card; planning/profiling may continue, broad code edits may not.
Use the prerequisite repair procedure below; do not wait for a downstream refactor
card to fix a gate that prevents that card from starting.

**R01 prerequisite performance repair procedure (no R03–R13 dependency):**
The current historical `performance_fixes_authorized: false` remains true for this
planning task. A future explicit instruction to execute this performance/refactor
plan includes these prerequisite repairs; it does not authorize them now. Preserve
retained red results as repair targets rather than accepting or hiding them.

1. From R00 measurements, assign each failing obligation one owner and a discriminating
   experiment: PERF-003 to parameter/slide/merge service investigation; PERF-004 to
   input/scheduler/refresh investigation; PERF-008 and endurance to absolute-phase
   runtime-versus-application investigation. Assign missing rows to recipe completion.
   Zero recorded throttling and a high service percentile are leads, not sufficient
   causal attribution; preserve unknown attribution until an experiment resolves it.
2. Before any repair write `R01-repair-<workload>.md`: exact failed gate, minimal
   reproducer, source identities, measured hot function/runtime boundary, proposed
   edit, unchanged inputs/outputs, focused and full reruns, and rollback. An item is
   bounded to one causal mechanism. The executor may choose its implementation.
3. In the existing module/API layout, permit a targeted local repair or equivalent
   optimization needed to pass the failing gate: for example reducing demonstrated
   redundant computation in one merge pass, fixing cancellation/count bookkeeping,
   or reusing a correctly owned refresh callback. It may use an R07–R10 technique
   without executing or depending on those cards. No module-family relocation, saved
   format change, new cache invalidation architecture or wholesale clock rewrite in
   this prerequisite track. Native runtime repairs follow the independent candidate
   and generic-conformance rule above. Do not add Mosaic-specific runtime behavior.
4. Compare the isolated repair against its retained failure with unchanged gates and
   adjacent-source regression runs. Preserve every failed attempt; after two attempts
   with the same cause, investigate rather than keep retrying. When all prerequisite
   repairs pass, freeze a new all-green baseline and repeat R02 profiling; remove
   already-completed techniques from later cards to avoid doing the repair twice.
5. If evidence shows that passing requires a change outside those bounds, record a
   precise scope blocker and proposed design. The user decides any amendment to the
   existing broad-refactor prerequisite; a focused review checks the proposed change
   but cannot grant that scope. This is an explicit exceptional stop, not a request
   for routine permission or an automatic relaxation of acceptance.

### R02 — Measure the selected execution path

**Depends:** the relevant R01 repair or measurement; read-only preparation may
accompany R01.

1. Trace init/load -> input -> edit/history -> pattern rebuild -> clock -> parameter
   dispatch -> note -> release -> rendering -> save/cleanup, with real function names.
2. Inventory globals, include order, mutable table owners, coroutine/metro owners,
   caches and persistence fields. Locate every writer before proposing revisions.
3. Use existing emulator performance capture first. Add bounded opt-in diagnostics
   only for missing spans: merge/effective lengths, scale cache, step/param resolution,
   slide updates, scheduler work, redraw, history and save/load.
4. Measure idle, dense notes, dense slides, live input, scale changes, undo/save,
   mixed outputs and recovery. Report counts, allocation/GC pressure, CPU, service
   time, timing percentiles/max/phase, RSS/slope, queue depth and redraw latency.
5. Measure instrumentation overhead by identical runs with it disabled/enabled.
   Acceptance uses the normal configuration; diagnostics must not hide the workload.

**Output:** `architecture-map.md`, `profile-baseline.json`, ranked hotspot table with
measured/hypothesized labels. **Done:** each optimization has a measurement and owner.

### R03 — Establish stable module seams and rework fragile unit tests

**Depends:** R02. **Files:** `mosaic.lua`, test helpers, selected module facades.

1. Extract lifecycle functions behind explicit application entrypoints while keeping
   norns `init`, `key`, `enc`, `redraw`, `cleanup` behavior and include order intact.
2. Inject only real external dependencies (clock, MIDI, params, screen/grid, file I/O)
   at construction or small module boundaries. Avoid an all-purpose context bag.
3. Replace `debug.getupvalue` tests with lifecycle/module contract tests. Compose real
   model/scheduler/music modules; mock only the external boundary under test.
4. Remove test reliance on private table layout only with a contract mapping. Keep
   syntax, duplicate-name, collection, source binding and runner-failure guards.

**Validate:** all units/contracts plus boot/reload/cleanup/persistence native cases.
**Done:** no behavior change; old entrypoints still work; each changed test mapped.
**Rollback:** facade extraction only. Do not simultaneously rewrite the model.

**Required fast contracts located under `tests/behaviour/`:** location does not make
these mock/helper contracts native workflow tests. R03 inventories their private
lookups; R06/R10 own each lookup migration when the corresponding production helper
moves. Specifically preserve all six `test_slide_{cancellation,reset,live_retime,
retime_phases,endpoint_phases,timing_type}.lua` contracts, `arp_release_contract.lua`,
`conditional_realign_contract.lua`, and `pattern_priority_contract.lua`; expand this
list if R00 finds more. Record each original function/upvalue and replacement seam.
Only change `up(...)`/`find_helper` resolution, `dofile`/include paths and minimal
dependency binding needed to call the same actual production logic. Keep assertion
expressions, inputs, expected values, domain loops, tick counts and failure cases
unchanged. Show before/after mappings and successful nonzero runs in the receipt.
Do not replace the helper with a test-side reimplementation. If the new seam cannot
express the same contract with lookup plumbing, retain a temporary production facade
and defer its removal; broader assertion migration requires a separate reviewed
contract-preserving unit-test change. Native recipes and performance oracles remain
frozen. This is not early execution of R16's UI-test migration.

### R04 — Make model ownership and identities explicit

**Depends:** R03. **Files:** `lib/models/program.lua`, `memory.lua`, direct model writers.

1. Separate initialization/default/migration helpers mechanically; retain save shape.
2. Introduce explicit project/song/channel arguments for internal operations; wrappers
   may resolve selection once. Keep editing target and playback target distinct.
3. Define project generation and targeted pattern/scale/device revision counters.
   Enumerate invalidators for direct edits, undo/redo, load/new, copy, recording,
   parameter actions and modulation before consuming a revision in any cache.
4. Migrate one writer family per slice. Bind memory state explicitly on project
   replacement; invalidate transient work without retaining old project tables.
5. Keep deep copies where isolation requires them; no table pooling in this card.

**Validate:** new/load/rejected-load/save, song-copy, channel/slot16 and global17,
mask precedence, history after wrap/branch/reload, recording and stale callbacks.
**Done:** ownership table and mutation map cover every writer; schemas unchanged.

### R05 — Separate edit transactions, history and persistence

**Depends:** R04. **Files:** `memory.lua`, `recorder.lua`, program save helpers,
`mosaic.lua` load/save paths, one page/control at a time.

1. Extract history ring and event handlers without changing logical indexing,
   serialization, maximum size, retained undo floor or legacy replay fallback.
2. Establish edit command inputs: explicit target, operation, value and before-state.
   Capture before mutation, apply once, record once, invalidate affected derived data.
3. Route representative manual and MIDI-mapped edits through the same command.
   Extend to remaining editor families; preserve hold/release timing and batching.
4. Extract validation/migrations/file operations. Test failed open/write/close and
   interrupted save/load using copies; keep autosave suspension and user data intact.
5. Only if R02 shows material history cost, add a last-event index keyed by the
   existing event identity. Correctly update it after truncate, wrap, undo/redo,
   clear, deserialize and project replacement. Benchmark before retaining it.

**Validate:** all memory/persistence/recording units and native anchors, old current
and 1.2.12 fixtures, mask clearing and all staged editor regressions.
**Done:** equivalent undo/save behavior, independent copied data, bounded history.
**Milestone A:** complete quick behaviour lane, targeted affected slow cases and
relevant performance workloads; scoped review of model/history/lifecycle before
optimizing downstream caches. No full slow-lane sweep.

### R06 — Extract musical resolution while preserving dispatch order

**Depends:** R04, R05. **Files:** `step.lua`, `pattern.lua`, `quantiser.lua`.

1. Write the current ordered transition table: global scale/track17, channel state,
   recording, parameter locks, probability, pitch/velocity resolution, note scheduling,
   and after-step recording. Check it against actual callback code and native oracles.
2. Extract stock-parameter precedence and pitch/mask resolution as functions of
   explicit inputs. Preserve nil/-1/0, truthiness, rounding and RNG call count/order.
3. Extract chord/arp descriptors separately from emission. Keep the established
   choice of values evaluated at scheduling time versus eventual callback time.
4. Move song-transition functions into a cohesive module, leaving facades in step.
   Do not change queue/copy/repeat/stop policy while moving them.
5. Run hand-derived domain matrices and old/new comparisons. The old implementation
   is a differential check, never the sole oracle for a newly discovered defect.

**Validate:** merge/pitch/scale masks, locks/trigless/probability, chords/strums/arps,
recording, song queues, boundary edits, external sync in both applicable time lanes.
**Done:** resolution can be tested without UI/devices; event ordering unchanged.

### R07 — Optimize pattern rebuilds using measured dependencies

**Depends:** R06 and complete writer/invalidation map from R04.

1. Benchmark `effective_lengths` and merge separately. First replace sorting with
   single-pass min/max/sum/count where formulas are equivalent. Preserve numeric
   accumulation order; test fractions/negative values and rounding boundaries.
2. Reuse effective lengths once per source revision/rebuild instead of recomputing
   per consumer. Avoid a global cache until its invalidators and memory bound are proven.
3. Remove repeated mode-string parsing and repeated step-mask lookups from inner
   loops using immutable local inputs. Preserve priority sources even when unassigned.
4. Introduce dirty song/channel tracking. Cover assignment, masks, source edits,
   range, scale interactions and currently inactive/edit-only slots.
5. Preserve per-channel publication within the per-song rebuild: build that channel's
   complete result, verify its target/revision, publish it, then yield as today. Do
   not wait for all 16 channels before publishing channel 1. Reject obsolete builds
   by target identity/revision. Whole-song atomic publication is outside this card;
   changing the publication unit requires a separate proposal and boundary proof.
   Retain M-PAT-BOUNDARY-001 and live-edit cases as admission guards.

**Validate:** merge all/skip/only and numeric modes, 1/16 targets, priority sources,
copy/undo/load, render states, boundary edits, input pressure and dense playback.
**Done:** benchmark benefit exceeds observed noise; no stale or cross-song output.
**Rollback:** reject caching/incrementality if its complexity buys no measurable gain.

### R08 — Make quantisation caches bounded and correctly invalidated

**Depends:** R04, R06; R07 accepted first to separate performance attribution.

1. Record the complete semantic key: project/song scale identity and contents,
   root/chord/degree/rotation/transpose, pentatonic settings and all current flags.
2. Remove unnecessary copies only for demonstrably immutable data. Test that callers
   cannot corrupt shared scales; otherwise return a copy at the boundary.
3. Replace repeated hashing with validated revision identity only when all writers
   participate. Never trust a version counter that direct assignments can bypass.
4. Compare simple bounded FIFO/LRU alternatives to existing eviction. Choose the
   simplest measured winner; specify capacity, eviction and reset explicitly.
5. Test >100 distinct keys, eviction/revisit, new/load/undo, scale edits and simultaneous
   channels. Check accidental globals and restore the source's random semantics.

**Validate:** complete quantiser matrices, M-SCALE-CACHE-001, scale-lock/merge/native
pitch cases, live edits and relevant PERF workloads. **Done:** equivalent pitches,
bounded memory, measured benefit. **No-go:** new stale-cache failures or missed writers.

### R09 — Repair and simplify cooperative scheduling and UI invalidation

**Depends:** R05–R08. **Files:** `scheduler.lua`, callback sites, UI refreshers.

1. Specify current scheduling semantics: monotonic job IDs, deterministic update
   order, newly created jobs, yielding, cancellation during a pass and exceptions.
2. Reproduce cancellation/count defects with composed modules and a native observable
   consequence where behavior changes. Resolve baseline-defect treatment first.
3. Extract scheduler storage from policy. Consider append order/tombstones with
   bounded compaction to avoid sorting each tick; preserve snapshot semantics.
4. Use stable keyed refresh/debounce functions bound to the correct project/page or
   song target. Cancel stale refreshes on lifecycle changes. Do not coalesce musical
   events, history entries or required press/release callbacks.
5. Preserve diagnostic error propagation and cleanup. Stop/cancel must remain
   responsive during large backlogs; integrate the existing external-backlog hardening.

**Validate:** scheduler cancellation/error matrices, paint race, tooltip/autosave,
memory redraw, editor flicker, pattern boundary, input load and overload recovery.
**Done:** bounded work, correct active counts/order, responsive UI and audible output.

### R10 — Extract owned playback lifetimes and clock transitions

**Depends:** R06, R09. **Files:** `m_clock.lua`, `m_lattice.lua`, `step.lua`, `m_midi.lua`.

1. Inventory each pending action: onset, release, arp, slide, transport send. Record
   owner, time domain, generation, cancellation and terminal cleanup semantics.
2. Extract voice ownership with captured originating route/player and identity.
   Distinguish cancellation of future onsets from releases already owed. A simple
   generation mismatch must not suppress a necessary Note Off.
3. Extract slide storage/interpolation/retiming and arp lifetime modules behind the
   old API, one at a time. Preserve slide replacement, endpoint-before-note and wrap.
4. Model existing start/stop/reset/continue/SPP/repeated-start/source-switch transitions
   explicitly. Panic retains the agreed sweep semantics; it is not a universal Stop.
5. Optimize delayed-action storage only if profiling justifies it. Keep deterministic
   ties, bounds and overflow diagnostics. Never drop releases or skip logical pulses
   to make a workload appear fast. Avoid a heap unless it outperforms simpler storage.
6. Do not rewrite the lattice and lifecycle in one slice. Any algorithmic clock change
   requires separate absolute-phase and runtime-boundary proof.

**Validate:** all timing/external-sync/slide/arp/panic/hotplug/recording cases, same-pitch
overlap, route changes with pending work, full outputs in supported MIDI/audio/CV/ii
profiles, capacity guards, stop backlog, endurance and PERF-003/008.
**Milestone B:** complete quick behaviour lane, the union of affected slow cases and
relevant performance gates, plus scoped ownership/timing review. No full slow-lane sweep.

### R11 — Separate device descriptors, parameter slots and output adapters

**Depends:** R10. **Files:** `devices/*`, `m_midi.lua`, parameter parts of `step.lua`.

1. Define descriptor fields from actual existing configs: stable ID, slot, type,
   domain/sentinel, encoding and applicable output. Inventory n.b. dynamic parameters.
2. Extract descriptor loading/validation, slot binding and protocol emission. Keep
   existing IDs, order, CC/NRPN sequences, 14-bit encoding and Digitakt exception.
3. Replace magic slot lookups with named constants/descriptors preserving numeric
   identity. Do not reorder saved mappings or serialized parameter slots.
4. Separate keyboard/CC/transport ingress from player dispatch; reuse captured owner
   lifetimes from R10. Handle hotplug/config failure according to existing contracts.
5. Prove that an additional descriptor uses this boundary without page/clock-specific
   branches. Use a test fixture, not a new undocumented user feature.

**Validate:** codec finite domains, all slots, map targets/channels, config failures,
recording, NRPN/panic/hotplug, n.b./JF routing and PCM/CV/ii output cases.
**Done:** extensible configuration without musical/state logic in device adapters.

### R12 — Simplify pages and controls around shared edit commands

**Depends:** R05, R09, R11. **Files:** pages, controls, `press.lua`, `m_grid.lua`, UI.

1. Extract channel-editor sections by cohesive behavior: selection/navigation,
   masks, locks, device params and history. Keep construction order and callbacks.
2. Move shared edit logic into R05 commands, one page family at a time. Encoders,
   grid gestures and MIDI mapping should reach the same semantic operation.
3. Introduce small view models for displayed values/LED states; keep volatile fields
   explicit. Invalidate only dirty views and respect the established redraw cadence.
4. Centralize only gestures already proven equivalent. Preserve source/destination
   press order, holds, shift combinations, release timing and disconnect behavior.
5. Remove dead paths and wrappers after checking every include/caller and native
   page path. Avoid a broad cosmetic rewrite or an unrelated UX redesign.

**Validate:** all navigation/gesture/page/mapping cases, raw framebuffer/LED and actual
browser assertions, tooltips/dashboard, staged flicker/mask regressions, PERF-004.
**Done:** no changed gestures or visual contracts; measured redraw/input cost retained.

### R13 — Tune allocation and resource bounds only where still justified

**Depends:** R07–R12. **Change:** measured hot spots only.

1. Repeat R02 profiles. Remove no-longer-useful optimizations from the candidate list.
2. Bound caches, pending work and diagnostic buffers. Test capacity/exhaustion,
   recovery and repeated project/device lifecycle; clear retained references.
3. Consider scratch buffers or precomputed parameter IDs only in hot paths with
   proved ownership and reentrancy safety. Never reuse a note container captured by
   a delayed callback. Do not replace necessary persistence/history copies blindly.
4. Evaluate GC behavior with normal and long runs. Keep or alter Stop's full collection
   only based on measured latency/memory and lifecycle semantics; do not disable GC.
5. Preserve service, output quality and memory budgets simultaneously. Publish each
   accepted optimization's benefit and cost; revert speculative micro-optimizations.

**Validate:** full performance matrix, ten-minute endurance, repeated load/reload,
large histories and all behavior families affected by changed buffers/data structures.

### R14 — Final cleanup, acceptance and review

**Depends:** all implementation cards.

1. Remove obsolete wrappers, duplicate logic, accidental globals, unused locals and
   explanatory comments that no longer match code. Keep third-party boundaries clear.
2. Run syntax, collection and unit/integration layers; verify contract migration map.
3. Run the complete behavior matrix on the final immutable candidate, every required
   profile/lane and the standalone constrained performance jobs. Verify all artifacts,
   source identities, outputs, repeats and unrun counts. Compare to accepted baseline.
4. Check all absolute gates as well as regression comparisons. A “passed previously
   -> passed now” comparison cannot excuse an existing red or missing requirement.
5. Use the runbook's scoped Paranoia review budget with the current Mosaic review
   policy (Claude Opus unless later user steering supersedes it). Address substantive
   findings; rerun only affected checks after fixes, broad gates if the impact requires.
6. Publish a concise final report: changed contracts, benchmark deltas,
   compatibility, retained limits and rollback revision.

This R14 run is the code-refactor phase's single full slow-lane sweep. Do not spend
that sweep while production edits remain expected.

**Done:** every applicable behavior/performance test passes, no unknown tested-source
drift, and no unowned functional failure remains. If any required
gate is red or unavailable, state “not accepted” and its exact owner/recovery step.

### R15 — Optional follow-up: feature-extension examples

**Depends:** R14. **Documentation plus disposable/test-only examples.**

Write three worked recipes with exact extension points and tests: a new parameter
descriptor; a new editor command with undo/save support; a new output adapter using
existing supported semantics. Each recipe covers domains, validation, ownership,
invalidation, persistence compatibility, rendering and runtime output assertions.
Demonstrate one descriptor/command in test fixtures without adding production UI.
Update the architecture map and remove instructions that require private internals.

**Done:** a future executor can add a feature through a small documented boundary;
new production features still require their own specification and additive gates.

### R16 — Separate follow-up: execute the existing behaviour-test refactor plan

**Depends:** R14 accepted and every required behaviour and performance
test passing on the finished Mosaic code refactor. This is a subsequent test-side
phase of the requested goal, not a way to make the code refactor pass.

The existing plan is [Plan: a UI layer that makes the behaviour cases robust to UI change](../ui-abstraction-plan.md),
at `/home/andy/projects/mosaic-behaviour-tests/docs/testing/ui-abstraction-plan.md`.
It is revision 13, test-side only, and explicitly excludes Mosaic production code
and emulator changes. Its targets are `tests/behaviour/ui_map.py`, semantic verbs
in `ui.py`, frame-oracle integration, separate raw interaction-contract cases,
migration guards and a fail-closed recipe/result comparison gate. Follow its
section 7 steps 0–4 rather than creating a competing test-harness redesign.

1. Freeze the all-green post-code-refactor tree, case inventory, profiles/lanes,
   behaviour/performance oracle hashes and full results as this phase's baseline.
   Recount the current suite; the plan's 773 cases/104 files describe an older tree.
2. Reconcile its source anchors and assumptions against the completed refactor.
   Retain its exact-input/advance and oracle-preservation guarantees. It has a
   documented unresolved review state: its final review reopened class `3ebc3349`,
   revision 13 adds the missing verbs/catch-all, but that revision was not re-reviewed.
   Do not treat its historical review count as admission. Resolve this specific
   verb-coverage issue with the current Mosaic bounded review policy before
   test migration; do not reproduce the historical 14-round review process.
3. Execute its classification/map/verb/gate construction, then migrate one family
   at a time with the stated before/after evidence, contract-set ceiling, allowlist
   shrinkage and repeatability gates. Preserve independent raw interaction oracles;
   UI maps must not become self-validating golden-output generators.
4. Keep the Mosaic production tree fixed. Use fast layers and the complete quick lane
   for routine feedback, with slow cases targeted to each migrated family. Maintain
   every required behavior and performance contract during migration. The phase permits test restructuring,
   not dropped cases, weakened assertions, looser timing or reduced workload density.
5. Complete its drift drill, then re-run the full behavior matrix and constrained
   performance gates on the final test harness. Publish a separate completion
   receipt linking both the accepted code-refactor baseline and this migration.

The step 5 run is R16's only full slow-lane sweep, required because the behaviour
harness itself has changed after R14. Intermediate R16 migration steps use quick plus
targeted slow feedback only.

**Done:** existing UI-abstraction plan fulfilled, required suites still all green,
and raw interaction contracts retained. **Recovery:** revert only the current test
migration slice; never change production behavior to accommodate the abstraction.

## 7. Test and performance command cookbook

### Existing unit/integration starting points

These are verified files under `lib/tests/lib/`, not an exhaustive test selection.
R00 expands each row using the current registry and coverage matrix; the entire
unit/integration suite still runs at milestones. Do not import only a test file
whose runner dependencies are absent or infer collection from its filename.

| Cards | Existing suites to inspect and retain by contract |
|---|---|
| R03–R05 | `memory_tests.lua`, `memory_hardening_tests.lua`, `memory_mutation_killers_tests.lua`, `persistence_round_trip_tests.lua`, `recorder_tests.lua`, `recorder_extra_tests.lua`, `integration_tests/pattern_and_song_tests.lua` |
| R06–R08 | `pattern_tests.lua`, `pattern_hardening_tests.lua`, `pattern_edit_generated_hardening_tests.lua`, `quantiser_tests.lua`, `quantiser_mutation_killers_tests.lua`, `scale_merge_hardening_tests.lua`, `integration_tests/merge_mode_tests.lua`, `integration_tests/scale_and_quantiser_tests.lua` |
| R09 | `scheduler_tests.lua`, `scheduler_mutation_killers_tests.lua`, `grid_input_tests.lua`, `grid_controls_tests.lua` |
| R10 | `m_clock_tests.lua`, `m_clock_performance_tests.lua`, `m_clock_delta_killers_tests.lua`, `m_lattice_tests.lua`, `m_lattice_delta_killers_tests.lua`, `midi_output_transport_mutation_killers_tests.lua`, `integration_tests/clock_tests.lua` |
| R11 | `device_map_real_tests.lua`, `device_value_encoding_tests.lua`, `m_midi_tests.lua`, `m_midi_input_tests.lua`, `integration_tests/param_tests.lua`, `integration_tests/norns_param_lock_tests.lua` |
| R12 | `trigger_edit_page_hardening_tests.lua`, `channel_edit_page_ui_delta_killers_tests.lua`, `channel_edit_page_ui_mutation_killers_tests.lua`, `grid_controls_tests.lua`, `grid_input_tests.lua` |

### Already-decided refactor defect agenda

At R00 re-read `suspected-defects.md`; do not rediscover or overrule recorded user
decisions. The inspected ledger explicitly defers S28 duplicate grid-down handling
to the refactor (R09/R12), S45 recording wrap selection to the clock refactor (R10),
and latent S46 fractional quantization and S54 lattice delay/reset defects to R10.
It marks S13 unused table serializer, S19 unused paint-button code, and S21 dial
ID/getter for removal (R14, after confirming no new caller). Give each an isolated
change and the appropriate regression; characterize external impact before fixing
latent behavior. Existing characterization units may change to test the already
agreed correction, with an explicit contract mapping. Required native/performance
oracles stay intact. A latent issue explicitly deferred by an existing decision is
not an invented R01 blocker; a failing required test always is.

Run in WSL from the selected **immutable tested Mosaic tree**. These are planning
commands, not results. R00 must resolve actual paths/identities and inspect `--help`.
Do not paste placeholder paths or trust a Docker tag without recording its image ID.

```sh
cd /home/andy/projects/mosaic-behaviour-tests
git status --short --branch
git rev-parse HEAD
git submodule status --recursive
export MONOME_EMULATOR=/home/andy/projects/monome-emulator-behaviour-audio-crow
python3 tests/behaviour/run.py --list
python3 tests/behaviour/suite.py run --help
python3 tests/behaviour/perf_dense.py --help
python3 tests/behaviour/perf_input.py --help
python3 tests/behaviour/perf_overload.py --help
```

R00 writes a resolved environment file naming the admitted installation JSON,
required profile list, mod-root mapping, pinned norns source, image ID and a unique
run output root. The full command must include all required profiles, not just
`suite.py`'s default `base-midi`. Use repeatable fresh sessions and the current
declared candidate patches for opt-in mods; don't silently alter supplied mods.

Routine feedback uses these shapes. `$AFFECTED_REGEX` must be an anchored regex
generated from the card's explicit case-ID list. `$QUICK_PROFILES` includes profiles
applicable to controlled time; audio/Crow remain excluded because they require real
time. Slow selections use their actual required profiles and sources.

```sh
# Smallest loop: fast layers plus affected controlled cases.
python3 tests/behaviour/suite.py run \
  --output "$RUN_ROOT/quick-affected" --emulator "$MONOME_EMULATOR" \
  --experimental-install "$INSTALLATION" --norns-source "$NORNS_SOURCE" \
  --lanes controlled-experimental --profiles "$QUICK_PROFILES" \
  --case-pattern "$AFFECTED_REGEX" "${QUICK_MOD_CODE_ROOT_ARGS[@]}"

# Card/milestone quick gate: every controlled-applicable case, no filter.
python3 tests/behaviour/suite.py run \
  --output "$RUN_ROOT/quick-complete" --emulator "$MONOME_EMULATOR" \
  --experimental-install "$INSTALLATION" --norns-source "$NORNS_SOURCE" \
  --lanes controlled-experimental --profiles "$QUICK_PROFILES" \
  "${QUICK_MOD_CODE_ROOT_ARGS[@]}"

# Targeted slow gate: exact affected real-time cases only.
python3 tests/behaviour/suite.py run \
  --output "$RUN_ROOT/slow-targeted" --emulator "$MONOME_EMULATOR" \
  --norns-source "$NORNS_SOURCE" --lanes real-time \
  --profiles "$TARGET_SLOW_PROFILES" --case-pattern "$TARGET_SLOW_REGEX" \
  "${TARGET_SLOW_MOD_CODE_ROOT_ARGS[@]}"
```

Do not pass `--skip-fast-layers` in the quick loop. A complete quick-lane run will
not set `complete_regression_run`, because final completeness intentionally requires
both lanes; judge it by `status: finished`, `passed: true`, stable sources, nonzero
collections and no selected failures. A targeted slow report is likewise partial by
design. Store both as development evidence, never as the R14 final acceptance report.

The following unfiltered two-lane form is reserved for R14 after the production
candidate is frozen, and later for R16 after the test-harness migration is frozen:

```sh
# Variables and repeated --mod-code-root PROFILE=PATH arguments are resolved at R00.
python3 tests/behaviour/suite.py run \
  --output "$RUN_ROOT/full" --emulator "$MONOME_EMULATOR" \
  --experimental-install "$INSTALLATION" --norns-source "$NORNS_SOURCE" \
  --profiles "$REQUIRED_PROFILES" --output-mod-root "$OUTPUT_MOD_ROOT" \
  --real-time-workers 1 --controlled-workers 1 --sequential-lanes \
  "${MOD_CODE_ROOT_ARGS[@]}"
python3 tests/behaviour/suite.py compare "$BASELINE/full/suite.json" "$RUN_ROOT/full/suite.json"
python3 - "$RUN_ROOT/full/suite.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    report = json.load(stream)
summary = report['summary']
assert report['status'] == 'finished', 'Suite has not finished'
assert report['passed'] is True, 'Suite failed'
assert report['complete_regression_run'] is True, 'Incomplete regression matrix'
assert summary['sources_stable'] is True, 'Tested source changed'
assert summary['required_not_run'] == 0, 'Required cases were not run'
assert summary['case_runs'] > 0 and summary['layer_items'] > 0, 'Empty collection'
assert not summary['case_runs_failed'], 'Native case failures'
assert not summary['layer_items_failed'], 'Fast-layer failures'
assert not summary['layer_items_not_run'], 'Fast-layer omissions'
print('Complete registered regression suite passed; manual/performance closure is separate')
PY

python3 tests/behaviour/perf_dense.py --workload dense \
  --image "$PERF_IMAGE" --channels 1,4,8,16 --repeats 3 --seconds 8 \
  --output "$RUN_ROOT/perf-002"
python3 tests/behaviour/perf_dense.py --workload slides \
  --image "$PERF_IMAGE" --channels 1,4,8,16 --repeats 3 --seconds 8 \
  --output "$RUN_ROOT/perf-003"
python3 tests/behaviour/perf_input.py --image "$PERF_IMAGE" --output "$RUN_ROOT/perf-004"
python3 tests/behaviour/perf_overload.py --image "$PERF_IMAGE" --output "$RUN_ROOT/perf-008"
```

Do not use `run.py --require-all` as a passing command: the inspected implementation
always raises, even after inventory sections are complete, because the full campaign
gate is not implemented. The explicit `suite.json` check above proves registered
regression completeness only; it is not manual requirement/interaction coverage or
the standalone performance campaign. R00 inventories those original campaign gates,
and R01 must finish any missing T08/manual-closure validator with its fail-closed
tests before claiming admission. Do not replace that requirement with the suite flag.
Resolve or implement PERF-001/005/006/007 and endurance entrypoints through R00's
obligation mapping and R01's missing-recipe items. The four performance commands
above do not claim to cover all eight workloads.

For fast checks use the suite's existing pinned-dependency Lua/unit machinery,
including standalone Lua contracts and Python oracle modules. Do not run the old
Lua runner unprepared: it can auto-fetch or skip based on native filesystem paths.
Confirm nonzero collection, expected inventory, no hidden network dependency and
the source digest. A filtered case command is iteration evidence only. Final runs
must not use `--skip-fast-layers`, `--real-time-subset`, or `--case-pattern`.

### Measurement and comparison protocol

* Preserve exact budgets from current Mosaic/emulator performance contracts. The
  central ten-minute 120 BPM mixed workload retains p99 absolute error <=10 ms,
  max <=50 ms and final phase <=20 ms, with complete ordered output and no stuck
  notes. Import all existing relative timing, memory, service, queue and profile
  limits verbatim into R00's ledger; central limits alone are insufficient.
  Inspected performance contract: process-group peak below 768 MiB, final-five-minute
  RSS slope <=1 MiB/min, queue returns to quiet baseline within one bar, p99 service
  <=50% of shortest independent musical deadline and any service crossing 100% is
  a hard fail; same-host p99 regression <=10% and CPU/event regression <=15%, with
  only the existing documented noise-calibration rule. Dense runner currently uses
  0.5 CPU quota and cpuset 0; recalibrate for a different host. Source contract is
  `/home/andy/projects/monome-emulator-performance-integration/docs/delivery/PERFORMANCE.md`
  (absent from the inspected behaviour/audio emulator tree). R00 must bind the actual
  composed runtime/tooling that implements it. Toolkit/Matrix performance is deferred
  by existing user priority; preserve that explicit deferral and distinguish it from
  required non-performance modulation behavior. Do not silently drop any required test.
* Keep the constrained proxy's image, CPU/cgroup/memory configuration, clocks,
  sample workload, seed and capture settings identical. Record kernel, CPU facts,
  throttling, host load and actual runtime/mod composition. This is a constrained
  x86 proxy claim, not physical norns hardware performance.
* Performance jobs run serially on an otherwise idle host. Do not kill unrelated
  user processes; wait or label contamination. Suite worker defaults are unsuitable
  for timing qualification. Avoid background builds, reviews and other native runs.
* Run matched fresh baseline/candidate repeats (alternate order to reveal drift),
  retaining at least the workload's existing repeat count. Report every repeat,
  medians and spread, p99/max/phase, CPU, RSS peak/slope, service and queue recovery.
  Do not average away a failing repeat or choose the fastest run.
* Distinguish acceptance limits from improvement targets. Every absolute and existing
  relative gate must pass. Accept an optimization only when its intended benefit
  exceeds measured repeat noise without violating another metric. No arbitrary
  speedup promise or looser resource budget is added by this plan.
  Before each optimization declare one target metric and direction. Use at least
  three matched fresh runs (or the workload's larger required count). If candidate
  and baseline ranges overlap, permit one additional fixed batch of six matched
  short runs, retaining all results. For a conservative wall-time speedup claim the
  final candidate target range must lie wholly below the baseline range; otherwise
  mark the claim inconclusive and stop spending runs. A verified reduction in
  deterministic work/allocations can justify the optimization without a wall-time
  speedup claim, provided all absolute and relative gates still pass. If neither
  benefit is demonstrated, revert the speculative optimization. Long-duration
  qualification retains its required duration/repeats and is not shortened or
  repeatedly rerun to chase a favorable result. No failed gate is discarded by this
  improvement-estimation procedure.
* Re-run a contaminated comparison only after recording the cause and preserving its
  artifacts; never reclassify unexplained failures as host noise. Do not use logical
  time speed as proof of real-time timing. Compare no-instrumentation acceptance runs.

## 8. Review cadence, risks and stopping rules

Apply the local runbook's Paranoia settings with Mosaic's latest review-engine policy:
Claude Opus for future checkpoints, and the explicitly user-selected Claude Fable
for this P0 and its focused follow-up. Use medium effort, ten-minute
wall limit, one critique plus at most one focused follow-up for a review checkpoint.
Plan review uses `class_closure: false`, `claim_verification: false`; structural
repository assessment is not verification of new external premises. Integration
reviews use `converge: false`, `class_closure: false`. No dual-vendor requirement,
per-card mutation campaign or human certification. Save raw response, session,
reviewed digest and triage. A tool failure is not a completed review.

Review this plan at P0 for scope/gates/dependency safety. Milestones A and B receive
scoped integration review of their changed architecture, and R14 receives final
review; do not re-review unrelated original delivery milestones. Targeted fault
guards demonstrate detection of stale caches, lost release, wrong ordering,
cross-project callback and false-green collection, using disposable fixtures.

| Risk | Prevention / stop rule |
|---|---|
| A weak executor rewrites everything at once | Facade-first extraction, one card/slice, package receipt, dependency gates |
| A passing comparison hides old reds or unrun profiles | Frozen inventory plus absolute all-pass gate and campaign closure |
| Cache invalidation misses direct writes | Writer map before revision use; undo/load/recording/modulation tests |
| Reduced allocation aliases live notes/history | Explicit ownership; no pooled retained objects; delayed overlap tests |
| Scheduling “optimization” changes phase or event order | Independent clocks/output oracle, exact ties, real-time endurance |
| UI batching hides an edit or changes gestures | Preserve callback semantics; native frame/grid and resulting MIDI checks |
| Saved formats silently change | Frozen legacy fixtures, explicit migrations, failed-I/O isolation |
| Hardware/runtime issue is disguised as application logic | Minimal generic probes, pinned independent runtime candidates |
| Complexity increases with no measured benefit | Revert speculative optimization; document declined alternatives |

The executor's first action is R00 reconciliation. The first production refactor
card is R03, and it remains blocked until R01 admission is green. This ordering is
intentional: the desired outcome is a faster, simpler, more extensible application
with preserved behavior, not a large diff whose correctness must be rediscovered.
