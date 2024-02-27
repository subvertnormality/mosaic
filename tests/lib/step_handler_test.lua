local step_handler = include("mosaic/lib/step_handler")
pattern_controller = include("mosaic/lib/pattern_controller")

include("mosaic/tests/helpers/mocks/device_map_mock")
include("mosaic/tests/helpers/mocks/channel_edit_page_ui_controller_mock")
include("mosaic/tests/helpers/mocks/midi_controller_mock")
include("mosaic/tests/helpers/mocks/params_mock")

local function setup()
  program.init()
  globals.reset()
end

function test_steps_process_note_on_events()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(sequencer_pattern)

  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  pattern_controller.update_working_patterns()

  step_handler.handle(1, 1)

  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end


-- Sequencer param tests

-- function test_trig_probability_causes_a_trig_to_be_fired_with_set_probability
-- function test_quantised_fixed_note_sets_a_trig_note_to_a_fixed_value_that_is_quantised
-- function test_bipolar_random_note_randomly_selects_note_in_plus_or_minus_range_around_mid_point
-- function test_twos_random_note_selects_random_note_within_multiples_of_two
-- function test_random_velocity_set_random_velocity_within_range
-- function test_fixed_note_sets_a_fixed_note_that_isnt_quantised


-- Chord tests

-- function test_chords ...