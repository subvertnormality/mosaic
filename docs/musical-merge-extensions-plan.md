# Musical merge extensions (MM-08 … MM-12)

Status: design contract for the MM-08+ card of `MUSICAL-MERGE-PLAN.md`
(proposal package, `docs/proposals/mosaic-ux-harmony/`). That card requires this
plan to be expanded "with exact common-time and fragment contracts before
implementing" and each extension to meet its entry gate. This document is that
expansion. Implementation base: `f908a553` (`codex/ui-reimplementation`, to be
fast-forwarded into `codex/1.4.0`).

The four extensions and their gates, from the proposal:

| Extension | Gate |
|---|---|
| Interlock | One-way dependency only, reject cycles; explicit common-time horizon for different clock divisions/ranges, swing boundaries and resets. Use a precomputed immutable plan, never callback order or the leader's random emitted result. |
| Phrase fragments | Define fragment wrap for non-divisible and short loops; preserve authored internal rhythm/data, explicit handling of differing lengths. Separate mode, not an implicit change to Foundation. |
| Passing-note freedom | Explicit structural markers and chord source; do not classify notes as passing from duration alone or claim automatic tonal resolution. |
| Silence-aware interlock | Separate from onset interlock. Proven gate/strum/cancel/sustain semantics and a bounded scheduling policy. |

Everything not stated here keeps the MM-01…MM-07 contracts in
`docs/mosaic_ux_harmony_source_freeze.md` and README "Merge Shape".

## 0. Shared rules

- **Off stays exact.** Mode Off, and every new field at its default, produce
  the identical merged pattern, MIDI, RNG consumption and lookahead behaviour of
  `f908a553`. A project saved by `f908a553` loads and plays identically.
- **Schema and migration.** Merge configuration gains `schema_version = 2`.
  Implement canonical migration in `lib/musical_merge/config.lua`, invoked on
  detached decoded data by the project load path before any live mutation.
  Missing configuration remains absent, retaining the existing Off fast path.
  Validate v1 with its existing validator first, then copy only its recognized
  semantic fields into a fresh v2 configuration and install the new defaults.
  Discard all unknown v1 keys, including nested target keys and keys whose names
  collide with newly introduced v2 fields: v1 never gave those keys semantics.
  Copy target fields according to target kind; ignored fields are not promoted
  into active v2 settings. Preserve recognized numeric values, ranking version,
  percentages and saved Harmony maps without reranking or rounding. Failure
  leaves the live project, transport and pending messages unchanged.
  Version 2 saves and validates against a closed, recursive field schema;
  unknown versions or unknown v2 keys reject before mutation. Canonicalization
  must be idempotent. Update version-gated runtime consumers, including
  `pattern.get_and_merge_patterns`, to accept canonical v2 Foundation settings
  while retaining the v1 ranking algorithm and all default-field behavior.
  The acceptance boundary is load-v1/save-v2/reload-v2 with unknown top-level
  and nested keys, collisions with each new field, Foundation enabled, and
  absent/explicit Off configurations. Compare pattern values, emitted MIDI,
  RNG consumption and lead-enabled lookahead with the pinned v1 baseline.
  The pinned baseline is `lib/tests/fixtures/merge_v1_baseline/`: v1 projects
  saved by `f908a553`'s own project save and that revision's observations,
  captured by `capture.sh` under the `f908a553` harness and identified by
  `MANIFEST.lua`; `lib/tests/lib/merge_v1_baseline_oracle_tests.lua` replays
  them through the candidate's production load/save and never regenerates them.
  New v2 fields and defaults:
  - `mode`: `off | foundation | fragments` (was `off | foundation`).
  - `interlock = {leader = nil, window = 0}`: leader channel 1..16 or nil
    (off); window 0..4 follower steps.
  - `space = {leader = nil, release = 0}`: **reserved and inert in this
    delivery** (§6): v2 validation accepts only exactly this value (leader nil,
    release 0) and rejects anything else, so no Space edge, admission or UI can
    exist; v1 keys that collide with it are discarded by migration as above.
  - `fragments = {size = 8, keep_anchor = false}`: size 4 | 8 | 16.
  - `structure = {markers = "off", group_id = nil}`: markers
    `off | anchors | every_4 | every_8`; group_id an enabled Harmony Ensemble
    group in the same song slot (required unless markers is off).
- **Ranking.** All new deterministic choices use the existing FNV-1a over a
  `|`-joined identity string, prefixed by a distinct tag so no new key can
  collide with a v1 Foundation rank key: `frag|…` for fragments. No new draw from
  Mosaic's RNG anywhere.
- **Activation.** All new fields are part of the one merge configuration and
  use the existing transaction: immediate while stopped, at the channel's next
  loop boundary while playing, `NEXT CYCLE` / `APPLIED` feedback, one undo
  event. Changing `mode`, `fragments.size` or the fragment identity fields
  (seed, variation, cycles) starts a new phrase epoch exactly as the existing
  epoch rule does for cycles/variation/seed/percentages.
- **Grid/MIDI agreement.** Every new decision is made in the working-pattern
  build (`pattern.get_and_merge_patterns`) or in `step.handle`'s existing
  pitch path, so the Channel grid projection and emitted MIDI read the same
  plan. Planners produce values and reasons only, never clock callbacks.
- **Masks and probability.** Explicit channel/step masks keep final precedence
  over every new decision (they are applied after, as today). Probability,
  mute and route failures never feed back into any plan, including another
  channel's.

## 1. Common musical time (used by MM-09 Interlock)

### 1.1 Nominal time

Nominal time is exact rational time in whole-note units, measured from the
**common origin**. It ignores swing, shuffle and host timing: swing moves when
an onset sounds, not which grid slot it occupies, so interlock decisions are
identical with swing on or off within the supported domain of §1.2 (a stated, tested property).

- A channel step lasts `d = 1 / (16 · m)` whole notes, where `m` is the
  channel's clock-mod multiplier: `value` for `clock_multiplication`,
  `1 / value` for `clock_division`, `1` for none (so `/1` is a 16th).
  Clock-mod values are converted to exact rationals from their decimal text
  (`5.3 = 53/10`, `2.6 = 13/5`, `1.3 = 13/10`, `1.5 = 3/2`), matching the value
  the sprocket division is computed from. This is the sole duration conversion:
  channel onset accumulation, gate endpoints, release margins and projection
  horizons derive from `d`; the master duration is this formula with `m = 1`.
  Arithmetic is on reduced integer fractions; no floating point enters a
  comparison. Acceptance must assert `/1 = 1/16`, `x2 = 1/32`,
  `/1.5 = 3/32`, `x5.3 = 5/424` and `/5.3 = 53/160` whole notes, and compare
  their numeric projections with `m_clock.calculate_divisor` and the resulting
  sprocket divisions. Arithmetic that cannot represent an exact intermediate
  must return an explicit unsupported result, never a rounded comparison.
- **Common origin.** Nominal time is 0 at transport Start, and becomes 0 again
  at every realign (a song-pattern transition that calls `realign_sprockets`
  with `step.reset_pattern`, which restarts every channel sprocket at step 1
  together). Both are the only instants at which all channel sprockets are
  known to be phase-aligned.

### 1.2 The schedule is a pure function of song data and self-owned counters

Nothing about another channel is read from callback-visible runtime state. A
follower's view of its leader is computed from **song data** plus **counters
and histories each channel owns about itself**, all indexed by nominal time, so
the result does not depend on the order the lattice runs sprockets within a
pulse (17 → 1 today; tests also run it reversed).

