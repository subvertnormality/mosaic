step_handler = include("mosaic/lib/step_handler")
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
  
    progress_clock_by_beats(test_step - 1)
  
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

  params:set("trigless_locks", 2) 

  program.add_step_param_trig_lock(test_step, 1, cc_value)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

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

  progress_clock_by_beats(test_step - 1)

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

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_trig_probability_param_lock_doesnt_fire_when_probability_is_too_low() 
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

  progress_clock_by_beats(test_step - 1)

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

  progress_clock_by_beats(test_step - 1)

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

  progress_clock_by_beats(test_step - 1)

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

  progress_clock_by_beats(test_step - 1)

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
  local shift = 1
  local c = 1

  test_pattern.note_values[test_step] = 1
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c


  local channel = program.get_selected_channel()


  channel.trig_lock_params[1].id = "bipolar_random_note"

  program.add_step_param_trig_lock(test_step, 1, shift)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_bipolar_random_note_param_lock_when_pentatonic_option_is_selected()

  setup()
  mock_random()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local scale = quantiser.get_scales()[1]

  local test_step = 1
  local cc_msb = 2
  local shift = 1
  local c = 1

  test_pattern.note_values[test_step] = 2
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 2
    }
  )

  program.get().default_scale = 2

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].id = "bipolar_random_note"

  params:set("all_scales_lock_to_pentatonic", 1)
  params:set("random_lock_to_pentatonic", 2)

  program.add_step_param_trig_lock(test_step, 1, shift)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 66)
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

  progress_clock_by_beats(test_step - 1)

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

  progress_clock_by_beats(test_step - 1)

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

  progress_clock_by_beats(test_step - 1)

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

  progress_clock_by_beats(test_step - 1)

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


  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

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

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

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

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

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

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

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


  channel.trig_lock_params[5].id = "chord_strum"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 0)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

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

  channel.trig_lock_params[5].id = "chord_strum"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

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



function test_chord_strum_param_lock_notes_adhere_to_scale_changes()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local scale = quantiser.get_scales()[1]
  
  program.set_scale(
    1,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  program.set_scale(
    2,
    {
      number = 2,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 3,
      root_note = 0
    }
  )

  program.set_scale(
    3,
    {
      number = 3,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 5,
      root_note = 0
    }
  )

  program.get().default_scale = 1

  local test_step = 1
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

  channel.trig_lock_params[5].id = "chord_strum"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1

  program.add_step_scale_trig_lock(1, 1)
  program.add_step_scale_trig_lock(3, 2)
  program.add_step_scale_trig_lock(4, 3)
  program.add_step_scale_trig_lock(5, 1)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

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

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 72)
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

  channel.trig_lock_params[5].id = "chord_strum"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 2)  -- 1/16

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(8)
  progress_clock_by_pulses(1)  -- This is not ideal, strums are slightly off time

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

function test_chord_strum_param_lock_with_backwards_strum_pattern()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()


  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_strum"
  channel.trig_lock_params[6].id = "chord_strum_pattern"

  channel.step_chord_masks[1] = {}
  channel.step_chord_masks[1][1] = chord_note_1
  channel.step_chord_masks[1][2] = chord_note_2
  channel.step_chord_masks[1][3] = chord_note_3
  channel.step_chord_masks[1][4] = chord_note_4
  program.add_step_param_trig_lock(1, 5, 17)  -- 1
  program.add_step_param_trig_lock(1, 6, 2) -- Backwards pattern

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(3) -- This is not ideal, reversed strums are even more slightly off time

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end


function test_chord_strum_param_lock_with_inside_out_strum_pattern()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()


  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_strum"
  channel.trig_lock_params[6].id = "chord_strum_pattern"

  channel.step_chord_masks[1] = {}
  channel.step_chord_masks[1][1] = chord_note_1
  channel.step_chord_masks[1][2] = chord_note_2
  channel.step_chord_masks[1][3] = chord_note_3
  channel.step_chord_masks[1][4] = chord_note_4
  program.add_step_param_trig_lock(1, 5, 17)  -- 1
  program.add_step_param_trig_lock(1, 6, 3) -- Inside out strum pattern

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(2) -- This is not ideal, reversed strums are even more slightly off time

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
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

  luaunit.assert_nil(note_on_event)

