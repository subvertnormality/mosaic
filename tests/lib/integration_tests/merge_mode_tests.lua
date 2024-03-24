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

function test_trig_merge_modes_skip()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local step_to_skip = 1
  local step_to_play = 4
  local step_to_play_2 = 11
  local step_to_skip_2 = 34
  local step_to_play_3 = 45
  local step_to_skip_3 = 64

  test_pattern.note_values[step_to_skip] = 0
  test_pattern.lengths[step_to_skip] = 1
  test_pattern.trig_values[step_to_skip] = 1
  test_pattern.velocity_values[step_to_skip] = 100

  test_pattern.note_values[step_to_skip_2] = 0
  test_pattern.lengths[step_to_skip_2] = 1
  test_pattern.trig_values[step_to_skip_2] = 1
  test_pattern.velocity_values[step_to_skip_2] = 100

  test_pattern.note_values[step_to_play] = 0
  test_pattern.lengths[step_to_play] = 1
  test_pattern.trig_values[step_to_play] = 1
  test_pattern.velocity_values[step_to_play] = 100

  test_pattern.note_values[step_to_play_2] = 1
  test_pattern.lengths[step_to_play_2] = 1
  test_pattern.trig_values[step_to_play_2] = 1
  test_pattern.velocity_values[step_to_play_2] = 100

  test_pattern.note_values[step_to_skip_3] = 0
  test_pattern.lengths[step_to_skip_3] = 1
  test_pattern.trig_values[step_to_skip_3] = 1
  test_pattern.velocity_values[step_to_skip_3] = 100

  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[step_to_skip] = 0
  test_pattern_2.lengths[step_to_skip] = 1
  test_pattern_2.trig_values[step_to_skip] = 1
  test_pattern_2.velocity_values[step_to_skip] = 100

  test_pattern_2.note_values[step_to_skip_2] = 0
  test_pattern_2.lengths[step_to_skip_2] = 1
  test_pattern_2.trig_values[step_to_skip_2] = 1
  test_pattern_2.velocity_values[step_to_skip_2] = 100

  test_pattern_2.note_values[step_to_play_3] = 3
  test_pattern_2.lengths[step_to_play_3] = 1
  test_pattern_2.trig_values[step_to_play_3] = 1
  test_pattern_2.velocity_values[step_to_play_3] = 100


  local test_pattern_3 = program.initialise_default_pattern()

  test_pattern_3.note_values[step_to_play_2] = 0
  test_pattern_3.lengths[step_to_play_2] = 1
  test_pattern_3.trig_values[step_to_play_2] = 1
  test_pattern_3.velocity_values[step_to_play_2] = 100

  local test_pattern_4 = program.initialise_default_pattern()

  test_pattern_4.note_values[step_to_skip_3] = 0
  test_pattern_4.lengths[step_to_skip_3] = 1
  test_pattern_4.trig_values[step_to_skip_3] = 1
  test_pattern_4.velocity_values[step_to_skip_3] = 100


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "skip"

  pattern_controller.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  -- Check there are no note on events for skipped step 1
  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(step_to_play - step_to_skip)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(step_to_play_2 - step_to_play)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(step_to_skip_2 - step_to_play_2)

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  -- Check there are no note on events for skipped step 34
  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(step_to_play_3 - step_to_skip_2)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(step_to_skip_3 - step_to_play_3)

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  -- Check there are no note on events for skipped step 64
  luaunit.assertNil(note_on_event)

end


