-- Phrase fragments (MM-08) planner. Contract: docs/musical-merge-extensions-plan.md
-- §2 (layout §2.1, source sequence §2.2, data preservation and the fragment-only
-- length resolver §2.3). README "Merge Shape" still lists phrase fragments as a
-- later design until the MM-11 UI/docs card, so every assertion here is a
-- characterisation of that approved contract, outside the current manual.
-- Mosaic's RNG is never consumed (plan §0 Ranking).

local loaded, fragments = pcall(include, "mosaic/lib/musical_merge/fragments")
local foundation = include("mosaic/lib/musical_merge/foundation")

local function source(overrides)
  local value = {trig_values = {}, note_values = {}, velocity_values = {}, lengths = {}}
  for step = 1, 64 do
    value.trig_values[step], value.note_values[step] = 0, 0
    value.velocity_values[step], value.lengths[step] = 100, 1
  end
  for key, items in pairs(overrides or {}) do
    for step, item in pairs(items) do value[key][step] = item end
  end
  return value
end

local function trigs_at(steps)
  local result = {}
  for _, step in ipairs(steps) do result[step] = 1 end
  return result
end

local function base(overrides)
  local args = {
    start_step = 5, end_step = 20, size = 4,
    candidates = {1, 2},
    patterns = {[1] = source(), [2] = source()},
    seed = 1234, song_slot = 3, channel = 7,
    binding = "1,2|average|average|average",
    phrase = 0, cycle = 1, keep_anchor = false, anchor = nil
  }
  for key, value in pairs(overrides or {}) do args[key] = value end
  return args
end

