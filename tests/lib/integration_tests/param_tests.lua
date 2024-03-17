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

local function mock_random()
  random = function (min, max)
    return max - min
  end
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

function test_params_trig_locks_are_processed_at_the_right_step()
    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    local test_pattern = program.initialise_default_pattern()
  
    local test_step = 8
    local cc_msb = 2
    local cc_value = 111
    local c = 1
  
    test_pattern.note_values[test_step] = 0
    test_pattern.lengths[test_step] = 1
    test_pattern.trig_values[test_step] = 1
    test_pattern.velocity_values[test_step] = 100
  
    program.get().selected_channel = c
  
    local channel = program.get_selected_channel()
  
    channel.trig_lock_params[1].device_name = "test"
    channel.trig_lock_params[1].type = "midi"
    channel.trig_lock_params[1].id = 1
    channel.trig_lock_params[1].cc_msb = cc_msb
  
    program.add_step_param_trig_lock(test_step, 1, cc_value)
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()
  
    -- Reset and set up the clock and MIDI event tracking
    clock_setup()
  
    progress_clock_by_beats(test_step)
  
    local midi_cc_event = table.remove(midi_cc_events)
  
    luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value, 1})
  
  end
  

function test_params_triggless_locks_are_processed_at_the_right_step()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local cc_value = 111
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  -- No trig
  test_pattern.trig_values[test_step] = 0
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].device_name = "test"
  channel.trig_lock_params[1].type = "midi"
  channel.trig_lock_params[1].id = 1
  channel.trig_lock_params[1].cc_msb = cc_msb

  params:set("trigless_locks", 1) 

  program.add_step_param_trig_lock(test_step, 1, cc_value)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value, 1})

end


function test_params_triggless_locks_are_not_processed_if_trigless_param_is_off()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local cc_value = 111
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  -- No trig
  test_pattern.trig_values[test_step] = 0
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].device_name = "test"
  channel.trig_lock_params[1].type = "midi"
  channel.trig_lock_params[1].id = 1
  channel.trig_lock_params[1].cc_msb = cc_msb

  params:set("trigless_locks", 0) 

  program.add_step_param_trig_lock(test_step, 1, cc_value)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_not_equals(midi_cc_event[2], 111)

end


function test_trig_probability_param_lock_trigs_when_probability_is_high_enough() 
  setup()
  mock_random()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local probability = 100
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "trig_probability"

  program.add_step_param_trig_lock(test_step, 1, probability)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_trig_probability_param_lock_doesnt_fire_when_probabiliyu_is_too_low() 
  setup()
  mock_random()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local probability = 99
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "trig_probability"

  program.add_step_param_trig_lock(test_step, 1, probability)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end


function test_trig_probability_param_lock_set_to_zero_doesnt_fire() 
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local probability = 0
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "trig_probability"

  program.add_step_param_trig_lock(test_step, 1, probability)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end

function test_trig_probability_param_lock_set_to_one_hundred_fires() 
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local probability = 100
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "trig_probability"

  program.add_step_param_trig_lock(test_step, 1, probability)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end

function test_quantised_fixed_note_param_lock()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local note = 1
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  -- channel.trig_lock_params[1].type = "trig_probability"
  channel.trig_lock_params[1].id = "quantised_fixed_note"

  program.add_step_param_trig_lock(test_step, 1, note)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end

function test_bipolar_random_note_param_lock()

  setup()
  mock_random()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local note = 1
  local c = 1

  test_pattern.note_values[test_step] = 1
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "bipolar_random_note"

  program.add_step_param_trig_lock(test_step, 1, note)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end

function test_twos_random_note_param_lock()

  setup()
  mock_random()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local note = 3
  local c = 1

  test_pattern.note_values[test_step] = 1
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "twos_random_note"

  program.add_step_param_trig_lock(test_step, 1, note)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 69)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)


end

function test_random_velocity_param_lock()

  setup()
  mock_random()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 30

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "random_velocity"

  program.add_step_param_trig_lock(test_step, 1, 10)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 40)
  luaunit.assert_equals(note_on_event[3], 1)
