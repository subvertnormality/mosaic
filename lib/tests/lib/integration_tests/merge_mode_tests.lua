pattern = include("mosaic/lib/pattern")

local clock_controller = include("mosaic/lib/clock/clock_controller")
local quantiser = include("mosaic/lib/quantiser")

-- Mocks
include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
include("mosaic/lib/tests/helpers/mocks/mosaic_midi_mock")
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

  pattern.update_working_patterns()

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

  pattern.update_working_patterns()

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

  pattern.update_working_patterns()

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


function test_trig_mask_stops_steps_trigging()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local step_to_play = 1
  local step_to_play_2 = 4
  local step_to_play_3 = 11
  local step_to_play_skip_due_to_mask = 34
  local step_to_play_5 = 45
  local step_to_play_6 = 64

  program.set_step_trig_mask(1, 34, 0)

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

  test_pattern.note_values[step_to_play_skip_due_to_mask] = 3
  test_pattern.lengths[step_to_play_skip_due_to_mask] = 1
  test_pattern.trig_values[step_to_play_skip_due_to_mask] = 1
  test_pattern.velocity_values[step_to_play_skip_due_to_mask] = 100

  test_pattern.note_values[step_to_play_5] = 4
  test_pattern.lengths[step_to_play_5] = 1
  test_pattern.trig_values[step_to_play_5] = 1
  test_pattern.velocity_values[step_to_play_5] = 100

  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[step_to_play_3] = 2
  test_pattern_2.lengths[step_to_play_3] = 1
  test_pattern_2.trig_values[step_to_play_3] = 1
  test_pattern_2.velocity_values[step_to_play_3] = 100

  test_pattern_2.note_values[step_to_play_skip_due_to_mask] = 3
  test_pattern_2.lengths[step_to_play_skip_due_to_mask] = 1
  test_pattern_2.trig_values[step_to_play_skip_due_to_mask] = 1
  test_pattern_2.velocity_values[step_to_play_skip_due_to_mask] = 100

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

  test_pattern_4.note_values[step_to_play_skip_due_to_mask] = 3
  test_pattern_4.lengths[step_to_play_skip_due_to_mask] = 1
  test_pattern_4.trig_values[step_to_play_skip_due_to_mask] = 1
  test_pattern_4.velocity_values[step_to_play_skip_due_to_mask] = 100


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "all"

  pattern.update_working_patterns()

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

  progress_clock_by_beats(step_to_play_skip_due_to_mask - step_to_play_3)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(step_to_play_5 - step_to_play_skip_due_to_mask)

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



function test_trig_mask_can_force_steps_trigging()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local step_to_play = 1
  local step_to_play_2 = 4
  local step_to_play_3 = 11
  local step_to_play_due_to_mask = 34
  local step_to_play_5 = 45
  local step_to_play_6 = 64

  program.set_step_trig_mask(1, 34, 1)

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

  test_pattern.note_values[step_to_play_due_to_mask] = 3
  test_pattern.lengths[step_to_play_due_to_mask] = 1
  test_pattern.trig_values[step_to_play_due_to_mask] = 0
  test_pattern.velocity_values[step_to_play_due_to_mask] = 100

  test_pattern.note_values[step_to_play_5] = 4
  test_pattern.lengths[step_to_play_5] = 1
  test_pattern.trig_values[step_to_play_5] = 1
  test_pattern.velocity_values[step_to_play_5] = 100

  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[step_to_play_3] = 2
  test_pattern_2.lengths[step_to_play_3] = 1
  test_pattern_2.trig_values[step_to_play_3] = 1
  test_pattern_2.velocity_values[step_to_play_3] = 100

  test_pattern_2.note_values[step_to_play_due_to_mask] = 3
  test_pattern_2.lengths[step_to_play_due_to_mask] = 1
  test_pattern_2.trig_values[step_to_play_due_to_mask] = 0
  test_pattern_2.velocity_values[step_to_play_due_to_mask] = 100

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

  test_pattern_4.note_values[step_to_play_due_to_mask] = 3
  test_pattern_4.lengths[step_to_play_due_to_mask] = 1
  test_pattern_4.trig_values[step_to_play_due_to_mask] = 0
  test_pattern_4.velocity_values[step_to_play_due_to_mask] = 100


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "all"

  pattern.update_working_patterns()

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

  progress_clock_by_beats(step_to_play_due_to_mask - step_to_play_3)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(step_to_play_5 - step_to_play_due_to_mask)

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

  pattern.update_working_patterns()

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

  pattern.update_working_patterns()

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

  pattern.update_working_patterns()

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

  pattern.update_working_patterns()

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