end

function test_chord_strum_param_lock_with_outside_in_strum_pattern()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()


  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_strum"
  channel.trig_lock_params[6].id = "chord_strum_pattern"

  channel.step_chord_masks[1] = {}
  channel.step_chord_masks[1][1] = chord_note_1
  channel.step_chord_masks[1][2] = chord_note_2
  channel.step_chord_masks[1][3] = chord_note_3
  channel.step_chord_masks[1][4] = chord_note_4
  program.add_step_param_trig_lock(1, 5, 17)  -- 1
  program.add_step_param_trig_lock(1, 6, 4) -- Outside in strum pattern

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(3) -- This is not ideal, reversed strums are slightly off time

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end

function test_chord_with_velocity_swell_param_lock()
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
  test_pattern.velocity_values[test_step] = 80

  program.get().selected_channel = c

  local channel = program.get_selected_channel()


  channel.trig_lock_params[4].id = "chord_velocity_modifier"

  program.add_step_param_trig_lock(test_step, 4, 10)

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 80)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 90)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 69)
  luaunit.assert_equals(note_on_event[2], 110)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end



function test_chord_with_velocity_fade_param_lock()
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
  test_pattern.velocity_values[test_step] = 80

  program.get().selected_channel = c

  local channel = program.get_selected_channel()


  channel.trig_lock_params[4].id = "chord_velocity_modifier"
  channel.trig_lock_params[4].cc_min_value = -40

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  program.add_step_param_trig_lock(test_step, 4, -10)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 80)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 70)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 60)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 69)
  luaunit.assert_equals(note_on_event[2], 50)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end


function test_global_params_are_processed_at_all_steps()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local test_step_2 = 10
  local test_step_3 = 15

  local cc_msb = 2
  local cc_value = 111
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  test_pattern.note_values[test_step_2] = 1
  test_pattern.lengths[test_step_2] = 1
  test_pattern.trig_values[test_step_2] = 1
  test_pattern.velocity_values[test_step_2] = 100

  test_pattern.note_values[test_step_3] = 2
  test_pattern.lengths[test_step_3] = 1
  test_pattern.trig_values[test_step_3] = 1
  test_pattern.velocity_values[test_step_3] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].device_name = "test"
  channel.trig_lock_params[1].type = "midi"
  channel.trig_lock_params[1].id = 1
  channel.trig_lock_params[1].cc_msb = cc_msb
  channel.trig_lock_banks[1] = cc_value

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()
  local midi_cc_event = table.remove(midi_cc_events)
  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value, 1}) -- CC is fired at start of pattern to reset value to default

  progress_clock_by_beats(test_step - 1)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value, 1})

  progress_clock_by_beats(test_step_2 - test_step)
  
  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value, 1})

  channel.trig_lock_banks[1] = cc_value + 1
  
  progress_clock_by_beats(test_step_3 - test_step_2)
  
  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value + 1, 1})


end





