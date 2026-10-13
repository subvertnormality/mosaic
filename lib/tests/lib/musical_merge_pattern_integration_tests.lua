-- README.md Musical Merge: Foundation is an alternative source-union trig policy,
-- while note/length resolvers and explicit masks retain their established ownership.

local pattern_under_test = include("mosaic/lib/pattern")
local merge_config = include("mosaic/lib/musical_merge/config")
local merge_state = include("mosaic/lib/musical_merge/state")

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

function test_musical_merge_projection_keeps_queued_removal_active_until_wrap()
  local song,channel=setup();merge_state.reset()
  song.patterns[1].trig_values[1]=1;song.patterns[2].trig_values[3]=1
  local active=enable(channel)
  local first=pattern_under_test.get_and_merge_patterns(1,"skip","average","average","average",song)
  luaunit.assert_not_nil(first.foundation)
  local removed=merge_config.new();merge_state.request(song,1,removed,true);channel.musical_merge=nil
  local queued=pattern_under_test.get_and_merge_patterns(1,"skip","average","average","average",song)
  luaunit.assert_equals(queued.foundation.config.mode,active.mode)
  merge_state.on_cycle_boundary(song,1,removed)
  local promoted=pattern_under_test.get_and_merge_patterns(1,"skip","average","average","average",song)
  luaunit.assert_nil(promoted.foundation)
end

-- Phrase fragments (MM-08) through the working-pattern build. Contract:
-- docs/musical-merge-extensions-plan.md §0 and §2; README "Merge Shape" still
-- defers this mode to MM-11, so these are characterisations of the approved plan.
-- "Explicit channel/step masks still win" is README "Merge Shape" behaviour.
local fragments_planner = include("mosaic/lib/musical_merge/fragments")

local function fragment_setup()
  local song, channel = setup()
  merge_state.reset()
  channel.start_trig, channel.end_trig = {5, 4}, {4, 5} -- steps 5..20
  local one, two = song.patterns[1], song.patterns[2]
  for _, step in ipairs({5, 6, 9, 12, 13, 17, 20}) do
    one.trig_values[step], one.note_values[step], one.velocity_values[step], one.lengths[step] = 1, step % 7, 60 + step, 1
  end
  for _, step in ipairs({5, 7, 8, 11, 14, 15, 18, 19}) do
    two.trig_values[step], two.note_values[step], two.velocity_values[step], two.lengths[step] = 1, -(step % 5), 20 + step, 1
  end
  one.trig_values[2], two.trig_values[40] = 1, 1 -- outside the playable range
  local value = merge_config.new()
  value.mode = "fragments";value.fragments.size = 4;value.seed = 321
  channel.musical_merge = value
  return song, channel, value
end

local function expected_plan(song, channel, value, phrase, cycle, modes)
  modes = modes or {"average", "average", "average"}
  return fragments_planner.plan({
    start_step = 5, end_step = 20, size = value.fragments.size, candidates = {1, 2},
    patterns = song.patterns, seed = value.seed, song_slot = 1, channel = 1,
    binding = "1,2|" .. table.concat(modes, "|"), phrase = phrase or 0, cycle = cycle or 1,
    keep_anchor = value.fragments.keep_anchor, anchor = value.anchor
  })
end

local function merge(song, note_mode)
  return pattern_under_test.get_and_merge_patterns(1, "skip", note_mode or "average", "average", "average", song)
end

function test_musical_merge_fragments_build_uses_raw_fragment_sources_not_legacy_merge()
  local song, channel, value = fragment_setup()
  local result = merge(song)
  local plan = expected_plan(song, channel, value)
  luaunit.assert_nil(result.foundation)
  luaunit.assert_equals(result.fragments.status, "ok")
  luaunit.assert_equals(result.fragments.fragments, plan.fragments)
  local owners = {}
  for _, fragment in ipairs(plan.fragments) do owners[fragment.source] = true end
  luaunit.assert_true(owners[1] and owners[2], "seed 321 should use both sources")
  for step = 1, 64 do
    local inside = step >= 5 and step <= 20
    luaunit.assert_equals(result.trig_values[step], inside and plan.trigs[step] or 0, step)
    if inside then
      local owner = song.patterns[plan.fragments[math.floor((step - 5) / 4) + 1].source]
      luaunit.assert_equals(result.note_values[step], owner.note_values[step], step)
      luaunit.assert_equals(result.velocity_values[step], owner.velocity_values[step], step)
      luaunit.assert_equals(result.lengths[step], plan.lengths[step], step)
    end
  end
  -- Step 5 is an onset in both sources: the legacy average merge would mark it.
  luaunit.assert_nil(result.merged_notes[5])
  luaunit.assert_equals(result.fragments.config.mode, "fragments")
end

function test_musical_merge_fragments_ignore_priority_merge_modes_and_shape_percentages()
  local song, channel, value = fragment_setup()
  song.patterns[3].note_values[6] = 99;song.patterns[3].note_values[7] = 99
  value.cycles, value.shape, value.percentages = 2, "custom", {0, 0}
  local result = merge(song, "pattern_number_3")
  local plan = expected_plan(song, channel, value, 0, 1, {"pattern_number_3", "average", "average"})
  for step = 5, 20 do luaunit.assert_equals(result.trig_values[step], plan.trigs[step], step) end
  luaunit.assert_not_equals(result.note_values[6], 99)
  luaunit.assert_not_equals(result.note_values[7], 99)
