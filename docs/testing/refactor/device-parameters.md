# Device and parameter ownership (R11)

Descriptor construction is separated from lookup and cache ownership.
This document records the compatibility contract, not a completed R11 claim.

## Existing identities to preserve

Device `id` identifies the configuration; `name` is displayed. `type` selects MIDI,
norns or None behavior. `unique` controls assignment to other channels. Routing
defaults and automatic parameter maps are applied by channel binding, not playback.
Dynamic n.b. descriptors retain their player object, supports_slew and native
parameter IDs/domains; they are runtime objects, not newly serialized project data.

Parameter `id` is the merge/mapping identity. `param_id` can name a native norns
parameter or a generated channel parameter. `index` is the merged numeric slot:
stock entries precede device entries, first duplicate ID wins, and copies remain
shallow (nested label tables retain their existing identity). None is slot 1;
fixed note and quantised fixed note retain slots 2 and 3. Reordering is incompatible
with saved mappings. MIDI controls retain the existing 180 allocated slots/channel.

Domains retain off_value, CC/NRPN minima/maxima, labels, and native warp/quantum.
Output retains CC address bytes or NRPN address bytes and the stored NRPN mode.
The Digitakt exception applies only to NRPN. Existing codec/domain modules remain
the encoding boundary. A missing value, zero, and Off must not be conflated.

## Ownership and validation

Descriptor construction owns loading, diagnostics, generated CC/None definitions,
stock definitions, n.b. discovery and deterministic merge ordering. Device map owns
lookup, shared cached merged tables, invalidation and assignment filtering. Keep
existing init/cache lifetime until an independently reproduced defect warrants a change.
Parameter binding owns control registration, visibility, defaults and slot assignment;
output adapters own emission. UI refresh/autosave stay outside protocol encoding.

Reuse device_map_real_tests and device_value_encoding_tests for field, identity,
cache, slot and encoding contracts. Focused native cases: M-SETUP-001/002/003,
M-SETUP-DEVICE-NAMES-001, M-SETUP-UNREADABLE-CONFIG-001 and M-PATCH-007.
Run n.b./JF routing checks when their construction/binding paths change.
No configuration-creator UI work, stricter config schema or automatic repair is added.

## Output lifetime boundaries

Do not combine routing resolution with protocol emission. Live MIDI control actions
capture the configured parameter/device and route when controls are bound, while
patch recall reads the current channel route when Play recalls controls. Step locks
prefer their assignment's stored NRPN mode before consulting project/device policy.
A shared emitter should receive an already resolved route and mode so extracting
it cannot silently move these decisions to a different point in time.

The existing eligibility checks also differ: step playback requires protocol minimum
and maximum fields, while live controls and recall check the maximum/address fields.
Preserve these callers' admission rules during extraction; changing acceptance of
incomplete configurations is a behavior change, not incidental cleanup.

## Descriptor extraction evidence (2026-09-13)

`device_descriptors.lua` owns config loading, generated devices, dynamic n.b.
discovery and shallow parameter merging. `device_map.lua` retains the shared stock
table, lookup/index, cache/invalidation and assignment filtering. Semantic review
found no concrete regression against 97ca62f. Existing n.b. quantum/step behavior
and assignment-before-sort device values are preserved, not repaired incidentally.

Validation: 1,546 Lua tests passed, plus ten inventory/name/syntax/coverage checks.
Native manifests below are under `/home/andy/projects/mosaic-behaviour-runs/`:

| Case | Lane/profile | Passing run |
| --- | --- | --- |
| M-SETUP-001 | controlled/base MIDI | 3b3ed91eb50c46fa9662425deeaaa4b5 |
| M-SETUP-002 | controlled/base MIDI | 9d9b700bb4064666b42305c06ebe470f |
| M-SETUP-003 | controlled/base MIDI | c36d882406bb4b3ca6308a589b247bb1 |
| M-SETUP-DEVICE-NAMES-001 | controlled/base MIDI | f4ae66ac56eb454baae1322224f03f8e |
| M-SETUP-UNREADABLE-CONFIG-001 | controlled/base MIDI | 8953400fce7d42a39afb8957b575074e |
| M-PATCH-007 | controlled/base MIDI | 84cfcdcf488c44668fb5e07b10c0ca98 |
| M-XA-005-NB-LOCK | real-time/nb-audio | ebd393052f4d40e1b76244f6bc69f6d2 |
| M-XA-007-NB-SWITCH-SLOTS | real-time/crow-jf | b084f9ca2701497290c5e8adefb66710 |

R11 remains in progress: parameter binding/assignment separation, shared output
handling and stable slot definitions follow this extraction.

## Assignment boundary

Registry binding remains responsible for control creation, ranges, formatting,
visibility and actions. Lock assignment owns copying descriptors into the ten
channel slots, mapping stock/native/MIDI parameter IDs and retaining NRPN mode.
It must compare the previous assignment before cancelling owned slides and clearing
pending recording: confirming the same assignment deliberately preserves both.
Default mapping has its own existing cleanup behavior and must not be silently
rewritten to call the interactive assignment path.

