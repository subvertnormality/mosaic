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

function test_clock_divisions_slow_down_the_clock_div_2()

  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[2] = 0
  test_pattern.lengths[2] = 2
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern

  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  pattern.update_working_patterns()

  clock_setup()

  local div_2_clock_mod = m_clock.calculate_divisor(m_clock.get_clock_divisions()[15])

  m_clock.set_channel_division(1, div_2_clock_mod)

  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(1)

  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)
  luaunit.assertNil(note_off_event)
  progress_clock_by_beats(1)
  luaunit.assertNil(note_off_event)
  progress_clock_by_beats(1)
  luaunit.assertNil(note_off_event)
  progress_clock_by_beats(1)

  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

end

function test_clock_divisions_slow_down_the_clock_div_3()

  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[2] = 0
  test_pattern.lengths[2] = 2
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern

  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  pattern.update_working_patterns()

  clock_setup()

  local div_3_clock_mod = m_clock.calculate_divisor(m_clock.get_clock_divisions()[17])

  m_clock.set_channel_division(1, div_3_clock_mod)

  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(1)
  progress_clock_by_beats(1)

  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)
  luaunit.assertNil(note_off_event)
  progress_clock_by_beats(1)
  luaunit.assertNil(note_off_event)
  progress_clock_by_beats(1)
  luaunit.assertNil(note_off_event)
  progress_clock_by_beats(1)
  luaunit.assertNil(note_off_event)
  progress_clock_by_beats(1)
  luaunit.assertNil(note_off_event)
  progress_clock_by_beats(1)
  
  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

end

function test_clock_multiplications_speed_up_the_clock_mul_2()

  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[2] = 0
  test_pattern.lengths[2] = 2
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern

  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  pattern.update_working_patterns()

  clock_setup()

  local mul_2_clock_mod = m_clock.calculate_divisor(m_clock.get_clock_divisions()[10])

  m_clock.set_channel_division(1, mul_2_clock_mod)

  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(1)

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


function test_clock_multiplications_speed_up_the_clock_mul_4()

  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[16] = 0
  test_pattern.lengths[16] = 32
  test_pattern.trig_values[16] = 1
  test_pattern.velocity_values[16] = 100

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern

  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  pattern.update_working_patterns()

  clock_setup()

  local mul_8_clock_mod = m_clock.calculate_divisor(m_clock.get_clock_divisions()[7])

  m_clock.set_channel_division(1, mul_8_clock_mod)

  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(4)
  -- progress_clock_by_pulses(12)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(8)

  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

end


function test_clock_multiplications_speed_up_the_clock_mul_8()

  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[16] = 0
  test_pattern.lengths[16] = 32
  test_pattern.trig_values[16] = 1
  test_pattern.velocity_values[16] = 100

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern

  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  pattern.update_working_patterns()

  clock_setup()

  local mul_8_clock_mod = m_clock.calculate_divisor(m_clock.get_clock_divisions()[3])

  m_clock.set_channel_division(1, mul_8_clock_mod)

  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(1)
  -- progress_clock_by_beats(1)

  progress_clock_by_pulses(24)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)
  progress_clock_by_beats(1)
  progress_clock_by_beats(1)
  progress_clock_by_beats(1)

  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 100)
  luaunit.assert_equals(note_off_event[3], 1)

end

