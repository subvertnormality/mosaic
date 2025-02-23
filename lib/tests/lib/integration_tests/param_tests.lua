step = include("mosaic/lib/step")
pattern = include("mosaic/lib/pattern")

local m_clock = include("mosaic/lib/clock/m_clock")
local quantiser = include("mosaic/lib/quantiser")

-- Mocks
include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/norns_mock")
include("mosaic/lib/tests/helpers/mocks/channel_sequence_page_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_mock")

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
  m_clock.init()
  m_clock:start()
end

local function progress_clock_by_beats(b)
  for i = 1, (24 * b) do
    m_clock.get_clock_lattice():pulse()
  end
end

local function progress_clock_by_pulses(p)
  for i = 1, p do
    m_clock.get_clock_lattice():pulse()
  end
end

-- Helper function to compare two events (for equality)
local function events_equal(event1, event2)
  return event1[1] == event2[1] and event1[2] == event2[2] and event1[3] == event2[3]
end

-- Helper function to check if a set of events contains a specific event
local function contains_event(events, target_event)
  for _, event in ipairs(events) do
      if events_equal(event, target_event) then
          return true
      end
  end
  return false
end

function test_params_trig_locks_are_processed_at_the_right_step()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local cc_value = 111
  local c = 1

  local my_param_id = "my_param_id"

  params:add(my_param_id, {
    name = "name",
    val = -1
  })

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].device_name = "test"
  channel.trig_lock_params[1].type = "midi"
  channel.trig_lock_params[1].id = 1
  channel.trig_lock_params[1].param_id = my_param_id
  channel.trig_lock_params[1].cc_msb = cc_msb
  channel.trig_lock_params[1].cc_min_value = -1 
  channel.trig_lock_params[1].cc_max_value = 127

  program.add_step_param_trig_lock(test_step, 1, cc_value)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value, 1})
  
end
  

function test_params_triggless_locks_are_processed_at_the_right_step()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local cc_value = 111
  local c = 1

  local my_param_id = "my_param_id"

  params:add(my_param_id, {
    name = "name",
    val = -1
  })

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
  channel.trig_lock_params[1].param_id = my_param_id
  channel.trig_lock_params[1].cc_msb = cc_msb
  channel.trig_lock_params[1].cc_min_value = -1 
  channel.trig_lock_params[1].cc_max_value = 127

  params:set("trigless_locks", 2) 

  program.add_step_param_trig_lock(test_step, 1, cc_value)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value, 1})

end


function test_params_triggless_locks_are_not_processed_if_trigless_param_is_off()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local cc_value = 111
  local c = 1

  local my_param_id = "my_param_id"

  params:add(my_param_id, {
    name = "name",
    val = -1
  })

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
  channel.trig_lock_params[1].param_id = my_param_id
  channel.trig_lock_params[1].cc_msb = cc_msb
  channel.trig_lock_params[1].cc_min_value = -1 
  channel.trig_lock_params[1].cc_max_value = 127

  params:set("trigless_locks", 0) 

  program.add_step_param_trig_lock(test_step, 1, cc_value)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_not_equals(midi_cc_event[2], 111)

end


function test_trig_probability_param_lock_trigs_when_probability_is_high_enough() 
  setup()
  mock_random()

  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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

  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end


function test_trig_probability_param_lock_set_to_zero_doesnt_fire() 
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end

function test_trig_probability_param_lock_set_to_one_hundred_fires() 
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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

  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end



function test_bipolar_random_note_param_lock_channel_16_slot_10()

  setup()
  mock_random()

  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local shift = 1
  local c = 16

  test_pattern.note_values[test_step] = 1
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c


  local channel = program.get_selected_channel()


  channel.trig_lock_params[10].id = "bipolar_random_note"

  program.add_step_param_trig_lock(test_step, 10, shift)

  program.get_song_pattern(song_pattern).patterns[16] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 16)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end

