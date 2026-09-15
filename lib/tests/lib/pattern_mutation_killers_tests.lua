-- Mutation killers for lib/pattern.lua (campaign mutation-bc0570c, wave 3).
-- Each test pins observable working-pattern values produced by
-- pattern.get_and_merge_patterns / pattern.update_working_pattern.
-- README references are to README.md at bc0570c.

local pattern_under_test = include("mosaic/lib/pattern")

local function fresh_channel_one()
  program.init()
  local song_pattern = program.get_song_pattern(1)
  local channel = song_pattern.channels[1]
  return song_pattern, channel
end

local function set_trig(p, s, length)
  p.trig_values[s] = 1
  p.lengths[s] = length
end

local function merged(channel_number, trig_mode)
  return pattern_under_test.get_and_merge_patterns(channel_number, trig_mode or "all", "average", "average", "average")
end

-- README.md:668 "Length Merge Modes" (Average): "Source lengths account for interruption
-- by the next trig in that pattern." One contributor passes through unchanged.
function test_pattern_killer_source_lengths_are_cut_at_the_next_trig_of_the_same_pattern()
  local song_pattern, channel = fresh_channel_one()
  local p = song_pattern.patterns[1]
  set_trig(p, 1, 4)    -- next trig at 3: cut to 2 (first step of the pattern)
  set_trig(p, 3, 1)
  set_trig(p, 5, 2)    -- next trig adjacent: cut to 1
  set_trig(p, 6, 1)
  set_trig(p, 10, 2)   -- next trig 3 steps later: the 2-step length is not reached, stays 2
  set_trig(p, 13, 1)
  set_trig(p, 17, 1)   -- a trig BEFORE step 20 does not cut step 20
  set_trig(p, 20, 5)   -- no trig in 21-24: stays 5
  set_trig(p, 64, 4)   -- wraps: next trig is step 1, cut to 1
  channel.selected_patterns[1] = true

  local lengths = merged(1).lengths

  local expected = {[1] = 2, [3] = 1, [5] = 1, [6] = 1, [10] = 2, [13] = 1, [17] = 1, [20] = 5, [64] = 1}
  for s, length in pairs(expected) do
    luaunit.assert_equals(lengths[s], length, "step " .. s)
  end
end

-- characterisation: a positive step trig mask on a step where the pattern has no
-- trig takes that pattern's stored length as-is; only trig steps are cut by the
-- next trig. (A trig toggled off in the pattern sequencer keeps its length:
-- lib/controls/sequencer.lua:165 changes only trig_values.)
function test_pattern_killer_trig_mask_on_a_trigless_step_keeps_the_pattern_length_uncut()
  local song_pattern, channel = fresh_channel_one()
  local p = song_pattern.patterns[1]
  p.trig_values[1] = 0
  p.lengths[1] = 6
  set_trig(p, 2, 1)
  channel.selected_patterns[1] = true
  program.set_step_trig_mask(1, 1, 1)

  local result = merged(1)

  luaunit.assert_equals(result.trig_values[1], 1)
  luaunit.assert_equals(result.lengths[1], 6)
  luaunit.assert_equals(result.lengths[2], 1)
end

-- README.md:597 "Adding Melodic Notes over Harmony and Drums": "You can apply
-- masks to all steps in a channel by setting the mask value without holding down a
-- step ... turn on or off every trigger ... The default mask value will apply to all
-- steps that don't have a specific mask lock set."
function test_pattern_killer_channel_trig_mask_applies_to_every_step_without_a_step_trig_mask()
  local song_pattern, channel = fresh_channel_one()
  set_trig(song_pattern.patterns[1], 9, 1)
  channel.selected_patterns[1] = true
  program.set_trig_mask(channel, 1)
  program.set_step_trig_mask(1, 5, 0)

  local trigs = merged(1).trig_values

  for s = 1, 64 do
    luaunit.assert_equals(trigs[s], s == 5 and 0 or 1, "step " .. s)
  end

  program.set_trig_mask(channel, 0)
  trigs = merged(1).trig_values
  for s = 1, 64 do
    luaunit.assert_equals(trigs[s], 0, "step " .. s)
  end
