step = include("mosaic/lib/step")
pattern = include("mosaic/lib/pattern")

local m_clock = include("mosaic/lib/clock/m_clock")
local quantiser = include("mosaic/lib/quantiser")

-- Mocks
include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/norns_mock")
include("mosaic/lib/tests/helpers/mocks/channel_sequence_page_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_mock")

local function setup()
  program.init()
  globals.reset()
  params.reset()
end

local function clock_setup()
  m_clock.init()
  m_clock:start()
end

local function progress_clock_by_beats(b)
  for i = 1, (24 * b) do
    m_clock.get_clock_lattice():pulse()
  end
end

local function progress_clock_by_pulses(p)
  for i = 1, p do
    m_clock.get_clock_lattice():pulse()
  end
end

local swing_to_pulses = {
  -- Negative swing values
  {swing = -49, even_pulses = 36, odd_pulses = 12},
  {swing = -45, even_pulses = 35, odd_pulses = 13},
  {swing = -41, even_pulses = 34, odd_pulses = 14},
  {swing = -37, even_pulses = 33, odd_pulses = 15},
  {swing = -33, even_pulses = 32, odd_pulses = 16},
  {swing = -29, even_pulses = 31, odd_pulses = 17},
  {swing = -25, even_pulses = 30, odd_pulses = 18},
  {swing = -21, even_pulses = 29, odd_pulses = 19},
  {swing = -17, even_pulses = 28, odd_pulses = 20},
  {swing = -13, even_pulses = 27, odd_pulses = 21},
  {swing = -9, even_pulses = 26, odd_pulses = 22},
  {swing = -5, even_pulses = 25, odd_pulses = 23},
  {swing = -1, even_pulses = 24, odd_pulses = 24},
  -- -- -- -- Zero swing (no change)
  {swing = 0, even_pulses = 24, odd_pulses = 24},
  -- -- -- -- Positive swing values
  {swing = 1, even_pulses = 24, odd_pulses = 24},
  {swing = 5, even_pulses = 23, odd_pulses = 25},
  {swing = 9, even_pulses = 22, odd_pulses = 26},
  {swing = 13, even_pulses = 21, odd_pulses = 27},
  {swing = 17, even_pulses = 20, odd_pulses = 28},
  {swing = 21, even_pulses = 19, odd_pulses = 29},
  {swing = 25, even_pulses = 18, odd_pulses = 30},
  {swing = 29, even_pulses = 17, odd_pulses = 31},
  {swing = 33, even_pulses = 16, odd_pulses = 32},
  {swing = 37, even_pulses = 15, odd_pulses = 33},
  {swing = 41, even_pulses = 14, odd_pulses = 34},
  {swing = 45, even_pulses = 13, odd_pulses = 35},
  {swing = 49, even_pulses = 12, odd_pulses = 36}
}

function test_swing_maintains_lengths_step_two()
  for _, test_case in ipairs(swing_to_pulses) do
    local test_pattern
    
    setup()
    local song_pattern = 1
    program.set_selected_song_pattern(1)
    test_pattern = program.initialise_default_pattern()

    test_pattern.note_values[2] = 0
    test_pattern.lengths[2] = 2
    test_pattern.trig_values[2] = 1
    test_pattern.velocity_values[2] = 20

    program.get_song_pattern(song_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

    program.get_channel(program.get().selected_song_pattern, 1).swing = test_case.swing

    pattern.update_working_patterns()

    clock_setup()

    local note_on_event = table.remove(midi_note_on_events)

    luaunit.assert_nil(note_on_event) -- No note on step 1

    progress_clock_by_pulses(test_case.odd_pulses)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 20)
    luaunit.assert_equals(note_on_event[3], 1)

    
    progress_clock_by_pulses(test_case.even_pulses)

    -- no note off beat 2
    local note_off_event = table.remove(midi_note_off_events)

    luaunit.assert_nil(note_off_event) -- test lengths aren't misfiring


    progress_clock_by_pulses(test_case.odd_pulses)
    
    local note_off_event = table.remove(midi_note_off_events)

    luaunit.assert_equals(note_off_event[1], 60)
    luaunit.assert_equals(note_off_event[2], 20)
    luaunit.assert_equals(note_off_event[3], 1)
  end