function test_param_trig_locks_for_channel_16_slot_10()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local cc_value = 111
  local c = 16

  local my_param_id = "my_param_id"

  params:add(my_param_id, {
    name = "name",
    val = -1
  })

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[10].device_name = "test"
  channel.trig_lock_params[10].type = "midi"
  channel.trig_lock_params[10].id = 1
  channel.trig_lock_params[10].param_id = my_param_id
  channel.trig_lock_params[10].cc_msb = cc_msb
  channel.trig_lock_params[10].cc_min_value = -1 
  channel.trig_lock_params[10].cc_max_value = 127

  program.add_step_param_trig_lock(test_step, 10, cc_value)

  program.get_song_pattern(song_pattern).patterns[16] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 16)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value, 1})
end

function test_param_trig_locks_for_channel_15_slot_9()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local cc_value = 111
  local c = 15

  local my_param_id = "my_param_id"

  params:add(my_param_id, {
    name = "name",
    val = -1
  })

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[9].device_name = "test"
  channel.trig_lock_params[9].type = "midi"
  channel.trig_lock_params[9].id = 1
  channel.trig_lock_params[9].param_id = my_param_id
  channel.trig_lock_params[9].cc_msb = cc_msb
  channel.trig_lock_params[9].cc_min_value = -1 
  channel.trig_lock_params[9].cc_max_value = 127

  program.add_step_param_trig_lock(test_step, 9, cc_value)

  program.get_song_pattern(song_pattern).patterns[15] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 15)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value, 1})
end



function test_bipolar_random_note_param_lock_using_norns_param_rather_than_trig_param()

  setup()
  mock_random()

  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  params:set("midi_device_params_channel_1_4", shift)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end

function test_trig_probability_param_lock_channel_16()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local probability = 100
  local c = 16

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[10].id = "trig_probability"

  program.add_step_param_trig_lock(test_step, 10, probability)

  program.get_song_pattern(song_pattern).patterns[16] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 16)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end

function test_random_velocity_param_lock_channel_14_slot_8()
  setup()
  mock_random()

  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local c = 14

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 30

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[8].id = "random_velocity"

  program.add_step_param_trig_lock(test_step, 8, 10)

  program.get_song_pattern(song_pattern).patterns[14] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 14)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 40)
  luaunit.assert_equals(note_on_event[3], 1)
end

function test_bipolar_random_note_param_lock_when_pentatonic_option_is_selected()

  setup()
  mock_random()

  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local scale = quantiser.get_scales()[1]

  local test_step = 1
  local cc_msb = 2
  local shift = 1
  local c = 1

  local param_id = "bipolar_random_note"

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

  params:add(param_id, {
    name = "",
    val = -1
  })

  params:set("all_scales_lock_to_pentatonic", 1)
  params:set("random_lock_to_pentatonic", 2)

  program.add_step_param_trig_lock(test_step, 1, shift)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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

  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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

  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1

  program.add_step_scale_trig_lock(1, 1)
  program.add_step_scale_trig_lock(3, 2)
  program.add_step_scale_trig_lock(4, 3)
  program.add_step_scale_trig_lock(5, 1)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 34)  -- 8

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(1, 5, 14)  -- 1
  program.add_step_param_trig_lock(1, 6, 2) -- Backwards pattern

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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


function test_chord_strum_param_lock_with_inside_out_strum_pattern_with_note_mask()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  program.get_song_pattern(song_pattern).channels[c].step_note_masks[1] = 60
  program.get_song_pattern(song_pattern).channels[c].step_trig_masks[1] = 1
  program.get_song_pattern(song_pattern).channels[c].step_velocity_masks[1] = 100
  program.get_song_pattern(song_pattern).channels[c].step_length_masks[1] = 8

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  channel.trig_lock_params[5].id = "chord_strum"
  channel.trig_lock_params[6].id = "chord_strum_pattern"

  channel.step_chord_masks[1] = {}
  channel.step_chord_masks[1][1] = chord_note_1
  channel.step_chord_masks[1][2] = chord_note_2
  channel.step_chord_masks[1][3] = chord_note_3
  channel.step_chord_masks[1][4] = chord_note_4
  program.add_step_param_trig_lock(1, 5, 14)  -- 1
  program.add_step_param_trig_lock(1, 6, 3) -- Inside out strum pattern

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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


