-- README.md Musical Merge: Foundation is an alternative source-union trig policy,
-- while note/length resolvers and explicit masks retain their established ownership.

local pattern_under_test = include("mosaic/lib/pattern")
local merge_config = include("mosaic/lib/musical_merge/config")

local function setup()
  program.init()
  local song = program.get_song_pattern(1)
  program.set_selected_song_pattern(1)
  local channel = song.channels[1]
  channel.selected_patterns = {[1] = true, [2] = true}
  channel.trig_merge_mode = "skip"
  channel.note_merge_mode = "average"
  channel.velocity_merge_mode = "average"
  channel.length_merge_mode = "average"
  return song, channel
end

local function enable(channel)
  channel.musical_merge = merge_config.new()
  channel.musical_merge.mode = "foundation"
  channel.musical_merge.anchor = 1
  return channel.musical_merge
end

function test_musical_merge_explicit_off_is_byte_for_byte_equivalent_to_absence()
  local song, channel = setup()
  song.patterns[1].trig_values[1] = 1
  song.patterns[2].trig_values[1] = 1
  song.patterns[1].note_values[1] = -4
  song.patterns[2].note_values[1] = 8
  local absent = pattern_under_test.get_and_merge_patterns(1, "skip", "average", "average", "average", song)
  channel.musical_merge = merge_config.new()
  local explicit = pattern_under_test.get_and_merge_patterns(1, "skip", "average", "average", "average", song)
  luaunit.assert_equals(explicit, absent)
end

function test_musical_merge_foundation_uses_raw_assigned_union_and_anchor_velocity()
  local song, channel = setup()
  local expected_anchor = {1, 5, 9, 13}
  local expected_additions = {3, 7, 11, 15}
  for index, step in ipairs(expected_anchor) do
    song.patterns[1].trig_values[step] = 1
    song.patterns[1].velocity_values[step] = 90 + index
  end
  for _, step in ipairs({3, 5, 7, 11, 15}) do
    song.patterns[2].trig_values[step] = 1
    song.patterns[2].velocity_values[step] = 100
  end
  enable(channel)
  local result = pattern_under_test.get_and_merge_patterns(1, "skip", "average", "average", "average", song)
  for index, step in ipairs(expected_anchor) do
    luaunit.assert_equals(result.trig_values[step], 1)
    luaunit.assert_equals(result.foundation.roles[step], "anchor")
    luaunit.assert_equals(result.velocity_values[step], 90 + index)
  end
  for _, step in ipairs(expected_additions) do
    luaunit.assert_equals(result.trig_values[step], 1)
    luaunit.assert_equals(result.foundation.roles[step], "addition")
    luaunit.assert_equals(result.velocity_values[step], 70)
  end
  luaunit.assert_equals(result.foundation.roles[5], "anchor")
end

function test_musical_merge_masks_override_amount_and_accent_at_the_existing_final_layer()
  local song, channel = setup()
  song.patterns[1].trig_values[1] = 1
  song.patterns[2].trig_values[3] = 1
  local value = enable(channel)
  value.amount = 0
  value.accent = 0
  channel.step_trig_masks[3] = 1
  channel.step_velocity_masks[3] = 77
  local result = pattern_under_test.get_and_merge_patterns(1, "skip", "average", "average", "average", song)
  luaunit.assert_equals(result.foundation.reasons[3], "accent")
  luaunit.assert_equals(result.trig_values[3], 1)
  luaunit.assert_equals(result.velocity_values[3], 77)
end

function test_musical_merge_unassigned_priority_is_data_but_never_a_rhythm_source()
  local song, channel = setup()
  song.patterns[1].trig_values[1] = 1
  song.patterns[2].trig_values[2] = 1
  song.patterns[3].trig_values[4] = 1
  song.patterns[3].note_values[2] = 12
  enable(channel)
  local result = pattern_under_test.get_and_merge_patterns(
    1, "skip", "pattern_number_3", "average", "average", song)
  luaunit.assert_equals(result.trig_values[2], 1)
  luaunit.assert_equals(result.note_values[2], 12)
  luaunit.assert_equals(result.trig_values[4], 0)
end

function test_musical_merge_missing_anchor_bypasses_to_saved_legacy_mode_visibly()
  local song, channel = setup()
  channel.selected_patterns = {[2] = true}
  song.patterns[2].trig_values[3] = 1
  local value = enable(channel)
  value.anchor = 1
  local result = pattern_under_test.get_and_merge_patterns(1, "skip", "average", "average", "average", song)
  luaunit.assert_equals(result.trig_values[3], 1)
  luaunit.assert_equals(result.foundation.status, "anchor_missing")
  luaunit.assert_equals(result.foundation.reason, "anchor_missing")
end

