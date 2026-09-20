-- README.md Voice leading / Musical Merge: opt-in placement changes final MIDI
-- pitch while preserving the ordinary scheduler, rhythm, velocity and source data.

local step = include("mosaic/lib/step")
local pattern_model = include("mosaic/lib/pattern")
local harmony_config = include("mosaic/lib/harmony/config")
local harmony_config_state = include("mosaic/lib/harmony/config_state")
local harmony_runtime_state = include("mosaic/lib/harmony/state")
local harmony_inspection = include("mosaic/lib/harmony/inspection")
local pattern_harmony = include("mosaic/lib/harmony/pattern")
local merge_config = include("mosaic/lib/musical_merge/config")
local quantiser = include("mosaic/lib/quantiser")

include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
local m_clock = include("mosaic/lib/clock/m_clock")

local function setup()
  program.init()
  globals.reset()
  params.reset()
  m_clock.init()
  harmony_config_state.reset()
  harmony_runtime_state.reset()
  harmony_inspection.reset()
  m_clock:start()
  program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  return song
end

local function exact_role(pitch)
  return {min=pitch,max=pitch,centre=pitch,preferred_leap=127,
    strict_leap=false,enabled=true}
end

local function source(song, number, notes, trigs)
  local value = program.initialise_default_pattern()
  for step_number, note in pairs(notes or {}) do value.note_values[step_number] = note end
  for _, step_number in ipairs(trigs or {}) do value.trig_values[step_number] = 1 end
  song.patterns[number] = value
end

local function assign(song, channel_number, pattern_number)
  fn.add_to_set(song.channels[channel_number].selected_patterns, pattern_number)
  pattern_model.update_working_pattern(channel_number, song)
end

local function progress(beats)
  for _ = 1, 24 * beats do m_clock.get_clock_lattice():pulse() end
end

function test_harmony_playback_revoice_places_complete_chord_bundle()
  local song = setup()
  source(song, 1, {[1]=0}, {1})
  local channel = song.channels[1]
  channel.chord_one_mask, channel.chord_two_mask = 2, 4
  channel.voicing = harmony_config.new_channel("revoice")
  channel.voicing.roles.v1, channel.voicing.roles.v2, channel.voicing.roles.v3 =
    exact_role(48), exact_role(52), exact_role(55)
  assign(song, 1, 1)

  step.handle(1, 1)
  luaunit.assert_equals({midi_note_on_events[1][1],midi_note_on_events[2][1],midi_note_on_events[3][1]},
    {48,52,55})
  luaunit.assert_equals(song.patterns[1].note_values[1], 0)
  local shown=harmony_inspection.snapshot(song,1)
  luaunit.assert_equals(shown.planned.status,"ok")
  luaunit.assert_equals(shown.planned.source,0)
  luaunit.assert_not_nil(shown.scheduled.pitch)
  luaunit.assert_not_nil(shown.emitted.pitch)
end