function test_chord_strum_param_lock_with_inside_out_strum_pattern()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(1, 5, 14)  -- 1
  program.add_step_param_trig_lock(1, 6, 3) -- Inside out strum pattern

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(1, 5, 14)  -- 1
  program.add_step_param_trig_lock(1, 6, 4) -- Outside in strum pattern

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local test_step_2 = 10
  local test_step_3 = 15

  local cc_msb = 2
  local cc_value = 111
  local c = 1
  local my_param_id = "my_param_id"

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

  params:add(my_param_id, {
    name = "param",
    val = -1
  })

  channel.trig_lock_params[1].device_name = "test"
  channel.trig_lock_params[1].type = "midi"
  channel.trig_lock_params[1].id = 1
  channel.trig_lock_params[1].param_id = my_param_id
  channel.trig_lock_params[1].cc_msb = cc_msb
  channel.trig_lock_params[1].cc_min_value = -1 
  channel.trig_lock_params[1].cc_max_value = 127
  params:set(my_param_id, cc_value)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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

  params:set(my_param_id, cc_value + 1)
  
  progress_clock_by_beats(test_step_3 - test_step_2)
  
  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value + 1, 1})


end





function test_global_params_are_processed_with_the_correct_value_across_song_patterns()
  setup()
  local song_pattern_1 = 1
  local song_pattern_2 = 2
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2
  local c = 1

  local cc_value_1 = 111
  local cc_value_2 = 112

  local my_param_id = "my_param_id"
  local my_param_id_2 = "my_param_id_2"

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  program.get_song_pattern(song_pattern_1).patterns[1] = test_pattern

  local channel_song_pattern_1 = program.get_song_pattern(song_pattern_1).channels[c]

  params:add(my_param_id, {
    name = "param",
    val = -1
  })

  channel_song_pattern_1.trig_lock_params[1].device_name = "test"
  channel_song_pattern_1.trig_lock_params[1].type = "midi"
  channel_song_pattern_1.trig_lock_params[1].id = 1
  channel_song_pattern_1.trig_lock_params[1].param_id = my_param_id
  channel_song_pattern_1.trig_lock_params[1].cc_msb = cc_msb
  channel_song_pattern_1.trig_lock_params[1].cc_min_value = -1 
  channel_song_pattern_1.trig_lock_params[1].cc_max_value = 127

  params:set(my_param_id, cc_value_1)

  fn.add_to_set(program.get_song_pattern(song_pattern_1).channels[c].selected_patterns, 1)

  local test_pattern_2 = program.initialise_default_pattern()

  local song_pattern_2_cc_value = 112

  test_pattern_2.note_values[test_step] = 0
  test_pattern_2.lengths[test_step] = 1
  test_pattern_2.trig_values[test_step] = 1
  test_pattern_2.velocity_values[test_step] = 100

  program.get_song_pattern(song_pattern_2).patterns[1] = test_pattern_2

  local channel_song_pattern_2 = program.get_song_pattern(song_pattern_2).channels[c]

  channel_song_pattern_2.trig_lock_params[1].device_name = "test"
  channel_song_pattern_2.trig_lock_params[1].type = "midi"
  channel_song_pattern_2.trig_lock_params[1].id = 1
  channel_song_pattern_2.trig_lock_params[1].param_id = my_param_id_2
  channel_song_pattern_2.trig_lock_params[1].cc_msb = cc_msb
  channel_song_pattern_2.trig_lock_params[1].cc_min_value = -1 
  channel_song_pattern_2.trig_lock_params[1].cc_max_value = 127
  params:set(my_param_id_2, cc_value_2)
  
  fn.add_to_set(program.get_song_pattern(song_pattern_2).channels[c].selected_patterns, 1)

  program.set_selected_song_pattern(song_pattern_1)
  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()
  local midi_cc_event = table.remove(midi_cc_events)
  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value_1, 1}) -- CC is fired at start of pattern to reset value to default

  progress_clock_by_beats(test_step - 1)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value_1, 1})

  program.set_selected_song_pattern(song_pattern_2)
  pattern.update_working_patterns()

  progress_clock_by_beats(64) -- get to next pattern

  progress_clock_by_beats(test_step - 1)

  local midi_cc_event = table.remove(midi_cc_events)

  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value_2, 1})

end

function test_arp_param_lock_with_four_extra_notes()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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


