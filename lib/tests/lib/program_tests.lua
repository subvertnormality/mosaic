
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

function test_get_next_trig_lock_step_basic_wrap()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- Set up trig locks at steps 5 and 10
  if not channel.step_trig_lock_banks then channel.step_trig_lock_banks = {} end
  channel.step_trig_lock_banks[5] = {[1] = 64}
  channel.step_trig_lock_banks[10] = {[1] = 100}
  
  -- From step 1, should find step 5
  local result = program.get_next_trig_lock_step(channel, 1, 1)
  luaunit.assert_equals(result.step, 5)
  luaunit.assert_equals(result.song_pattern, 1)
  
  -- From step 7, should find step 10
  result = program.get_next_trig_lock_step(channel, 7, 1)
  luaunit.assert_equals(result.step, 10)
  luaunit.assert_equals(result.song_pattern, 1)
  
  -- From step 12, should wrap to step 5
  result = program.get_next_trig_lock_step(channel, 12, 1)
  luaunit.assert_equals(result.step, 5)
  luaunit.assert_equals(result.song_pattern, 1)
end

function test_get_next_trig_lock_step_no_trig_locks()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- Empty trig lock banks
  channel.step_trig_lock_banks = {}
  
  local result = program.get_next_trig_lock_step(channel, 1, 1)
  luaunit.assert_nil(result)
end

function test_get_next_trig_lock_step_nil_banks()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- No trig lock banks defined
  channel.step_trig_lock_banks = nil
  
  local result = program.get_next_trig_lock_step(channel, 1, 1)
  luaunit.assert_nil(result)
end

function test_get_next_trig_lock_step_works_when_song_mode_is_enabled()
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
  
  -- Test finding trig lock in next pattern
  local result = program.get_next_trig_lock_step(c1_song_pattern_1, 5, 1)
  luaunit.assert_equals(result.step, 3)
  luaunit.assert_equals(result.song_pattern, 2)
end

function test_get_next_trig_lock_step_song_mode_same_pattern()
  setup()
  
  -- Set up current pattern trig locks
  local channel = program.get_channel(1, 1)
  if not channel.step_trig_lock_banks then channel.step_trig_lock_banks = {} end
  channel.step_trig_lock_banks[5] = {[1] = 64}
  
  -- Enable song mode
  params:set("song_mode", 2)
  
  -- Set up program state to stay in same pattern
  program.get().selected_song_pattern = 1
  program.get().next_song_pattern = 1
  
  -- Should find trig lock in current pattern
  local result = program.get_next_trig_lock_step(channel, 1, 1)
  luaunit.assert_equals(result.step, 5)
  luaunit.assert_equals(result.song_pattern, 1)
end

function test_get_next_trig_lock_step_song_mode_no_next_trig_locks()
  setup()
  
  -- Set up current pattern trig locks
  local channel1 = program.get_channel(1, 1)
  if not channel1.step_trig_lock_banks then channel1.step_trig_lock_banks = {} end
  channel1.step_trig_lock_banks[5] = {[1] = 64}
  
  -- Set up empty next pattern
  local channel2 = program.get_channel(2, 1)
  channel2.step_trig_lock_banks = {}
  
  -- Enable song mode
  params:set("song_mode", 2)
  
  -- Set up program state to move to next pattern
  program.get().selected_song_pattern = 1
  program.get().next_song_pattern = 2
  
  -- Should wrap in current pattern since next has no trig locks
  local result = program.get_next_trig_lock_step(channel1, 6, 1)
  luaunit.assert_equals(result.step, 5)
  luaunit.assert_equals(result.song_pattern, 1)
end

function test_get_next_trig_lock_step_different_parameters()
  setup()
  local channel = program.get_channel(1, 1)
  
  -- Set up trig locks for different parameters
  if not channel.step_trig_lock_banks then channel.step_trig_lock_banks = {} end
  channel.step_trig_lock_banks[5] = {[1] = 64, [2] = 100}
  channel.step_trig_lock_banks[10] = {[2] = 50}
  
  -- Should find correct steps for different parameters
  local result1 = program.get_next_trig_lock_step(channel, 1, 1)
  luaunit.assert_equals(result1.step, 5)
  
  local result2 = program.get_next_trig_lock_step(channel, 6, 2)
  luaunit.assert_equals(result2.step, 10)
end