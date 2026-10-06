-- README#trig-parameters: "Trig params are unique to a song pattern". A channel's
-- sequencer params set without holding a step belong to the song pattern that
-- was selected when they were set; moving to another pattern must not carry
-- them along. Device params are a patch shared by every pattern (README
-- "Device configuration"), so the tests only expect sequencer params to differ.
step = step or include("mosaic/lib/step")
pattern = include("mosaic/lib/pattern")
local divisions = include("mosaic/lib/clock/divisions")

include("mosaic/lib/tests/helpers/mocks/norns_mock")
include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
local m_clock = include("mosaic/lib/clock/m_clock")

local function division_index(value)
  for index, entry in ipairs(divisions.note_divisions) do
    if entry.value == value then return index end
  end
  error("no note division " .. value)
end

local STRUM = fn.get_param_id_from_stock_id("chord_strum", 1)
local SPREAD = fn.get_param_id_from_stock_id("chord_spread", 1)

-- Channel 1 plays a three-note chord on song pattern 1; every sequencer param
-- starts at its off value, as it does in a new project.
local function setup_chord()
  program.init()
  globals.reset()
  params.reset()
  m_clock.init()
  m_clock:start()
  fn.each_stock_param_id(1, function(stock_id, param_id)
    local off = (stock_id == "fixed_note" or stock_id == "quantised_fixed_note" or stock_id == "trig_probability") and -1 or 0
    params:set(param_id, off)
  end)
  program.set_selected_song_pattern(1)
  for song_pattern = 1, 2 do
    local test_pattern = program.initialise_default_pattern()
    test_pattern.note_values[1] = 0
    test_pattern.lengths[1] = 2
    test_pattern.trig_values[1] = 1
    test_pattern.velocity_values[1] = 100
    local slot_channel = program.get_channel(song_pattern, 1)
    slot_channel.chord_one_mask = 2
    slot_channel.chord_two_mask = 4
    slot_channel.trig_lock_params[1] = {id = "chord_strum", param_id = STRUM, off_value = 0, type = "midi"}
    program.get_song_pattern(song_pattern).patterns[1] = test_pattern
    fn.add_to_set(slot_channel.selected_patterns, 1)
    pattern.update_working_pattern(1, program.get_song_pattern(song_pattern))
  end
  local channel = program.get_channel(1, 1)
  program.get().default_scale = 1
  program.get_scale(1).root_note = 0
  program.get_scale(1).number = 1
  return channel
end

-- Note-on pulses of channel 1's step 1 under the selected song pattern.
local function note_on_pulses()
  midi_note_on_events = {}
  step.handle(1, 1)
  local pulses = {}
  for pulse = 0, 100 do
    if pulse > 0 then m_clock.get_clock_lattice():pulse() end
    while #midi_note_on_events > 0 do
      pulses[#pulses + 1] = {pulse, table.remove(midi_note_on_events, 1)[1]}
    end
  end
  return pulses
end

local BLOCK = {{0, 60}, {0, 64}, {0, 67}}
local STRUMMED = {{0, 60}, {48, 64}, {96, 67}}

-- Set on pattern 2's Trig params page with no step held, Strum 1 applies to
-- pattern 2 only; pattern 1 still plays its block chord.
function test_strum_set_in_song_pattern_2_does_not_strum_song_pattern_1()
  setup_chord()
  program.set_selected_song_pattern(2)
  params:set(STRUM, division_index(1))
  params:set(SPREAD, division_index(1))
  program.set_selected_song_pattern(1)
  luaunit.assert_equals(note_on_pulses(), BLOCK, "pattern 1 plays its block chord")
  luaunit.assert_equals(params:get(STRUM), 0, "pattern 1 shows Strum off")
end

function test_song_pattern_2_keeps_its_strum_when_it_is_selected_again()
  setup_chord()
  program.set_selected_song_pattern(2)
  params:set(STRUM, division_index(1))
  params:set(SPREAD, division_index(1))
  program.set_selected_song_pattern(1)
  program.set_selected_song_pattern(2)
  luaunit.assert_equals(params:get(STRUM), division_index(1))
  luaunit.assert_equals(params:get(SPREAD), division_index(1))
  luaunit.assert_equals(note_on_pulses(), STRUMMED)
end

-- The class, not the one call site: every sequencer param on every channel is
-- kept per song pattern.
function test_every_sequencer_param_on_every_channel_is_unique_to_a_song_pattern()
  setup_chord()
  local ids = {}
  for channel_number = 1, 16 do
    fn.each_stock_param_id(channel_number, function(stock_id, param_id)
      params:set(param_id, 1)
      ids[#ids + 1] = {stock_id, param_id}
    end)
  end
  luaunit.assert_true(#ids >= 16 * 14)
  program.set_selected_song_pattern(2)
  for _, entry in ipairs(ids) do params:set(entry[2], 5) end
  program.set_selected_song_pattern(3)
  for _, entry in ipairs(ids) do params:set(entry[2], 9) end
  program.set_selected_song_pattern(1)
  for _, entry in ipairs(ids) do luaunit.assert_equals(params:get(entry[2]), 1, "pattern 1 " .. entry[2]) end
  program.set_selected_song_pattern(2)
  for _, entry in ipairs(ids) do luaunit.assert_equals(params:get(entry[2]), 5, "pattern 2 " .. entry[2]) end
  program.set_selected_song_pattern(3)
  for _, entry in ipairs(ids) do luaunit.assert_equals(params:get(entry[2]), 9, "pattern 3 " .. entry[2]) end
end

-- README "Device configuration": stored device params stay the same across song patterns.
function test_device_patch_params_are_shared_by_every_song_pattern()
  setup_chord()
  local patch = "midi_device_params_channel_1_30"
  params:set(patch, 40)
  program.set_selected_song_pattern(2)
  luaunit.assert_equals(params:get(patch), 40)
  params:set(patch, 77)
  program.set_selected_song_pattern(1)
  luaunit.assert_equals(params:get(patch), 77)
end

-- A pattern never visited carries the current values, as projects made before
-- values were kept per pattern always did.
function test_a_song_pattern_not_visited_before_inherits_the_current_values()
  setup_chord()
  params:set(STRUM, division_index(1))
  program.set_selected_song_pattern(4)
  luaunit.assert_equals(params:get(STRUM), division_index(1))
end

-- Copying the selected pattern over another gives the copy the values on screen.
function test_a_copied_song_pattern_takes_the_values_of_its_source()
  setup_chord()
  params:set(STRUM, division_index(1))
  program.set_selected_song_pattern(2)
  params:set(STRUM, division_index(2))
  program.set_selected_song_pattern(1)
  luaunit.assert_equals(params:get(STRUM), division_index(1))
  program.set_song_pattern(1, 3)
  program.set_selected_song_pattern(3)
  luaunit.assert_equals(params:get(STRUM), division_index(1))
  program.set_selected_song_pattern(2)
  luaunit.assert_equals(params:get(STRUM), division_index(2))
end