function test_clock_multiplications_speed_up_the_clock_mul_16()

  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[16] = 0
  test_pattern.lengths[16] = 32
  test_pattern.trig_values[16] = 1
  test_pattern.velocity_values[16] = 100

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern

  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  pattern.update_working_patterns()

  clock_setup()

  local mul_16_clock_mod = m_clock.calculate_divisor(m_clock.get_clock_divisions()[1])

  m_clock.set_channel_division(1, mul_16_clock_mod)

  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(1)
  -- progress_clock_by_pulses(14) -- incorrect TODO: fix this

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)
  progress_clock_by_beats(1)

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

  local clock_division = 1
  local delay_multiplier = 1


  m_clock.delay_action(
    channel,
    ((clock_division * delay_multiplier)),
    false,
    function()
      has_fired = true
    end
  )

  luaunit.assert_false(has_fired)

  progress_clock_by_beats(4)
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

  m_clock.delay_action(
    channel,
    (clock_division_index * delay_multiplier),
    false,
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

  m_clock.delay_action(
    channel,
    nil,
    false,
    function()
      has_fired = true
    end
  )

  luaunit.assert_true(has_fired)

end


function test_clock_can_delay_action_with_channel_clock_division_set()

  setup()
  clock_setup()
  progress_clock_by_beats(1)
  local mul_8_clock_mod = m_clock.calculate_divisor(m_clock.get_clock_divisions()[3])

  m_clock.set_channel_division(1, mul_8_clock_mod)

  local has_fired = false

  local channel = 1

  local division = 1
  local delay_multiplier = 1

  m_clock.delay_action(
    channel,
    (division * delay_multiplier),
    false,
    function()
      has_fired = true
    end
  )

  luaunit.assert_false(has_fired)

  progress_clock_by_pulses(13)

  luaunit.assert_true(has_fired)

end


function test_delay_action_with_full_delay_fires_as_expected()

  setup()
  clock_setup()

  local has_fired = false

  local channel = 1

  local clock_division = 1
  local delay_multiplier = 1

  m_clock.delay_action(
    channel,
    (clock_division * delay_multiplier),
    false,
    function()
      has_fired = true
    end
  )

  progress_clock_by_pulses(24)
  progress_clock_by_pulses(2) -- we need at least one pulse to trigger the meta action and one for the action

  luaunit.assert_true(has_fired)

end




function test_execute_action_across_steps_works_with_normal_clock()
  setup()
  clock_setup()

  local values = {}
  m_clock.execute_action_across_steps_by_pulses({
    channel_number = 1,
    trig_lock = 1,
    start_step = 1,
    end_step = 4,
    start_value = 0,
    end_value = 127,
    func = function(val)
      table.insert(values, math.floor(val))
    end
  })

  progress_clock_by_pulses(96) -- One full beat (24 pulses) per step, 4 steps total
  
  -- Should have ~96 values transitioning from 0 to 127
  luaunit.assert_equals(#values, 96)
  luaunit.assert_equals(values[1], 0)
  luaunit.assert_equals(values[#values], 127)
end

function test_execute_action_across_steps_works_with_clock_division()
  setup()
  clock_setup()
  
  local div_2_clock_mod = m_clock.calculate_divisor(m_clock.get_clock_divisions()[15])
  m_clock.set_channel_division(1, div_2_clock_mod)

  local values = {}
  m_clock.execute_action_across_steps_by_pulses({
    channel_number = 1,
    trig_lock = 1,
    start_step = 1,
    end_step = 4,
    start_value = 0,
    end_value = 100,
    func = function(val)
      table.insert(values, math.floor(val))
    end
  })

  progress_clock_by_pulses(192) -- Two beats per step with div 2
  
  -- Should have ~192 values transitioning from 0 to 100
  luaunit.assert_equals(#values, 192)
  luaunit.assert_equals(values[1], 0)
  luaunit.assert_equals(values[#values], 100)
end

function test_cancel_spread_actions_for_channel()
  setup()
  clock_setup()

  local values = {}
  local values_count_before_cancel
  
  m_clock.execute_action_across_steps_by_pulses({
    channel_number = 1,
    trig_lock = 1,
    start_step = 1,
    end_step = 4,
    start_value = 0,
    end_value = 127,
    func = function(val)
      table.insert(values, math.floor(val))
    end
  })

  -- Progress halfway
  progress_clock_by_pulses(48)
  values_count_before_cancel = #values
  
  -- Cancel and try to progress more
  m_clock.cancel_spread_actions_for_channel_trig_lock(1, 1)
  progress_clock_by_pulses(48)
  
  -- Verify:
  luaunit.assert_true(values_count_before_cancel > 0)
  luaunit.assert_equals(values[1], 0)
  luaunit.assert_true(values[#values] < 127)
end

function test_spread_actions_handle_shuffle()
  setup()
  clock_setup()
  
  local channel = program.get_channel(program.get().selected_song_pattern, 1)
  channel.shuffle_amount = 50 -- Set moderate shuffle
  channel.swing_shuffle_type = 2
  channel.shuffle_feel = 1
  
  local values = {}
  m_clock.execute_action_across_steps_by_pulses({
    channel_number = 1,
    trig_lock = 1,
    start_step = 1,
    end_step = 3,
    start_value = 0,
    end_value = 127,
    func = function(val)
      table.insert(values, math.floor(val))
    end
  })

  progress_clock_by_pulses(96)
  
  -- Should still complete the transition with shuffle
  luaunit.assert_equals(values[1], 0)
  luaunit.assert_equals(values[#values], 127)
end