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
  
    -- channel.trig_lock_params[1].type = "trig_probability"
    channel.trig_lock_params[1].id = "trig_probability"
  
    program.add_step_param_trig_lock(test_step, 1, probability)
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()
  
    -- Reset and set up the clock and MIDI event tracking
    clock_setup()
  
    progress_clock_by_beats(test_step)
  
    local note_on_event = table.remove(midi_note_on_events)

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
  
    -- channel.trig_lock_params[1].type = "trig_probability"
    channel.trig_lock_params[1].id = "trig_probability"
  
    program.add_step_param_trig_lock(test_step, 1, probability)
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[c].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()
  
    -- Reset and set up the clock and MIDI event tracking
    clock_setup()
  
    progress_clock_by_beats(test_step)
  
    local note_on_event = table.remove(midi_note_on_events)

    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  
  end

  -- function test_quantised_fixed_note_param_lock()

  -- end

  -- function test_bipolar_random_note_param_lock()

  -- end

  -- function test_twos_random_note_param_lock()

  -- end

  -- function test_random_velocity_param_lock()

  -- end


  -- function test_fixed_note_param_lock()

  -- end

  -- function test_chord_with_one_extra_note_param_lock()

  -- end