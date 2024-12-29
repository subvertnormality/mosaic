local step = include("mosaic/lib/step")
pattern = include("mosaic/lib/pattern")

include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
local m_clock = include("mosaic/lib/clock/m_clock")

local function setup()
  program.init()
  globals.reset()
  params.reset()
  m_clock.init()
  m_clock:start()
end

local function mock_random()
  random = function (min, max)
    return max - min
  end
end

local function progress_clock_by_beats(b)
  for i = 1, (24 * b) do
    m_clock.get_clock_lattice():pulse()
  end
end

function test_steps_process_note_on_events()
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  step.handle(1, 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end


function test_manually_calculate_step_scale_number_standard_speeds()
  setup()
  
  -- Both channels at standard speed (4)
  local channel = 2
  local clock_division_17 = 4
  local channel_division = 4
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  program.add_step_scale_trig_lock(2, 3)
  
  -- At standard speeds, steps should map 1:1
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1), 2)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 2), 3)
end

function test_manually_calculate_step_scale_number_channel_half_speed()
  setup()
  
  -- Channel at half speed (2), scale channel at standard (4)
  local channel = 2
  local clock_division_17 = 4
  local channel_division = 2
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  program.add_step_scale_trig_lock(2, 3)
  program.add_step_scale_trig_lock(3, 4)
  
  -- At half speed, one channel step spans multiple global steps
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1), 2)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 2), 4)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 3), 4)
end

function test_manually_calculate_step_scale_number_channel_double_speed()
  setup()
  
  -- Channel at double speed (8), scale channel at standard (4)
  local channel = 2
  local clock_division_17 = 4
  local channel_division = 8
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  program.add_step_scale_trig_lock(2, 3)
  
  -- At double speed, multiple channel steps map to one global step
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1), 2)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 2), 2)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 3), 3)
end

function test_manually_calculate_step_scale_number_scale_channel_double_speed()
  setup()
  
  -- Channel at standard (4), scale channel at double speed (8)
  local channel = 2
  local clock_division_17 = 8
  local channel_division = 4
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  program.add_step_scale_trig_lock(2, 3)
  program.add_step_scale_trig_lock(3, 4)
  
  -- With scale channel at double speed, fewer channel steps needed to advance global step
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1), 2)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 2), 4)
end

function test_manually_calculate_step_scale_number_both_channels_double_speed()
  setup()
  
  -- Both channels at double speed (8)
  local channel = 2
  local clock_division_17 = 8
  local channel_division = 8
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  program.add_step_scale_trig_lock(2, 3)
  
  -- When both at same speed (even if not standard), should map 1:1
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1), 2)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 2), 3)
end

function test_manually_calculate_step_scale_number_very_fast_vs_very_slow()
  setup()
  
  -- Channel very fast (16), scale channel very slow (1)
  local channel = 2
  local clock_division_17 = 1
  local channel_division = 16
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  program.add_step_scale_trig_lock(2, 3)
  
  -- Many channel steps should map to single global step
  for i = 1, 16 do
    luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, i), 2)
  end
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 17), 3)
end

function test_manually_calculate_step_scale_number_channel_with_override()
  setup()
  
  -- Standard speeds but with channel override
  local channel = 2
  local clock_division_17 = 4
  local channel_division = 4
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  
  -- Add channel-specific override
  program.get_channel(program.get().selected_song_pattern, channel).step_scale_trig_lock_banks[1] = 5
  
  -- Channel override should take precedence regardless of speeds
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1), 5)
end


function test_manually_calculate_step_scale_number_extreme_speed_differences()
  setup()
  
  local channel = 2
  local clock_division_17 = 0.5
  local channel_division = 32
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  program.add_step_scale_trig_lock(2, 3)
  program.add_step_scale_trig_lock(3, 4)
  
  -- Many channel steps should map to first global step due to extreme speed difference
  for i = 1, 64 do
    luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, i), 2)
  end
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 65), 3)
end


function test_manually_calculate_step_scale_number_extreme_speed_differences_inverted()
  setup()
  
  local channel = 2
  local clock_division_17 = 32
  local channel_division = 0.5
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  program.add_step_scale_trig_lock(2, 3)
  program.add_step_scale_trig_lock(3, 4)
  
  -- For very mismatched speeds, we want to stay on the first scale for many steps
  for i = 1, 64 do
    luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, i), 2)
  end
end


function test_manually_calculate_step_scale_number_with_scale_gaps()
  setup()
  
  -- Test with gaps in scale sequence
  local channel = 2
  local clock_division_17 = 4
  local channel_division = 4
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  -- Skip step 2
  program.add_step_scale_trig_lock(3, 4)
  
  -- Should handle gaps by keeping previous scale
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1), 2)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 2), 2)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 3), 4)
end