function test_global_params_are_processed_with_the_correct_value_across_song_patterns()
  setup()
  local sequencer_pattern_1 = 1
  local sequencer_pattern_2 = 2
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local c = 1

  local cc_value_1 = 111
  local cc_value_2 = 112

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  program.get_sequencer_pattern(sequencer_pattern_1).patterns[1] = test_pattern

  local channel_song_pattern_1 = program.get_sequencer_pattern(sequencer_pattern_1).channels[c]

  channel_song_pattern_1.trig_lock_params[1].device_name = "test"
  channel_song_pattern_1.trig_lock_params[1].type = "midi"
  channel_song_pattern_1.trig_lock_params[1].id = 1
  channel_song_pattern_1.trig_lock_params[1].cc_msb = cc_msb
  channel_song_pattern_1.trig_lock_banks[1] = cc_value_1

  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern_1).channels[c].selected_patterns, 1)

  local test_pattern_2 = program.initialise_default_pattern()

  local song_pattern_2_cc_value = 112

  test_pattern_2.note_values[test_step] = 0
  test_pattern_2.lengths[test_step] = 1
  test_pattern_2.trig_values[test_step] = 1
  test_pattern_2.velocity_values[test_step] = 100

  program.get_sequencer_pattern(sequencer_pattern_2).patterns[1] = test_pattern_2

  local channel_song_pattern_2 = program.get_sequencer_pattern(sequencer_pattern_2).channels[c]

  channel_song_pattern_2.trig_lock_params[1].device_name = "test"
  channel_song_pattern_2.trig_lock_params[1].type = "midi"
  channel_song_pattern_2.trig_lock_params[1].id = 1
  channel_song_pattern_2.trig_lock_params[1].cc_msb = cc_msb
  channel_song_pattern_2.trig_lock_banks[1] = cc_value_2

  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern_2).channels[c].selected_patterns, 1)

  program.set_selected_sequencer_pattern(sequencer_pattern_1)
  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()
  local midi_cc_event = table.remove(midi_cc_events)
  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value_1, 1}) -- CC is fired at start of pattern to reset value to default

  progress_clock_by_beats(test_step - 1)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value_1, 1})

  program.set_selected_sequencer_pattern(sequencer_pattern_2)
  pattern_controller.update_working_patterns()

  progress_clock_by_beats(64) -- get to next pattern

  progress_clock_by_beats(test_step - 1)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value_2, 1})

end

function test_arp_param_lock_with_four_extra_notes()
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
  test_pattern.lengths[test_step] = 8
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

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

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end

function test_arp_param_lock_with_four_extra_notes_divison()
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
  test_pattern.lengths[test_step] = 8
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 21) -- 2

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end



function test_arp_param_lock_adheres_to_scale_changes()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()



  local scale = quantiser.get_scales()[1]
  
  program.set_scale(
    1,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  program.set_scale(
    2,
    {
      number = 2,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 3,
      root_note = 0
    }
  )

  program.set_scale(
    3,
    {
      number = 3,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 5,
      root_note = 0
    }
  )

  program.get().default_scale = 1

  local test_step = 1
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 8
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 21) -- 2

  program.add_step_scale_trig_lock(1, 1)
  program.add_step_scale_trig_lock(3, 2)
  program.add_step_scale_trig_lock(5, 3)
  program.add_step_scale_trig_lock(7, 1)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 71)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end


function test_arp_param_lock_with_four_extra_notes_but_one_blank_rests_for_that_step()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 10
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = 0
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

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

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

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

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)
end



function test_arp_with_velocity_swell_param_lock()
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
  test_pattern.lengths[test_step] = 5
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 80

  program.get().selected_channel = c

  local channel = program.get_selected_channel()


  channel.trig_lock_params[4].id = "chord_velocity_modifier"
  channel.trig_lock_params[5].id = "chord_arp"

  program.add_step_param_trig_lock(test_step, 4, 10)
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 80)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 90)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 69)
  luaunit.assert_equals(note_on_event[2], 110)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 120)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end



function test_arp_param_lock_with_backwards_strum_pattern()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()


  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 6
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"
  channel.trig_lock_params[6].id = "chord_strum_pattern"

  channel.step_chord_masks[1] = {}
  channel.step_chord_masks[1][1] = chord_note_1
  channel.step_chord_masks[1][2] = chord_note_2
  channel.step_chord_masks[1][3] = chord_note_3
  channel.step_chord_masks[1][4] = chord_note_4
  program.add_step_param_trig_lock(1, 5, 17)  -- 1
  program.add_step_param_trig_lock(1, 6, 2) -- Backwards pattern

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
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


function test_arp_param_lock_with_inside_out_strum_pattern()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()


  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 6
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"
  channel.trig_lock_params[6].id = "chord_strum_pattern"

  channel.step_chord_masks[1] = {}
  channel.step_chord_masks[1][1] = chord_note_1
  channel.step_chord_masks[1][2] = chord_note_2
  channel.step_chord_masks[1][3] = chord_note_3
  channel.step_chord_masks[1][4] = chord_note_4
  program.add_step_param_trig_lock(1, 5, 17)  -- 1
  program.add_step_param_trig_lock(1, 6, 3) -- Inside out strum pattern

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
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

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end

