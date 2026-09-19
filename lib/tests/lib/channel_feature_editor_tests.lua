-- README.md Channel pages: Merge Shape and Harmony use staged E2/E3 drafts;
-- K3 applies the whole validated draft and K2 cancels without musical mutation.

local feature_editor = include("mosaic/lib/pages/channel_edit_page/channel_feature_editor")
local merge_state = include("mosaic/lib/musical_merge/state")
local harmony_state = include("mosaic/lib/harmony/config_state")
local harmony_config = include("mosaic/lib/harmony/config")

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
  local _,channel=setup();channel.chord_one_mask=4;channel.chord_three_mask=7
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
