local step = include("mosaic/lib/step")
pattern = include("mosaic/lib/pattern")

local quantiser = include("mosaic/lib/quantiser")


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
  luaunit.assert_equals(note_events[1][1], 61) -- D4 (C4 + random shift)
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
  luaunit.assert_equals(note_events[1][1], 63) -- F4 (C4 + bipolar shift + twos shift)
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
  luaunit.assert_equals(note_events[1][1], 61) -- D4 (C4 + random shift)
  luaunit.assert_equals(note_events[2][1], 65) -- F4 (D4 + minor third)
  luaunit.assert_equals(note_events[3][1], 69) -- A4 (D4 + fifth)
end

function test_note_mask_with_fully_act_on_note_masks_simple()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.note_mask_values[1] = 61 -- Fixed C#4 (should be quantized to D4 in C major)
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100
  
  local channel = program.get_channel(song_pattern, 1)
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up C major scale
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 1
  scale.chord = 2

  -- Enable fully act on note masks
  params:set("quantiser_fully_act_on_note_masks", 2)
  
  step.handle(1, 1)
  
  local note_events = midi_note_on_events
  luaunit.assert_equals(#note_events, 1)
  luaunit.assert_equals(note_events[1][1], 62) -- D4 (C#4 quantized to next scale degree)
end

function test_note_mask_with_fully_act_on_note_masks_and_transpose()
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
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up C major scale with transpose
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 1
  scale.chord = 1
  scale.transpose = 2
  -- Enable fully act on note masks
  params:set("quantiser_fully_act_on_note_masks", 2)
  
  step.handle(1, 1)
  
  local note_events = midi_note_on_events
  luaunit.assert_equals(#note_events, 1)
  luaunit.assert_equals(note_events[1][1], 62) -- E4 (C4 transposed up 2 semitones)
end

function test_note_mask_with_fully_act_on_note_masks_and_chords_minor_scale()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.note_mask_values[1] = 61 -- Fixed C#4 (should be quantized to D4 in C major)
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100
  
  local channel = program.get_channel(song_pattern, 1)
  channel.chord_one_mask = 2  -- Third
  channel.chord_two_mask = 4  -- Fifth
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up minor scale
  program.get().default_scale = 1

  local scale = quantiser.get_scales()[3]
  
  program.set_scale(
    1,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0,
      transpose = 2
    }
  )

  -- Enable fully act on note masks
  params:set("quantiser_fully_act_on_note_masks", 2)
  
  step.handle(1, 1)
  
  local note_events = midi_note_on_events
  luaunit.assert_equals(#note_events, 3)
  luaunit.assert_equals(note_events[1][1], 62) -- C tranposed up 2 semitones
  luaunit.assert_equals(note_events[2][1], 65) -- E4 (C + minor third) tranposed up 2 semitones
  luaunit.assert_equals(note_events[3][1], 69) -- G4 (C + fifth) tranposed up 2 semitones
end

function test_note_mask_with_fully_act_on_note_masks_octave_and_transpose()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.note_mask_values[1] = 73 -- Fixed C#5 (should be quantized to D5 in C major)
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  local channel = program.get_channel(song_pattern, 1)
  channel.octave = 1 -- Add octave

  pattern.update_working_patterns()

  -- Set up C major scale with transpose
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 1
  scale.transpose = 2 -- Transpose up 2 semitones

  -- Enable fully act on note masks
  params:set("quantiser_fully_act_on_note_masks", 2)
  
  step.handle(1, 1)
  
  local note_events = midi_note_on_events
  luaunit.assert_equals(#note_events, 1)
  luaunit.assert_equals(note_events[1][1], 86) -- E6 (C#5 quantized to C, octave up, transposed up 2 semitones to E)
end


function test_note_mask_with_fully_act_on_note_masks_octave_and_transpose_using_param()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.note_mask_values[1] = 73 -- Fixed C#5 (should be quantized to D5 in C major)
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  local channel = program.get_channel(song_pattern, 1)
  channel.octave = 1 -- Add octave


  channel.trig_lock_params[4].id = "fully_quantise_mask"
  program.add_step_param_trig_lock(1, 4, 2) -- Enable

  pattern.update_working_patterns()

  -- Set up C major scale with transpose
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 1
  scale.transpose = 2 -- Transpose up 2 semitones

  step.handle(1, 1)
  
  local note_events = midi_note_on_events
  luaunit.assert_equals(#note_events, 1)
  luaunit.assert_equals(note_events[1][1], 86) -- E6 (C#5 quantized to D5, octave up, transposed up 2 semitones to E)
end



function test_note_mask_with_fully_act_on_note_masks_octave_and_transpose_override_to_be_off_using_param()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.note_mask_values[1] = 73 -- Fixed C#5 (should be quantized to D5 in C major)
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  local channel = program.get_channel(song_pattern, 1)
  channel.octave = 1 -- Add octave

  channel.trig_lock_params[4].id = "fully_quantise_mask"
  program.add_step_param_trig_lock(1, 4, 1) -- Explicitly disable

  pattern.update_working_patterns()

  -- Set up C major scale with transpose
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 1
  scale.transpose = 2 -- Transpose up 2 semitones

  -- Enable fully act on note masks
  params:set("quantiser_fully_act_on_note_masks", 2)
  
  step.handle(1, 1)
  
  local note_events = midi_note_on_events
  luaunit.assert_equals(#note_events, 1)
  luaunit.assert_equals(note_events[1][1], 85)
end


function test_manually_calculate_step_scale_number_step_1_standard_speeds()
  setup()
  
  -- Both channels at standard speed (4)
  local channel = 2
  local clock_division_17 = 4
  local channel_division = 4
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2) -- Scale 2 on step 1
  
  -- Step 1 should always use step 1's scale regardless of clock divisions
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1), 2)
end

function test_manually_calculate_step_scale_number_step_1_different_speeds()
  setup()
  
  -- Channel at half speed (2), scale channel at standard (4)
  local channel = 2
  local clock_division_17 = 4
  local channel_division = 2
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2) -- Scale 2 on step 1
  program.add_step_scale_trig_lock(2, 3) -- Scale 3 on step 2
  
  -- Step 1 should still use step 1's scale even at different speeds
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1), 2)
  -- Step 2 should map to step 3 due to speed difference
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 2), 3)
end