function test_arp_param_lock_on_note_mask_with_four_extra_notes()
  setup()
  
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1


  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  program.get_song_pattern(song_pattern).channels[c].step_note_masks[test_step] = 77
  program.get_song_pattern(song_pattern).channels[c].step_trig_masks[test_step] = 1
  program.get_song_pattern(song_pattern).channels[c].step_velocity_masks[test_step] = 100
  program.get_song_pattern(song_pattern).channels[c].step_length_masks[test_step] = 8

  channel.trig_lock_params[5].id = "chord_arp"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 77)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 79)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 81)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 83)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 84)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 77)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 79)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 81)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end

function test_arp_param_lock_with_four_extra_notes_divison()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 18) -- 2

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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


function test_arp_param_lock_with_four_extra_notes_fraction()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 0.51
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
  program.add_step_param_trig_lock(test_step, 5, 3) -- 1/8

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_nil(note_off_event)
  -- TODO figure out why this isn't working any more
  progress_clock_by_pulses(3)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(3)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 62)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(3)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 64)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(3)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 65)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(3)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 67)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end

function test_arp_param_lock_adheres_to_scale_changes()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 18) -- 2

  program.add_step_scale_trig_lock(1, 1)
  program.add_step_scale_trig_lock(3, 2)
  program.add_step_scale_trig_lock(5, 3)
  program.add_step_scale_trig_lock(7, 1)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(1, 5, 14)  -- 1
  program.add_step_param_trig_lock(1, 6, 2) -- Backwards pattern

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(1, 5, 14)  -- 1
  program.add_step_param_trig_lock(1, 6, 3) -- Inside out strum pattern

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(1, 5, 14)  -- 1
  program.add_step_param_trig_lock(1, 6, 4) -- Outside in strum pattern

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(1, 5, 14)  -- 1
  program.add_step_param_trig_lock(1, 6, 4) -- Outside in strum pattern

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(1, 5, 14)  -- 1

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(1, 5, 14)  -- 1

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1
  program.add_step_param_trig_lock(test_step, 6, 5) -- 1/4

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1
  program.add_step_param_trig_lock(test_step, 6, 5) -- 1/4

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1
  program.add_step_param_trig_lock(test_step, 6, 5) -- 1/4
  program.add_step_param_trig_lock(test_step, 7, -1)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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

  -- Collect the actual events
  local actual_events = {}
  table.insert(actual_events, table.remove(midi_note_on_events, 1))
  table.insert(actual_events, table.remove(midi_note_on_events, 1))

  -- Define the expected events (without assuming any order)
  local expected_event_1 = {65, 100, 1}  -- 1.5!
  local expected_event_2 = {67, 100, 1}  -- 1.5!

  -- Assert that both expected events are present in actual events
  luaunit.assert_true(contains_event(actual_events, expected_event_1), "Expected event 1 not found")
  luaunit.assert_true(contains_event(actual_events, expected_event_2), "Expected event 2 not found")


end



function test_chord_strum_param_lock_with_minus_two_acceleration()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1
  program.add_step_param_trig_lock(test_step, 6, 3) -- 1/8
  program.add_step_param_trig_lock(test_step, 7, -2)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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

  -- Collect the actual events
  local actual_events = {}
  table.insert(actual_events, table.remove(midi_note_on_events, 1))
  table.insert(actual_events, table.remove(midi_note_on_events, 1))

  -- Define the expected events (without assuming any order)
  local expected_event_1 = {65, 100, 1}  -- 1.5!
  local expected_event_2 = {67, 100, 1}  -- 1.5!

  -- Assert that both expected events are present in actual events
  luaunit.assert_true(contains_event(actual_events, expected_event_1), "Expected event 1 not found")
  luaunit.assert_true(contains_event(actual_events, expected_event_2), "Expected event 2 not found")


end




function test_chord_strum_param_lock_with_four_acceleration()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1
  program.add_step_param_trig_lock(test_step, 6, 5) -- 1/4
  program.add_step_param_trig_lock(test_step, 7, 4)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1
  program.add_step_param_trig_lock(test_step, 6, 5) -- 1/4
  program.add_step_param_trig_lock(test_step, 7, -1)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1
  program.add_step_param_trig_lock(test_step, 6, 3) -- 1/8
  program.add_step_param_trig_lock(test_step, 7, 2)

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

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

