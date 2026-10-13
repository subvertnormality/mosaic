# Pilot reconciliation

Baseline: freshly fetched `codex/1.4.0`, `54d7b871`. The audit distinguishes conflicting claims from incomplete explanations. No Mosaic runtime changes are made for this pilot.

| ID | Evidence | Finding and pilot treatment |
|---|---|---|
| D01 | cheat_sheet.html:1038; tests/behaviour/ui_map.py:172; tests/behaviour/ui.py:146 | Cheat sheet presents all Channel pages as one E1 sequence. The actual UI uses the Masks / Trig params / Channel tasks family; other editors open from tasks with E2 and K3. Pilot explicitly shows the tasks route. This legacy reference needs correction at migration. |
| D02 | README.md:797,824; lib/pages/channel_edit_page/channel_edit_masks.lua:119; tests/behaviour/mask_clearing.py:25 | “Global” in the Masks introduction means a selected-channel default, not a value across every channel. Clarify scope in the pilot; this is ambiguous terminology, not a proven code defect. M-MASK-007 verifies inheritance after clearing. |
| D03 | README.md:828; lib/pages/channel_edit_page/channel_edit_page_ui.lua:214; tests/behaviour/mask_clearing.py:54 | Chord instructions say “select each note” without distinguishing interval values. The UI shows scale-relative 2nd/3rd/.../oct values. Pilot labels them as additional interval voices and keeps the absolute MIDI keyboard route separate. |
| D04 | mosaic.lua:1; fetched branch and commit `54d7b871` | Script header still says v1.3.0. Pilot identifies its source as the requested 1.4.0 branch and records the commit; it does not infer a release from the header. |
| D05 | tests/behaviour/manual-inventory.json:6; tests/behaviour/run.py:50 | Existing manual inventory/gate deliberately remains incomplete. Passing the pilot cannot establish full-manual coverage. Preserve the inventory and false campaign-complete flags. |

Full inventory entries retain README excerpts, mapped requirements, case IDs, available oracles, source identities and explicitly unreviewed code candidates. An automated cross-reference is not a claim that every feature has been semantically audited. Masks receives the detailed pilot audit; other features need review during expansion.

## Observed workflow boundary: edit then clear during one continuous hold

In the pilot development replay, editing step 2 to velocity 0 and pressing K2 before releasing that same long-held step left step 2 silent after release. Releasing it, holding it anew, then pressing K2 restored the channel velocity as expected. README.md:834 does not describe this distinction; lib/pages/channel_edit_page/channel_edit_navigation.lua:144–158 and lib/models/program.lua:552–562 own the clear path. The cause has not been isolated, so this is an observed discrepancy, not a diagnosed production defect. The failed expectations remain at `/home/andy/mosaic-manual-runs/feaece2ed9854ed8aea74b0109df65b7/report.json`; the passing, deliberately different recipe is `/home/andy/mosaic-manual-runs/8073741308ed470c8c0ca0d328f03861/report.json`. The pilot teaches the verified release/rehold workflow. No failing baseline was overwritten and no Mosaic code was changed.

## Reference expansion source audit

These findings compare the preserved 1.4.0 README with code and existing case definitions. They are not new native replay results.

| ID | Evidence | Finding and treatment |
|---|---|---|
| D06 | lib/devices/device_map.lua:26–38; lib/pages/channel_edit_page/channel_edit_page_ui.lua:189; norns lua/lib/musicutil.lua:617–620 | The stock Fixed Note parameter has a separate label table beginning MIDI 0 at C0; numeric MIDI 60 is C5 there. Masks uses musicutil and displays numeric MIDI 60 as C3. Keep the norns convention explanation scoped to Masks and identify MIDI numbers when comparing pages. This is an existing UI label inconsistency, not a pitch-transposition change. |
| D07 | manual/legacy/README-1.4.0.md:1126; lib/pages/song_edit_page/song_edit_page.lua:37–42 | “Currently in play” overstates the bright Song slot: its selected-song-pattern highlight also exists while stopped. The reference explains selected versus queued/playing state. |
| D08 | manual/legacy/README-1.4.0.md:1130,1138; lib/song_transition.lua:74–82; tests/behaviour/song_mode_flow.py:1–7,38–39 | “Selecting a Pattern” means a Song Sequence slot in this section. “First filled slot within that sequence” means the start of the contiguous active group, not the first populated slot anywhere. Existing case definitions distinguish groups 1–2 and 4–5; reference wording preserves that boundary. |
| D09 | manual/legacy/README-1.4.0.md:1630; tests/behaviour/cases.py endurance/slide cases | The 110 BPM Doubledecker overload example is explicitly historical v1.1.1 evidence. The expanded reference does not present it as a current universal performance limit or physical-norns claim from host tests. |
| D10 | manual/legacy/README-1.4.0.md:1256; lib/pages/scale_edit_page/scale_edit_page.lua:61–94 | Transposition Locks prose says the scale page is accessed in Channel Editor; the gesture is owned by the global Scale workspace (channel 17). The expanded controls use that workspace and explicitly flag the retained legacy wording for reconciliation. |
| D11 | manual/legacy/README-1.4.0.md:1312; lib/models/program.lua:879–910 | Param Slides Wrap says “beyond step 64,” but destinations use the effective channel loop start/end, capped by global length. The reference explains the effective boundary and flags the preserved legacy wording. |

## D12 · Suppressed Foundation candidate readout

The frozen README’s Result and Reason section describes roles as anchor, addition or fragment. Source review for the dedicated native Reason fixture found that lib/musical_merge/foundation.lua:142–145 retains rejection reasons and contributor sources for a blocked candidate but assigns no role or velocity there. lib/pages/channel_edit_page/channel_feature_editor.lua:134 falls back to EMPTY for a missing role; its value formatter at lines 67–74 renders missing values as NONE. The resulting current readout is EMPTY P2 / NONE for the suppressed candidate, while an admitted addition is ADDITION P2 / 70 in the fixture.

The expanded reference explicitly explains that existing readout and directs the reader to Decision for the exclusion reason. The native fixture characterises the discrepancy and separately checks actual grid/MIDI suppression; it does not silently change the production implementation or relabel the frozen README. Native passing evidence remains pending until the dedicated fixture completes.


## D13 · Frozen configuration-path statement

`manual/legacy/README-1.4.0.md:186` directs custom device files to `dust > mosaic > config`; preserve this frozen historical claim without editing the legacy file. The current quick-start sends stock device configurations to `data/mosaic/config` (`README.md:28`), and current setup authoring gives the same data path for stock and custom maps (`manual/features/reference-learn.yaml:304,392,461,470–471`). The device loader passes `norns.state.data .. "config"` to `device_descriptors.load_devices` (`lib/devices/device_map.lua:316–317`). Current user instructions therefore remain `data/mosaic/config`; the archived line is recorded as a source discrepancy, not as current installation guidance.
