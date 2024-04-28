local pattern_controller = include("mosaic/lib/pattern_controller")

-- Merge modes

-- Trig : Skip / Only / Any
-- Note : Up / Down / Average / Channel
-- Velocity : / Up / Down / Average / Channel
-- Length : / Up / Down / Average / Channel


function test_skip_should_set_trig_step_to_zero_when_all_steps_are_zero()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "skip"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "skip", false, false, false).trig_values[1], 0)
end

function test_skip_should_set_trig_step_to_one_when_only_one_step_is_one()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "skip"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "skip", false, false, false).trig_values[1], 1)
end


function test_skip_should_set_trig_step_to_zero_when_more_than_one_step_is_one()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "skip"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "skip", false, false, false).trig_values[1], 0)
end

function test_selected_patterns_set_order_should_not_matter()
  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "skip"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "skip", false, false, false).trig_values[1], 0)
end


function test_trig_mode_blend_should_set_trig_step_to_zero_when_all_steps_are_zero()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "blend"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "skip", false, false, false).trig_values[1], 0)
end


function test_trig_mode_only_should_set_trig_step_to_one_when_more_than_one_steps_are_one()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "only"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "only", false, false, false).trig_values[1], 1)
end

function test_trig_mode_only_should_set_trig_step_to_zero_when_only_one_step_is_one()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "only"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "only", false, false, false).trig_values[1], 0)
end

function test_trig_mode_only_should_set_trig_step_to_zero_when_all_steps_are_one()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "only"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "only", false, false, false).trig_values[1], 1)
end

function test_trig_mode_only_with_multiple_steps_with_different_valued_rules()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "only"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0

  program.get_sequencer_pattern(1).patterns[1].trig_values[2] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[2] = 0
  program.get_sequencer_pattern(1).patterns[3].trig_values[2] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[2] = 0

  program.get_sequencer_pattern(1).patterns[1].trig_values[3] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[3] = 0
  program.get_sequencer_pattern(1).patterns[3].trig_values[3] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[3] = 0

  program.get_sequencer_pattern(1).patterns[1].trig_values[4] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[4] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[4] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[4] = 1

  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "only", false, false, false).trig_values[1], 1)
  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "only", false, false, false).trig_values[2], 0)
  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "only", false, false, false).trig_values[3], 0)
  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "only", false, false, false).trig_values[4], 1)

end

function test_trig_mode_only_with_multiple_steps_with_inactive_patterns()

  program.get_sequencer_pattern(1).patterns[1].trig_values[5] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[5] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[5] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[5] = 1

  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = false
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = false
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = false

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "only", false, false, false).trig_values[5], 0)
end

function test_trig_mode_all_should_set_trig_step_to_one_when_a_step_is_one()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "all"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, false, false).trig_values[1], 1)
end

function test_trig_mode_all_should_set_trig_step_to_one_when_two_steps_are_one()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "all"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, false, false).trig_values[1], 1)
end

function test_trig_mode_all_should_set_trig_step_to_one_when_all_steps_are_one()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "all"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, false, false).trig_values[1], 1)
end

function test_trig_mode_all_should_set_trig_step_to_zero_when_all_steps_are_zero()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "all"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, false, false).trig_values[1], 0)
end

function test_pattern_number_should_use_note_value_from_chosen_pattern_number()
  program.init()
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 5
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 4
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 3
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 1
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", "pattern_number_3", false, false).note_values[1], 3)
end

function test_steps_with_just_one_note_should_use_that_note()
  program.init()
  program.get_sequencer_pattern(1).patterns[1].trig_values[2] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[2] = 56
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 39
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 33
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", "up", false, false).note_values[2], 56)
end

function test_notes_should_add_up_when_using_up_merge_mode()
  program.init()
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 56
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 39
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 33
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", "up", false, false).note_values[1], ((math.floor(((56 + 45 + 33) / 3) + 0.5) - 33) + 56))
end

function test_notes_should_subtract_down_when_using_down_merge_mode()
  program.init()
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 56
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 39
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 33
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", "down", false, false).note_values[1], (33 - (math.floor(((56 + 45 + 33) / 3) + 0.5) - 33)))
end

function test_notes_should_average_when_using_average_merge_mode()
  program.init()
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 56
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 39
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 33
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", "average", false, false).note_values[1], math.floor(((56 + 45 + 33) / 3) + 0.5))
end

function test_pattern_number_should_use_velocity_value_from_chosen_pattern_number()
  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "pattern_number_4"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].velocity_values[1] = 50
  program.get_sequencer_pattern(1).patterns[2].velocity_values[1] = 40
  program.get_sequencer_pattern(1).patterns[3].velocity_values[1] = 30
  program.get_sequencer_pattern(1).patterns[4].velocity_values[1] = 10
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, "pattern_number_3", false).velocity_values[1], 30)
end

function test_velocities_should_add_up_when_using_up_merge_mode()
  program.init()
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].velocity_values[1] = 56
  program.get_sequencer_pattern(1).patterns[2].velocity_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].velocity_values[1] = 39
  program.get_sequencer_pattern(1).patterns[4].velocity_values[1] = 33
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, "up", false).velocity_values[1], ((math.floor(((56 + 45 + 33) / 3) + 0.5) - 33) + 56))
end