function test_chord_with_root_note_muted()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 1
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  -- Set up param to mute root note
  channel.trig_lock_params[4].id = "mute_root_note"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  program.add_step_param_trig_lock(test_step, 4, 1) -- Enable root note muting

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  -- Should not get root note event
  local note_on_event = table.remove(midi_note_on_events, 1)

  -- First note should be the first chord note (E)
  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  -- Second note should be the second chord note (G)
  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  -- Third note should be the third chord note (A)
  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  -- Should be no more notes
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_nil(note_on_event)
end

function test_chord_arp_with_root_note_muted()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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
  channel.trig_lock_params[4].id = "mute_root_note"
  

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  program.add_step_param_trig_lock(test_step, 5, 14) -- 1
  program.add_step_param_trig_lock(test_step, 4, 1) -- Enable root note muting

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)

  progress_clock_by_beats(test_step - 1)

  -- Should not get root note event
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_nil(note_on_event)

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

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

end

function test_chord_strum_with_root_note_muted()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 4
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  -- Set up both chord strum and root note muting
  channel.trig_lock_params[4].id = "mute_root_note"
  channel.trig_lock_params[5].id = "chord_strum"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  
  program.add_step_param_trig_lock(test_step, 4, 1) -- Enable root note muting
  program.add_step_param_trig_lock(test_step, 5, 14) -- Standard strum division

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  -- Should not get root note event
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1)

  -- First note should be the first chord note (E)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  -- Second note should be the second chord note (G)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  -- Third note should be the third chord note (A)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  -- No more notes after pattern length
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_nil(note_on_event)
end

function test_chord_strum_arp_with_root_note_muted()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local cc_msb = 2

  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 5
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c

  local channel = program.get_selected_channel()

  -- Set up chord strum, arp and root note muting
  channel.trig_lock_params[4].id = "mute_root_note"
  channel.trig_lock_params[6].id = "chord_arp"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  
  program.add_step_param_trig_lock(test_step, 4, 1) -- Enable root note muting
  program.add_step_param_trig_lock(test_step, 6, 14) -- Standard arp division

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)

  pattern.update_working_patterns()

  -- Reset and set up the clock and MIDI event tracking
  clock_setup()

  progress_clock_by_pulses(1)
  progress_clock_by_beats(test_step - 1)

  -- Should not get root note event
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_nil(note_on_event)

  progress_clock_by_beats(1)

  -- First note should be the first chord note (E)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)


  -- Second note should be the second chord note (G)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  -- Third note should be the third chord note (A)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)


  -- Should loop back to first chord note
  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  -- No more notes after pattern length
  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_nil(note_on_event)
end

function test_chord_strum_with_root_note_muted_and_outside_in_pattern()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local chord_note_1 = 1
  local chord_note_2 = 2
  local chord_note_3 = 3
  local chord_note_4 = 4
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 4
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c
  local channel = program.get_selected_channel()

  -- Set up chord strum, root muting, and outside-in pattern
  channel.trig_lock_params[4].id = "mute_root_note"
  channel.trig_lock_params[5].id = "chord_strum"
  channel.trig_lock_params[6].id = "chord_strum_pattern"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  
  program.add_step_param_trig_lock(test_step, 4, 1) -- Enable root note muting
  program.add_step_param_trig_lock(test_step, 5, 14) -- Standard strum division
  program.add_step_param_trig_lock(test_step, 6, 3) -- Outside-in pattern

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)
  pattern.update_working_patterns()
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  -- Should not get root note event
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_nil(note_on_event)

  -- Should get outer notes first (due to outside-in pattern)
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62) -- A (chord_note_3)

  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 67) -- B (chord_note_4)

  -- Then inner notes
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 64) -- E (chord_note_1)

  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65) -- G (chord_note_2)

  -- No more notes
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_nil(note_on_event)
end