end


function test_swing_maintains_lengths_across_multiple_steps_all_swings()


  for _, test_case in ipairs(swing_to_pulses) do
    local test_pattern
    
    setup()
    local song_pattern = 1
    program.set_selected_song_pattern(1)
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

    program.get_song_pattern(song_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

    program.get_channel(program.get().selected_song_pattern, 1).swing = test_case.swing

    pattern.update_working_patterns()

    clock_setup()

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 20)
    luaunit.assert_equals(note_on_event[3], 1)

    local note_off_event = table.remove(midi_note_off_events, 1)

    luaunit.assert_nil(note_off_event) -- test lengths aren't misfiring

    progress_clock_by_pulses(test_case.odd_pulses)

  
    local note_off_event = table.remove(midi_note_off_events, 1)

    luaunit.assert_equals(note_off_event[1], 60)
    luaunit.assert_equals(note_off_event[2], 20)
    luaunit.assert_equals(note_off_event[3], 1)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 62)
    luaunit.assert_equals(note_on_event[2], 21)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_pulses(test_case.even_pulses)

    local note_off_event = table.remove(midi_note_off_events, 1)

    luaunit.assert_equals(note_off_event[1], 62)
    luaunit.assert_equals(note_off_event[2], 21)
    luaunit.assert_equals(note_off_event[3], 1)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 64)
    luaunit.assert_equals(note_on_event[2], 22)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_pulses(test_case.odd_pulses)

    local note_off_event = table.remove(midi_note_off_events, 1)

    luaunit.assert_equals(note_off_event[1], 64)
    luaunit.assert_equals(note_off_event[2], 22)
    luaunit.assert_equals(note_off_event[3], 1)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 65)
    luaunit.assert_equals(note_on_event[2], 23)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_pulses(test_case.even_pulses)

    local note_off_event = table.remove(midi_note_off_events, 1)

    luaunit.assert_equals(note_off_event[1], 65)
    luaunit.assert_equals(note_off_event[2], 23)
    luaunit.assert_equals(note_off_event[3], 1)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 24)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_pulses(test_case.odd_pulses)

    local note_off_event = table.remove(midi_note_off_events, 1)

    luaunit.assert_equals(note_off_event[1], 60)
    luaunit.assert_equals(note_off_event[2], 24)
    luaunit.assert_equals(note_off_event[3], 1)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 62)
    luaunit.assert_equals(note_on_event[2], 25)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_pulses(test_case.even_pulses)

    local note_off_event = table.remove(midi_note_off_events, 1)

    luaunit.assert_equals(note_off_event[1], 62)
    luaunit.assert_equals(note_off_event[2], 25)
    luaunit.assert_equals(note_off_event[3], 1)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 64)
    luaunit.assert_equals(note_on_event[2], 26)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_pulses(test_case.odd_pulses)

    local note_off_event = table.remove(midi_note_off_events, 1)

    luaunit.assert_equals(note_off_event[1], 64)
    luaunit.assert_equals(note_off_event[2], 26)
    luaunit.assert_equals(note_off_event[3], 1)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 65)
    luaunit.assert_equals(note_on_event[2], 27)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_pulses(test_case.even_pulses)

    local note_off_event = table.remove(midi_note_off_events, 1)

    luaunit.assert_equals(note_off_event[1], 65)
    luaunit.assert_equals(note_off_event[2], 27)
    luaunit.assert_equals(note_off_event[3], 1)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 28)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_pulses(test_case.odd_pulses)

    local note_off_event = table.remove(midi_note_off_events, 1)

    luaunit.assert_equals(note_off_event[1], 60)
    luaunit.assert_equals(note_off_event[2], 28)
    luaunit.assert_equals(note_off_event[3], 1)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 62)
    luaunit.assert_equals(note_on_event[2], 29)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_pulses(test_case.even_pulses)

    local note_off_event = table.remove(midi_note_off_events, 1)

    luaunit.assert_equals(note_off_event[1], 62)
    luaunit.assert_equals(note_off_event[2], 29)
    luaunit.assert_equals(note_off_event[3], 1)
  end