**Supported domain (stated once; every guarantee in §1, §3 and §6 defers to it).**
An admission is *supported* when neither the follower nor the leader has
`resync` set and no `PLAN LIMIT` applies. For every supported admission the
result is independent of sprocket callback order within a pulse and of swing
and shuffle, and equals what the replayed leader schedule plays.

**Unsupported-admission fallback (the one authoritative rule; §1.4, §1.5 and §3
defer to it).** An unsupported admission bypasses **Interlock only** for that
follower cycle, with the visible status `RESYNC` or `PLAN LIMIT` shown on
Result/Reason separately from any rejection reason. Everything else of the
Foundation pipeline runs normally and exactly as with Interlock off: gap
filtering and its `gap` reasons, the eligible set, FNV ranking, phrase-adjusted
Amount, Accent and masks. No other claim is made for an unsupported admission.
Acceptance, for each of `RESYNC` and `PLAN LIMIT`, with a nonzero gap and
partial Amount: the gap-rejected positions and reasons, the eligible and
admitted counts and positions equal those of the same configuration with
Interlock off, no `INTERLOCK` reason is recorded, and the bypass status is
shown.

#### 1.2.1 Transport-wide counters (state machine)

The transport owns, for every channel 1..16, whether or not any merge feature is
enabled (so enabling Interlock mid-play needs no history that was never kept):

| Event | Effect |
|---|---|
| Start (`prepare_start` / transport reset sets every step to 1) | origin serial += 1; every `k_c = 0`; `timing_c` captured; `resync_c = false`; every channel's cycle log (1.2.2) restarts with one entry for cycle 0 recording the configuration and the `merge_state` cycle/phrase that govern it. The first onset after Start is not a wrap (`step_cursor` with `first_run` keeps step 1), so it advances nothing. |
| Channel wrap (`step_cursor.next` returns `wrapped`) | `k_c += 1`. This is an integer increment done for every channel in the existing wrap branch, outside the merge-only condition; it changes no musical output. |
| Realign (song transition with `reset_channels`: `step.reset_pattern` sets every step to 99, then `realign_sprockets`) | New common origin at nominal master time `T_r` of that pattern boundary: origin serial += 1; every `k_c = −1` (the forced wrap at the next onset makes it 0 without counting an elapsed cycle); `timing_c` recaptured, `resync_c = false`; cycle logs restart, and the entry for the forced wrap's cycle 0 records whatever `merge_state` then holds — the phrase is **not** reset by this plan: a same-slot realign keeps the phrase position `merge_state` keeps (it only advances it at the forced wrap, as today), and a slot change resets it only through the existing `reset_song`. All later times in §1 are measured from `T_r`. |
| Timing change for channel c while playing (clock mod, start/end, or global pattern length differs from `timing_c`) | `resync_c = true` until the next origin. |
| Global (pattern-boundary) activation of channel c's merge configuration while playing (1.2.2) | `resync_c = true` until the next origin. |
| Song-slot transition without realign | `resync_c = true` for every channel until the next origin: the new slot's data takes over mid-cycle at the pattern boundary, so no cycle-indexed schedule describes the split cycle. |
| Stop, project load, New | All counters, histories and caches discarded; `resync` irrelevant until Start. |

`merge_state` and its cycle/phrase counters are unchanged by this plan. The
cycle log copies them; it never derives them. Tests compare the logged values
with `merge_state` after every row of this table, and compare Off/default
playback with the base revision (first enable, last disable and re-enable
mid-play included: the counters and logs exist for every channel whether or not
any feature is on, so enabling needs no history that was never kept).

#### 1.2.2 Cycle log (what governed each cycle, keyed by nominal time)

Each channel keeps a log of **segments** `{at, config, cycle, phrase}` for the
current origin. A segment says: from nominal time `at`, onsets of this channel
use `config` at phrase position (`cycle`, `phrase`) — the values `merge_state`
holds at that moment, copied, not computed.

- At every wrap of the channel (1.2.1), after `merge_state.on_cycle_boundary`
  has promoted any queued configuration and advanced the phrase, the channel
  appends `{at = k·P_c}` for the cycle `k` it starts. This runs for every
  channel; for channels without merge state it records Off.
- A global activation (`on_pattern_boundary` promoting a `global_queued`
  configuration — only cross-feature repairs such as deleting a referenced
  Harmony group while playing) changes a channel's configuration mid-cycle at a
  pattern boundary, where swing can move individual onsets to either side of
  it. No cycle-indexed schedule describes that, so instead of logging a
  mid-cycle segment it sets `resync = true` for that channel until the next
  origin (1.2.1). Every logged segment therefore starts at a channel wrap, and a
  configuration is constant within a supported cycle.
- A stopped apply only happens before Start, so it is the Start segment.

**Retention:** segments covering the last 64 cycles of the channel. A query
that needs an older segment (possible only when the support interval of 1.4
reaches further back) makes the admission bypass with `PLAN LIMIT`.

#### 1.2.3 Evaluating a leader cycle

While neither channel has `resync` set, leader cycle `i ≥ 0` occupies nominal
`[i·P_l, (i+1)·P_l)` with `P_l = N_l·d_l`, and its playable position `n`
(1-based) has onset `i·P_l + (n−1)·d_l`. This is the sprocket's own schedule
from the origin (every step lasts exactly `d`; swing only displaces the audible
onset), so it holds with swing and shuffle and independent of host timing.

- **Governing segment at an onset `o` in leader cycle `i`.** Within the
  supported domain the only transitions that change a leader's configuration or
  phrase are its own channel boundaries (global activations resync, 1.2.2), so
  the frontier is the cycle index: boundaries with index ≤ `k_l` are *applied*,
  later ones *pending*.
  - If `i ≤ k_l`, the logged segment of cycle `i`.
  - Otherwise it is **predicted** from a pure copy of the leader's current
    `merge_state` record by replaying the pending boundaries `k_l+1 … i`, each
    exactly as `m_clock` applies it: `on_cycle_boundary` runs **only if** the
    channel has a saved `musical_merge` or `merge_state.has` is true for it
    (`m_clock.lua:617-620`), so a channel with no configuration never advances a
    phrase and a first enable mid-play starts exactly where the code would.
  - **Pending global activations exclude the pair outright.** From the moment
    a `global_queued` configuration exists for the leader or for the follower
    (queued by `request_global` while playing), every admission of that
    follower is unsupported (`RESYNC`), for every queried onset and gate, before
    any prediction is consumed; at queue time the follower is rebuilt (1.3), so
    its retained admission and next-onset lookahead are replaced by the bypass
    immediately. When the activation lands the channel's sticky `resync` (1.2.2)
    continues the bypass until the next origin. If the queued global change is
    withdrawn before it activates (undo, or superseded), the pair returns to the
    supported domain at the follower's next rebuild, because no configuration
    change inside a cycle ever happened. Thus no supported admission is ever
    decided while a mid-cycle configuration change is possible, in either swing
    direction.
  - A pattern boundary that will change the song slot or realign ends the
    origin: leader onsets at or after it are excluded from the query. The
    follower is rebuilt at that boundary by the existing
    `pattern.update_working_patterns()` call and re-plans against the new origin.
  The prediction for cycle `k_l + 1` equals the segment the leader will log when
  its boundary callback runs, and a configuration is constant within a cycle,
  so the answer is the same whether that callback has run earlier in the
  current pulse or runs later, including when swing or shuffle displaces any of
  the leader's callbacks: eligibility depends only on the queried onset's cycle
  index. Tested: every query with the leader's callback run before and after the
  follower's, swing and shuffle on and off, across a predicted queued activation
  and a predicted phrase-epoch restart inside the horizon, a leader with no saved
  configuration, a first enable mid-play; and, for global activations, a
  nominally earlier leader onset delayed past the activation and a nominally
  later onset advanced before it (swing and shuffle, both directions, reversed
  callback order), asserting the bypass from queue time
  through the next origin and recovery when the queue is withdrawn; supported
  results are identical and equal what the leader then plays.