function test_chord_with_root_note_muted_and_empty_slots()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)
  local test_pattern = program.initialise_default_pattern()

  local test_step = 8
  local chord_note_1 = 1
  local chord_note_2 = 0  -- Empty slot
  local chord_note_3 = 3
  local chord_note_4 = 0  -- Empty slot
  local c = 1

  test_pattern.note_values[test_step] = 0
  test_pattern.lengths[test_step] = 4
  test_pattern.trig_values[test_step] = 1
  test_pattern.velocity_values[test_step] = 100

  program.get().selected_channel = c
  local channel = program.get_selected_channel()

  channel.trig_lock_params[4].id = "mute_root_note"

  channel.step_chord_masks[test_step] = {}
  channel.step_chord_masks[test_step][1] = chord_note_1
  channel.step_chord_masks[test_step][2] = chord_note_2
  channel.step_chord_masks[test_step][3] = chord_note_3
  channel.step_chord_masks[test_step][4] = chord_note_4
  
  program.add_step_param_trig_lock(test_step, 4, 1) -- Enable root note muting

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[c].selected_patterns, 1)
  pattern.update_working_patterns()
  clock_setup()

  progress_clock_by_beats(test_step - 1)

  -- Should get only the non-empty, non-root notes
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62) -- E (chord_note_1)

  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65) -- A (chord_note_3)

  -- No more notes (empty slots should be skipped)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_nil(note_on_event)
end

function test_param_locks_fire_on_first_step_when_transitioning_song_patterns()
  setup()
  local song_pattern_1 = 1
  local song_pattern_2 = 2
  program.set_selected_song_pattern(song_pattern_1)
  
  -- Set up first pattern
  local test_pattern_1 = program.initialise_default_pattern()
  local cc_msb = 2
  local cc_value_1 = 111
  local c = 1

  local my_param_id = "my_param_id"

  params:add(my_param_id, {
    name = "name",
    val = -1
  })

  -- Configure first step of first pattern
  test_pattern_1.note_values[1] = 0
  test_pattern_1.lengths[1] = 1
  test_pattern_1.trig_values[1] = 1
  test_pattern_1.velocity_values[1] = 100

  program.get().selected_channel = c
  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].device_name = "test"
  channel.trig_lock_params[1].type = "midi"
  channel.trig_lock_params[1].id = 1
  channel.trig_lock_params[1].param_id = my_param_id
  channel.trig_lock_params[1].cc_msb = cc_msb
  channel.trig_lock_params[1].cc_min_value = -1 
  channel.trig_lock_params[1].cc_max_value = 127

  program.add_step_param_trig_lock(1, 1, cc_value_1)

  -- Set up second pattern
  program.set_selected_song_pattern(song_pattern_2)
  local test_pattern_2 = program.initialise_default_pattern()
  local cc_value_2 = 122

  -- Configure first step of second pattern
  test_pattern_2.note_values[1] = 0
  test_pattern_2.lengths[1] = 1
  test_pattern_2.trig_values[1] = 1
  test_pattern_2.velocity_values[1] = 100

  -- Add patterns to song patterns
  program.get_song_pattern(song_pattern_1).patterns[1] = test_pattern_1
  program.get_song_pattern(song_pattern_2).patterns[1] = test_pattern_2
  
  fn.add_to_set(program.get_song_pattern(song_pattern_1).channels[c].selected_patterns, 1)
  fn.add_to_set(program.get_song_pattern(song_pattern_2).channels[c].selected_patterns, 1)

  -- Set up second pattern's param lock
  local channel_song_pattern_2 = program.get_song_pattern(song_pattern_2).channels[c]
  channel_song_pattern_2.trig_lock_params[1].device_name = "test"
  channel_song_pattern_2.trig_lock_params[1].type = "midi"
  channel_song_pattern_2.trig_lock_params[1].id = 1
  channel_song_pattern_2.trig_lock_params[1].param_id = my_param_id
  channel_song_pattern_2.trig_lock_params[1].cc_msb = cc_msb
  channel_song_pattern_2.trig_lock_params[1].cc_min_value = -1 
  channel_song_pattern_2.trig_lock_params[1].cc_max_value = 127

  program.add_step_param_trig_lock_to_channel(channel_song_pattern_2, 1, 1, cc_value_2)

  -- Enable song mode and activate both patterns
  params:set("song_mode", 2)
  program.get_song_pattern(song_pattern_1).active = true
  program.get_song_pattern(song_pattern_2).active = true

  -- Start from first pattern
  program.set_selected_song_pattern(song_pattern_1)
  pattern.update_working_patterns()

  -- Set up clock and start playback
  clock_setup()

  -- Check first pattern's param lock fires
  local midi_cc_event = table.remove(midi_cc_events)
  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value_1, 1})

  -- Progress to end of first pattern
  progress_clock_by_beats(64)

  -- Check second pattern's param lock fires
  local midi_cc_event = table.remove(midi_cc_events)
  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value_2, 1})