function test_harmony_playback_revoice_rebuilds_for_each_changed_pitch_bundle()
  local song = setup()
  source(song, 1, {[1]=0,[2]=1,[3]=2}, {1,2,3})
  local channel = song.channels[1]
  channel.chord_one_mask = 1
  channel.voicing = harmony_config.new_channel("revoice")
  assign(song, 1, 1)

  step.handle(1, 1)
  local first_revision = harmony_runtime_state.snapshot(song).channels[1].prepared.revision
  step.handle(1, 2)
  local second_revision = harmony_runtime_state.snapshot(song).channels[1].prepared.revision
  step.handle(1, 3)
  local third_revision = harmony_runtime_state.snapshot(song).channels[1].prepared.revision

  local pitches = {}
  for _, event in ipairs(midi_note_on_events) do pitches[#pitches + 1] = event[1] end
  luaunit.assert_equals({first_revision,second_revision,third_revision}, {
    "revoice|1|1|0|0|0|root|60|chord1|62",
    "revoice|1|1|0|0|0|root|62|chord1|64",
    "revoice|1|1|0|0|0|root|64|chord1|65"})
  luaunit.assert_equals(pitches, {48,50,50,52,52,53})
end

function test_harmony_playback_revoice_pins_absolute_note_mask_without_rewriting_it()
  local song=setup();source(song,1,{[1]=0},{1})
  local channel=song.channels[1];channel.step_note_masks[1]=60;channel.chord_one_mask=2
  channel.voicing=harmony_config.new_channel("revoice")
  channel.voicing.roles.v1={min=48,max=72,centre=72,preferred_leap=127,strict_leap=false,enabled=true}
  channel.voicing.roles.v2={min=52,max=79,centre=76,preferred_leap=127,strict_leap=false,enabled=true}
  assign(song,1,1);step.handle(1,1)
  luaunit.assert_equals(midi_note_on_events[1][1],60)
  luaunit.assert_equals(channel.step_note_masks[1],60)
end

function test_harmony_playback_revoice_cache_distinguishes_equal_pitch_absolute_pin()
  local song=setup();source(song,1,{[1]=0,[2]=0},{1,2})
  local channel=song.channels[1];channel.step_note_masks[2]=60
  channel.voicing=harmony_config.new_channel("revoice");assign(song,1,1)
  step.handle(1,1);step.handle(1,2)
  luaunit.assert_equals({midi_note_on_events[1][1],midi_note_on_events[2][1]},{48,60})
end

function test_harmony_playback_revoice_arp_uses_frozen_solved_bundle()
  local song = setup()
  source(song, 1, {[1]=0}, {1})
  local channel = song.channels[1]
  channel.chord_one_mask, channel.chord_two_mask = 2, 4
  channel.voicing = harmony_config.new_channel("revoice")
  channel.voicing.roles.v1, channel.voicing.roles.v2, channel.voicing.roles.v3 =
    exact_role(48), exact_role(52), exact_role(55)
  channel.trig_lock_params[1] = {id="chord_arp",param_id="chord_arp_1"}
  program.add_step_param_trig_lock(1, 1, 4)
  assign(song, 1, 1)

  step.handle(1, 1)
  luaunit.assert_equals(midi_note_on_events[1][1], 48)
  -- A later scale mutation cannot alter already prepared arp pitches.
  song.scales[1].root_note = 6
  song.scales[1].version = song.scales[1].version + 1
  progress(1)
  progress(1)
  luaunit.assert_equals({midi_note_on_events[2][1],midi_note_on_events[3][1]}, {52,55})
end

function test_harmony_playback_delayed_first_arp_voice_commits_at_first_reached_onset()
  local song=setup();source(song,1,{[1]=0},{1})
  local channel=song.channels[1];channel.chord_one_mask=2
  channel.voicing=harmony_config.new_channel("revoice")
  channel.trig_lock_params[1]={id="chord_arp",param_id="chord_arp_1"}
  channel.trig_lock_params[2]={id="chord_strum_pattern",param_id="chord_strum_pattern_1"}
  program.add_step_param_trig_lock(1,1,4)
  program.add_step_param_trig_lock(1,2,2) -- reverse: empty chord4 is the first slot
  assign(song,1,1);step.handle(1,1)
  luaunit.assert_equals(#midi_note_on_events,0)
  local runtime=harmony_runtime_state.snapshot(song).channels[1]
  luaunit.assert_nil(runtime.consumed)
  luaunit.assert_equals(runtime.consumed_count,0)
  progress(1);progress(1);progress(1);progress(1)
  runtime=harmony_runtime_state.snapshot(song).channels[1]
  luaunit.assert_true(#midi_note_on_events>0)
  luaunit.assert_not_nil(runtime.consumed)
  luaunit.assert_equals(runtime.consumed_count,1)
end

local function delayed_first_arp(song,length,spread,acceleration,mute_root)
  local channel=song.channels[1];channel.chord_one_mask=2
  channel.voicing=harmony_config.new_channel("revoice")
  channel.trig_lock_params[1]={id="chord_arp",param_id="chord_arp_1"}
  channel.trig_lock_params[2]={id="chord_strum_pattern",param_id="chord_strum_pattern_1"}
  program.add_step_param_trig_lock(1,1,4)
  program.add_step_param_trig_lock(1,2,2) -- reverse: three empty slots precede chord1
  if spread then
    channel.trig_lock_params[3]={id="chord_spread",param_id="chord_spread_1"}
    program.add_step_param_trig_lock(1,3,spread)
  end
  if acceleration then
    channel.trig_lock_params[4]={id="chord_acceleration",param_id="chord_acceleration_1",cc_min_value=-5}
    program.add_step_param_trig_lock(1,4,acceleration)
  end
  if mute_root then
    channel.trig_lock_params[5]={id="mute_root_note",param_id="mute_root_note_1"}
    program.add_step_param_trig_lock(1,5,1)
  end
  song.patterns[1].lengths[1]=length
  assign(song,1,1);step.handle(1,1)
  return harmony_runtime_state.snapshot(song).channels[1]
end

function test_harmony_playback_zero_gate_silent_arp_does_not_commit_history()
  local song=setup();source(song,1,{[1]=0},{1})
  local runtime=delayed_first_arp(song,0)
  luaunit.assert_nil(runtime.consumed)
  luaunit.assert_equals(runtime.consumed_count,0)
end

function test_harmony_playback_gate_before_first_voiced_arp_slot_does_not_commit_history()
  local song=setup();source(song,1,{[1]=0},{1})
  local runtime=delayed_first_arp(song,0.5)
  luaunit.assert_nil(runtime.consumed)
  luaunit.assert_equals(runtime.consumed_count,0)
end

function test_harmony_playback_terminating_interval_before_first_voiced_arp_slot_does_not_commit_history()
  local song=setup();source(song,1,{[1]=0},{1})
  -- arp 1/6 + spread 1/12 is positive once; acceleration -5 terminates
  -- interval two while the reverse sequence is still on leading rests.
  local runtime=delayed_first_arp(song,2,2,-5)
  luaunit.assert_nil(runtime.consumed)
  luaunit.assert_equals(runtime.consumed_count,0)
end

function test_harmony_playback_swung_gate_before_first_voiced_arp_slot_does_not_commit_history()
  local song=setup();source(song,1,{[1]=0},{1})
  local channel=song.channels[1];channel.swing_shuffle_type=1;channel.swing=50
  channel.start_trig={1,4};channel.end_trig={1,4}
  m_clock.set_swing_shuffle_type(1,1);m_clock.set_channel_swing(1,50)
  local runtime=delayed_first_arp(song,0.55,nil,nil,true)
  progress(2)
  runtime=harmony_runtime_state.snapshot(song).channels[1]
  luaunit.assert_equals(#midi_note_on_events,0)
  luaunit.assert_nil(runtime.consumed)
  luaunit.assert_equals(runtime.consumed_count,0)
end

function test_harmony_playback_reachable_delayed_arp_commits_only_at_actual_onset()
  local song=setup();source(song,1,{[1]=0},{1})
  local channel=song.channels[1];channel.chord_one_mask=2
  channel.voicing=harmony_config.new_channel("revoice")
  channel.trig_lock_params[1]={id="chord_arp",param_id="chord_arp_1"}
  channel.trig_lock_params[2]={id="chord_strum_pattern",param_id="chord_strum_pattern_1"}
  program.add_step_param_trig_lock(1,1,4)
  program.add_step_param_trig_lock(1,2,2)
  song.patterns[1].lengths[1]=2
  assign(song,1,1);step.handle(1,1)
  local runtime=harmony_runtime_state.snapshot(song).channels[1]
  luaunit.assert_equals(#midi_note_on_events,0)
  luaunit.assert_nil(runtime.consumed)
  luaunit.assert_equals(runtime.consumed_count,0)
  progress(4)
  runtime=harmony_runtime_state.snapshot(song).channels[1]
  luaunit.assert_true(#midi_note_on_events>0)
  luaunit.assert_not_nil(runtime.consumed)
  luaunit.assert_equals(runtime.consumed_count,1)
end

function test_harmony_inspection_keeps_authored_source_distinct_from_note_mask_merge_pitch()
  local song=setup();source(song,1,{[1]=0},{1});source(song,2,{[2]=3},{2})
  local channel=song.channels[1]
  fn.add_to_set(channel.selected_patterns,1);fn.add_to_set(channel.selected_patterns,2)
  channel.trig_merge_mode="skip";channel.step_note_masks[2]=60
  channel.musical_merge=merge_config.new();channel.musical_merge.mode="foundation"
  channel.musical_merge.anchor=1;channel.musical_merge.target={kind="degrees",degrees={1}}
  pattern_model.update_working_pattern(1,song);step.handle(1,2)
  local shown=harmony_inspection.snapshot(song,1)
  luaunit.assert_equals(shown.planned.source,3)
  luaunit.assert_not_equals(shown.planned.merge,shown.planned.source)
  luaunit.assert_equals(shown.planned.bypass,"note_mask")
end

function test_harmony_playback_pattern_reuses_mapped_identity_and_leaves_raw_exact()
  local song = setup()
  source(song, 1, {[1]=0,[2]=7}, {1,2})
  local channel = song.channels[1]
  channel.voicing = harmony_config.new_channel("pattern")
  channel.voicing.roles.v1 = exact_role(48)
  assign(song, 1, 1)
  local binding = pattern_harmony.binding_key(channel)
  channel.voicing.pattern_maps[binding] = {schema_version=1,revision=1,
    assignments={["0"]="bass"}}

  step.handle(1, 1)
  step.handle(1, 2)
  luaunit.assert_equals({midi_note_on_events[1][1],midi_note_on_events[2][1]}, {48,72})
  luaunit.assert_equals({song.patterns[1].note_values[1],song.patterns[1].note_values[2]}, {0,7})
end

function test_harmony_playback_ensemble_replaces_each_member_with_explicit_role()
  local song = setup()
  source(song, 1, {[1]=3}, {1})
  source(song, 2, {[1]=6}, {1})
  assign(song, 1, 1)
  assign(song, 2, 2)
  local group = harmony_config.new_group(1)
  group.enabled = true
  group.template = {offsets={0,4},required={true,true}}
  group.members = {{role="bass",channel=1},{role="top",channel=2}}
  group.roles = {bass=exact_role(48),top=exact_role(55)}
  song.voicing = {schema_version=1,groups={[1]=group}}
  song.channels[1].voicing = harmony_config.new_channel("ensemble")
  song.channels[1].voicing.group_id = 1
  song.channels[2].voicing = harmony_config.new_channel("ensemble")
  song.channels[2].voicing.group_id = 1

  step.handle(1, 1)
  step.handle(2, 1)
  luaunit.assert_equals({midi_note_on_events[1][1],midi_note_on_events[2][1]}, {48,55})
end

function test_harmony_playback_ensemble_local_octave_is_visible_bypass_with_legacy_pitch()
  local song=setup();source(song,1,{[1]=0},{1});assign(song,1,1)
  local group=harmony_config.new_group(1);group.enabled=true
  group.members={{role="bass",channel=1}};group.roles={bass=exact_role(48)}
  song.voicing={schema_version=1,groups={[1]=group}}
  local channel=song.channels[1];channel.voicing=harmony_config.new_channel("ensemble")
  channel.voicing.group_id=1
  program.add_step_octave_trig_lock(1,1)

  step.handle(1,1)
  luaunit.assert_equals(midi_note_on_events[1][1],72)
  local shown=harmony_inspection.snapshot(song,1,1)
  luaunit.assert_equals(shown.planned.status,"local_octave")
  luaunit.assert_equals(shown.planned.bypass,"local_octave")
  luaunit.assert_equals(shown.planned.output,72)
  luaunit.assert_equals(shown.emitted.pitch,72)
end

function test_harmony_playback_explicit_group_scale_does_not_treat_global_inheritance_as_local_override()
  local song=setup();source(song,1,{[1]=0},{1});assign(song,1,1)
  local base=quantiser.get_scales()[1]
  program.set_scale(2,{number=1,scale=base.scale,pentatonic_scale=base.pentatonic_scale,
    chord=1,root_note=2,transpose=0,chord_degree_rotation=0,version=1})
  local group=harmony_config.new_group(1);group.enabled=true;group.source={kind="scale_slot",scale_slot=2}
  group.roles.bass=exact_role(50);song.voicing={schema_version=1,groups={[1]=group}}
  song.channels[1].voicing=harmony_config.new_channel("ensemble");song.channels[1].voicing.group_id=1
  step.handle(1,1)
  luaunit.assert_equals(midi_note_on_events[1][1],50)
end

function test_harmony_playback_missing_ensemble_group_obeys_explicit_fallback()
  local song=setup();source(song,1,{[1]=0},{1});assign(song,1,1)
  local channel=song.channels[1];channel.voicing=harmony_config.new_channel("ensemble");channel.voicing.group_id=1
  song.voicing={schema_version=1,groups={}}
  luaunit.assert_equals(harmony_config_state.effective_channel(song,1,channel.voicing).mode,"ensemble")
  local pitches={};for _,event in ipairs(midi_note_on_events)do pitches[#pitches+1]=event[1]end
  luaunit.assert_equals(pitches,{})
  step.handle(1,1);luaunit.assert_equals(#midi_note_on_events,0)

  channel.voicing.fallback="legacy"
  harmony_config_state.reset_song(song)
  step.handle(1,1);luaunit.assert_equals(midi_note_on_events[1][1],60)
end

function test_musical_merge_structural_target_changes_only_foundation_addition()
  local song = setup()
  source(song, 1, {[1]=0}, {1})
  source(song, 2, {[2]=3}, {2})
  local channel = song.channels[1]
  fn.add_to_set(channel.selected_patterns, 1)
  fn.add_to_set(channel.selected_patterns, 2)
  channel.trig_merge_mode = "skip"
  channel.musical_merge = merge_config.new()
  channel.musical_merge.mode = "foundation"
  channel.musical_merge.anchor = 1
  channel.musical_merge.target = {kind="degrees",degrees={1}}
  pattern_model.update_working_pattern(1, song)

  step.handle(1, 1)
  step.handle(1, 2)
  luaunit.assert_equals({midi_note_on_events[1][1],midi_note_on_events[2][1]}, {60,60})
  luaunit.assert_equals(song.patterns[2].note_values[2], 3)
end


function test_harmony_failed_revoice_arp_is_strictly_silent()
  local song=setup();source(song,1,{[1]=0},{1});local channel=song.channels[1]
  channel.chord_one_mask=2;channel.voicing=harmony_config.new_channel("revoice")
  channel.voicing.roles.v1=exact_role(49);channel.voicing.roles.v2=exact_role(53)
  channel.trig_lock_params[1]={id="chord_arp",param_id="chord_arp_1"}
  program.add_step_param_trig_lock(1,1,4);assign(song,1,1)
  luaunit.assert_equals(harmony_config_state.effective_channel(song,1,channel.voicing).mode,"revoice")
  step.handle(1,1);progress(3)
  luaunit.assert_equals(harmony_runtime_state.snapshot(song).channels[1].prepared.status,"no_solution")
  local pitches={};for _,event in ipairs(midi_note_on_events)do pitches[#pitches+1]=event[1]end
  luaunit.assert_equals(pitches,{})
  luaunit.assert_nil(harmony_runtime_state.snapshot(song).channels[1].consumed)
end

function test_harmony_pattern_source_edit_invalidates_prepared_frame()
  local song=setup();source(song,1,{[1]=0},{1});local channel=song.channels[1]
  channel.voicing=harmony_config.new_channel("pattern");channel.voicing.roles.v1=exact_role(48)
  assign(song,1,1);local binding=pattern_harmony.binding_key(channel)
  channel.voicing.pattern_maps[binding]={schema_version=1,revision=1,assignments={["0"]="bass",["1"]="bass"}}
  step.handle(1,1);luaunit.assert_equals(midi_note_on_events[1][1],48)
  song.patterns[1].note_values[1]=1;pattern_model.update_working_pattern(1,song)
  luaunit.assert_equals(channel.working_pattern.note_values[1],1)
  luaunit.assert_equals(pattern_harmony.binding_key(channel),binding)
  step.handle(1,1)
  luaunit.assert_equals(#midi_note_on_events,1)
  local inspection=harmony_inspection.snapshot(song,1)
  luaunit.assert_equals(inspection.planned.status,"alias_conflict")
  luaunit.assert_nil(inspection.planned.bypass)

  channel.voicing.fallback="legacy";harmony_config_state.reset_song(song)
  step.handle(1,1);inspection=harmony_inspection.snapshot(song,1)
  luaunit.assert_equals(#midi_note_on_events,2)
  luaunit.assert_equals(inspection.planned.status,"alias_conflict")
  luaunit.assert_equals(inspection.planned.fallback,"legacy")
  luaunit.assert_nil(inspection.planned.bypass)
end

function test_harmony_pattern_runtime_alias_conflict_preserves_history_and_recovers_without_edit()
  local song=setup();source(song,1,{[1]=0},{1});local channel=song.channels[1]
  channel.voicing=harmony_config.new_channel("pattern");channel.voicing.roles.v1=exact_role(48)
  assign(song,1,1);local binding=pattern_harmony.binding_key(channel)
  channel.voicing.pattern_maps[binding]={schema_version=1,revision=1,
    assignments={["0"]="bass",["1"]="bass"}}
  step.handle(1,1)
  local valid=harmony_runtime_state.snapshot(song).channels[1].consumed
  luaunit.assert_equals(midi_note_on_events[1][1],48)

  song.patterns[1].note_values[1]=1;pattern_model.update_working_pattern(1,song)
  step.handle(1,1)
  luaunit.assert_equals(#midi_note_on_events,1)
  luaunit.assert_equals(harmony_inspection.snapshot(song,1,1).planned.status,"alias_conflict")
  luaunit.assert_equals(harmony_runtime_state.snapshot(song).channels[1].consumed,valid)

  song.patterns[1].note_values[1]=0;pattern_model.update_working_pattern(1,song)
  step.handle(1,1)
  luaunit.assert_equals(midi_note_on_events[2][1],48)
  luaunit.assert_equals(harmony_inspection.snapshot(song,1,1).planned.status,"ok")
  luaunit.assert_not_nil(harmony_runtime_state.snapshot(song).channels[1].consumed)
end

function test_harmony_ensemble_absolute_mask_is_visible_legacy_bypass()
  local song=setup();source(song,1,{[1]=0},{1})
  local group=harmony_config.new_group(1);group.enabled=true;group.roles.bass=exact_role(48)
  song.voicing={schema_version=1,groups={[1]=group}}
  local channel=song.channels[1];channel.voicing=harmony_config.new_channel("ensemble");channel.voicing.group_id=1
  channel.step_note_masks[1]=60;assign(song,1,1)
  step.handle(1,1)
  luaunit.assert_equals(midi_note_on_events[1][1],60)
  luaunit.assert_equals(harmony_inspection.snapshot(song,1).planned.bypass,"note_mask")
  luaunit.assert_nil(harmony_runtime_state.snapshot(song).groups[1])
end

function test_pattern_harmony_uses_post_foundation_structural_pitch_once()
  local song=setup();source(song,1,{[1]=0},{1});source(song,2,{[2]=3},{2})
  local channel=song.channels[1];fn.add_to_set(channel.selected_patterns,1);fn.add_to_set(channel.selected_patterns,2)
  channel.trig_merge_mode="skip";channel.musical_merge=merge_config.new();channel.musical_merge.mode="foundation"
  channel.musical_merge.anchor=1;channel.musical_merge.target={kind="degrees",degrees={1}}
  channel.voicing=harmony_config.new_channel("pattern");channel.voicing.roles.v1=exact_role(60)
  pattern_model.update_working_pattern(1,song);local binding=pattern_harmony.binding_key(channel)
  channel.voicing.pattern_maps[binding]={schema_version=1,revision=1,assignments={["3"]="bass"}}
  step.handle(1,2)
  luaunit.assert_equals(midi_note_on_events[1][1],60)
end
