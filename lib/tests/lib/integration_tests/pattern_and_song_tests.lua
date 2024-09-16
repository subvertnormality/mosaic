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


function test_current_step_number_is_set_to_start_step_when_lower_than_start_trig_number()

  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[3] = 0
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).start_trig[1] = 3
  program.get_channel(1).start_trig[2] = 4


  pattern_controller.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

end

function test_current_step_number_is_set_to_start_step_when_lower_than_start_trig_number()

  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  local step = 3

  test_pattern.note_values[step] = 0
  test_pattern.lengths[step] = 1
  test_pattern.trig_values[step] = 1
  test_pattern.velocity_values[step] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).start_trig[1] = step
  program.get_channel(1).start_trig[2] = 4


  pattern_controller.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_song_mode_functions_with_short_channel_pattern_lengths_and_short_sequencer_pattern_lengths_when_pattern_reset_is_disabled()

  setup()

  params:set("song_mode", 2) 
  params:set("reset_on_end_of_pattern", 1)
  params:set("reset_on_end_of_sequencer_pattern", 1)

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[3] = 0
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 101

  
  program.get_sequencer_pattern(sequencer_pattern).repeats = 1
  program.get_sequencer_pattern(sequencer_pattern).active = true
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).start_trig[1] = 3
  program.get_channel(1).start_trig[2] = 4

  program.get_channel(1).end_trig[1] = 4
  program.get_channel(1).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern).global_pattern_length = 4

  local sequencer_pattern_2 = 2
  program.set_selected_sequencer_pattern(2)
  
  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[6] = 0
  test_pattern_2.lengths[6] = 1
  test_pattern_2.trig_values[6] = 1
  test_pattern_2.velocity_values[6] = 126

  program.get_sequencer_pattern(sequencer_pattern_2).repeats = 1
  program.get_sequencer_pattern(sequencer_pattern_2).active = true
  program.get_sequencer_pattern(sequencer_pattern_2).patterns[2] = test_pattern_2
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern_2).channels[16].selected_patterns, 2)

  program.get_channel(16).start_trig[1] = 1
  program.get_channel(16).start_trig[2] = 4

  program.get_channel(16).end_trig[1] = 8
  program.get_channel(16).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern_2).global_pattern_length = 8

  program.set_selected_sequencer_pattern(1)

  pattern_controller.update_working_patterns()

  clock_setup()

  -- First trig in song sequence 1 fires
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  -- First trig in song sequence 1 fires again due to channel being half the length of song sequence
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)


  -- the global clock continues when the song sequence changes
  progress_clock_by_beats(3)

  -- Step 6 of the second song sequence now fires
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 126)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(3)

  -- First trig in song sequence 1 fires again
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

end



function test_short_channel_pattern_lengths_and_short_sequencer_pattern_lengths_when_both_pattern_resets_are_disabled()

  setup()

  params:set("song_mode", 2) 
  params:set("reset_on_end_of_pattern", 1)
  params:set("reset_on_end_of_sequencer_pattern", 1)

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[4] = 0
  test_pattern.lengths[4] = 1
  test_pattern.trig_values[4] = 1
  test_pattern.velocity_values[4] = 101

  test_pattern.note_values[5] = 0
  test_pattern.lengths[5] = 1
  test_pattern.trig_values[5] = 1
  test_pattern.velocity_values[5] = 102
  
  program.get_sequencer_pattern(sequencer_pattern).repeats = 1
  program.get_sequencer_pattern(sequencer_pattern).active = true
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).start_trig[1] = 1
  program.get_channel(1).start_trig[2] = 4

  program.get_channel(1).end_trig[1] = 6
  program.get_channel(1).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern).global_pattern_length = 4

  pattern_controller.update_working_patterns()

  clock_setup()

  progress_clock_by_beats(3)

  -- Fourth trig in song sequence 1 fires
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  -- Fifth trig in song sequence 1 doesnt fire because the song sequence is shorter than the channel pattern
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assertNil(note_on_event)

  progress_clock_by_beats(3)

  -- Fourth trig in song sequence 1 fires again
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

end

function test_song_mode_functions_with_short_channel_pattern_lengths_and_short_sequencer_pattern_lengths_when_pattern_reset_is_enabled()

  setup()
  params:set("song_mode", 2) 
  params:set("reset_on_end_of_pattern", 2)

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[3] = 0
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 101

  
  program.get_sequencer_pattern(sequencer_pattern).repeats = 1
  program.get_sequencer_pattern(sequencer_pattern).active = true
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).start_trig[1] = 3
  program.get_channel(1).start_trig[2] = 4

  program.get_channel(1).end_trig[1] = 4
  program.get_channel(1).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern).global_pattern_length = 4

  local sequencer_pattern_2 = 2
  program.set_selected_sequencer_pattern(2)
  
  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[6] = 0
  test_pattern_2.lengths[6] = 1
  test_pattern_2.trig_values[6] = 1
  test_pattern_2.velocity_values[6] = 126

  program.get_sequencer_pattern(sequencer_pattern_2).repeats = 1
  program.get_sequencer_pattern(sequencer_pattern_2).active = true
  program.get_sequencer_pattern(sequencer_pattern_2).patterns[1] = test_pattern_2
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern_2).channels[16].selected_patterns, 1)

  program.get_channel(16).start_trig[1] = 1
  program.get_channel(16).start_trig[2] = 4

  program.get_channel(16).end_trig[1] = 8
  program.get_channel(16).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern_2).global_pattern_length = 8

  program.set_selected_sequencer_pattern(1)

  pattern_controller.update_working_patterns()

  clock_setup()

  -- First trig in song sequence 1 fires
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)
  progress_clock_by_beats(2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)
  progress_clock_by_beats(5)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 126)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(3)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

