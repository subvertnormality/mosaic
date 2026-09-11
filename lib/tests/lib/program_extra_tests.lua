-- program model: store and song-pattern defaults, getters/setters, step trig/octave/scale/
-- transpose locks, slides, masks, working-pattern updates and copies that must not alias.
-- Globals replaced here (memory, params values) are restored by with_* even on failure.
local musicutil = require("musicutil")
local quantiser = include("mosaic/lib/quantiser")

local function with_params(values, body)
  local saved = {}
  for id, value in pairs(values) do
    saved[id] = params:get(id)
    params:set(id, value)
  end
  local ok, err = pcall(body)
  for id in pairs(values) do params:set(id, saved[id]) end
  if not ok then error(err, 0) end
end

local function with_memory(replacement, body)
  local saved = memory
  memory = replacement
  local ok, err = pcall(body)
  memory = saved
  if not ok then error(err, 0) end
end

local function truthy(value)
  return not not value
end

local function filled(value)
  local t = {}
  for i = 1, 64 do t[i] = value end
  return t
end

local function default_channel(i)
  return {
    number = i,
    trig_lock_params = {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}},
    trig_lock_calculator_ids = {},
    step_trig_lock_banks = {},
    trig_lock_slides = {false, false, false, false, false, false, false, false, false, false},
    step_trig_lock_slides = {},
    step_octave_trig_lock_banks = {},
    step_scale_trig_lock_banks = {},
    step_trig_masks = {},
    step_note_masks = {},
    step_velocity_masks = {},
    step_length_masks = {},
    step_micro_time_masks = {},
    step_chord_masks = {},
    -- characterisation: the working pattern's note_mask_values starts empty, unlike a
    -- stored pattern's table of -1.
    working_pattern = {trig_values = filled(0), lengths = filled(1), note_values = filled(0),
      velocity_values = filled(100), note_mask_values = {}},
    start_trig = {1, 4},
    end_trig = {16, 7},
    selected_patterns = {},
    default_scale = 1,
    step_scale_number = 1,
    root_note = 0,
    chord = 1,
    trig_merge_mode = "skip",
    note_merge_mode = "average",
    velocity_merge_mode = "average",
    length_merge_mode = "average",
    octave = 0,
    clock_mods = {name = "/1", value = 1, type = "clock_division"},
    current_step = 1,
    mute = false
  }
end

local function default_pattern()
  return {trig_values = filled(0), lengths = filled(1), note_values = filled(0),
    note_mask_values = filled(-1), velocity_values = filled(100)}
end

-- characterisation (defaults below are the model's, not README statements)
function test_program_extra_init_store_defaults()
  program.init()
  local devices = {}
  for i = 1, 16 do devices[i] = {midi_channel = 1, midi_device = 1, device_map = "none"} end
  luaunit.assert_equals(program.get(), {
    nrpn_policy_version = 1,
    nrpn_stored_modes = {},
    selected_page = pages.pages.channel_edit_page,
    selected_song_pattern = 1,
    selected_pattern = 1,
    selected_channel = 1,
    selected_scale = 1,
    root_note = 0,
    chord = 1,
    default_scale = 1,
    current_step = 1,
    current_channel_step = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1},
    song_patterns = {},
    global_step_accumulator = 0,
    devices = devices,
    blink_state = false,
    memory = {channels = {}, current_indices = {}, original_states = {}, pattern_states = {}}
  })
  luaunit.assert_false(rawequal(program.get().devices[1], program.get().devices[2]))
end

function test_program_extra_song_pattern_defaults_are_created_lazily()
  program.init()
  luaunit.assert_nil(program.get().song_patterns[4])
  local song_pattern = program.get_song_pattern(4)
  luaunit.assert_true(rawequal(program.get().song_patterns[4], song_pattern))
  luaunit.assert_true(rawequal(program.get_song_pattern(4), song_pattern))
  luaunit.assert_equals(song_pattern.active, false)
  luaunit.assert_equals(song_pattern.global_pattern_length, 64)
  luaunit.assert_equals(song_pattern.scale, 0)
  luaunit.assert_equals(song_pattern.repeats, 1)
  luaunit.assert_nil(song_pattern.transpose)
  local c_major = quantiser.get_scale(1)
  local scales = {}
  for i = 1, 16 do
    scales[i] = {number = 1, scale = c_major.scale, pentatonic_scale = c_major.pentatonic_scale,
      root_note = 0, chord = 1, chord_degree_rotation = 0, version = 1}
  end
  luaunit.assert_equals(song_pattern.scales, scales)
  local patterns = {}
  for i = 1, 16 do patterns[i] = default_pattern() end
  luaunit.assert_equals(song_pattern.patterns, patterns)
  local channels = {}
  for i = 1, 17 do channels[i] = default_channel(i) end
  luaunit.assert_equals(song_pattern.channels, channels)
end

function test_program_extra_song_pattern_defaults_do_not_alias()
  program.init()
  local a, b = program.get_song_pattern(1), program.get_song_pattern(2)
  luaunit.assert_false(rawequal(a, b))
  luaunit.assert_false(rawequal(a.channels[1], b.channels[1]))
  luaunit.assert_false(rawequal(a.channels[1], a.channels[2]))
  luaunit.assert_false(rawequal(a.patterns[1], a.patterns[2]))
  luaunit.assert_false(rawequal(a.scales[1], a.scales[2]))
  a.channels[1].working_pattern.trig_values[1] = 1
  a.channels[1].trig_lock_params[1].id = "x"
  a.patterns[1].trig_values[1] = 1
  a.scales[1].root_note = 5
  luaunit.assert_equals(a.channels[2].working_pattern.trig_values[1], 0)
  luaunit.assert_equals(b.channels[1].working_pattern.trig_values[1], 0)
  luaunit.assert_nil(a.channels[2].trig_lock_params[1].id)
  luaunit.assert_equals(a.patterns[2].trig_values[1], 0)
  luaunit.assert_equals(b.patterns[1].trig_values[1], 0)
  luaunit.assert_equals(a.scales[2].root_note, 0)
  luaunit.assert_equals(b.scales[1].root_note, 0)
end

function test_program_extra_initialise_default_pattern_is_fresh_each_call()
  local p1, p2 = program.initialise_default_pattern(), program.initialise_default_pattern()
  luaunit.assert_equals(p1, default_pattern())
  p1.trig_values[3] = 1
  luaunit.assert_equals(p2.trig_values[3], 0)
  luaunit.assert_equals(program.initialise_64_table(7), filled(7))
end