function test_velocities_should_subtract_down_when_using_down_merge_mode()
  program.init()
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].velocity_values[1] = 56
  program.get_sequencer_pattern(1).patterns[2].velocity_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].velocity_values[1] = 39
  program.get_sequencer_pattern(1).patterns[4].velocity_values[1] = 33
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, "down", false).velocity_values[1], (33 - (math.floor(((56 + 45 + 33) / 3) + 0.5) - 33)))
end

function test_velocities_should_average_when_using_average_merge_mode()
  program.init()
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].velocity_values[1] = 56
  program.get_sequencer_pattern(1).patterns[2].velocity_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].velocity_values[1] = 39
  program.get_sequencer_pattern(1).patterns[4].velocity_values[1] = 33
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, "average", false).velocity_values[1], math.floor(((56 + 45 + 33) / 3) + 0.5))
end

function test_pattern_number_should_use_lengths_value_from_chosen_pattern_number()
  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "pattern_number_4"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].lengths[1] = 50
  program.get_sequencer_pattern(1).patterns[2].lengths[1] = 40
  program.get_sequencer_pattern(1).patterns[3].lengths[1] = 30
  program.get_sequencer_pattern(1).patterns[4].lengths[1] = 10
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, false, "pattern_number_3").lengths[1], 30)
end

function test_lengths_should_add_up_when_using_up_merge_mode()
  program.init()
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].lengths[1] = 56
  program.get_sequencer_pattern(1).patterns[2].lengths[1] = 45
  program.get_sequencer_pattern(1).patterns[3].lengths[1] = 39
  program.get_sequencer_pattern(1).patterns[4].lengths[1] = 33
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, false, "up").lengths[1], ((math.floor(((56 + 45 + 33) / 3) + 0.5) - 33) + 56))
end

function test_lengths_should_subtract_down_when_using_down_merge_mode()
  program.init()
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].lengths[1] = 56
  program.get_sequencer_pattern(1).patterns[2].lengths[1] = 45
  program.get_sequencer_pattern(1).patterns[3].lengths[1] = 39
  program.get_sequencer_pattern(1).patterns[4].lengths[1] = 33
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, false, "down").lengths[1], (33 - (math.floor(((56 + 45 + 33) / 3) + 0.5) - 33)))
end

function test_lengths_should_average_when_using_average_merge_mode()
  program.init()
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].lengths[1] = 56
  program.get_sequencer_pattern(1).patterns[2].lengths[1] = 45
  program.get_sequencer_pattern(1).patterns[3].lengths[1] = 39
  program.get_sequencer_pattern(1).patterns[4].lengths[1] = 33
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, false, "average").lengths[1], math.floor(((56 + 45 + 33) / 3) + 0.5))
end


function test_trig_masks_can_trigger_steps()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "skip"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  program.get_sequencer_pattern(1).channels[1].step_trig_masks[1] = 1

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "skip", false, false, false).trig_values[1], 1)
end


function test_trig_masks_can_mask_steps()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "skip"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  program.get_sequencer_pattern(1).channels[1].step_trig_masks[1] = 0

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "skip", false, false, false).trig_values[1], 0)
end

function test_trig_masks_set_to_off_doesnt_trig()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "skip"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  program.get_sequencer_pattern(1).channels[1].step_trig_masks[1] = -1

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "skip", false, false, false).trig_values[1], 0)
end

function test_trig_masks_set_to_off_doesnt_mask()
  program.init()
  program.get_sequencer_pattern(1).channels[1].trig_merge_mode = "skip"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  program.get_sequencer_pattern(1).channels[1].step_trig_masks[1] = -1

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "skip", false, false, false).trig_values[1], 1)
end


function test_note_masks_should_take_precedence_over_note_values()
  program.init()
  program.get_sequencer_pattern(1).patterns[2].trig_values[5] = 1
  program.get_sequencer_pattern(1).patterns[2].note_values[5] = 45
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true

  program.get_sequencer_pattern(1).channels[1].step_note_masks[5] = 78

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", "up", false, false).note_values[5], 78)
end

function test_velocity_masks_should_take_precedence_over_velocity_values()
  program.init()
  program.get_sequencer_pattern(1).patterns[2].trig_values[5] = 1
  program.get_sequencer_pattern(1).patterns[2].velocity_values[5] = 5
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true

  program.get_sequencer_pattern(1).channels[1].step_velocity_masks[5] = 79

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, "up", false).velocity_values[5], 79)
end

function test_length_masks_should_take_precedence_over_lengths()
  program.init()
  program.get_sequencer_pattern(1).patterns[2].trig_values[5] = 1
  program.get_sequencer_pattern(1).patterns[2].lengths[5] = 4
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true

  program.get_sequencer_pattern(1).channels[1].step_length_masks[5] = 80

  luaunit.assert_equals(pattern_controller.get_and_merge_patterns(1, "all", false, false, "up").lengths[5], 80)
end