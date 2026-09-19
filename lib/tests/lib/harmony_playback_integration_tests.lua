-- README.md Voice leading / Musical Merge: opt-in placement changes final MIDI
-- pitch while preserving the ordinary scheduler, rhythm, velocity and source data.

local step = include("mosaic/lib/step")
local pattern_model = include("mosaic/lib/pattern")
local harmony_config = include("mosaic/lib/harmony/config")
local pattern_harmony = include("mosaic/lib/harmony/pattern")
local merge_config = include("mosaic/lib/musical_merge/config")

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