end

function test_param_locks_fire_on_first_step_when_song_mode_off()
  setup()
  local song_pattern_1 = 1
  local song_pattern_2 = 2
  program.set_selected_song_pattern(song_pattern_1)
  
  -- Set up first pattern
  local test_pattern_1 = program.initialise_default_pattern()
  local cc_msb = 2
  local cc_value_1 = 111
  local c = 1

  local my_param_id = "my_param_id"

  params:add(my_param_id, {
    name = "name",
    val = -1
  })

  -- Configure first step of first pattern
  test_pattern_1.note_values[1] = 0
  test_pattern_1.lengths[1] = 1
  test_pattern_1.trig_values[1] = 1
  test_pattern_1.velocity_values[1] = 100

  program.get().selected_channel = c
  local channel = program.get_selected_channel()

  channel.trig_lock_params[1].device_name = "test"
  channel.trig_lock_params[1].type = "midi"
  channel.trig_lock_params[1].id = 1
  channel.trig_lock_params[1].param_id = my_param_id
  channel.trig_lock_params[1].cc_msb = cc_msb
  channel.trig_lock_params[1].cc_min_value = -1 
  channel.trig_lock_params[1].cc_max_value = 127

  program.add_step_param_trig_lock(1, 1, cc_value_1)

  -- Set up second pattern
  program.set_selected_song_pattern(song_pattern_2)
  local test_pattern_2 = program.initialise_default_pattern()
  local cc_value_2 = 122

  -- Configure first step of second pattern
  test_pattern_2.note_values[1] = 0
  test_pattern_2.lengths[1] = 1
  test_pattern_2.trig_values[1] = 1
  test_pattern_2.velocity_values[1] = 100

  -- Add patterns to song patterns
  program.get_song_pattern(song_pattern_1).patterns[1] = test_pattern_1
  program.get_song_pattern(song_pattern_2).patterns[1] = test_pattern_2
  
  fn.add_to_set(program.get_song_pattern(song_pattern_1).channels[c].selected_patterns, 1)
  fn.add_to_set(program.get_song_pattern(song_pattern_2).channels[c].selected_patterns, 1)

  -- Set up second pattern's param lock
  local channel_song_pattern_2 = program.get_song_pattern(song_pattern_2).channels[c]
  channel_song_pattern_2.trig_lock_params[1].device_name = "test"
  channel_song_pattern_2.trig_lock_params[1].type = "midi"
  channel_song_pattern_2.trig_lock_params[1].id = 1
  channel_song_pattern_2.trig_lock_params[1].param_id = my_param_id
  channel_song_pattern_2.trig_lock_params[1].cc_msb = cc_msb
  channel_song_pattern_2.trig_lock_params[1].cc_min_value = -1 
  channel_song_pattern_2.trig_lock_params[1].cc_max_value = 127

  program.add_step_param_trig_lock_to_channel(channel_song_pattern_2, 1, 1, cc_value_2)

  -- Enable song mode and activate both patterns
  params:set("song_mode", 1)
  program.get_song_pattern(song_pattern_1).active = true
  program.get_song_pattern(song_pattern_2).active = true

  -- Start from first pattern
  program.set_selected_song_pattern(song_pattern_1)
  pattern.update_working_patterns()

  -- Set up clock and start playback
  clock_setup()

  -- Check first pattern's param lock fires
  local midi_cc_event = table.remove(midi_cc_events)
  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value_1, 1})

  -- Progress to end of first pattern
  progress_clock_by_beats(64)

  -- Check second pattern's param lock fires
  local midi_cc_event = table.remove(midi_cc_events)
  luaunit.assert_items_equals(midi_cc_event, {cc_msb, cc_value_1, 1})
end