function test_program_extra_selected_song_pattern_defaults_to_one()
  program.init()
  program.get().selected_song_pattern = nil
  local song_pattern = program.get_selected_song_pattern()
  luaunit.assert_equals(program.get().selected_song_pattern, 1)
  luaunit.assert_true(rawequal(song_pattern, program.get_song_pattern(1)))
  program.set_selected_song_pattern(6)
  luaunit.assert_equals(program.get().selected_song_pattern, 6)
  luaunit.assert_true(rawequal(program.get_selected_song_pattern(), program.get_song_pattern(6)))
  luaunit.assert_false(rawequal(program.get_selected_song_pattern(), program.get_song_pattern(1)))
end

function test_program_extra_selected_page_round_trips()
  program.init()
  luaunit.assert_equals(program.get_selected_page(), pages.pages.channel_edit_page)
  program.set_selected_page(pages.pages.song_edit_page)
  luaunit.assert_equals(program.get_selected_page(), pages.pages.song_edit_page)
  luaunit.assert_equals(program.get().selected_page, pages.pages.song_edit_page)
end

function test_program_extra_is_song_pattern_active()
  program.init()
  luaunit.assert_equals(program.is_song_pattern_active(7), false)
  luaunit.assert_nil(program.get().song_patterns[7]) -- asking does not create it
  program.get_song_pattern(7)
  luaunit.assert_equals(program.is_song_pattern_active(7), false)
  program.get_song_pattern(7).active = true
  luaunit.assert_equals(program.is_song_pattern_active(7), true)
  luaunit.assert_equals(program.is_song_pattern_active(8), false)
end

function test_program_extra_set_song_pattern_copies_source_into_destination()
  program.init()
  local source = program.get_song_pattern(2)
  source.active = true
  source.channels[3].step_note_masks[9] = 61
  source.channels[3].step_chord_masks[9] = {2, nil, -1}
  source.channels[3].working_pattern.trig_values[9] = 1
  program.set_song_pattern(2, 5)
  local copy = program.get().song_patterns[5]
  luaunit.assert_false(rawequal(copy, source))
  luaunit.assert_equals(copy, source)
  -- later edits on either side do not leak
  source.channels[3].step_note_masks[9] = 70
  source.channels[3].step_chord_masks[9][1] = 5
  copy.channels[3].working_pattern.trig_values[9] = 0
  luaunit.assert_equals(copy.channels[3].step_note_masks[9], 61)
  luaunit.assert_equals(copy.channels[3].step_chord_masks[9], {2, nil, -1})
  luaunit.assert_equals(source.channels[3].working_pattern.trig_values[9], 1)
  -- copying an absent source creates the default first
  program.set_song_pattern(9, 10)
  luaunit.assert_equals(program.get().song_patterns[10], program.get_song_pattern(9))
  luaunit.assert_false(rawequal(program.get().song_patterns[10], program.get_song_pattern(9)))
end

function test_program_extra_set_migrates_sequencer_patterns()
  local legacy = {x = 1}
  program.set({nrpn_policy_version = 1, sequencer_patterns = {[1] = legacy}})
  luaunit.assert_equals(program.get(), {
    nrpn_policy_version = 1,
    song_patterns = {[1] = {x = 1}},
    memory = {channels = {}, current_indices = {}, original_states = {}, pattern_states = {}}
  })
  luaunit.assert_true(rawequal(program.get().song_patterns[1], legacy))
  -- song_patterns wins when both exist; sequencer_patterns is left in place
  program.set({nrpn_policy_version = 1, sequencer_patterns = {[1] = {a = 1}}, song_patterns = {[2] = {b = 2}}})
  luaunit.assert_equals(program.get().song_patterns, {[2] = {b = 2}})
  luaunit.assert_equals(program.get().sequencer_patterns, {[1] = {a = 1}})
  -- nested sequencer_patterns inside a song pattern are renamed too
  program.set({nrpn_policy_version = 1, song_patterns = {[3] = {sequencer_patterns = {q = 1}}, [4] = {r = 2}}})
  luaunit.assert_equals(program.get().song_patterns, {[3] = {song_patterns = {q = 1}}, [4] = {r = 2}})
  -- no patterns at all: an empty table and default memory
  program.set({nrpn_policy_version = 1})
  luaunit.assert_equals(program.get(), {nrpn_policy_version = 1, song_patterns = {},
    memory = {channels = {}, current_indices = {}, original_states = {}, pattern_states = {}}})
  -- characterisation: nil gives an empty store; get() then fills song_patterns and memory
  program.set(nil)
  luaunit.assert_equals(program.get(), {song_patterns = {},
    memory = {channels = {}, current_indices = {}, original_states = {}, pattern_states = {}}})
  program.init()
end

