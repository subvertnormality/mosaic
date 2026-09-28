-- README.md Channel pages: Merge Shape and Harmony use staged E2/E3 drafts;
-- K3 applies the whole validated draft and K2 cancels without musical mutation.

local feature_editor = include("mosaic/lib/pages/channel_edit_page/channel_feature_editor")
local merge_state = include("mosaic/lib/musical_merge/state")
local harmony_state = include("mosaic/lib/harmony/config_state")
local harmony_config = include("mosaic/lib/harmony/config")
local harmony_inspection = include("mosaic/lib/harmony/inspection")

local function setup()
  program.init(); globals.reset(); params.reset()
  m_clock.init()
  merge_state.reset(); harmony_state.reset()
  program.set_selected_song_pattern(1)
  return program.get_song_pattern(1), program.get_channel(1, 1)
end

local function select_label(value, label)
  for index, field in ipairs(value:get_fields()) do
    if field.label == label then value.selected=index; return field end
  end
  error("missing field " .. label .. " on " .. value:get_screen())
end

local function open_label(value, label)
  select_label(value,label);value:key(3)
end

function test_feature_editor_e2_large_turn_selects_visible_row()
  setup()
  for _, kind in ipairs({"merge", "harmony"}) do
    local value = feature_editor.new(kind)
    value:enter()
    local last = #value:get_fields()
    value:enc(2, 24)
    luaunit.assert_equals(value.selected, last, kind .. " E2 positive")
    value:enc(2, -24)
    luaunit.assert_equals(value.selected, 1, kind .. " E2 negative")
  end
end

function test_channel_merge_shape_editor_cancel_discards_complete_draft()
  local _, channel = setup()
  local value = feature_editor.new("merge")
  value:enter()
  value:enc(3, 1)
  luaunit.assert_true(value.dirty)
  value:key(2)
  luaunit.assert_false(value.dirty)
  luaunit.assert_nil(channel.musical_merge)
  luaunit.assert_equals(value.status, "DRAFT CANCELLED")
end

function test_channel_merge_shape_editor_applies_valid_foundation_transaction()
  local song, channel = setup()
  channel.selected_patterns[1] = true
  local value = feature_editor.new("merge")
  value:enter()
  value.draft.mode, value.draft.anchor, value.dirty = "foundation", 1, true
  luaunit.assert_true(value:key(3))
  luaunit.assert_equals(channel.musical_merge.mode, "foundation")
  luaunit.assert_equals(value.status, "APPLIED")
  luaunit.assert_equals(merge_state.effective(song, 1, channel.musical_merge).config.anchor, 1)
end

function test_channel_harmony_editor_validates_and_applies_without_touching_patterns()
  local song, channel = setup()
  song.patterns[1].note_values[1] = -7
  local value = feature_editor.new("harmony")
  value:enter()
  value.draft.mode, value.dirty = "pattern", true
  luaunit.assert_true(value:key(3))
  luaunit.assert_equals(channel.voicing.mode, "pattern")
  luaunit.assert_equals(song.patterns[1].note_values[1], -7)
  luaunit.assert_equals(value.status, "APPLIED")
end

function test_merge_editor_routes_every_declared_screen_and_e1_returns_to_root()
  local _,channel=setup();channel.selected_patterns[1]=true
  local value=feature_editor.new("merge");value:enter()
  local routes={Rhythm="M02",Phrase="M04",Pitch="M05",Result="M07"}
  for label,route in pairs(routes)do
    open_label(value,label);luaunit.assert_equals(value:get_screen(),route)
    luaunit.assert_true(value:encoder_one());luaunit.assert_equals(value:get_screen(),"M01")
  end
  open_label(value,"Rhythm");open_label(value,"Amount detail")
  luaunit.assert_equals(value:get_screen(),"M03");value:key(2);luaunit.assert_equals(value:get_screen(),"M02")
  value:encoder_one();open_label(value,"Pitch");open_label(value,"Target setup")
  luaunit.assert_equals(value:get_screen(),"M06")
  value:encoder_one();open_label(value,"Result");open_label(value,"Reason")
  luaunit.assert_equals(value:get_screen(),"M08")
  value:show_merge_gesture("TRIG SKIP");luaunit.assert_equals(value:get_screen(),"M09")
  value:hide_merge_gesture();luaunit.assert_equals(value:get_screen(),"M08")
end

function test_merge_child_draft_is_atomic_and_cancel_discards_parent_and_child_changes()
  local _,channel=setup();channel.selected_patterns[1]=true
  local value=feature_editor.new("merge");value:enter()
  value:enc(3,1) -- Foundation on M01
  open_label(value,"Rhythm");select_label(value,"Anchor");value:enc(3,1)
  select_label(value,"Add amount");value:enc(3,-1)
  luaunit.assert_true(value.dirty);value:key(2)
  luaunit.assert_equals(value:get_screen(),"M01")
  luaunit.assert_equals(value.draft.mode,"off")
  luaunit.assert_nil(channel.musical_merge)
end

function test_merge_anchor_selector_enters_first_assigned_pattern_from_none()
  local _,channel=setup();channel.selected_patterns[1]=true;channel.selected_patterns[2]=true
  local value=feature_editor.new("merge");value:enter();open_label(value,"Rhythm")
  luaunit.assert_nil(value.draft.anchor)
  value:enc(3,1)
  luaunit.assert_equals(value.draft.anchor,1)
end

function test_merge_phrase_custom_percentages_and_empty_degree_target_fail_validation()
  local _,channel=setup();channel.selected_patterns[1]=true
  local value=feature_editor.new("merge");value:enter();value.draft.mode="foundation";value.draft.anchor=1
  open_label(value,"Phrase");select_label(value,"Cycles");value:enc(3,1)
  luaunit.assert_equals(value.draft.cycles,2)
  select_label(value,"Cycle 1");value:enc(3,-1)
  luaunit.assert_equals(value.draft.shape,"custom")
  luaunit.assert_true(value:key(3));luaunit.assert_equals(channel.musical_merge.percentages[1],99)

  value:encoder_one();open_label(value,"Pitch")
  value.draft.target={kind="degrees",degrees={}}
  value.dirty=true;select_label(value,"Keep anchor")
  luaunit.assert_false(value:key(3));luaunit.assert_not_nil(value.status:match("INVALID"))