function test_note_merge_modes_down()
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
  program.get_channel(1).note_merge_mode = "down"

  pattern.update_working_patterns()

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

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_4 - merged_step_to_play_3)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 59)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_5 - twice_merged_step_to_play_4)

  local note_on_event = table.remove(midi_note_on_events, 1)
  
  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_6 - none_merged_step_to_play_5)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 59)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end


-- test_note_merge_modes_average

function test_note_merge_modes_average()
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
  program.get_channel(1).note_merge_mode = "average"

  pattern.update_working_patterns()

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

  luaunit.assert_equals(note_on_event[1], 64)
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

  luaunit.assert_equals(note_on_event[1], 69)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_velocity_merge_modes_up()
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
  test_pattern.velocity_values[none_merged_step_to_play] = 50

  test_pattern.note_values[none_merged_step_to_play_2] = 1
  test_pattern.lengths[none_merged_step_to_play_2] = 1
  test_pattern.trig_values[none_merged_step_to_play_2] = 1
  test_pattern.velocity_values[none_merged_step_to_play_2] = 50

  test_pattern.note_values[merged_step_to_play_3] = 1
  test_pattern.lengths[merged_step_to_play_3] = 1
  test_pattern.trig_values[merged_step_to_play_3] = 1
  test_pattern.velocity_values[merged_step_to_play_3] = 50

  test_pattern.note_values[twice_merged_step_to_play_4] = 3
  test_pattern.lengths[twice_merged_step_to_play_4] = 1
  test_pattern.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern.velocity_values[twice_merged_step_to_play_4] = 50

  test_pattern.note_values[none_merged_step_to_play_5] = 4
  test_pattern.lengths[none_merged_step_to_play_5] = 1
  test_pattern.trig_values[none_merged_step_to_play_5] = 1
  test_pattern.velocity_values[none_merged_step_to_play_5] = 50

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
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 120

  local test_pattern_4 = program.initialise_default_pattern()

  test_pattern_4.note_values[twice_merged_step_to_play_4] = 6
  test_pattern_4.lengths[twice_merged_step_to_play_4] = 1
  test_pattern_4.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern_4.velocity_values[twice_merged_step_to_play_4] = 120

  test_pattern_3.note_values[twice_merged_step_to_play_6] = 7
  test_pattern_3.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_3.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 120


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 3)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).velocity_merge_mode = "up"

  pattern.update_working_patterns()

  clock_setup()
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 50)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_2 - none_merged_step_to_play)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 50)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(merged_step_to_play_3 - none_merged_step_to_play_2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 125)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_4 - merged_step_to_play_3)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 127)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_5 - twice_merged_step_to_play_4)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 50)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_6 - none_merged_step_to_play_5)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 69)
  luaunit.assert_equals(note_on_event[2], 127)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_velocity_merge_modes_up()
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
  test_pattern.velocity_values[none_merged_step_to_play] = 50

  test_pattern.note_values[none_merged_step_to_play_2] = 1
  test_pattern.lengths[none_merged_step_to_play_2] = 1
  test_pattern.trig_values[none_merged_step_to_play_2] = 1
  test_pattern.velocity_values[none_merged_step_to_play_2] = 50

  test_pattern.note_values[merged_step_to_play_3] = 1
  test_pattern.lengths[merged_step_to_play_3] = 1
  test_pattern.trig_values[merged_step_to_play_3] = 1
  test_pattern.velocity_values[merged_step_to_play_3] = 50

  test_pattern.note_values[twice_merged_step_to_play_4] = 3
  test_pattern.lengths[twice_merged_step_to_play_4] = 1
  test_pattern.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern.velocity_values[twice_merged_step_to_play_4] = 50

  test_pattern.note_values[none_merged_step_to_play_5] = 4
  test_pattern.lengths[none_merged_step_to_play_5] = 1
  test_pattern.trig_values[none_merged_step_to_play_5] = 1
  test_pattern.velocity_values[none_merged_step_to_play_5] = 50

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
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 120

  local test_pattern_4 = program.initialise_default_pattern()

  test_pattern_4.note_values[twice_merged_step_to_play_4] = 6
  test_pattern_4.lengths[twice_merged_step_to_play_4] = 1
  test_pattern_4.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern_4.velocity_values[twice_merged_step_to_play_4] = 120

  test_pattern_3.note_values[twice_merged_step_to_play_6] = 7
  test_pattern_3.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_3.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 120


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 3)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).velocity_merge_mode = "down"

  pattern.update_working_patterns()

  clock_setup()
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 50)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_2 - none_merged_step_to_play)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 50)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(merged_step_to_play_3 - none_merged_step_to_play_2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 25)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_4 - merged_step_to_play_3)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 10)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_5 - twice_merged_step_to_play_4)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 50)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_6 - none_merged_step_to_play_5)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 69)
  luaunit.assert_equals(note_on_event[2], 90)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_velocity_merge_modes_up()
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
  test_pattern.velocity_values[none_merged_step_to_play] = 50

  test_pattern.note_values[none_merged_step_to_play_2] = 1
  test_pattern.lengths[none_merged_step_to_play_2] = 1
  test_pattern.trig_values[none_merged_step_to_play_2] = 1
  test_pattern.velocity_values[none_merged_step_to_play_2] = 50

  test_pattern.note_values[merged_step_to_play_3] = 1
  test_pattern.lengths[merged_step_to_play_3] = 1
  test_pattern.trig_values[merged_step_to_play_3] = 1
  test_pattern.velocity_values[merged_step_to_play_3] = 50

  test_pattern.note_values[twice_merged_step_to_play_4] = 3
  test_pattern.lengths[twice_merged_step_to_play_4] = 1
  test_pattern.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern.velocity_values[twice_merged_step_to_play_4] = 50

  test_pattern.note_values[none_merged_step_to_play_5] = 4
  test_pattern.lengths[none_merged_step_to_play_5] = 1
  test_pattern.trig_values[none_merged_step_to_play_5] = 1
  test_pattern.velocity_values[none_merged_step_to_play_5] = 50

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
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 120

  local test_pattern_4 = program.initialise_default_pattern()

  test_pattern_4.note_values[twice_merged_step_to_play_4] = 6
  test_pattern_4.lengths[twice_merged_step_to_play_4] = 1
  test_pattern_4.trig_values[twice_merged_step_to_play_4] = 1
  test_pattern_4.velocity_values[twice_merged_step_to_play_4] = 120

  test_pattern_3.note_values[twice_merged_step_to_play_6] = 7
  test_pattern_3.lengths[twice_merged_step_to_play_6] = 1
  test_pattern_3.trig_values[twice_merged_step_to_play_6] = 1
  test_pattern_3.velocity_values[twice_merged_step_to_play_6] = 120


  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  program.get_sequencer_pattern(sequencer_pattern).patterns[4] = test_pattern_4
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 3)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 4)

  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).velocity_merge_mode = "average"

  pattern.update_working_patterns()

  clock_setup()
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 50)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_2 - none_merged_step_to_play)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 50)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(merged_step_to_play_3 - none_merged_step_to_play_2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 75)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_4 - merged_step_to_play_3)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 90)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(none_merged_step_to_play_5 - twice_merged_step_to_play_4)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 50)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(twice_merged_step_to_play_6 - none_merged_step_to_play_5)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 69)
  luaunit.assert_equals(note_on_event[2], 110)
  luaunit.assert_equals(note_on_event[3], 1)

