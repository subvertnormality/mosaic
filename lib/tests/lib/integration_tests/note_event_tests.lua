pattern_controller = include("mosaic/lib/pattern_controller")

local clock_controller = include("mosaic/lib/clock_controller")
local quantiser = include("mosaic/lib/quantiser")

-- Mocks
include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
include("mosaic/lib/tests/helpers/mocks/midi_controller_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_controller_mock")
include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/norns_mock")
include("mosaic/lib/tests/helpers/mocks/channel_sequence_page_controller_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_controller_mock")

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



function test_pattern_doesnt_fire_when_sequencer_pattern_is_not_selected()

    local test_pattern
  
    setup()
    local sequencer_pattern = 2
    program.set_selected_sequencer_pattern(1)
    test_pattern = program.initialise_default_pattern()
  
    local steps = 6
  
    test_pattern.note_values[steps] = 0
    test_pattern.lengths[steps] = 1
    test_pattern.trig_values[steps] = 1
    test_pattern.velocity_values[steps] = 20
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()
  
    -- Reset and set up the clock and MIDI event tracking
    clock_setup()
  
    -- Progress the clock according to the current steps being tested
    progress_clock_by_beats(steps)
  
  
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    -- Check there are no note on events
    luaunit.assertNil(note_on_event)
  
  end
  
  
  function test_multiple_patterns_fire_notes_on_events_from_trigs_in_each_pattern()
  
    local test_pattern
  
    setup()
    local sequencer_pattern = 3
    program.set_selected_sequencer_pattern(3)
    test_pattern = program.initialise_default_pattern()
    test_pattern2 = program.initialise_default_pattern()
  
    local steps = 6
  
    test_pattern.note_values[steps] = 0
    test_pattern.lengths[steps] = 1
    test_pattern.trig_values[steps] = 1
    test_pattern.velocity_values[steps] = 20
  
    local steps2 = 8
  
    test_pattern2.note_values[steps2] = 1
    test_pattern2.lengths[steps2] = 1
    test_pattern2.trig_values[steps2] = 1
    test_pattern2.velocity_values[steps2] = 30
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern2
  
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  
    pattern_controller.update_working_patterns()
  
    -- Reset and set up the clock and MIDI event tracking
    clock_setup()
  
    -- Progress the clock according to the current steps being tested
    progress_clock_by_beats(steps)
  
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 20)
    luaunit.assert_equals(note_on_event[3], 1)
  
    progress_clock_by_beats(steps2 - steps)
  
    note_on_event = table.remove(midi_note_on_events)
  
    luaunit.assert_equals(note_on_event[1], 62)
    luaunit.assert_equals(note_on_event[2], 30)
    luaunit.assert_equals(note_on_event[3], 1)
  
  end
  
  function test_multiple_patterns_fire_notes_on_events_from_trigs_in_each_pattern_when_patterns_are_asigned_to_different_channels()
  
    local test_pattern
  
    setup()
    local sequencer_pattern = 3
    program.set_selected_sequencer_pattern(3)
    test_pattern = program.initialise_default_pattern()
    test_pattern2 = program.initialise_default_pattern()
  
    local steps = 6
  
    test_pattern.note_values[steps] = 0
    test_pattern.lengths[steps] = 1
    test_pattern.trig_values[steps] = 1
    test_pattern.velocity_values[steps] = 20
  
    local steps2 = 8
  
    test_pattern2.note_values[steps2] = 1
    test_pattern2.lengths[steps2] = 1
    test_pattern2.trig_values[steps2] = 1
    test_pattern2.velocity_values[steps2] = 30
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern2
  
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[16].selected_patterns, 2)
  
    pattern_controller.update_working_patterns()
  
    -- Reset and set up the clock and MIDI event tracking
    clock_setup()
  
    -- Progress the clock according to the current steps being tested
    progress_clock_by_beats(steps)
  
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 20)
    luaunit.assert_equals(note_on_event[3], 1)
  
    progress_clock_by_beats(steps2 - steps)
  
    note_on_event = table.remove(midi_note_on_events)
  
    luaunit.assert_equals(note_on_event[1], 62)
    luaunit.assert_equals(note_on_event[2], 30)
    luaunit.assert_equals(note_on_event[3], 1)
  
  end
  


