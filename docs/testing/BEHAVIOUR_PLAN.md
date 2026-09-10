# Mosaic behaviour and musical timing campaign

Status: Paranoia critique and focused follow-up completed; substantive findings resolved; execution in progress, coverage incomplete.
Requested 2026-09-07. Companion to PLAN.md, not a replacement for emulator delivery.

## Deliverable and ownership

Dedicated repository: `../mosaic`; worktree:
`../mosaic-behaviour-tests`, branch `codex/behaviour-validation`.
The user authorises local fixes and pushing this branch to the Mosaic repository.
Initial clone/worktree commit: `160d1ea7506773e65f298094e11d005dcb568dff`, matching
the existing emulator fixture. No repository AGENTS.md was present at setup.
Preserve its existing branches, working changes and project data. Inspect local
AGENTS.md before writing there. Record the selected starting commit, worktree path
and branch. Do not silently substitute the emulator's inspection clone for that
repository. If its revision differs from the existing fixture pin, inventory the
manual/source delta before reusing any result.

Mosaic owns `tests/behaviour/`: requirements, recipes, independent musical oracles,
test configuration, diagnostic fixtures, regression tests and its campaign state.
Use `docs/testing/BEHAVIOUR_PLAN.md`, `docs/testing/cards/`,
`docs/testing/decisions.md`, `docs/testing/bugs.json` and
`tests/behaviour/manual-inventory.json`. Names are proposed until T00 creates them.
This document is staged for initial transfer; the Mosaic copy becomes authoritative
and emulator state links to it rather than maintaining a second copy.

The emulator owns generic native adapters, clock control, input/observation API,
generic test-runner support and conformance. Mosaic tests must use its public
CLI/API or a documented generic client package. Do not import emulator-private
`tests/mosaic_*` modules as the permanent integration. Port useful existing test
recipes/oracles, preserving attribution and failed baselines. Generic installation
and conformance continue to pass with Mosaic/nb/matrix/toolkit absent.

Runtime and application pins are independent. Test the current Mosaic worktree,
including intentional dirty changes, not a hidden fixed fixture copy. Each run
records the actual source tree and loaded entrypoint. No refactor is part of this
campaign: first establish the validated behaviour baseline and fix demonstrated
bugs. Publishing or merging Mosaic changes follows the user's chosen policy.

MIDI, controls, display and all documented software behaviours are required.
Physical Crow/Sinfonion conversion and audible audio/n.b. DSP remain outside the
agreed scope; software Sinfonion messages and both matrix/toolkit MIDI modulation
paths remain required. Do not exclude MIDI timing merely because audio is excluded.

## What complete coverage means

T00 binds README.md AND cheat_sheet.html, full commit and content hashes. The user confirmed on 2026-09-07 that the source-header browser manual is derived from repository documentation. README.md and cheat_sheet.html are the authoritative inventory sources; the browser view adds no independent source obligation. Parse all
headings and stable anchors, then manually-by-code-review reconcile each section's
individual normative statements, options, gestures and limits into atomic
requirements. This is specification review, never manual product acceptance.
Pure installation prose, examples and future roadmap entries get explicit
classifications and reasons; no blanket section exclusions. Changes to the manual
invalidate its coverage reconciliation until new statements are classified.

Every requirement records ID, source anchor/line/text hash, intended behaviour,
preconditions, input recipe IDs, independent expected outputs, domain/boundaries,
interactions, owning card, required time lanes and implementation/run status.
Collection fails missing, duplicate or unmapped IDs, zero-case selections, missing
expected outputs, unsupported required capabilities and skipped/xfail cases.
Recorded evidence from emulator C08 is migration input, not automatic green status
for tests moved to another tree or a different Mosaic revision.

Cover every finite selector option and each state transition. Enumerate small
musical domains exhaustively: 128 grid cells, 16 pattern/channel/scale slots,
all scales/degrees/rotations, legal clock divisions and documented enum values.
For large numeric domains use min, min+1, zero/sentinel, default/interior, max-1,
max, below/above-bound attempts and every discontinuity; use full enumeration
where cheap under controlled time. Record selected domains explicitly.
For arbitrary-length input sequences, exhaustive means complete declared feature
coverage plus systematic exploration, not a claim to enumerate infinite histories.
Maintain a checked interaction matrix: all applicable pairs of behaviour families,
with named exclusions for meaningless pairs, and selected triples involving timing,
locks/recording, song changes and lifecycle. Fixed-seed state-machine campaigns
exercise longer histories and shrink failures to minimal physical-input recipes.
Coverage breadth must not be purchased by removing specific musical assertions.

