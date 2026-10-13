# Mosaic harmony and musical-merge source freeze

Implementation base: `5384d0babb01fd5004bdcd6a95eaa8609aa72915` (`origin/main`,
2026-09-19). This record resolves the source drift and contradictions found by
the one-shot pre-code Codex Paranoia review `01a0ba0a-9a92-7970-9583-c6722f0e9fc0`.
It is the MM-01/H-01/PH-01 implementation boundary for the proposal documents.

## Existing source boundaries

- `pattern.get_and_merge_patterns` independently derives trig, note, velocity and
  length values. Priority note/velocity/length patterns can participate without
  being assigned as trig sources. Channel and step masks are applied at the end.
- `m_clock` advances a channel at its sprocket onset. A wrap is known before
  parameter processing and before the boundary note is prepared. MIDI-lock
  lookahead for the following onset is scheduled only after the current onset has
  finished.
- `step.handle` draws probability once, establishes the effective scale and
  transpose, draws pitch randomisation once, applies note-mask quantisation,
  quantised fixed note and final fixed note, then delegates root/chord timing.
  Existing delayed chord callbacks otherwise resolve pitch later.
- The Channel grid is a chronological 64-step trig/mask surface. It has no pitch
  coordinate. Pitch faders belong to the Pattern Note page. The Channel Note
  Dashboard and contextual norns inspection are the source-correct places to show
  final Harmony pitches.
- Channel norns pages currently clamp rather than wrap. The authoritative combined
  order is: Masks, Trig Locks, Memory, Clock Mods, MIDI Config, Note Dashboard,
  Merge Shape, Harmony. E1 clamps at both ends. E1 in a dirty child cancels and
  returns to its parent; a clean top-level feature page rejoins this order.

## Ordered musical pipeline and ownership

The runtime pipeline is:

`stored patterns -> legacy merge or Foundation -> active phrase selection ->`
`existing mask/random/fixed pitch precedence -> structural addition target ->`
`Pattern/Revoice/Ensemble placement -> existing scheduler and route`.

The Channel grid continues to show chronological active onsets, masks, velocities
and lengths. It does not invent a pitch axis. Harmony results are shown on the Note
Dashboard and in Source -> Merge/Foundation -> Phrase -> Scale/Key -> Harmony ->
Output inspection for the selected/touched step. Projection is read-only. Existing
grid edits retain their current source owner. `SELECTED` means admitted by the
active deterministic rhythm plan, `SCHEDULED` means accepted by the note scheduler,
`PLAYED` means an emitted event, `QUEUED` means a validated configuration awaiting
its boundary, and `PREVIEW` is reserved for a non-active draft.

Foundation is computed from assigned raw trig sources, never from a completed
Skip/Only result. Its planned trig/velocity metadata is inserted before explicit
channel/step masks. Note and length values continue through the existing resolver.
An explicit On trig mask may create an onset after amount/accent filtering and an
explicit velocity mask wins after accent.

## Deterministic version-1 policies

### Foundation and phrase

- Ranking version 1 is unsigned FNV-1a over
  `version|seed|song-slot|channel|binding|phrase|step`, sorted by hash then step.
  `phrase` is zero for Fixed variation. This gives a stable total order and nested
  amount supersets without drawing Mosaic's RNG.
- Effective amount is
  `round_half_up(add_amount * cycle_percentage / 100)`, followed by
  `round_half_up(effective_amount * eligible_count / 100)` admitted candidates.
  There is no intermediate floating-point percentage reuse.
- Flat is all 100. Build cycle `i/N` is `round_half_up(100*i/N)`. Answer alternates
  100,25 beginning with 100. Fill is 25 except the final cycle, which is 100. All
  shapes are `[100]` for one cycle. Editing any percentage makes Custom. Growing a
  Custom curve appends 100; shrinking retains its prefix.
- Version-1 persisted Merge Shape configuration contains mode, anchor pattern,
  amount, accent, gap, seed, ranking version, cycles, shape, explicit percentages,
  variation, keep-anchor-pitch, target kind, selected degree indices and Harmony
  material source group. Invalid or unknown versions reject the loaded project
  before active-project mutation. Missing configuration is Off.
- Degree selections are 1-based members of the effective ordered scale inventory
  after its existing merge/rotation semantics. The edit draft is source-revision
  checked. If no selected member exists after a runtime inventory change, eligible
  additions take the visible `TARGET EMPTY` legacy bypass until the source recovers.