- **User edits between prediction and activation.** If the leader's queued
  configuration changes after a follower predicted it, that apply is a leader
  change and rebuilds the followers (1.3); already-emitted follower onsets are
  not recalled.
- **Phrase position** is the governing segment's (`cycle`, `phrase`).
- **Leader anchors for cycle `i`** (the one authoritative definition; §1.3,
  §1.4, §3 and §7 derive from it): if the governing segment's configuration is
  Foundation with a valid anchor pattern, the positions `p` in the leader's
  playable range where the **currently stored** anchor pattern has a trig;
  otherwise none. Nothing else of the leader is read. This equals the set
  `foundation.plan` marks `anchor` for the same configuration and stored data,
  which a test asserts; no leader working pattern or plan is built. The existing
  recursive leader-plan ingress in the MM-09 implementation
  (`leader_query` building leader plans through `get_and_merge_patterns` with
  `merge_override`, `lib/pattern.lua:265-279`) is replaced by this anchor reader,
  and acceptance asserts that an admission performs zero leader-plan builds.

### 1.3 Freshness: when a follower plans

**Authoritative rule:** a follower's Interlock admission is computed
inside its ordinary working-pattern build, for its current cycle `j = k_f`
(output window `[j·P_f, (j+1)·P_f)`), every time that build runs. Grid
projection and MIDI read that one build, so they always agree. Mid-cycle
rebuilds for the follower's own edits recompute from the same inputs.