end

function test_musical_merge_fragments_masks_keep_final_precedence_without_a_second_cap()
  local song, channel = fragment_setup()
  channel.selected_patterns = {[1] = true}
  local one = song.patterns[1]
  one.lengths[13] = 16
  channel.step_length_masks[5] = 12 -- overrides the fragment cap on an onset
  channel.step_trig_masks[14] = 1 -- a masked onset after 13 does not re-cap it
  channel.step_trig_masks[6] = 0
  channel.step_note_masks[9] = 30
  channel.step_velocity_masks[12] = 5
  local result = merge(song)
  luaunit.assert_equals(result.lengths[5], 12)
  luaunit.assert_equals(result.lengths[13], 4) -- 13 -> 17 in the composed onsets
  luaunit.assert_equals(result.trig_values[14], 1)
  luaunit.assert_equals(result.trig_values[6], 0)
  luaunit.assert_equals(result.note_mask_values[9], 30)
  luaunit.assert_equals(result.velocity_values[12], 5)
end

function test_musical_merge_fragments_without_assigned_patterns_bypass_to_legacy()
  local song, channel = fragment_setup()
  channel.selected_patterns = {}
  local result = merge(song)
  local saved = channel.musical_merge;channel.musical_merge = nil;merge_state.reset()
  local legacy = merge(song)
  channel.musical_merge = saved
  luaunit.assert_equals(result.fragments.status, "assign_pattern")
  luaunit.assert_equals(result.fragments.reason, "ASSIGN PATTERN")
  result.fragments = nil
  luaunit.assert_equals(result, legacy)
end

function test_musical_merge_fragments_fixed_and_per_phrase_through_phrase_state()
  local function sequences(variation)
    local song, channel, value = fragment_setup()
    value.cycles, value.percentages, value.variation = 2, {100, 100}, variation
    local seen = {}
    for boundary = 1, 6 do
      local result = merge(song)
      local runtime = merge_state.effective(song, 1, value)
      local plan = expected_plan(song, channel, value, runtime.ranking_phrase, runtime.cycle)
      luaunit.assert_equals(result.fragments.fragments, plan.fragments)
      luaunit.assert_equals({result.fragments.cycle, result.fragments.phrase}, {runtime.cycle, runtime.phrase})
      local sources = {}
      for index, fragment in ipairs(result.fragments.fragments) do sources[index] = fragment.source end
      seen[boundary] = table.concat(sources, ",")
      merge_state.on_cycle_boundary(song, 1, value)
    end
    return seen
  end
  local fixed = sequences("fixed")
  luaunit.assert_equals({fixed[3], fixed[5]}, {fixed[1], fixed[1]})
  luaunit.assert_equals({fixed[4], fixed[6]}, {fixed[2], fixed[2]})
  local per = sequences("per_phrase")
  luaunit.assert_equals(per[1], fixed[1])
  luaunit.assert_false(per[3] == per[1] and per[5] == per[1] and per[4] == per[2] and per[6] == per[2])
end

function test_musical_merge_fragments_build_consumes_no_rng()
  local song = fragment_setup()
  local original, calls = math.random, 0
  math.random = function(...) calls = calls + 1;return original(...) end
  merge(song)
  math.random = original
  luaunit.assert_equals(calls, 0)
end

-- §0 Off stays exact: a v1 configuration and its canonical v2 migration build
-- identical working patterns, including Foundation ranking.
function test_musical_merge_v1_and_migrated_v2_build_identical_patterns()
  local v1_foundation = {schema_version = 1, mode = "foundation", anchor = 1, amount = 60, accent = 80, gap = 1,
    seed = 777, ranking_version = 1, cycles = 2, shape = "build", percentages = {50, 100}, variation = "per_phrase",
    keep_anchor_pitch = true, target = {kind = "scale"}, extra = "ignored"}
  local v1_off = {schema_version = 1, mode = "off", amount = 100, accent = 70, gap = 0, seed = 0,
    ranking_version = 1, cycles = 1, shape = "flat", percentages = {100}, variation = "fixed",
    keep_anchor_pitch = false, target = {kind = "legacy"}}
  for _, saved in ipairs({v1_foundation, v1_off}) do
    local song, channel = setup()
    for _, step in ipairs({1, 5, 9, 13}) do song.patterns[1].trig_values[step] = 1 end
    for _, step in ipairs({2, 3, 7, 11, 14, 15}) do song.patterns[2].trig_values[step] = 1 end
    merge_state.reset();channel.musical_merge = saved
    local v1_results = {}
    for cycle = 1, 3 do
      v1_results[cycle] = merge(song);merge_state.on_cycle_boundary(song, 1, saved)
    end
    merge_state.reset();channel.musical_merge = merge_config.canonicalize(saved)
    for cycle = 1, 3 do
      local result = merge(song)
      if result.foundation then
        luaunit.assert_equals(result.foundation.config.schema_version, 2)
        result.foundation.config = v1_results[cycle].foundation.config
      end
      luaunit.assert_equals(result, v1_results[cycle], cycle)
      merge_state.on_cycle_boundary(song, 1, channel.musical_merge)
    end
  end
end
