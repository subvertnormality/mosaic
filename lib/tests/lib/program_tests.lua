include("mosaic/lib/tests/helpers/mocks/params_mock")

local function setup()
  program.init()
  globals.reset()
  params.reset()
end


function test_program_should_get_and_set_step_trig_mask()
  setup()
  local channel = program.get_channel(1, 1)
  channel.step_trig_masks[1] = 1
  
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
end

function test_program_should_get_and_set_step_note_mask()
  setup()
  local channel = program.get_channel(1, 1)
  channel.step_note_masks[1] = 60
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
end

function test_program_should_get_and_set_step_velocity_mask()
  setup()
  local channel = program.get_channel(1, 1)
  channel.step_velocity_masks[1] = 100
  
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
end

function test_program_should_get_and_set_step_length_mask()
  setup()
  local channel = program.get_channel(1, 1)
  channel.step_length_masks[1] = 4
  
  luaunit.assert_equals(channel.step_length_masks[1], 4)
end

function test_program_should_get_and_set_step_chord_mask()
  setup()
  local channel = program.get_channel(1, 1)
  if not channel.step_chord_masks then
    channel.step_chord_masks = {}
  end
  channel.step_chord_masks[1] = {1, 3, 5}
  
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_program_should_handle_multiple_song_patterns()
  setup()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(2, 1)
  
  channel1.step_note_masks[1] = 60
  channel2.step_note_masks[1] = 64
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end

function test_program_should_handle_multiple_channels()
  setup()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  channel1.step_note_masks[1] = 60
  channel2.step_note_masks[1] = 64
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end

function test_program_should_handle_multiple_steps()
  setup()
  local channel = program.get_channel(1, 1)
  
  channel.step_note_masks[1] = 60
  channel.step_note_masks[2] = 64
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 64)
end

function test_program_should_handle_nil_masks()
  setup()
  local channel = program.get_channel(1, 1)
  channel.step_note_masks[1] = nil
  
  luaunit.assert_equals(channel.step_note_masks[1], nil)
end

function test_program_should_initialize_chord_masks_table()
  setup()
  local channel = program.get_channel(1, 1)
  if not channel.step_chord_masks then
    channel.step_chord_masks = {}
  end
  channel.step_chord_masks[1] = {1, 3, 5}
  
  luaunit.assert_not_nil(channel.step_chord_masks)
  luaunit.assert_equals(type(channel.step_chord_masks), "table")
end

function test_program_should_maintain_channel_numbers()
  setup()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  luaunit.assert_equals(channel1.number, 1)
  luaunit.assert_equals(channel2.number, 2)
end

function test_get_next_trig_lock_step_basic_wrap_when_enabled()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- Set up trig locks at steps 5 and 10
  if not channel.step_trig_lock_banks then channel.step_trig_lock_banks = {} end
  channel.step_trig_lock_banks[5] = {[1] = 64}
  channel.step_trig_lock_banks[10] = {[1] = 100}
  
  -- Enable wrapping
  params:set("wrap_param_slides", 2)
  
  -- From step 12, should wrap to step 5
  local result = program.get_next_trig_lock_step(channel, 12, 1)
  luaunit.assert_equals(result.step, 5)
  luaunit.assert_equals(result.current_song_pattern, 1)
  luaunit.assert_equals(result.next_song_pattern, 1)
  luaunit.assert_equals(result.should_wrap, true)
end

function test_get_next_trig_lock_step_no_wrap_when_disabled()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- Set up trig locks at steps 5 and 10
  if not channel.step_trig_lock_banks then channel.step_trig_lock_banks = {} end
  channel.step_trig_lock_banks[5] = {[1] = 64}
  channel.step_trig_lock_banks[10] = {[1] = 100}
  
  -- Disable wrapping
  params:set("wrap_param_slides", 1)
  
  -- From step 12, should not wrap
  local result = program.get_next_trig_lock_step(channel, 12, 1)
  luaunit.assert_nil(result)
end

function test_get_next_trig_lock_step_no_cross_pattern_in_song_mode()
  setup()
  
  -- Set up current pattern trig locks
  local c1_song_pattern_1 = program.get_channel(1, 1)
  if not c1_song_pattern_1.step_trig_lock_banks then c1_song_pattern_1.step_trig_lock_banks = {} end
  program.add_step_param_trig_lock_to_channel(c1_song_pattern_1, 5, 1, 64)
  
  -- Set up next pattern trig locks
  local c1_song_pattern_2 = program.get_channel(2, 1)
  if not c1_song_pattern_2.step_trig_lock_banks then c1_song_pattern_2.step_trig_lock_banks = {} end
  program.add_step_param_trig_lock_to_channel(c1_song_pattern_2, 3, 1, 100)
  
  -- Enable song mode
  params:set("song_mode", 2)
  
  -- Set up program state for next pattern
  program.get().selected_song_pattern = 1
  program.get().next_song_pattern = 2
  program.get().song_patterns[2].active = true
  
  -- Test that we don't find trig lock in next pattern
  local result = program.get_next_trig_lock_step(c1_song_pattern_1, 5, 1)
  luaunit.assert_nil(result)