end

function test_harmony_editor_routes_h01_children_and_tone_map_open_is_read_only()
  local song,channel=setup();channel.selected_patterns[1]=true
  song.patterns[1].note_values[1]=0;channel.working_pattern.note_values[1]=0
  local value=feature_editor.new("harmony");value:enter()
  value.draft.mode="pattern"
  open_label(value,"Tone Map");luaunit.assert_equals(value:get_screen(),"TONE_MAP")
  luaunit.assert_equals(value.draft.pattern_maps,{})
  value:encoder_one();luaunit.assert_equals(value:get_screen(),"H01")
  for label,route in pairs({Register="H02",Bass="H03",Groups="H04",Rules="H08",Entry="H09",Result="H05"})do
    open_label(value,label);luaunit.assert_equals(value:get_screen(),route)
    value:encoder_one();luaunit.assert_equals(value:get_screen(),"H01")
  end
end

function test_harmony_result_prefers_active_event_bypass_without_a_solver_result()
  local song=setup();harmony_inspection.plan(song,1,{step=1,status="ok",bypass="note_mask",output=65})
  local value=feature_editor.new("harmony");value:enter();open_label(value,"Result")
  luaunit.assert_equals(select_label(value,"Status").get(),"BYPASS note_mask")
end

function test_harmony_failure_details_use_active_event_not_unapplied_draft()
  local song=setup();local value=feature_editor.new("harmony");value:enter()
  harmony_inspection.plan(song,1,{step=1,status="group_missing",reason="group_missing",fallback="legacy",output=nil})
  value.draft.fallback="silence"
  open_label(value,"Result")
  luaunit.assert_equals(select_label(value,"Status").get(),"LEGACY group_missing")
  open_label(value,"Failure details")
  luaunit.assert_equals(select_label(value,"Reason").get(),"group_missing")
  luaunit.assert_equals(select_label(value,"Fallback").get(),"legacy")
end


function test_harmony_result_unrecorded_step_is_empty_instead_of_showing_stale_solver_state()
  local song=setup();local value=feature_editor.new("harmony");value:enter()
  harmony_inspection.plan(song,1,{step=2,status="ok",output=62,role_pitches={v1=62}})
  open_label(value,"Result")
  luaunit.assert_equals(select_label(value,"Status").get(),"NO EVENT")
  luaunit.assert_equals(select_label(value,"CH1").get(),"NO EVENT")
  luaunit.assert_error(function()select_label(value,"Failure details")end)
end

function test_harmony_result_distinguishes_local_scale_bypass_and_specific_failure_reason()
  local song=setup();local value=feature_editor.new("harmony");value:enter()
  harmony_inspection.plan(song,1,{step=1,status="local_scale_bypass",bypass="local_scale_bypass",output=60})
  open_label(value,"Result")
  luaunit.assert_equals(select_label(value,"Status").get(),"LOCAL SCALE BYPASS")
  value:encoder_one()
  harmony_inspection.plan(song,1,{step=1,status="no_solution",reason="range",fallback="silence"})
  open_label(value,"Result")
  luaunit.assert_equals(select_label(value,"Status").get(),"NO VOICING range")
  open_label(value,"Failure details")
  luaunit.assert_equals(select_label(value,"Reason").get(),"range")
end

function test_harmony_result_names_local_octave_bypass_instead_of_no_voicing()
  local song=setup();local value=feature_editor.new("harmony");value:enter()
  harmony_inspection.plan(song,1,{step=1,status="local_octave",bypass="local_octave",output=72})
  open_label(value,"Result")
  luaunit.assert_equals(select_label(value,"Status").get(),"LOCAL OCTAVE BYPASS")
  luaunit.assert_error(function()select_label(value,"Failure details")end)
end

function test_harmony_group_result_surfaces_a_members_local_scale_bypass()
  local song=setup();local group=harmony_config.four_part_smooth(1,{1,2,3,4});group.enabled=true
  song.voicing={schema_version=1,groups={[1]=group}}
  song.channels[1].voicing=harmony_config.new_channel("ensemble");song.channels[1].voicing.group_id=1
  harmony_inspection.plan(song,1,{step=1,status="ok",output=48})
  harmony_inspection.plan(song,2,{step=1,status="local_scale_bypass",reason="local_scale_bypass",
    bypass="local_scale_bypass",output=64})
  local value=feature_editor.new("harmony");value:enter();open_label(value,"Result")
  luaunit.assert_equals(select_label(value,"Status").get(),"LOCAL SCALE BYPASS")
end

function test_harmony_result_step_selector_reads_one_coherent_event_chain()
  local song=setup();local first={step=1,status="ok",output=60};local second={step=2,status="ok",output=62}
  harmony_inspection.plan(song,1,first);harmony_inspection.scheduled(song,1,60,"root",first);harmony_inspection.emitted(song,1,60,"root",first)
  harmony_inspection.plan(song,1,second);harmony_inspection.scheduled(song,1,62,"root",second);harmony_inspection.emitted(song,1,62,"root",second)
  local value=feature_editor.new("harmony");value:enter();open_label(value,"Result")
  -- One row per voice: planned > sent, as note names (60 and 62).
  local musicutil=require("musicutil")
  local c,d=musicutil.note_num_to_name(60,true),musicutil.note_num_to_name(62,true)
  luaunit.assert_equals(select_label(value,"CH1").get(),c.." > "..c)
  select_label(value,"Step").set(2)
  luaunit.assert_equals(select_label(value,"CH1").get(),d.." > "..d)
end

