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


local swing_to_pulses = {
  {zero_offset_pulses = 0, swing = 1, even_pulses = 23, odd_pulses = 25},
  {zero_offset_pulses = 0, swing = 2, even_pulses = 23, odd_pulses = 25},
  {zero_offset_pulses = 1, swing = 3, even_pulses = 23, odd_pulses = 25},
  {zero_offset_pulses = 1, swing = 4, even_pulses = 23, odd_pulses = 25},
  {zero_offset_pulses = 1, swing = 5, even_pulses = 21, odd_pulses = 27},
  {zero_offset_pulses = 1, swing = 6, even_pulses = 21, odd_pulses = 27},
  {zero_offset_pulses = 2, swing = 7, even_pulses = 21, odd_pulses = 27},
  {zero_offset_pulses = 2, swing = 8, even_pulses = 21, odd_pulses = 27},
  {zero_offset_pulses = 2, swing = 9, even_pulses = 19, odd_pulses = 29},
  {zero_offset_pulses = 2, swing = 10, even_pulses = 19, odd_pulses = 29},
  {zero_offset_pulses = 3, swing = 11, even_pulses = 18, odd_pulses = 30},
  {zero_offset_pulses = 3, swing = 12, even_pulses = 18, odd_pulses = 30},
  {zero_offset_pulses = 3, swing = 13, even_pulses = 17, odd_pulses = 31},
  {zero_offset_pulses = 3, swing = 14, even_pulses = 17, odd_pulses = 31},
  {zero_offset_pulses = 4, swing = 15, even_pulses = 17, odd_pulses = 31},
  {zero_offset_pulses = 4, swing = 16, even_pulses = 17, odd_pulses = 31},
  {zero_offset_pulses = 4, swing = 17, even_pulses = 16, odd_pulses = 32},
  {zero_offset_pulses = 4, swing = 18, even_pulses = 16, odd_pulses = 32},
  {zero_offset_pulses = 5, swing = 19, even_pulses = 15, odd_pulses = 33},
  {zero_offset_pulses = 5, swing = 20, even_pulses = 15, odd_pulses = 33},
  {zero_offset_pulses = 5, swing = 21, even_pulses = 14, odd_pulses = 34},
  {zero_offset_pulses = 5, swing = 22, even_pulses = 14, odd_pulses = 34},
  {zero_offset_pulses = 6, swing = 23, even_pulses = 13, odd_pulses = 35},
  {zero_offset_pulses = 6, swing = 24, even_pulses = 13, odd_pulses = 35},
  {zero_offset_pulses = 6, swing = 25, even_pulses = 12, odd_pulses = 36},
  {zero_offset_pulses = 6, swing = 26, even_pulses = 12, odd_pulses = 36},
  {zero_offset_pulses = 6, swing = 27, even_pulses = 11, odd_pulses = 37},
  {zero_offset_pulses = 7, swing = 28, even_pulses = 11, odd_pulses = 37},
  {zero_offset_pulses = 7, swing = 29, even_pulses = 10, odd_pulses = 38},
  {zero_offset_pulses = 7, swing = 30, even_pulses = 10, odd_pulses = 38},
  {zero_offset_pulses = 7, swing = 31, even_pulses = 9, odd_pulses = 39},
  {zero_offset_pulses = 8, swing = 32, even_pulses = 9, odd_pulses = 39},
  {zero_offset_pulses = 8, swing = 33, even_pulses = 8, odd_pulses = 40},
  {zero_offset_pulses = 8, swing = 34, even_pulses = 8, odd_pulses = 40},
  {zero_offset_pulses = 8, swing = 35, even_pulses = 7, odd_pulses = 41},
  {zero_offset_pulses = 9, swing = 36, even_pulses = 7, odd_pulses = 41},
  {zero_offset_pulses = 9, swing = 37, even_pulses = 6, odd_pulses = 42},
  {zero_offset_pulses = 9, swing = 38, even_pulses = 6, odd_pulses = 42},
  {zero_offset_pulses = 9, swing = 39, even_pulses = 5, odd_pulses = 43},
  {zero_offset_pulses = 10, swing = 40, even_pulses = 5, odd_pulses = 43},
  {zero_offset_pulses = 10, swing = 41, even_pulses = 4, odd_pulses = 44},
  {zero_offset_pulses = 10, swing = 42, even_pulses = 4, odd_pulses = 44},
  {zero_offset_pulses = 10, swing = 43, even_pulses = 3, odd_pulses = 45},
  {zero_offset_pulses = 11, swing = 44, even_pulses = 3, odd_pulses = 45},
  {zero_offset_pulses = 11, swing = 45, even_pulses = 2, odd_pulses = 46},
  {zero_offset_pulses = 11, swing = 46, even_pulses = 2, odd_pulses = 46},
  {zero_offset_pulses = 11, swing = 47, even_pulses = 1, odd_pulses = 47},
  {zero_offset_pulses = 12, swing = 48, even_pulses = 1, odd_pulses = 47},
  {zero_offset_pulses = 12, swing = 49, even_pulses = 1, odd_pulses = 47}
} 