end


function test_fixed_note_param_lock()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local probability = 100
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "trig_probability"

  program.add_step_param_trig_lock(test_step, 1, probability)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end

function test_quantised_fixed_note_param_lock()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local note = 100
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  -- channel.trig_lock_params[1].type = "trig_probability"
  channel.trig_lock_params[1].id = "fixed_note"

  program.add_step_param_trig_lock(test_step, 1, note)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 100)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end

function test_chord_with_four_extra_note_param_lock()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "chord1"
  channel.trig_lock_params[2].id = "chord2"
  channel.trig_lock_params[3].id = "chord3"
  channel.trig_lock_params[4].id = "chord4"

  program.add_step_param_trig_lock(test_step, 1, chord_note_1)
  program.add_step_param_trig_lock(test_step, 2, chord_note_2)
  program.add_step_param_trig_lock(test_step, 3, chord_note_3)
  program.add_step_param_trig_lock(test_step, 4, chord_note_4)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end

function test_chord_with_one_extra_note_param_lock()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "chord1"

  program.add_step_param_trig_lock(test_step, 1, chord_note_1)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end


function test_chord_with_two_extra_note_param_lock()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 3
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "chord1"
  channel.trig_lock_params[2].id = "chord2"

  program.add_step_param_trig_lock(test_step, 1, chord_note_1)
  program.add_step_param_trig_lock(test_step, 2, chord_note_2)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end


function test_chord_with_three_extra_note_param_lock()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 3
  local chord_note_3 = 5
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "chord1"
  channel.trig_lock_params[2].id = "chord2"
  channel.trig_lock_params[3].id = "chord3"

  program.add_step_param_trig_lock(test_step, 1, chord_note_1)
  program.add_step_param_trig_lock(test_step, 2, chord_note_2)
  program.add_step_param_trig_lock(test_step, 3, chord_note_3)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 69)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end


function test_chord_strum_param_lock_with_four_extra_note_with_off_value_plays_all_notes_at_once()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "chord1"
  channel.trig_lock_params[2].id = "chord2"
  channel.trig_lock_params[3].id = "chord3"
  channel.trig_lock_params[4].id = "chord4"
  channel.trig_lock_params[5].id = "chord_strum"

  program.add_step_param_trig_lock(test_step, 1, chord_note_1)
  program.add_step_param_trig_lock(test_step, 2, chord_note_2)
  program.add_step_param_trig_lock(test_step, 3, chord_note_3)
  program.add_step_param_trig_lock(test_step, 4, chord_note_4)
  program.add_step_param_trig_lock(test_step, 5, 0)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(7)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end

function test_chord_strum_param_lock_with_four_extra_notes_division()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "chord1"
  channel.trig_lock_params[2].id = "chord2"
  channel.trig_lock_params[3].id = "chord3"
  channel.trig_lock_params[4].id = "chord4"
  channel.trig_lock_params[5].id = "chord_strum"

  program.add_step_param_trig_lock(test_step, 1, chord_note_1)
  program.add_step_param_trig_lock(test_step, 2, chord_note_2)
  program.add_step_param_trig_lock(test_step, 3, chord_note_3)
  program.add_step_param_trig_lock(test_step, 4, chord_note_4)
  program.add_step_param_trig_lock(test_step, 5, 18) -- /4

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(7)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)
  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end


function test_chord_strum_param_lock_with_four_extra_notes_multiplication()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "chord1"
  channel.trig_lock_params[2].id = "chord2"
  channel.trig_lock_params[3].id = "chord3"
  channel.trig_lock_params[4].id = "chord4"
  channel.trig_lock_params[5].id = "chord_strum"

  program.add_step_param_trig_lock(test_step, 1, chord_note_1)
  program.add_step_param_trig_lock(test_step, 2, chord_note_2)
  program.add_step_param_trig_lock(test_step, 3, chord_note_3)
  program.add_step_param_trig_lock(test_step, 4, chord_note_4)
  program.add_step_param_trig_lock(test_step, 5, 10)  -- x2

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(7)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(8)
  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(8)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(8)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(8)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(8)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end