Focused regression coverage for this split reuses M-REC-PARAM-011 (changed
assignment), M-REC-PARAM-012 (same assignment), M-PATCH-038 (active slide ownership),
M-SETUP-003 (device defaults), and M-PARAM-036 (stock/None assignment). The existing
real parameter-manager unit tests cover all ten slots and descriptor aliasing.

### Assignment extraction validation (2026-09-13)

The registry now delegates assignment/default mapping to `param_lock_assignments`.
`param_slots` names channel count, control/lock counts, slew and fixed-note slots,
and preserves concatenated control IDs versus formatted assignment IDs.
All 1,546 Lua tests, 18 standalone slide-ownership checks and ten coverage/syntax
checks pass. The slide fixture includes the real new modules; assertions unchanged.
Controlled native runs passed (same evidence root as above):

| Case | Passing run |
| --- | --- |
| M-REC-PARAM-011 | e103339f9e584e158ece7d264785a4e1 |
| M-REC-PARAM-012 | 24a75f5fed4d48668e677d34335697a7 |
| M-PATCH-038 | 22e2bf5678f041f6aa59e71aa894c8f2 |
| M-SETUP-003 | 2a4c0e66937b48b5bc56d1a5360f54b7 |
| M-PARAM-036 | 7376e7aa888f426da6c6db6ec19723a3 |

Protocol serialization and MIDI ingress separation remain outstanding in R11.

## Wire serialization extraction (2026-09-13)

`midi_wire_output` owns CC receiver lookup/byte splitting and NRPN validation and
ordered 99/98/6/38 emission. The public m_midi methods remain; NRPN resolves the
owning module's CC method on each call, and device lookup remains dynamic.
Caller eligibility, route/mode resolution and UI/autosave effects are unchanged.

The exhaustive 16,384-value NRPN reconstruction test and invalid-input/no-partial-
output checks pass. Panic live-note ownership and ten coverage/syntax checks pass.
The full Lua run had 1,544 passes and two timing failures (live slide admission
2.480 ms against 2 ms; massive automation processing above 2 ms). Those same two
load-sensitive cases passed in isolation, with limits unchanged. This is not a
claim that the full run was all green or that a performance defect was repaired.

Controlled native passes:
- M-PATCH-052: `6349dfdb89a04f0c9632927fad955cb4` (both NRPN modes, boundary values,
  route override, Off and device switching).
- M-PATCH-038: `66a94a43a1524ef285ad33e0ac4398b9` (CC slide reassignment/output).

MIDI ingress and mapping registration remain to separate in R11.

## MIDI input ownership extraction (2026-09-13)

`midi_input.new` owns source/channel/key release stacks, recording chord groups,
white-key mapping and CC page-return timers. It captures the original local step,
quantiser, divisions and owning MIDI module dependencies; other globals remain
looked up at invocation. The global handler seam and init callback remain intact.
Stop resets chords at the original point, retaining pending note releases.
The handler body matches the prior implementation apart from name and whitespace.

All 1,546 Lua tests, ten coverage/syntax checks, five panic scheduler scenarios,
the live-note panic contract and exhaustive NRPN/invalid-input checks pass.
The additional panic scheduler fixture now loads the real extracted dependencies;
this repairs a loader omission from the preceding wire extraction, not an assertion.

Native passes under the recorded evidence root:
| Case | Lane | Run |
| --- | --- | --- |
| M-MIDI-002 | controlled | c64842d64b284d59b87518325926d152 |
| M-MIDI-003 | controlled | fc31f1a532214131bf4c134865b73303 |
| M-MIDI-004 | controlled | 8d5634715d814a86a189db73c0e4b8fc |
| M-REC-026 | controlled | bb9776fb578d4bd3b4e422fe178cc563 |
| M-KEYBOARD-STOP-001 | controlled | f003dc7a6bc448349f9856b6db551fb8 |
| M-XA-003-JF-OWNERSHIP | real-time/crow-jf | ad1e0dcd3272442f9995aa37dba73c94 |

MIDI mapping registration remains to separate before closing R11.

## MIDI mapping registration extraction (2026-09-13)

`midi_mapping_params.setup` owns registration and the shared acceleration state
created by each setup call. The public m_midi entry point delegates to it. Callback
bodies match the previous implementation apart from name/whitespace; dynamic
selection, target resolution and control-reset order are preserved.
All 1,546 Lua tests and ten coverage/syntax checks pass. Controlled native passes:

| Case | Run |
| --- | --- |
| M-MAP-001 | 028519105edd45048a864b94c381c09d |
| M-MAP-002 | 1b466765ac1e446c90248027989ff42b |
| M-MAP-003 | 71039b993257479892c4a29a11a2c298 |
| M-MAP-004 | 8bb87ca700df472ea5f78355cb5d2599 |
| M-MAP-PAGE-RETURN-001 | 82c07afc6a48425392f67050603664ac |

R11 final inspection found remaining fixed-note/quantised-note slot literals in
step.lua and generated control IDs in patch recall. Replace those using the
existing slot definitions before claiming the card complete.