end

-- README.md:597: "... set a fixed velocity for every trigger ..." (as above).
function test_pattern_killer_channel_velocity_mask_applies_to_every_step_without_a_step_velocity_mask()
  local song_pattern, channel = fresh_channel_one()
  local p = song_pattern.patterns[1]
  set_trig(p, 3, 1)
  p.velocity_values[3] = 20
  channel.selected_patterns[1] = true
  program.set_velocity_mask(channel, 50)
  program.get_step_velocity_masks(1)[7] = 90

  local velocities = merged(1).velocity_values

  for s = 1, 64 do
    luaunit.assert_equals(velocities[s], s == 7 and 90 or 50, "step " .. s)
  end
end

-- README.md:597 (as above), for the channel length mask.
function test_pattern_killer_channel_length_mask_applies_to_every_step_without_a_step_length_mask()
  local song_pattern, channel = fresh_channel_one()
  set_trig(song_pattern.patterns[1], 3, 4)
  channel.selected_patterns[1] = true
  program.set_length_mask(channel, 2)
  program.set_step_length_mask(channel, 11, 8)

  local lengths = merged(1).lengths

  for s = 1, 64 do
    luaunit.assert_equals(lengths[s], s == 11 and 8 or 2, "step " .. s)
  end
end

-- characterisation: a stored channel trig or velocity mask of -1 is the "unset"
-- value (the channel edit page shows an unset mask as -1) and leaves pattern
-- values in place. The UI stores nil rather than -1, so -1 arrives only through
-- program.set_*_mask.
-- characterisation (suspected defect: lib/pattern.lua:221 tests
-- channel_data.lengths_mask, a field nothing sets, instead of length_mask, so a
-- channel length mask of -1 is applied as a length of -1 to every step; recorded
-- as D12 in docs/testing/refactor-gap-scan.md).
function test_pattern_killer_minus_one_channel_masks_are_unset_for_trig_and_velocity_but_not_length()
  local song_pattern, channel = fresh_channel_one()
  local p = song_pattern.patterns[1]
  set_trig(p, 4, 3)
  p.velocity_values[4] = 70
  channel.selected_patterns[1] = true
  program.set_trig_mask(channel, -1)
  program.set_velocity_mask(channel, -1)
  program.set_length_mask(channel, -1)

  local result = merged(1)

  luaunit.assert_equals(result.trig_values[4], 1)
  luaunit.assert_equals(result.trig_values[5], 0)
  luaunit.assert_equals(result.velocity_values[4], 70)
  luaunit.assert_equals(result.lengths[4], -1)
  luaunit.assert_equals(result.lengths[5], -1)
end

function test_pattern_effective_lengths_fractional_boundary_and_isolated_cycle()
  -- README 668: only a following trig inside the source gate interrupts it.
  -- Characterisation: an isolated trig does not interrupt itself after 64 steps.
  local song, channel = fresh_channel_one()
  local p = song.patterns[1]
  for s = 1, 64 do p.trig_values[s] = 0; p.lengths[s] = 1 end
  channel.selected_patterns[1] = true
  set_trig(p, 1, 2.5)
  set_trig(p, 4, 3.1)
  set_trig(p, 7, 3)
  set_trig(p, 10, 0.25)
  local result = merged(1)
  luaunit.assert_equals(result.lengths[1], 2.5)
  luaunit.assert_equals(result.lengths[4], 3)
  luaunit.assert_equals(result.lengths[7], 3)
  luaunit.assert_equals(result.lengths[10], 0.25)
  for s = 1, 64 do p.trig_values[s] = 0 end
  set_trig(p, 64, 128)
  luaunit.assert_equals(merged(1).lengths[64], 128)
end