function test_harmony_tone_map_is_per_binding_staged_and_cancelled_without_source_mutation()
  local song,channel=setup();channel.selected_patterns[1]=true
  song.patterns[1].note_values[1]=-7;channel.working_pattern.note_values[1]=-7
  local value=feature_editor.new("harmony");value:enter();value.draft.mode="pattern";open_label(value,"Tone Map")
  select_label(value,"Tone -7");value:enc(3,1)
  luaunit.assert_true(value.dirty);value:key(2)
  luaunit.assert_equals(value:get_screen(),"H01")
  luaunit.assert_equals(value.draft.pattern_maps,{})
  luaunit.assert_equals(song.patterns[1].note_values[1],-7)
end

function test_harmony_tone_map_reset_requires_explicit_confirmation()
  local song,channel=setup();channel.selected_patterns[1]=true
  song.patterns[1].note_values[1]=0;channel.working_pattern.note_values[1]=0
  local value=feature_editor.new("harmony");value:enter();value.draft.mode="pattern";open_label(value,"Tone Map")
  select_label(value,"Tone 0");value:enc(3,1)
  luaunit.assert_true(value:apply())
  value:enter();open_label(value,"Tone Map")
  open_label(value,"Reset map")
  luaunit.assert_equals(value:get_screen(),"TONE_MAP_RESET")
  value:key(2)
  luaunit.assert_not_nil(next(value.draft.pattern_maps))
  open_label(value,"Reset map");open_label(value,"Confirm reset")
  local binding=include("mosaic/lib/harmony/pattern").binding_key(channel)
  luaunit.assert_equals(value.draft.pattern_maps[binding].assignments,{})
end

function test_harmony_group_delete_confirmation_is_atomic_and_turns_members_off()
  local song=setup()
  local group=harmony_config.new_group(1);group.enabled=true
  song.voicing={schema_version=1,groups={[1]=group}}
  song.channels[1].voicing=harmony_config.new_channel("ensemble")
  song.channels[1].voicing.group_id=1
  song.channels[2].musical_merge=include("mosaic/lib/musical_merge/config").new()
  song.channels[2].musical_merge.target={kind="chord",group_id=1}
  local value=feature_editor.new("harmony");value:enter();open_label(value,"Groups")
  select_label(value,"Group");value.selected_group=1;open_label(value,"Delete group")
  luaunit.assert_equals(value:get_screen(),"H04_DELETE");open_label(value,"Confirm delete")
  luaunit.assert_nil(song.voicing.groups[1]);luaunit.assert_equals(song.channels[1].voicing.mode,"off")
  luaunit.assert_equals(song.channels[2].musical_merge.target.kind,"legacy")
  luaunit.assert_equals(value.status,"APPLIED")
end

function test_harmony_first_playing_apply_keeps_old_active_snapshot_until_pattern_boundary()
  local song,channel=setup();local value=feature_editor.new("harmony");value:enter();m_clock:start()
  value.draft.mode="pattern";value.dirty=true
  luaunit.assert_true(value:key(3));luaunit.assert_equals(value.status,"NEXT PATTERN")
  luaunit.assert_equals(harmony_state.effective_channel(song,1,channel.voicing).mode,"off")
  harmony_state.on_pattern_boundary(song)
  luaunit.assert_equals(harmony_state.effective_channel(song,1,channel.voicing).mode,"pattern")
end

function test_harmony_playing_group_delete_activates_group_and_merge_reference_atomically()
  local song=setup();local group=harmony_config.new_group(1);group.enabled=true
  song.voicing={schema_version=1,groups={[1]=group}}
  song.channels[1].voicing=harmony_config.new_channel("ensemble");song.channels[1].voicing.group_id=1
  local merge_config=include("mosaic/lib/musical_merge/config");local merge_state=include("mosaic/lib/musical_merge/state")
  song.channels[2].musical_merge=merge_config.new();song.channels[2].musical_merge.target={kind="chord",group_id=1}
  local value=feature_editor.new("harmony");value:enter();m_clock:start();open_label(value,"Groups");value.selected_group=1;open_label(value,"Delete group");open_label(value,"Confirm delete")
  luaunit.assert_equals(value.status,"NEXT PATTERN")
  luaunit.assert_not_nil(harmony_state.effective_song(song,song.voicing).groups[1])
  luaunit.assert_equals(merge_state.effective(song,2,song.channels[2].musical_merge).config.target.kind,"chord")
  harmony_state.on_pattern_boundary(song);merge_state.on_pattern_boundary(song)
  luaunit.assert_nil(harmony_state.effective_song(song,song.voicing).groups[1])
  luaunit.assert_equals(merge_state.effective(song,2,song.channels[2].musical_merge).config.target.kind,"legacy")
end

function test_optional_config_history_undo_redo_restores_merge_transaction()
  local _,channel=setup();channel.selected_patterns[1]=true
  local value=feature_editor.new("merge");value:enter();value.draft.mode="foundation";value.draft.anchor=1;value.dirty=true
  luaunit.assert_true(value:key(3));luaunit.assert_equals(channel.musical_merge.mode,"foundation")
  memory.undo(1);luaunit.assert_nil(channel.musical_merge)
  memory.redo(1);luaunit.assert_equals(channel.musical_merge.mode,"foundation")
end

function test_optional_config_group_history_is_atomic_from_every_affected_channel()
  local song=setup();local group=harmony_config.new_group(1);group.enabled=true
  song.voicing={schema_version=1,groups={[1]=group}}
  song.channels[1].voicing=harmony_config.new_channel("ensemble");song.channels[1].voicing.group_id=1
  local merge_config=include("mosaic/lib/musical_merge/config")
  song.channels[2].musical_merge=merge_config.new();song.channels[2].musical_merge.target={kind="chord",group_id=1}
  local value=feature_editor.new("harmony");value:enter();open_label(value,"Groups");value.selected_group=1;open_label(value,"Delete group");open_label(value,"Confirm delete")
  memory.undo(2)
  luaunit.assert_not_nil(song.voicing.groups[1]);luaunit.assert_equals(song.channels[1].voicing.mode,"ensemble")
  luaunit.assert_equals(song.channels[2].musical_merge.target.kind,"chord")
  memory.redo(1)
  luaunit.assert_nil(song.voicing.groups[1]);luaunit.assert_equals(song.channels[1].voicing.mode,"off")
  luaunit.assert_equals(song.channels[2].musical_merge.target.kind,"legacy")
