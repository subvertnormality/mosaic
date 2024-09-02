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

  test_pattern.note_values[2] = 1
  test_pattern.lengths[2] = 1
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 21

  test_pattern.note_values[3] = 2
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 22

  test_pattern.note_values[4] = 3
  test_pattern.lengths[4] = 1
  test_pattern.trig_values[4] = 1
  test_pattern.velocity_values[4] = 23

  test_pattern.note_values[5] = 0
  test_pattern.lengths[5] = 1
  test_pattern.trig_values[5] = 1
  test_pattern.velocity_values[5] = 24

  test_pattern.note_values[6] = 1
  test_pattern.lengths[6] = 1
  test_pattern.trig_values[6] = 1
  test_pattern.velocity_values[6] = 25

  test_pattern.note_values[7] = 2
  test_pattern.lengths[7] = 1
  test_pattern.trig_values[7] = 1
  test_pattern.velocity_values[7] = 26

  test_pattern.note_values[8] = 3
  test_pattern.lengths[8] = 1
  test_pattern.trig_values[8] = 1
  test_pattern.velocity_values[8] = 27

  test_pattern.note_values[9] = 0
  test_pattern.lengths[9] = 1
  test_pattern.trig_values[9] = 1
  test_pattern.velocity_values[9] = 28

  test_pattern.note_values[10] = 1
  test_pattern.lengths[10] = 1
  test_pattern.trig_values[10] = 1
  test_pattern.velocity_values[10] = 29

  test_pattern.note_values[11] = 2
  test_pattern.lengths[11] = 1
  test_pattern.trig_values[11] = 1
  test_pattern.velocity_values[11] = 30

  test_pattern.note_values[12] = 3
  test_pattern.lengths[12] = 1
  test_pattern.trig_values[12] = 1
  test_pattern.velocity_values[12] = 31

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).swing = 22

  pattern_controller.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60) -- ON: 0
  luaunit.assert_equals(note_on_event[2], 20)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(24) -- (1)
  
  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 60) -- OFF: 1
  luaunit.assert_equals(note_off_event[2], 20)
  luaunit.assert_equals(note_off_event[3], 1)

  progress_clock_by_pulses(5) -- (1 5/24)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62) -- ON: 1 5/24
  luaunit.assert_equals(note_on_event[2], 21)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(19)  -- (2)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 62) -- OFF: 2
  luaunit.assert_equals(note_off_event[2], 21)
  luaunit.assert_equals(note_off_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64) -- ON: 2
  luaunit.assert_equals(note_on_event[2], 22)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(13) -- (2 13/24)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 64) -- OFF: 2 13/24
  luaunit.assert_equals(note_off_event[2], 22)
  luaunit.assert_equals(note_off_event[3], 1)

  progress_clock_by_pulses(16)  -- (3 5/24)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65) -- ON: 3 5/24
  luaunit.assert_equals(note_on_event[2], 23)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(19)  -- (4)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 65) --OFF:  4
  luaunit.assert_equals(note_off_event[2], 23)
  luaunit.assert_equals(note_off_event[3], 1)


  progress_clock_by_pulses(0)  -- (4)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60) -- ON: 4
  luaunit.assert_equals(note_on_event[2], 24)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(13) -- (4 13/24)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 60) -- OFF: 4 13/24
  luaunit.assert_equals(note_off_event[2], 24)
  luaunit.assert_equals(note_off_event[3], 1)

  progress_clock_by_pulses(16)  -- (5 5/24)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62) -- ON: 5 5/24
  luaunit.assert_equals(note_on_event[2], 25)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(19)  -- (6)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 62) -- OFF: 6
  luaunit.assert_equals(note_off_event[2], 25)
  luaunit.assert_equals(note_off_event[3], 1)

  progress_clock_by_pulses(0)  -- (6)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64) -- ON: 6
  luaunit.assert_equals(note_on_event[2], 26)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(13) -- (6 13/24)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 64) -- OFF: 6 13/24
  luaunit.assert_equals(note_off_event[2], 26)
  luaunit.assert_equals(note_off_event[3], 1)

  progress_clock_by_pulses(16)  -- (7 5/24)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65) -- ON: 7 5/24
  luaunit.assert_equals(note_on_event[2], 27)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(19)  -- (8)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 65) -- OFF: 8
  luaunit.assert_equals(note_off_event[2], 27)
  luaunit.assert_equals(note_off_event[3], 1)

  progress_clock_by_pulses(0)  -- (8)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60) -- ON: 8
  luaunit.assert_equals(note_on_event[2], 28)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(13) -- (8 13/24)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 60) -- OFF: 8 13/24
  luaunit.assert_equals(note_off_event[2], 28)
  luaunit.assert_equals(note_off_event[3], 1)

  progress_clock_by_pulses(16)  -- (9 5/24)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62) -- ON: 9 5/24
  luaunit.assert_equals(note_on_event[2], 29)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(19)  -- (10)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 62) -- OFF: 10
  luaunit.assert_equals(note_off_event[2], 29)
  luaunit.assert_equals(note_off_event[3], 1)
  


end