- Phrase configuration activates before the first onset of the next channel cycle
  and before that onset's parameters are prepared. Activation invalidates unsent
  lookahead for the affected upcoming onset; already emitted parameter messages are
  not recalled. Exact lead-enabled controlled-time and real-time cases gate release.

### Harmony material and Pattern identity

- An Explicit chord target may reference only an enabled Ensemble group ID in the
  same song slot. It consumes the group's immutable **material** payload (template
  pitch classes and source revision), never its voiced or emitted pitches. This is
  upstream of placement and cannot self-reference. Missing, deleted, disabled or
  empty sources visibly bypass to Legacy; recovery occurs on the next source
  revision. Group copy preserves IDs within the copied slot; deletion clears
  referring targets atomically.
- Pattern mapping keys are effective relative values within a binding. A placement
  frame is additionally keyed by effective source revision and the applicable
  octave/transpose/pentatonic transform signature. Step scale/transpose/octave
  changes therefore form a new frame. Random, fixed/absolute note and chord-mask
  onsets bypass Pattern visibly. If aliases mapped to one role resolve to different
  pitch classes in one frame, mapped events fail closed (or use explicit Legacy
  fallback) until a compatible revision appears.
- Channel Note Dashboard snapshots distinguish planned, scheduled and last-emitted
  pitches. Redraw never evaluates probability, draws RNG, consumes Harmony history
  or predicts an unresolved onset.

### Solver and roles

- Solver policy version 1 uses hard range, pin, coverage, crossing, exact-unison,
  strict-leap and strict-direction constraints. Candidate MIDI notes are enumerated
  by pitch class inside each inclusive range; no result is clamped.
- Persistent solved roles are `v1` through `v5`, ordered by the last consumed
  pitches. Source IDs (`root`, `chord1`...`chord4`) remain separate and retain
  articulation order, velocity and mute meaning. On Anchor, candidates are assigned
  by ascending pitch then source ID. Added/removed sources are reassigned by the
  same deterministic optimum; equal pitches use source-ID order.
- Score components are exact non-negative integers: soft direction violation;
  feasible exact common tones moved; weighted semitone motion (bass weight 2,
  upper weight 1); maximum upper leap; sum beyond preferred leap; centre deviation;
  upper-spacing excess plus bass-separation deficit; ascending MIDI tuple; source-ID
  tuple. Smooth uses that order. Compact moves centre/spacing before common tones.
  Independent omits the common-tone component. Preset/order version is serialized.
- Initial movement and common-tone costs are zero; centre/spacing and stable tuples
  choose the Anchor. Unsupported policy versions fail validation. Search has a
  versioned node budget and returns `BUDGET EXCEEDED`, never a partial optimum.
- Revoice preserves its input pitch-class multiset and sounding source count. Its
  pedal must be an input pitch class. Non-chord pedal is Ensemble-only. Ensemble
  roles are Bass, Inner1..3 and Top and remain bound to explicit channels.

## Transactions, history and lifecycle

Harmony draft -> requested -> active transitions occur immediately while stopped
or at Mosaic's existing global song-pattern boundary while playing. Merge Shape
uses the same states but activates at the affected channel-loop boundary. Stop
makes the latest requested snapshots active for the next Start, clears transient
queues and resets phrase position to cycle 1/phrase 0. Save stores requested config,
not transient frames.

Group creation, membership changes, deletion and channel mode changes are one
song-slot-scoped history event containing before/after snapshots of the group table
and every affected channel reference. Undo or redo from an affected channel applies
the complete event atomically; a later edit truncates redo. Validation occurs before
requested or active state changes, including history restoration.

Cold load, New and reload clear solver/phrase history. Failed frames do not replace
last consumed pitches. Scheduling the first eligible event consumes a prepared frame
once; redraw, rests, probability failures, missing routes and mutes do not. Note Off
always owns the pitch and route actually scheduled by its Note On.

## Acceptance gates

MM-07 and H-06 require focused unit/integration suites, the full Lua suite,
controlled-time emulator behaviour, and every applicable real-time behaviour lane.
Missing lanes, admission failures or timing-threshold failures block completion.
The pre-code Linux baseline ran 1,701 tests with 1,700 successes and one existing
2.030 ms performance-threshold failure (`test_live_slide_admission_all_channel_parameter_slots`,
limit 2 ms); it must be rerun and distinguished from feature cost. The Windows runner
is inapplicable because existing tests invoke Linux commands.