function test_clock_processes_notes_at_various_steps()

    -- Define a table of lengths to test
    local steps_to_test = {1, 2, 5, 10, 33, 64} -- Add more lengths as needed
    local test_pattern
  
    local velocity
  
    for _, steps in ipairs(steps_to_test) do
  
        setup()
        local sequencer_pattern = 1
        program.set_selected_sequencer_pattern(1)
        test_pattern = program.initialise_default_pattern()
  
        velocity = 99
        
        test_pattern.note_values[steps] = 0
        test_pattern.lengths[steps] = 1
        test_pattern.trig_values[steps] = 1
        test_pattern.velocity_values[steps] = velocity
  
        program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
        fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  
        pattern_controller.update_working_patterns()
  
        -- Reset and set up the clock and MIDI event tracking
        clock_setup()
  
        -- Progress the clock according to the current steps being tested
        progress_clock_by_beats(steps)
  
        local note_on_event = table.remove(midi_note_on_events, 1)
  
        -- Check the note on event
        luaunit.assert_equals(note_on_event[1], 60)
        luaunit.assert_equals(note_on_event[2], velocity)
        luaunit.assert_equals(note_on_event[3], 1)
  
    end
  end

function test_clock_processes_note_events()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)
  
  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

end


function test_note_off_values_dont_fire_too_early_or_late()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  test_pattern.note_values[2] = 0
  test_pattern.lengths[2] = 1
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 101

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(23)

  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_nil(note_off_event)

  progress_clock_by_pulses(1)
  
  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)
end

function test_clock_processes_notes_of_various_lengths()

  -- local lengths_to_test = {3/8, 1/8, 1/4, 1/3, 1/2, 0.75, 1, 1.25, 2.5, 3, 4, 5, 16, 17, 24, 31, 32, 33, 47, 48, 63, 64, 65, 128} -- Add more lengthsas needed
  local lengths_to_test = {1/4} -- Add more lengthsas needed

  
  local test_pattern

  for _, length in ipairs(lengths_to_test) do

      setup()
      local sequencer_pattern = 1
      program.set_selected_sequencer_pattern(1)
      test_pattern = program.initialise_default_pattern()
      
      test_pattern.note_values[1] = 0
      test_pattern.lengths[1] = length
      test_pattern.trig_values[1] = 1
      test_pattern.velocity_values[1] = 100

      program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
      fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

      pattern_controller.update_working_patterns()

      -- Reset and set up the clock and MIDI event tracking
      clock_setup()

      local note_on_event = table.remove(midi_note_on_events, 1)

      -- Check the note on event
      luaunit.assert_equals(note_on_event[1], 60)
      luaunit.assert_equals(note_on_event[2], 100)
      luaunit.assert_equals(note_on_event[3], 1)

      -- Progress the clock according to the current length being tested
      progress_clock_by_beats(length)

      -- Check the note off event after the specified number of beats
      local note_off_event = table.remove(midi_note_off_events)

      luaunit.assert_equals(note_off_event[1], 60)
      luaunit.assert_equals(note_off_event[2], 100)
      luaunit.assert_equals(note_off_event[3], 1)
  end
end
  

function test_end_trig_functions_as_expected()

  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local step = 1
  local end_trig = 4

  test_pattern.note_values[step] = 0
  test_pattern.lengths[step] = 1
  test_pattern.trig_values[step] = 1
  test_pattern.velocity_values[step] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).end_trig[1] = end_trig
  program.get_channel(1).end_trig[2] = 4

  pattern_controller.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(4)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(4)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end
  