end


function test_drunk_shuffle_amount_100()
  local test_pattern
  
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  program.get_channel(program.get().selected_song_pattern, 1).swing = 0

  program.get_channel(program.get().selected_song_pattern, 1).swing_shuffle_type = 2
  program.get_channel(program.get().selected_song_pattern, 1).shuffle_basis = 1
  program.get_channel(program.get().selected_song_pattern, 1).shuffle_feel = 1
  program.get_channel(program.get().selected_song_pattern, 1).shuffle_amount = 100

  pattern.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 20)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(32)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 60)
  luaunit.assert_equals(note_off_event[2], 20)
  luaunit.assert_equals(note_off_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 21)
  luaunit.assert_equals(note_on_event[3], 1)

  
  progress_clock_by_pulses(21)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 62)
  luaunit.assert_equals(note_off_event[2], 21)
  luaunit.assert_equals(note_off_event[3], 1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 22)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(22)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 64)
  luaunit.assert_equals(note_off_event[2], 22)
  luaunit.assert_equals(note_off_event[3], 1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 23)
  luaunit.assert_equals(note_on_event[3], 1)


  progress_clock_by_pulses(5)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_nil(note_off_event) -- TODO Note off events are firing too early

  progress_clock_by_pulses(16)

  local note_off_event = table.remove(midi_note_off_events, 1)

  luaunit.assert_equals(note_off_event[1], 65)
  luaunit.assert_equals(note_off_event[2], 23)
  luaunit.assert_equals(note_off_event[3], 1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 24)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(32)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 25)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(21)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 26)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(22)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 27)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(21)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 28)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(31)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_pulses(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 29)
  luaunit.assert_equals(note_on_event[3], 1)

end



function test_drunk_shuffle_amount_0()
  local test_pattern
  
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  program.get_channel(program.get().selected_song_pattern, 1).swing = 0

  program.get_channel(program.get().selected_song_pattern, 1).swing_shuffle_type = 2
  program.get_channel(program.get().selected_song_pattern, 1).shuffle_basis = 1
  program.get_channel(program.get().selected_song_pattern, 1).shuffle_feel = 1
  program.get_channel(program.get().selected_song_pattern, 1).shuffle_amount = 0

  pattern.update_working_patterns()

  clock_setup()

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 20)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(24)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 21)
  luaunit.assert_equals(note_on_event[3], 1)
  
  progress_clock_by_pulses(24)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 22)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(24)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 23)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(24)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 24)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(24)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 25)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(24)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 26)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(24)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 27)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(24)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 28)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(23)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_nil(note_on_event)

  progress_clock_by_pulses(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 29)
  luaunit.assert_equals(note_on_event[3], 1)

end