- **Leader edits reach followers.** Whenever `pattern.update_working_patterns`
  or `update_working_pattern` rebuilds a channel that is a leader in the
  current slot, the channels that follow it are added to the same rebuild set,
  with the same lookahead invalidation that an edit to the follower itself
  receives today (`scheduler:invalidate` for the follower's next onset). A
  pending asynchronous sweep therefore rebuilds leader and followers in the
  same sweep, leaders first. The sweep may yield between channels; until the
  follower's own rebuild runs, its working pattern keeps its previous admission,
  and grid and MIDI both read that working pattern, so they still agree. An
  already-emitted follower onset is not recalled.
- **Leader applies** (a queued or stopped merge-configuration change on a
  leader) also rebuild its followers, so predictions (1.2.3) follow the new
  queue.
- **Acceptance for this rule (controlled time):** follower edit mid-cycle;
  leader source edit mid-cycle with unequal cycle lengths; an edit landing
  between the leader's and the follower's rebuild within one yielding sweep; a
  synchronous `update_working_pattern` while a sweep is pending; a sweep that
  completes after a newer edit (stale completion must not overwrite the newer
  admission — the sweep rebuilds from live data, so the last build wins). Each
  asserts the retained admission until replacement, the lookahead invalidation,
  and that grid LEDs and emitted MIDI agree at every step.
- **What Interlock reads (performance).** Interlock builds no leader plan.
  Its input is the leader's anchors, which by §3 are the anchor pattern's trigs
  inside the leader's playable range under the governing configuration, before
  masks. For every leader cycle in the support, logged or predicted, they are
  read directly from the **currently stored** anchor pattern and the governing
  segment's configuration — the same values `foundation.plan` marks as `anchor`
  from the same inputs (a test asserts equality for every configuration shape in
  the Interlock suite). Interlock is defined against the leader's anchors as
  currently stored, projected over the support; it does not reconstruct an
  anchor pattern as it was before a later edit. Anchor-pattern edits go through
  `update_source_working_patterns`, which rebuilds the leader and so its
  followers (above); any other anchor-pattern write reaches the follower at its
  next build. Cost per admission: at most 64 leader cycles × 64 stored anchor
  values plus the membership checks.
- **Wrap-rebuild memo (performance).** No leader state or leader plan is
  cached across pulses: every pulse recomputes the Interlock admission
  (above) from live data. Every working-pattern build (edits, follower
  rebuilds, sweeps, stopped applies and the clock's wrap rebuild
  `update_working_pattern(c, song, true, pulse)`) seeds and may reuse
  follower-side work from a memo per song pattern and channel that is
  validated by **content** on every use, so the first wrap after Start is
  served by what the stopped builds computed. Rebuild requests are not
  relied on: source arrays and step masks are written in place without one
  (`program.update_working_pattern_for_step`, the memory event handlers).
  The legacy source merge (before Foundation and masks) is reused only when
  its merge modes, its source visit order (number, enabled value and source
  table identity, in iteration order), each source's trig class at every
  step (`== 1`, `== true` or neither), the positive step trig masks, and the
  note, velocity, length and note-mask values at every step the merge or
  `foundation.plan` can read (trig and positive-mask steps; all 64 under a
  pattern-priority mode) equal the stored copy, numbers also by subtype
  (`math.type`). The Foundation plan is then reused only on such a hit (a
  miss replaces the entry and drops its plan) and when its 12 remaining
  inputs (loop start and end, anchor, effective amount, accent, gap, seed,
  song slot, channel, binding, ranking phrase, ranking version) are equal by
  value and subtype and the Interlock filters are the same ordered list with
  exactly the same blocked sets. A hit returns a fresh copy of the pristine
  merged pattern, so nothing written to a returned working pattern reaches
  the memo, and a plan with a fresh top level (the build adds its own
  fields there) whose sub-tables are shared: plan sub-tables are immutable
  once `foundation.plan` has built them (no Mosaic code writes them; a test
  plays, inspects and renders Result/Reason with them read-only).
  Within one lattice pulse (the token m_clock's wrap branch passes down, a
  fresh table per `Lattice:pulse_all`, so a pulse that raises shares nothing
  with the next) the followers that wrap together also share work: equal
  source snapshots are one object, validated once per pulse, and one
  Interlock admission serves every follower whose key matches. The key holds
  every admission input that code running inside a pulse can write (the
  follower and leader merge_state records, the timeline counters, resync
  flags and origin serial, the song table and slot, the origin end); the
  rest (pattern data, ranges, clock mods, assignments, saved configurations)
  is written only by input handlers and editors, which never run inside a
  pulse (a pulse runs to completion in one coroutine). Never shared: a
  global queue on either channel or a queued leader configuration. The
  follower's timing check runs on every build.
- **While stopped** `j = 0` and `k_l = 0`: the stopped grid preview shows what
  the first cycle after Start will play, using any queued/requested
  configuration as the entry at 0.
- Off (no leaders configured anywhere in the slot) adds no rebuilds, no
  admission work and no change to musical output. The §1.2.1 counters and the
  §1.2.2 cycle log are always maintained (one integer increment and one bounded
  ring append per channel wrap) so that a mid-play enable has history; that
  bookkeeping is the only Off-path cost and a test asserts Off output is
  identical to the base revision.

### 1.4 Query support and bounded work

The follower cycle is the output horizon, not the complete query. Leader cycles
are evaluated over the **support** interval
`[j·P_f − window·d_f, j·P_f + (N_f − 1)·d_f + window·d_f]` — from the follower's
first onset to its last onset, widened by the window — clipped at the origin
(no leader cycles before 0) and at a known origin end, so an anchor in the
preceding or following leader cycle within the window is found. The number of
leader cycles counted is `floor(high / P_l) − floor(low / P_l) + 1` over that
closed interval. For an output onset `o`, Interlock inspects leader
anchors in `[o − window·d_f, o + window·d_f]`. Leader cycles in the support are
enumerated explicitly, because consecutive cycles can differ in configuration.

**Budget (single authority).** Per follower admission: at most **64 leader
cycles** in the support, and membership checks at most 64 follower candidates ×
the leader anchors in those cycles. No leader plan is built. If the cycle bound
would be exceeded (for example follower `/128` against leader `x16` with a
one-step loop) the admission is unsupported with `PLAN LIMIT` and follows the
fallback rule of §1.2 (Interlock bypassed; gap and the rest unchanged).
Acceptance: exactly-at-limit and one-over-limit, both horizon edges, exact
endpoints, origin clipping, an anchor in the preceding cycle within the window,
large ratios and the fallback.

**Device acceptance (timing oracle).** `tests/behaviour/hardware_performance.py`
gains cases on the PERF-002 dense workload at 130 bpm with 16 channels, each
judged like-for-like against the same workload with Merge Shape Off
(**Timing gates** below):
- `PERF-MERGE-HW-STEADY`: channel 2 (Foundation, two sources) follows
  channel 1 (Foundation, 16-step anchor with 4 anchors) through Interlock,
  window 1, both `/1`.
- `PERF-MERGE-HW-WORST`: the maximum supported admission work. Channel 1 is a
  Foundation leader with a one-step playable range `/1` whose anchor pattern has
  a trig there, so every leader cycle has one anchor; channels 2–16 are
  Foundation followers `/1` with 64-step ranges, anchor pattern with a trig on
  step 1 and a second assigned source with trigs on every other step, window 0.
  Each follower admission's support is `[64j/16, (64j + 63)/16]`, which meets
  leader cycles `64j … 64j + 63` — exactly the 64-cycle budget, 64 anchors —
  and every follower candidate coincides with a leader anchor. The test asserts,
  per admission: status supported (not `PLAN LIMIT`), cycle count 64, anchor
  count 64, zero leader-plan builds, and every candidate addition removed with
  `INTERLOCK CH01`; all 15 followers wrap on the same pulse.
- `PERF-MERGE-HW-DENSE`: maximum anchors per admission. Channel 1 is a
  Foundation leader `x16` with a 64-step range and an anchor pattern with a
  trig on every step; channels 2–16 are Foundation followers `/4` with 64-step
  ranges, an assigned anchor pattern with **no** trigs and a second source with
  trigs on **every** step (64 candidates, the maximum: no position is an
  anchor), window 0. Since `d_f / d_l = 64`, each follower
  step lasts exactly one leader cycle, so each admission's support meets exactly
  64 leader cycles and 4,096 anchors, and every follower onset coincides with a
  leader step-1 anchor. Per admission the test asserts: supported, cycle count
  64, leader anchor count 4,096, zero leader-plan builds, all 64 candidates
  removed with `INTERLOCK CH01`; all 15 followers wrap together.
- `PERF-MERGE-HW-DENSE-EDIT`: DENSE plus a grid edit of channel 1's step-1
  anchor trig every 16 beats, alternately off and on (rebuild requests,
  follower propagation and yielding sweeps under maximum work). Per follower
  admission, in both states: supported, cycle count 64, zero builds; trig on:
  4,096 leader anchors and all 64 candidates removed; trig off: 4,032 leader
  anchors, no candidate coincides with an anchor, so no Interlock rejection
  and — with gap 0, Amount 100, Accent 70, no masks — eligible = admitted = 64. Every follower
  shows the new state at its first admission after each edit.
- `PERF-MERGE-HW-EDIT`: WORST plus a grid edit of channel 1's anchor pattern
  every two bars that toggles its single trig off and on again (the
  configuration stays legal and the support unchanged). Assertions are
  state-dependent, per follower admission: in both states supported, cycle
  count 64 and zero leader-plan builds; with the trig on, 64 anchors and every
  candidate removed with `INTERLOCK CH01`; with the trig off, 0 anchors, no
  Interlock rejection, and — with gap 0, Amount 100, Accent 70 and no masks —
  eligible = admitted = the follower's 31 candidate additions. The test asserts
  that every one of the 15 followers shows the new state at its first admission
  after each edit (propagation), rebuild requests and yielding sweeps included.
- **Capture duration:** every case captures at least three complete cycles of
  its slowest follower, computed from §1.1 step durations (a `/1` step is one
  sixteenth, a `/4` step one beat): WORST and EDIT 3 × 16 beats = 48 beats
  (≈ 22 s at 130 bpm); DENSE and DENSE-EDIT 3 × 64 beats = 192 beats
  (≈ 88.6 s); STEADY 3 × 4 beats, raised to the 8 s default. This overrides the
  8 s default where longer.
- **Off baseline (same notes).** Each case plays two windows of the same
  capture duration in one session: Merge Shape Off, then enabled. The Off
  window keeps the channels, ranges and clock mods and removes every merge
  configuration; each workload channel plays the enabled window's working
  pattern (its stopped build, the steady state of these fixed
  configurations with the leader's anchor on) rendered into spare pattern
  slots as legacy sources: source A holds the rendered trigs, notes,
  velocities, lengths and note masks; where the enabled build averaged
  several sources (the merged-pentatonic flag) source B repeats those steps
  with the same values; trig merge mode `all`, value modes `average`. The
  workload asserts the rebuilt Off working patterns equal the rendered ones.
- **Grid origin.** Each window's notes are placed on their channel grids
  counted from the first Note On, and the grid origin is then shifted by the
  median signed placement error, so it follows the steady clock phase: a
  late Start burst (16 notes leaving together) no longer makes every later
  note read early.
- **Compared steps and validity.** The sixteenth steps captured by both
  windows are compared, except, in the EDIT cases, steps within one step of
  a time when the enabled leader's anchor was toggled off (from the recorder's
  step-cell key rows; the Off window always plays the anchor-on notes). On
  every compared step the note set — fine grid slot, MIDI channel, pitch and
  velocity — must be identical in both windows; otherwise the case is
  **invalid** (reported as such, not as a timing pass or fail).
- **Timing gates.** Absolute, on the enabled window: event-timing maximum at
  most 50 ms, and the sustained and hard service gates unchanged. Merge-added,
  over the compared steps (enabled − Off, same session, same notes): p99
  lateness (the one-stall-tolerant p99 of absolute placement error) at most
  5 ms, and step-jitter maximum at most 5 ms. The absolute p99, step jitter
  and final phase of both windows are reported for information.
- **Start latency:** each case measures, in both windows, the time from the
  Start input's acting edge (the Play key-up: Mosaic applies a grid tap on
  release), by its native timestamp, to the first emitted Note On. That time
  contains the phase at which the clock's first pulse falls after the key-up,
  which varies between otherwise identical windows (device STEADY: the grid
  began 57–67 ms after the key-up) and is not merge work: Start builds
  nothing and prepares the transport identically with Merge Shape on or off.
  The gate therefore compares how late each window's first step left
  relative to its own steady grid (the robust origin above): it passes when
  enabled − Off is at most the `step_jitter_maximum_ns` threshold (10 ms).
  The key-up and key-down times and each grid's phase after the key-up are
  reported. The harness checks that the first step's note set (MIDI channels
  and pitches) is identical in both windows; if it is not, or a Start key-up
  was not recorded, the case is invalid.