function test_chord_arp_param_lock_with_outside_in_strum_pattern()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 6
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"
  channel.trig_lock_params[6].id = "chord_strum_pattern"

  channel.step_chord_masks[1] = {}
  channel.step_chord_masks[1][1] = chord_note_1
  channel.step_chord_masks[1][2] = chord_note_2
  channel.step_chord_masks[1][3] = chord_note_3
  channel.step_chord_masks[1][4] = chord_note_4
  program.add_step_param_trig_lock(1, 5, 17)  -- 1
  program.add_step_param_trig_lock(1, 6, 4) -- Outside in strum pattern

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
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



function test_chord_arp_param_lock_with_outside_in_strum_pattern_and_rests()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local cc_msb = 2

  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 6
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"
  channel.trig_lock_params[6].id = "chord_strum_pattern"

  channel.step_chord_masks[1] = {}
  channel.step_chord_masks[1][1] = 0
  channel.step_chord_masks[1][2] = chord_note_2
  channel.step_chord_masks[1][3] = chord_note_3
  channel.step_chord_masks[1][4] = chord_note_4
  program.add_step_param_trig_lock(1, 5, 17)  -- 1
  program.add_step_param_trig_lock(1, 6, 4) -- Outside in strum pattern

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
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



function test_rests_dont_apply_when_in_last_chord_slots()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local cc_msb = 2
  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local c = 1

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 6
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"
  channel.trig_lock_params[6].id = "chord_strum_pattern"

  channel.step_chord_masks[1] = {}
  channel.step_chord_masks[1][1] = chord_note_1
  channel.step_chord_masks[1][2] = chord_note_2
  channel.step_chord_masks[1][3] = chord_note_3
  channel.step_chord_masks[1][4] = 0
  program.add_step_param_trig_lock(1, 5, 17)  -- 1

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

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

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end



function test_rests_dont_apply_when_in_last_chord_slots_multiple_slots()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local cc_msb = 2
  local chord_note_1 = 1
  local c = 1

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 6
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"
  channel.trig_lock_params[6].id = "chord_strum_pattern"

  channel.step_chord_masks[1] = {}
  channel.step_chord_masks[1][1] = chord_note_1
  channel.step_chord_masks[1][2] = 0
  channel.step_chord_masks[1][3] = 0
  channel.step_chord_masks[1][4] = 0
  program.add_step_param_trig_lock(1, 5, 17)  -- 1

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  -- progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)
  progress_clock_by_pulses(12)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end


function test_chord_strum_param_lock_with_spread()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 1
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

  channel.trig_lock_params[5].id = "chord_strum"
  channel.trig_lock_params[6].id = "chord_spread"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1
  program.add_step_param_trig_lock(test_step, 6, 5) -- 1/4

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  -- progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60) -- 0!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 1

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1/4) -- 1.25

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62) -- 1.25!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 2.25

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event) -- 2.25

  progress_clock_by_beats(1/4) -- 2.5
  progress_clock_by_beats(1/4) -- 2.75

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64) -- 2.75!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 3.75

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)  -- 3.75

  progress_clock_by_beats(1/4) -- 4
  progress_clock_by_beats(1/4) -- 4.25
  progress_clock_by_beats(1/4) -- 4.5

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)  -- 4.5!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)  -- 5.5

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1/4)  -- 5.75
  progress_clock_by_beats(1/4)  -- 6
  progress_clock_by_beats(1/4)  -- 6.25
  progress_clock_by_beats(1/4)  -- 6.5

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67) -- 6.5!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
  

  progress_clock_by_beats(1) -- 7.5

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end



function test_chord_arp_param_lock_with_spread()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 1
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 15
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"
  channel.trig_lock_params[6].id = "chord_spread"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1
  program.add_step_param_trig_lock(test_step, 6, 5) -- 1/4

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60) -- 0!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 1

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1/4) -- 1.25
  progress_clock_by_pulses(1)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62) -- 1.25!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 2.25

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event) -- 2.25

  progress_clock_by_beats(1/2) -- 2.75

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64) -- 2.75!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 3.75

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)  -- 3.75

  progress_clock_by_beats(1/2) -- 4
  progress_clock_by_beats(1/4) -- 4.25

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)  -- 4.25!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)  -- 5.25

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1)  -- 6

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
  

  progress_clock_by_beats(1) -- 7

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1)  -- 8
  progress_clock_by_beats(1/4)  -- 8.25

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  
  progress_clock_by_beats(1) -- 9.25

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1)  -- 10.25
  progress_clock_by_beats(1/2)  -- 10.75

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  
  progress_clock_by_beats(1) -- 11.75

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1)  -- 12.5
  progress_clock_by_beats(3/4)  -- 13.25

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 14.25

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(2) 

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end



