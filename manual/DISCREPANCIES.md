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