function test_trig_merge_modes_only()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local step_to_play = 1
  local step_to_skip = 4
  local step_to_skip_2 = 11
  local step_to_skip_4 = 34
  local step_to_skip_3 = 45
  local step_to_play_2 = 64

  test_pattern.note_values[step_to_play] = 0
  test_pattern.lengths[step_to_play] = 1
  test_pattern.trig_values[step_to_play] = 1
  test_pattern.velocity_values[step_to_play] = 100

  test_pattern.note_values[step_to_skip_4] = 1
  test_pattern.lengths[step_to_skip_4] = 1
  test_pattern.trig_values[step_to_skip_4] = 1
  test_pattern.velocity_values[step_to_skip_4] = 100

  test_pattern.note_values[step_to_play_2] = 3
  test_pattern.lengths[step_to_play_2] = 1
  test_pattern.trig_values[step_to_play_2] = 1
  test_pattern.velocity_values[step_to_play_2] = 100

  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[step_to_play] = 0
  test_pattern_2.lengths[step_to_play] = 1
  test_pattern_2.trig_values[step_to_play] = 1
  test_pattern_2.velocity_values[step_to_play] = 100

  test_pattern_2.note_values[step_to_skip] = 0
  test_pattern_2.lengths[step_to_skip] = 1
  test_pattern_2.trig_values[step_to_skip] = 1
  test_pattern_2.velocity_values[step_to_skip] = 100

  test_pattern_2.note_values[step_to_skip_2] = 0
  test_pattern_2.lengths[step_to_skip_2] = 1
  test_pattern_2.trig_values[step_to_skip_2] = 1
  test_pattern_2.velocity_values[step_to_skip_2] = 100

  test_pattern_2.note_values[step_to_play_2] = 3
  test_pattern_2.lengths[step_to_play_2] = 1
  test_pattern_2.trig_values[step_to_play_2] = 1
  test_pattern_2.velocity_values[step_to_play_2] = 100


  local test_pattern_3 = program.initialise_default_pattern()

  test_pattern_3.note_values[step_to_skip_4] = 0
  test_pattern_3.lengths[step_to_skip_4] = 1
  test_pattern_3.trig_values[step_to_skip_4] = 1
  test_pattern_3.velocity_values[step_to_skip_4] = 100

  local test_pattern_4 = program.initialise_default_pattern()

  test_pattern_4.note_values[step_to_skip_3] = 0
  test_pattern_4.lengths[step_to_skip_3] = 1
  test_pattern_4.trig_values[step_to_skip_3] = 1
  test_pattern_4.velocity_values[step_to_skip_3] = 100


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "only"

  pattern_controller.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(step_to_skip - step_to_play)

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  -- Check there are no note on events for skipped step 4
  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(step_to_skip_2 - step_to_skip)

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  -- Check there are no note on events for skipped step 4
  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(step_to_skip_4 - step_to_skip_2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(step_to_skip_3 - step_to_skip_4)

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  -- Check there are no note on events for skipped step 45
  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(step_to_play_2 - step_to_skip_3)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_trig_merge_modes_all()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local step_to_play = 1
  local step_to_play_2 = 4
  local step_to_play_3 = 11
  local step_to_play_4 = 34
  local step_to_play_5 = 45
  local step_to_play_6 = 64

  test_pattern.note_values[step_to_play] = 0
  test_pattern.lengths[step_to_play] = 1
  test_pattern.trig_values[step_to_play] = 1
  test_pattern.velocity_values[step_to_play] = 100

  test_pattern.note_values[step_to_play_2] = 1
  test_pattern.lengths[step_to_play_2] = 1
  test_pattern.trig_values[step_to_play_2] = 1
  test_pattern.velocity_values[step_to_play_2] = 100

  test_pattern.note_values[step_to_play_3] = 2
  test_pattern.lengths[step_to_play_3] = 1
  test_pattern.trig_values[step_to_play_3] = 1
  test_pattern.velocity_values[step_to_play_3] = 100

  test_pattern.note_values[step_to_play_4] = 3
  test_pattern.lengths[step_to_play_4] = 1
  test_pattern.trig_values[step_to_play_4] = 1
  test_pattern.velocity_values[step_to_play_4] = 100

  test_pattern.note_values[step_to_play_5] = 4
  test_pattern.lengths[step_to_play_5] = 1
  test_pattern.trig_values[step_to_play_5] = 1
  test_pattern.velocity_values[step_to_play_5] = 100

  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[step_to_play_3] = 2
  test_pattern_2.lengths[step_to_play_3] = 1
  test_pattern_2.trig_values[step_to_play_3] = 1
  test_pattern_2.velocity_values[step_to_play_3] = 100

  test_pattern_2.note_values[step_to_play_4] = 3
  test_pattern_2.lengths[step_to_play_4] = 1
  test_pattern_2.trig_values[step_to_play_4] = 1
  test_pattern_2.velocity_values[step_to_play_4] = 100

  test_pattern_2.note_values[step_to_play_6] = 5
  test_pattern_2.lengths[step_to_play_6] = 1
  test_pattern_2.trig_values[step_to_play_6] = 1
  test_pattern_2.velocity_values[step_to_play_6] = 100


  local test_pattern_3 = program.initialise_default_pattern()

  test_pattern_3.note_values[step_to_play_6] = 5
  test_pattern_3.lengths[step_to_play_6] = 1
  test_pattern_3.trig_values[step_to_play_6] = 1
  test_pattern_3.velocity_values[step_to_play_6] = 100

  local test_pattern_4 = program.initialise_default_pattern()

  test_pattern_4.note_values[step_to_play_4] = 3
  test_pattern_4.lengths[step_to_play_4] = 1
  test_pattern_4.trig_values[step_to_play_4] = 1
  test_pattern_4.velocity_values[step_to_play_4] = 100


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "all"

  pattern_controller.update_working_patterns()

  clock_setup()
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(step_to_play_2 - step_to_play)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(step_to_play_3 - step_to_play_2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(step_to_play_4 - step_to_play_3)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(step_to_play_5 - step_to_play_4)

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(step_to_play_6 - step_to_play_5)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 69)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end

function test_note_merge_modes_up()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local none_merged_step_to_play = 1
  local none_merged_step_to_play_2 = 4
  local merged_step_to_play_3 = 11
  local twice_merged_step_to_play_4 = 34
  local none_merged_step_to_play_5 = 45
  local twice_merged_step_to_play_6 = 64

  test_pattern.note_values[none_merged_step_to_play] = 0
  test_pattern.lengths[none_merged_step_to_play] = 1
  test_pattern.trig_values[none_merged_step_to_play] = 1
  test_pattern.velocity_values[none_merged_step_to_play] = 100

  test_pattern.note_values[none_merged_step_to_play_2] = 1
  test_pattern.lengths[none_merged_step_to_play_2] = 1
  test_pattern.trig_values[none_merged_step_to_play_2] = 1
  test_pattern.velocity_values[none_merged_step_to_play_2] = 100

  test_pattern.note_values[merged_step_to_play_3] = 1
  test_pattern.lengths[merged_step_to_play_3] = 1
  test_pattern.trig_values[merged_step_to_play_3] = 1
  test_pattern.velocity_values[merged_step_to_play_3] = 100

  test_pattern.note_values[twice_merged_step_to_play_4] = 3
  test_pattern.lengths[twice_merged_step_to_play_4] = 1
  test_pattern.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern.note_values[none_merged_step_to_play_5] = 4
  test_pattern.lengths[none_merged_step_to_play_5] = 1
  test_pattern.trig_values[none_merged_step_to_play_5] = 1
  test_pattern.velocity_values[none_merged_step_to_play_5] = 100

  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[merged_step_to_play_3] = 2
  test_pattern_2.lengths[merged_step_to_play_3] = 1
  test_pattern_2.trig_values[merged_step_to_play_3] = 1
  test_pattern_2.velocity_values[merged_step_to_play_3] = 100

  test_pattern_2.note_values[twice_merged_step_to_play_4] = 1
  test_pattern_2.lengths[twice_merged_step_to_play_4] = 1
  test_pattern_2.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern_2.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern_2.note_values[twice_merged_step_to_play_6] = 2
  test_pattern_2.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_2.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_2.velocity_values[twice_merged_step_to_play_6] = 100


  local test_pattern_3 = program.initialise_default_pattern()

  test_pattern_3.note_values[twice_merged_step_to_play_6] = 5
  test_pattern_3.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_3.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 100

  local test_pattern_4 = program.initialise_default_pattern()

  test_pattern_4.note_values[twice_merged_step_to_play_4] = 6
  test_pattern_4.lengths[twice_merged_step_to_play_4] = 1
  test_pattern_4.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern_4.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern_3.note_values[twice_merged_step_to_play_6] = 7
  test_pattern_3.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_3.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 100


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 3)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).note_merge_mode = "up"

  pattern_controller.update_working_patterns()

  clock_setup()
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_2 - none_merged_step_to_play)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(merged_step_to_play_3 - none_merged_step_to_play_2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_4 - merged_step_to_play_3)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 74)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_5 - twice_merged_step_to_play_4)

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_6 - none_merged_step_to_play_5)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 77)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end