end

function test_get_next_trig_lock_step_returns_value()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- Set up trig lock with specific value
  if not channel.step_trig_lock_banks then channel.step_trig_lock_banks = {} end
  channel.step_trig_lock_banks[5] = {[1] = 64}
  
  -- Check that value is returned in result
  local result = program.get_next_trig_lock_step(channel, 1, 1)
  luaunit.assert_equals(result.value, 64)
end

function test_get_next_trig_lock_step_wrap_from_last_step()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- Set up trig lock at step 5
  if not channel.step_trig_lock_banks then channel.step_trig_lock_banks = {} end
  channel.step_trig_lock_banks[5] = {[1] = 64}
  
  -- Enable wrapping
  params:set("wrap_param_slides", 2)
  
  -- From step 64 (last step), should wrap to step 5
  local result = program.get_next_trig_lock_step(channel, 64, 1)
  luaunit.assert_equals(result.step, 5)
  luaunit.assert_equals(result.should_wrap, true)
end

function test_get_next_trig_lock_step_wrap_with_single_trig_lock()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- Set up single trig lock at step 5
  if not channel.step_trig_lock_banks then channel.step_trig_lock_banks = {} end
  channel.step_trig_lock_banks[5] = {[1] = 64}
  
  -- Enable wrapping
  params:set("wrap_param_slides", 2)
  
  -- Should find same trig lock repeatedly when wrapping
  local result1 = program.get_next_trig_lock_step(channel, 6, 1)
  luaunit.assert_equals(result1.step, 5)
  luaunit.assert_equals(result1.should_wrap, true)
  
  local result2 = program.get_next_trig_lock_step(channel, result1.step + 1, 1)
  luaunit.assert_equals(result2.step, 5)
  luaunit.assert_equals(result2.should_wrap, true)
end

function test_get_next_trig_lock_step_wrap_with_multiple_parameters()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- Set up trig locks for different parameters
  if not channel.step_trig_lock_banks then channel.step_trig_lock_banks = {} end
  channel.step_trig_lock_banks[5] = {[1] = 64, [2] = 100}
  
  -- Enable wrapping
  params:set("wrap_param_slides", 2)
  
  -- Should wrap correctly for each parameter independently
  local result1 = program.get_next_trig_lock_step(channel, 6, 1)
  luaunit.assert_equals(result1.step, 5)
  luaunit.assert_equals(result1.value, 64)
  luaunit.assert_equals(result1.should_wrap, true)
  
  local result2 = program.get_next_trig_lock_step(channel, 6, 2)
  luaunit.assert_equals(result2.step, 5)
  luaunit.assert_equals(result2.value, 100)
  luaunit.assert_equals(result2.should_wrap, true)
end

function test_get_next_trig_lock_step_wrap_at_step_one()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- Set up trig lock at last step
  if not channel.step_trig_lock_banks then channel.step_trig_lock_banks = {} end
  channel.step_trig_lock_banks[64] = {[1] = 64}
  
  -- Enable wrapping
  params:set("wrap_param_slides", 2)
  
  -- From step 1, should find step 64 without wrapping
  local result = program.get_next_trig_lock_step(channel, 1, 1)
  luaunit.assert_equals(result.step, 64)
  luaunit.assert_equals(result.should_wrap, nil)
end

function test_get_next_trig_lock_step_empty_steps_between_locks()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- Set up trig locks with gaps
  if not channel.step_trig_lock_banks then channel.step_trig_lock_banks = {} end
  channel.step_trig_lock_banks[5] = {[1] = 64}
  channel.step_trig_lock_banks[50] = {[1] = 100}
  
  -- Enable wrapping
  params:set("wrap_param_slides", 2)
  
  -- Should handle large gaps between trig locks
  local result1 = program.get_next_trig_lock_step(channel, 6, 1)
  luaunit.assert_equals(result1.step, 50)
  
  local result2 = program.get_next_trig_lock_step(channel, 51, 1)
  luaunit.assert_equals(result2.step, 5)
  luaunit.assert_equals(result2.should_wrap, true)
end