## Oracles and bug decisions

Use literal note/CC/event tables and independently derived rational musical rules.
A slow reference sequencer/quantiser may exist only in tests: no imports of
Mosaic's generator, quantiser, scheduler, merge or persistence implementation to
compute expected results. Check reference functions against hand-worked examples
and mathematical invariants. Current output is never its own new golden.

Check the same action's grid/frame result and resulting MIDI where applicable.
Identify complete phrases, rests and silence windows; a positive prefix is not a
whole-loop assertion. No extra/missing notes, doubled transitions or stuck releases.
Use complete event logs with sequence checks, not just the snapshot MIDI tail.
Retain exact order; specify any musically unordered simultaneity explicitly and
still enforce note-off/retrigger, transport and parameter-before-note constraints.
Never sort away a race. A stopped transport must remain silent for a defined
interval. Image oracles declare layout and narrowly named volatile fields, with
independent semantic output checks. No human screenshot or listening approval.

Distinguish five failure classes: test/driver mistake, emulator fidelity defect,
Mosaic bug, specification ambiguity and host/resource failure. None earns a pass.
First preserve source identities, inputs, raw MIDI/frame/grid/logs and failure.
Reproduce with a minimal real-input case; isolate boundary faults using independent
non-Mosaic probes. Never fix a Mosaic failure by special-casing emulator behaviour.
For a Mosaic bug, save the failing test on the baseline and an isolated application
fix. Once verified, commit the regression and fix together on the campaign branch;
retain the old failure and exact before/after identities in the bug ledger.

Documentation/code/unit disagreements are explicit decisions. Documented behaviour
is the intended starting oracle; ambiguity needs resolution rather than selecting
the output that passes. Existing pending decisions: Lower note/velocity/length
merge formulas and the independent one-step channel gesture. Only dependent cases
wait. Existing candidate patches (memory preservation, note-off counts, mask
clearing, tresillo bounds, duration cutoff) must be checked for applicability to
the selected revision and revalidated individually then together. No blind apply.
The stopped scale highlight is an existing required display regression.

## Musical time contract

Maintain three values per event: ideal musical position as rational beats, intended
runtime tick position under the declared quantisation rule, and actual emission
time. Report musical quantisation error separately from scheduler jitter. An
implementation's off-by-one pulse is a candidate Mosaic defect, not automatically
an accepted expected timestamp. Existing C07 phase-minus-two note-off expectations
describe pinned dispatch and must be revisited against musical intent before the
refactor baseline is declared correct. Disputed rounding/phase semantics stay
visible in decisions; never broaden tolerances to hide a musical error.

Controlled lane D uses actual Mosaic and official norns Lua/native scheduling with
clock-source adapters only. It must control/declare clock.run/sleep/sync/cancel,
tempo/beat phase and transport, metro/redraw/debounce, monotonic elapsed time,
os.time/date and randomness, plus any relevant mod/JACK/OSC time source. No second
Mosaic scheduler, mocked step handler, frozen autosave or direct mutation of app
globals. Unsupported sources fail D capability admission instead of silently using
wall time. Advancing time has a deterministic quiescence/barrier definition,
bounded work, detection of zero-delay runaway and visible pending events.

Test exact boundary events at tick-1, tick, tick+1 and fractional positions where
the transport admits them; same-time ordering, phase resets, cancel-after-queue,
restart and tempo changes while work is pending. Seed random sources explicitly;
test ordinary unseeded startup separately. Three fresh-process repeats of each
admitted D case must agree on semantic events and visible end state. Replaying the
same wrong trace proves repeatability only, not musical correctness.

Real-time lane E/R remains mandatory for every software workflow and all timing
families. Capture at native MIDI emission using monotonic time, not browser receipt.
Map piecewise tempos and clock-source changes against an independent input-time
schedule. Verify transport/MIDI clock and external sync as well as note onsets,
durations, releases, CC slide trajectories and modulation phase. D/E differences
must be explained and resolved at their source; neither lane replaces the other.