function test_manually_calculate_step_scale_number_with_very_large_steps()
  setup()
  
  -- Test with very large step numbers
  local channel = 2
  local clock_division_17 = 4
  local channel_division = 4
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  program.add_step_scale_trig_lock(2, 3)
  
  -- Should handle very large steps 
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1000), 3)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 9999), 3)
end


function test_speed_ratio_over_16()
  setup()

  local channel = 2
  local clock_division_17 = 1
  local channel_division = 32

  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)

  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)
  program.add_step_scale_trig_lock(2, 3)

  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1), 2)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 32), 2)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 33), 3)
end


function test_random_notes_with_chords()
  setup()
  mock_random() -- This will make random return max-min
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  
  -- Set up initial pattern with C as root note (0) and chord notes for third (+2) and fifth (+4)
  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100
  
  local channel = program.get_channel(song_pattern, 1)
  -- Using relative scale degrees for chord masks
  channel.chord_one_mask = 2  -- Third relative to root
  channel.chord_two_mask = 4  -- Fifth relative to root
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up C major scale
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0  -- C
  scale.number = 1     -- Major scale
  
  -- Set random note param to shift up by 1 step (to D)
  channel.trig_lock_params[1].id = "bipolar_random_note"
  program.add_step_param_trig_lock(1, 1, 1) -- Shift up by 1 step
  
  step.handle(1, 1)
  
  -- Should get three note on events - root D and chord notes F and A
  local note_events = midi_note_on_events
  
  luaunit.assert_equals(#note_events, 3)
  luaunit.assert_equals(note_events[1][1], 62) -- D
  luaunit.assert_equals(note_events[2][1], 65) -- F 
  luaunit.assert_equals(note_events[3][1], 69) -- A
end

function test_random_notes_with_arp()
  setup()
  mock_random() -- This will make random return max-min
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  
  -- Set up initial pattern with C as root note (0)
  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100
  
  local channel = program.get_channel(song_pattern, 1)
  -- Using relative scale degrees for chord masks
  channel.chord_one_mask = 2  -- Third relative to root
  channel.chord_two_mask = 4  -- Fifth relative to root
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up C major scale
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0  -- C
  scale.number = 1     -- Major scale
  
  -- Set random note param to shift up by 1 step (to D)
  channel.trig_lock_params[1] = {id = "bipolar_random_note", param_id = "random_note_1"}
  program.add_step_param_trig_lock(1, 1, 1) -- Shift up by 1 step
  
  -- Enable arpeggio mode with standard division
  channel.trig_lock_params[2] = {id = "chord_arp", param_id = "chord_arp_1"}
  program.add_step_param_trig_lock(1, 2, 4) -- Standard division
  
  -- Initialize m_clock for arp timing
  m_clock.init()
  m_clock:start()
  
  
  -- Should get first note immediately
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62) -- D
  
  -- Clear events and advance clock to get next notes
  progress_clock_by_beats(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65) -- F
  
  -- Clear and advance again for final note
  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 69) -- A
end

function test_random_notes_with_arp_and_velocity_mod()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100
  
  local channel = program.get_channel(song_pattern, 1)
  channel.chord_one_mask = 2
  channel.chord_two_mask = 4
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up scale
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 1
  
  -- Add random note and arp with velocity modifier
  channel.trig_lock_params[1] = {id = "bipolar_random_note", param_id = "random_note_1"}
  program.add_step_param_trig_lock(1, 1, 1)
  
  channel.trig_lock_params[2] = {id = "chord_arp", param_id = "chord_arp_1"}
  program.add_step_param_trig_lock(1, 2, 4)
  
  channel.trig_lock_params[3] = {id = "chord_velocity_modifier", param_id = "chord_velocity_1"}
  program.add_step_param_trig_lock(1, 3, 10) -- Increase velocity by 10 per note
  
  m_clock.init()
  m_clock:start()
  
  -- First note
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62) -- D
  luaunit.assert_equals(note_on_event[2], 100) -- Base velocity
  
  progress_clock_by_beats(1)
  
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65) -- F
  luaunit.assert_equals(note_on_event[2], 110) -- Velocity + 10
  
  progress_clock_by_beats(1)

  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 69) -- A
  luaunit.assert_equals(note_on_event[2], 120) -- Velocity + 20
end

function test_random_notes_with_arp_and_note_mask()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.note_mask_values[1] = 60 -- Fixed C4
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100
  
  local channel = program.get_channel(song_pattern, 1)
  channel.chord_one_mask = 2
  channel.chord_two_mask = 4
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up scale
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 1
  
  -- Add random note and arp
  channel.trig_lock_params[1] = {id = "bipolar_random_note", param_id = "random_note_1"}
  program.add_step_param_trig_lock(1, 1, 1)
  
  channel.trig_lock_params[2] = {id = "chord_arp", param_id = "chord_arp_1"}
  program.add_step_param_trig_lock(1, 2, 4)
  
  m_clock.init()
  m_clock:start()
  
  -- Random note shift should be added to note mask value
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62) -- C4 (mask)
  
  progress_clock_by_beats(1)
  
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65) -- E4 (mask + third)
  
  progress_clock_by_beats(1)

  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 69) -- G4 (mask + fifth)
