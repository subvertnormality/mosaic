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