-- local swing_to_pulses = {
--   -- {zero_offset_pulses = 0, swing = 1, even_pulses = 23, odd_pulses = 25},
--   -- {zero_offset_pulses = 0, swing = 2, even_pulses = 23, odd_pulses = 25},
--   -- {zero_offset_pulses = 0, swing = 3, even_pulses = 23, odd_pulses = 25},
--   -- {zero_offset_pulses = 0, swing = 4, even_pulses = 23, odd_pulses = 25},
--   -- {zero_offset_pulses = 1, swing = 5, even_pulses = 21, odd_pulses = 27},
--   -- {zero_offset_pulses = 1, swing = 6, even_pulses = 21, odd_pulses = 27},
--   -- {zero_offset_pulses = 1, swing = 7, even_pulses = 21, odd_pulses = 27},
--   -- {zero_offset_pulses = 1, swing = 8, even_pulses = 21, odd_pulses = 27},
--   -- {zero_offset_pulses = 2, swing = 9, even_pulses = 19, odd_pulses = 29},
--   -- {zero_offset_pulses = 2, swing = 10, even_pulses = 19, odd_pulses = 29},
--   -- {zero_offset_pulses = 2, swing = 11, even_pulses = 18, odd_pulses = 30},
--   -- {zero_offset_pulses = 2, swing = 12, even_pulses = 18, odd_pulses = 30},
--   -- {zero_offset_pulses = 3, swing = 13, even_pulses = 17, odd_pulses = 31},
--   -- {zero_offset_pulses = 3, swing = 14, even_pulses = 17, odd_pulses = 31},
--   -- {zero_offset_pulses = 3, swing = 15, even_pulses = 17, odd_pulses = 31},
--   -- {zero_offset_pulses = 3, swing = 16, even_pulses = 17, odd_pulses = 31},
--   -- {zero_offset_pulses = 4, swing = 17, even_pulses = 16, odd_pulses = 32},
--   -- {zero_offset_pulses = 4, swing = 18, even_pulses = 16, odd_pulses = 32},
--   -- {zero_offset_pulses = 4, swing = 19, even_pulses = 15, odd_pulses = 33},
--   -- {zero_offset_pulses = 4, swing = 20, even_pulses = 15, odd_pulses = 33},
--   -- {zero_offset_pulses = 5, swing = 21, even_pulses = 14, odd_pulses = 34},
--   -- {zero_offset_pulses = 5, swing = 22, even_pulses = 14, odd_pulses = 34},
--   -- {zero_offset_pulses = 5, swing = 23, even_pulses = 13, odd_pulses = 35},
--   -- {zero_offset_pulses = 5, swing = 24, even_pulses = 13, odd_pulses = 35},
--   -- {zero_offset_pulses = 6, swing = 25, even_pulses = 12, odd_pulses = 36},
--   -- {zero_offset_pulses = 6, swing = 26, even_pulses = 12, odd_pulses = 36},
--   -- {zero_offset_pulses = 6, swing = 27, even_pulses = 11, odd_pulses = 37},
--   -- {zero_offset_pulses = 6, swing = 28, even_pulses = 11, odd_pulses = 37},
--   -- {zero_offset_pulses = 6, swing = 29, even_pulses = 10, odd_pulses = 38},
--   {zero_offset_pulses = 7, swing = 30, even_pulses = 10, odd_pulses = 38},
--   -- {zero_offset_pulses = 7, swing = 31, even_pulses = 9, odd_pulses = 39},
--   -- {zero_offset_pulses = 7, swing = 32, even_pulses = 9, odd_pulses = 39},
--   -- {zero_offset_pulses = 7, swing = 33, even_pulses = 8, odd_pulses = 40},
--   -- {zero_offset_pulses = 8, swing = 34, even_pulses = 8, odd_pulses = 40},
--   -- {zero_offset_pulses = 8, swing = 35, even_pulses = 7, odd_pulses = 41},
--   -- {zero_offset_pulses = 8, swing = 36, even_pulses = 7, odd_pulses = 41},
--   -- {zero_offset_pulses = 8, swing = 37, even_pulses = 6, odd_pulses = 42},
--   -- {zero_offset_pulses = 9, swing = 38, even_pulses = 6, odd_pulses = 42},
--   -- {zero_offset_pulses = 9, swing = 39, even_pulses = 5, odd_pulses = 43},
--   -- {zero_offset_pulses = 9, swing = 40, even_pulses = 5, odd_pulses = 43},
--   -- {zero_offset_pulses = 9, swing = 41, even_pulses = 4, odd_pulses = 44},
--   -- {zero_offset_pulses = 10, swing = 42, even_pulses = 4, odd_pulses = 44},
--   -- {zero_offset_pulses = 10, swing = 43, even_pulses = 3, odd_pulses = 45},
--   -- {zero_offset_pulses = 10, swing = 44, even_pulses = 3, odd_pulses = 45},
--   -- {zero_offset_pulses = 10, swing = 45, even_pulses = 2, odd_pulses = 46},
--   -- {zero_offset_pulses = 11, swing = 46, even_pulses = 2, odd_pulses = 46},
--   -- {zero_offset_pulses = 11, swing = 47, even_pulses = 1, odd_pulses = 47},
--   -- {zero_offset_pulses = 11, swing = 48, even_pulses = 1, odd_pulses = 47},
--   -- {zero_offset_pulses = 11, swing = 49, even_pulses = 1, odd_pulses = 47}
-- } 

