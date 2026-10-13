-- README.md Musical Merge: Foundation protects anchor onsets and deterministically
-- admits additions without consuming Mosaic's RNG. Expectations are independent
-- literal sets and finite-domain invariants from the implementation contract.

local loaded, foundation = pcall(include, "mosaic/lib/musical_merge/foundation")

local function set(values)
  local result = {}
  for _, value in ipairs(values) do result[value] = true end
  return result
end

local function steps_with(values, wanted)
  local result = {}
  for step = 1, 64 do
    if values[step] == wanted then result[#result + 1] = step end
  end
  return result
end

local function same_steps(left, right)
  if #left ~= #right then return false end
  for index = 1, #left do
    if left[index] ~= right[index] then return false end
  end
  return true
end

local function base(overrides)
  local args = {
    start_step = 1,
    end_step = 16,
    anchor = 1,
    source_trigs = {
      [1] = set({1, 5, 9, 13}),
      [2] = set({3, 5, 7, 11, 15})
    },
    source_velocities = {[1] = {[1] = 91, [5] = 92, [9] = 93, [13] = 94}},
    merged_velocities = {[3] = 100, [7] = 80, [11] = 60, [15] = 40},
    amount = 100,
    accent = 70,
    gap = 0,
    seed = 1234,
    song_slot = 3,
    channel = 7,
    binding = "1,2",
    phrase = 0,
    ranking_version = 1
  }
  for key, value in pairs(overrides or {}) do args[key] = value end
  return args
end

function test_foundation_module_exists()
  luaunit.assert_true(loaded)
end

function test_foundation_exact_anchor_union_gap_and_accent_example()
  local result = foundation.plan(base())
  luaunit.assert_equals(steps_with(result.roles, "anchor"), {1, 5, 9, 13})
  luaunit.assert_equals(steps_with(result.roles, "addition"), {3, 7, 11, 15})
  luaunit.assert_equals({result.velocities[1], result.velocities[5], result.velocities[9], result.velocities[13]},
    {91, 92, 93, 94})
  luaunit.assert_equals({result.velocities[3], result.velocities[7], result.velocities[11], result.velocities[15]},
    {70, 56, 42, 28})

  local gap_two = foundation.plan(base({gap = 2}))
  luaunit.assert_equals(steps_with(gap_two.roles, "addition"), {})
  luaunit.assert_equals(gap_two.reasons[3], "gap")
end

function test_foundation_amount_is_reproducible_and_nested()
  local previous = {}
  for amount = 0, 100 do
    local result = foundation.plan(base({amount = amount}))
    local again = foundation.plan(base({amount = amount}))
    luaunit.assert_equals(result.roles, again.roles)
    for step in pairs(previous) do
      luaunit.assert_equals(result.roles[step], "addition", "amount removed step " .. step)
    end
    previous = {}
    for _, step in ipairs(steps_with(result.roles, "addition")) do previous[step] = true end
  end
  luaunit.assert_equals(#steps_with(foundation.plan(base({amount = 50})).roles, "addition"), 2)
end

function test_foundation_uses_actual_wrapping_range_for_anchor_gap()
  local args = base({
    start_step = 61,
    end_step = 4,
    source_trigs = {[1] = set({64}), [2] = set({1, 2, 61})},
    gap = 1
  })
  local result = foundation.plan(args)
  luaunit.assert_equals(result.roles[64], "anchor")
  luaunit.assert_equals(result.reasons[1], "gap")
  luaunit.assert_equals(result.roles[2], "addition")
  luaunit.assert_equals(result.roles[61], "addition")
end

function test_foundation_accent_boundaries_and_explicit_zero_policy()
  local quiet = foundation.plan(base({
    source_trigs = {[1] = set({1}), [2] = set({2, 3, 4})},
    merged_velocities = {[2] = 1, [3] = 0, [4] = -2},
    accent = 1
  }))
  luaunit.assert_equals(quiet.velocities[2], 1)
  luaunit.assert_equals(quiet.velocities[3], 0)
  luaunit.assert_equals(quiet.velocities[4], -2)

  local zero = foundation.plan(base({accent = 0}))
  luaunit.assert_equals(steps_with(zero.roles, "addition"), {})
  luaunit.assert_equals(zero.reasons[3], "accent")
end

function test_foundation_never_invents_candidates_across_all_sources_and_ranges()
  for source_count = 1, 16 do
    local sources = {[1] = {}}
    local union = {}
    for source = 1, source_count do
      sources[source] = {}
      for step = 7, 19 do
        if (step + source) % (source + 1) == 0 then
          sources[source][step] = true
          union[step] = true
        end
      end
    end
    local result = foundation.plan(base({
      start_step = 7,
      end_step = 19,
      source_trigs = sources,
      amount = 37,
      gap = source_count % 3
    }))
    for step = 1, 64 do
      if result.trigs[step] == 1 then
        luaunit.assert_true(union[step], "invented step " .. step .. " with " .. source_count .. " sources")
      end
    end
  end
end

function test_foundation_per_phrase_ranking_changes_only_with_phrase_identity()
  local fixed_a = foundation.plan(base({amount = 50, phrase = 0}))
  local fixed_b = foundation.plan(base({amount = 50, phrase = 0}))
  luaunit.assert_equals(fixed_a.roles, fixed_b.roles)
  local changed = false
  for phrase = 1, 16 do
    local varied = foundation.plan(base({amount = 50, phrase = phrase}))
    if not same_steps(steps_with(fixed_a.roles, "addition"),
      steps_with(varied.roles, "addition")) then
      changed = true
      break
    end
  end
  luaunit.assert_true(changed)
end