function test_note_merge_modes_pattern_number_1()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local none_merged_step_to_play = 1
  local none_merged_step_to_play_2 = 4
  local merged_step_to_play_3 = 11
  local twice_merged_step_to_play_4 = 34
  local none_merged_step_to_play_5 = 45
  local twice_merged_step_to_play_6 = 64

  test_pattern.note_values[none_merged_step_to_play] = 0
  test_pattern.lengths[none_merged_step_to_play] = 1
  test_pattern.trig_values[none_merged_step_to_play] = 1
  test_pattern.velocity_values[none_merged_step_to_play] = 100

  test_pattern.note_values[none_merged_step_to_play_2] = 1
  test_pattern.lengths[none_merged_step_to_play_2] = 1
  test_pattern.trig_values[none_merged_step_to_play_2] = 1
  test_pattern.velocity_values[none_merged_step_to_play_2] = 100

  test_pattern.note_values[merged_step_to_play_3] = 1
  test_pattern.lengths[merged_step_to_play_3] = 1
  test_pattern.trig_values[merged_step_to_play_3] = 1
  test_pattern.velocity_values[merged_step_to_play_3] = 100

  test_pattern.note_values[twice_merged_step_to_play_4] = 3
  test_pattern.lengths[twice_merged_step_to_play_4] = 1
  test_pattern.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern.note_values[none_merged_step_to_play_5] = 4
  test_pattern.lengths[none_merged_step_to_play_5] = 1
  test_pattern.trig_values[none_merged_step_to_play_5] = 1
  test_pattern.velocity_values[none_merged_step_to_play_5] = 100

  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[merged_step_to_play_3] = 2
  test_pattern_2.lengths[merged_step_to_play_3] = 1
  test_pattern_2.trig_values[merged_step_to_play_3] = 1
  test_pattern_2.velocity_values[merged_step_to_play_3] = 100

  test_pattern_2.note_values[twice_merged_step_to_play_4] = 1
  test_pattern_2.lengths[twice_merged_step_to_play_4] = 1
  test_pattern_2.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern_2.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern_2.note_values[twice_merged_step_to_play_6] = 2
  test_pattern_2.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_2.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_2.velocity_values[twice_merged_step_to_play_6] = 100


  local test_pattern_3 = program.initialise_default_pattern()

  test_pattern_3.note_values[twice_merged_step_to_play_6] = 5
  test_pattern_3.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_3.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 100

  local test_pattern_4 = program.initialise_default_pattern()

  test_pattern_4.note_values[twice_merged_step_to_play_4] = 6
  test_pattern_4.lengths[twice_merged_step_to_play_4] = 1
  test_pattern_4.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern_4.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern_3.note_values[twice_merged_step_to_play_6] = 7
  test_pattern_3.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_3.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 100


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 3)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).note_merge_mode = "pattern_number_1"

  pattern_controller.update_working_patterns()

  clock_setup()
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_2 - none_merged_step_to_play)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(merged_step_to_play_3 - none_merged_step_to_play_2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_4 - merged_step_to_play_3)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_5 - twice_merged_step_to_play_4)

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_6 - none_merged_step_to_play_5)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_note_merge_modes_pattern_number_1_takes_note_value_from_pattern_even_when_theres_no_trig()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local none_merged_step_to_play = 1
  local none_merged_step_to_play_2 = 4
  local merged_step_to_play_3 = 11
  local twice_merged_step_to_play_4 = 34
  local none_merged_step_to_play_5 = 45
  local twice_merged_step_to_play_6 = 64

  test_pattern.note_values[none_merged_step_to_play] = 0
  test_pattern.lengths[none_merged_step_to_play] = 1
  test_pattern.trig_values[none_merged_step_to_play] = 1
  test_pattern.velocity_values[none_merged_step_to_play] = 100

  test_pattern.note_values[none_merged_step_to_play_2] = 1
  test_pattern.lengths[none_merged_step_to_play_2] = 1
  test_pattern.trig_values[none_merged_step_to_play_2] = 1
  test_pattern.velocity_values[none_merged_step_to_play_2] = 100

  test_pattern.note_values[merged_step_to_play_3] = 1
  test_pattern.lengths[merged_step_to_play_3] = 1
  test_pattern.trig_values[merged_step_to_play_3] = 0
  test_pattern.velocity_values[merged_step_to_play_3] = 100

  test_pattern.note_values[twice_merged_step_to_play_4] = 3
  test_pattern.lengths[twice_merged_step_to_play_4] = 1
  test_pattern.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern.note_values[none_merged_step_to_play_5] = 4
  test_pattern.lengths[none_merged_step_to_play_5] = 1
  test_pattern.trig_values[none_merged_step_to_play_5] = 1
  test_pattern.velocity_values[none_merged_step_to_play_5] = 100

  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[merged_step_to_play_3] = 2
  test_pattern_2.lengths[merged_step_to_play_3] = 1
  test_pattern_2.trig_values[merged_step_to_play_3] = 1
  test_pattern_2.velocity_values[merged_step_to_play_3] = 100

  test_pattern_2.note_values[twice_merged_step_to_play_4] = 1
  test_pattern_2.lengths[twice_merged_step_to_play_4] = 1
  test_pattern_2.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern_2.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern_2.note_values[twice_merged_step_to_play_6] = 2
  test_pattern_2.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_2.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_2.velocity_values[twice_merged_step_to_play_6] = 100


  local test_pattern_3 = program.initialise_default_pattern()

  test_pattern_3.note_values[twice_merged_step_to_play_6] = 5
  test_pattern_3.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_3.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 100

  local test_pattern_4 = program.initialise_default_pattern()

  test_pattern_4.note_values[twice_merged_step_to_play_4] = 6
  test_pattern_4.lengths[twice_merged_step_to_play_4] = 1
  test_pattern_4.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern_4.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern_3.note_values[twice_merged_step_to_play_6] = 7
  test_pattern_3.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_3.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 100


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 3)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).note_merge_mode = "pattern_number_1"

  pattern_controller.update_working_patterns()

  clock_setup()
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_2 - none_merged_step_to_play)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(merged_step_to_play_3 - none_merged_step_to_play_2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_4 - merged_step_to_play_3)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_5 - twice_merged_step_to_play_4)

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_6 - none_merged_step_to_play_5)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_note_merge_modes_pattern_number_1_takes_note_value_from_pattern_even_when_pattern_is_disabled()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local none_merged_step_to_play = 1
  local none_merged_step_to_play_2 = 4
  local merged_step_to_play_3 = 11
  local twice_merged_step_to_play_4 = 34
  local none_merged_step_to_play_5 = 45
  local twice_merged_step_to_play_6 = 64

  test_pattern.note_values[none_merged_step_to_play] = 0
  test_pattern.lengths[none_merged_step_to_play] = 1
  test_pattern.trig_values[none_merged_step_to_play] = 1
  test_pattern.velocity_values[none_merged_step_to_play] = 100

  test_pattern.note_values[none_merged_step_to_play_2] = 1
  test_pattern.lengths[none_merged_step_to_play_2] = 1
  test_pattern.trig_values[none_merged_step_to_play_2] = 1
  test_pattern.velocity_values[none_merged_step_to_play_2] = 100

  test_pattern.note_values[merged_step_to_play_3] = 1
  test_pattern.lengths[merged_step_to_play_3] = 1
  test_pattern.trig_values[merged_step_to_play_3] = 0
  test_pattern.velocity_values[merged_step_to_play_3] = 100

  test_pattern.note_values[twice_merged_step_to_play_4] = 3
  test_pattern.lengths[twice_merged_step_to_play_4] = 1
  test_pattern.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern.note_values[none_merged_step_to_play_5] = 4
  test_pattern.lengths[none_merged_step_to_play_5] = 1
  test_pattern.trig_values[none_merged_step_to_play_5] = 1
  test_pattern.velocity_values[none_merged_step_to_play_5] = 100

  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[merged_step_to_play_3] = 2
  test_pattern_2.lengths[merged_step_to_play_3] = 1
  test_pattern_2.trig_values[merged_step_to_play_3] = 1
  test_pattern_2.velocity_values[merged_step_to_play_3] = 100

  test_pattern_2.note_values[twice_merged_step_to_play_4] = 1
  test_pattern_2.lengths[twice_merged_step_to_play_4] = 1
  test_pattern_2.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern_2.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern_2.note_values[twice_merged_step_to_play_6] = 2
  test_pattern_2.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_2.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_2.velocity_values[twice_merged_step_to_play_6] = 100


  local test_pattern_3 = program.initialise_default_pattern()

  test_pattern_3.note_values[twice_merged_step_to_play_6] = 5
  test_pattern_3.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_3.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 100

  local test_pattern_4 = program.initialise_default_pattern()

  test_pattern_4.note_values[twice_merged_step_to_play_4] = 6
  test_pattern_4.lengths[twice_merged_step_to_play_4] = 1
  test_pattern_4.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern_4.velocity_values[twice_merged_step_to_play_4] = 100

  test_pattern_3.note_values[twice_merged_step_to_play_6] = 7
  test_pattern_3.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_3.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 100


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  -- fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 3)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).note_merge_mode = "pattern_number_1"

  pattern_controller.update_working_patterns()

  clock_setup()


  progress_clock_by_beats(merged_step_to_play_3)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_4 - merged_step_to_play_3)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_5 - twice_merged_step_to_play_4)

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(twice_merged_step_to_play_6 - none_merged_step_to_play_5)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end


-- test_note_merge_modes_down


-- test_note_merge_modes_average

-- test_velocity_merge_modes_up

-- test_velocity_merge_modes_down

-- test_velocity_merge_modes_average

-- test_length_merge_modes_up

-- test_length_merge_modes_down

-- test_length_merge_modes_average