local function range(first, last)
  local result = {}
  for step = first, last do result[#result + 1] = step end
  return result
end

function test_fragments_module_exists()
  luaunit.assert_true(loaded)
end

-- §2.1: fragments partition P from p_1; the last one is shorter; never wrap.
function test_fragments_layout_partitions_every_length_and_size_from_the_channel_start()
  for _, count in ipairs({1, 3, 4, 7, 8, 16, 17, 64}) do
    local start = count == 64 and 1 or 5
    for _, size in ipairs({4, 8, 16}) do
      local layout = fragments.layout(count, size)
      local expected_count = math.floor((count + size - 1) / size)
      luaunit.assert_equals(#layout, expected_count, count .. "/" .. size)
      local covered = 0
      for index, fragment in ipairs(layout) do
        local k = index - 1
        luaunit.assert_equals(fragment.first, k * size + 1)
        luaunit.assert_equals(fragment.last, math.min((k + 1) * size, count))
        covered = covered + fragment.last - fragment.first + 1
      end
      luaunit.assert_equals(covered, count)
      local result = fragments.plan(base({start_step = start, end_step = start + count - 1, size = size}))
      luaunit.assert_equals(result.positions, range(start, start + count - 1))
      luaunit.assert_equals(#result.fragments, expected_count)
      for index, fragment in ipairs(result.fragments) do
        luaunit.assert_equals(fragment.index, index - 1)
        luaunit.assert_equals(fragment.first_step, start + layout[index].first - 1)
        luaunit.assert_equals(fragment.last_step, start + layout[index].last - 1)
      end
    end
  end
end

function test_fragments_layout_literal_short_and_non_divisible_loops()
  local seventeen = fragments.plan(base({start_step = 5, end_step = 21, size = 8}))
  luaunit.assert_equals({seventeen.fragments[1].first_step, seventeen.fragments[1].last_step}, {5, 12})
  luaunit.assert_equals({seventeen.fragments[2].first_step, seventeen.fragments[2].last_step}, {13, 20})
  luaunit.assert_equals({seventeen.fragments[3].first_step, seventeen.fragments[3].last_step}, {21, 21})
  local short = fragments.plan(base({start_step = 30, end_step = 32, size = 16}))
  luaunit.assert_equals(#short.fragments, 1)
  luaunit.assert_equals({short.fragments[1].first_step, short.fragments[1].last_step}, {30, 32})
end

-- §2.2: the exact tagged identity string, hashed with the shared FNV-1a.
function test_fragments_source_uses_the_tagged_identity_string()
  local args = base({candidates = {2, 5, 9}})
  luaunit.assert_equals(fragments.rank_identity(args, 1, 0), "frag|1|1234|3|7|1,2|average|average|average|0|1|0")
  luaunit.assert_equals(fragments.rank_identity(base({phrase = 2}), 3, 5),
    "frag|1|1234|3|7|1,2|average|average|average|2|3|5")
  for k = 0, 7 do
    local expected = ({2, 5, 9})[foundation.fnv1a(
      "frag|1|1234|3|7|1,2|average|average|average|0|1|" .. k) % 3 + 1]
    luaunit.assert_equals(fragments.choose(args, 1, k), expected)
  end
end

function test_fragments_sequence_is_reproducible_per_seed_and_seed_sensitive()
  local function sequence(seed)
    local result = fragments.plan(base({start_step = 1, end_step = 64, size = 4, seed = seed,
      candidates = {1, 2, 3}, patterns = {source(), source(), source()}}))
    local chosen = {}
    for index, fragment in ipairs(result.fragments) do chosen[index] = fragment.source end
    return chosen
  end
  luaunit.assert_equals(sequence(1234), sequence(1234))
  local differs = false
  for seed = 0, 20 do
    if seed ~= 1234 then
      local other = sequence(seed)
      for index = 1, 16 do if other[index] ~= sequence(1234)[index] then differs = true end end
    end
  end
  luaunit.assert_true(differs)
end

function test_fragments_one_candidate_owns_every_fragment()
  local result = fragments.plan(base({candidates = {6}, patterns = {[6] = source()}}))
  for _, fragment in ipairs(result.fragments) do luaunit.assert_equals(fragment.source, 6) end
end

function test_fragments_no_assigned_pattern_bypasses_with_assign_pattern()
  local result = fragments.plan(base({candidates = {}}))
  luaunit.assert_equals(result.status, "assign_pattern")
  luaunit.assert_equals(result.reason, "ASSIGN PATTERN")
end

-- §2.2 Fixed repeats the phrase; Per phrase draws per phrase number. The planner
-- receives the ranking phrase (0 for Fixed) and the cycle within the phrase.
function test_fragments_fixed_and_per_phrase_sequences_across_three_phrases()
  local function chosen(phrase, cycle)
    local result = fragments.plan(base({start_step = 1, end_step = 64, size = 4, phrase = phrase, cycle = cycle,
      candidates = {1, 2, 3}, patterns = {source(), source(), source()}}))
    local values = {}
    for index, fragment in ipairs(result.fragments) do values[index] = fragment.source end
    return table.concat(values, ",")
  end
  local fixed = {}
  for phrase = 0, 2 do for cycle = 1, 2 do fixed[#fixed + 1] = chosen(0, cycle) end end
  luaunit.assert_equals(fixed[3], fixed[1]);luaunit.assert_equals(fixed[5], fixed[1])
  luaunit.assert_equals(fixed[4], fixed[2]);luaunit.assert_equals(fixed[6], fixed[2])
  luaunit.assert_not_equals(fixed[1], fixed[2])
  local per = {chosen(0, 1), chosen(1, 1), chosen(2, 1)}
  luaunit.assert_not_equals(per[1], per[2]);luaunit.assert_not_equals(per[2], per[3])
  luaunit.assert_equals(chosen(2, 1), per[3])
end

-- §2.3: trig, note, velocity and length are the chosen source's authored values.
function test_fragments_preserve_authored_internal_rhythm_and_data()
  local one = source({trig_values = trigs_at({5, 6, 9, 13, 17}),
    note_values = {[5] = 3, [6] = -2, [9] = 7, [13] = 11, [17] = 1},
    velocity_values = {[5] = 11, [6] = 12, [9] = 13, [13] = 14, [17] = 15},
    lengths = {[5] = 1, [6] = 1, [9] = 1, [13] = 1, [17] = 1}})
  local two = source({trig_values = trigs_at({7, 8, 11, 15, 19}),
    note_values = {[7] = -5, [8] = 4, [11] = 9, [15] = -9, [19] = 2},
    velocity_values = {[7] = 21, [8] = 22, [11] = 23, [15] = 24, [19] = 25},
    lengths = {[7] = 1, [8] = 1, [11] = 1, [15] = 1, [19] = 1}})
  local patterns = {one, two}
  local result = fragments.plan(base({patterns = patterns}))
  luaunit.assert_equals(result.status, "ok")
  for _, fragment in ipairs(result.fragments) do
    local owner = patterns[fragment.source]
    for step = fragment.first_step, fragment.last_step do
      luaunit.assert_equals(result.trigs[step], owner.trig_values[step], step)
      luaunit.assert_equals(result.notes[step], owner.note_values[step], step)
      luaunit.assert_equals(result.velocities[step], owner.velocity_values[step], step)
      luaunit.assert_equals(result.lengths[step], owner.lengths[step], step)
      luaunit.assert_equals(result.fragment_of[step], fragment.index)
      luaunit.assert_equals(result.reasons[step], string.format("FRAGMENT %d · P%02d", fragment.index, fragment.source))
      if owner.trig_values[step] == 1 then
        luaunit.assert_equals(result.roles[step], "fragment")
        luaunit.assert_equals(result.sources[step], {fragment.source})
      else
        luaunit.assert_nil(result.roles[step])
      end
    end
  end
  for step = 1, 64 do
    if step < 5 or step > 20 then
      luaunit.assert_equals(result.trigs[step], 0, step)
      luaunit.assert_nil(result.reasons[step])
    end
  end
end

-- §2.3 Keep anchor: when the anchor pattern owns the fragment its onsets are
-- ordinary fragment onsets; an unassigned anchor keeps nothing.
function test_fragments_keep_anchor_owned_by_anchor_and_unassigned_anchor()
  local anchor = source({trig_values = trigs_at({5, 6}), note_values = {[5] = 12, [6] = 13}})
  local other = source({trig_values = trigs_at({7}), note_values = {[7] = -2}})
  local args = base({start_step = 5, end_step = 12, size = 16, candidates = {2, 4},
    patterns = {[2] = anchor, [4] = other}, anchor = 2, keep_anchor = true})
  local found
  for seed = 0, 64 do
    args.seed = seed
    if fragments.choose(args, 1, 0) == 2 then found = seed break end
  end
  luaunit.assert_not_nil(found)
  local result = fragments.plan(args)
  luaunit.assert_equals(result.anchor_status, "ok")
  luaunit.assert_equals({result.roles[5], result.roles[6], result.trigs[7]}, {"fragment", "fragment", 0})
  luaunit.assert_equals(result.reasons[6], "FRAGMENT 0 · P02")
  luaunit.assert_equals(result.kept_anchor_count, 0)
  local unassigned = fragments.plan(base({start_step = 5, end_step = 12, size = 16, candidates = {4},
    patterns = {[2] = anchor, [4] = other}, anchor = 2, keep_anchor = true}))
  luaunit.assert_equals(unassigned.anchor_status, "anchor_missing")
  luaunit.assert_equals({unassigned.trigs[5], unassigned.trigs[6], unassigned.trigs[7]}, {0, 0, 1})
end

-- §2.3 Keep anchor: anchor-only onsets take the anchor's data; shared onsets
-- belong to the fragment owner.
function test_fragments_keep_anchor_with_every_owner_is_exact()
  local anchor = source({trig_values = trigs_at({5, 6}), note_values = {[5] = 12, [6] = 13},
    velocity_values = {[5] = 91, [6] = 92}, lengths = {[5] = 1, [6] = 1}})
  local other = source({trig_values = trigs_at({5, 7}), note_values = {[5] = -1, [7] = -2},
    velocity_values = {[5] = 41, [7] = 42}, lengths = {[5] = 1, [7] = 1}})
  -- A single fragment (size 16 over 8 positions) owned by the non-anchor pattern.
  local args = base({start_step = 5, end_step = 12, size = 16, candidates = {2, 4},
    patterns = {[2] = anchor, [4] = other}, anchor = 2, keep_anchor = true})
  local owner
  for seed = 0, 64 do
    args.seed = seed
    if fragments.choose(args, 1, 0) == 4 then owner = seed break end
  end
  luaunit.assert_not_nil(owner)
  local result = fragments.plan(args)
  luaunit.assert_equals({result.trigs[5], result.roles[5], result.notes[5], result.velocities[5]}, {1, "fragment", -1, 41})
  luaunit.assert_equals({result.trigs[6], result.roles[6], result.notes[6], result.velocities[6]}, {1, "anchor", 13, 92})
  luaunit.assert_equals(result.reasons[6], "KEPT ANCHOR")
  luaunit.assert_equals({result.trigs[7], result.roles[7], result.notes[7]}, {1, "fragment", -2})
  luaunit.assert_equals(result.kept_anchor_count, 1)
  args.keep_anchor = false
  local without = fragments.plan(args)
  luaunit.assert_equals(without.trigs[6], 0)
  luaunit.assert_nil(without.roles[6])
end

-- §2.3 Differing lengths: the fragment-only playable-ring resolver.
function test_fragments_length_resolver_sole_onset_self_wraps_after_n_steps()
  local positions = range(5, 12)
  local lengths = fragments.resolve_lengths(positions, trigs_at({7}), {[7] = 20})
  luaunit.assert_equals(lengths[7], 8)
  luaunit.assert_equals(fragments.resolve_lengths(positions, trigs_at({7}), {[7] = 5})[7], 5)
end

function test_fragments_length_resolver_ignores_trigs_outside_the_playable_range()
  local positions = range(5, 12)
  local lengths = fragments.resolve_lengths(positions, trigs_at({3, 7, 13, 40}), {[3] = 9, [7] = 20, [13] = 9, [40] = 30})
  luaunit.assert_equals(lengths[7], 8)
  luaunit.assert_equals(lengths[3], 9);luaunit.assert_equals(lengths[13], 9);luaunit.assert_equals(lengths[40], 30)
end

function test_fragments_length_resolver_fractional_and_nonpositive_lengths()
  local positions = range(1, 8)
  local lengths = fragments.resolve_lengths(positions, trigs_at({1, 4, 6, 8}), {[1] = 2.5, [4] = 3.5, [6] = 0, [8] = -1})
  luaunit.assert_equals(lengths[1], 2.5)
  luaunit.assert_equals(lengths[4], 2)
  luaunit.assert_equals(lengths[6], 0)
  luaunit.assert_equals(lengths[8], -1)
end

function test_fragments_length_resolver_adjacent_fragments_and_loop_end_wrap()
  local positions = range(9, 16)
  local lengths = fragments.resolve_lengths(positions, trigs_at({12, 13, 15}), {[12] = 4, [13] = 4, [15] = 6})
  luaunit.assert_equals(lengths[12], 1)
  luaunit.assert_equals(lengths[13], 2)
  -- 15 -> 16 -> wraps to 9 .. 12: distance 5 on the 8-position ring.
  luaunit.assert_equals(lengths[15], 5)
end

function test_fragments_length_resolver_no_onsets_changes_nothing()
  local lengths = fragments.resolve_lengths(range(1, 4), {}, {[1] = 9, [2] = 9})
  luaunit.assert_equals({lengths[1], lengths[2]}, {9, 9})
end

function test_fragments_plan_caps_composed_lengths_across_fragment_boundaries()
  local long = source({trig_values = trigs_at({5, 8, 9, 12}), lengths = {[5] = 16, [8] = 16, [9] = 16, [12] = 16}})
  local result = fragments.plan(base({start_step = 5, end_step = 12, size = 4, candidates = {1},
    patterns = {[1] = long}}))
  luaunit.assert_equals({result.lengths[5], result.lengths[8], result.lengths[9], result.lengths[12]}, {3, 1, 3, 1})
end

function test_fragments_planner_consumes_no_rng()
  local original, calls = math.random, 0
  math.random = function(...) calls = calls + 1;return original(...) end
  fragments.plan(base({start_step = 1, end_step = 64, size = 4}))
  math.random = original
  luaunit.assert_equals(calls, 0)
end
