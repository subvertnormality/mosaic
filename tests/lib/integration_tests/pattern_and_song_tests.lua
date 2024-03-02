step_handler = include("mosaic/lib/step_handler")
pattern_controller = include("mosaic/lib/pattern_controller")

local clock_controller = include("mosaic/lib/clock_controller")
local quantiser = include("mosaic/lib/quantiser")

-- Mocks
include("mosaic/tests/helpers/mocks/sinfonion_mock")
include("mosaic/tests/helpers/mocks/params_mock")
include("mosaic/tests/helpers/mocks/midi_controller_mock")
include("mosaic/tests/helpers/mocks/channel_edit_page_ui_controller_mock")
include("mosaic/tests/helpers/mocks/device_map_mock")
include("mosaic/tests/helpers/mocks/norns_mock")
include("mosaic/tests/helpers/mocks/channel_sequence_page_controller_mock")
include("mosaic/tests/helpers/mocks/channel_edit_page_controller_mock")

local function setup()
  program.init()
  globals.reset()
  params.reset()
end

local function clock_setup()
  clock_controller.init()
  clock_controller:start()
end

local function progress_clock_by_beats(b)
  for i = 1, (24 * b) do
    clock_controller.get_clock_lattice():pulse()
  end
end

local function progress_clock_by_pulses(p)
  for i = 1, p do
    clock_controller.get_clock_lattice():pulse()
  end
end


function test_current_step_number_is_set_to_start_step_when_lower_than_start_trig_number()

    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    local test_pattern = program.initialise_default_pattern()
  
    test_pattern.note_values[3] = 0
    test_pattern.lengths[3] = 1
    test_pattern.trig_values[3] = 1
    test_pattern.velocity_values[3] = 100
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  
    program.get_channel(1).start_trig[1] = 3
    program.get_channel(1).start_trig[2] = 4
  
  
    pattern_controller.update_working_patterns()
  
    clock_setup()
  
    local note_on_event = table.remove(midi_note_on_events)
  
    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  
    progress_clock_by_beats(1)
  
  end
  
  function test_current_step_number_is_set_to_start_step_when_lower_than_start_trig_number()
  
    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    local test_pattern = program.initialise_default_pattern()
  
    local step = 3
  
    test_pattern.note_values[step] = 0
    test_pattern.lengths[step] = 1
    test_pattern.trig_values[step] = 1
    test_pattern.velocity_values[step] = 100
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  
    program.get_channel(1).start_trig[1] = step
    program.get_channel(1).start_trig[2] = 4
  
  
    pattern_controller.update_working_patterns()
  
    clock_setup()
  
    local note_on_event = table.remove(midi_note_on_events)
  
    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  
  end


function test_sequence_page_change_at_end_of_song_pattern_lengths()

    local lengths_to_test = {4, 8, 10, 11, 24, 32, 33, 64, 65, 128, 300} -- Add more lengths as needed
  
    for _, length in ipairs(lengths_to_test) do
      setup()
      local sequencer_pattern = 1
      program.set_selected_sequencer_pattern(1)
      local test_pattern = program.initialise_default_pattern()
  
      program.get_selected_sequencer_pattern().global_pattern_length = length
  
      program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
      fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  
      pattern_controller.update_working_patterns()
  
      clock_setup()
  
      -- Progress the clock according to the current length being tested
      progress_clock_by_beats(length)
      
  
      luaunit.assert_equals(table.remove(channel_sequencer_page_controller_refresh_events), true)
  
      progress_clock_by_beats(length * 2)
  
      luaunit.assert_equals(table.remove(channel_sequencer_page_controller_refresh_events), true)
      luaunit.assert_equals(table.remove(channel_sequencer_page_controller_refresh_events), true)
    end
  
  end
  