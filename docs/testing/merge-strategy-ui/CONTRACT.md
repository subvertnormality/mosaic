# Effective merge strategy selector

Approved 3 October 2026. Production implemented after both native baseline reds. Final native candidate acceptance remains separately pending.

- The Channel Merge Modes screen C09 and grid trig merge key (14,8) select one ordered strategy: Skip, Only, All, Foundation, Fragments. Encoder detents clamp; grid taps wrap.
- C09 retains stable `trig_mode` field identity, labelled Strategy. It shows the selection cursor. The adjacent Active row names the strategy actually in force; Pending names an accepted queued strategy with its existing channel-cycle or global-pattern boundary.
- A refused Foundation request leaves the cursor on Foundation with NEEDS ANCHOR, without changing active or pending musical state. The next positive encoder detent or grid tap reaches Fragments. No anchor is silently assigned.
- Choosing a legacy strategy turns Shape off through its existing validated transaction and retains all Shape settings. Foundation/Fragments retain saved legacy settings. Foundation owns trigs; Fragments owns trigs, notes, velocities and lengths. Legacy fields overridden by the active strategy are visibly inactive and cannot edit.
- Shape transitions retain existing validation, history, stopped apply, channel-cycle queue and cross-feature global-pattern queue behavior. Playback engines, MIDI and musical algorithms are not changed.
- Merge Shape M02 replaces independent Mode with an effective read-only Strategy and a link to C09. Rhythm remains second, followed by the existing vertical parameter detail pages. Opening the selector discards an unapplied parameter draft; returning reloads accepted configuration.
- Masks remains unchanged.

## Evidence

The smallest existing read-only adapter regression expects label Strategy and values FOUNDATION/FRAGMENTS while retaining saved legacy ONLY. It fails on the unfixed source because the current label is Trig mode. `effective-strategy-red.log` and `effective-strategy-red-source.json` preserve the result and source identity.

Native application baselines must fail in both applicable clock lanes before production changes. The first controlled attempt reached ONLY rather than intended ALL and is not valid contract evidence; corrected public setup must establish ALL before the Foundation selection assertion.


Both valid native baselines are preserved in `native-selector-baseline-red.json`: controlled bd32065f28164ad7ab0ee17f07911f0d and real 4238977365094e29a6a9461e6c15dfd2. The identical corrected public fixture established ALL with separate detents, then proved the old UI remained ALL after a Foundation request. Earlier incorrectly established fixture attempts are explicitly invalid, not relabelled as behavior reds.

Ten new focused strategy tests pass, including the actual existing editor validation/transaction API for missing-anchor refusal, recovery to Fragments, saved legacy restoration and activation/deactivation at the existing queue boundary. Pure cursor tests include preserved global-pattern queue, no runtime creation during presentation, and externally accepted changes invalidating failed cursors. The existing musical/transaction fixtures were separately migrated and109affected tests pass. Root owns the final full Lua suite and application campaigns.

The full declarative/source validator passes without skips. The immutable original inventory is preserved. Six historical branch identities now explicitly cite exact original bodies and exact reviewed replacement source/dependencies, rather than claiming the removed three-state behavior survived. Thirty-seven current sources,64callbacks,164historical branches and125manual sections are pinned. Selected overflow marquee prose was corrected in exactly two layout-contract strings; the full Lua candidate's executable source remains byte-identical.