function test_chord_strum_param_lock_with_minus_one_acceleration()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 1
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

  channel.trig_lock_params[5].id = "chord_strum"
  channel.trig_lock_params[6].id = "chord_spread"
  channel.trig_lock_params[7].id = "chord_acceleration"
  channel.trig_lock_params[7].cc_min_value = -5

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1
  program.add_step_param_trig_lock(test_step, 6, 5) -- 1/4
  program.add_step_param_trig_lock(test_step, 7, -1)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60) -- 0!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(3/4) -- 0.75

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62) -- 0.75!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2/4) -- 1.25

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64) -- 1.25!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1/4) -- 1.5

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)  -- 1.5!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)  -- 1.5!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)


end



function test_chord_strum_param_lock_with_minus_two_acceleration()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 1
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

  channel.trig_lock_params[5].id = "chord_strum"
  channel.trig_lock_params[6].id = "chord_spread"
  channel.trig_lock_params[7].id = "chord_acceleration"
  channel.trig_lock_params[7].cc_min_value = -5

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1
  program.add_step_param_trig_lock(test_step, 6, 3) -- 1/8
  program.add_step_param_trig_lock(test_step, 7, -2)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60) -- 0!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(3/4) -- 0.75

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62) -- 0.75!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2/4) -- 1.25

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64) -- 1.25!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1/4) -- 1.5

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)  -- 1.5!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)  -- 1.5!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)


end




function test_chord_strum_param_lock_with_four_acceleration()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 1
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

  channel.trig_lock_params[5].id = "chord_strum"
  channel.trig_lock_params[6].id = "chord_spread"
  channel.trig_lock_params[7].id = "chord_acceleration"
  channel.trig_lock_params[7].cc_min_value = -5

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1
  program.add_step_param_trig_lock(test_step, 6, 5) -- 1/4
  program.add_step_param_trig_lock(test_step, 7, 4)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60) -- 0!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 1
  progress_clock_by_beats(1) -- 1

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62) -- 2!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 3
  progress_clock_by_beats(2) -- 5

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64) -- 5!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 6
  progress_clock_by_beats(3) -- 9

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)  -- 9!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 10
  progress_clock_by_beats(4) -- 14

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)  -- 14!
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)


end


function test_chord_arp_param_lock_with_minus_one_acceleration()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 1
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 16
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"
  channel.trig_lock_params[6].id = "chord_spread"
  channel.trig_lock_params[7].id = "chord_acceleration"
  channel.trig_lock_params[7].cc_min_value = -5

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1
  program.add_step_param_trig_lock(test_step, 6, 5) -- 1/4
  program.add_step_param_trig_lock(test_step, 7, -1)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(3/4)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2/4)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64) 
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1/4)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1/4)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end




function test_chord_arp_param_lock_with_two_acceleration()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 1
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 10
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_arp"
  channel.trig_lock_params[6].id = "chord_spread"
  channel.trig_lock_params[7].id = "chord_acceleration"
  channel.trig_lock_params[7].cc_min_value = -5

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 17) -- 1
  program.add_step_param_trig_lock(test_step, 6, 3) -- 1/8
  program.add_step_param_trig_lock(test_step, 7, 2)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)

  pattern_controller.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)
  progress_clock_by_beats(2/8)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)
  progress_clock_by_beats(4/8) -- 2 6/8

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64) 
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 3 6/8
  progress_clock_by_beats(6/8) -- 4 2/8

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1) -- 5 2/8
  progress_clock_by_beats(1) -- 6 2/8

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2) -- 8 2/8
  progress_clock_by_beats(2/8) -- 8 4/8

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2) -- 10 4/8
  progress_clock_by_beats(4/8) -- 11 2/8

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end