Keep current central thresholds: 120 BPM ten-minute mixed workload, p99 absolute
scheduling error <=10 ms, maximum <=50 ms, final phase error <=20 ms; no missing
events, stale state, errors or leaked notes/clocks/processes. Also test declared
minimum/maximum tempo and representative odd/intermediate tempos and coprime
channel divisions. Record ppqn, rounding, load, host, intervals, quantiles and phase
versus expected event index. Swing/shuffle are intentional timing functions, not
jitter. Define cycle duration, offset polarity, feel/basis tables, symmetry or
asymmetry and accumulated error. Proposed tighter musical rounding bounds must be
specified from the intended algorithm before observing a candidate.

## Feature families and required edge/interaction cases

| Family | Required cases and independently observed consequences |
|---|---|
| F01 Startup/config/devices | Fresh/saved boot, all supported device types/config fields, absent device, invalid/truncated/duplicate/out-of-range config, assignment commit/cancel, wrong/missing ports, no unintended host writes; visible selection and exact MIDI routing. |
| F02 Navigation/display | Every grid/norns page, all keys/encoders, press/hold/shift combinations and thresholds, simultaneous holds/releases, tooltips/dashboard values, active/edit-only/empty indicators, live redraw, reconnect/focus loss, page wrap/clamp; test browser rendering against raw frames. |
| F03 Pattern editing | All16 slots and64 steps, group1/16/17/32/33/48/49/64 boundaries, trig create/remove/XOR/paint/preview/cancel/shift, note/velocity ranges including zero, group copying, length1/64/wrap/next-trig cutoff/reset, no cross-slot corruption. |
| F04 Rhythm generators | All five drum banks,128 patterns, tresillo8..64 and A/B asymmetry, every Euclid fill/length1..32 including fill>length and rotation, numeric primes/masks/factors and wrap. Check whole LED pattern, pitch/velocity at hits, silence at rests, paint composition and seeded random controls. |
| F05 Channels/merges | All16 channels, independent start/end/global17 lengths, empty/single/multiple assignments, two/three-pattern union/intersection/exclusion including triple overlap, all note/velocity/length modes and fixed-pattern override, ties/fractions/negative/clamped results, order independence where promised, mute/unmute while notes overlap. |
| F06 Harmony | All scale/root/degree/rotation/transpose/octave choices and boundaries,16 scale slots, active versus edit-only, global+local+lock composition, chromatic/raw/snapped/fully quantised masks, all/random/merged pentatonic switches independently and together, scale17 length/locks and held-scale option; exact voiced pitches. |
| F07 Masks/memory | Trig/note/velocity/length and all chord masks, channel defaults versus step overrides, unset versus zero, partial edits, clear-step/clear-all, undo/redo/endpoints/forget branching, record-generated history, isolation between channels/song slots, musical restoration after save/reload. |
| F08 Clocks/transport | Start/stop/reset and shift-stop, every division/multiplier, inheritance versus override, swing -50/0/+50 and interior, every shuffle feel/basis, live setting change application point, independent coprime channels, internal and external MIDI clock source changes, lost/jittered clock, tempo ramps/steps and pending work. |
| F09 Trig parameters | Every stock parameter and legal enum/range: probability0/100/intermediate, fixed/quantised/random/twos precedence, positive/negative/zero randomness and pentatonic interaction, fully-quantise override, root mute; seeded distributions plus exact allowed sets/counts. Device parameters: all supported types/CC bounds and malformed maps. |
| F10 Chord articulation | 0..4 extra voices, duplicate pitches, bounds, each shape/order/velocity rule, strum versus arp precedence, rests, signed spread/acceleration, tiny/long/fractional divisions, scale changes mid-strum, mute/stop/song changes during delayed notes, balanced releases on all channels/ports. |
| F11 Locks/slides | Global/channel/step precedence for params/masks/scales/transpose/octave, trigless on/off, set/edit/clear/undo, one/no/multiple endpoints, equal values, increasing/decreasing slopes, wrap on/off, step versus global slides, endpoint inclusion/rounding, no slide across song patterns, clock/scale changes mid-slide. |
| F12 Song | All90 slots, select/queue/copy/clear documented gestures, empty/active/playing indicators, repeats and sequence length bounds, mode on/off, reset-at-repeat/change options, per-sequence tempo, unequal channel lengths, queued switches at boundaries, switches during held input/recording/locks, no double/skipped transition. |
| F13 Recording | Arm/disarm, held-step and live notes/chords/CC, correct/wrong port/channel, quantised onset and duration, just-before/on/after boundaries, same-note overlap, note-off after disarm/stop/slot change, velocity-zero, sustain if supported by manual/config, capacity bounds, undo and round-trip playback. |
| F14 Mapping/protocol | PMAP learn/edit/remove/persistence, absolute/relative binary-offset limits, selected/all-channel routing, white-key mapping and degree/rotation/transpose combinations, all16 MIDI channels, running status/realtime/SysEx/partial packets, no accidental loopback, Elektron program/channel/reset options, Sinfonion software messages. |
| F15 Persistence | New/save/load/cancel/overwrite, names and file dialogs, PSET/PMAP/project/autosave, fresh/cold/reload continuity, malformed/truncated/unknown-version data, failed writes/permissions/interruption with prior data preserved, isolated worktree data, history semantics; compare reconstructed musical output. |
| F16 Modulation | Activate the pinned matrix/toolkit mods through native lifecycle and configure each via user controls. Verify both documented integration paths changing Mosaic MIDI device parameters, depth/rate boundaries and competition with manual edits/locks/slides. Use separately sourced mod expectations only for chosen trajectories; attribute a shape defect to the mod and routing/precedence defects to Mosaic. Full third-party mod conformance is not a Mosaic-manual requirement. No direct params:set as the positive user workflow. |
| F17 Recovery/performance | Panic, all-note-off accounting, interrupted client/backend, capture overflow/drop, reconnect, ten lifecycle cycles, mixed16-channel load with locks/slides/chords/recording, autosave intervals, bounded action/render latency, external clock stability, explicit overload failure without lost evidence. |
| F18 Composition/refactor | Manual's complete rhythm/harmony/melody/song/modulation recipes spanning several features, pairwise matrix and selected stress triples, reproducible generated histories, before/after restart equivalence and baseline/candidate/refactor semantic comparison. |