end

function test_random_notes_with_arp_and_strum_pattern()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100
  
  local channel = program.get_channel(song_pattern, 1)
  channel.chord_one_mask = 2
  channel.chord_two_mask = 4
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up scale
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 1
  
  -- Add random note, arp and reverse strum pattern
  channel.trig_lock_params[1] = {id = "bipolar_random_note", param_id = "random_note_1"}
  program.add_step_param_trig_lock(1, 1, 1)
  
  channel.trig_lock_params[2] = {id = "chord_arp", param_id = "chord_arp_1"}
  program.add_step_param_trig_lock(1, 2, 4)
  
  channel.trig_lock_params[3] = {id = "chord_strum_pattern", param_id = "chord_strum_pattern_1"}
  program.add_step_param_trig_lock(1, 3, 2) -- Reverse pattern
  
  m_clock.init()
  m_clock:start()
  
  -- Should play highest note first
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 69) -- A (fifth)
  
  progress_clock_by_beats(1)
  
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65) -- F (third)
  
  progress_clock_by_beats(1)

  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62) -- D (root)
end

function test_random_notes_with_note_mask_and_chords()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.note_mask_values[1] = 60 -- Fixed C4
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100
  
  local channel = program.get_channel(song_pattern, 1)
  channel.chord_one_mask = 2  -- Third
  channel.chord_two_mask = 4  -- Fifth
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up scale
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 1
  
  -- Add random note shift
  channel.trig_lock_params[1] = {id = "bipolar_random_note", param_id = "random_note_1"}
  program.add_step_param_trig_lock(1, 1, 1) -- Shift up by 1 step
  
  step.handle(1, 1)
  
  -- Should get three note on events - all shifted up by random amount
  local note_events = midi_note_on_events
  
  luaunit.assert_equals(#note_events, 3)
  luaunit.assert_equals(note_events[1][1], 62) -- D4 (C4 + random shift)
  luaunit.assert_equals(note_events[2][1], 65) -- F4 (D4 + third)
  luaunit.assert_equals(note_events[3][1], 69) -- A5 (D4 + fifth)
end

function test_random_notes_with_note_mask_and_chords_multiple_random_sources()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.note_mask_values[1] = 60 -- Fixed C4
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100
  
  local channel = program.get_channel(song_pattern, 1)
  channel.chord_one_mask = 2
  channel.chord_two_mask = 4
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up scale
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 1
  
  -- Add both bipolar and twos random shifts
  channel.trig_lock_params[1] = {id = "bipolar_random_note", param_id = "random_note_1"}
  program.add_step_param_trig_lock(1, 1, 1) -- Shift up by 1 step
  
  channel.trig_lock_params[2] = {id = "twos_random_note", param_id = "twos_random_note_1"}
  program.add_step_param_trig_lock(1, 2, 1) -- Additional shift up by 2 step
  
  step.handle(1, 1)
  
  -- Should get three note on events - all shifted up by combined random amount
  local note_events = midi_note_on_events
  
  luaunit.assert_equals(#note_events, 3)
  luaunit.assert_equals(note_events[1][1], 65) -- F4 (C4 + bipolar shift + twos shift)
  luaunit.assert_equals(note_events[2][1], 69) -- A5 (E4 + third)
  luaunit.assert_equals(note_events[3][1], 72) -- C4 (E4 + fifth)
end

function test_random_notes_with_note_mask_and_chords_minor_scale()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.note_mask_values[1] = 60 -- Fixed C4
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100
  
  local channel = program.get_channel(song_pattern, 1)
  channel.chord_one_mask = 2
  channel.chord_two_mask = 4
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up minor scale
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 2 -- Minor scale
  
  -- Add random note shift
  channel.trig_lock_params[1] = {id = "bipolar_random_note", param_id = "random_note_1"}
  program.add_step_param_trig_lock(1, 1, 1) -- Shift up by 1 step
  
  step.handle(1, 1)
  
  -- Should get three note on events - all shifted up by random amount, using minor scale intervals
  local note_events = midi_note_on_events
  
  luaunit.assert_equals(#note_events, 3)
  luaunit.assert_equals(note_events[1][1], 62) -- D4 (C4 + random shift)
  luaunit.assert_equals(note_events[2][1], 65) -- F4 (D4 + minor third)
  luaunit.assert_equals(note_events[3][1], 69) -- A4 (D4 + fifth)
end