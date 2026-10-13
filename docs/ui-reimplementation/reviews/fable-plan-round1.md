## What works

Nothing notable.

## What doesn't work

- [BLOCKER] All three lanes independently found that every Rhythm Doctor contract site (R13 fields, G41/G42 lifetimes, R01/R05/R11 prose, doctor.dispatch, field_contracts.doctor.policy, DOC.RD.LANES, A08/A09, grid.contexts.Trig, plan lines 106-107 and 141-142) hard-codes a three-lane adapter at grid (3,2)/(4,2)/(5,2) with every edit stopped-only. The adapter on disk derives lanes from bank.lane_names (three on-device, up to ten remote) laid out on rows 2 and 3, columns 3..7 via lane_cells()/lane_at(); the trigger page draws and resolves presses from that geometry; READY-bank window/step, sensitivity, paint policy, lane select, preview and paint are allowed while the sequencer runs; transport start keeps an armed paint preview; STOP SEQUENCER shows only when no READY bank exists. The README documents exactly this. The source inventory's MAN.032/MAN.033 text is the older wording, so the spec was derived from stale premises. Implementing as written silently drops lanes 4..10, removes the while-playing paint workflow, mis-routes G41/G42 to R11 whenever playing is true, and leaves the 128-cell partition with no Record or lane ownership. The recorded discrepancy DOC.RD.LANES resolves the wrong question (three versus four). (plan:106-107, plan:141-142, repository/lib/rhythm_doctor/ui_adapter.lua:14-24, repository/lib/rhythm_doctor/ui_adapter.lua:42-46, repository/lib/rhythm_doctor/ui_adapter.lua:237-239, repository/lib/rhythm_doctor/ui_adapter.lua:376-406, repository/lib/rhythm_doctor/ui_adapter.lua:671-677, repository/lib/pages/trigger_edit_page/trigger_edit_page.lua:479-484, repository/README.md:475-483, repository/README.md:510-517, repository/docs/ui-reimplementation/source-inventory.json:6110, repository/docs/ui-reimplementation/source-inventory.json:6096, repository/docs/ui-reimplementation/spec.json:10147-10148, repository/docs/ui-reimplementation/spec.json:17282-17309, repository/docs/ui-reimplementation/spec.json:9677-9678, repository/docs/ui-reimplementation/spec.json:28168-28188, repository/docs/ui-reimplementation/spec.json:22140-22145, repository/docs/ui-reimplementation/spec.json:28696-28702, repository/docs/ui-reimplementation/spec.json:28714-28715, repository/docs/ui-reimplementation/spec.json:20729-20734, repository/docs/ui-reimplementation/spec.json:7298, repository/docs/ui-reimplementation/spec.json:6476, repository/docs/ui-reimplementation/generated/validation.json:14, plan:106, plan:142, repository/lib/rhythm_doctor/ui_adapter.lua:12-24, repository/lib/pages/trigger_edit_page/trigger_edit_page.lua:124-132, repository/lib/pages/trigger_edit_page/trigger_edit_page.lua:474-484, repository/README.md:572-577, repository/README.md:596-598, repository/README.md:607-611, repository/docs/ui-reimplementation/spec.json:20730-20734, repository/docs/ui-reimplementation/spec.json:17282-17293, repository/docs/ui-reimplementation/spec.json:10083-10148, repository/docs/ui-reimplementation/spec.json:28696-28700, repository/docs/ui-reimplementation/spec.json:23953-23979, repository/docs/ui-reimplementation/spec.json:23941-23981, repository/docs/ui-reimplementation/spec.json:24049-24077, repository/docs/ui-reimplementation/spec.json:28697, repository/lib/rhythm_doctor/ui_adapter.lua:376-399, repository/lib/pages/trigger_edit_page/trigger_edit_page.lua:476-482, repository/README.md:571-577, repository/README.md:610, repository/docs/ui-reimplementation/spec.json:28487-28488, repository/docs/ui-reimplementation/spec.json:22144, repository/docs/ui-reimplementation/spec.json:28188, repository/docs/ui-reimplementation/spec.json:17293, repository/docs/ui-reimplementation/spec.json:17340-17365, repository/docs/ui-reimplementation/spec.json:15458, repository/lib/rhythm_doctor/ui_adapter.lua:231-239, repository/lib/rhythm_doctor/ui_adapter.lua:364-369, repository/lib/rhythm_doctor/ui_adapter.lua:408-417, repository/lib/rhythm_doctor/ui_adapter.lua:737-740, repository/README.md:504-517)
- [MAJOR] The Merge 'Voice leading' action (old route HARMONY_LINK) is declared like every other static edge: owner.before_if_present, return.push, owner.open_translated_route to H01, and source_route_map maps HARMONY_LINK to H01. The owner does something different: it calls reload(), discarding any unapplied merge draft without status, then select_harmony_page(), which refuses while a grid key is held and enters the harmony editor fresh at its root with an empty stack; no return frame ever existed. Passing H01 into the merge editor's screen variable yields an empty field list. Only the prose of owner.invoke_selected and M10 mentions cancelling the Shape draft; the operative edge and the route map do not. A literal executor keeps the merge draft dirty, opens a screen the merge provider cannot describe, and K2 on H01 pops back to M07 with stale state. (plan:51-56, repository/lib/pages/channel_edit_page/channel_feature_editor.lua:434, repository/lib/pages/channel_edit_page/channel_feature_editor.lua:171, repository/lib/pages/channel_edit_page/channel_edit_navigation.lua:291-296, repository/docs/ui-reimplementation/spec.json:29233-29252, repository/docs/ui-reimplementation/spec.json:28405, repository/docs/ui-reimplementation/spec.json:22170-22175, repository/lib/pages/channel_edit_page/channel_feature_editor.lua:390, repository/docs/ui-reimplementation/spec.json:13087, plan:54-56)
- [MAJOR] Flows G01-G04 (page buttons including the Trig/Note/Velocity cycle) are grid_outcome flows whose target screens live in other contexts, yet outcome.follow only sets screen and target. state_schema.context is a required router field consumed by tasks.open, tasks.enter_selected, primary() fallback and grid geometry. A separate grid.context event with context.follow_primary exists but nothing states which press emits it. The registry adds a second disagreeing authority: N02, N03 and N05 declare context Channel although they navigate Scale, Pattern and Song, and P05 declares Channel while being a task in five other contexts, so context cannot be derived from the registry either. validate.py seeds state.context from screens[].context and test_contract never covers G03's cycle edges, so the router can sit on P03 with context Channel and E1 goes to N01 instead of N03. The local preflight reproduced this in the model. (plan:72-76, repository/docs/ui-reimplementation/tools/model.py:52-63, repository/docs/ui-reimplementation/spec.json:21843-21862, repository/docs/ui-reimplementation/spec.json:22218-22235, repository/docs/ui-reimplementation/spec.json:15683-15736, repository/docs/ui-reimplementation/reviews/LOCAL-PREFLIGHT.md:14-23, repository/docs/ui-reimplementation/tools/model.py:20, repository/docs/ui-reimplementation/tools/model.py:40-42, repository/docs/ui-reimplementation/spec.json:15683-15718, repository/docs/ui-reimplementation/spec.json:22218-22223, repository/docs/ui-reimplementation/spec.json:21971-22005, repository/docs/ui-reimplementation/spec.json:5171, repository/docs/ui-reimplementation/spec.json:5277, repository/docs/ui-reimplementation/spec.json:6883, repository/docs/ui-reimplementation/tools/validate.py:72-76, repository/docs/ui-reimplementation/tests/test_contract.py:35-36, repository/lib/m_grid.lua:98-131, repository/docs/ui-reimplementation/spec.json:15701-15716, repository/docs/ui-reimplementation/spec.json:21971-21981, repository/docs/ui-reimplementation/spec.json:21843-21852, repository/docs/ui-reimplementation/spec.json:5168-5171, repository/docs/ui-reimplementation/spec.json:5274-5277, repository/docs/ui-reimplementation/spec.json:6880-6883, repository/docs/ui-reimplementation/spec.json:2209-2215, repository/docs/ui-reimplementation/tools/validate.py:72-73, repository/docs/ui-reimplementation/tests/test_contract.py:31-36, repository/lib/m_grid.lua:110-119, plan:72-73)
- [MAJOR] code/screen.lua is declared the reusable live layout and pinned by sha as authority, but it violates the view_model overflow contract the same package states. Overview cells (20 or 27 usable px) and the detail layout (47 px) pass every compact_value and value through fit(), which drops characters and appends a tilde with no full-value line or route; the contract requires numeric values never to be truncated and long names to get a separate full-name line on selection. NRPN and 14-bit device values span 0..16383 and merge seeds reach 65535, so a lower-power executor copying the file ships clipped numeric data such as '163~'. The only full-value path is the focused layout, which on overflow raises a Lua assert; on norns an assert inside redraw kills the script instead of failing layout acceptance visibly. A18's 'full numeric value' assertion cannot pass and offline replay with synthetic metrics cannot detect it. (plan:95-101, plan:110-115, repository/docs/ui-reimplementation/code/screen.lua:8-13, repository/docs/ui-reimplementation/code/screen.lua:33-38, repository/docs/ui-reimplementation/code/screen.lua:47-55, repository/docs/ui-reimplementation/code/screen.lua:61-66, repository/docs/ui-reimplementation/spec.json:28343-28348, repository/docs/ui-reimplementation/spec.json:20709-20713, repository/docs/ui-reimplementation/reviews/LOCAL-PREFLIGHT.md:25-35, repository/docs/ui-reimplementation/code/screen.lua:28-37, repository/docs/ui-reimplementation/code/screen.lua:58-66, repository/docs/ui-reimplementation/spec.json:28343-28345, repository/docs/ui-reimplementation/spec.json:28298, plan:112-113, repository/lib/devices/nrpn_codec.lua:15-16, repository/docs/ui-reimplementation/spec.json:28344-28347, repository/docs/ui-reimplementation/spec.json:28281-28291, repository/lib/pages/channel_edit_page/channel_edit_parameters.lua:144-153, plan:112, plan:120-121)
- [MAJOR] Retention is checked per registration only: validate.py requires each of 63 grid registrations to name at least one flow and that registration positions match the source. Callbacks such as the channel dual-press handler contain several independent branches (step range, octave lock, scale lock, dual mute) mapped as a set to G11/G12/G13/G15 with no per-branch guard, edge or case id, and every flow carries the same generic tests array. The plan tells the executor to exercise both release orders, modifiers and all branches but supplies no enumerable scope or case-to-outcome matrix, so the UI07 gate can pass with a rare grid gesture left without a follow outcome. (plan:132-137, repository/docs/ui-reimplementation/tools/validate.py:40-44, repository/docs/ui-reimplementation/tools/validate.py:53-59, repository/docs/ui-reimplementation/source-inventory.json:150-164, repository/lib/pages/channel_edit_page/channel_edit_page.lua:241-307, repository/docs/ui-reimplementation/spec.json:15636-15642, repository/docs/ui-reimplementation/reviews/LOCAL-PREFLIGHT.md:37-49)
- [MAJOR] hold.begin unconditionally applies scope.follow, which in the Channel context moves the screen to C01/C02. The current Note Dashboard shows, while a step is held, that step's source/merge/scale/harmony provenance and planned/scheduled/emitted pitches; the spec's C06 has no held-step fields and C08 states held steps are observed in place, which contradicts the follow rule because a hold leaves C06/C08 before anything can be observed. A lower-power executor will resolve the contradiction arbitrarily and the held-step inspection gesture disappears without a stated replacement. (plan:77-78, repository/lib/pages/channel_edit_page/channel_edit_page_ui.lua:259-293, repository/docs/ui-reimplementation/spec.json:21864-21872, repository/docs/ui-reimplementation/spec.json:22242-22247, repository/docs/ui-reimplementation/spec.json:879-880, repository/docs/ui-reimplementation/spec.json:1076)
- [MAJOR] Two lists claim authority over what a task navigator can open. spec.tasks is keyed by context and tasks.enter_selected asserts the destination is in it; the N01..N05 screens carry their own field lists. They disagree: N01 lists Masks (C01) and Trig params (C02) which tasks.Channel omits, in a different order; N03 lists Rhythm Doctor (R01) which tasks.Trig omits and lists 'pattern' as P01 although tasks.Note/Velocity expect P03/P04; N04 lists six native screens (X01, X04..X08) with no tasks list at all and omits X09 and has no entry route. The model raises on K3 for every mismatched entry, the two orders cannot both be the E2 order, and a lower-power executor cannot tell which list wins. (plan:65-66, repository/docs/ui-reimplementation/spec.json:37-48, repository/docs/ui-reimplementation/spec.json:4983-5137, repository/docs/ui-reimplementation/tools/model.py:41-42, repository/docs/ui-reimplementation/spec.json:37-74, repository/docs/ui-reimplementation/spec.json:4983-5138, repository/docs/ui-reimplementation/spec.json:5293-5350, repository/docs/ui-reimplementation/spec.json:5357, repository/docs/ui-reimplementation/spec.json:22164-22169, repository/docs/ui-reimplementation/spec.json:6744-6862, repository/docs/ui-reimplementation/tools/validate.py:20-26, repository/docs/ui-reimplementation/spec.json:5295-5343, repository/docs/ui-reimplementation/spec.json:6767-6839, repository/docs/ui-reimplementation/spec.json:14709-14714, repository/docs/ui-reimplementation/spec.json:5145)
- [MAJOR] The contract requires stable ids assigned at declaration, dynamic keys of parameter id plus slot, never keyed from rendered labels, and validate.py is the gate. The registry violates this and the validator cannot see it: C02 keys its ten slot fields by the currently assigned parameter name and lists id 'none' twice, so slots 9 and 10 are not addressable and selection retention is ambiguous, contradicting field_contracts.parameters identity (slot_index + assigned_parameter_id); C13 keys its slot as 'cc11'; M12, M13 and M14 bind fields by label text ('Add amount', 'Degree 1', 'Step'). validate.py checks providers, specimens, entry flows and grid partitions but never field id uniqueness or binding.field equality with id, so an executor generating adapter keys from these fixtures produces collisions and label-derived dispatch keys. (plan:44-47, repository/docs/ui-reimplementation/spec.json:389-416, repository/docs/ui-reimplementation/spec.json:27996-27999, repository/docs/ui-reimplementation/spec.json:28336, repository/docs/ui-reimplementation/spec.json:27996-27998, repository/docs/ui-reimplementation/spec.json:28433-28434, repository/docs/ui-reimplementation/spec.json:14797-14805, repository/docs/ui-reimplementation/spec.json:14882-14890, repository/docs/ui-reimplementation/spec.json:14967-14975, repository/docs/ui-reimplementation/spec.json:7169-7178, repository/docs/ui-reimplementation/tools/validate.py:20-26, repository/lib/pages/channel_edit_page/channel_edit_page_ui.lua:104-108)
- [MAJOR] On the Trig, Note, Velocity, Scale grid-viewer and Song grid-viewer pages E2 currently changes the viewed channel, documented in the manual. In the contract those screens are read_only, E2 is focus.move_clamped everywhere except Doctor, and no inspection-kind view_channel descriptor is declared, so the function has no route. P03 and P05 text says E2 changes the view channel, contradicting the algebra, and the retention ledger maps the enc handlers to read_only flows without a grid_viewer unit. (repository/lib/pages/trigger_edit_page/trigger_edit_page_ui.lua:153-161, repository/lib/pages/note_edit_page/note_edit_page_ui.lua:30-40, repository/lib/pages/velocity_edit_page/velocity_edit_page_ui.lua:22-32, repository/lib/pages/scale_edit_page/scale_edit_page_ui.lua:288-292, repository/lib/pages/song_edit_page/song_edit_page_ui.lua:154-160, repository/README.md:641, repository/README.md:676, repository/docs/ui-reimplementation/spec.json:1781-1782, repository/docs/ui-reimplementation/spec.json:2075, repository/docs/ui-reimplementation/spec.json:2292, repository/docs/ui-reimplementation/spec.json:21312-21339, repository/docs/ui-reimplementation/spec.json:28337, repository/docs/ui-reimplementation/spec.json:15526-15545, repository/docs/ui-reimplementation/source-inventory.json:4082-4092, plan:58-59)
- [MAJOR] G40 selects Doctor screens by doctor_state values RECORDING, ANALYSING, CANCEL_CONFIRM and CLEAR_CONFIRM, but the runtime's state set is EMPTY, FAILED, LISTENING, RECORDING, ANALYSING, READY, ALIGNMENT_REQUIRED and REANALYSING with a separate modal token whose operation is clear, cancel_capture or cancel_correction. The cancel_correction modal and the ALIGNMENT_REQUIRED and REANALYSING states have no screen or confirmation contract, so a rejected correction cannot be cancelled through the catalogue. (repository/docs/ui-reimplementation/spec.json:17222-17258, repository/lib/rhythm_doctor/state_machine.lua:209-221, repository/lib/rhythm_doctor/state_machine.lua:232-238, repository/lib/rhythm_doctor/ui_adapter.lua:171-181, repository/lib/rhythm_doctor/ui_adapter.lua:193-197, repository/docs/ui-reimplementation/spec.json:29710-29719, repository/docs/ui-reimplementation/spec.json:7686, repository/docs/ui-reimplementation/spec.json:9361, plan:89)
- [MAJOR] G07 (pattern assign) and G16..G18 (merge-mode buttons) are declared navigation replace to C09 while their lifetime text promises the prior editor is restored on release or on the next held step. Today these taps never leave the Masks/Trig Locks page (only Merge Shape shows a transient M09). Under the model a tap moves the norns to C09 and a later hold pushes C09 as the return frame, so release lands on C09 again, contradicting the text and the grid-first rule that grid taps do not steal the workspace. (repository/docs/ui-reimplementation/spec.json:15862-15882, repository/docs/ui-reimplementation/spec.json:16229-16241, repository/docs/ui-reimplementation/spec.json:16268-16280, repository/docs/ui-reimplementation/spec.json:16307-16319, repository/docs/ui-reimplementation/tools/model.py:52-63, repository/docs/ui-reimplementation/tools/model.py:23-29, repository/lib/pages/channel_edit_page/channel_edit_page.lua:331-365, repository/lib/pages/channel_edit_page/channel_edit_navigation.lua:306-314, repository/lib/pages/channel_edit_page/channel_feature_editor.lua:444-445, repository/docs/ui-reimplementation/README.md:49-52)
- [MAJOR] Screen M10 'HARMONY' is declared with provider merge and existing_route H01, and its binding and SCREEN.M10 entry both route the merge adapter to H01. The merge editor's get_fields has no H01 branch and returns an empty list for any unknown route, so describe(M10, H01) yields EMPTY. This is exactly the wrong-route translation the plan warns about, it violates the provider_protocol rule that presentation-only snapshots cannot be fed into get_fields as existing routes, and M10 is in the A18 acceptance list so the gate would fail or be waved through with a hand-built fixture. (repository/docs/ui-reimplementation/spec.json:13005-13010, repository/docs/ui-reimplementation/spec.json:13230-13233, repository/docs/ui-reimplementation/spec.json:20348-20359, repository/lib/pages/channel_edit_page/channel_feature_editor.lua:113-171, repository/docs/ui-reimplementation/spec.json:28436-28437, repository/docs/ui-reimplementation/spec.json:29043, plan:51-54)
- [MAJOR] S02's state contract gives the executor two incompatible instructions about a musical write: 'Clock writes must target channel 17 even if selected_channel differs' and 'bind verified existing behaviour, flag a pre-existing wrong-channel defect separately'. The existing behaviour writes the scale clock division to program.get_selected_channel() while the refresh reads channel 17; K2 with held steps on the scale page clears trig/scale/octave locks on the selected channel via clear_trig_locks_for_step_for_channel, which S01 and S02 describe as a scale-lock clear and a global lock clear. An executor choosing 'must target channel 17' changes MIDI-affecting behaviour without an oracle; one choosing 'bind existing' ships the defect while the spec says it must not. The defect is not recorded in discrepancies. (repository/docs/ui-reimplementation/spec.json:1433, repository/lib/pages/scale_edit_page/scale_edit_page_ui.lua:103-117, repository/lib/pages/scale_edit_page/scale_edit_page_ui.lua:166-176, repository/lib/pages/scale_edit_page/scale_edit_page_ui.lua:318-330, repository/lib/models/program.lua:491-509, repository/docs/ui-reimplementation/spec.json:1323, repository/docs/ui-reimplementation/spec.json:1432, repository/docs/ui-reimplementation/spec.json:20729-20744, plan:15)
- [MINOR] The algebra depends on a native boolean, a K1.short event and a native.return event, but no document names where these come from on norns. The script's key() only receives raw K1 edges; the system toggles the menu on a short K1 tap before the script sees it and consumes input while open. Rules modal.block.K1.short and modal.block.K1.down therefore promise 'confirmation owns input' feedback for a tap the script never receives, and confirmation_contracts.common.invalidation omits native menu entry, so a modal token can survive a menu round-trip while the rule text implies it was blocked. A lower-power executor may invent a K1 tap detector or never emit native.return. (plan:84, repository/docs/ui-reimplementation/spec.json:21089-21110, repository/docs/ui-reimplementation/spec.json:21968, repository/docs/ui-reimplementation/spec.json:29689-29694, repository/lib/ui.lua:66-72, repository/docs/ui-reimplementation/spec.json:20761-20770, repository/docs/ui-reimplementation/spec.json:21112-21120, repository/docs/ui-reimplementation/spec.json:21903-21911, repository/docs/ui-reimplementation/spec.json:22026-22031, repository/lib/ui.lua:66-100, repository/mosaic.lua:314-320)
- [MINOR] validate.py verifies each manual section by hashing the inventory's own stored text, so stale inventory prose can never fail that check; only the whole-file README hash and heading list guard drift. The inventory's MAN.032/MAN.033 text already differs materially from the README on disk, which is how the stale Doctor wording reached the spec. (plan:7, repository/docs/ui-reimplementation/tools/validate.py:45-47, repository/docs/ui-reimplementation/tools/validate.py:48-52, repository/docs/ui-reimplementation/source-inventory.json:6106-6112, repository/README.md:465)
- [MINOR] m_grid runs pre handlers at key-down, short and dual handlers at release, long by timer and post at release, but the contract never says which phase emits hold.begin, hold.change, grid.outcome or hold.end. Emitting grid.outcome for a temporary flow before hold.begin pushes two return frames while hold.end pops one, and both-release-order tests cannot be specified without this table. (repository/lib/m_grid.lua:240-287, repository/lib/press.lua:127-157, repository/docs/ui-reimplementation/spec.json:21864-21892, repository/docs/ui-reimplementation/tools/model.py:54-57, repository/docs/ui-reimplementation/source-inventory.json:265-276, plan:72-75)
- [MINOR] Three sites disagree on the Doctor setup fields: field_contracts and doctor.dispatch make Manual BPM and Input editable UI-only values, R01 shows them as UNAVAIL and says the presentation marks them unavailable, and the manual documents the E2/E3 draft with K2/K3. The executor cannot tell whether E3 edits or refuses, and the README rule in UI07 cannot be applied. (repository/docs/ui-reimplementation/spec.json:28169-28173, repository/docs/ui-reimplementation/spec.json:22140-22145, repository/docs/ui-reimplementation/spec.json:7263-7297, repository/lib/rhythm_doctor/ui_adapter.lua:299-329, repository/README.md:531-532, plan:107-108)
- [MINOR] The current grid step handler cancels an unapplied feature draft at press time via leave_feature_editor_for_grid. The spec's hold.begin effects push a return frame and follow the family but do not cancel; cancel is attached only to held.E1/E3/K2/K3, while G44's lifetime and the plan say the hold cancels. Under the spec a hold-and-release with no action restores the feature screen with its dirty draft intact, which the old flow never did, and the model test constructs a held-and-dirty state that cannot exist today. Defensible either way but stated inconsistently. (repository/docs/ui-reimplementation/spec.json:21863-21873, repository/docs/ui-reimplementation/spec.json:20945-20957, repository/docs/ui-reimplementation/spec.json:17440, repository/lib/pages/channel_edit_page/channel_edit_page.lua:151-155, repository/lib/pages/channel_edit_page/channel_edit_navigation.lua:298-304, plan:80-82, repository/docs/ui-reimplementation/tests/test_contract.py:24-26)
- [MINOR] On the Trig Locks page with no held steps, the current K3 handler toggles the channel-wide parameter slide only when K1 is not held; K1+K3 is deliberately a no-op because K1 is the fine-control modifier. The spec's param.slide rule has no shift guard, so K1+K3 on C02/C13/F08 would toggle a channel slide, a MIDI-affecting change the plan does not declare as a gesture change. (repository/docs/ui-reimplementation/spec.json:21523-21533, repository/lib/pages/channel_edit_page/channel_edit_navigation.lua:210-220, repository/docs/ui-reimplementation/spec.json:22062-22067, plan:82-83)
- [MINOR] C06 states K3 opens the C08 source detail and C09 states it is reached from C06 by selecting Merge then K3. The only K3 rule for read-only profiles that navigates is read.action, which requires the selected descriptor to have kind action; C06's field list has root, chord, velocity and length only, the read_only provider declares no action descriptors, feature_action_edges covers only merge and harmony owners, and the binding algorithm turns every non-action field of a read-only screen into readonly. Both routes are prose-only, K3 resolves to read.k3 noop, and C08 is reachable only through SCREEN.C08, an owner-state receipt rather than a gesture. (repository/docs/ui-reimplementation/spec.json:879, repository/docs/ui-reimplementation/spec.json:1182, repository/docs/ui-reimplementation/spec.json:815-872, repository/docs/ui-reimplementation/spec.json:21822-21841, repository/docs/ui-reimplementation/spec.json:28337, repository/docs/ui-reimplementation/spec.json:18410-18431, repository/docs/ui-reimplementation/spec.json:29112-29113)
- [MINOR] providers.confirmation cites lib/ui.lua symbol key and providers.tasks cites lib/ui.lua symbol enc as the owners to wrap. ui.key and ui.enc are page dispatchers with no confirmation or task-list state; the real confirmation owners are the Doctor runtime modal token (R03/R10), the harmony editor inline invoke closures (H17/H19) and save_confirm for S05, as confirmation_contracts already says per screen. The plan requires one adapter per providers entry wrapping existing closures, so an executor has no closure to wrap and may invent one. (repository/docs/ui-reimplementation/spec.json:15571-15575, repository/docs/ui-reimplementation/spec.json:15547-15551, repository/lib/ui.lua:50-100, repository/docs/ui-reimplementation/spec.json:29683-29711, repository/lib/rhythm_doctor/ui_adapter.lua:190-197, repository/lib/pages/scale_edit_page/scale_edit_page_ui.lua:81-100, plan:24-26)
- [MINOR] source_route_map only exists for merge and harmony, yet C10, C11, C12, C13, F01, F06 and F08 declare existing_route values equal to their new screen IDs for providers (parameters, device, masks, clock) whose owners have no route concept. The plan forbids invented controller routes for variants and the describe() protocol takes a source_route argument, so an executor cannot tell whether C10 is a filtered view of the C02 slot descriptors, a distinct owner state, or an error. Prose implies filtered variants but nothing machine-readable says which descriptors each shows. (repository/docs/ui-reimplementation/spec.json:28394-28422, repository/docs/ui-reimplementation/spec.json:6287-6293, repository/docs/ui-reimplementation/spec.json:6370, repository/docs/ui-reimplementation/spec.json:7093-7098, repository/docs/ui-reimplementation/spec.json:7153-7159, repository/docs/ui-reimplementation/spec.json:3444-3449, repository/docs/ui-reimplementation/spec.json:4186-4191, repository/lib/pages/channel_edit_page/channel_edit_page_ui.lua:574, plan:58)