Any documented parameter not named in this table must still receive its own atomic
requirement in T00. This table is the minimum family scope, not the final count.
Audio-only settings get specific scope classification, never blanket exclusion of
their software routing, selection or persistence behaviour when relevant to MIDI.

## Executable stages / plan cards

Each card records inputs, exact commands, collected requirements, passed/failed
counts and artifact locations in Mosaic campaign state. An emulator gap gets a
linked emulator task and generic probe. Independent work continues when one
requirement is blocked. No routine approval between eligible cards.

### T00 — Worktree, manual inventory and baseline
Depends: repository location. Inspect Git status/remotes/worktrees/instructions;
create a dedicated branch/worktree from the agreed base without touching existing
changes. Bind manual/source/runtime identity. Populate atomic F01–F18 requirements
and domains, classify scope, reconcile prior emulator coverage and known bugs.
Run unchanged unit baseline and one real startup/edit/MIDI scenario against the
worktree. Output plan, inventory, bugs ledger and baseline evidence. Done only when
every manual statement has a disposition and the runtime proves which code loaded.

### T01 — Mosaic-owned runner and trustworthy observations
Depends: T00. Port existing recipes/oracles into Mosaic; expose needed generic
client functionality in emulator. Supply a single command with list/filter/run/
replay and require-all, stable case IDs and pinned external dependencies. Isolated
data by default; writes never target the user's live project. Record complete
inputs/MIDI, bounded snapshots, errors and cleanup. Inject wrong pitch, dropped
release, swallowed scheduler error, stale evidence and missing inventory; each
must fail the intended check. Done when baseline cases run from Mosaic with no
private fixture-driver dependency and all false-green probes are detected.

### T02 — Controlled time and temporal reference
Depends: T01 and generic clock boundary proof. The user authorises bringing
C16 capability forward alongside real-time work as needed for musical timing.
Inventory all runtime/mod time sources; implement native clock adapters and exact
advance barriers in emulator, independent of Mosaic. Establish rational-beat
reference tables, rounding decisions and generic timer/metronome/MIDI probes.
Run three D repeats and E comparison across resets, tempo changes and cancellation.
Do the bounded P5 clock review before declaring D admitted. Failed/partial D does
not stall independent E cases, but full campaign completion requires both lanes.

