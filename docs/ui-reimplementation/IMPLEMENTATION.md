# Executor procedure

## First green baseline

Work on the user's 1.4.0 development checkout. Preserve its existing unrelated
changes. The inventory identifies a working-tree baseline, not a clean commit.
Validate the package and inspect any drift before editing production code. Assume
the UI test abstraction refactor is already finished; do not repeat it, rewrite
musical case bodies or weaken failure thresholds.

Run the existing post-refactor guard and inventory the contract cases and stable
navigation verbs. Store baseline screen/grid/MIDI evidence separately from the
candidate, with source identity. The implementation's UI contract set may change
only through an explicit reviewed allowlist update. A changed navigation recipe is
expected; a changed musical oracle needs an independent behavior justification.

Follow `spec.json#/migration` in dependency order. Each slice must stay reversible
and independently reviewable. Keep the old renderer usable through UI02. Introduce
new routing only after adapters demonstrate descriptor parity. Never move the
musical engine, persistence schema or emulator internals to accommodate this UI.

## Adapter extraction (UI02)

Create `lib/ui_adapters.lua` with one adapter per `providers` entry. Preserve each
existing getter/edit/action closure, validator, delta policy and commit boundary.
The adapter wraps these operations; it does not reproduce their algorithms.

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
stable IDs at the declaration, not by normalising visible text. Dynamic identities
include their slot/role/degree/raw-tone identity. Keep a descriptor set for every
conditional mode, empty set and maximum cardinality. Compare it with the original
owner descriptors before removing the old draw path.

For Merge and Harmony, `existing_route` and `source_route_map` distinguish current
controller route IDs from new visual screen IDs. For example, old Merge M01 is
new M02; old M04 is new M06. Passing the new screen ID directly into the old editor
would edit the wrong fields. `feature_action_edges` identifies every static action
route in the current editor, including the source declaration and new destination.
Inline actions retain their complete `before`/`invoke` closures and validators.

Read-only visual variants use snapshots, not invented controller routes. An
inspection descriptor can move its own viewed step while remaining read-only to
music. Native parameters retain their IDs, metadata and actions, including
runtime-generated n.b./device inventories. They are not rebuilt from examples.

## Router and grid follow (UI03)

Create `lib/ui_router.lua`. Implement the equality/membership guard algebra and
highest-priority selection literally; ties are errors. Use the Python model as a
presentation oracle, not as a replacement for owner behavior. Zero encoder delta
is ignored. Large E1 deltas move one family boundary; owner E2/E3 scaling remains
unchanged. Derive `profile` from the screen registry and `field_kind` from the
current descriptor. Do not cache them across a dynamic field change.

Grid callbacks run once through their original public input path. Their resolved
outcome identifies page, target, field, flow ID and any mode-specific branch. Add
the follow notification after successful resolution; do not infer outcomes by
watching changed state, synthesize a second grid input or advance time to observe
focus. Global transport/mute/panic feedback retains the workspace. Explicit
page/source choices invalidate old return frames. Temporary held inspectors
restore only a still-valid parent on the final release.

Capture the complete held-step set and owner identity before dispatch. A Channel
hold cancels only an unapplied feature draft, restores the remembered family and
then sends clear/slide/edit to that scope. K1 does not turn a held-step clear into
an all-channel clear. Preserve raw release edges even where key-down is consumed.
Native input ownership takes precedence over all custom norns bindings.

Apply validates the original owner token, target and revision. Running Merge
queues at the existing channel boundary; Harmony uses its existing global pattern
boundary. Cancel discards a new draft without retracting an already accepted queue.
Modal tokens must remain authoritative in their owner, particularly Doctor.
Transport, disconnect and source invalidation must invalidate stale confirmation
and preview tokens through the existing owner lifecycle.

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
separate transactions. Use the exact three-lane Doctor adapter and its runtime
lifecycle. Setup BPM/input fields are UI metadata unless the backend genuinely
supports them; do not promise audio routing that does not exist.

Draw native 128×64 pixels. Use the declared title/scope/body/status/footer regions.
One footer owns the last line. Artwork occupies its reserved region and may be
suppressed to display a long value. Never silently truncate numeric data. A `~`
means abbreviated text; its full form must be available in detail. OFF, INHERIT,
NONE, MIXED and zero must not collapse to one symbol. Screen-specific diagrams use
the arrays in `diagram_contracts`; accepted fixture arrays must never ship as data.

Test long labels, empty inventories, maximum values, held sets, native dialogs,
error/queued/active variants and art poses with the native font/framebuffer oracle.
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
source location, replacement flow and passing case IDs. Fail the gate for a
missing function, unbound dynamic field, unknown action destination, unowned event,
source drift, stale target, clipped numeric value or unexplained changed oracle.
The inventory is a retention ledger, not proof of branch coverage: exercise both
release orders, modifiers and all conditional branches of retained callbacks.

Update the README and cheat sheet together only when the new behavior is real.
Replace stale page ordinals with semantic task names, explain changed gestures and
capture deterministic native grid/screen images for actual new workflows. Resolve
the documented three/four-lane discrepancy without creating a fourth Doctor lane.
Save these images under `images/` alongside their semantic behavior assertions.
Leave no emulator sessions, held keys, active notes or modified user projects.