end

function test_optional_config_later_edit_truncates_redo_branch()
  local _,channel=setup();local harmony=feature_editor.new("harmony");harmony:enter();harmony.draft.mode="pattern";harmony.dirty=true;harmony:key(3)
  memory.undo(1);luaunit.assert_nil(channel.voicing)
  channel.selected_patterns[1]=true
  local merge=feature_editor.new("merge");merge:enter();merge.draft.mode="foundation";merge.draft.anchor=1;merge.dirty=true;merge:key(3)
  memory.redo(1)
  luaunit.assert_nil(channel.voicing)
  luaunit.assert_equals(channel.musical_merge.mode,"foundation")
end

function test_optional_config_history_interleaves_with_existing_mask_history_order()
  local _,channel=setup();channel.selected_patterns[1]=true
  local merge=feature_editor.new("merge");merge:enter();merge.draft.mode="foundation";merge.draft.anchor=1;merge.dirty=true;merge:key(3)
  memory.record_event(1,"note_mask",{song_pattern=1,step=1,note=60})
  luaunit.assert_equals(channel.step_note_masks[1],60)
  memory.undo(1)
  luaunit.assert_nil(channel.step_note_masks[1]);luaunit.assert_equals(channel.musical_merge.mode,"foundation")
  memory.undo(1);luaunit.assert_nil(channel.musical_merge)
  memory.redo(1);luaunit.assert_equals(channel.musical_merge.mode,"foundation");luaunit.assert_nil(channel.step_note_masks[1])
  memory.redo(1);luaunit.assert_equals(channel.step_note_masks[1],60)
end

function test_optional_config_apply_without_a_change_does_not_create_history()
  setup()
  local value=feature_editor.new("merge");value:enter()
  luaunit.assert_equals(memory.get_event_count(1),0)
  luaunit.assert_true(value:apply())
  luaunit.assert_equals(memory.get_event_count(1),0)
end

