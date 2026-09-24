# Executor procedure

## First green baseline

Work on the 1.4.0 branch at the commit named by `source-inventory.json#/head`. The
inventory identifies a committed baseline (`baseline: commit`), not a working tree:
every inventoried source must be committed and unmodified before validation, because
a checkout carrying stale local copies silently changes the contract's premises. Run
`git status` on the inventoried files first and stop on any local change. Assume the
UI test abstraction refactor is already finished; do not repeat it, rewrite musical
case bodies or weaken failure thresholds.

Run the existing post-refactor guard and inventory the contract cases and stable
navigation verbs. Store baseline screen/grid/MIDI evidence separately from the
candidate, with source identity. The implementation's UI contract set may change
only through an explicit reviewed allowlist update. A changed navigation recipe is
expected; a changed musical oracle needs an independent behavior justification. The
only intended interaction changes are listed in
`spec.json#/test_migration/documented_interaction_changes`.

Follow `spec.json#/migration` in dependency order. Each slice must stay reversible
and independently reviewable. Keep the old renderer usable through UI02. Introduce
new routing only after adapters demonstrate descriptor parity. Never move the
musical engine, persistence schema or emulator internals to accommodate this UI.

## Adapter extraction (UI02)

Create `lib/ui_adapters.lua` with one adapter per `providers` entry. Preserve each
existing getter/edit/action closure, validator, delta policy and commit boundary.
The adapter wraps these operations; it does not reproduce their algorithms.
`confirmation` wraps no `lib/ui.lua` state: it forwards to the per-screen owner
closure named in `confirmation_contracts` (the Doctor runtime modal token, the
Harmony invoke closures or scale `save_confirm`). `tasks` is new presentation code
driven by `spec.tasks`.

The logical protocol is:

```lua
-- No callable closures are serialized to JSON. They remain on the Lua owner.
adapter:describe(screen_id, source_route, target, generation) --> descriptors
adapter:edit(field_id, delta, target, generation, modifiers) --> outcome
adapter:invoke(field_id, target, generation, modifiers) --> outcome
adapter:apply(owner_token, target, draft_revision) --> outcome
adapter:cancel(owner_token) --> outcome
adapter:snapshot(target, event_id) --> immutable_snapshot
```

Outcome carries `ok`, `code`, captured `target`, `owner_generation`, optional
`source_route`, active/queued/draft revision and visible status. Reuse existing
return values where available; a wrapper may add read-only identity metadata.

Descriptors contain stable `id`, `label`, `short_label`, `kind`, visibility,
enabled state, domain metadata, formatted values and owner-local closures. Add
stable IDs at the declaration, not by normalising visible text. The IDs are the
spec field ids and a binding's `field` always equals its `id`: parameter slots are
`slot_1..slot_10` with the assigned parameter as metadata
(`field_contracts.parameters.identity`), Merge detail uses `add_amount`,
`degree_<n>`, `step` and so on, Doctor lanes are `lane:<name>`. Every repeated
descriptor declares its `repeat_key`. Keep a descriptor set for every conditional
mode, empty set and maximum cardinality. Compare it with the original owner
descriptors before removing the old draw path.

`existing_route` names the owner state an adapter describes, and
`source_route_map[provider]` declares every such state. For Merge and Harmony it maps
current controller route IDs to new visual screen IDs: old Merge M01 is new M02, old
M04 is new M06. Passing a new screen ID into the old editor would edit the wrong
fields. For Parameters, Masks, Clock and Device (`route_kind: descriptor_filter`) the
key is a view: the adapter describes the owner's single descriptor set and applies
the view's `filter` and `requires`; it never invents a second owner state.
`snapshot:<screen>` routes exist only for `visual_variants`. An adapter rejects
`describe()` for a route it does not own with an error outcome, never an empty list.

`feature_action_edges` identifies every static action in the current editor by a
stable `field_id`, with its source declaration and new destination. A `kind: route`
edge runs `before`, pushes the exact parent and opens the mapped route. The Merge
Pitch "Voice leading" action (old `HARMONY_LINK`) is a `cross_owner_link`: the owner
reloads, discarding any unapplied Merge draft, and enters Harmony fresh at H01 with
an empty stack, so the edge carries `owner.cancel_unapplied`, `return.invalidate` and
`owner.enter_root` and no return frame to Merge exists. M10 is the accepted render
variant of that arrival (harmony provider, route H01). Inline actions retain their
complete `before`/`invoke` closures and validators.