function test_manually_calculate_step_scale_number_step_1_very_different_speeds()
  setup()
  
  -- Test with more extreme speed differences
  local channel = 2
  local clock_division_17 = 4
  local channel_division = 16 -- Much faster
  
  m_clock.set_channel_division(17, clock_division_17)
  m_clock.set_channel_division(channel, channel_division)
  
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2) -- Scale 2 on step 1
  program.add_step_scale_trig_lock(2, 3) -- Scale 3 on step 2
  
  -- Step 1 should still use step 1's scale even at very different speeds
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 1), 2)
  -- Later steps should map according to the speed ratio
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 2), 2)
  luaunit.assert_equals(step.manually_calculate_step_scale_number(channel, 5), 3)
end


function test_step_1_scale_and_params_processing()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  -- Set up a basic pattern with a note on step 1
  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up scale for step 1
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2) -- Scale 2 on step 1
  
  -- Process step 1
  step.handle(1, 1)
  
  -- Verify note output
  local note_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_not_nil(note_event, "No note event generated for step 1")
  -- Add specific note value assertion based on your scale 2
  luaunit.assert_equals(note_event[1], 60)
  luaunit.assert_equals(note_event[2], 100)
  luaunit.assert_equals(note_event[3], 1)

end

function test_step_1_params_with_same_clock_speeds()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  -- Set up pattern with step 1 trig lock
  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  local channel = program.get_channel(song_pattern, 1)

  local my_param_id = "my_param_id"

  params:add(my_param_id, {
    name = "name",
    val = -1
  })
  
  -- Add a MIDI CC parameter trig lock on step 1
  channel.trig_lock_params[1] = {
    type = "midi",
    cc_msb = 1,
    cc_min_value = 0,
    cc_max_value = 127,
    param_id = my_param_id,
    device_name = "test",
    id = 1
  }
  program.add_step_param_trig_lock_to_channel(channel, 1, 1, 64) -- CC value of 64 on step 1

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set different clock speeds
  m_clock.set_channel_division(17, 4)  -- Standard speed for global
  m_clock.set_channel_division(1, 4)   -- Standard speed for channel 1

  m_clock.init()
  m_clock:start()
  
  -- Verify MIDI CC was sent
  local cc_event = table.remove(midi_cc_events, 1)
  luaunit.assert_not_nil(cc_event, "No CC event generated for step 1")
  luaunit.assert_equals(cc_event[1], 1)  -- CC number
  luaunit.assert_equals(cc_event[2], 64) -- CC value
end

