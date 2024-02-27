step_handler = include("mosaic/lib/step_handler")
pattern_controller = include("mosaic/lib/pattern_controller")

local clock_controller = include("mosaic/lib/clock_controller")

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
  math.randomseed(os.time())
  program.init()
  globals.reset()
end

local function clock_setup()
  clock_controller.init()
  clock_controller:start()
end

local function progress_clock_one_beat()
  for i = 1, 24 do
    clock_controller.get_clock_lattice():pulse()
  end
end

local function progress_clock_by_pulses(p)
  for i = 1, p do
    clock_controller.get_clock_lattice():pulse()
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

  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_one_beat()
  
  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

end

function test_clock_processes_notes_of_various_lengths()

  -- Define a table of lengths to test
  local lengths_to_test = {1, 2, 3, 4, 5, 16, 17, 24, 31, 32, 33, 47, 48, 63, 64, 65, 150, 277} -- Add more lengths as needed
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

      local note_on_event = table.remove(midi_note_on_events)

      -- Check the note on event
      luaunit.assert_equals(note_on_event[1], 60)
      luaunit.assert_equals(note_on_event[2], 100)
      luaunit.assert_equals(note_on_event[3], 1)

      -- Progress the clock according to the current length being tested
      for _ = 1, length do
          progress_clock_one_beat()
      end

      -- Check the note off event after the specified number of beats
      local note_off_event = table.remove(midi_note_off_events)

      luaunit.assert_equals(note_off_event[1], 60)
      luaunit.assert_equals(note_off_event[2], 100)
      luaunit.assert_equals(note_off_event[3], 1)
  end
end


function test_clock_processes_sequence_page_change_at_end_of_song_pattern_lengths()

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
    for _ = 1, length do
        progress_clock_one_beat()
    end

    luaunit.assert_equals(table.remove(channel_sequencer_page_controller_refresh_events), true)

    for _ = 1, length * 2 do
      progress_clock_one_beat()
    end

    luaunit.assert_equals(table.remove(channel_sequencer_page_controller_refresh_events), true)
    luaunit.assert_equals(table.remove(channel_sequencer_page_controller_refresh_events), true)
  end

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

      velocity = math.random(0, 127)
      
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
      for _ = 1, steps do
        progress_clock_one_beat()
      end

      local note_on_event = table.remove(midi_note_on_events)

      -- Check the note on event
      luaunit.assert_equals(note_on_event[1], 60)
      luaunit.assert_equals(note_on_event[2], velocity)
      luaunit.assert_equals(note_on_event[3], 1)

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
  for _ = 1, steps do
    progress_clock_one_beat()
  end

  local note_on_event = table.remove(midi_note_on_events)

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
  for _ = 1, steps do
    progress_clock_one_beat()
  end

  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 20)
  luaunit.assert_equals(note_on_event[3], 1)

  for _ = 1, steps2 - steps do
    progress_clock_one_beat()
  end

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
  for _ = 1, steps do
    progress_clock_one_beat()
  end

  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 20)
  luaunit.assert_equals(note_on_event[3], 1)

  for _ = 1, steps2 - steps do
    progress_clock_one_beat()
  end

  note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 30)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_channel_17_doesnt_fire_notes()

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

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern

  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[17].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  -- Progress the clock according to the current steps being tested
  for _ = 1, steps do
    progress_clock_one_beat()
  end

  local note_on_event = table.remove(midi_note_on_events)

  -- Check there are no note on events
  luaunit.assertNil(note_on_event)

end


function test_clock_divisions_slow_down_the_clock_div_2()

  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[2] = 0
  test_pattern.lengths[2] = 2
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern

  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  clock_setup()

  local div_2_clock_mod = clock_controller.calculate_divisor(clock_controller.get_clock_divisions()[15])

  clock_controller.set_channel_division(1, div_2_clock_mod)

  luaunit.assertNil(note_on_event)

  progress_clock_one_beat()

  luaunit.assertNil(note_on_event)

  progress_clock_one_beat()

  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_one_beat()
  luaunit.assertNil(note_off_event)
  progress_clock_one_beat()
  luaunit.assertNil(note_off_event)
  progress_clock_one_beat()
  luaunit.assertNil(note_off_event)
  progress_clock_one_beat()

  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

end