Read-only visual variants use snapshots, not invented controller routes. A read-only
screen gets a K3 route only from an explicit action descriptor plus an edge; C06 has
none, so C08 opens from its owner outcome and C09 from tasks and merge grid outcomes.
An inspection descriptor may move its own view state (a viewed step, or
`view_channel` per `field_contracts.viewer`) with E3 while remaining read-only to
music. The grid-viewer pages (P01, P03, P04, P05, S03) keep their `grid_viewer`
instance; E3 on `view_channel` calls `next_channel`/`prev_channel` and never writes
`selected_channel`, replacing the old E2 gesture. C06 binds the Note Dashboard's
held-step provenance from one `harmony_inspection` snapshot per draw. Native
parameters retain their IDs, metadata and actions, including runtime-generated
n.b./device inventories and the Rhythm Doctor analysis-server parameters. They are
not rebuilt from examples.

## Router and grid follow (UI03)

Create `lib/ui_router.lua`. Implement the equality/membership guard algebra and
highest-priority selection literally; ties are errors. Use the Python model as a
presentation oracle, not as a replacement for owner behavior. Zero encoder delta
is ignored. Large E1 deltas move one family boundary; owner E2/E3 scaling remains
unchanged. Derive `profile` and `hold_policy` from the screen registry and
`field_kind` from the current descriptor. Do not cache them across a dynamic field
change.

Grid callbacks run once through their original public input path. The router wraps
`g.key`, `g.remove`, script `key()` and the redraw clock and emits events only as
`input_algebra.emission` states: hold.begin (or hold.change) after pre on key-down,
exactly one grid.outcome after each short, dual or long handler, hold.change or
hold.end after post on release. Never emit an outcome from pre or post, infer one
from changed state or synthesize a second grid input.

A resolved outcome sets `context`, `screen` and `target` together (`outcome.follow`).
Page buttons G01–G04, including every edge of the Trig→Note→Velocity cycle, are the
only flows that change `context`; they cancel the unapplied draft and invalidate old
return frames. After every event `context` must be one of `screens[screen].context`.
Retain flows never navigate: transport, mute, panic, pattern assignment and
merge-mode taps show feedback on the current screen; inside a Merge screen a
merge-mode tap shows M09 until the gesture ends. Temporary inspectors restore a
parent on the final release only if its generation still matches. Task navigators
come only from `spec.tasks`; the N0x field lists are generated from it.

Capture the complete held-step set and owner identity before dispatch. A hold
behaves the same on every screen of a kind, following its `hold_policy`. On
`follow_family` Channel screens, Merge and Harmony included, `hold.begin` pushes one
return frame and shows the remembered family (C01/C02); the final release returns to
the parent if its generation still matches. On `observe_in_place` screens (C06, C08,
C09 and the non-Channel pages) it only updates the held scope. An unapplied feature
draft is cancelled exactly where the owner cancels it today: in the step callback
(`leave_feature_editor_for_grid`) or by a held E1/E3/K2/K3. The only difference from
today is where release lands (`IC.HOLD.FEATURE`). Clear, slide and edit go to the
held scope. K1 does not turn a held-step clear into an all-channel clear; K1+K3 with
no held steps stays a no-op on Trig params. K2 on a feature root with no parent
cancels the draft and stays, as the owner does today.

Native state is norns menu mode. norns handles a short K1 tap itself and the script
never receives it, so K1.short and native.return are emitted when the router
observes menu mode change. Held K1 edges are the only K1 input the script sees; they
are a modifier and modals never block them. Preserve raw release edges even where
key-down is consumed. Native input ownership takes precedence over all custom norns
bindings.

Apply validates the original owner token, target and revision. Running Merge
queues at the existing channel boundary; Harmony uses its existing global pattern
boundary. Cancel discards a new draft without retracting an already accepted queue.
Modal tokens must remain authoritative in their owner, particularly Doctor: the
router resolves Doctor screens only from `doctor_routes` (runtime state, the modal
operation after `sync_modal`, adapter drafts, armed preview and transport) and never
invents states. Transport, disconnect and source invalidation must invalidate stale
confirmation and preview tokens through the existing owner lifecycle; a norns menu
round trip re-validates the token by generation. The scale clock adapter binds the
existing write and cites `CODE.SCALE.CLOCK.TARGET`.

## Rendering and field migration (UI04–UI06)

