fn = include("mosaic/lib/functions")
program = include("mosaic/lib/program")

local pattern_controller = include("mosaic/lib/pattern_controller")

function pass(test_name)
  print("Test "..test_name.." PASS")
end

function fail(test_name)
  print("Test "..test_name.." FAIL")
end


function skip_should_set_trig_step_to_zero_when_all_steps_are_zero()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "skip"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  if pattern_controller.get_and_merge_patterns(1, "skip").trig_values[1] == 0 then
    pass("skip_should_set_trig_step_to_one_when_only_one_step_is_one")
  else
    fail("skip_should_set_trig_step_to_one_when_only_one_step_is_one")
  end
end

function skip_should_set_trig_step_to_one_when_only_one_step_is_one()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "skip"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  if pattern_controller.get_and_merge_patterns(1, "skip").trig_values[1] == 1 then
    pass("skip_should_set_trig_step_to_one_when_only_one_step_is_one")
  else
    fail("skip_should_set_trig_step_to_one_when_only_one_step_is_one")
  end
end

function add_should_set_trig_step_to_one_when_only_one_step_is_one()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "add"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  if pattern_controller.get_and_merge_patterns(1, "add").trig_values[1] == 1 then
    pass("add_should_set_trig_step_to_one_when_only_one_step_is_one")
  else
    fail("add_should_set_trig_step_to_one_when_only_one_step_is_one")
  end
end

function subtract_should_set_trig_step_to_one_when_only_one_step_is_one()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "add"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  if pattern_controller.get_and_merge_patterns(1, "add").trig_values[1] == 1 then
    pass("subtract_should_set_trig_step_to_one_when_only_one_step_is_one")
  else
    fail("subtract_should_set_trig_step_to_one_when_only_one_step_is_one")
  end
end

function average_should_set_trig_step_to_one_when_only_one_step_is_one()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "average"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  if pattern_controller.get_and_merge_patterns(1, "average").trig_values[1] == 1 then
    pass("average_should_set_trig_step_to_one_when_only_one_step_is_one")
  else
    fail("average_should_set_trig_step_to_one_when_only_one_step_is_one")
  end
end

function add_should_set_trig_step_to_one_when_more_than_one_step_is_one()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "add"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  if pattern_controller.get_and_merge_patterns(1, "add").trig_values[1] == 1 then
    pass("add_should_set_trig_step_to_one_when_more_than_one_step_is_one")
  else
    fail("add_should_set_trig_step_to_one_when_more_than_one_step_is_one")
  end
end

function skip_should_set_trig_step_to_zero_when_more_than_one_step_is_one()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "skip"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true

  if pattern_controller.get_and_merge_patterns(1, "skip").trig_values[1] == 0 then
    pass("skip_should_set_trig_step_to_zero_when_more_than_one_step_is_one")
  else
    fail("skip_should_set_trig_step_to_zero_when_more_than_one_step_is_one")
  end
end

function selected_patterns_set_order_should_not_matter()

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

  if pattern_controller.get_and_merge_patterns(1, "skip").trig_values[1] == 0 then
    pass("selected_patterns_set_order_should_not_matter")
  else
    fail("selected_patterns_set_order_should_not_matter")
  end
end

function pattern_number_should_use_note_value_from_chosen_pattern_number()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "pattern_number_4"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 5
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 4
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 3
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 2
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  if pattern_controller.get_and_merge_patterns(1, "pattern_number_4").note_values[1] == 2 then
    pass("pattern_number_should_use_note_value_from_chosen_pattern_number")
  else
    fail("pattern_number_should_use_note_value_from_chosen_pattern_number")
  end
end

function pattern_number_should_use_note_value_from_chosen_pattern_number_even_if_trig_is_off()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "pattern_number_4"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 5
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 4
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 3
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 2
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  if pattern_controller.get_and_merge_patterns(1, "pattern_number_4").note_values[1] == 2 then
    pass("pattern_number_should_use_note_value_from_chosen_pattern_number_even_if_trig_is_off")
  else
    fail("pattern_number_should_use_note_value_from_chosen_pattern_number_even_if_trig_is_off")
  end
end

function pattern_number_should_use_length_value_from_chosen_pattern_number()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "pattern_number_2"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].lengths[1] = 5
  program.get_sequencer_pattern(1).patterns[2].lengths[1] = 4
  program.get_sequencer_pattern(1).patterns[3].lengths[1] = 3
  program.get_sequencer_pattern(1).patterns[4].lengths[1] = 2
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  if pattern_controller.get_and_merge_patterns(1, "pattern_number_2").lengths[1] == 4 then
    pass("pattern_number_should_use_length_value_from_chosen_pattern_number")
  else
    fail("pattern_number_should_use_length_value_from_chosen_pattern_number")
  end
end