## Risks

Nothing notable.

## Gaps

The accepted settlement followed 1 earlier rejected staged payload. None of the rejected payloads' class or debt operations were applied; only the final accepted payload settled.

Validation diagnostics:

    /findings/8/evidence/4: unresolvable repository anchor 'repository/lib/mosaic.lua:314-320'

## Improvements

- [BLOCKER] Re-derive the Doctor contract from the adapter and README on disk in one edit. (1) Lane inventory: R13 fields become a repeated descriptor keyed lane:<name> from adapter:lanes() with cells from adapter:lane_cells(); G41 intent and lifetime become 'lane cells per adapter lane_cells(); count follows bank.lane_names; cells past the last lane inert'; grid.contexts.Trig gains an algorithm-5 overlay covering (1,2)=record, (2,2)=reserved, (3..7,2..3)=lane[index], and validate.py requires the overlay to partition those cells. (2) Transport gate defined once in field_contracts.doctor.transport_gate: stopped-only for Record, capture setup, K2/K3, Alignment; allowed while playing when state is READY for lane select, window bar/step, sensitivity, paint policy, paint preview/commit/undo/redo; transport start cancels capture/analysis and setup/alignment drafts but keeps an armed paint preview. doctor.dispatch, field_contracts.doctor.policy, providers.doctor.commit_boundary, R01/R05/R11 prose and G41/G42 playing alternatives (when playing and doctor_state in EMPTY/FAILED/LISTENING/RECORDING/ANALYSING) cite it. (3) A08 visible becomes 'lane set equals bank lane_names; capture/alignment stopped-only; READY paint while playing'; A09 inputs 'select each present lane'. (4) DOC.RD.LANES decision: 'README line 610 four-lane wording is stale; inventory is bank-driven; UI follows adapter'. (5) Refresh source-inventory MAN.032/MAN.033 text and README/ui_adapter fingerprints deliberately. (6) Plan lines 106-107 and 141-142: replace 'exact three-lane Doctor adapter' with 'the Doctor adapter's bank-driven lane inventory (lanes()/lane_cells()); never add a lane the bank does not declare'. Add model/acceptance cases: ten-lane bank selects lane at (3,3) and (7,2); G42 with playing true and READY resolves to R08/R09/R15 not R11; READY paint while playing succeeds.
- [MAJOR] Give the HARMONY_LINK edge its own kind. In feature_action_edges for from M07 / old_action_route HARMONY_LINK set effects to owner.cancel_unapplied (merge), return.invalidate, owner.switch_owner or a new owner.enter_root effect contract ('call the target owner's enter(); root screen, empty stack; refused while a grid key is held'), landing on H01. Remove HARMONY_LINK from source_route_map or mark it kind cross_owner_link never written to the merge screen variable. State in field_contracts.merge.M07 that the link discards the unapplied merge draft and enters Harmony root with no return frame (or, if a return to M07 is the intended new gesture, say so, keep return.push carrying generation, and still add owner.cancel_unapplied). Add a provider_protocol requirement that adapters reject describe() for routes they do not own, and a model test from a dirty M07 asserting dirty false and return_stack empty after K3 on the harmony action.
- [MAJOR] Make one resolved grid outcome atomically set context, screen and target. Add a required context to each replace-navigation grid_outcome flow (G01 Channel, G02 Scale, G03 Trig/Note/Velocity per alternative, G04 Song, G40..G43 Trig), have outcome.follow in model.py and effect_contracts.outcome.follow assign it from the resolved screen's registry context or payload.page, capture target and invalidate returns once when the flow declares it. Define grid.context as the page-change form of grid.outcome or delete it. Correct registry contexts: N02 Scale, N03 Trig (shared by Note/Velocity via state), N05 Song, P05 context inherit/shared with primary from the entering context. Validator: for every replace flow, the destination screen's context must equal the flow's declared context. Tests: G01-G04 and both G03 cycle edges assert screen and context together, then tasks.open after G03 to Note reaches N03 with tasks.Note.
- [MAJOR] Amend screen.lua and re-fingerprint programs.screen: for fields with kind value the overview and detail paths never call fit(); overview cells draw compact_value only if it fits, otherwise a marker, and the selected field's full value renders on a dedicated full-width line (status row y 55 or the reserved full-name line above C02 cells); detail rows give numeric values the full 126 px minus label, shrinking the label instead; mark unselected overflow with a tilde only for non-value kinds. Replace the assert with a visible LAYOUT OVERFLOW status plus a returned failure flag that the acceptance harness treats as a fail. Add to view_model.overflow that compact_value is metadata for text only and numeric kinds must have a full-width route on the same screen; add a validate.py rule that every overview screen declares a full_value_line region. Add replay cases per layout with maximum numeric domains (16383, 65535, -8192, negative fine-start ms) and require A18's full-numeric assertion to run with the native font oracle, not synthetic metrics.
- [MAJOR] Extend each grid_registrations entry with a branches list of {guard (modifier/page/state), edge (press/long/dual/pre/post/release order), source line range, outcome flow id or retain_without_navigation, case id}. Make validate.py fail on any registration whose branch list is empty or whose branch flow ids are unknown, and require the UI07 gate to cite one passing case id per branch.
- [MAJOR] Add a per-screen hold policy to the registry (follow_family | observe_in_place). Set C06, C08, C09, H05/H06, M05/M14 and the pattern viewers to observe_in_place so hold.begin updates target.step_set and the snapshot without navigation, and keep follow_family for feature/edit/detail screens. Bind the dashboard's held-step provenance fields (source, merge, scale, harmony, planned, scheduled, emitted) as C06 or C08 descriptors, and add a model test that a hold on C06 keeps screen C06 with step_set populated.
- [MAJOR] Make spec.tasks the single authority (ordered list with ids, labels and destinations), keyed by navigator screen with per-context overrides where needed (N03: pattern -> P01|P03|P04 by context). Generate or validate the N01/N02/N03/N04/N05 field lists from it: add a validate.py rule that each N-screen field id maps to exactly one tasks entry in the same order. Decide and record the disputed rows: add C01/C02 to tasks.Channel or drop them from N01; add NAV.Trig.R01 guarded by algorithm 5 or drop rhythm_doctor from N03; add N04 to tasks.Channel with a NAV.Channel.N04 flow and tasks X01, X04..X09, or delete N04. Add a model test entering every navigator row from every context via K3 without assertion.
- [MAJOR] Rekey C02 and C13 fields as slot_1..slot_10 with the assigned parameter id and label as metadata, and make field_contracts.parameters.identity the single authority they cite. Rekey M12/M13/M14 bindings to snake ids (add_amount, degree_<n>, step, role, sources, decision, velocity, pitch_target) and add these ids beside the declarations in the source when UI02 runs. Extend validate.py: for every screen, field ids unique, binding.field == id, ids match ^[a-z0-9_:]+$, and every dynamic screen (parameters, merge M13, harmony H02/H07/H10/H11, doctor R13) declares a repeat key pattern in field_contracts. Add a mutation test that duplicates a field id and expects validation failure.
- [MAJOR] Add to field_contracts a viewer entry: view_channel:inspection1..16 bound to grid_viewer:next_channel/prev_channel (and view_step where applicable), declared for P01, P03, P04, P05 and S03 with the rule 'E2 selects the field, E3 on view_channel moves it; selected_channel is never written'. Rewrite P03/P05 controls_explanation accordingly. Add controller_units for grid_viewer next/prev in the five page_ui.enc handlers with replacement flow NAV.*.P05. Extend A11 with 'change view channel via E3 on the inspection field; musical selected_channel unchanged'.
- [MAJOR] Add one authoritative doctor_routes table in spec: rows for each runtime machine.state (EMPTY, FAILED, LISTENING, RECORDING, ANALYSING, READY, ALIGNMENT_REQUIRED, REANALYSING) by modal.operation (none, clear, cancel_capture, cancel_correction) by playing, mapping to an R screen, and state that G40/G41/G42 alternatives are derived from it. Add an R screen (or make R03 a dynamic-title confirmation bound to modal_copy) for cancel_correction with a confirmation_contracts entry, and map ALIGNMENT_REQUIRED/REANALYSING to R06/R07/R12. Define modal := adapter.modal ~= nil after sync_modal. Add A08 inputs 'reject correction then cancel' and 'alignment required'.
- [MAJOR] Set G16, G17, G18 to navigation retain with a feedback field on the current screen (as G06), plus an alternative when the current screen's provider is merge to M09 with navigation temporary so release restores. Set G07 to retain with feedback (or temporary until next deliberate action) and drop the contradictory lifetime sentence. Add model tests: tap (14,8) from C01 stays C01; from M02 to M09 then hold.end returns M02; assign pattern from C02 stays C02 with feedback.
- [MAJOR] Either delete M10 (the HARMONY_LINK edge already lands on H01, the harmony owner's root) and remove it from A18 and fixtures, or keep it as a visual variant: set provider harmony, existing_route H01, add 'M10: H01 entered from the Merge Pitch link' to visual_variants, change SCREEN.M10 entry to harmony, and add a validate.py rule that a screen's existing_route must appear in source_route_map for its provider when that provider has a route map (merge, harmony).
- [MAJOR] Choose one and state it once. Recommended: bind existing behaviour exactly (scale_clock adapter edit/commit call update_clock_mods unchanged, target = selected channel) and add discrepancies entry CODE.SCALE.CLOCK.TARGET: 'update_clock_mods writes the selected channel while refresh reads channel 17; out of scope for UI migration; tracked separately with its own musical oracle'. Rewrite S02 state_explanation to cite that entry and drop 'must target channel 17'. Rewrite S01/S02 held-K2 text to 'held-step K2 calls program.clear_trig_locks_for_step_for_channel on the selected channel (scale, param, octave and slide locks), unchanged'. If instead the fix is intended, declare it as an explicit behaviour change in test_migration with a justification and oracle.
- [MINOR] State in spec.effect_contracts.native.open/native.close and IMPLEMENTATION.md UI03: native := norns menu mode observed at each redraw and dispatch (the system toggles it on a short K1 tap the script never receives); native.return is emitted on the first redraw after menu mode returns to false; held K1 edges remain the only K1 input the script sees. Replace modal.block.K1.short with the ordinary K1.short handoff (return.push, native.open) and keep K1.down as owner.preserve_key_edge under modal. Add 'native menu open' to confirmation_contracts.common.invalidation or state the token survives and is re-validated on native.return. Add an emulator case toggling the menu and asserting the generation-checked return.
- [MINOR] Slice README by heading line ranges in validate.py, hash the actual slice for each manual section and compare with the stored digest; report the section id on mismatch. Refresh MAN.032/MAN.033 text as part of the Doctor contract repair.
- [MINOR] Add an emission table to input_algebra: register_pre on first held step emits hold.begin, further pre emits hold.change, short/long/dual emit exactly one grid.outcome after the handler returns, post on last release emits hold.end; forbid grid.outcome from pre. Add a model test that hold.begin, G08 outcome, hold.end leaves the return stack unchanged, in both release orders.
- [MINOR] Choose one: keep the fields editable UI-only with status LOCAL ONLY (matches adapter and manual) and change R01 examples/controls text and A08 to say so; or mark them unavailable, in which case record the removed descriptor under coverage_policy.no_disappearing_function and add the README rewrite to UI07. Make field_contracts.doctor.setup the single authority and have R01 cite it.
- [MINOR] Pick one moment for the cancel and state it once. Recommended: add owner.cancel_unapplied to hold.begin when context Channel and the current profile is feature (matching the source and the plan), and change G44 navigation to replace with follow 'remembered family; feature draft cancelled at press'. If deferral is intended instead, reword G44 lifetime and plan line 80 to 'the first held action cancels'. Update the test to start from a clean held state or assert the cancel op on hold.begin.
- [MINOR] Add shift false to param.slide and add rule param.slide.shift (K3.down, profile parameters, shift true, priority 200, effects noop) so the algebra stays tie-free; note the K1 exclusion in family.slide_if_parameters. If the change is intended, record it in test_migration as a documented interaction change.
- [MINOR] Add explicit action descriptors to C06 (source_detail -> C08, merge_detail -> C09, kind action, provider read_only) and corresponding feature_action_edges entries with owner read_only and effects return.push plus route, or drop the C06 K3 prose and reach C08/C09 only through NAV.Channel tasks. Extend validate.py: every 'K3 opens <screen>' route must correspond to an action field plus an edge or a flow whose entry is a gesture.
- [MINOR] Set providers.confirmation.source to 'per-screen owner: confirmation_contracts[screen].owner (doctor runtime modal token, harmony editor invoke closures, scale save_confirm)' with symbol confirm_modal / invoke / save_confirm.confirm, and providers.tasks.source to 'new presentation-owned navigator (no legacy owner; data from spec.tasks)'. Add S05 to confirmation_contracts with owner scale save_confirm.
- [MINOR] Add to source_route_map an entry per unrouted provider mapping each variant to its owner state and filter, e.g. parameters: {C02: all slots, C10: slots whose parameter id is strum/arp/chord_*, C13: selected slot only, F08: C02 snapshot after slide toggle}; masks: {C01: all, C12: selected mask only, F06: held scope snapshot}; clock: {C04: all, F01: C04 after grid follow}; device: {C05: all, C11: confirmation state}. State in provider_protocol.describe that source_route for these providers selects a filter over the single owner descriptor set and never a second owner state.

---
_paranoia-local · engine=claude · session_ref=`5940bb28-a8f4-49d8-a84d-eb7a375cc84a` — to dispute a finding, call `rebut` with this session_ref and your counter-evidence._

=== PATCH PROPOSAL (SUPPLEMENTAL; REVIEW VERDICT UNCHANGED) ===
PATCH-PROPOSAL: PROPOSED
BOUND-REVIEWED-SNAPSHOT-JSON: "1963b555ca529de745420e69c9f49c2be1d2ea81d3bdf6d17370a5c5f025fc8f"
BOUND-STRUCTURAL-SNAPSHOT-JSON: "08b4a273676f137b3ca9136da27c4da889f153a007af6416efddb80294512f97"
BOUND-CONTRACT-DIGEST-JSON: null
TARGET-IDS: ["structural:D1", "structural:D2", "structural:D3", "structural:D4", "structural:D5", "structural:D6", "structural:D7", "structural:D8", "structural:D9", "structural:D10", "structural:D11", "structural:D12", "structural:D13"]
PLAN-SOURCE-KIND-JSON: "plan_path"
PLAN-SOURCE-PATH-JSON: "/home/andy/mosaic-review/docs/ui-reimplementation/IMPLEMENTATION.md"
PLAN-DIGEST-JSON: "1963b555ca529de745420e69c9f49c2be1d2ea81d3bdf6d17370a5c5f025fc8f"
PLAN-VIRTUAL-LABEL-JSON: "plan-artifact.md"
PROPOSAL-CALLS: 1
PROPOSAL-DURATION-MS: 137858
PROPOSAL-AUTHOR-SESSION-JSON: "18c6499c-f747-4cc7-9a79-0c2e5d3cd47f"
PROPOSAL-SESSION-JSON: "18c6499c-f747-4cc7-9a79-0c2e5d3cd47f"
AUTHOR-SUMMARY-JSON: "Candidate plan patch only; no files changed, nothing executed. Adds a \"Contract repairs (UI01)\" section that binds every spec/inventory/validator/model correction the census demanded as a fail-closed gate before UI02: bank-driven Doctor lane inventory and a single transport-gate authority with A08/A09, DOC.RD.LANES, grid overlay and G41/G42 rewrites (D1); an authoritative doctor_routes table keyed by runtime state, modal operation and playing (D10); atomic context+screen+target grid outcomes and corrected N02/N03/N05/P05 contexts (D3); spec.tasks as the single navigator authority with generated N-screen rows (D7); slot-keyed and snake-case field ids with validator uniqueness/binding rules (D8); retain-navigation merge-button and pattern-assign flows (D11); M10 deleted or rebound to harmony (D12); scale-clock target discrepancy recorded once and existing behaviour bound (D13); branch-level retention ledger with validator enforcement (D5); per-screen hold policy and dashboard held-step provenance descriptors (D6); view_channel inspection descriptors for the grid-viewer pages (D9). UI02 text now treats HARMONY_LINK as a cross-owner link that cancels the unapplied merge draft, invalidates returns and enters Harmony root (D2). UI04\u2013UI06 text replaces \"exact three-lane Doctor adapter\" with the adapter's lanes()/lane_cells() inventory and transport gate (D1) and requires screen.lua to be repaired and re-fingerprinted so numeric values are never fitted with ~ and overflow is a visible failure, not an assert (D4). UI07 text ties the gate to per-branch case ids and resolves the lane discrepancy as bank-driven rather than three-versus-four (D1, D5)."
AUTHOR-COVERED: ["structural:D1", "structural:D2", "structural:D3", "structural:D4", "structural:D5", "structural:D6", "structural:D7", "structural:D8", "structural:D9", "structural:D10", "structural:D11", "structural:D12", "structural:D13"]
AUTHOR-UNADDRESSED: []
SUGGESTED-TESTS-JSON: ["model.py: ten-lane bank payload selects lane at (3,3) and (7,2) via G41 and lands on R13 with lane:<name> field id; three-lane bank leaves (6,2),(7,2),(3,3) inert.", "model.py: G42 with playing=true and doctor_state=READY resolves to R08/R09/R15, not R11; G40 with playing=true and state EMPTY resolves to R11.", "model.py: G01\u2013G04 and both G03 cycle edges assert screen and context together; tasks.open after G03 to Note reaches N03 with tasks.Note.", "model.py: from dirty M07, K3 on the Voice leading action leaves dirty=false, return_stack empty, screen H01; K2 on H01 returns to Channel primary, not M07.", "validate.py mutation: duplicate a field id in C02 and expect failure; set binding.field != id in M12 and expect failure; give a screen an existing_route absent from its provider's source_route_map and expect failure.", "validate.py mutation: empty a grid_registrations branches list and expect failure; remove a doctor_routes row and expect the G40 derivation to fail.", "model.py: tap (14,8) from C01 stays C01 with feedback; from M02 goes to M09 and hold.end returns M02; pattern assign from C02 stays C02.", "model.py: hold.begin on C06 keeps screen C06 with step_set populated; hold.begin on H02 moves to remembered family.", "Lua replay with native screen.text_extents: values 16383, 65535, -8192 and a negative fine-start ms in overview_params, detail and focused layouts render the full digits with no ~ and no assert; an oversized value yields the LAYOUT OVERFLOW flag.", "test_contract.py: every N01..N05 row from every context enters via K3 without a spec assertion error and matches spec.tasks order.", "Behaviour case: on P03, E2 then E3 on view_channel changes the viewed grid channel while program selected_channel is unchanged.", "Behaviour case: scale page, held step + K2 clears that step's locks on the selected channel only; S02 clock edit writes the selected channel (existing behaviour) and the CODE.SCALE.CLOCK.TARGET discrepancy is cited."]
LIMITATIONS-JSON: ["Only the plan text is patched; the spec.json, source-inventory.json, model.py, validate.py and screen.lua changes are bound as UI01/UI04 obligations, not authored here.", "No validation, tests or Lua replay were run; suggested tests are unexecuted.", "The scale-clock remedy (D13) binds existing selected-channel behaviour and records the defect; if the owner intends the channel-17 fix, that is a musical behaviour change needing its own oracle and is not assumed here.", "The DOC.RD.LANES rewrite relies on the README four-lane sentence cited in the census evidence; the exact README line should be re-checked when the inventory text is refreshed.", "Whether M10 is deleted or rebound to harmony, and whether C01/C02, R01 and N04 stay in the navigators, are left as recorded decisions for the owner within UI01 rather than decided here."]
PATCH-SHA256: 5ae8281f0fcd1f6c4a09ba22221adc32fa36058193b0d0235c1bb327d9404853
VALIDATION: original source spans matched; patch not applied; tests not executed
PROPOSAL-AUDIT-JSON: "20260924T204904-critique_plan_patch_proposal-e58b83a6.json"
APPLICATION-SUITABILITY: CURRENT-PREIMAGE-REQUIRED
```diff
diff --git a/plan-artifact.md b/plan-artifact.md
--- a/plan-artifact.md
+++ b/plan-artifact.md
@@ -18,6 +18,109 @@
 and independently reviewable. Keep the old renderer usable through UI02. Introduce
 new routing only after adapters demonstrate descriptor parity. Never move the
 musical engine, persistence schema or emulator internals to accommodate this UI.
+
+## Contract repairs (UI01, before any production edit)
+
+The package was compiled against inventory text that no longer matches the
+working tree. UI01 is not done until every item below is applied to `spec.json`,
+`source-inventory.json`, `tools/model.py`, `tools/validate.py` and
+`tests/test_contract.py`, the validator and Python tests pass without
+`--skip-source-fingerprints`, and each refreshed fingerprint (README,
+`lib/rhythm_doctor/ui_adapter.lua`, MAN.032/MAN.033 text) is reviewed as a diff,
+not re-hashed to go green. A gap in any item fails UI01.
+
+1. **Doctor lane inventory.** R13 fields become one repeated descriptor keyed
+   `lane:<name>` produced from `adapter:lanes()` with cells from
+   `adapter:lane_cells()`; the count follows `bank.lane_names` (three on-device,
+   up to ten remote), laid out on rows 2–3, columns 3–7, cells past the last lane
+   inert. `grid.contexts.Trig` gains an algorithm-5 overlay: (1,2) record, (2,2)
+   reserved, (3..7,2..3) lane[index]; `validate.py` requires the overlay to
+   partition those cells. G41 intent/lifetime cite `lane_cells()`; the R13
+   "no remote inventory" text, P06/R01/R05/R11 three-lane prose and A09 lane
+   inputs are rewritten to "select each present lane".
+2. **Doctor transport gate, defined once.** Add
+   `field_contracts.doctor.transport_gate`: stopped-only for Record, capture
+   setup, Alignment and their K2/K3; with a READY bank, lane select, window
+   bar/step, sensitivity, paint policy and paint preview/commit/undo/redo are
+   allowed while playing; transport start cancels capture/analysis and
+   setup/alignment drafts but keeps an armed paint preview; STOP SEQUENCER shows
+   only when no READY bank exists. `doctor.dispatch`,
+   `field_contracts.doctor.policy`, `providers.doctor.commit_boundary`, R11 and
+   the G40/G41/G42 `playing` alternatives (only when `doctor_state` is
+   EMPTY/FAILED/LISTENING/RECORDING/ANALYSING) cite it instead of restating it.
+   A08 visible becomes "lane set equals bank lane_names; capture/alignment
+   stopped-only; READY paint while playing". `DOC.RD.LANES` decision becomes
+   "inventory is bank-driven; the README four-lane sentence is stale; UI follows
+   the adapter".
+3. **Doctor routes, one table.** Add `doctor_routes` keyed by runtime
+   `machine.state` (EMPTY, FAILED, LISTENING, RECORDING, ANALYSING, READY,
+   ALIGNMENT_REQUIRED, REANALYSING) × `modal.operation` (none, clear,
+   cancel_capture, cancel_correction) × playing, each mapping to one R screen.
+   G40/G41/G42 alternatives are derived from it; a `cancel_correction`
+   confirmation screen (or R03 with a modal-bound title) gets a
+   `confirmation_contracts` entry; ALIGNMENT_REQUIRED/REANALYSING map to
+   R06/R07/R12. `modal` means `adapter.modal ~= nil` after `sync_modal`.
+4. **Grid outcomes set context atomically.** Every replace-navigation
+   `grid_outcome` flow declares its `context` (G01 Channel, G02 Scale, G03
+   Trig/Note/Velocity per alternative, G04 Song, G40..G43 Trig).
+   `outcome.follow` in `model.py` and `effect_contracts` assigns context from the
+   resolved screen, captures target and invalidates returns once when the flow
+   says so. `grid.context` is documented as the page-change form of
+   `grid.outcome` or deleted. Registry contexts corrected: N02 Scale, N03 Trig
+   (shared by Note/Velocity through state), N05 Song, P05 inherits the entering
+   context. Validator: a replace flow's destination context must equal its
+   declared context.
+5. **One task authority.** `spec.tasks` is the ordered list of ids, labels and
+   destinations per navigator screen, with per-context overrides (N03 pattern →
+   P01|P03|P04). N01..N05 field rows are generated from it or validated against
+   it row-for-row in order. Record the disputed rows explicitly: C01/C02 in or
+   out of N01; R01 in N03 only with a `NAV.Trig.R01` flow guarded by algorithm 5;
+   N04 kept only with a `tasks.Channel` entry, a `NAV.Channel.N04` flow and the
+   X01, X04..X09 rows, otherwise deleted.
+6. **Stable field ids.** Rekey C02 and C13 fields `slot_1..slot_10` with the
+   assigned parameter id and label as metadata, citing
+   `field_contracts.parameters.identity`. Rekey M12/M13/M14 bindings to snake ids
+   (`add_amount`, `degree_<n>`, `step`, `role`, `sources`, `decision`,
+   `velocity`, `pitch_target`) and add those ids beside the source declarations
+   in UI02. Validator: ids unique per screen, `binding.field == id`, ids match
+   `^[a-z0-9_:]+$`, every dynamic screen (parameters, M13, H02/H07/H10/H11, R13)
+   declares its repeat-key pattern. Add a mutation test duplicating an id.
+7. **Grid taps keep the workspace.** G16/G17/G18 become `navigation: retain`
+   with a feedback field on the current screen, plus an alternative to M09 with
+   `navigation: temporary` when the current provider is merge, so release
+   restores. G07 becomes retain with feedback; delete its contradictory
+   "next held step returns" lifetime sentence.
+8. **M10.** Delete M10 from screens, fixtures and A18 (the Harmony link already
+   lands on H01), or rebind it as provider harmony, `existing_route` H01, listed
+   in `visual_variants`. Validator: a screen's `existing_route` must appear in
+   its provider's `source_route_map` when that provider has one.
+9. **Scale clock target.** Bind existing behaviour exactly: the `scale_clock`
+   adapter calls `update_clock_mods` unchanged (target = selected channel). Add
+   `discrepancies` entry `CODE.SCALE.CLOCK.TARGET` ("update_clock_mods writes the
+   selected channel while refresh reads channel 17; out of scope; tracked
+   separately with its own musical oracle"). S02 cites it and drops "must target
+   channel 17"; S01/S02 held-K2 text becomes "calls
+   `program.clear_trig_locks_for_step_for_channel` on the selected channel,
+   unchanged".
+10. **Branch ledger.** Each `grid_registrations` entry gains a `branches` list of
+    {guard (modifier/page/state), edge (press/long/dual/pre/post/release order),
+    source line range, outcome flow id or `retain_without_navigation`, case id}.
+    Validator fails on an empty branch list or unknown branch flow id.
+11. **Hold policy per screen.** Add `hold_policy: follow_family |
+    observe_in_place` to the registry. C06, C08, C09, H05/H06, M05/M14 and the
+    pattern viewers are `observe_in_place`: `hold.begin` updates
+    `target.step_set` and the snapshot without navigation. Bind the dashboard's
+    held-step provenance (source, merge, scale, harmony, planned, scheduled,
+    emitted) as C06 or C08 descriptors.
+12. **Viewer channel.** Add `field_contracts.viewer`: `view_channel`
+    (inspection, 1..16, bound to `grid_viewer:next_channel/prev_channel`) and
+    `view_step` where applicable, declared for P01, P03, P04, P05 and S03; E2
+    selects the field, E3 moves it, `selected_channel` is never written. Rewrite
+    P03/P05 controls text; add `grid_viewer` controller units for the five
+    `page_ui.enc` handlers; extend A11 accordingly.
+
+Each item is complete only when it has a `test_contract.py` or replay case named
+in the acceptance matrix; the cases listed under UI07 below are the minimum.
 
 ## Adapter extraction (UI02)
 
@@ -43,8 +146,9 @@
 
 Descriptors contain stable `id`, `label`, `short_label`, `kind`, visibility,
 enabled state, domain metadata, formatted values and owner-local closures. Add
-stable IDs at the declaration, not by normalising visible text. Dynamic identities
-include their slot/role/degree/raw-tone identity. Keep a descriptor set for every
+stable IDs at the declaration, not by normalising visible text, using the ids
+fixed by UI01 item 6 (`slot_<n>` for parameter slots, snake ids for Merge detail
+screens). Dynamic identities include their slot/role/degree/raw-tone/lane identity. Keep a descriptor set for every
 conditional mode, empty set and maximum cardinality. Compare it with the original
 owner descriptors before removing the old draw path.
 
@@ -55,9 +159,21 @@
 route in the current editor, including the source declaration and new destination.
 Inline actions retain their complete `before`/`invoke` closures and validators.
 
+The Merge `Voice leading` action (old `HARMONY_LINK`) is a cross-owner link, not a
+route: the owner reloads (discarding any unapplied merge draft) and calls
+`select_harmony_page`, which refuses while a grid key is held and enters Harmony
+fresh at H01 with an empty stack. Its edge therefore carries `owner.cancel_unapplied`
+(merge), `return.invalidate` and a new `owner.enter_root` effect contract, never
+`return.push`/`owner.open_translated_route`; remove `HARMONY_LINK` from
+`source_route_map` (or mark it `cross_owner_link`) so it is never written to the
+merge screen variable. Adapters must reject `describe()` for routes they do not
+own (`merge_fields` returns an empty list for H01). M10 follows UI01 item 8.
+
 Read-only visual variants use snapshots, not invented controller routes. An
-inspection descriptor can move its own viewed step while remaining read-only to
-music. Native parameters retain their IDs, metadata and actions, including
+inspection descriptor can move its own viewed step or viewed channel while
+remaining read-only to music; the grid-viewer pages (P01, P03, P04, P05, S03)
+expose `view_channel` this way per UI01 item 12, so the current E2 channel
+browsing keeps a route without writing `selected_channel`. Native parameters retain their IDs, metadata and actions, including
 runtime-generated n.b./device inventories. They are not rebuilt from examples.
 
 ## Router and grid follow (UI03)
@@ -70,12 +186,19 @@
 current descriptor. Do not cache them across a dynamic field change.
 
 Grid callbacks run once through their original public input path. Their resolved
-outcome identifies page, target, field, flow ID and any mode-specific branch. Add
-the follow notification after successful resolution; do not infer outcomes by
-watching changed state, synthesize a second grid input or advance time to observe
-focus. Global transport/mute/panic feedback retains the workspace. Explicit
-page/source choices invalidate old return frames. Temporary held inspectors
-restore only a still-valid parent on the final release.
+outcome identifies page, target, field, flow ID and any mode-specific branch, and
+the router applies context, screen and target from it atomically (UI01 item 4);
+no separate context event is inferred from the screen. Add the follow
+notification after successful resolution; do not infer outcomes by watching
+changed state, synthesize a second grid input or advance time to observe focus.
+Global transport/mute/panic feedback and the merge-mode/pattern-assign taps
+(G07, G16–G18) retain the workspace with feedback; only the Merge Shape page
+shows the temporary M09 gesture and restores on release. Explicit page/source
+choices invalidate old return frames. Hold behaviour follows the screen's
+`hold_policy`: edit and feature screens follow the remembered family;
+`observe_in_place` screens (C06/C08 provenance, C09, H05/H06, M05/M14, pattern
+viewers) update the held set and snapshot without leaving. Temporary held
+inspectors restore only a still-valid parent on the final release.
 
 Capture the complete held-step set and owner identity before dispatch. A Channel
 hold cancels only an unapplied feature draft, restores the remembered family and
@@ -86,9 +209,14 @@
 Apply validates the original owner token, target and revision. Running Merge
 queues at the existing channel boundary; Harmony uses its existing global pattern
 boundary. Cancel discards a new draft without retracting an already accepted queue.
-Modal tokens must remain authoritative in their owner, particularly Doctor.
-Transport, disconnect and source invalidation must invalidate stale confirmation
-and preview tokens through the existing owner lifecycle.
+Modal tokens must remain authoritative in their owner, particularly Doctor: the
+router resolves Doctor screens only through the `doctor_routes` table (UI01 item
+3) from the runtime state, the synced modal operation and playing; it never
+invents states such as CANCEL_CONFIRM. Transport, disconnect and source
+invalidation must invalidate stale confirmation and preview tokens through the
+existing owner lifecycle. The scale clock adapter binds the existing selected-
+channel write and cites `CODE.SCALE.CLOCK.TARGET`; changing that target is a
+musical behaviour change and is out of scope here.
 
 ## Rendering and field migration (UI04–UI06)
 
@@ -103,14 +231,30 @@
 The four newly explicit views M12/M13/M14/H19 close routes not previously encoded
 as separate visual catalogue entries. Their data, controls and parent routes are
 in the spec. Feature layouts can share a renderer while their owners retain
-separate transactions. Use the exact three-lane Doctor adapter and its runtime
-lifecycle. Setup BPM/input fields are UI metadata unless the backend genuinely
-supports them; do not promise audio routing that does not exist.
+separate transactions. Use the Doctor adapter's bank-driven lane inventory
+(`lanes()`/`lane_cells()`: three on-device, up to ten remote on rows 2–3,
+columns 3–7) and its runtime lifecycle; never add or drop a lane the bank does
+not declare, and gate input only through `field_contracts.doctor.transport_gate`
+(READY-bank lane select, window, sensitivity, policy and paint work while
+playing; Record, setup and Alignment are stopped-only; transport start keeps an
+armed preview). Setup BPM/input fields are UI metadata unless the backend
+genuinely supports them; do not promise audio routing that does not exist.
 
 Draw native 128×64 pixels. Use the declared title/scope/body/status/footer regions.
 One footer owns the last line. Artwork occupies its reserved region and may be
 suppressed to display a long value. Never silently truncate numeric data. A `~`
-means abbreviated text; its full form must be available in detail. OFF, INHERIT,
+means abbreviated text; its full form must be available in detail. The pinned
+`code/screen.lua` does not yet meet this: before UI04 amend it and re-fingerprint
+`programs.screen` so that fields of kind `value` are never passed through `fit()`
+in overview or detail layouts; overview cells draw `compact_value` only when it
+fits and otherwise a marker, with the selected field's full value on a dedicated
+full-width line; detail rows give numeric values the full width minus label,
+shrinking the label; `~` marks unselected overflow for non-value kinds only; and
+the focused-layout `assert` becomes a visible LAYOUT OVERFLOW status plus a
+returned failure flag the acceptance harness treats as a fail. Add to
+`view_model.overflow` that numeric kinds need a full-width route on the same
+screen and a validator rule that every overview screen declares its
+`full_value_line` region. OFF, INHERIT,
 NONE, MIXED and zero must not collapse to one symbol. Screen-specific diagrams use
 the arrays in `diagram_contracts`; accepted fixture arrays must never ship as data.
 
@@ -130,15 +274,21 @@
 random, source/projection, persistence and LED oracles remain intact.
 
 For every legacy registration and retained controller unit, record the candidate
-source location, replacement flow and passing case IDs. Fail the gate for a
-missing function, unbound dynamic field, unknown action destination, unowned event,
-source drift, stale target, clipped numeric value or unexplained changed oracle.
-The inventory is a retention ledger, not proof of branch coverage: exercise both
-release orders, modifiers and all conditional branches of retained callbacks.
+source location, replacement flow and passing case IDs, one per entry in its
+`branches` list (UI01 item 10). Fail the gate for a missing function, unbound
+dynamic field, unknown action destination, unowned event, source drift, stale
+target, clipped numeric value, a branch without a passing case id, or an
+unexplained changed oracle. The inventory is a retention ledger, not proof of
+branch coverage: exercise both release orders, modifiers and all conditional
+branches of retained callbacks, and the validator must reject unmapped branches,
+not merely unmapped registrations.
 
 Update the README and cheat sheet together only when the new behavior is real.
 Replace stale page ordinals with semantic task names, explain changed gestures and
 capture deterministic native grid/screen images for actual new workflows. Resolve
-the documented three/four-lane discrepancy without creating a fourth Doctor lane.
+`DOC.RD.LANES` as "lane inventory is bank-driven; the README four-lane sentence
+is stale": document the two-row lane block and while-playing READY-bank use
+exactly as the adapter and the current README already state, and never invent a
+lane the bank does not declare.
 Save these images under `images/` alongside their semantic behavior assertions.
 Leave no emulator sessions, held keys, active notes or modified user projects.
```
CALLER: plan-artifact.md is a virtual diff label, not a repository path. Inspect the candidate, apply it deliberately to the original plan buffer or PLAN-SOURCE-PATH-JSON when non-null, then submit the changed plan in the same lineage with the next lawful round label. A stale proposal requires a new review.

CLAIM-REGISTER: 4 active external claims; 0 retired and excluded from active inventory
CLAIM-CLOSURE: 4 supported, 0 refuted, 0 unverified
LINEAGE: mosaic-ui-reimplementation-20260924 (rounds recorded: 1)
CLASS-REGISTER: staged census parsed — NONE; 1 earlier rejected payload discarded; none of their operations applied; validation: /findings/8/evidence/4: unresolvable repository anchor 'repository/lib/mosaic.lua:314-320'
CLASS-CLOSURE: 0 open, 0 closed, 0 surviving matches, 0 exempt, 0 unmechanized
STRUCTURAL-PHASE: correction
STRUCTURAL-DEBT: 13 blocking open
STRUCTURAL-CONVERGENCE: BLOCKED — staged structural debt remains open.
STAGED-ATTEMPTS: total=5 validation-retries=1 validation-invalid=1 execution-failed=0
CONVERGENCE: BLOCKED — structural closure remains open.
REVIEW-ATTEMPTS: total=8 validation-retries=1 validation-invalid=1 execution-failed=0