- **Taps and capture.** Every tap of a window (pattern select, Play, the
  EDIT step-1 edits, Stop) is one Maiden evaluation that presses the key and
  schedules its release 40 ms later on a norns clock, so a stalled Maiden
  reply cannot turn it into a long press (a host-timed Stop whose release
  arrived 30 s late did, and the transport kept playing). Timing is analysed
  over the window's duration from its first Note On; every Note On inside it
  must be released later in the capture, while notes that start after it may
  still be sounding when a late Stop ends the capture.
**Timing roles (owner decision, 27 Sept 2026).** `PERF-MERGE-HW-STEADY` is the
release timing gate: every gate above must pass. `WORST`, `EDIT`, `DENSE` and
`DENSE-EDIT` are **characterisation** loads: the same notes with Merge Shape Off
already exceed the absolute gates on the norns (WORST's 16-note wrap steps give
Off step jitter ~14.5 ms; DENSE's x16 leader stalls ~92 ms with Merge Shape
Off), so their timing figures are recorded and published as the documented
follower limit (README "Interlock"), while admissions, edit propagation, Start
latency (valid, ≤ 10 ms) and transport still gate. The role is `timing_role`
in `merge_workloads.MERGE_CASES`.

**Status (27 Sept 2026, norns CM3+, 130 bpm, harness b28c4df7).**
- STEADY: every gate passes — merge-added p99 +1.4 ms, step jitter +3.1 ms,
  absolute max 5.7 ms, Start latency +1.8 ms.
- WORST (15 followers wrapping together): admissions and Start latency pass;
  merge-added p99 +9.4 ms, step jitter +10.3 ms, absolute max 23.9 ms (Off
  14.3 ms) — about 0.65 ms per follower wrapping on the same step.
- EDIT: all 5 edits reach every follower inside its cycle; merge-added p99
  +5.3 ms, step jitter +1.9 ms, absolute max 12.1 ms.
- DENSE: admissions pass; merge-added p99 ≈ +2.8 ms; absolute max 118.6 ms
  against 91.9 ms Off (an x16-leader stall present without Merge Shape); the
  like-for-like note sets are invalid at 4 of ~768 steps where that stall moves
  x16 leader notes across a fine slot.
- DENSE-EDIT: propagation passed at c6e19128 (11 of 11 edits); the b28c4df7
  run was lost to a full device disk and is not repeated.
Reports: `mosaic-behaviour-runs/merge-perf-20260927/mergeperf-*-b28c4df7-*`.

### 1.5 Dependency rules

(Edges are Interlock leaders only; the inert `space` field creates none.)

- A channel can name at most one Interlock leader (`interlock.leader`). It
  cannot name itself. Every rule and test in this section is about Interlock
  edges; the inert `space` field (§0) is not an edge, and validation tests
  assert that any non-inert `space` value is rejected at apply, load and
  history restore.
- **One-way only:** a channel that has a leader cannot itself be a leader
  (Interlock). This forbids chains and therefore every cycle. Apply
  rejects a violating draft with `LEADER HAS LEADER` or `CHANNEL IS A LEADER`;
  project validation rejects a loaded slot containing one.
  While playing, validation uses the union of configured dependency edges in
  the active snapshot, requested snapshot, per-channel queues, global queues
  and proposed replacement. Treat configured edges conservatively even when
  their feature is inactive. Reject the entire transaction if this union has
  a self-edge, chain or cycle; do not silently delete another channel's edge.
  Thus a queued removal does not free its former leader to become a follower
  until the removal has actually activated. The user may retry after that
  boundary. Stopped transactions validate the resulting snapshot atomically.
  Implement this shared check in the optional configuration transaction path
  and project validation, including history restoration. Boundary activation
  must verify the invariant before mutation; an unexpected violation retains
  the previous active snapshot and displays the rejection reason. Tests must
  cover Interlock edges, different channel lengths, a slow-channel removal
  followed by a fast-channel addition, queued replacement, Stop, undo and redo.
  Every intermediate active graph must satisfy the same one-way invariant.
- The leader must be in the same song slot. If the leader's configuration for
  a queried cycle is Off, or Foundation with a missing anchor, that leader
  cycle contributes no anchors to Interlock. The follower shows `LEADER OFF` or
  `LEADER MISSING` when no evaluated leader cycle contributed anchors.
- **First cycle after Start.** Leader cycle 0 exists from the origin, so the
  follower's first cycle is filtered like any other; there is no waiting cycle.
- **Resync** (§1.2.1) on either channel, or `PLAN LIMIT`, makes the admission
  unsupported; the fallback rule of §1.2 applies (Interlock bypassed only).

## 2. MM-08 Phrase fragments

A separate mode, `mode = "fragments"`. It never runs through the Foundation
planner and Foundation fields are neither shown nor used while it is active.

### 2.1 Fragment layout

- Let `P = [p_1 … p_N]` be the channel's playable positions (start..end,
  capped by global length, never wrapping — project validation forbids
  first > last).
- Fragments partition `P` from `p_1`: fragment `k` (0-based) covers positions
  `p_{kS+1} … p_{min((k+1)S, N)}` for size `S`. The last fragment is shorter
  when `N` is not a multiple of `S`; a loop shorter than `S` is one fragment of
  `N` positions. Fragments never cross the loop end and never wrap into the
  next cycle. Fragment boundaries are therefore relative to the channel's own
  start step, not to absolute step 1.

### 2.2 Source sequence

- Candidates are the channel's assigned trig patterns, ascending by number.
  With one assigned pattern every fragment uses it. With none, the mode bypasses
  to legacy with `ASSIGN PATTERN`, as Foundation does.
- Fragment `k` in phrase cycle `c` uses
  `candidates[ fnv1a("frag|1|seed|slot|channel|binding|phrase|c|k") % count + 1 ]`,
  where `phrase` is 0 for Fixed variation and the phrase number for Per
  phrase, and `c` is the 1-based cycle within the phrase (always 1 when cycles
  is 1). So with Fixed the whole phrase repeats exactly; with Per phrase each
  new phrase draws a new sequence; a saved seed always reproduces it.
  `binding` is the same string Foundation uses.
- Shape percentages do not apply to fragments; the Phrase page shows Cycles and
  Variation only in this mode.

### 2.3 Data preservation

For each position `p` in fragment `k` with chosen source `s`:

- trig, note, velocity and length are `patterns[s]`' authored raw values at
  `p` — the fragment keeps that source's internal rhythm and data exactly. The
  legacy note/velocity/length merge modes do not apply inside a fragment (the
  screen says so), and neither does merged-pentatonic.