function pattern_number_should_not_use_note_value_from_chosen_pattern_number_if_pattern_isnt_selected()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "pattern_number_4"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 5
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 4
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 3
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 2
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  if pattern_controller.get_and_merge_patterns(1, "pattern_number_4").note_values[1] ~= 2 then
    pass("pattern_number_should_not_use_note_value_from_chosen_pattern_number_if_pattern_isnt_selected")
  else
    fail("pattern_number_should_not_use_note_value_from_chosen_pattern_number_if_pattern_isnt_selected")
  end
end

function notes_should_add_up_when_using_add_merge_mode()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "add"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 72
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 34
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 28
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true


  if pattern_controller.get_and_merge_patterns(1, "add").note_values[1] == 72 + math.ceil((72 + 45 + 28) / 3) then
    pass("notes_should_add_up_when_using_add_merge_mode")
  else
    fail("notes_should_add_up_when_using_add_merge_mode")
  end
end

function notes_should_average_when_using_average_merge_mode() 
  
  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "average"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 72
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 34
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 28
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  if pattern_controller.get_and_merge_patterns(1, "average").note_values[1] == math.ceil((72 + 45 + 28) / 3) then
    pass("notes_should_average_when_using_average_merge_mode")
  else
    fail("notes_should_average_when_using_average_merge_mode")
  end

end

function notes_should_subtract_when_using_subtract_merge_mode()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "subtract"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 72
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 34
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 28
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  if pattern_controller.get_and_merge_patterns(1, "subtract").note_values[1] == 72 - math.ceil((72 + 45 + 28) / 3) then
    pass("notes_should_subtract_when_using_subtract_merge_mode")
  else
    fail("notes_should_subtract_when_using_subtract_merge_mode")
  end
end

function notes_should_not_change_when_using_subtract_merge_mode_with_only_one_pattern()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "subtract"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].trig_values[2] = 1
  program.get_sequencer_pattern(1).patterns[1].trig_values[3] = 1
  program.get_sequencer_pattern(1).patterns[1].trig_values[4] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 2
  program.get_sequencer_pattern(1).patterns[1].note_values[2] = 3
  program.get_sequencer_pattern(1).patterns[1].note_values[3] = 4
  program.get_sequencer_pattern(1).patterns[1].note_values[4] = 5
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  if pattern_controller.get_and_merge_patterns(1, "subtract").note_values[1] == 2 and
  pattern_controller.get_and_merge_patterns(1, "subtract").note_values[2] == 3 and
  pattern_controller.get_and_merge_patterns(1, "subtract").note_values[3] == 4 and
  pattern_controller.get_and_merge_patterns(1, "subtract").note_values[4] == 5
  then
    pass("notes_should_not_change_when_using_subtract_merge_mode_with_only_one_pattern")
  else
    fail("notes_should_not_change_when_using_subtract_merge_mode_with_only_one_pattern")
  end
end

function velocity_values_should_average_the_values_when_using_add_merge_mode()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "add"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].velocity_values[1] = 90
  program.get_sequencer_pattern(1).patterns[2].velocity_values[1] = 67
  program.get_sequencer_pattern(1).patterns[3].velocity_values[1] = 110
  program.get_sequencer_pattern(1).patterns[4].velocity_values[1] = 102
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  -- TODO: This doesn't make sense. Perhaps use average for length and velocity, but add the notes?
  if pattern_controller.get_and_merge_patterns(1, "add").velocity_values[1] == 90 + 67 + 102 then
    pass("velocity_values_should_average_the_values_when_using_add_merge_mode")
  else
    fail("velocity_values_should_average_the_values_when_using_add_merge_mode")
  end
end

function notes_should_ignore_values_that_dont_have_trigs_when_using_add_merge_mode()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "add"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 72
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 34
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 28
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  
  if pattern_controller.get_and_merge_patterns(1, "add").note_values[1] == 72 + math.ceil((45 + 28) / 2) then
    pass("notes_should_ignore_values_that_dont_have_trigs_when_using_add_merge_mode")
  else
    fail("notes_should_ignore_values_that_dont_have_trigs_when_using_add_merge_mode")
  end
end


function notes_should_ignore_values_that_dont_have_trigs_when_using_subtract_merge_mode()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "subtract"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 72
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 34
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 28
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  
  if pattern_controller.get_and_merge_patterns(1, "subtract").note_values[1] == 72 - math.ceil((45 + 28) / 2) then
    pass("notes_should_ignore_values_that_dont_have_trigs_when_using_subtract_merge_mode")
  else
    fail("notes_should_ignore_values_that_dont_have_trigs_when_using_subtract_merge_mode")
  end
end

function notes_should_ignore_values_that_dont_have_trigs_when_using_average_merge_mode()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "average"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 0
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 72
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 45
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 34
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 28
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[3] = true
  
  if pattern_controller.get_and_merge_patterns(1, "average").note_values[1] == math.ceil((45 + 28) / 2) then
    pass("notes_should_ignore_values_that_dont_have_trigs_when_using_average_merge_mode")
  else
    fail("notes_should_ignore_values_that_dont_have_trigs_when_using_average_merge_mode")
  end
end