end

function test_trig_merge_modes_with_inactive_patterns()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  
  -- Set up patterns with different trigs
  local test_pattern = program.initialise_default_pattern()
  test_pattern.trig_values[1] = 1
  test_pattern.trig_values[4] = 1
  test_pattern.trig_values[7] = 1
  
  local test_pattern_2 = program.initialise_default_pattern()
  test_pattern_2.trig_values[1] = 1
  test_pattern_2.trig_values[7] = 1
  
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  
  -- Test with only pattern 1 active
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  program.get_channel(1).trig_merge_mode = "skip"
  pattern.update_working_patterns()
  
  clock_setup()
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60)  -- First trig should play
  
  progress_clock_by_beats(3)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60)  -- Second trig should play
  
  -- Enable second pattern and verify behavior changes
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  pattern.update_working_patterns()
  
  progress_clock_by_beats(3)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assertNil(note_on_event)  -- Overlapping trig should be skipped
end

function test_note_merge_modes_with_octave_shifts()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  
  -- Create patterns with notes in different octaves
  local test_pattern = program.initialise_default_pattern()
  test_pattern.trig_values[1] = 1
  test_pattern.note_values[1] = 0  -- Middle C
  
  local test_pattern_2 = program.initialise_default_pattern()
  test_pattern_2.trig_values[1] = 1
  test_pattern_2.note_values[1] = 6  -- C one octave up
  
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  
  -- Test average mode
  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).note_merge_mode = "average"
  pattern.update_working_patterns()
  
  clock_setup()
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65)  -- Should be halfway between 60 and 72
end