end



function test_song_mode_functions_with_short_channel_pattern_lengths_and_short_sequencer_pattern_lengths_when_seq_pattern_reset_is_enabled()

  setup()
  params:set("song_mode", 2) 
  params:set("reset_on_end_of_sequencer_pattern", 2) 
  params:set("reset_on_end_of_pattern", 1) 

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[3] = 0
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 101

  
  program.get_sequencer_pattern(sequencer_pattern).repeats = 1
  program.get_sequencer_pattern(sequencer_pattern).active = true
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).start_trig[1] = 3
  program.get_channel(1).start_trig[2] = 4

  program.get_channel(1).end_trig[1] = 4
  program.get_channel(1).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern).global_pattern_length = 4

  local sequencer_pattern_2 = 2
  program.set_selected_sequencer_pattern(2)
  
  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[6] = 0
  test_pattern_2.lengths[6] = 1
  test_pattern_2.trig_values[6] = 1
  test_pattern_2.velocity_values[6] = 126

  program.get_sequencer_pattern(sequencer_pattern_2).repeats = 1
  program.get_sequencer_pattern(sequencer_pattern_2).active = true
  program.get_sequencer_pattern(sequencer_pattern_2).patterns[2] = test_pattern_2
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern_2).channels[16].selected_patterns, 2)

  program.get_channel(16).start_trig[1] = 1
  program.get_channel(16).start_trig[2] = 4

  program.get_channel(16).end_trig[1] = 8
  program.get_channel(16).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern_2).global_pattern_length = 8

  program.set_selected_sequencer_pattern(1)

  pattern_controller.update_working_patterns()

  clock_setup()

  -- First trig in song sequence 1 fires
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  -- First trig in song sequence 1 fires again due to channel being half the length of song sequence
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  -- the clock resets when the song sequence changes
  progress_clock_by_beats(7)

  -- Step 6 of the second song sequence now fires
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 126)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(3)

  -- First trig in song sequence 1 fires again
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)
end
  



function test_song_mode_functions_with_sequencer_pattern_repeats()

  setup()
  params:set("song_mode", 2) 
  params:set("reset_on_end_of_sequencer_pattern", 2) 
  params:set("reset_on_end_of_pattern", 1) 

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[3] = 0
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 101

  
  program.get_sequencer_pattern(sequencer_pattern).repeats = 2
  program.get_sequencer_pattern(sequencer_pattern).active = true
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).start_trig[1] = 3
  program.get_channel(1).start_trig[2] = 4

  program.get_channel(1).end_trig[1] = 4
  program.get_channel(1).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern).global_pattern_length = 4

  local sequencer_pattern_2 = 2
  program.set_selected_sequencer_pattern(2)
  
  local test_pattern_2 = program.initialise_default_pattern()

  test_pattern_2.note_values[6] = 0
  test_pattern_2.lengths[6] = 1
  test_pattern_2.trig_values[6] = 1
  test_pattern_2.velocity_values[6] = 126

  program.get_sequencer_pattern(sequencer_pattern_2).repeats = 1
  program.get_sequencer_pattern(sequencer_pattern_2).active = true
  program.get_sequencer_pattern(sequencer_pattern_2).patterns[2] = test_pattern_2
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern_2).channels[16].selected_patterns, 2)

  program.get_channel(16).start_trig[1] = 1
  program.get_channel(16).start_trig[2] = 4

  program.get_channel(16).end_trig[1] = 8
  program.get_channel(16).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern_2).global_pattern_length = 8

  program.set_selected_sequencer_pattern(1)

  pattern_controller.update_working_patterns()

  clock_setup()

  -- First trig in song sequence 1 fires
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  -- First trig in song sequence 1 fires again due to channel being half the length of song sequence
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  -- First trig in song sequence 1 fires again due to channel being half the length of song sequence
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2)

  -- First trig in song sequence 1 fires again due to channel being half the length of song sequence
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  -- the clock resets when the song sequence changes
  progress_clock_by_beats(7)

  -- Step 6 of the second song sequence now fires
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 126)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(3)

  -- First trig in song sequence 1 fires again
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)
end
  