function test_drunk_shuffle_amount_75()
  local test_pattern
  
  setup()
  local song_pattern = 1
  program.set_selected_song_pattern(1)
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

  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_song_pattern(song_pattern).channels[1].selected_patterns, 1)

  program.get_channel(program.get().selected_song_pattern, 1).swing = 0

  program.get_channel(program.get().selected_song_pattern, 1).swing_shuffle_type = 2
  program.get_channel(program.get().selected_song_pattern, 1).shuffle_basis = 1
  program.get_channel(program.get().selected_song_pattern, 1).shuffle_feel = 1
  program.get_channel(program.get().selected_song_pattern, 1).shuffle_amount = 75

  pattern.update_working_patterns()

  clock_setup()

  -- Store the timing values from first pattern for comparison
  local first_pattern_timings = {}

  local note_on_event = table.remove(midi_note_on_events, 1)
  first_pattern_timings[1] = 0 -- First note happens immediately

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 20)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(30)
  first_pattern_timings[2] = 30

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 21)
  luaunit.assert_equals(note_on_event[3], 1)

  
  progress_clock_by_pulses(24)
  first_pattern_timings[3] = 24

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 22)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(20)
  first_pattern_timings[4] = 20
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 23)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(22)
  first_pattern_timings[5] = 22
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 24)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(30)
  first_pattern_timings[6] = 30
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 25)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(22)
  first_pattern_timings[7] = 22
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 26)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(22)
  first_pattern_timings[8] = 22
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 27)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(22)
  first_pattern_timings[9] = 22
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 28)
  luaunit.assert_equals(note_on_event[3], 1)

  -- Progress through remaining steps to get back to step 1
  -- We're at step 9, need to progress through steps 10-64 and get to step 1
  -- Each step is 24 pulses (default ppqn)
  progress_clock_by_pulses(24 * ((64 - 9) + 1))

  -- Second pattern iteration - verify timing matches first pattern
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 20)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(30)
  luaunit.assert_equals(30, first_pattern_timings[2], "Second pattern timing mismatch at step 2")
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 21)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(24)
  luaunit.assert_equals(24, first_pattern_timings[3], "Second pattern timing mismatch at step 3")
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 22)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(20)
  luaunit.assert_equals(20, first_pattern_timings[4], "Second pattern timing mismatch at step 4")
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 23)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(22)
  luaunit.assert_equals(22, first_pattern_timings[5], "Second pattern timing mismatch at step 5")
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 24)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(30)
  luaunit.assert_equals(30, first_pattern_timings[6], "Second pattern timing mismatch at step 6")
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 25)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(22)
  luaunit.assert_equals(22, first_pattern_timings[7], "Second pattern timing mismatch at step 7")
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 26)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(22)
  luaunit.assert_equals(22, first_pattern_timings[8], "Second pattern timing mismatch at step 8")
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 27)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_pulses(22)
  luaunit.assert_equals(22, first_pattern_timings[9], "Second pattern timing mismatch at step 9")
  
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 28)
  luaunit.assert_equals(note_on_event[3], 1)
end