### T03 — Editing, harmony and existing defect migration
Depends: T01; add D after T02. Implement F02–F07 positive, negative, boundary and
interaction cases. Bring across existing native tests with fresh worktree evidence.
Validate known candidate patches against current source individually and combined;
record each bug's red/green evidence. Finish unresolved merge/one-step semantics
before affected cases can pass. Done when every owned atomic requirement passes
E and admitted D, including preserved MIDI ordering and complete phrase checks.

### T04 — Musical scheduling, locks, articulation and songs
Depends: T03 for editing primitives; T02 for D. Implement F08–F12 with independently
specified beat/pitch/CC tables, all enum options, edge timing and pair interactions.
Test tempo/phase changes, external sync, positive/negative shuffle/slide offsets,
record and stop races, pending chord releases and song-repeat boundaries. Diagnose
musical error separately from dispatch jitter. Inject wrong transition, one-pulse
duration shift and lost delayed note-off. Done when exact D and bounded E results
pass and every seeded fault fails; no correction by output-derived timing goldens.

### T05 — Recording, mapping, devices and modulation
Depends: T01 and required T03/T04 primitives. Implement F01/F13/F14/F16, both real
mod profiles and base MIDI profile. Establish event boundary ownership before
testing recording exactly on ticks. Verify recorded playback, controller routing,
all lock/mod parameter interactions and software program messages. Fix emulator
MIDI stream discrepancies with generic probes. Done when all owned requirements
pass with real inbound MIDI and exact/referenced resulting output in D/E lanes.

### T06 — Persistence, lifecycle and realistic compositions
Depends: T03; integrate T04/T05 as available. Implement F15/F17/F18, cold process
restarts, autosave, failed writes, corrupted data and isolation. Ten lifecycle
cycles plus ten-minute real-time mixed endurance meet the unchanged central gates.
Complete manual composition walkthroughs as executable recipes. Done when files,
musical output and visible state round-trip and faults cannot clobber valid data.

### T07 — Systematic bug hunting and coverage closure
Depends: T02–T06. Reconcile manual requirements against collected and executed
cases; fail omissions. Run full enum/domain matrices and seeded state-machine
histories with bounded lengths increasing from2 to32 to256 actions. Record seed,
generator version, legal-action model, coverage novelty and shrinking recipe.
Each family receives all declared pair interactions and timing-sensitive triples.
Expand specific counterexamples, not indiscriminate full Cartesian products.
Run scheduled long campaigns separately from the fast development subset; all
required domains must finish before declaring suite complete. Review the coverage
and timing oracle boundary with proportionate Paranoia, fix substantive findings.

### T08 — Refactor baseline and ongoing use
Depends: T07 and required emulator reliability gates. Freeze a correct Mosaic
baseline commit, tests/oracles, emulator lock and documented semantics. Run full
zero-skip D/E/B/R/F and unchanged unit selection from a fresh worktree. Produce
manual coverage report, fixed-bug ledger, runtime/profile limitations and commands
for focused versus full validation. Prove an independently seeded musical and
control regression is detected without changing test expectations. Refactoring
starts only after this gate; tests must remain implementation-independent. Later
refactors compare semantic output to this validated baseline AND independent
oracles, so matching an old bug is not treated as correctness.

## Review and execution mechanics

Requested initial review P-MOSAIC-PLAN: one Paranoia critique, medium effort,
ten-minute limit, class_closure=false and claim_verification=false for structure;
one focused follow-up if major changes or a blocking dispute warrant it. Retain
request, exact reviewed text hash, raw output and finding disposition. Inspect
installed schemas before invocation. No claim that a plan review verifies runtime
fidelity. P5 for clock changes and the existing emulator P2–P4 gates remain.
Avoid duplicate broad reviews of the same material; scope later review to new
coverage/oracle/runtime boundaries. No dual-vendor convergence or human testing.

Each stage's done condition is evidence, not elapsed time or assertion count.
The user need not repeatedly approve ordinary local fixes in the dedicated branch.
Unresolved credentials/path/publication choices block only dependent actions.
Keep emulator delivery state and Mosaic campaign state linked, with explicit
next actions and live process IDs across context boundaries. Publish no completion
claim while required capabilities, requirements or failing baseline decisions remain.


