# Page/edit ownership (R12)

R12 is in progress. The first slice separates channel-mask operations from selector
construction and rendering, keeping the eight existing behaviors explicit.
Encoder and MIDI-map callers retain their shared public handler entry points.

## Mask operation contracts

Held sequencer rows 4–7 affect step locks only for the selected channel. A fixed
mapping to another channel edits that channel's mask from its own value. The
explicit target song survives delayed gesture release across a song transition.
Held edits continue through recorder portions; they must not prewrite the value
before history captures the old state. Preserve each handler's X/nil/zero semantics,
chord working-pattern updates, selector identity and construction order.

Existing coverage: channel_edit_mask_handler_tests, channel_edit_page_ui_delta_killers_tests,
m_midi_input_tests, grid_controls_tests; native M-MAP-004, M-MEMORY-008/009,
M-MASK-HELD-EXTRA-001, M-MASK-CHORD-X-001 and M-MASK-032.
Do not generalize distinct mask semantics merely because the handlers look alike.
R12's subsequent navigation/locks/device/history and view/gesture work remains.

## Mask extraction receipt (2026-09-13)

`channel_edit_masks.new` owns the eight handlers and page dispatch, receiving the
original selectors, public UI table and captured divisions dependency. Public
methods delegate; page dispatch still reads replaceable public handlers at invocation.
Review found the initially missing divisions capture; it was corrected before tests.

All 1,546 Lua tests and ten coverage/syntax checks pass. Controlled native manifests
under `/home/andy/projects/mosaic-behaviour-runs/`:

| Case | Run |
| --- | --- |
| M-MAP-004 | 9798ac4a74e8483dba8ebdaf38120d29 |
| M-MEMORY-008 | d37f14ec126b434d9f4299427ad8f1c8 |
| M-MEMORY-009 | a48a6833cac647f7b57f326bfaccce97 |
| M-MASK-HELD-EXTRA-001 | abdacaafd9024d5ab1142a2ebae88548 |
| M-MASK-CHORD-X-001 | 233794a09b8049328680dd4da40e950d |
| M-MASK-032 | 2111fb0ef67e43678bf42717184743d1 |

This completes the mask-operation extraction only, not all R12 page/visual acceptance.