function notes_should_ignore_values_from_unselected_patterns_when_using_add_merge_mode()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "add"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].note_values[1] = 72
  program.get_sequencer_pattern(1).patterns[2].note_values[1] = 54
  program.get_sequencer_pattern(1).patterns[3].note_values[1] = 33
  program.get_sequencer_pattern(1).patterns[4].note_values[1] = 12
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  if pattern_controller.get_and_merge_patterns(1, "add").note_values[1] == 72 + math.ceil((72 + 54 + 12) / 3) then
    pass("notes_should_ignore_values_from_unselected_patterns_when_using_add_merge_mode")
  else
    fail("notes_should_ignore_values_from_unselected_patterns_when_using_add_merge_mode")
  end
end


function lengths_should_average_the_values_when_using_add_merge_mode()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "add"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].lengths[1] = 1
  program.get_sequencer_pattern(1).patterns[2].lengths[1] = 3
  program.get_sequencer_pattern(1).patterns[3].lengths[1] = 2
  program.get_sequencer_pattern(1).patterns[4].lengths[1] = 4
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  if pattern_controller.get_and_merge_patterns(1, "add").lengths[1] == math.ceil((1 + 3 + 4) / 3) then
    pass("lengths_should_add_the_values_when_using_add_merge_mode")
  else
    fail("lengths_should_add_the_values_when_using_add_merge_mode")
  end
end

function velocity_values_should_average_the_values_when_using_add_merge_mode()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "add"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].velocity_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].velocity_values[1] = 3
  program.get_sequencer_pattern(1).patterns[3].velocity_values[1] = 2
  program.get_sequencer_pattern(1).patterns[4].velocity_values[1] = 4
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  if pattern_controller.get_and_merge_patterns(1, "add").velocity_values[1] == math.ceil((1 + 3 + 4) / 3) then
    pass("velocity_values_should_average_the_values_when_using_add_merge_mode")
  else
    fail("velocity_values_should_average_the_values_when_using_add_merge_mode")
  end
end


function velocity_values_should_average_the_values_when_using_subtract_merge_mode()

  program.init()
  program.get_sequencer_pattern(1).channels[1].merge_mode = "subtract"
  program.get_sequencer_pattern(1).patterns[1].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[3].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[4].trig_values[1] = 1
  program.get_sequencer_pattern(1).patterns[1].velocity_values[1] = 1
  program.get_sequencer_pattern(1).patterns[2].velocity_values[1] = 3
  program.get_sequencer_pattern(1).patterns[3].velocity_values[1] = 2
  program.get_sequencer_pattern(1).patterns[4].velocity_values[1] = 4
  program.get_sequencer_pattern(1).channels[1].selected_patterns[4] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[2] = true
  program.get_sequencer_pattern(1).channels[1].selected_patterns[1] = true

  if pattern_controller.get_and_merge_patterns(1, "add").velocity_values[1] == math.ceil((1 + 3 + 4) / 3) then
    pass("velocity_values_should_average_the_values_when_using_subtract_merge_mode")
  else
    fail("velocity_values_should_average_the_values_when_using_subtract_merge_mode")
  end
end


function init()
  skip_should_set_trig_step_to_zero_when_all_steps_are_zero()
  skip_should_set_trig_step_to_one_when_only_one_step_is_one()
  add_should_set_trig_step_to_one_when_only_one_step_is_one()
  subtract_should_set_trig_step_to_one_when_only_one_step_is_one()
  average_should_set_trig_step_to_one_when_only_one_step_is_one()
  add_should_set_trig_step_to_one_when_more_than_one_step_is_one()
  skip_should_set_trig_step_to_zero_when_more_than_one_step_is_one()
  selected_patterns_set_order_should_not_matter()
  pattern_number_should_use_note_value_from_chosen_pattern_number()
  pattern_number_should_use_note_value_from_chosen_pattern_number_even_if_trig_is_off()
  pattern_number_should_use_length_value_from_chosen_pattern_number()
  pattern_number_should_not_use_note_value_from_chosen_pattern_number_if_pattern_isnt_selected()
  notes_should_add_up_when_using_add_merge_mode()
  notes_should_subtract_when_using_subtract_merge_mode()
  notes_should_average_when_using_average_merge_mode()
  notes_should_not_change_when_using_subtract_merge_mode_with_only_one_pattern()
  velocity_values_should_average_the_values_when_using_add_merge_mode()
  notes_should_ignore_values_that_dont_have_trigs_when_using_add_merge_mode()
  notes_should_ignore_values_that_dont_have_trigs_when_using_subtract_merge_mode()
  notes_should_ignore_values_that_dont_have_trigs_when_using_average_merge_mode()
  notes_should_ignore_values_from_unselected_patterns_when_using_add_merge_mode()
  lengths_should_average_the_values_when_using_add_merge_mode()
  velocity_values_should_average_the_values_when_using_add_merge_mode()
  velocity_values_should_average_the_values_when_using_subtract_merge_mode()

end