## Review clarifications: executable prerequisites and terminology

These clarifications resolve initial Paranoia findings and govern the cards above.

- **Manual sources:** both README.md and cheat_sheet.html are mandatory, including
  K3 fine control and page-dependent K2 / K1+K2 clearing gestures. The source-header
  short link is classified as a derived view by user confirmation on 2026-09-07. A README-only reconciliation is invalid.
- **Test lanes:** U=existing supplementary Lua units; I=generic native interface
  probes; E=actual Mosaic in real time; D=actual Mosaic under admitted controlled
  time; B=browser rendering and controls; R=real-time timing/endurance/lifecycle;
  F=deliberate fault sensitivity. D does not replace E/R or musical oracles.
- **Emulator cards:** C07 is completed native real-time clock/replay conformance;
  C16 is the controlled-time adapter, now scheduled after native clocks and the
  external-suite client rather than after platform releases. P5 is its bounded
  clock-boundary review. P2 reviews full emulator workflow/fault evidence, P3 WSL
  release/update/rollback, P4 Linux parity. Each allows one critique and at most
  one justified focused follow-up. This campaign's T00-T08 definitions and timing
  gates are self-contained; local emulator checkout paths are configuration, not
  an acceptance dependency on a particular Windows mount.
- **Time coherence:** D derives util.time, native clock seconds/beats/tempo,
  clock.sleep/sync, metros and os.time/date from one advanced logical epoch and
  a piecewise tempo map. Recording durations and the0.15s MIDI-map acceleration
  boundary must be tested across tempo changes against integrated beat intervals.
  A generic source-coherence probe checks elapsed seconds versus beats; real MIDI
  recording then verifies user-visible snapped note durations. Frozen wall time
  alongside advancing beats is an admission failure.
- **Random seed:** preserve Lua's PRNG and cached math.random references. Apply the
  native seed policy before script init, including every math.randomseed(os.time())
  reseed, and record the effective seed. Do not replace math.random. A normal
  unseeded boot remains a separate required case.
- **Source mounting and isolation:** before ANY T00 runtime boot, create a new
  session data root and a code root outside the source tree; symlink code/mosaic
  directly to this worktree. Native include/require names remain mosaic. No source
  copying, live-project data or emulator fixture snapshot is the app under test.
  Match recorded loaded mosaic/mosaic.lua hash to worktree bytes and bind all
  source/test files and submodules. Artifact directories stay outside code roots.
- **Dependencies:** initialise lib/nb at503be3ae9a7f4368a8bc35d6081795e0a130cadf
  (gitlink in baseline). For modulation tests, separately fetch matrix at
  41e11286bee8dbe48e8746e7a456400f93dc739a and toolkit at
  2e9fb56fe7b2b25bd6a0d80c40e82f7a7f9368a7 from their canonical sixolet GitHub
  repos, expose their actual code-directory names and activate enabled_mods via
  native system.mods before init. Record revisions and loaded-mod evidence.
  Base profile has no enabled mods. Tests configure modulation through public
  UI inputs, then assert Mosaic's actual outgoing MIDI. Generic parameter probes
  may diagnose a boundary but cannot replace those positive workflows.
- **MIDI fixture precondition:** provide exactly named virtual Norns2sinfonion
  alongside Emulator MIDI and Second MIDI. Sinfonion cases require nonzero expected
  program changes and exact values/order on that port; an absent port or empty
  capture is failure. All16 channels are required for output routing. Keyboard
  input-channel semantics need a decision: current source only handles raw channel1
  statuses and the manual is silent. Characterise ignored channels, but do not
  label all-channel keyboard support correct/defective without the decision.
- **Supplementary units:** run unchanged Lua tests in an isolated copy seeded with
  the pinned native norns Lua tree, preventing run_tests.lua's latest-release
  download. Bind the runtime installation hash and Lua5.3 version. Fail unexpected
  network fetches/missing data. Never replace the user's unit artefact directory.
- **Errors:** retain matron stdout/stderr and fail on Mosaic's caught Coroutine
  error diagnostic even when the runtime continues. Native exceptions remain
  structured failures. Check logs through shutdown, not only until an assertion
  passes. T01 includes an injected caught scheduler failure proving this gate.
