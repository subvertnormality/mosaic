# Explicit selected-step writer slice

This R04 slice gives selected-step mask and trig-lock gestures one stable channel
target for the duration of the operation. The UI resolves the selected song and
channel once, then calls an explicit-channel operation. Existing number/selection
APIs remain as compatibility wrappers and resolve their target once.

## Operations moved

- `toggle_step_trig_mask_for_channel(channel, step)`
- `clear_step_trig_mask_for_channel(channel, step)`
- `clear_masks_for_step_for_channel(channel, step)`
- `clear_trig_locks_for_step_for_channel(channel, step)`

The channel editor's K1 step toggle, K1 long-press clear, and held-step K2 clear
now use these operations. The scale editor's held-step K2 clear does the same.
Channel 17 retains its existing rule: clear scale and transpose locks while
leaving track parameter, octave, and slide tables alone.

## Deferred writers

The recorder and memory replay paths already carry explicit channel tables for
individual parameter locks and remain unchanged. Other direct mask writers in
`channel_edit_page_ui.lua`, recorder events that defer song identity, MIDI input
portions, undo/redo, and legacy memory replay remain mapped for later R04/R05
slices. Revision counters remain deferred until all invalidators for a real cache
consumer are behind explicit operations.

## Validation

- Pre-review Lua unit/integration suite: 1,516 passed, 0 failed. After the
  preservation fix and channel-17 assertion, 1,515 passed and the known
  load-sensitive `test_massive_concurrent_automation_with_param_slides` exceeded
  its two-millisecond suite-load bound; that test passed immediately in isolation.
- Repository inventory/name/syntax guards: 6 passed.
- Controlled native: `M-MASK-018`, `M-PATCH-040`, `M-PATCH-041` passed.
- Real-time native: `M-MASK-018`, `M-PATCH-040`, `M-PATCH-041` passed.
- A new unit contract targets a channel in another song, changes selection
  independently, and verifies that only the captured target changes.

Evidence manifests:

- controlled `M-MASK-018`: `ab7610c3bd1149f396d15298a46e7f35`
- controlled `M-MASK-018` after review fix: `6e9099ff7101431f889fb3c97e7d998b`
- controlled `M-PATCH-040`: `e4881eec687f4cedb50df0ea9071aac3`
- controlled `M-PATCH-041`: `6bb98a7f9dad434099c9e8af57c0a4cb`
- real-time `M-MASK-018`: `22199095218d41d3a73eddac94a55fe3`
- real-time `M-PATCH-040`: `42866d36f7394d71a8206235fa73aa5c`
- real-time `M-PATCH-041`: `b56cb91612704f0fab282f38f262c3db`
