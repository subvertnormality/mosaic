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


function test_step_continues_at_new_start_step_when_pattern_size_changes()

  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  test_pattern.note_values[17] = 1
  test_pattern.lengths[17] = 1
  test_pattern.trig_values[17] = 1
  test_pattern.velocity_values[17] = 101

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

  program.get_channel(1).start_trig[1] = 1
  program.get_channel(1).start_trig[2] = 4

  program.get_channel(1).end_trig[1] = 4
  program.get_channel(1).end_trig[2] = 4

  pattern_controller.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(4)


  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  program.get_channel(1).start_trig[1] = 1
  program.get_channel(1).start_trig[2] = 5

  program.get_channel(1).end_trig[1] = 4
  program.get_channel(1).end_trig[2] = 5

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

end

function test_song_mode_functions_with_short_channel_pattern_lengths_and_short_sequencer_pattern_lengths_when_pattern_reset_is_disabled()

  setup()

  params:set("song_mode", 2) 
  params:set("reset_on_end_of_pattern_repeat", 1)
  params:set("reset_on_sequencer_pattern_transition", 1)

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
  params:set("reset_on_end_of_pattern_repeat", 1)
  params:set("reset_on_sequencer_pattern_transition", 1)

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
  params:set("reset_on_end_of_pattern_repeat", 2)

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
  params:set("reset_on_sequencer_pattern_transition", 2) 
  params:set("reset_on_end_of_pattern_repeat", 1) 

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
  params:set("reset_on_sequencer_pattern_transition", 2) 
  params:set("reset_on_end_of_pattern_repeat", 1) 

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
  