function test_velocity_merge_with_extreme_values()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  
  -- Create patterns with extreme velocity values
  local test_pattern = program.initialise_default_pattern()
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 127
  
  local test_pattern_2 = program.initialise_default_pattern()
  test_pattern_2.trig_values[1] = 1
  test_pattern_2.velocity_values[1] = 0
  
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  
  -- Test different velocity merge modes with extreme values
  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).velocity_merge_mode = "average"
  pattern.update_working_patterns()
  
  clock_setup()
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[2], 64)  -- Should be average of 0 and 127
end

function test_length_merge_with_multiple_patterns()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  
  -- Create multiple patterns with different lengths
  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.trig_values[1] = 1
  test_pattern.lengths[1] = 1
  
  local test_pattern_2 = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern_2.trig_values[1] = 1
  test_pattern_2.lengths[1] = 2
  
  local test_pattern_3 = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern_3.trig_values[1] = 1
  test_pattern_3.lengths[1] = 4
  
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  program.get_sequencer_pattern(sequencer_pattern).patterns[3] = test_pattern_3
  
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 3)
  
  -- Test average length merge mode
  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).length_merge_mode = "average"
  pattern.update_working_patterns()
  
  clock_setup()
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60)

  progress_clock_by_beats(1)

  local note_off_event = table.remove(midi_note_off_events, 1)
  luaunit.assert_nil(note_off_event)

  progress_clock_by_beats(1)

  local note_off_event = table.remove(midi_note_off_events, 1)
  luaunit.assert_equals(note_off_event[1], 60)
end

function test_combined_merge_modes_integration()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  
  -- Create patterns with various combinations
  local test_pattern = program.initialise_default_pattern()
  test_pattern.trig_values[1] = 1
  test_pattern.note_values[1] = 0
  test_pattern.velocity_values[1] = 100
  test_pattern.lengths[1] = 1
  
  local test_pattern_2 = program.initialise_default_pattern()
  test_pattern_2.trig_values[1] = 1
  test_pattern_2.note_values[1] = 7
  test_pattern_2.velocity_values[1] = 80
  test_pattern_2.lengths[1] = 3
  
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  
  -- Set different merge modes for each parameter
  program.get_channel(1).trig_merge_mode = "only"
  program.get_channel(1).note_merge_mode = "up"
  program.get_channel(1).velocity_merge_mode = "down"
  program.get_channel(1).length_merge_mode = "average"
  
  pattern.update_working_patterns()


  clock_setup()
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 79)  -- Higher note due to up merge
  luaunit.assert_equals(note_on_event[2], 70)  -- Lower velocity due to down merge

  progress_clock_by_beats(1)

  local note_off_event = table.remove(midi_note_off_events, 1)
  luaunit.assert_nil(note_off_event)  -- Should be no note off event

  progress_clock_by_beats(1)

  local note_off_event = table.remove(midi_note_off_events, 1)
  luaunit.assert_equals(note_off_event[1], 79)  -- Should be note off for the higher note

end

function test_pattern_specific_merge_modes()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  
  -- Create patterns with different values
  local test_pattern = program.initialise_default_pattern()
  test_pattern.trig_values[1] = 1
  test_pattern.note_values[1] = 0
  test_pattern.velocity_values[1] = 100
  test_pattern.lengths[1] = 1
  
  local test_pattern_2 = program.initialise_default_pattern()
  test_pattern_2.trig_values[1] = 1
  test_pattern_2.note_values[1] = 7
  test_pattern_2.velocity_values[1] = 80
  test_pattern_2.lengths[1] = 2
  
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  
  -- Test pattern-specific merging
  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).note_merge_mode = "pattern_number_1"
  program.get_channel(1).velocity_merge_mode = "pattern_number_2"
  
  pattern.update_working_patterns()
  clock_setup()
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60)  -- Should use note from pattern 1
  luaunit.assert_equals(note_on_event[2], 80)  -- Should use velocity from pattern 2
