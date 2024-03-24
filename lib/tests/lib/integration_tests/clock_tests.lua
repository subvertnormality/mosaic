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


function test_swing_maintains_lengths_step_two()
  local test_pattern
  
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[2] = 0
  test_pattern.lengths[2] = 2
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 20

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).swing = 70

  pattern_controller.update_working_patterns()

  clock_setup()

  progress_clock_by_beats(1)
  progress_clock_by_pulses(9)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 20)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)
  
  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 20)
  luaunit.assert_equals(note_off_event[3], 1)

end


function test_swing_maintains_lengths_across_multiple_steps()
  local test_pattern
  
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 20

  test_pattern.note_values[2] = 0
  test_pattern.lengths[2] = 1
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 21

  test_pattern.note_values[3] = 0
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 22

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).swing = 54

  pattern_controller.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 20)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)
  
  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 20)
  luaunit.assert_equals(note_off_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  -- Check there are no note on events
  luaunit.assertNil(note_on_event)

  progress_clock_by_pulses(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 21)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(23)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 22)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(1)

  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 21)
  luaunit.assert_equals(note_off_event[3], 1)

  progress_clock_by_pulses(23)

  local note_off_event = table.remove(midi_note_off_events)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 22)
  luaunit.assert_equals(note_off_event[3], 1)

end
