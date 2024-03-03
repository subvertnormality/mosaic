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

function test_song_mode_functions_with_short_channel_pattern_lengths_and_short_sequencer_pattern_lengths()

  setup()

  params:set("song_mode", 1) 

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[3] = 0
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 101

  
  program.get_sequencer_pattern(sequencer_pattern).repeats = 1
  program.get_sequencer_pattern(sequencer_pattern).active = true
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).start_trig[1] = 3
  program.get_channel(1).start_trig[2] = 4

  program.get_channel(1).end_trig[1] = 4
  program.get_channel(1).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern).global_pattern_length = 4

  local sequencer_pattern_2 = 2
  program.set_selected_sequencer_pattern(2)
  
  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[6] = 0
  test_pattern_2.lengths[6] = 1
  test_pattern_2.trig_values[6] = 1
  test_pattern_2.velocity_values[6] = 126

  program.get_sequencer_pattern(sequencer_pattern_2).repeats = 1
  program.get_sequencer_pattern(sequencer_pattern_2).active = true
  program.get_sequencer_pattern(sequencer_pattern_2).patterns[2] = test_pattern_2
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern_2).channels[16].selected_patterns, 2)

  program.get_channel(16).start_trig[1] = 1
  program.get_channel(16).start_trig[2] = 4

  program.get_channel(16).end_trig[1] = 8
  program.get_channel(16).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern_2).global_pattern_length = 8

  program.set_selected_sequencer_pattern(1)

  pattern_controller.update_working_patterns()

  clock_setup()

  -- First trig in sequencer pattern 1 fires
  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  -- First trig in sequencer pattern 1 fires again due to channel being half the length of sequencer pattern
  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(3)

  -- Step 6 of the second sequencer pattern now fires
  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 126)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(3)

  -- First trig in sequencer pattern 1 fires again
  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

end



-- function test_song_mode_functions_with_short_channel_pattern_lengths_and_short_sequencer_pattern_lengths_when_sequence_reset_is_enabled()

--   setup()

--   params:set("song_mode", 1) 
--   params:set("reset_on_end_of_pattern", 1)

--   local sequencer_pattern = 1
--   program.set_selected_sequencer_pattern(1)
--   local test_pattern = program.initialise_default_pattern()

--   test_pattern.note_values[3] = 0
--   test_pattern.lengths[3] = 1
--   test_pattern.trig_values[3] = 1
--   test_pattern.velocity_values[3] = 101

  
--   program.get_sequencer_pattern(sequencer_pattern).repeats = 1
--   program.get_sequencer_pattern(sequencer_pattern).active = true
--   program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
--   fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

--   program.get_channel(1).start_trig[1] = 3
--   program.get_channel(1).start_trig[2] = 4

--   program.get_channel(1).end_trig[1] = 4
--   program.get_channel(1).end_trig[2] = 4

--   program.get_sequencer_pattern(sequencer_pattern).global_pattern_length = 4

--   local sequencer_pattern_2 = 2
--   program.set_selected_sequencer_pattern(2)
  
--   local test_pattern_2 = program.initialise_default_pattern()

--   test_pattern_2.note_values[6] = 0
--   test_pattern_2.lengths[6] = 1
--   test_pattern_2.trig_values[6] = 1
--   test_pattern_2.velocity_values[6] = 126

--   program.get_sequencer_pattern(sequencer_pattern_2).repeats = 1
--   program.get_sequencer_pattern(sequencer_pattern_2).active = true
--   program.get_sequencer_pattern(sequencer_pattern_2).patterns[2] = test_pattern_2
--   fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern_2).channels[16].selected_patterns, 2)

--   program.get_channel(16).start_trig[1] = 1
--   program.get_channel(16).start_trig[2] = 4

--   program.get_channel(16).end_trig[1] = 8
--   program.get_channel(16).end_trig[2] = 4

--   program.get_sequencer_pattern(sequencer_pattern_2).global_pattern_length = 8

--   program.set_selected_sequencer_pattern(1)

--   pattern_controller.update_working_patterns()

--   clock_setup()

--   -- First trig in sequencer pattern 1 fires
--   local note_on_event = table.remove(midi_note_on_events)

--   luaunit.assert_equals(note_on_event[1], 60)
--   luaunit.assert_equals(note_on_event[2], 101)
--   luaunit.assert_equals(note_on_event[3], 1)

--   progress_clock_by_beats(2)

--   -- First trig in sequencer pattern 1 fires again due to channel being half the length of sequencer pattern
--   local note_on_event = table.remove(midi_note_on_events)

--   luaunit.assert_equals(note_on_event[1], 60)
--   luaunit.assert_equals(note_on_event[2], 101)
--   luaunit.assert_equals(note_on_event[3], 1)

--   progress_clock_by_beats(2)
--   print(program.get().global_step_accumulator)
--   progress_clock_by_beats(8)
--   print(program.get().global_step_accumulator)
--   -- Step 6 of the second sequencer pattern now fires
--   local note_on_event = table.remove(midi_note_on_events)

--   luaunit.assert_equals(note_on_event[1], 60)
--   luaunit.assert_equals(note_on_event[2], 126)
--   luaunit.assert_equals(note_on_event[3], 1)

--   -- progress_clock_by_beats(3)

--   -- -- First trig in sequencer pattern 1 fires again
--   -- local note_on_event = table.remove(midi_note_on_events)

--   -- luaunit.assert_equals(note_on_event[1], 60)
--   -- luaunit.assert_equals(note_on_event[2], 101)
--   -- luaunit.assert_equals(note_on_event[3], 1)

-- end
