-- The pulse-advance lock lead contract, driven through the real clock.
--
-- Under this contract a step's parameter values leave in an earlier pulse than
-- the step, and the note keeps the timing it has at lead 0. The previous
-- contract achieved its lead the other way round, by delaying the note behind
-- the locks, which is what put note dispatch part way through a step.
step = include("mosaic/lib/step")
pattern = include("mosaic/lib/pattern")

local m_clock = include("mosaic/lib/clock/m_clock")

include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/norns_mock")
include("mosaic/lib/tests/helpers/mocks/channel_sequence_page_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_mock")

local CC_MSB, CC_VALUE, TEST_STEP = 2, 111, 8

local function setup()
  program.init()
  globals.reset()
  params.reset()
  m_clock.set_lock_contract("legacy-delay-v1")
end

local function build_locked_channel()
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  params:add("lookahead_param", {name = "name", val = -1})
  for step_number = 1, 16 do
    test_pattern.note_values[step_number] = 0
    test_pattern.lengths[step_number] = 1
    test_pattern.trig_values[step_number] = 1
    test_pattern.velocity_values[step_number] = 100
  end
  program.get().selected_channel = 1
  local channel = program.get_selected_channel()
  channel.trig_lock_params[1].device_name = "test"
  channel.trig_lock_params[1].type = "midi"
  channel.trig_lock_params[1].id = 1
  channel.trig_lock_params[1].param_id = "lookahead_param"
  channel.trig_lock_params[1].cc_msb = CC_MSB
  channel.trig_lock_params[1].cc_min_value = -1
  channel.trig_lock_params[1].cc_max_value = 127
  program.add_step_param_trig_lock(TEST_STEP, 1, CC_VALUE)
  program.get_song_pattern(1).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(1).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()
end

local function run_pulses(count)
  for _ = 1, count do m_clock.get_clock_lattice():pulse() end
end

local function find(kind, value)
  for _, event in ipairs(midi_event_log) do
    if event.kind == kind and event.a == value then return event end
  end
end

local function count(kind, value)
  local total = 0
  for _, event in ipairs(midi_event_log) do
    if event.kind == kind and event.a == value then total = total + 1 end
  end
  return total
end

function test_pulse_advance_sends_a_locked_value_before_its_own_step()
  setup()
  build_locked_channel()
  m_midi.set_lead_time(25)
  m_clock.set_lock_contract("pulse-advance")
  m_clock.init()
  m_clock:start()
  run_pulses(24 * TEST_STEP)

  local value = find("cc", CC_MSB)
  luaunit.assert_not_nil(value, "the locked value must be sent")
  luaunit.assert_equals(value.b, CC_VALUE)

  -- The note of the locked step is the last note on or before that step.
  local note
  for _, event in ipairs(midi_event_log) do
    if event.kind == "note_on" and event.pulse >= value.pulse then
      note = event
      break
    end
  end
  luaunit.assert_not_nil(note, "the locked step must still sound")
  luaunit.assert_true(value.pulse < note.pulse,
    string.format("value left on pulse %d, note on pulse %d", value.pulse, note.pulse))
end

function test_pulse_advance_sends_each_locked_value_exactly_once()
  setup()
  build_locked_channel()
  m_midi.set_lead_time(25)
  m_clock.set_lock_contract("pulse-advance")
  m_clock.init()
  m_clock:start()
  run_pulses(24 * TEST_STEP)
  -- Sending early and then again at the step would double every locked value.
  luaunit.assert_equals(count("cc", CC_MSB), 1)
end

function test_legacy_contract_still_sends_the_value_at_its_own_step()
  setup()
  build_locked_channel()
  m_midi.set_lead_time(25)
  m_clock.set_lock_contract("legacy-delay-v1")
  m_clock.init()
  m_clock:start()
  run_pulses(24 * TEST_STEP)

  local value = find("cc", CC_MSB)
  luaunit.assert_not_nil(value)
  local note
  for _, event in ipairs(midi_event_log) do
    if event.kind == "note_on" and event.pulse >= value.pulse then
      note = event
      break
    end
  end
  -- The existing contract resolves the value on the step's own pulse.
  luaunit.assert_equals(value.pulse, note.pulse)
  luaunit.assert_equals(count("cc", CC_MSB), 1)
end

function test_pulse_advance_at_lead_zero_keeps_the_value_on_its_own_step()
  setup()
  build_locked_channel()
  m_midi.set_lead_time(0)
  m_clock.set_lock_contract("pulse-advance")
  m_clock.init()
  m_clock:start()
  run_pulses(24 * TEST_STEP)

  local value = find("cc", CC_MSB)
  luaunit.assert_not_nil(value)
  local note
  for _, event in ipairs(midi_event_log) do
    if event.kind == "note_on" and event.pulse >= value.pulse then
      note = event
      break
    end
  end
  luaunit.assert_equals(value.pulse, note.pulse)
  luaunit.assert_equals(count("cc", CC_MSB), 1)
end