function test_clock_divisions_slow_down_the_clock_div_3()

  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[2] = 0
  test_pattern.lengths[2] = 2
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern

  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  clock_setup()

  local div_3_clock_mod = clock_controller.calculate_divisor(clock_controller.get_clock_divisions()[17])

  clock_controller.set_channel_division(1, div_3_clock_mod)

  luaunit.assertNil(note_on_event)

  progress_clock_one_beat()
  progress_clock_one_beat()

  luaunit.assertNil(note_on_event)

  progress_clock_one_beat()

  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_one_beat()
  luaunit.assertNil(note_off_event)
  progress_clock_one_beat()
  luaunit.assertNil(note_off_event)
  progress_clock_one_beat()
  luaunit.assertNil(note_off_event)
  progress_clock_one_beat()
  luaunit.assertNil(note_off_event)
  progress_clock_one_beat()
  luaunit.assertNil(note_off_event)
  progress_clock_one_beat()
  
  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

end



function test_clock_multiplications_speed_up_the_clock_mul_2()

  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[2] = 0
  test_pattern.lengths[2] = 2
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern

  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  clock_setup()

  local mul_2_clock_mod = clock_controller.calculate_divisor(clock_controller.get_clock_divisions()[10])

  clock_controller.set_channel_division(1, mul_2_clock_mod)

  luaunit.assertNil(note_on_event)

  progress_clock_one_beat()

  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_one_beat()

  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

end


function test_clock_multiplications_speed_up_the_clock_mul_16()

  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[16] = 0
  test_pattern.lengths[16] = 32
  test_pattern.trig_values[16] = 1
  test_pattern.velocity_values[16] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern

  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  clock_setup()

  local mul_16_clock_mod = clock_controller.calculate_divisor(clock_controller.get_clock_divisions()[1])

  clock_controller.set_channel_division(1, mul_16_clock_mod)

  luaunit.assertNil(note_on_event)

  progress_clock_one_beat()

  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_one_beat()
  progress_clock_one_beat()

  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

end

function test_clock_can_delay_action_with_no_channel_clock_division_set()

  setup()
  clock_setup()

  local has_fired = false

  local channel = 1

  local clock_division_index = 13
  local delay_multiplier = 1

  clock_controller.delay_action(
    channel,
    clock_division_index,
    delay_multiplier,
    function()
      has_fired = true
    end
  )

  luaunit.assert_false(has_fired)

  progress_clock_one_beat()
  progress_clock_one_beat()
  progress_clock_one_beat()
  progress_clock_one_beat()
  progress_clock_by_pulses(1)

  luaunit.assert_true(has_fired)

end


function test_clock_delay_action_with_no_division_specified_executes_immediately()

  setup()
  clock_setup()

  local has_fired = false

  local channel = 1

  local clock_division_index = 0
  local delay_multiplier = 1

  clock_controller.delay_action(
    channel,
    clock_division_index,
    delay_multiplier,
    function()
      has_fired = true
    end
  )

  luaunit.assert_true(has_fired)

end

function test_clock_delay_action_with_nil_division_executes_immediately()

  setup()
  clock_setup()

  local has_fired = false

  local channel = 1

  local clock_division_index = nil
  local delay_multiplier = 1

  clock_controller.delay_action(
    channel,
    clock_division_index,
    delay_multiplier,
    function()
      has_fired = true
    end
  )

  luaunit.assert_true(has_fired)

end


function test_clock_can_delay_action_with_channel_clock_division_set()

  setup()
  clock_setup()
  progress_clock_one_beat()
  local mul_8_clock_mod = clock_controller.calculate_divisor(clock_controller.get_clock_divisions()[3])

  clock_controller.set_channel_division(1, mul_8_clock_mod)


  pattern_controller.update_working_patterns()

  local has_fired = false

  local channel = 1

  local clock_division_index = 13
  local delay_multiplier = 1

  clock_controller.delay_action(
    channel,
    clock_division_index,
    delay_multiplier,
    function()
      has_fired = true
    end
  )

  luaunit.assert_false(has_fired)

  progress_clock_by_pulses(13)

  luaunit.assert_true(has_fired)

end


-- function test_params_are_processed_at_the_right_step
-- function test_trigless_param_is_processed_if_trigless_locks_are_on
-- function test_trigless_param_are_not_processed_if_trigless_locks_are_off


-- function test_global_default_scale_setting_quantises_notes_properly
-- function test_channel_default_scale_setting_quantises_notes_properly
-- function test_global_step_scale_quantises_notes_properly
-- function test_channel_step_scale_quantises_notes_properly