- **Existing defects:** docs/testing/bugs.json and decisions.md are executable
  inputs to T03. Imported candidate patches and their hashes live under
  tests/behaviour/candidates; their provenance records emulator baseline bundles.
  Reproduce against this worktree before committing each fix. Pending publication
  approval wording is superseded: the user authorises pushing this branch.

Review outcome: focused follow-up `d8e019ad-c0ba-4074-a2c7-1341b09a13ce` found no consequential plan-level gap. This admits execution, not coverage completion. Inventory Sinfonion commands 5–10 as init-only unless a documented runtime contract supplies another requirement.

Review engine policy (2026-09-10 user steering): all future Paranoia critiques and follow-ups use Opus only. This supersedes the 2026-09-07 Codex-only instruction; completed reviews remain historical evidence.


## Native MIDI hot-plug panic edge domain

M-PANIC-011 through 014 cover removal before/during a stopped panic crossed with
reconnection during/after its sweep. Inputs are actual grid and MIDI device events.
Native connection timestamps must prove each intended overlap. Two unaffected
ports emit all 128 pitches on all 16 channels in order. A port absent at invocation
gets no new sweep job; a port removed during the job emits only its connected
prefix and, if restored before completion, its remaining suffix. Missed messages
are not replayed. Edge counts are tied to the unaffected port within one pitch
group because the device transition can interleave within its 16 sends. At removal,
port 1 may lead port 2 by up to 16 messages but cannot trail it: panic jobs are
created and resumed in ascending port order. The oracle enforces that direction.

Every case checks restored keyboard input, a subsequent full sweep on all ports,
unchanged page LEDs and the authored melody. The full native export is accounted
for; snapshot tails are only used to schedule interactions. Independent oracle
tests remove, duplicate, reorder/change or misplace events and transition intervals.
These cases extend PANIC-GESTURE and NAV-PAGES. They do not complete the broader
active/pending musical, recording, song-transition or lifecycle interaction matrix,
or admit controlled time. Evidence is in `hotplug-validation.json`.

## Audio/Crow scope amendment — emulator f301e76

The user expanded the behaviour campaign to the newly integrated audio and virtual Crow functionality. [AUDIO_CROW_REFACTOR_SCOPE.md](AUDIO_CROW_REFACTOR_SCOPE.md) is the authoritative additive X00–X06 plan, with 22 initial regression families in [audio-crow-scope.json](audio-crow-scope.json). For its named supported profiles it supersedes earlier audio/n.b. DSP exclusions in this document. Existing MIDI/manual requirements remain mandatory. Audio/Crow require real-time evidence; controlled Lua time does not certify them. The broad refactor is gated on both campaigns. All new families are planned, not executed; existing emulator fixture passes do not count as current Mosaic-worktree coverage.


## Critical refactor prerequisites: locks, trig parameters and scale merging

User priority confirmed 2026-09-08. These are already required by F05/F06/F09/F11
and F18; the following makes their interaction obligations explicit. Owners remain
T03 (editing/harmony), T04 (musical scheduling/locks), T05 (recording/modulation),
and T08 (refactor admission). This is a required todo list, not passing coverage.
Complete these before the broad refactor; isolated parameter tests are insufficient.