function test_offset_global_cap_uses_channel_clock_and_relative_steps()
  local bounds = {{1,4,1},{1,4,3},{2,4,2},{3,6,2},{16,19,3},{62,64,2},{63,64,1},{63,64,2},{1,64,64}}
  local rates = {{"clock_multiplication",1,24},{"clock_multiplication",2,12},{"clock_division",2,48},{"clock_multiplication",3,8},{"clock_division",3,72}}
  for _, b in ipairs(bounds) do
    for _, rate in ipairs(rates) do
      setup()
      local first,last,cap=b[1],b[2],b[3]
      local song=program.get_selected_song_pattern()
      song.global_pattern_length=cap
      local authored=program.initialise_default_pattern()
      for i=1,64 do
        authored.trig_values[i]=1;authored.note_values[i]=0
        authored.velocity_values[i]=i;authored.lengths[i]=1
      end
      song.patterns[1]=authored;fn.add_to_set(song.channels[1].selected_patterns,1)
      for _,number in ipairs({1,17}) do
        local channel=song.channels[number]
        channel.start_trig={((first-1)%16)+1,math.floor((first-1)/16)+4}
        channel.end_trig={((last-1)%16)+1,math.floor((last-1)/16)+4}
        channel.clock_mods={type=rate[1],value=rate[2]}
      end
      pattern.update_working_patterns();clock_setup()
      local length=math.min(last-first+1,cap)
      -- Include startup and several complete loops/global boundaries. Observe
      -- actual MIDI plus scale playhead; no copied scheduler helper is used.
      local count=math.max(length*3+1,math.ceil(cap*24*3/rate[3])+1)
      for n=0,count-1 do
        local expected=first+(n%length)
        local event=table.remove(midi_note_on_events,1)
        luaunit.assert_not_nil(event)
        luaunit.assert_equals(event,{60,expected,1,1})
        luaunit.assert_equals(#midi_note_on_events,0)
        luaunit.assert_equals(program.get_current_step_for_channel(1),expected)
        luaunit.assert_equals(program.get_current_step_for_channel(17),expected)
        progress_clock_by_pulses(rate[3])
      end
    end
  end
end

-- Stop/start must use final stored musical settings, independent of edit order.
-- Only hardware stop sinks are stubbed; model, scheduler and step code are real.
local function with_restart_sinks(body)
  local old_testing = testing
  testing = true -- This fixture supplies every native-lattice pulse explicitly.
  local old_clock = _G.m_clock
  _G.m_clock = m_clock -- Production module functions share this global table.
  local old_handler = norns_param_state_handler
  norns_param_state_handler = include("mosaic/lib/devices/norns_param_state_handler")
  local old_stop = m_midi.stop
  local old_nb = nb
  local old_nb_stop = nb and nb.stop_all
  nb = nb or {}
  nb.stop_all = function() end
  m_midi.stop = function() end
  local ok, err = pcall(body)
  m_midi.stop = old_stop
  norns_param_state_handler = old_handler
  _G.m_clock = old_clock
  testing = old_testing
  nb.stop_all = old_nb_stop
  nb = old_nb
  if not ok then error(err) end
end

function test_stopped_shuffle_start_rebuilds_both_processors_only_when_stopped()
  with_restart_sinks(function()
    setup();m_clock.init();m_clock:stop()
    local channel = program.get_channel(1, 1)
    channel.swing_shuffle_type=2;channel.shuffle_feel=1
    channel.shuffle_basis=2;channel.shuffle_amount=100
    m_clock.init()
    channel.shuffle_basis=3;m_clock.set_channel_shuffle_basis(1,3)
    m_clock:start()
    local lattice=m_clock.get_clock_lattice()
    local on=m_clock.channel_1_clock
    local off=on.end_of_clock_processor
    -- Fresh Drunk/5 preview: 38.4 + 0.5 -> 38, residual0.9.
    luaunit.assertAlmostEquals(on.ppqn_error,0.9,1e-10)
    luaunit.assertAlmostEquals(off.ppqn_error,0.9,1e-10)
    progress_clock_by_pulses(5)
    local phase,carry=on.phase,on.ppqn_error
    m_clock:start() -- An already-playing Start must not rebuild or rewind.
    luaunit.assertEquals(m_clock.get_clock_lattice(),lattice)
    luaunit.assertEquals(m_clock.channel_1_clock,on)
    luaunit.assertEquals(on.phase,phase)
    luaunit.assertEquals(on.ppqn_error,carry)
    m_clock:stop()
  end)
end

function test_shuffle_stopped_edit_history_and_replay_have_identical_midi_pulses()
  with_restart_sinks(function()
    local expected={0,39,58,77,96,135,154,173,192,231,250,269,288,327,346,365,384}
    for _,history in ipairs({false,true}) do
      setup();m_clock.init();m_clock:stop()
      local song=program.get_song_pattern(1)
      local channel=program.get_channel(1,1)
      local source=program.initialise_default_pattern()
      for i=1,4 do
        source.note_values[i]=0;source.lengths[i]=1
        source.trig_values[i]=1;source.velocity_values[i]=100
      end
      song.patterns[1]=source;fn.add_to_set(channel.selected_patterns,1)
      channel.start_trig={1,4};channel.end_trig={4,4}
      channel.swing_shuffle_type=2;channel.shuffle_feel=1
      channel.shuffle_basis=history and 1 or 3;channel.shuffle_amount=100
      pattern.update_working_patterns();m_clock.init()
      if history then
        channel.shuffle_basis=2;m_clock.set_channel_shuffle_basis(1,2)
        channel.shuffle_basis=3;m_clock.set_channel_shuffle_basis(1,3)
        channel.shuffle_amount=0;m_clock.set_channel_shuffle_amount(1,0)
        channel.shuffle_amount=100;m_clock.set_channel_shuffle_amount(1,100)
      end
      for replay=1,2 do
        midi_note_on_events={};midi_note_off_events={}
        m_clock:start()
        local seen={}
        for tick=0,384 do
          local before=#midi_note_on_events
          progress_clock_by_pulses(1)
          if #midi_note_on_events>before then
            luaunit.assertEquals(#midi_note_on_events,before+1)
            seen[#seen+1]=tick
          end
        end
        luaunit.assertEquals(seen,expected)
        luaunit.assertEquals(#midi_note_off_events,#seen-1)
        -- Final hardware Stop release is covered by native note_pairs;
        -- this fixture stubs the hardware stop sinks.
        m_clock:stop()
      end
    end
  end)
end


function test_external_start_resets_active_transport_and_releases()
  with_restart_sinks(function()
    setup();m_clock.init();m_clock:stop();m_clock:start(true)
    local previous=m_clock.get_clock_lattice()
    progress_clock_by_pulses(30)
    luaunit.assertTrue(previous.transport>1)
    local releases=0
    m_midi.stop=function() releases=releases+1 end
    m_clock:start(true)
    local restarted=m_clock.get_clock_lattice()
    luaunit.assertNotEquals(restarted,previous)
    luaunit.assertEquals(restarted.transport,1)
    luaunit.assertEquals(releases,1)
    luaunit.assertTrue(m_clock.is_playing())
    m_clock:start() -- Local already-playing Start retains the transport.
    luaunit.assertEquals(m_clock.get_clock_lattice(),restarted)
    luaunit.assertEquals(releases,1)
    m_clock:stop()
  end)
end


local function boundary_lifecycle_case(operation, activated)
  with_restart_sinks(function()
    local old_midi, old_run, old_cancel = clock.midi, clock.run, clock.cancel
    local old_start, old_stop = m_midi.start, m_midi.stop
    local subscribers, threads, id = {}, {}, 0
    local starts, stops = 0, 0
    clock.midi = {
      subscribe_output=function(callbacks) id=id+1;subscribers[id]=callbacks;return id end,
      cancel_output=function(handle) subscribers[handle]=nil end
    }
    clock.run=function(body)
      id=id+1;local handle=id;threads[handle]=coroutine.create(body)
      local ok,err=coroutine.resume(threads[handle]);assert(ok,err);return handle
    end
    clock.cancel=function(handle)threads[handle]=nil end
    m_midi.start=function()starts=starts+1 end
    m_midi.stop=function()stops=stops+1 end
    local ok,err=pcall(function()
      setup();m_clock.init();m_clock:stop();params:set("clock_midi_out_1",1)
      m_clock:start()
      local _, callbacks = next(subscribers);luaunit.assertNotNil(callbacks)
      if activated then callbacks.before();callbacks.after(1,0) end
      stops=0
      m_clock[operation]()
      luaunit.assertNil(next(subscribers), "Direct lifecycle call left native subscription")
      luaunit.assertNil(next(threads), "Direct lifecycle call left intermediate scheduler")
      luaunit.assertFalse(m_clock.is_playing())
      luaunit.assertEquals(stops,1,"Lifecycle replacement must release held voices through Stop")
      -- Already-captured old callbacks must remain inert after replacement.
      callbacks.before();callbacks.after(10,0)
      luaunit.assertEquals(starts,activated and 1 or 0)
      luaunit.assertFalse(m_clock.get_clock_lattice().enabled)
    end)
    m_clock:stop()
    clock.midi,clock.run,clock.cancel=old_midi,old_run,old_cancel
    m_midi.start,m_midi.stop=old_start,old_stop
    if not ok then error(err) end
  end)
end
function test_boundary_pending_direct_init_cleans_transport() boundary_lifecycle_case("init",false) end
function test_boundary_active_direct_init_cleans_transport() boundary_lifecycle_case("init",true) end
function test_boundary_pending_direct_reset_cleans_transport() boundary_lifecycle_case("reset",false) end
function test_boundary_active_direct_reset_cleans_transport() boundary_lifecycle_case("reset",true) end