function test_swing_maintains_lengths_step_two()
  for _, test_case in ipairs(swing_to_pulses) do
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

    program.get_channel(1).swing = test_case.swing

    pattern_controller.update_working_patterns()

    clock_setup()

    progress_clock_by_pulses(test_case.zero_offset_pulses)


    -- No note on beat 1

    progress_clock_by_pulses(test_case.odd_pulses)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 20)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_pulses(test_case.even_pulses)

    -- no note off beat 2

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

    program.get_channel(1).swing = test_case.swing

    pattern_controller.update_working_patterns()

    clock_setup()

    progress_clock_by_pulses(test_case.zero_offset_pulses)

    local note_on_event = table.remove(midi_note_on_events, 1)

    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 20)
    luaunit.assert_equals(note_on_event[3], 1)

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


-- function test_shuffle()
--   for _, test_case in ipairs(swing_to_pulses) do
--     local test_pattern
    
--     setup()
--     local sequencer_pattern = 1
--     program.set_selected_sequencer_pattern(1)
--     test_pattern = program.initialise_default_pattern()

--     test_pattern.note_values[1] = 0
--     test_pattern.lengths[1] = 1
--     test_pattern.trig_values[1] = 1
--     test_pattern.velocity_values[1] = 20

--     test_pattern.note_values[2] = 0
--     test_pattern.lengths[2] = 1
--     test_pattern.trig_values[2] = 1
--     test_pattern.velocity_values[2] = 21

--     test_pattern.note_values[3] = 0
--     test_pattern.lengths[3] = 1
--     test_pattern.trig_values[3] = 1
--     test_pattern.velocity_values[3] = 22

--     program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
--     fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)

--     program.get_channel(1).swing = 20
--     -- program.get_channel(1).shuffle_basis = 1
--     -- program.get_channel(1).shuffle_feel = 1

--     pattern_controller.update_working_patterns()

--     clock_setup()

--     progress_clock_by_pulses(100)

--     local note_on_event = table.remove(midi_note_on_events, 1)

--     luaunit.assert_equals(note_on_event[1], 60)
--     luaunit.assert_equals(note_on_event[2], 20)
--     luaunit.assert_equals(note_on_event[3], 1)

--     progress_clock_by_pulses(1)

    
--     local note_off_event = table.remove(midi_note_off_events)

--     luaunit.assert_equals(note_off_event[1], 60)
--     luaunit.assert_equals(note_off_event[2], 20)
--     luaunit.assert_equals(note_off_event[3], 1)
--   end
-- end