- **Keep anchor** (`fragments.keep_anchor`, needs a valid anchor): positions
  where the anchor pattern has a trig and `s` does not also take the anchor's
  trig, note, velocity and length. Where both have a trig, `s` wins (it is the
  fragment's owner). Anchor-kept onsets have role `anchor`; fragment onsets role
  `fragment`.
- **Differing lengths.** Add a fragment-only composed-length resolver in the
  musical-merge implementation and call it from `pattern.get_and_merge_patterns`
  after source composition and Keep anchor, before explicit masks. Do not
  change or reuse the legacy `effective_lengths` helper as a playable-ring
  algorithm: that helper resolves each source over its complete 64 positions
  and excludes full-cycle self-interruption.
  In the fragment resolver, use exactly the ordered playable positions `P`
  from §2.1. For each composed onset at index `i`, find the next composed onset
  forward on that ring; if it is the sole onset, its next occurrence is itself
  after `N` steps. Let that strictly positive index distance be `delta`.
  For authored length `L > 0`, store `min(L, delta)` without rounding; preserve
  zero and negative lengths exactly. Ignore trigs outside `P` when finding
  successors. If there are no onsets, there is nothing to cap. This applies
  across fragment boundaries and the loop end, including short and offset
  loops, and intentionally defines new fragment behavior. Explicit length and
  trig masks then retain their existing final precedence, so a mask may
  deliberately override the cap or alter the composed onset set without a
  second cap pass. Tests must cover sole-onset self-wrap, outside-range trigs,
  fractional and nonpositive lengths, adjacent fragments, loop-end wrap and
  mask overrides, while legacy and Foundation length fixtures remain exact.
- Explicit masks are then applied exactly as today. Probability, chords, arp
  and strum act on the resulting step values unchanged.
- Reasons for M08: `FRAGMENT k · Pnn` and `KEPT ANCHOR`.

## 3. MM-09 Interlock (onset)

Foundation only. The follower's **additions** avoid the leader's **anchor
onsets** in common time. Anchors of either channel are never changed.

- Leader anchors are as defined in §1.2.3 (the currently stored anchor
  pattern's trigs inside the leader's playable range under the governing
  configuration, before masks and probability — the planned structural onsets,
  not whether they sounded).
- For each follower candidate addition at position `p_i` with nominal onset
  `T + (i−1)·d_f`, the candidate is removed with reason `INTERLOCK CHnn` if any
  projected leader anchor onset `a` satisfies
  `|a − onset| ≤ window · d_f`. Window 0 means exactly coincident nominal onsets.
- **Authoritative candidate pipeline (gap and Interlock).** For an unsupported
  admission the Interlock predicate is simply absent, per the §1.2 fallback
  rule. Construct the raw
  assigned-source union and protected anchors as Foundation does today. For
  each non-anchor candidate, evaluate gap and Interlock independently
  against the same immutable admission inputs. Store every applicable rejection
  reason in that order; M14 shows the ordered list and any single-reason
  projection uses its first entry. A disabled or visibly bypassed filter adds
  no rejection, and its bypass status is displayed separately. Candidates
  surviving both predicates form the eligible set. Apply the existing
  FNV ranking and tie-break, existing phrase-adjusted Amount calculation and
  existing Accent behavior to that set, then apply explicit masks last.
  M03 Eligible is the surviving candidate count and Admitted is the count
  selected before masks; Accent zero retains its existing zero-admission
  behavior. Amount-rejected survivors receive the existing amount/accent
  reason. Anchors are never put through these candidate filters.
  With immutable source, leader anchors, window, gap, seed, phrase
  and nonzero Accent, increasing Amount cannot remove an admitted addition.
  Masks can override the result and are outside that nested-set claim.
  Acceptance must combine gap and Interlock with non-100-percent Amount, overlapping
  rejection reasons, Accent zero and mask overrides, asserting exact eligible
  and admitted counts as well as selected positions.
- Swing, shuffle and host timing never change a supported admission (§1.2); unsupported ones bypass visibly.

## 4. MM-10 Structural chord tones ("passing-note freedom")

Foundation only. Explicit markers pick structural moments; onsets there snap to
an explicit chord; additions between markers keep their free target.

- **Markers** (explicit, never inferred from duration or velocity):
  - `anchors`: every Foundation anchor onset position.
  - `every_4` / `every_8`: positions `p_1, p_5, p_9 …` / `p_1, p_9 …` of the
    channel's playable positions (counted from the loop start), whether or not
    an onset lands there.
- **Chord source**: the enabled Harmony Ensemble group `structure.group_id`,
  using its immutable material exactly as the existing Explicit chord target
  does (`structural_target_context` → `harmony_context.group_material`). An
  active snapshot whose source becomes unavailable or empty bypasses marker
  snapping with `CHORD MISSING` and legacy pitch; recovery uses the next source
  revision. This runtime fallback does not authorize saving dangling references.
  Apply/load validation requires an existing enabled group while markers are
  on. Canonical markers Off stores `group_id = nil`.
- **Reference lifecycle.** Extend `channel_feature_editor.lua`,
  `optional_config_transaction.lua`, `musical_merge/state.lua` and
  `project_validation.lua` to include Structure references in the existing
  song-slot transaction. Deleting or disabling a group atomically sets every
  affected requested Structure configuration to markers Off/group nil, together
  with the existing repairs for other group references. Invalidate affected
  dirty drafts as stale and replace affected queued Structure requests so an
  old queue cannot restore a deleted reference. During playback, the group and
  all reference repairs activate together at the existing global pattern
  boundary through the cross-feature queue; an earlier channel wrap must not
  activate a partial repair. Until then the old active group and references
  remain paired. Stop settles the whole requested snapshot together.
  The group, references and queue replacement are one history event; undo/redo
  validates and restores the complete snapshot through the same boundary.
  Save stores the valid requested snapshot, never transitional active/queued
  mixtures. Reject stale or invalid restoration before any mutation. Require
  deletion and disable with unequal channel cycles, active and queued marker
  settings, stale drafts, undo/redo, Stop and save/reload acceptance.
- **Shared pitch resolution.** Extract a pure per-position structural policy
  used by both `step.handle` and the Harmony Pattern material-building loop in
  `step.lua`; bind its snapping helper in `musical_merge/pitch_target.lua`.
  Inputs include the position, Foundation role, active marker policy, immutable
  chord material, existing anchor-pitch choice and explicit bypass flags.
  Select the policy before scale conversion: an eligible marker suppresses
  merged-pentatonic and Addition Target, then snaps the converted pitch to the
  nearest chord pitch class, lower on ties. The global all-scales policy keeps
  its existing upstream conversion semantics. Explicit note-mask, random,
  fixed and quantised-fixed bypasses retain the complete existing legacy path.
  Missing marker material likewise uses the complete legacy path with the
  source reason. Non-marker positions follow the between-marker rule below.
  Pattern material construction must use this same per-position policy, rather
  than infer structural eligibility solely from an addition role.
- **Downstream Harmony.** Pattern still maps raw-value identities. If the same
  raw value resolves to different pitch classes at marker and non-marker
  positions, preserve the existing `source_conflict` fail-closed behavior for
  mapped values; do not pick a representative position or overwrite the conflict.
  Unmapped values retain their per-event resolved pitch. A successful Pattern
  placement must preserve that resolved pitch class. Revoice and Ensemble are
  bypassed for successfully snapped marker root events with visible
  `MARKER PRIORITY`, leaving the snapped root unchanged; outside those events
  they retain their existing behavior. Existing explicit pitch bypasses win
  before this marker rule. Local chord and arp voice generation remain governed
  by existing playback and are not promised to contain only marker chord tones.
  Grid inspection and MIDI must consume the same final root decision, including
  a mapped conflict's silence. Require mapped and unmapped markers, repeated
  raw values across marker boundaries, conflict recovery, Revoice/Ensemble
  interaction and root grid/MIDI comparisons. Failure to resolve a mapped
  conflict must not emit a guessed pitch.
- **Between markers**: additions keep the existing Addition Target
  (Legacy/Scale/Degrees/Chord); anchors keep their legacy pitch. That freedom is
  the "passing" part; no claim is made that the line resolves.
- Structural policy selection and downstream precedence are defined only by
  the shared-resolution rules above; playback, Pattern material and inspection
  must derive their result from that policy rather than quantise independently.
- **Persisted Pattern identity.** In `lib/harmony/pattern.lua`, Structure Off
  must produce the byte-identical legacy binding key, including when the v2
  default fields are present. An inactive group ID has no binding semantics
  and canonicalizes to nil. Do not rewrite or discard existing Pattern maps.
  For enabled markers on an active Foundation configuration only, append an
  unambiguous versioned suffix containing marker kind and group ID to the
  existing key. Changes to those active fields select a fresh map; returning
  Structure to Off recovers the original map. Merge mode Off retains its exact
  existing binding behavior regardless of inactive fields. Acceptance must
  load a saved v1 Foundation-plus-Pattern configuration with a nonempty map,
  assert exact key and mapped playback preservation through v2 migration,
  save/reload it, then toggle Structure on and off and recover the old map.
- Reasons: `MARKER · CHORD Gnn`, `MARKER PRIORITY`, existing pitch bypass and
  Pattern conflict reasons as specified above.

## 5. MM-11 UI, README and persistence

- **Screens** (spec.json + owner fields; route map extended):
  - M02 Merge Shape: Mode gains `Fragments`; rows Rhythm/Phrase/Pitch/Result.
    In Fragments mode Rhythm opens the new **Fragments** screen; Pitch shows only
    the Harmony link.
  - Fragments screen: Size 4/8/16, Keep anchor Off/On, Anchor (assigned
    patterns, shown only with Keep anchor), Seed.
  - M03 Rhythm (Foundation) gains an `Interlock ›` row opening its child
    screen (Leader, Window). Its editable domains derive from §0. Result and
    Reason expose `RESYNC`, `LEADER OFF`, `LEADER MISSING` and `PLAN LIMIT`
    bypasses. Invalid leaders are listed but Apply rejects them according to
    §1.5. There is no Space screen (§6).
  - M07 Pitch gains `Structure ›` → Structure screen: Markers
    Off/Anchors/Every 4/Every 8, Chord group (enabled groups).
  - M05/M14 Result and Reason show the new roles/reasons.
- The existing E1/E2/E3/K2/K3 transaction rules, DRAFT/QUEUED/ACTIVE states and
  marquee truncation apply, subject to the dependency validation in §1.5 and
  atomic cross-feature reference lifecycle in §4.
- README "Merge Shape" replaces the MM-08+ deferral paragraph with a
  subsection per feature (with emulator captures), and the cheat sheet gains
  the new rows. Manual inventory requirements MERGE-FRAGMENTS,
  MERGE-INTERLOCK and MERGE-STRUCTURE are added. The README keeps a one-line
  statement that silence-aware interlock (Space) is not part of this release.

## 6. MM-12 Space — DEFERRED (residual MM-12)

**Not part of this delivery.** Plan review rounds 13–14 established that
filtering a follower against a leader's *sounding* gates needs the leader's
played lengths and articulation as they were when each gate started. Rebuilding
them from current song data is wrong after an edit (a shortened note would free
space that was still sounding), live articulation values are written by lock
and slide callbacks, and the worst-case plan building is unmeasured on the
device. The engine implemented at `b8fd72e5` was reverted (`627f3d6e`); the
`space` field (top level of the v2 merge configuration, §0) remains reserved:
it accepts only `{leader = nil, release = 0}`, with no behaviour, no edges and
no UI. A future design must first
specify historical ownership and retention of leader gate inputs, their writer
inventory, and a device-measured budget, and pass plan review, before any code.
The text below is retained as design notes for that work, not as a contract of
this delivery; the `space` schema field and its dependency edges stay inert.

### 6.0 Former contract (design notes only)

Foundation only, separate from onset interlock (separate leader and fields).
Both predicates participate in the authoritative candidate pipeline in §3.
This card implements nominal planned occupancy, not a guarantee that the
leader is audibly silent. The original silence-aware entry gate in the opening
table remains assigned to residual MM-12-AUDIBLE below; it is not discharged
by this narrower feature.

The follower's candidate addition at nominal onset `o` is removed with reason
`SPACE CHnn` when `o` falls inside any projected leader **gate interval**
extended by `release · d_f`.

### 6.1 Gate semantics (planned gates, not emitted notes)

From the leader's cycle plans `leader_plan(i)` (§1.2; its final working pattern after masks):

- Every position with trig 1 is considered for a gate, whether or not
  probability later drops it and whether or not the channel is muted. Voice
  eligibility and interval construction follow the rules below; probability,
  mute and route outcomes never change the immutable record. This reserves
  nominal occupancy for potentially skipped notes, but is not an actual-time
  or audible-silence guarantee.
- **Length:** `length_steps` is the final post-mask working-pattern length at
  that position. Do not assume a source-onset cap survives numeric merging or
  a length mask, and do not recalculate it using the fragment resolver. The
  ordinary positive-length gate is `[onset, onset + length_steps*d_l)`.
  Gate intervals are half-open; release extension and projection membership
  derive from §1.4.
- **Articulation snapshot:** implement a pure gate-input resolver shared with
  the input resolution used by `step.lua` and
  `lib/musical_resolution/strum_descriptor.lua`. At record construction it
  captures the final step length, chord masks, root mute, strum pattern,
  division, spread, acceleration and arp selection for every playable position.
  Resolve channel values, per-step overrides, parameter-slot values and stock
  precedence exactly as playback would from that immutable snapshot; convert
  division/spread indices through the existing division tables. Reading this
  snapshot must not execute parameter locks, send messages, invoke callbacks
  or consume RNG. A value dependent on unavailable live state makes the whole
  Space record unavailable with `GATE INPUT UNAVAILABLE`; never assume zero.
  Changes after capture cannot mutate the record and use the publication and
  admission rules of §1.3.
  **Stored inputs only.** During playback, parameter locks and slides write the
  live values of articulation parameters from clock callbacks, so a live read
  would depend on which callback ran last. The snapshot therefore reads only
  song data and values that change solely through user edits: chord masks,
  root mute, arp selection, the channel's stock articulation values, and the
  stored per-step lock values. A leader channel on which **any** step carries a
  trig lock, slot value or slide for a strum/chord articulation parameter
  (strum pattern, division, spread, acceleration, chord masks as parameters),
  or whose articulation parameter is modulated or mapped, has its Space record
  unavailable (`GATE INPUT UNAVAILABLE`, Space bypassed, Interlock unaffected).
  Such values are then never read live. Regression: a lock on the leader's strum
  division makes Space bypass with that reason in both callback orders; the
  same leader without the lock yields identical admissions in both orders.
  Articulation edits through the UI reach followers at their next build (§1.3).
- **Strum:** use the existing chord ordering and strum descriptors to enumerate
  the fixed root/chord slots, including reverse root-only strums, sparse chord
  masks and muted roots. Ignore omitted voices and nil/invalid descriptor
  delays. `strum_tail_steps` is the maximum valid nonnegative scheduled delay
  among root and chord voices, with immediate voices at zero. The delayed root
  participates even when there are no chord voices. Reserve a conservative
  envelope from the structural onset through that maximum delay plus the full
  positive note length; empty gaps inside a strum remain reserved. If no voice
  can be scheduled, there is no gate. An unsupported or non-finite input makes
  the record unavailable rather than publishing an underestimated tail.
  Bind tests to the actual descriptor outputs for forward/reverse patterns,
  sparse slots, root-only reverse strums, root mute, negative acceleration,
  invalid gaps, the per-step-lock bypass above and changing captured inputs.
  Assert no RNG or lock side effects while constructing the record.
- **Arp:** an arp is bounded by the gate length already, so it adds nothing.
- **Cancel:** Stop, mute, panic and note-off cancellation are runtime events
  and never shorten a planned gate.
- **Sustain:** Mosaic has no sustain-pedal state of its own; a sustain CC
  sent as a parameter lock is not interpreted and does not extend a gate. This
  is stated in the manual.
- Zero or negative effective lengths contribute no gate.

### 6.2 Scheduling policy

The filter runs inside the follower's working-pattern build under the single
freshness rule of §1.3, uses only leader cycle plans (§1.2) and the query support of §1.4, and uses
§1.4's complete query budget and whole-admission fallback. It adds no callbacks,
clocks or delay to either channel. Record visibility and edit freshness must
come from §1.2–§1.3, not a separate Space
rule. Unavailable articulation snapshots visibly bypass Space for that cycle;
no bypass result may be reported as proof of silence.

### 6.3 Durable residual MM-12 (Space) and MM-12-AUDIBLE

**MM-12 (Space) — owner: the Mosaic maintainer (repository owner), recorded in
`docs/testing/unit-integration-hardening-matrix.json` domain H16
`residual_gaps` and in the README's statement that Space is not part of this
release. Status: OPEN, deferred; no code, UI or manual claim exists.** Its
acceptance boundary, before any implementation: a new plan section that passes
Paranoia plan review and specifies (1) historical ownership, publication and
retention of every leader gate input (pattern lengths after merges and masks,
chord masks, root mute, strum/arp articulation) as it was when each gate
started, with a complete dependency-to-writer inventory (mask edits, recording,
apply/restore, undo/redo, lock writes and clears, assignment replacement,
parameter changes) and visible bypass where history is missing; (2)
callback-order independence for those inputs; (3) a device-measured work budget
with the `hardware_performance.py` timing gates. Only then may an
implementation card be opened.

**MM-12-AUDIBLE** — Owner: the same. Status: OPEN, blocking any release claim
that Mosaic has met the proposal's silence-aware interlock entry gate. The
nominal-occupancy implementation above may be reviewed under its narrower
name, but cannot close this residual.

Acceptance boundary: first define a plan-reviewable contract for conservative
sounding-time coverage or an explicitly supported eligibility domain, including
swing/shuffle, clock retiming, edits, startup, resets, pending strums, cancellation,
arp termination, masks and externally sustained notes. Specify fail-closed
behavior for every unsupported input and scheduling-budget exhaustion; an
unfiltered fallback cannot satisfy audible avoidance. Then require executable
controlled-time and real-time MIDI cases proving no eligible follower addition
starts inside the covered leader sounding intervals. External sustain may be
excluded only by an explicit eligibility condition and visible manual/UI scope.
Until that contract and its later implementation evidence pass review, README,
cheat sheet, captures and acceptance reports must retain the narrower claim.

### 6.4 Residual MM-ACC-PUBLIC (remaining public-input acceptance)

Owner: the Mosaic maintainer (repository owner). Status: OPEN, recorded in
`docs/testing/unit-integration-hardening-matrix.json` H16 `residual_gaps`.

Public-input cases now cover unequal leader/follower loops under a burst of
edits (M-MERGE-INTERLOCK-004), visible PLAN LIMIT bypass at the 65-cycle boundary (M-MERGE-INTERLOCK-005), and playing loop-range RESYNC (M-MERGE-INTERLOCK-006); Every 4/Every 8 markers, Harmony Pattern
conflict recovery and Revoice MARKER PRIORITY (M-MERGE-STRUCTURE-004);
and group deletion undo/redo, Stop settlement and save/reload
(M-MERGE-STRUCTURE-005), plus Ensemble marker priority
(M-MERGE-STRUCTURE-006), in controlled-time and real-time lanes.

Remaining scope — behaviour verified by Lua unit/integration tests
(named in H16) but not yet by public-input emulator cases: Interlock
yielding-sweep interleavings (an edit between the leader's and follower's
rebuilds, stale sweep completion), RESYNC after non-realigning song changes, swing/shuffle invariance and reversed
callback order; Structure CHORD MISSING, arp roots and stale drafts.

Acceptance boundary: each scenario above gains a behaviour case through grid,
norns key/encoder or MIDI input observing MIDI and grid LEDs or the screen, in
the controlled-time and real-time lanes where applicable, registered in
`tests/behaviour/cases.py` and the manual inventory, with red evidence on a
revision lacking the behaviour where one exists.

Delivery restriction: until closed, no release note, README text or
acceptance report may claim public-input acceptance for these scenarios; the
1.4 release notes list MM-ACC-PUBLIC with MM-12 as open residuals, and the
README makes no statement beyond what the named behaviour cases assert.

## 7. Delivery cards and acceptance

Each card: red-green tests first (unit/integration for planners and state,
behaviour cases through real grid/norns/MIDI input in controlled-time and
real-time lanes), then code, then README/cheat sheet/images, then the full Lua
suite and affected behaviour lanes.

| Card | Scope | Acceptance |
|---|---|---|
| MM-08 Fragments | §2, schema v2 + migration | Layout for N = 1, 3, 4, 7, 8, 16, 17, 64 and sizes 4/8/16 with nonzero start; sequence reproducibility per seed; Fixed vs Per-phrase across 3 phrases; authored data preserved subject to §2.3's fragment-only length rule; every §2.3 boundary/mask case; keep-anchor precedence; complete §0 migration round trips and baseline equivalence. Behaviour: grid/MIDI agree for two cycles, both lanes. |
| MM-09 Interlock | §1, §3 | Exact whole-note conversion assertions from §1.1 against sprocket divisions; nominal-time tests for the listed modifier pairs, unequal ranges, realign and division change; same-pulse order independence with changing records and reversed sprocket order; first-cycle behavior; §1.5 active/requested/queued graph transitions and history; §1.4 edge, carry-in, large-ratio and budget cases; exact §3 combined-filter counts and nested sets. Swing/shuffle invariance; resync bypass after division, range and non-realigning slot changes; activation-history queries at, before and after the leader's own boundary in the same pulse; epoch-derived phrase equality with merge_state; direct anchor reads equal plan-derived anchors and every admission performs zero leader-plan builds; the `space` field accepts only its inert value. Behaviour compares the admitted nominal plan with grid positions and corresponding emitted MIDI events, without claiming actual-time nonoverlap. |
| MM-10 Structure | §4 | Marker sets; chord snapping with ties; bypass precedence; between-marker additions unchanged; exact legacy binding/map preservation and active suffix behavior; missing-group recovery; complete reference lifecycle cases; shared playback/Pattern resolution, repeated-value conflicts and downstream Harmony precedence. Behaviour: successfully snapped marker root events preserve a chord pitch class in MIDI and grid inspection; mapped conflicts fail closed; generated chord/arp voices are outside that assertion. |
| MM-11 UI/docs | §5 | Screens through runtime input; apply/queue/cancel and atomic group lifecycle; reasons on M14; README/cheat sheet/images (README states Space is not available); spec validate/replay green. |
| MM-12 Space | §6 | **Deferred** (residual MM-12): no engine, UI or manual claim in this delivery; the reserved `space` schema field is validated and inert. |
| Integrated | all | Full Lua suite, affected behaviour lanes, Paranoia branch review; resolve confirmed BLOCKER/FATAL/MAJOR findings or route permitted deferred obligations to named durable residuals with owner and acceptance boundary. |