`code/screen.lua` is the reusable live layout proto-code. The rendering boundary
receives only a `ViewModel`: no clocks, global selection setters, solver, random
source, MIDI output or mutable program table. Construct title, scope, status and
fields from a single captured snapshot. Bind every field through its descriptor.
The original recipes show the accepted screen artwork and proportions, not runtime
values. All source-backed fields remain accessible, including those absent from a
small specimen.

The four newly explicit views M12/M13/M14/H19 close routes not previously encoded
as separate visual catalogue entries. Their data, controls and parent routes are
in the spec. Feature layouts can share a renderer while their owners retain
separate transactions. Use the Doctor adapter's bank-driven lane inventory
(`lanes()`/`lane_cells()`/`lane_at()`: three on-device lanes, or up to ten from the
analysis server, on rows 2–3, columns 3–7 as `grid.doctor_override` declares) and its
runtime lifecycle. Never add or drop a lane the bank does not declare, and keep no
lane list outside the adapter. Gate input only through
`field_contracts.doctor.transport_gate`: with a READY bank the E2/E3 fields, phrase
browse and paint work while playing; lane selection is never gated; Record, setup,
Alignment and every K2/K3 are stopped-only; transport start keeps an armed preview.
Manual BPM and Input stay editable LOCAL ONLY values (`field_contracts.doctor.setup`);
never present them as audio routing.

Draw native 128×64 pixels in the regions declared in `layout_contract`. One footer
owns the last line. Artwork occupies its reserved region and yields it when a value
needs the width. Values of kind value, readonly or inspection are exact: never
abbreviate, clip or add `~` to them. The selected exact value is always drawn whole
on the same screen (focused `value_region`, the detail selected row with a shrunk
label, or the overview `full_value_line`); a cell that cannot hold a value shows the
`...` marker. `~` marks abbreviated non-value text only, and its full form must be
available in detail. `screen.draw` never raises: when a value cannot be drawn whole it
paints `LAYOUT OVERFLOW` on the family's `overflow_status` line and returns `false`,
which acceptance treats as a failure. OFF, INHERIT, NONE, MIXED and zero must not
collapse to one symbol. Screen-specific diagrams use the arrays in
`diagram_contracts`; accepted fixture arrays must never ship as data.

Test long labels, empty inventories, maximum values, held sets, native dialogs,
error/queued/active variants and art poses with the native font/framebuffer oracle.
Replay already runs 16383, 65535, -8192 and a negative fractional fine-start in every
layout; A18's full-numeric check is certified only with native `screen.text_extents`.
Check semantic text and artwork bounds separately; intentional outlines are not
text overlap. Offline Lua replay is a syntax/runtime check with synthetic metrics,
not an overlap certificate. Do not accept a screenshot alone as behavioral proof.

## Final integration (UI07)

Use `acceptance_matrix` as the minimum cross-feature campaign. Every assertion
cites its manual section or an explicit characterization. Run affected unit and
integration coverage, the relevant actual-emulator behavior cases, and the full
Lua suite once the implementation settles. Timing cases keep controlled-time and
applicable real-time evidence; exclusions need a recorded reason. Existing MIDI,
random, source/projection, persistence and LED oracles remain intact.

For every legacy registration and retained controller unit, record the candidate
source location, replacement flow and passing case IDs. Each `grid_registrations`
entry carries a `branches` list (guard, edge, committed line range, outcome flow or
`retain_without_navigation`, case ID); the gate needs one passing case per branch,
covering both release orders for dual gestures, K1 variants and no-op branches that
must stay no-ops. Fail the gate for a registration without branches, a branch
without a passing case, a missing function, unbound dynamic field, unknown action
destination, unowned event, source drift, stale target, clipped numeric value or
unexplained changed oracle. `validate.py` enforces the structural checks; the branch
list is the scope of the exercise, not proof of coverage.

Update the README and cheat sheet together only when the new behavior is real.
Replace stale page ordinals with semantic task names, explain changed gestures
(`documented_interaction_changes`) and capture deterministic native grid/screen
images for actual new workflows. Resolve `DOC.RD.LANES`: the lane inventory is
bank-driven and the "returns all four lanes" sentence under Availability is stale;
document the two-row lane block, while-playing use of a READY bank and phrase browse
exactly as the adapter implements them. Save these images under `images/` alongside
their semantic behavior assertions. Leave no emulator sessions, held keys, active
notes or modified user projects.