function test_step_1_params_with_different_clock_speeds()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  -- Set up pattern with step 1 trig lock
  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  local channel = program.get_channel(song_pattern, 1)

  local my_param_id = "my_param_id"

  params:add(my_param_id, {
    name = "name",
    val = -1
  })
  
  -- Add a MIDI CC parameter trig lock on step 1
  channel.trig_lock_params[1] = {
    type = "midi",
    cc_msb = 1,
    cc_min_value = 0,
    cc_max_value = 127,
    param_id = my_param_id,
    device_name = "test",
    id = 1
  }
  program.add_step_param_trig_lock_to_channel(channel, 1, 1, 64) -- CC value of 64 on step 1

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set different clock speeds
  m_clock.set_channel_division(17, 4)  -- Standard speed for global
  m_clock.set_channel_division(1, 8)   -- Standard speed for channel 1

  m_clock.init()
  m_clock:start()
  
  -- Verify MIDI CC was sent
  local cc_event = table.remove(midi_cc_events, 1)
  luaunit.assert_not_nil(cc_event, "No CC event generated for step 1")
  luaunit.assert_equals(cc_event[1], 1)  -- CC number
  luaunit.assert_equals(cc_event[2], 64) -- CC value
end

function test_step_1_processing_after_pattern_change()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  -- Set up pattern with step 1 note and trig lock
  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  
  -- Set up scale for step 1
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2)

  pattern.update_working_patterns()
  
  -- Process step 1, change pattern, then process step 1 again
  step.handle(1, 1)
  local first_note = table.remove(midi_note_on_events, 1)
  
  program.set_selected_song_pattern(2) -- Change pattern
  pattern.update_working_patterns()
  
  step.handle(1, 1)
  local second_note = table.remove(midi_note_on_events, 1)
  
  -- Both notes should be processed with step 1's scale
  luaunit.assert_equals(first_note[1], second_note[1])
end

function test_running_sequencer_step_1_scale()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  -- Set up pattern with notes on steps 1 and 2
  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.note_values[2] = 0
  test_pattern.lengths[1] = 1
  test_pattern.lengths[2] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[1] = 100
  test_pattern.velocity_values[2] = 100

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  
  -- Set up different scales for steps 1 and 2
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(1, 2) -- Scale 2 on step 1
  program.add_step_scale_trig_lock(2, 3) -- Scale 3 on step 2

  pattern.update_working_patterns()
  
  -- Start the clock and run for a few steps
  m_clock.init()
  m_clock:start()
  
  -- Run for 2 beats to capture both steps
  progress_clock_by_beats(2)
  
  -- Check the notes that were generated
  local first_note = table.remove(midi_note_on_events, 1)
  local second_note = table.remove(midi_note_on_events, 1)
  
  -- Verify notes were processed with correct scales
  luaunit.assert_not_nil(first_note, "No note generated for step 1")
  luaunit.assert_not_nil(second_note, "No note generated for step 2")
  -- Add assertions for expected note values based on scales 2 and 3
end