function test_program_extra_set_hands_serialized_memory_to_memory()
  local received = {}
  local serialized = {channels = {}, current_indices = {[2] = 3}}
  with_memory({deserialize_state = function(s) received[#received + 1] = s end}, function()
    local existing = {channels = {1}, serialized = serialized}
    program.set({nrpn_policy_version = 1, song_patterns = {}, memory = existing})
    luaunit.assert_equals(#received, 1)
    luaunit.assert_true(rawequal(received[1], serialized))
    luaunit.assert_true(rawequal(program.get().memory, existing))
    -- without serialized state memory is not consulted
    program.set({nrpn_policy_version = 1, song_patterns = {}, memory = {channels = {}}})
    luaunit.assert_equals(#received, 1)
  end)
  program.init()
end

function test_program_extra_prepare_for_save_stores_memory_serialization()
  program.init()
  local calls = 0
  local snapshot = {marker = "snapshot"}
  with_memory({serialize_state = function() calls = calls + 1; return snapshot end}, function()
    local store = program.prepare_for_save()
    luaunit.assert_true(rawequal(store, program.get()))
    luaunit.assert_equals(calls, 1)
    luaunit.assert_true(rawequal(program.get().memory.serialized, snapshot))
  end)
  -- whatever memory returns is stored as is
  with_memory({serialize_state = function() return nil end}, function()
    program.prepare_for_save()
    luaunit.assert_nil(program.get().memory.serialized)
  end)
end

function test_program_extra_get_restores_missing_containers()
  program.init()
  program.get().song_patterns = nil
  program.get().memory = nil
  luaunit.assert_equals(program.get().song_patterns, {})
  luaunit.assert_equals(program.get().memory,
    {channels = {}, current_indices = {}, original_states = {}, pattern_states = {}})
  -- characterisation: get_memory alone creates a bare table
  program.get().memory = nil
  local created = program.get_memory()
  luaunit.assert_equals(created, {})
  luaunit.assert_true(rawequal(program.get_memory(), created))
end

function test_program_extra_param_trig_lock_requires_a_parameter()
  program.init()
  local channel = program.get_channel(1, 1)
  program.add_step_param_trig_lock_to_channel(channel, 4, nil, 50)
  luaunit.assert_equals(channel.step_trig_lock_banks, {})
  luaunit.assert_equals(program.step_has_param_trig_lock(channel, 4), false)
  channel.trig_lock_params[2] = {cc_min_value = 0, cc_max_value = 127}
  program.add_step_param_trig_lock_to_channel(channel, 4, 2, 50)
  luaunit.assert_equals(channel.step_trig_lock_banks, {[4] = {[2] = 50}})
  luaunit.assert_equals(program.step_has_param_trig_lock(channel, 4), true)
  luaunit.assert_nil(program.get_step_param_trig_lock(channel, 4, 1))
  luaunit.assert_nil(program.get_step_param_trig_lock(channel, 5, 2))
  -- characterisation (suspected defect: `~= {}` compares against a new table, so an
  -- emptied step bank still reports a parameter lock; program.lua:332).
  channel.step_trig_lock_banks[6] = {}
  luaunit.assert_equals(program.step_has_param_trig_lock(channel, 6), true)
end

function test_program_extra_add_step_param_trig_lock_uses_selected_channel()
  program.init()
  program.get().selected_channel = 3
  local channel = program.get_channel(1, 3)
  channel.trig_lock_params[1] = {cc_min_value = 10, cc_max_value = 20}
  program.add_step_param_trig_lock(8, 1, 99)
  luaunit.assert_equals(channel.step_trig_lock_banks, {[8] = {[1] = 20}})
  luaunit.assert_equals(program.get_channel(1, 1).step_trig_lock_banks, {})
end

function test_program_extra_octave_trig_lock_clamps_to_two_octaves()
  program.init()
  program.get().selected_channel = 2
  local channel = program.get_channel(1, 2)
  for _, case in ipairs({{5, 2}, {2, 2}, {1, 1}, {0, 0}, {-2, -2}, {-7, -2}}) do
    program.add_step_octave_trig_lock(3, case[1])
    luaunit.assert_equals(program.get_step_octave_trig_lock(channel, 3), case[2])
    luaunit.assert_equals(channel.step_octave_trig_lock_banks[3], case[2])
    luaunit.assert_equals(truthy(program.step_octave_has_trig_lock(channel, 3)), case[2] ~= 0)
  end
  program.add_step_octave_trig_lock(3, nil)
  luaunit.assert_nil(program.get_step_octave_trig_lock(channel, 3))
  luaunit.assert_equals(truthy(program.step_octave_has_trig_lock(channel, 3)), false)
  luaunit.assert_equals(program.get_channel(1, 1).step_octave_trig_lock_banks, {})
  channel.step_octave_trig_lock_banks = nil
  luaunit.assert_nil(program.get_step_octave_trig_lock(channel, 3))
  luaunit.assert_equals(truthy(program.step_octave_has_trig_lock(channel, 3)), false)
end

function test_program_extra_scale_trig_lock_clamps_to_sixteen_scales()
  program.init()
  program.get().selected_channel = 4
  local channel = program.get_channel(1, 4)
  for _, case in ipairs({{0, 1}, {1, 1}, {9, 9}, {16, 16}, {40, 16}}) do
    program.add_step_scale_trig_lock(12, case[1])
    luaunit.assert_equals(program.get_step_scale_trig_lock(channel, 12), case[2])
    luaunit.assert_equals(program.step_scale_has_trig_lock(channel, 12), case[2])
  end
  program.add_step_scale_trig_lock(12, nil)
  luaunit.assert_nil(program.get_step_scale_trig_lock(channel, 12))
  luaunit.assert_nil(program.step_scale_has_trig_lock(channel, 12))
  channel.step_scale_trig_lock_banks = nil
  luaunit.assert_nil(program.get_step_scale_trig_lock(channel, 12))
  luaunit.assert_nil(program.step_scale_has_trig_lock(channel, 12))
end

function test_program_extra_transpose_trig_lock_lives_on_channel_seventeen()
  program.init()
  program.get().selected_song_pattern = 2
  local scale_channel = program.get_channel(2, 17)
  luaunit.assert_nil(scale_channel.step_transpose_trig_lock_banks)
  luaunit.assert_nil(program.get_step_transpose_trig_lock(5))
  for _, case in ipairs({{20, 12}, {12, 12}, {3, 3}, {-12, -12}, {-30, -12}}) do
    program.add_step_transpose_trig_lock(5, case[1])
    luaunit.assert_equals(program.get_step_transpose_trig_lock(5), case[2])
  end
  luaunit.assert_equals(scale_channel.step_transpose_trig_lock_banks, {[5] = -12})
  luaunit.assert_nil(program.get_channel(1, 17).step_transpose_trig_lock_banks)
  -- only reported as a trig lock while channel 17 is selected
  program.get().selected_channel = 1
  luaunit.assert_equals(program.step_transpose_has_trig_lock(5), false)
  program.get().selected_channel = 16
  luaunit.assert_equals(program.step_transpose_has_trig_lock(5), false)
  program.get().selected_channel = 17
  luaunit.assert_equals(program.step_transpose_has_trig_lock(5), -12)
  luaunit.assert_nil(program.step_transpose_has_trig_lock(6))
  program.add_step_transpose_trig_lock(5, nil)
  luaunit.assert_nil(program.get_step_transpose_trig_lock(5))
end

function test_program_extra_song_and_scale_transpose()
  program.init()
  luaunit.assert_equals(program.get_transpose(), 0)
  program.set_transpose(-5)
  luaunit.assert_equals(program.get_transpose(), -5)
  luaunit.assert_equals(program.get_selected_song_pattern().transpose, -5)
  program.set_selected_song_pattern(2)
  luaunit.assert_equals(program.get_transpose(), 0)
  program.set_transpose(nil)
  luaunit.assert_equals(program.get_selected_song_pattern().transpose, 0)
  program.set_scale_transpose(3, 7)
  luaunit.assert_equals(program.get_song_pattern(2).scales[3].transpose, 7)
  luaunit.assert_nil(program.get_song_pattern(2).scales[4].transpose)
  luaunit.assert_nil(program.get_song_pattern(1).scales[3].transpose)
  -- characterisation: scale 0 is rebuilt on every call, so its transpose is not kept
  program.set_scale_transpose(0, 7)
  luaunit.assert_nil(program.get_scale(0).transpose)
end

function test_program_extra_channel_param_slides()
  program.init()
  local channel = program.get_channel(1, 1)
  luaunit.assert_equals(program.get_channel_param_slide(channel, 4), false)
  program.toggle_channel_param_slide(channel, 4)
  luaunit.assert_equals(program.get_channel_param_slide(channel, 4), true)
  program.toggle_channel_param_slide(channel, 4)
  luaunit.assert_equals(program.get_channel_param_slide(channel, 4), false)
  program.set_channel_param_slide(channel, 9, true)
  luaunit.assert_equals(channel.trig_lock_slides,
    {false, false, false, false, false, false, false, false, true, false})
  -- a channel without the table gets one
  local bare = {}
  luaunit.assert_nil(program.get_channel_param_slide(bare, 2))
  luaunit.assert_equals(bare.trig_lock_slides, {})
  local bare2 = {}
  program.toggle_channel_param_slide(bare2, 2)
  luaunit.assert_equals(bare2.trig_lock_slides, {[2] = true})
end

function test_program_extra_step_param_slides()
  program.init()
  local channel = program.get_channel(1, 2)
  luaunit.assert_nil(program.get_step_param_slide(channel, 3, 1))
  luaunit.assert_equals(program.step_has_param_slide(channel, 3), false)
  program.toggle_step_param_slide(channel, 3, 1)
  program.toggle_step_param_slide(channel, 3, 10)
  luaunit.assert_equals(channel.step_trig_lock_slides, {[3] = {[1] = true, [10] = true}})
  luaunit.assert_equals(program.get_step_param_slide(channel, 3, 1), true)
  luaunit.assert_equals(program.step_has_param_slide(channel, 3), true)
  program.toggle_step_param_slide(channel, 3, 1)
  -- characterisation: toggling off leaves false in place, not nil
  luaunit.assert_equals(channel.step_trig_lock_slides, {[3] = {[1] = false, [10] = true}})
  luaunit.assert_equals(program.step_has_param_slide(channel, 3), true) -- slot 10 alone counts
  program.clear_step_param_slide(channel, 3, 10)
  luaunit.assert_equals(channel.step_trig_lock_slides, {[3] = {[1] = false}})
  luaunit.assert_equals(program.step_has_param_slide(channel, 3), false)
  program.clear_step_param_slide(channel, 3, 1)
  luaunit.assert_equals(channel.step_trig_lock_slides, {})
  -- only slots 1..10 count
  channel.step_trig_lock_slides[4] = {[11] = true}
  luaunit.assert_equals(program.step_has_param_slide(channel, 4), false)
  -- channels without the table
  local bare = {}
  luaunit.assert_equals(program.step_has_param_slide(bare, 1), false)
  luaunit.assert_nil(program.get_step_param_slide(bare, 1, 1))
  luaunit.assert_equals(bare.step_trig_lock_slides, {})
  local bare2 = {}
  program.toggle_step_param_slide(bare2, 7, 2)
  luaunit.assert_equals(bare2.step_trig_lock_slides, {[7] = {[2] = true}})
end

function test_program_extra_step_mask_queries_read_selected_channel()
  program.init()
  program.get().selected_channel = 5
  local channel = program.get_channel(1, 5)
  local queries = {
    {program.step_has_trig_mask, "step_trig_masks", 1},
    {program.step_has_note_mask, "step_note_masks", 64},
    {program.step_has_velocity_mask, "step_velocity_masks", 20},
    {program.step_has_length_mask, "step_length_masks", 4},
    {program.step_has_micro_time_mask, "step_micro_time_masks", -3},
  }
  for _, q in ipairs(queries) do
    luaunit.assert_nil(q[1](9))
    channel[q[2]][9] = q[3]
    luaunit.assert_equals(q[1](9), q[3])
    luaunit.assert_nil(q[1](10))
    program.get_channel(1, 1)[q[2]][10] = q[3]
    luaunit.assert_nil(q[1](10))
    channel[q[2]] = nil
    luaunit.assert_nil(q[1](9))
  end
  local chords = {program.step_has_chord_1_mask, program.step_has_chord_2_mask,
    program.step_has_chord_3_mask, program.step_has_chord_4_mask}
  for i, query in ipairs(chords) do
    luaunit.assert_nil(query(9))
  end
  channel.step_chord_masks[9] = {nil, 3, nil, -2}
  luaunit.assert_equals({chords[1](9), chords[2](9), chords[3](9), chords[4](9)}, {nil, 3, nil, -2})
  channel.step_chord_masks[9] = {7, nil, 5}
  luaunit.assert_equals({chords[1](9), chords[2](9), chords[3](9), chords[4](9)}, {7, nil, 5, nil})
  channel.step_chord_masks = nil
  for _, query in ipairs(chords) do luaunit.assert_nil(query(9)) end
end

function test_program_extra_step_has_trig_lock_each_source()
  local sources = {
    function(c) c.step_trig_lock_banks[7] = {[1] = 3} end,
    function(c) c.step_octave_trig_lock_banks[7] = 1 end,
    function(c) c.step_scale_trig_lock_banks[7] = 2 end,
    function(c) c.step_trig_masks[7] = 0 end,
    function(c) c.step_note_masks[7] = 60 end,
    function(c) c.step_velocity_masks[7] = 90 end,
    function(c) c.step_length_masks[7] = 2 end,
    function(c) c.step_micro_time_masks[7] = 1 end,
    function(c) c.step_chord_masks[7] = {1} end,
    function(c) c.step_chord_masks[7] = {nil, 1} end,
    function(c) c.step_chord_masks[7] = {nil, nil, 1} end,
    function(c) c.step_chord_masks[7] = {nil, nil, nil, 1} end,
    function(c) c.step_trig_lock_slides[7] = {[4] = true} end,
  }
  for i, apply in ipairs(sources) do
    program.init()
    local channel = program.get_channel(1, 1)
    luaunit.assert_equals(program.step_has_trig_lock(channel, 7), false)
    apply(channel)
    luaunit.assert_equals(truthy(program.step_has_trig_lock(channel, 7)), true, "source " .. i)
    luaunit.assert_equals(program.step_has_trig_lock(channel, 8), false, "source " .. i)
  end
  -- an octave lock of 0 is not a lock
  program.init()
  local channel = program.get_channel(1, 1)
  channel.step_octave_trig_lock_banks[7] = 0
  luaunit.assert_equals(program.step_has_trig_lock(channel, 7), false)
  -- transpose counts only when channel 17 is selected
  program.add_step_transpose_trig_lock(7, 2)
  luaunit.assert_equals(program.step_has_trig_lock(channel, 7), false)
  program.get().selected_channel = 17
  luaunit.assert_equals(truthy(program.step_has_trig_lock(program.get_channel(1, 17), 7)), true)
end

function test_program_extra_step_has_trig_lock_mixes_selected_channel_masks()
  -- characterisation (suspected defect: step_has_trig_lock takes a channel but reads masks
  -- from the selected channel; program.lua:354-362). No production caller today.
  program.init()
  program.get().selected_channel = 1
  program.get_channel(1, 1).step_note_masks[7] = 60
  luaunit.assert_equals(truthy(program.step_has_trig_lock(program.get_channel(1, 2), 7)), true)
end

function test_program_extra_trig_lock_calculator_ids()
  program.init()
  local channel = program.get_channel(1, 1)
  -- characterisation: an existing table reports nil for an unseen parameter...
  luaunit.assert_nil(program.get_trig_lock_calculator_id(channel, 3))
  program.increment_trig_lock_calculator_id(channel, 3)
  program.increment_trig_lock_calculator_id(channel, 3)
  program.increment_trig_lock_calculator_id(channel, 4)
  luaunit.assert_equals(program.get_trig_lock_calculator_id(channel, 3), 2)
  luaunit.assert_equals(program.get_trig_lock_calculator_id(channel, 4), 1)
  -- ...while a missing table is created with that parameter at 0
  local bare = {}
  luaunit.assert_equals(program.get_trig_lock_calculator_id(bare, 5), 0)
  luaunit.assert_equals(bare.trig_lock_calculator_ids, {[5] = 0})
  local bare2 = {}
  program.increment_trig_lock_calculator_id(bare2, 6)
  luaunit.assert_equals(bare2.trig_lock_calculator_ids, {[6] = 1})
end

local function seed_locks(channel, step)
  channel.step_trig_lock_banks[step] = {[1] = 10, [2] = 20}
  channel.step_octave_trig_lock_banks[step] = 1
  channel.step_scale_trig_lock_banks[step] = 3
  channel.step_trig_lock_slides[step] = {[1] = true}
end

function test_program_extra_clear_trig_locks_for_step_on_a_track_channel()
  program.init()
  program.get().selected_channel = 2
  local channel = program.get_channel(1, 2)
  seed_locks(channel, 4)
  seed_locks(channel, 5)
  program.add_step_transpose_trig_lock(4, 3)
  program.clear_trig_locks_for_step(4)
  luaunit.assert_nil(channel.step_trig_lock_banks[4])
  luaunit.assert_nil(channel.step_octave_trig_lock_banks[4])
  luaunit.assert_nil(channel.step_scale_trig_lock_banks[4])
  luaunit.assert_nil(channel.step_trig_lock_slides[4])
  luaunit.assert_equals(channel.step_trig_lock_banks[5], {[1] = 10, [2] = 20})
  luaunit.assert_equals(channel.step_octave_trig_lock_banks[5], 1)
  luaunit.assert_equals(channel.step_scale_trig_lock_banks[5], 3)
  luaunit.assert_equals(channel.step_trig_lock_slides[5], {[1] = true})
  -- the transpose lock belongs to channel 17 and is untouched
  luaunit.assert_equals(program.get_step_transpose_trig_lock(4), 3)
  -- clearing an empty step is harmless
  program.clear_trig_locks_for_step(30)
  luaunit.assert_nil(channel.step_trig_lock_banks[30])
end

function test_program_extra_clear_trig_locks_for_step_on_the_scale_channel()
  program.init()
  program.get().selected_channel = 17
  local channel = program.get_channel(1, 17)
  seed_locks(channel, 4)
  program.add_step_transpose_trig_lock(4, 3)
  program.add_step_transpose_trig_lock(5, 6)
  program.clear_trig_locks_for_step(4)
  luaunit.assert_nil(channel.step_scale_trig_lock_banks[4])
  luaunit.assert_nil(program.get_step_transpose_trig_lock(4))
  luaunit.assert_equals(program.get_step_transpose_trig_lock(5), 6)
  -- characterisation: on channel 17 param, octave and slide locks are left alone
  luaunit.assert_equals(channel.step_trig_lock_banks[4], {[1] = 10, [2] = 20})
  luaunit.assert_equals(channel.step_octave_trig_lock_banks[4], 1)
  luaunit.assert_equals(channel.step_trig_lock_slides[4], {[1] = true})
end

function test_program_extra_clear_one_trig_lock_for_step_for_channel()
  program.init()
  local channel = program.get_channel(1, 3)
  channel.step_trig_lock_banks[6] = {[1] = 10, [2] = 20}
  channel.step_trig_lock_slides[6] = {[1] = true, [2] = true}
  -- clearing one lock clears that parameter's slide while another lock remains on the step
  -- (bugs.json undo-lock-clears-step-slide; formerly S34 characterisation).
  program.clear_trig_lock_for_step_for_channel(channel, 6, 1)
  luaunit.assert_equals(channel.step_trig_lock_banks[6], {[2] = 20})
  luaunit.assert_equals(channel.step_trig_lock_slides[6], {[2] = true})
  program.clear_trig_lock_for_step_for_channel(channel, 6, 2)
  luaunit.assert_nil(channel.step_trig_lock_banks[6])
  luaunit.assert_nil(channel.step_trig_lock_slides[6])
  -- a slide on a step with no lock for its parameter (hold + K3 on a lock-less step) is kept
  -- when another parameter's lock there is cleared
  channel.step_trig_lock_banks[5] = {[2] = 20}
  channel.step_trig_lock_slides[5] = {[1] = true, [2] = true}
  program.clear_trig_lock_for_step_for_channel(channel, 5, 2)
  luaunit.assert_nil(channel.step_trig_lock_banks[5])
  luaunit.assert_equals(channel.step_trig_lock_slides[5], {[1] = true})
  -- clearing an absent lock leaves the parameter's slide alone
  channel.step_trig_lock_banks[11] = {[2] = 20}
  channel.step_trig_lock_slides[11] = {[1] = true}
  program.clear_trig_lock_for_step_for_channel(channel, 11, 1)
  luaunit.assert_equals(channel.step_trig_lock_slides[11], {[1] = true})
  -- the slide table goes when its last entry is cleared
  channel.step_trig_lock_banks[7] = {[3] = 1}
  channel.step_trig_lock_slides[7] = {[3] = true}
  program.clear_trig_lock_for_step_for_channel(channel, 7, 3)
  luaunit.assert_nil(channel.step_trig_lock_banks[7])
  luaunit.assert_nil(channel.step_trig_lock_slides[7])
  -- empty step without slides
  channel.step_trig_lock_banks[8] = {[3] = 1}
  program.clear_trig_lock_for_step_for_channel(channel, 8, 3)
  luaunit.assert_nil(channel.step_trig_lock_banks[8])
  luaunit.assert_nil(channel.step_trig_lock_slides[8])
  -- absent parameter, absent step and missing tables are no-ops
  channel.step_trig_lock_banks[9] = {[1] = 5}
  program.clear_trig_lock_for_step_for_channel(channel, 9, 2)
  program.clear_trig_lock_for_step_for_channel(channel, 10, 1)
  luaunit.assert_equals(channel.step_trig_lock_banks[9], {[1] = 5})
  local bare = {number = 1}
  program.clear_trig_lock_for_step_for_channel(bare, 1, 1)
  luaunit.assert_equals(bare, {number = 1})
  -- channel 17 is never touched
  local scale_channel = program.get_channel(1, 17)
  scale_channel.step_trig_lock_banks[2] = {[1] = 4}
  program.clear_trig_lock_for_step_for_channel(scale_channel, 2, 1)
  luaunit.assert_equals(scale_channel.step_trig_lock_banks[2], {[1] = 4})
end

function test_program_extra_clear_channel_lock_tables()
  program.init()
  local channel = program.get_channel(1, 1)
  seed_locks(channel, 2)
  channel.step_transpose_trig_lock_banks = {[2] = 1}
  channel.step_note_masks[2] = 60
  program.clear_device_trig_locks_for_channel(channel)
  luaunit.assert_equals(channel.step_trig_lock_banks, {})
  luaunit.assert_equals(channel.step_octave_trig_lock_banks, {[2] = 1})
  program.clear_trig_locks_for_channel(channel)
  luaunit.assert_equals(channel.step_octave_trig_lock_banks, {})
  luaunit.assert_equals(channel.step_scale_trig_lock_banks, {})
  luaunit.assert_equals(channel.step_transpose_trig_lock_banks, {})
  -- characterisation: neither clears slides nor masks
  luaunit.assert_equals(channel.step_trig_lock_slides, {[2] = {[1] = true}})
  luaunit.assert_equals(channel.step_note_masks, {[2] = 60})
end

local function seed_masks(channel, step)
  channel.step_trig_masks[step] = 1
  channel.step_note_masks[step] = 60
  channel.step_velocity_masks[step] = 90
  channel.step_length_masks[step] = 2
  channel.step_micro_time_masks[step] = 3
  channel.step_chord_masks[step] = {1, 2, 3, 4}
end

function test_program_extra_clear_masks_for_step_clears_selected_channel_step()
  program.init()
  program.get().selected_channel = 6
  local channel = program.get_channel(1, 6)
  local other = program.get_channel(1, 7)
  seed_masks(channel, 11)
  seed_masks(channel, 12)
  seed_masks(other, 11)
  program.clear_masks_for_step(11)
  luaunit.assert_nil(channel.step_trig_masks[11])
  luaunit.assert_nil(channel.step_note_masks[11])
  luaunit.assert_nil(channel.step_velocity_masks[11])
  luaunit.assert_nil(channel.step_length_masks[11])
  luaunit.assert_nil(channel.step_micro_time_masks[11])
  -- characterisation: the chord table stays, emptied
  luaunit.assert_equals(channel.step_chord_masks[11], {})
  luaunit.assert_equals(channel.step_note_masks[12], 60)
  luaunit.assert_equals(channel.step_chord_masks[12], {1, 2, 3, 4})
  luaunit.assert_equals(other.step_note_masks[11], 60)
  luaunit.assert_equals(other.step_chord_masks[11], {1, 2, 3, 4})
  -- a step with no chord table is fine
  program.clear_masks_for_step(40)
  luaunit.assert_nil(channel.step_chord_masks[40])
end

function test_program_extra_clear_single_masks_by_channel_number()
  program.init()
  program.get().selected_song_pattern = 3
  local channel = program.get_channel(3, 2)
  seed_masks(channel, 5)
  program.clear_step_trig_mask(2, 5)
  luaunit.assert_nil(channel.step_trig_masks[5])
  program.clear_step_note_mask(2, 5)
  luaunit.assert_nil(channel.step_note_masks[5])
  program.clear_step_velocity_mask(2, 5)
  luaunit.assert_nil(channel.step_velocity_masks[5])
  program.clear_step_length_mask(2, 5)
  luaunit.assert_nil(channel.step_length_masks[5])
  program.clear_step_micro_time_mask(2, 5)
  luaunit.assert_nil(channel.step_micro_time_masks[5])
  program.clear_step_chord_2_mask(2, 5)
  luaunit.assert_equals(channel.step_chord_masks[5], {1, nil, 3, 4})
  program.clear_step_chord_4_mask(2, 5)
  luaunit.assert_equals(channel.step_chord_masks[5], {1, nil, 3})
  program.clear_step_chord_1_mask(2, 5)
  program.clear_step_chord_3_mask(2, 5)
  luaunit.assert_equals(channel.step_chord_masks[5], {})
  for _, clear in ipairs({program.clear_step_chord_1_mask, program.clear_step_chord_2_mask,
      program.clear_step_chord_3_mask, program.clear_step_chord_4_mask}) do
    clear(2, 6)
  end
  luaunit.assert_nil(channel.step_chord_masks[6])
  -- song pattern 1 untouched
  luaunit.assert_equals(program.get_channel(1, 2).step_note_masks, {})
end

function test_program_extra_clear_masks_for_channel()
  program.init()
  local channel = program.get_channel(1, 1)
  seed_masks(channel, 5)
  channel.step_trig_lock_banks[5] = {[1] = 2}
  program.clear_masks_for_channel(channel)
  for _, key in ipairs({"step_trig_masks", "step_note_masks", "step_velocity_masks",
      "step_length_masks", "step_micro_time_masks", "step_chord_masks"}) do
    luaunit.assert_equals(channel[key], {}, key)
  end
  luaunit.assert_equals(channel.step_trig_lock_banks, {[5] = {[1] = 2}})
end

function test_program_extra_mask_setters_and_getters()
  program.init()
  program.get().selected_song_pattern = 2
  local channel = program.get_channel(2, 4)
  program.set_step_trig_mask(4, 3, 1)
  luaunit.assert_equals(channel.step_trig_masks, {[3] = 1})
  luaunit.assert_true(rawequal(program.get_step_trig_masks(4), channel.step_trig_masks))
  luaunit.assert_true(rawequal(program.get_step_note_masks(4), channel.step_note_masks))
  luaunit.assert_true(rawequal(program.get_step_velocity_masks(4), channel.step_velocity_masks))
  luaunit.assert_true(rawequal(program.get_step_length_masks(4), channel.step_length_masks))
  -- a missing trig mask table is recreated; characterisation: the others are not
  channel.step_trig_masks = nil
  channel.step_note_masks = nil
  luaunit.assert_equals(program.get_step_trig_masks(4), {})
  luaunit.assert_nil(program.get_step_note_masks(4))
  channel.step_trig_masks = nil
  program.set_step_trig_mask(4, 8, 0)
  luaunit.assert_equals(channel.step_trig_masks, {[8] = 0})
  -- object-taking setters
  local c = program.get_channel(2, 5)
  program.set_step_note_mask(c, 2, 61)
  program.set_step_length_mask(c, 2, 3)
  luaunit.assert_equals(c.step_note_masks, {[2] = 61})
  luaunit.assert_equals(c.step_length_masks, {[2] = 3})
  program.set_trig_mask(c, 1)
  program.set_note_mask(c, 62)
  program.set_velocity_mask(c, 70)
  program.set_length_mask(c, 4)
  program.set_chord_one_mask(c, 1)
  program.set_chord_two_mask(c, 2)
  program.set_chord_three_mask(c, 3)
  program.set_chord_four_mask(c, 4)
  luaunit.assert_equals({c.trig_mask, c.note_mask, c.velocity_mask, c.length_mask,
    c.chord_one_mask, c.chord_two_mask, c.chord_three_mask, c.chord_four_mask},
    {1, 62, 70, 4, 1, 2, 3, 4})
  luaunit.assert_equals(program.get_length_mask(c), 4)
  luaunit.assert_nil(program.get_length_mask(channel))
  -- chord mask setter by channel number
  program.set_step_chord_mask(5, 3, 9, -2)
  program.set_step_chord_mask(5, 1, 9, 4)
  luaunit.assert_equals(c.step_chord_masks, {[9] = {4, nil, -2}})
  program.set_step_chord_mask(5, 3, 9, nil)
  luaunit.assert_equals(c.step_chord_masks, {[9] = {4}})
end

function test_program_extra_toggle_step_trig_mask_inverts_the_trig()
  program.init()
  local channel = program.get_channel(1, 1)
  channel.working_pattern.trig_values[2] = 1
  program.toggle_step_trig_mask(1, 1)
  program.toggle_step_trig_mask(1, 2)
  luaunit.assert_equals(channel.step_trig_masks, {[1] = 1, [2] = 0})
  -- characterisation: a second toggle derives from the trig again, not the mask
  program.toggle_step_trig_mask(1, 1)
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  -- a trig value other than 0 or 1 leaves the mask alone
  channel.working_pattern.trig_values[3] = 2
  program.toggle_step_trig_mask(1, 3)
  luaunit.assert_nil(channel.step_trig_masks[3])
  channel.step_trig_masks = nil
  program.toggle_step_trig_mask(1, 1)
  luaunit.assert_equals(channel.step_trig_masks, {[1] = 1})
end

function test_program_extra_get_scale_zero_is_a_fresh_chromatic_scale()
  program.init()
  local expected_scale = musicutil.generate_scale(0, "chromatic", 20)
  local chromatic = program.get_scale(0)
  luaunit.assert_equals(chromatic, {name = "Chromatic", number = 0, scale = expected_scale,
    pentatonic_scale = expected_scale, romans = {}, root_note = 0, chord = 1, chord_degree_rotation = 0})
  luaunit.assert_equals({chromatic.scale[1], chromatic.scale[2], chromatic.scale[13]}, {0, 1, 12})
  -- characterisation: musicutil stops at MIDI note 127
  luaunit.assert_equals(#chromatic.scale, 128)
  chromatic.root_note = 4
  luaunit.assert_equals(program.get_scale(0).root_note, 0)
  luaunit.assert_true(rawequal(program.get_scale(2), program.get_selected_song_pattern().scales[2]))
end

function test_program_extra_get_scale_copies_legacy_store_scales()
  program.init()
  local legacy = {[1] = {number = 5, root_note = 2}}
  program.get().scales = legacy
  program.get_selected_song_pattern().scales = nil
  local scale = program.get_scale(1)
  luaunit.assert_equals(scale, {number = 5, root_note = 2})
  luaunit.assert_false(rawequal(scale, legacy[1]))
  scale.root_note = 9
  luaunit.assert_equals(legacy[1].root_note, 2)
end

function test_program_extra_set_scale_bumps_version()
  program.init()
  program.set_scale(3, {number = 4})
  luaunit.assert_equals(program.get_scale(3), {number = 4, version = 2})
  program.set_scale(3, {number = 5})
  luaunit.assert_equals(program.get_scale(3).version, 3)
  program.get_selected_song_pattern().scales[4].version = nil
  program.set_scale(4, {number = 6})
  luaunit.assert_equals(program.get_scale(4).version, 1)
  luaunit.assert_equals(program.get_song_pattern(2).scales[3].version, 1)
end

function test_program_extra_set_all_song_pattern_scales()
  program.init()
  program.get_song_pattern(1)
  program.get_song_pattern(3)
  local scale = {number = 7}
  program.set_all_song_pattern_scales(2, scale)
  luaunit.assert_equals(program.get_song_pattern(1).scales[2].number, 7)
  luaunit.assert_equals(program.get_song_pattern(3).scales[2].number, 7)
  luaunit.assert_equals(program.get_song_pattern(3).scales[2].version, 2)
  luaunit.assert_equals(program.get_song_pattern(1).scales[1].number, 1)
  -- only song patterns that already exist receive it
  luaunit.assert_equals(program.get_song_pattern(2).scales[2].number, 1)
  -- characterisation (suspected defect: one table is stored in every song pattern, so an
  -- in-place edit of one pattern's scale changes them all; program.lua:668-672).
  luaunit.assert_true(rawequal(program.get_song_pattern(1).scales[2], program.get_song_pattern(3).scales[2]))
  program.set_chord_degree_rotation_for_scale(2, 3)
  luaunit.assert_equals(program.get_song_pattern(3).scales[2].chord_degree_rotation, 3)
end

function test_program_extra_chord_degree_rotation_clamps()
  program.init()
  for _, case in ipairs({{-1, 0}, {0, 0}, {4, 4}, {6, 6}, {9, 6}}) do
    program.set_chord_degree_rotation_for_scale(5, case[1])
    luaunit.assert_equals(program.get_scale(5).chord_degree_rotation, case[2])
  end
  program.set_chord_degree_rotation_for_scale(5, nil)
  luaunit.assert_equals(program.get_scale(5).chord_degree_rotation, 6)
  luaunit.assert_equals(program.get_scale(6).chord_degree_rotation, 0)
end

function test_program_extra_effective_swing_and_shuffle_resolution()
  program.init()
  local channel = program.get_channel(1, 1)
  with_params({global_swing_shuffle_type = 1, global_swing = 17, global_shuffle_feel = 3,
      global_shuffle_basis = 5, global_shuffle_amount = 40}, function()
    -- swing: a channel value above -51 wins, otherwise global swing only under type 1
    luaunit.assert_equals(program.get_effective_swing(channel), 17)
    channel.swing = -50
    luaunit.assert_equals(program.get_effective_swing(channel), -50)
    channel.swing = -51
    luaunit.assert_equals(program.get_effective_swing(channel), 17)
    -- shuffle values fall back to 0 under type 1
    luaunit.assert_equals(program.get_effective_shuffle_feel(channel), 0)
    luaunit.assert_equals(program.get_effective_shuffle_basis(channel), 0)
    luaunit.assert_equals(program.get_effective_shuffle_amount(channel), 0)
    params:set("global_swing_shuffle_type", 2)
    luaunit.assert_equals(program.get_effective_swing(channel), 0)
    luaunit.assert_equals(program.get_effective_shuffle_feel(channel), 3)
    luaunit.assert_equals(program.get_effective_shuffle_basis(channel), 5)
    luaunit.assert_equals(program.get_effective_shuffle_amount(channel), 40)
    -- a positive channel value wins; 0 inherits
    channel.shuffle_feel, channel.shuffle_basis, channel.shuffle_amount = 1, 6, 1
    luaunit.assert_equals(program.get_effective_shuffle_feel(channel), 1)
    luaunit.assert_equals(program.get_effective_shuffle_basis(channel), 6)
    luaunit.assert_equals(program.get_effective_shuffle_amount(channel), 1)
    channel.shuffle_feel, channel.shuffle_basis, channel.shuffle_amount = 0, 0, 0
    luaunit.assert_equals(program.get_effective_shuffle_feel(channel), 3)
    luaunit.assert_equals(program.get_effective_shuffle_basis(channel), 5)
    luaunit.assert_equals(program.get_effective_shuffle_amount(channel), 40)
    channel.swing = 12
    luaunit.assert_equals(program.get_effective_swing(channel), 12)
  end)
end

function test_program_extra_blink_state_toggles()
  program.init()
  luaunit.assert_equals(program.get_blink_state(), false)
  program.toggle_blink_state()
  luaunit.assert_equals(program.get_blink_state(), true)
  program.toggle_blink_state()
  luaunit.assert_equals(program.get_blink_state(), false)
end

function test_program_extra_update_working_pattern_for_step()
  program.init()
  local channel = program.get_channel(1, 1)
  program.update_working_pattern_for_step(channel, 5, 1, 3, 80, 4)
  local wp = channel.working_pattern
  luaunit.assert_equals({wp.trig_values[5], wp.note_mask_values[5], wp.velocity_values[5], wp.lengths[5]}, {1, 3, 80, 4})
  -- nil arguments leave values alone; 0 is a value
  program.update_working_pattern_for_step(channel, 5, nil, nil, nil, nil)
  luaunit.assert_equals({wp.trig_values[5], wp.note_mask_values[5], wp.velocity_values[5], wp.lengths[5]}, {1, 3, 80, 4})
  program.update_working_pattern_for_step(channel, 5, 0, 0, 0, 0)
  luaunit.assert_equals({wp.trig_values[5], wp.note_mask_values[5], wp.velocity_values[5], wp.lengths[5]}, {0, 0, 0, 0})
  luaunit.assert_equals(wp.note_values[5], 0)
  luaunit.assert_equals(wp.trig_values[6], 0)
  -- a channel without a working pattern gets a default one first
  local bare = {}
  program.update_working_pattern_for_step(bare, 2, 1, nil, nil, nil)
  local expected = default_pattern()
  expected.trig_values[2] = 1
  luaunit.assert_equals(bare.working_pattern, expected)
end

function test_program_extra_update_working_pattern_trig()
  program.init()
  local channel = program.get_channel(1, 1)
  program.update_working_pattern_trig(channel, 64, 1)
  luaunit.assert_equals(channel.working_pattern.trig_values[64], 1)
  luaunit.assert_equals(channel.working_pattern.trig_values[63], 0)
  local bare = {}
  program.update_working_pattern_trig(bare, 1, 1)
  local expected = default_pattern()
  expected.trig_values[1] = 1
  luaunit.assert_equals(bare.working_pattern, expected)
end

function test_program_extra_clear_working_pattern_for_step()
  program.init()
  local channel = program.get_channel(1, 1)
  program.update_working_pattern_for_step(channel, 7, 1, 5, 20, 3)
  channel.working_pattern.note_values[7] = 9
  program.update_working_pattern_for_step(channel, 8, 1, 5, 20, 3)
  program.clear_working_pattern_for_step(channel, 7)
  local wp = channel.working_pattern
  luaunit.assert_equals({wp.trig_values[7], wp.note_values[7], wp.velocity_values[7], wp.lengths[7]}, {0, 0, 100, 1})
  -- characterisation: the note mask value is not reset
  luaunit.assert_equals(wp.note_mask_values[7], 5)
  luaunit.assert_equals({wp.trig_values[8], wp.velocity_values[8], wp.lengths[8]}, {1, 20, 3})
  local bare = {}
  program.clear_working_pattern_for_step(bare, 1)
  luaunit.assert_equals(bare, {})
end

function test_program_extra_repeat_count()
  program.init()
  luaunit.assert_nil(program.get().repeat_count)
  luaunit.assert_equals(program.get_repeat_count(), 1)
  luaunit.assert_equals(program.get().repeat_count, 1)
  program.set_repeat_count(4)
  luaunit.assert_equals(program.get_repeat_count(), 4)
end

function test_program_extra_current_step_per_channel()
  program.init()
  for c = 1, 17 do luaunit.assert_equals(program.get_current_step_for_channel(c), 1) end
  program.set_current_step_for_channel(17, 33)
  program.set_current_step_for_channel(2, 5)
  luaunit.assert_equals(program.get_current_step_for_channel(17), 33)
  luaunit.assert_equals(program.get_current_step_for_channel(2), 5)
  luaunit.assert_equals(program.get_current_step_for_channel(1), 1)
end

function test_program_extra_step_scale_numbers_use_selected_song_pattern()
  program.init()
  program.set_selected_song_pattern(2)
  program.set_channel_step_scale_number(3, 9)
  program.set_global_step_scale_number(4)
  luaunit.assert_equals(program.get_channel_step_scale_number(3), 9)
  luaunit.assert_equals(program.get_channel_step_scale_number(17), 4)
  luaunit.assert_nil(program.get_channel_step_scale_number(18))
  program.set_selected_song_pattern(1)
  luaunit.assert_equals(program.get_channel_step_scale_number(3), 1)
  luaunit.assert_equals(program.get_channel_step_scale_number(17), 1)
end

function test_program_extra_selected_channel_and_pattern_getters()
  program.init()
  program.get().selected_song_pattern = 3
  program.get().selected_channel = 9
  program.get().selected_pattern = 12
  luaunit.assert_true(rawequal(program.get_selected_channel(), program.get_channel(3, 9)))
  luaunit.assert_true(rawequal(program.get_selected_pattern(), program.get_song_pattern(3).patterns[12]))
  luaunit.assert_equals(program.get_selected_channel().number, 9)
  luaunit.assert_true(program.step_has_trig(program.get_channel(3, 9), 1) == false)
  program.get_channel(3, 9).working_pattern.trig_values[1] = 1
  luaunit.assert_true(program.step_has_trig(program.get_channel(3, 9), 1))
end