function test_feature_editor_draw_keeps_context_body_and_footer_out_of_page_header()
  setup()
  local value=feature_editor.new("merge");value:enter()
  local calls={};local x,y
  local original_screen=screen
  screen={
    move=function(nx,ny)x,y=nx,ny end,
    text=function(label)calls[#calls+1]={x=x,y=y,label=label,align="left"}end,
    text_right=function(label)calls[#calls+1]={x=x,y=y,label=label,align="right"}end,
    level=function()end
  }
  value:draw()
  screen=original_screen
  luaunit.assert_equals(calls[1],{x=2,y=17,label="M01",align="left"})
  luaunit.assert_equals(calls[2],{x=126,y=17,label="CH01",align="right"})
  luaunit.assert_equals({calls[3].y,calls[4].y,calls[5].y,calls[6].y},{27,36,45,54})
  luaunit.assert_equals(calls[#calls].y,63)
end


function test_merge_selecting_custom_preserves_existing_cycle_percentages()
  local _,channel=setup();channel.selected_patterns[1]=true
  local value=feature_editor.new("merge");value:enter();value.draft.cycles=2
  value.draft.shape="fill";value.draft.percentages={25,100}
  open_label(value,"Phrase");select_label(value,"Shape")
  value:enc(3,1)
  luaunit.assert_equals(value.draft.shape,"custom")
  luaunit.assert_equals(value.draft.percentages,{25,100})
end

function test_harmony_revoice_bass_tones_are_actual_source_ids()
  local _,channel=setup();channel.chord_one_mask=4;channel.step_chord_masks[9]={[3]=7}
  local value=feature_editor.new("harmony");value:enter();value.draft.mode="revoice";value.draft.bass.mode="inversion"
  open_label(value,"Bass");select_label(value,"Tone")
  local field=value:get_fields()[value.selected]
  luaunit.assert_equals(field.values,{"root","chord1","chord3"})
end

function test_optional_config_undo_preserves_later_independent_channel_edit()
  local song=setup();song.channels[1].selected_patterns[1]=true;song.channels[2].selected_patterns[1]=true
  local one=feature_editor.new("merge");one:enter();one.draft.mode="foundation";one.draft.anchor=1;one.dirty=true;one:apply()
  program.get().selected_channel=2
  local two=feature_editor.new("merge");two:enter();two.draft.mode="foundation";two.draft.anchor=1;two.draft.amount=42;two.dirty=true;two:apply()
  memory.undo(1)
  luaunit.assert_nil(song.channels[1].musical_merge)
  luaunit.assert_equals(song.channels[2].musical_merge.amount,42)
end

-- A refused restoration used to leave bulk undo spinning. undo_all loops while
-- the event count is above zero, and a feature undo only decrements it when
-- the transition is applied, so a refusal meant the loop never ended and the
-- Lua thread stopped answering: no screen, no grid, no clock. The guard is
-- progress, not the particular reason a restoration was refused.
function test_optional_config_bulk_undo_reports_refusal_instead_of_retrying()
  local song = setup(); song.channels[1].selected_patterns[1] = true
  local editor = feature_editor.new("merge"); editor:enter()
  editor.draft.mode = "foundation"; editor.draft.anchor = 1; editor.dirty = true; editor:apply()
  luaunit.assert_true(memory.get_event_count(1) > 0, "the edit is undoable to begin with")

  -- Undo the only feature event, then ask again: there is nothing left to
  -- undo, so a second bulk undo must return rather than loop.
  luaunit.assert_true(memory.undo_all(1) ~= false, "the first bulk undo completes")
  luaunit.assert_equals(memory.get_event_count(1), 0, "and empties the channel history")
  memory.undo_all(1)
  luaunit.assert_equals(memory.get_event_count(1), 0, "a bulk undo with nothing to undo is a no-op")
end

function test_optional_config_bulk_redo_reports_refusal_instead_of_retrying()
  local song = setup(); song.channels[1].selected_patterns[1] = true
  local editor = feature_editor.new("merge"); editor:enter()
  editor.draft.mode = "foundation"; editor.draft.anchor = 1; editor.dirty = true; editor:apply()
  memory.undo_all(1)
  luaunit.assert_true(memory.redo_all(1) ~= false, "the redo completes")
  memory.redo_all(1)
  luaunit.assert_equals(memory.get_event_count(1), memory.get_total_event_count(1),
    "a bulk redo with nothing left to redo is a no-op")
end

-- README.md Channel pages: K3 applies the whole validated draft. Plan §0
-- (characterisation): a live v1 configuration is edited as its canonical v2 form,
-- and a saved v2 Fragments configuration is kept intact by an unrelated edit.
function test_merge_editor_drafts_live_v1_configuration_as_canonical_v2()
  local song, channel = setup()
  channel.selected_patterns[1] = true
  channel.musical_merge = {schema_version=1,mode="foundation",anchor=1,amount=100,accent=70,gap=0,seed=0,
    ranking_version=1,cycles=1,shape="flat",percentages={100},variation="fixed",keep_anchor_pitch=false,
    target={kind="legacy"},unknown=true}
  local value = feature_editor.new("merge")
  value:enter()
  luaunit.assert_equals(value.draft.schema_version, 2)
  luaunit.assert_nil(value.draft.unknown)
  value.draft.amount, value.dirty = 40, true
  luaunit.assert_true(value:key(3))
  luaunit.assert_equals(channel.musical_merge.schema_version, 2)
  luaunit.assert_equals(channel.musical_merge.amount, 40)
  luaunit.assert_equals(merge_state.effective(song, 1, channel.musical_merge).config.amount, 40)
end

function test_merge_editor_keeps_saved_v2_fragments_fields_through_an_edit()
  local _, channel = setup()
  channel.selected_patterns[1] = true
  channel.musical_merge = include("mosaic/lib/musical_merge/config").new()
  channel.musical_merge.mode, channel.musical_merge.fragments.size = "fragments", 16
  local value = feature_editor.new("merge")
  value:enter()
  value.draft.seed, value.dirty = 5, true
  luaunit.assert_true(value:key(3))
  luaunit.assert_equals({channel.musical_merge.mode, channel.musical_merge.fragments.size, channel.musical_merge.seed},
    {"fragments", 16, 5})
end

-- Merge shape extensions (docs/musical-merge-extensions-plan.md §5; README
-- "Merge Shape"): the Fragments, Interlock and Structure screens, the reasons
-- the Result and Reason screens show, and Apply's rejections.

local merge_config = include("mosaic/lib/musical_merge/config")
local merge_display = include("mosaic/lib/musical_merge/display")

local function labels(value)
  local result = {}
  for index, field in ipairs(value:get_fields()) do result[index] = field.label end
  return result
end

function test_merge_display_translates_engine_reasons_for_the_norns_font()
  -- The font has no '·' glyph and players count fragments from 1.
  luaunit.assert_equals(merge_display.reason("FRAGMENT 0 \194\183 P03"), "FRAGMENT 1 P03")
  luaunit.assert_equals(merge_display.reason("FRAGMENT 11 \194\183 P16"), "FRAGMENT 12 P16")
  luaunit.assert_equals(merge_display.reason("MARKER \194\183 CHORD G02"), "MARKER CHORD G02")
  luaunit.assert_equals(merge_display.reason("KEPT ANCHOR"), "KEPT ANCHOR")
  luaunit.assert_nil(merge_display.reason(nil))
  luaunit.assert_equals(merge_display.reasons({"INTERLOCK CH02"}), "INTERLOCK CH02")
  luaunit.assert_equals(merge_display.reasons({"gap", "INTERLOCK CH02"}), "gap, INTERLOCK")
  luaunit.assert_nil(merge_display.reasons({}))
  luaunit.assert_equals(merge_display.admission(nil), "OFF")
  luaunit.assert_equals(merge_display.admission({status = "ok"}), "ON")
  luaunit.assert_equals(merge_display.admission({status = "RESYNC"}), "RESYNC")
  luaunit.assert_equals(merge_display.leader_values(3)[1], "off")
  luaunit.assert_equals(#merge_display.leader_values(3), 16)
  for _, shown in ipairs(merge_display.leader_values(3)) do luaunit.assert_not_equals(shown, "ch03") end
  luaunit.assert_equals(merge_display.leader_number("ch07"), 7)
  luaunit.assert_nil(merge_display.leader_number("off"))
  luaunit.assert_equals(merge_display.shape_prefix("foundation", "trig"), "SHAPE")
  luaunit.assert_nil(merge_display.shape_prefix("foundation", "note"))
  for _, kind in ipairs({"trig", "note", "velocity", "length"}) do
    luaunit.assert_equals(merge_display.shape_prefix("fragments", kind), "FRAGMENTS")
  end
  luaunit.assert_nil(merge_display.shape_prefix("off", "trig"))
end

function test_merge_fragments_mode_routes_rhythm_to_fragments_and_hides_foundation_rows()
  local _,channel=setup();channel.selected_patterns[1]=true;channel.selected_patterns[2]=true
  local value=feature_editor.new("merge");value:enter()
  value:enc(3,1);value:enc(3,1)
  luaunit.assert_equals(value.draft.mode,"fragments")
  open_label(value,"Rhythm");luaunit.assert_equals(value:get_screen(),"FRAGMENTS")
  luaunit.assert_equals(labels(value),{"Size","Keep anchor","Seed"})
  select_label(value,"Size");value:enc(3,1);luaunit.assert_equals(value.draft.fragments.size,16)
  select_label(value,"Keep anchor");value:enc(3,1)
  luaunit.assert_equals(labels(value),{"Size","Keep anchor","Anchor","Seed"})
  -- Keep anchor needs an assigned anchor (plan §2.3): Apply refuses without one.
  luaunit.assert_false(value:key(3));luaunit.assert_equals(value.status,"INVALID merge anchor")
  select_label(value,"Anchor");value:enc(3,1);luaunit.assert_equals(value.draft.anchor,1)
  luaunit.assert_true(value:key(3));luaunit.assert_equals(value.status,"APPLIED")
  luaunit.assert_equals(channel.musical_merge.mode,"fragments")
  luaunit.assert_equals(channel.musical_merge.fragments,{size=16,keep_anchor=true})
  value:encoder_one();open_label(value,"Phrase");luaunit.assert_equals(labels(value),{"Cycles","Variation"})
  value:encoder_one();luaunit.assert_equals(labels(value),{"Mode","Rhythm","Phrase","Result"})
end

function test_merge_fragments_keep_anchor_rejects_an_unassigned_anchor()
  local _,channel=setup();channel.selected_patterns[2]=true
  local value=feature_editor.new("merge");value:enter()
  value.draft.mode="fragments";value.draft.fragments.keep_anchor=true;value.draft.anchor=1;value.dirty=true
  luaunit.assert_false(value:key(3));luaunit.assert_equals(value.status,"INVALID anchor not assigned")
  luaunit.assert_nil(channel.musical_merge)
end

function test_merge_fragments_result_and_reason_name_the_fragment_from_one()
  local song,channel=setup();channel.selected_patterns[1]=true;channel.selected_patterns[2]=true
  local start=fn.calc_grid_count(channel.start_trig[1],channel.start_trig[2])
  song.patterns[2].trig_values[start]=1;song.patterns[2].velocity_values[start]=33
  local config=merge_config.new();config.mode="fragments";config.fragments.size=4
  channel.musical_merge=config;pattern.update_working_patterns(song,{[1]=true})
  local plan=channel.working_pattern.fragments
  luaunit.assert_equals(plan.status,"ok")
  local source=plan.fragments[1].source
  local value=feature_editor.new("merge");value:enter();open_label(value,"Result")
  select_label(value,"Step").set(start)
  luaunit.assert_equals(select_label(value,"Decision").get(),string.format("FRAGMENT 1 P%02d",source))
  open_label(value,"Reason")
  luaunit.assert_equals(select_label(value,"Decision").get(),string.format("FRAGMENT 1 P%02d",source))
  luaunit.assert_equals(select_label(value,"Pitch target").get(),"NOT USED")
  if source==2 then
    luaunit.assert_equals(select_label(value,"Role").get(),"fragment P2")
    luaunit.assert_equals(select_label(value,"Velocity").get(),33)
  end
end

function test_merge_fragments_without_patterns_shows_assign_pattern()
  local song,channel=setup()
  local config=merge_config.new();config.mode="fragments";channel.musical_merge=config
  pattern.update_working_patterns(song,{[1]=true})
  local value=feature_editor.new("merge");value:enter();open_label(value,"Result")
  luaunit.assert_equals(select_label(value,"Decision").get(),"ASSIGN PATTERN")
end

function test_merge_interlock_screen_edits_leader_and_window_and_apply_rejects_a_chain()
  local song,channel=setup();channel.selected_patterns[1]=true
  local leader=song.channels[2];leader.selected_patterns[1]=true
  local chained=merge_config.new();chained.mode="foundation";chained.anchor=1;chained.interlock.leader=3
  leader.musical_merge=chained
  local value=feature_editor.new("merge");value:enter()
  value.draft.mode="foundation";value.draft.anchor=1
  open_label(value,"Rhythm");open_label(value,"Interlock")
  luaunit.assert_equals(value:get_screen(),"INTERLOCK")
  luaunit.assert_equals(labels(value),{"Leader","Window","Status"})
  local leader_field=select_label(value,"Leader")
  luaunit.assert_equals(feature_editor.field_value(leader_field),"OFF")
  -- Every other channel is listed; this one never is.
  for _,shown in ipairs(leader_field.values)do luaunit.assert_not_equals(shown,"ch01")end
  value:enc(3,1);luaunit.assert_equals(value.draft.interlock.leader,2)
  luaunit.assert_equals(feature_editor.field_value(select_label(value,"Leader")),"CH02")
  select_label(value,"Window");value:enc(3,1);value:enc(3,1);value:enc(3,1);value:enc(3,1);value:enc(3,1)
  luaunit.assert_equals(value.draft.interlock.window,4)
  -- Channel 2 already follows channel 3 (plan §1.5).
  luaunit.assert_false(value:key(3));luaunit.assert_equals(value.status,"INVALID LEADER HAS LEADER")
  luaunit.assert_nil(channel.musical_merge)
  luaunit.assert_true(value.dirty)
  -- A channel that is a leader cannot follow.
  leader.musical_merge=nil;song.channels[3].musical_merge=merge_config.new()
  song.channels[3].musical_merge.interlock.leader=1
  value:reload();value.draft.mode="foundation";value.draft.anchor=1;value.draft.interlock.leader=2;value.dirty=true
  luaunit.assert_false(value:key(3));luaunit.assert_equals(value.status,"INVALID CHANNEL IS A LEADER")
  song.channels[3].musical_merge=nil
  value:reload();value.draft.mode="foundation";value.draft.anchor=1;value.draft.interlock.leader=2;value.dirty=true
  luaunit.assert_true(value:key(3));luaunit.assert_equals(channel.musical_merge.interlock,{leader=2,window=0})
end

function test_merge_result_shows_interlock_admission_and_a_rejected_queue()
  local song,channel=setup();channel.selected_patterns[1]=true;song.channels[2].selected_patterns[1]=true
  local config=merge_config.new();config.mode="foundation";config.anchor=1;config.interlock.leader=2
  channel.musical_merge=config;pattern.update_working_patterns(song,{[1]=true})
  local value=feature_editor.new("merge");value:enter();open_label(value,"Result")
  local shown=select_label(value,"Interlock").get()
  luaunit.assert_equals(shown,merge_display.admission(channel.working_pattern.foundation.interlock))
  luaunit.assert_error(function()select_label(value,"Rejected")end)
  merge_state.effective(song,1,config).queued=nil
  merge_state.peek(song,1).rejected="LEADER HAS LEADER"
  value:encoder_one();open_label(value,"Result")
  luaunit.assert_equals(select_label(value,"Rejected").get(),"LEADER HAS LEADER")
end

function test_merge_reason_lists_every_rejection_reason_in_order()
  local song,channel=setup()
  channel.working_pattern.foundation={status="ok",roles={},reasons={[5]="gap"},reason_lists={[5]={"gap","INTERLOCK CH02"}},
    sources={[5]={2}},velocities={}}
  local value=feature_editor.new("merge");value:enter();open_label(value,"Result")
  select_label(value,"Step").set(5)
  luaunit.assert_equals(feature_editor.field_value(select_label(value,"Decision")),"GAP, INTERLOCK")
  open_label(value,"Reason")
  luaunit.assert_equals(feature_editor.field_value(select_label(value,"Decision")),"GAP, INTERLOCK")
  luaunit.assert_equals(select_label(value,"Role").get(),"EMPTY P2")
end

-- Review D9 (plan §1.2 fallback, §3 "its bypass status is displayed
-- separately", §5 "Result and Reason expose RESYNC ... PLAN LIMIT"): the
-- Reason dashboard (six rows) shows the Interlock admission in its own row
-- next to the ordered rejection reasons; the role row names the sources.
function test_merge_reason_shows_interlock_bypass_separately_from_reasons()
  for _, status in ipairs({"RESYNC", "PLAN LIMIT"}) do
    local song,channel=setup()
    channel.working_pattern.foundation={status="ok",config={mode="foundation"},roles={[5]="addition"},reasons={[5]="gap"},
      reason_lists={[5]={"gap"}},sources={[5]={2,3}},velocities={},interlock={status=status,blocked={}}}
    local value=feature_editor.new("merge");value:enter();open_label(value,"Result")
    select_label(value,"Step").set(5)
    luaunit.assert_equals(select_label(value,"Interlock").get(),status)
    open_label(value,"Reason")
    luaunit.assert_equals(labels(value),{"Step","Role","Decision","Interlock","Velocity","Pitch target"})
    luaunit.assert_equals(feature_editor.field_value(select_label(value,"Decision")),"GAP")
    luaunit.assert_equals(select_label(value,"Interlock").get(),status)
    luaunit.assert_equals(select_label(value,"Role").get(),"addition P2,3")
  end
  -- Filtering, no leader, and Fragments (Interlock is Foundation-only).
  local song,channel=setup()
  channel.working_pattern.foundation={status="ok",roles={},reasons={},reason_lists={[5]={"gap","INTERLOCK CH02"}},
    sources={},velocities={},interlock={status="ok",blocked={[5]=true}}}
  local value=feature_editor.new("merge");value:enter();open_label(value,"Result");select_label(value,"Step").set(5)
  open_label(value,"Reason")
  luaunit.assert_equals(feature_editor.field_value(select_label(value,"Decision")),"GAP, INTERLOCK")
  luaunit.assert_equals(select_label(value,"Interlock").get(),"ON")
  luaunit.assert_equals(select_label(value,"Role").get(),"EMPTY")
  channel.working_pattern.foundation.interlock=nil
  luaunit.assert_equals(select_label(value,"Interlock").get(),"OFF")
  channel.working_pattern.foundation=nil;channel.working_pattern.fragments={status="ok",roles={},reasons={},sources={}}
  luaunit.assert_equals(select_label(value,"Interlock").get(),"NOT USED")
end

function test_merge_structure_screen_sets_markers_and_an_enabled_group()
  local song,channel=setup();channel.selected_patterns[1]=true
  local group=harmony_config.four_part_smooth(2,{1,2,3,4});group.enabled=true
  local disabled=harmony_config.four_part_smooth(1,{5,6,7,8});disabled.enabled=false
  song.voicing={schema_version=1,groups={[1]=disabled,[2]=group}}
  local value=feature_editor.new("merge");value:enter()
  value.draft.mode="foundation";value.draft.anchor=1
  open_label(value,"Pitch");open_label(value,"Structure")
  luaunit.assert_equals(value:get_screen(),"STRUCTURE")
  luaunit.assert_equals(labels(value),{"Markers"})
  luaunit.assert_equals(feature_editor.field_value(select_label(value,"Markers")),"OFF")
  value:enc(3,1);value:enc(3,1)
  luaunit.assert_equals(value.draft.structure,{markers="every_4",group_id=2})
  luaunit.assert_equals(feature_editor.field_value(select_label(value,"Markers")),"EVERY 4")
  luaunit.assert_equals(select_label(value,"Chord group").values,{2})
  luaunit.assert_true(value:key(3));luaunit.assert_equals(channel.musical_merge.structure,{markers="every_4",group_id=2})
  -- Markers Off stores no group (plan §4).
  select_label(value,"Markers");value:enc(3,-1);value:enc(3,-1)
  luaunit.assert_equals(value.draft.structure.markers,"off");luaunit.assert_nil(value.draft.structure.group_id)
  luaunit.assert_equals(labels(value),{"Markers"})
end

function test_merge_structure_apply_requires_an_enabled_group()
  local song,channel=setup();channel.selected_patterns[1]=true
  local value=feature_editor.new("merge");value:enter()
  value.draft.mode="foundation";value.draft.anchor=1
  open_label(value,"Pitch");open_label(value,"Structure");value:enc(3,1)
  luaunit.assert_equals(value.draft.structure.markers,"anchors");luaunit.assert_nil(value.draft.structure.group_id)
  luaunit.assert_false(value:key(3));luaunit.assert_not_nil(value.status:match("^INVALID"))
  luaunit.assert_nil(channel.musical_merge)
end

function test_merge_reason_shows_the_structural_marker_decision()
  local song,channel=setup();channel.selected_patterns[1]=true
  local group=harmony_config.four_part_smooth(1,{1,2,3,4});group.enabled=true
  song.voicing={schema_version=1,groups={[1]=group}}
  local config=merge_config.new();config.mode="foundation";config.anchor=1;config.structure={markers="every_4",group_id=1}
  channel.musical_merge=config;pattern.update_working_patterns(song,{[1]=true})
  local start=fn.calc_grid_count(channel.start_trig[1],channel.start_trig[2])
  local value=feature_editor.new("merge");value:enter();open_label(value,"Result")
  select_label(value,"Step").set(start)
  luaunit.assert_equals(select_label(value,"Pitch").get(),"MARKER CHORD G01")
  harmony_inspection.plan(song,1,{step=start,status="off",structural_status="chord_missing",structural_reason="CHORD MISSING"})
  open_label(value,"Reason")
  luaunit.assert_equals(select_label(value,"Pitch target").get(),"CHORD MISSING")
  value:encoder_one();open_label(value,"Result");select_label(value,"Step").set(start+1)
  luaunit.assert_error(function()select_label(value,"Pitch")end)
end

-- Review D8 (plan §4 "Explicit note-mask, random, fixed and quantised-fixed
-- bypasses retain the complete existing legacy path"): a marker event whose
-- pitch bypassed Structure snapping is reported as that bypass on Result and
-- Reason, never as the marker chord it did not use. The planned-marker preview
-- is kept for a marker with no played event. Played through step.handle.
function test_merge_result_and_reason_report_a_marker_bypass_not_the_marker_chord()
  local cases = {
    {name = "note_mask", shown = "BYPASS NOTE MASK", setup = function(channel, start) channel.step_note_masks[start] = 61 end},
    {name = "random", shown = "BYPASS RANDOM", setup = function(channel, start)
      channel.trig_lock_params[1] = {id = "bipolar_random_note", param_id = "test_random"}
      program.add_step_param_trig_lock(start, 1, 4) end},
    {name = "fixed", shown = "BYPASS FIXED", setup = function(channel, start)
      channel.trig_lock_params[3] = {id = "fixed_note", param_id = "test_fixed"}
      program.add_step_param_trig_lock(start, 3, 63) end},
    {name = "quantised_fixed", shown = "BYPASS QUANTISED FIXED", setup = function(channel, start)
      channel.trig_lock_params[3] = {id = "quantised_fixed_note", param_id = "test_fixed"}
      program.add_step_param_trig_lock(start, 3, 63) end},
  }
  local original_random = random
  local ok, err = pcall(function()
    for _, case in ipairs(cases) do
      local song, channel = setup(); harmony_inspection.reset(); channel.selected_patterns[1] = true
      local group = harmony_config.four_part_smooth(1, {1, 2, 3, 4}); group.enabled = true
      song.voicing = {schema_version = 1, groups = {[1] = group}}
      local config = merge_config.new(); config.mode = "foundation"; config.anchor = 1
      config.structure = {markers = "every_4", group_id = 1}
      channel.musical_merge = config
      local start = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
      song.patterns[1].trig_values[start] = 1; song.patterns[1].note_values[start] = 1
      case.setup(channel, start); pattern.update_working_patterns(song, {[1] = true})
      local value = feature_editor.new("merge"); value:enter(); open_label(value, "Result")
      select_label(value, "Step").set(start)
      -- Not yet played: the planned marker.
      luaunit.assert_equals(select_label(value, "Pitch").get(), "MARKER CHORD G01", case.name)
      random = function() return 1 end
      step.handle(1, start)
      random = original_random
      luaunit.assert_equals(harmony_inspection.snapshot(song, 1, start).planned.structural_status, case.name)
      luaunit.assert_equals(select_label(value, "Pitch").get(), case.shown, case.name)
      open_label(value, "Reason")
      luaunit.assert_equals(select_label(value, "Pitch target").get(), case.shown, case.name)
    end
  end)
  random = original_random
  if not ok then error(err, 0) end
end

function test_harmony_result_names_marker_priority_whatever_the_fallback()
  local song=setup();local value=feature_editor.new("harmony");value:enter()
  harmony_inspection.plan(song,1,{step=1,status="marker_priority",reason="MARKER PRIORITY",bypass="marker_priority",
    fallback="legacy",output=60})
  open_label(value,"Result")
  luaunit.assert_equals(select_label(value,"Status").get(),"MARKER PRIORITY")
end

function test_harmony_group_delete_lists_merge_structure_and_target_references()
  local song=setup();local group=harmony_config.four_part_smooth(1,{1,2});group.enabled=true
  song.voicing={schema_version=1,groups={[1]=group}}
  song.channels[1].voicing=harmony_config.new_channel("ensemble");song.channels[1].voicing.group_id=1
  local marked=merge_config.new();marked.structure={markers="anchors",group_id=1};song.channels[5].musical_merge=marked
  local targeted=merge_config.new();targeted.target={kind="chord",group_id=1};song.channels[7].musical_merge=targeted
  local value=feature_editor.new("harmony");value:enter()
  open_label(value,"Groups");open_label(value,"Delete group")
  luaunit.assert_equals(value:get_screen(),"H04_DELETE")
  luaunit.assert_equals(select_label(value,"Affected").get(),"1,5,7")
  open_label(value,"Confirm delete")
  luaunit.assert_equals(song.channels[5].musical_merge.structure,{markers="off"})
  luaunit.assert_equals(song.channels[7].musical_merge.target,{kind="legacy"})
  luaunit.assert_equals(song.channels[1].voicing.mode,"off")
end
