-- README "Trig Parameters": a trig lock overrides the parameter's value on its step;
-- steps without a lock use the default value. For norns/nb device parameters
-- (param type "norns") Mosaic sets the norns parameter and restores it afterwards.
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

local function progress_clock_by_beats(b)
  for i = 1, (24 * b) do
    m_clock.get_clock_lattice():pulse()
  end
end

local function norns_lock_setup(channel_number)
  program.init()
  globals.reset()
  params.reset()
  norns_param_state_handler = include("mosaic/lib/devices/norns_param_state_handler")
  norns_param_state_handler.flush_norns_original_param_trig_lock_store()
  params:add("test_norns_target", {name = "target", val = 10})
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  for s = 8, 9 do
    test_pattern.note_values[s] = 0
    test_pattern.lengths[s] = 1
    test_pattern.trig_values[s] = 1
    test_pattern.velocity_values[s] = 100
  end
  program.get().selected_channel = channel_number
  local channel = program.get_selected_channel()
  channel.trig_lock_params[1].device_name = "test"
  channel.trig_lock_params[1].type = "norns"
  channel.trig_lock_params[1].id = "test_norns_target"
  channel.trig_lock_params[1].param_id = "test_norns_target"
  program.add_step_param_trig_lock(8, 1, 77)
  program.get_song_pattern(1).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(1).channels[channel_number].selected_patterns, 1)
  pattern.update_working_patterns()
  m_clock.init()
  m_clock:start()
end

function test_norns_parameter_step_lock_applies_on_its_step_then_default_returns()
  norns_lock_setup(1)
  progress_clock_by_beats(7)
  luaunit.assert_equals(params:get("test_norns_target"), 77)
  progress_clock_by_beats(1)
  luaunit.assert_equals(params:get("test_norns_target"), 10)
end

function test_norns_parameter_step_locks_on_two_channels_restore_their_own_defaults()
  norns_lock_setup(3)
  params:add("test_norns_other", {name = "other", val = 40})
  local other = program.get_channel(1, 5)
  other.trig_lock_params[1].device_name = "test"
  other.trig_lock_params[1].type = "norns"
  other.trig_lock_params[1].id = "test_norns_other"
  other.trig_lock_params[1].param_id = "test_norns_other"
  program.add_step_param_trig_lock_to_channel(other, 8, 1, 99)
  program.get_song_pattern(1).channels[5].selected_patterns = {}
  fn.add_to_set(program.get_song_pattern(1).channels[5].selected_patterns, 1)
  pattern.update_working_patterns()
  progress_clock_by_beats(7)
  luaunit.assert_equals(params:get("test_norns_target"), 77)
  luaunit.assert_equals(params:get("test_norns_other"), 99)
  progress_clock_by_beats(1)
  luaunit.assert_equals(params:get("test_norns_target"), 10)
  luaunit.assert_equals(params:get("test_norns_other"), 40)
end