| Required interaction | Extensive regression obligations |
|---|---|
| Parameter locks × stored/global/channel/step values | Every supported parameter type and slot; Off versus zero and extrema; set/edit/clear/undo; stored recall before first lock before note; equal values, adjacent locks, unlocked steps and original-value restoration where specified; edit/clear/reassign while pending; preserve MIDI Off does-not-send/does-not-cancel contract. |
| Trig parameters × locks and probability | Every stock enum/range with boundaries and seeded randomness; parameter precedence and independent slots; active, inactive, probability-accepted/rejected steps with trigless on/off; recorded locks overwrite the intended steps only; clearing or reassigning a slot cannot retain old behaviour. |
| Scale merging × quantisation and scale locks | Explicitly map manual pattern-note merge formulas and merged-pentatonic behaviour alongside global/channel/step scale composition. Cover every merge mode, two/three source patterns, no/single/double/triple overlap, ties, fractional/negative results, fixed assigned/unassigned priority sources and assignment order where meaningful. Verify literal resulting MIDI pitches, not only scale membership. |
| Scale merging × masks, transpose, degree, rotation and octave | All finite scale/slot/setting choices in domain tests; targeted combined boundaries around octave/MIDI limits. Distinguish raw/snapped/fully-quantised masks and all/random/merged pentatonic switches; cover all switch combinations. Inactive note data, source edits/unassignment, scale edits, active versus edit-only slots and song copies must invalidate the correct cached result without changing another channel. |
| Locks/slides × musical time and lifecycle | No/one/multiple/equal/ascending/descending endpoints, adjacent chains, non-1 ranges, wrap on/off and no cross-song slide. Endpoint-before-note ordering; no duplicate/stale writes after replacement, clear, reassignment, stop or song change. Combine fractional division, swing/shuffle and live tempo/range changes; preserve pending note releases and continuous intended parameter motion. |
| Scale changes × delayed voices and recording | Scale-lock hold-until-wrap option, replacement locks and probability-rejected steps; global track17 versus per-channel boundaries. Change merged pattern/scale while chords, strums, arps and keyboard notes are pending. Verify intended pitch application point, unchanged owned releases, recorded/replayed pitch and first-press/final-release duration. |
| Required stress combinations | Merge + scale lock + random/trig parameter; trigless + slide + external-clock change; recording + lock edit + song transition; manual edit + modulation + lock restoration. Add channel/source/player reassignment with queued work and save/reload of each critical combined state. Audio/JF equivalents use the supported XA-009..014 profiles and their own output oracles; MIDI evidence alone cannot certify them. |

Expand small finite domains fully. Use explicit boundary cases and a reviewed
pairwise interaction matrix plus the named high-risk triples, avoiding an opaque
Cartesian explosion. Expected merge formulas, pitch tables, event order and
musical deadlines must be independently specified from the manual/agreed contract.
Use actual user inputs and full MIDI/grid/screen traces, plus PCM/ii/CV where
applicable. Controlled timing checks supplement real-time validation. Fault guards
must catch a stale merged scale, wrong precedence, missed/extra lock, wrong endpoint,
wrong pitch and release routed to a replacement owner. Candidate-specific passes
must be rerun on the accepted baseline before T08; no broad refactor admission
while required cases or confirmed defects remain unresolved.


## Norns-class performance and musical load

User priority added 2026-09-10. F17 is expanded into a required automated
performance campaign before broad refactor admission. The emulator contract is
`docs/delivery/PERFORMANCE.md` in the general-purpose emulator repository. Monome
documents standard norns as quad-core1.2GHz,1GB RAM on CM3/CM3+ with a real-time
kernel. Those facts define a constrained proxy target, but x86 quota and QEMU wall
time must not be described as physical-norns measurements.

Mosaic performance scenarios must use real UI/MIDI inputs and exact MIDI/grid/screen
oracles while collecting process CPU, peak/slope RSS, queue depth, input latency,
frame age, note onset/release error, jitter quantiles and final phase. Cover quiet,
single-axis sweeps and high-risk combinations across1/4/8/16 active channels,
minimum/typical/maximum tempo and division, dense trigs/chords, lock density,
trigless locks/slides/trig params, scale merging/quantisation, external and internal
clock, live recording/editing, MIDI traffic, full-grid/screen updates, autosave,
reload and reconnect. Explicit triples include external clock+dense locks+rendering,
recording+playback+parameter updates, and scale merge+scale locks+random trig params.

The ten-minute real-time mixed run keeps the central10/50/20ms p99/max/final-phase
limits, exact event accounting and zero stuck notes. Constrained runs use the
emulator's768MiB process-group limit and calibrated CPU profile, require queue
return to baseline within one bar and final-five-minute RSS slope at most1MiB/min.
Candidate comparisons on the same host/runtime may not regress p99 timing by more
than10% or CPU per musical event by more than15% without a recorded calibration
showing measurement noise. P99 sustained work must use at most half the shortest
independently calculated musical deadline; exceeding the deadline is a hard fail.

Every failure is minimized and profiled before optimization. Retain it as a unit,
integration or behaviour regression at the cheapest faithful layer, then rerun the
combined musical case. Do not obtain green results by lowering event density,
dropping redraws, weakening timing or changing expected output. Base-MIDI is the
current priority; Toolkit/Matrix performance is deferred until the user restores
that priority.