end

function test_merge_modes_with_rests()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  
  -- Create patterns with strategic rests
  local test_pattern = program.initialise_default_pattern()
  test_pattern.trig_values[1] = 1
  test_pattern.trig_values[2] = 0  -- Rest
  test_pattern.trig_values[3] = 1
  test_pattern.note_values[1] = 0  -- C (60)
  test_pattern.note_values[3] = 1  -- D (62)
  
  local test_pattern_2 = program.initialise_default_pattern()
  test_pattern_2.trig_values[1] = 0  -- Rest
  test_pattern_2.trig_values[2] = 1
  test_pattern_2.trig_values[3] = 1
  test_pattern_2.note_values[2] = 4  -- G (67)
  test_pattern_2.note_values[3] = 5  -- A (69)
  
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  
  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).note_merge_mode = "average"
  pattern.update_working_patterns()
  
  clock_setup()
  
  -- Check first step (pattern 1 only)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60)  -- C
  
  -- Check second step (pattern 2 only)
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 67)  -- G
  
  -- Check third step (both patterns)
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  -- Average of note values 1 and 5 = 3, which should play as F (65)
  luaunit.assert_equals(note_on_event[1], 65)
end



function test_note_merge_modes_calculation()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  


  -- Create patterns with specific note values
  local test_pattern = program.initialise_default_pattern()
  test_pattern.trig_values[1] = 1
  test_pattern.note_values[1] = 0  -- C (60)
  
  local test_pattern_2 = program.initialise_default_pattern()
  test_pattern_2.trig_values[1] = 1
  test_pattern_2.note_values[1] = 4  -- G (67)
  
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)

  local channel = program.get_channel(1)

  -- Set length to 1

  channel.start_trig[1] = 1 
  channel.start_trig[2] = 4
  channel.end_trig[1] = 1 
  channel.end_trig[2] = 4

  
  -- Test average mode
  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).note_merge_mode = "average"
  pattern.update_working_patterns()
  
  clock_setup()
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  -- Average of 0 and 4 = 2, which should play as E (64)
  luaunit.assert_equals(note_on_event[1], 64)
  
  -- Test up mode
  program.get_channel(1).note_merge_mode = "up"
  pattern.update_working_patterns()
  
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  -- average(0,4) + (max(0,4) - min(0,4)) = 2 + (4 - 0) = 6, which should play as B (71)
  luaunit.assert_equals(note_on_event[1], 71)
  
  -- Test down mode
  program.get_channel(1).note_merge_mode = "down"
  pattern.update_working_patterns()
  
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 57)
end

function test_merge_modes_at_pattern_boundaries()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  
  -- Create patterns with different lengths
  local test_pattern = program.initialise_default_pattern()
  test_pattern.trig_values[63] = 1
  test_pattern.trig_values[64] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.note_values[63] = 0  -- C (60)
  test_pattern.note_values[64] = 1  -- D (62)
  test_pattern.note_values[1] = 2   -- E (64)
  
  local test_pattern_2 = program.initialise_default_pattern()
  test_pattern_2.trig_values[64] = 1
  test_pattern_2.trig_values[1] = 1
  test_pattern_2.trig_values[2] = 1
  test_pattern_2.note_values[64] = 4  -- G (67)
  test_pattern_2.note_values[1] = 5   -- A (69)
  test_pattern_2.note_values[2] = 6   -- B (71)
  
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
  
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 2)
  
  program.get_channel(1).trig_merge_mode = "all"
  program.get_channel(1).note_merge_mode = "average"
  pattern.update_working_patterns()
  
  -- Move to pattern boundary
  program.set_current_step_for_channel(1, 63)
  clock_setup()
  
  -- Check step 63 (pattern 1 only)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60)  -- C
  
  -- Check step 64 (both patterns)
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  -- Average of note values 1 and 4 = 2.5, rounded to 3, which should play as E (64)
  luaunit.assert_equals(note_on_event[1], 65)
  
  -- Check step 1 (both patterns)
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  -- Average of note values 2 and 5 = 3.5, rounded to 4, which should play as F (65)
  luaunit.assert_equals(note_on_event[1], 67)
end