function test_step_param_processing_on_sequencer_start()
  setup()
  mock_random()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)

  -- Set up pattern with CC locks on steps 1 and 2
  local test_pattern = program.initialise_default_pattern()
  test_pattern.trig_values[1] = 1
  test_pattern.trig_values[2] = 1

  local channel = program.get_channel(song_pattern, 1)
  
  -- Add MIDI CC parameter trig locks
  channel.trig_lock_params[1] = {
    type = "midi",
    cc_msb = 1,
    cc_min_value = 0,
    cc_max_value = 127,
    param_id = "test_param",
    device_name = "test",
    id = 1
  }
  
  program.add_step_param_trig_lock_to_channel(channel, 1, 1, 64)  -- CC 64 on step 1
  program.add_step_param_trig_lock_to_channel(channel, 2, 1, 100) -- CC 100 on step 2

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set different clock speeds to match real-world scenario
  m_clock.set_channel_division(1, 8)   -- Double speed
  m_clock.set_channel_division(17, 4)  -- Normal speed

  -- Check sequencer start behavior
  m_clock.init()
  midi_cc_events = {}
  m_clock:start()
  
  -- Run for a few pulses to capture initial behavior
  for i = 1, 24 do  -- One beat
    m_clock.get_clock_lattice():pulse()
  end
  
  -- Should have seen step 1's CC (64) before any pulses
  local saw_initial_cc = false
  for _, event in ipairs(midi_cc_events) do
    if event[2] == 64 then
      saw_initial_cc = true
      break
    end
  end
  luaunit.assert_true(saw_initial_cc, "Should see step 1's CC (64) immediately on start")
  
  -- Clear events and run until we see a wrap
  midi_cc_events = {}
  local found_wrap = false
  
  for i = 1, 24*80 do  -- Run for many beats to catch a wrap
    m_clock.get_clock_lattice():pulse()
    
    if #midi_cc_events > 0 then
      local current_step = program.get_current_step_for_channel(1)
      for _, event in ipairs(midi_cc_events) do

        -- Check wrap behavior (step 64 should fire step 1's CC)
        if current_step == 64 and event[2] == 64 then
          found_wrap = true
        end
        -- Check look-ahead behavior (step 1 should fire step 2's CC)
        if current_step == 1 then
          luaunit.assert_equals(event[2], 100, "Step 1 should fire step 2's CC (100)")
        end
      end
      midi_cc_events = {}
    end
  end
  
  luaunit.assert_true(found_wrap, "Should see step 1's CC (64) at step 64 during wrap")
end

function test_note_mask_with_chords_no_scale_degree_effect()
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
  channel.chord_one_mask = 2  -- Major third
  channel.chord_two_mask = 4  -- Perfect fifth
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up scale with degree that would modify notes if active
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0  -- C
  scale.number = 1     -- Major scale
  scale.chord = 2      -- Second degree (which would modify the chord notes if active)

  -- Disable fully act on note masks
  params:set("quantiser_fully_act_on_note_masks", 1)
  
  step.handle(1, 1)
  
  -- Should get three note on events - all using raw intervals from mask
  local note_events = midi_note_on_events
  
  luaunit.assert_equals(#note_events, 3)
  luaunit.assert_equals(note_events[1][1], 60) -- C4 (mask value)
  luaunit.assert_equals(note_events[2][1], 64) -- E4 (C4 + 4 semitones)
  luaunit.assert_equals(note_events[3][1], 67) -- G4 (C4 + 7 semitones)
end

function test_note_mask_with_chords_with_scale_degree_effect()
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
  channel.chord_one_mask = 2  -- Major third
  channel.chord_two_mask = 4  -- Perfect fifth
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up scale with degree that would modify notes if active
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0  -- C
  scale.number = 1     -- Major scale
  scale.chord = 2      -- Second degree (which would modify the chord notes if active)

  -- Fully act on note masks
  params:set("quantiser_fully_act_on_note_masks", 2)
  
  step.handle(1, 1)
  
  -- Should get three note on events - all using raw intervals from mask
  local note_events = midi_note_on_events
  
  luaunit.assert_equals(#note_events, 3)
  luaunit.assert_equals(note_events[1][1], 62) -- D (mask value)
  luaunit.assert_equals(note_events[2][1], 65) -- F (C4 + 4 semitones)
  luaunit.assert_equals(note_events[3][1], 69) -- A (C4 + 7 semitones)
end

function test_note_mask_with_chords_and_arp_no_scale_degree_effect()
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
  channel.chord_one_mask = 2  -- Major third
  channel.chord_two_mask = 4  -- Perfect fifth
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up scale with degree that would modify notes if active
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0  -- C
  scale.number = 1     -- Major scale
  scale.chord = 2      -- Second degree (would modify if active)

  -- Enable arpeggio mode
  channel.trig_lock_params[1] = {id = "chord_arp", param_id = "chord_arp_1"}
  program.add_step_param_trig_lock(1, 1, 4) -- Standard division

  -- Disable fully act on note masks
  params:set("quantiser_fully_act_on_note_masks", 1)
  params:set("quantiser_fully_act_on_note_masks", 1)
  
  -- Initialize m_clock for arp timing
  m_clock.init()
  m_clock:start()
  
  -- First note
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60) -- C4 (mask value)
  
  progress_clock_by_beats(1)
  
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 64) -- E4 (C4 + 4 semitones)
  
  progress_clock_by_beats(1)

  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 67) -- G4 (C4 + 7 semitones)
end


function test_note_mask_with_chords_and_arp_scale_degree_effect()
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
  channel.chord_one_mask = 2  -- Major third
  channel.chord_two_mask = 4  -- Perfect fifth
  
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)
  pattern.update_working_patterns()

  -- Set up scale with degree that would modify notes if active
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0  -- C
  scale.number = 1     -- Major scale
  scale.chord = 2      -- Second degree (would modify if active)

  -- Enable arpeggio mode
  channel.trig_lock_params[1] = {id = "chord_arp", param_id = "chord_arp_1"}
  program.add_step_param_trig_lock(1, 1, 4) -- Standard division

  -- Disable fully act on note masks
  params:set("quantiser_fully_act_on_note_masks", 2)
  
  -- Initialize m_clock for arp timing
  m_clock.init()
  m_clock:start()
  
  -- First note
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62) -- C4 (mask value)
  
  progress_clock_by_beats(1)
  
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65) -- E4 (C4 + 4 semitones)
  
  progress_clock_by_beats(1)

  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 69) -- G4 (C4 + 7 semitones)
end