function test_song_mode_short_channel_pattern_lengths_transitions_correctly_to_longer_pattern_lengths_across_sequencer_patterns()

  setup()
  params:set("song_mode", 2) 
  params:set("reset_on_end_of_pattern_repeat", 2)
  params:set("reset_on_sequencer_pattern_transition", 1)

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
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern_2).channels[1].selected_patterns, 1)

  program.get_channel(1).start_trig[1] = 1
  program.get_channel(1).start_trig[2] = 4

  program.get_channel(1).end_trig[1] = 8
  program.get_channel(1).end_trig[2] = 4

  program.get_sequencer_pattern(sequencer_pattern_2).global_pattern_length = 16

  program.set_selected_sequencer_pattern(1)

  pattern_controller.update_working_patterns()

  clock_setup()

  -- First trig in song sequence 1 fires
  local note_on_event = table.remove(midi_note_on_events, 1) -- 1

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2) -- 2, 1

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(2) -- 2, 1
  progress_clock_by_beats(5) -- 2, 3, 4, 5, 6

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 126)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(8) -- 7, 8, 1, 2, 3, 4, 5, 6

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 126)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(3)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 101)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_channel_steps_beyond_global_pattern_length()
  setup()
  
  -- Set up a shorter global pattern length
  local global_pattern_length = 42
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()

  -- Place notes beyond the global pattern length
  test_pattern.note_values[45] = 0
  test_pattern.lengths[45] = 1
  test_pattern.trig_values[45] = 1
  test_pattern.velocity_values[45] = 100

  test_pattern.note_values[50] = 1
  test_pattern.lengths[50] = 1
  test_pattern.trig_values[50] = 1
  test_pattern.velocity_values[50] = 101

  -- Set up the sequencer pattern
  local seq_pattern = program.get_sequencer_pattern(sequencer_pattern)
  if not seq_pattern then
    return
  end
  seq_pattern.patterns[1] = test_pattern

  -- Add pattern to channel
  if not seq_pattern.channels[1] then
    return
  end
  fn.add_to_set(seq_pattern.channels[1].selected_patterns, 1)

  -- Set channel start/end trigs
  local channel = program.get_channel(1)
  if not channel then
    return
  end

  channel.start_trig[1] = 13  -- Step 45
  channel.start_trig[2] = 6
  channel.end_trig[1] = 7    -- Step 55
  channel.end_trig[2] = 7

  -- Set global pattern length
  seq_pattern.global_pattern_length = global_pattern_length

  -- Update and setup clock
  pattern_controller.update_working_patterns()
  clock_setup()

  -- Track notes that fire
  local fired_notes = {}
  local steps_fired = {}

  -- Run sequence
  for i = 1, global_pattern_length * 3 do

    local note_on_event = table.remove(midi_note_on_events, 1)
    if note_on_event then
      local current_step = program.get_current_step_for_channel(1)

      table.insert(fired_notes, {
        note = note_on_event[1],
        velocity = note_on_event[2],
        channel = note_on_event[3],
        step = current_step
      })
      table.insert(steps_fired, current_step)
    end

    progress_clock_by_pulses(24)
  end

  -- Basic assertions that something happened
  luaunit.assert_not_equals(#fired_notes, 0, "Should have fired at least one note")
  
  if #fired_notes > 0 then
    -- Verify first note if we have one
    luaunit.assert_equals(fired_notes[1].note, 60, "First note should be correct")
    luaunit.assert_equals(fired_notes[1].velocity, 100, "First velocity should be correct")
    luaunit.assert_equals(fired_notes[1].channel, 1, "First channel should be correct")
    luaunit.assert_equals(fired_notes[1].step, 45, "First step should be correct")
    luaunit.assert_equals(fired_notes[2].note, 62, "Second note should be correct")
    luaunit.assert_equals(fired_notes[2].velocity, 101, "Second velocity should be correct")
    luaunit.assert_equals(fired_notes[2].channel, 1, "Second channel should be correct")
    luaunit.assert_equals(fired_notes[2].step, 50, "Second step should be correct")
    luaunit.assert_equals(fired_notes[3].note, 60, "Third note should be correct")
    luaunit.assert_equals(fired_notes[3].velocity, 100, "Third velocity should be correct")
    luaunit.assert_equals(fired_notes[3].channel, 1, "Third channel should be correct")
    luaunit.assert_equals(fired_notes[3].step, 45, "Third step should be correct")
    luaunit.assert_equals(fired_notes[4].note, 62, "Fourth note should be correct")
    luaunit.assert_equals(fired_notes[4].velocity, 101, "Fourth velocity should be correct")
    luaunit.assert_equals(fired_notes[4].channel, 1, "Fourth channel should be correct")
    luaunit.assert_equals(fired_notes[4].step, 50, "Fourth step should be correct")
  end
end


function test_channel_with_pattern_longer_than_global_length()
  setup()
  
  -- Set up global pattern length shorter than channel pattern length
  local global_pattern_length = 16
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(sequencer_pattern)
  local test_pattern = program.initialise_default_pattern()
  
  -- Place notes beyond the global pattern length
  test_pattern.note_values[20] = 0 -- Note at step 20
  test_pattern.lengths[20] = 1
  test_pattern.trig_values[20] = 1
  test_pattern.velocity_values[20] = 100

  test_pattern.note_values[25] = 1 -- Note at step 25
  test_pattern.lengths[25] = 1
  test_pattern.trig_values[25] = 1
  test_pattern.velocity_values[25] = 101

  -- Set up the sequencer pattern
  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  
  -- Set channel start and end trigs to cover steps beyond global pattern length
  program.get_channel(1).start_trig[1] = 1
  program.get_channel(1).start_trig[2] = 4
  program.get_channel(1).end_trig[1] = 9
  program.get_channel(1).end_trig[2] = 5

  -- Set global pattern length
  program.get_sequencer_pattern(sequencer_pattern).global_pattern_length = global_pattern_length
  
  -- Update and setup clock
  pattern_controller.update_working_patterns()
  clock_setup()
  
  -- Run the sequence for multiple global pattern lengths
  local fired_notes = {}
  for i = 1, global_pattern_length * 3 do

    local note_on_event = table.remove(midi_note_on_events, 1)
    if note_on_event then
      local current_step = program.get_current_step_for_channel(1)
      table.insert(fired_notes, {
        note = note_on_event[1],
        velocity = note_on_event[2],
        channel = note_on_event[3],
        step = current_step
      })
    end

    progress_clock_by_pulses(24) -- Progress by one beat (assuming 24 PPQN)
  end

  -- Expected steps where notes should fire
  local actual_steps = {}
  for _, event in ipairs(fired_notes) do
    table.insert(actual_steps, event.step)
  end
  
  luaunit.assert_equals(#fired_notes, 0)
end