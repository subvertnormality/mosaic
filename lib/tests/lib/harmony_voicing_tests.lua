-- README.md Voice leading: the solver preserves declared material, obeys hard
-- ranges/inversions, prefers literal common tones and fails closed on no solution.

local loaded, voicing = pcall(include, "mosaic/lib/harmony/voicing")

local function role(id, low, high, centre, leap)
  return {id = id, min = low, max = high, centre = centre, preferred_leap = leap or 7}
end

local function solve(material, roles, extra)
  local frame = {
    mode = "revoice",
    material = material,
    roles = roles,
    previous = {},
    crossing = false,
    exact_unison = false,
    preset = "smooth",
    policy_version = 1,
    node_budget = 200000,
    bass = {mode = "smooth", direction = "nearest"}
  }
  for key, value in pairs(extra or {}) do frame[key] = value end
  return voicing.solve(frame)
end

function test_harmony_voicing_module_exists()
  luaunit.assert_true(loaded)
end

function test_harmony_voicing_literal_four_part_anchor_and_common_tones()
  local roles = {
    role("v1", 36, 55, 43, 12), role("v2", 48, 67, 55),
    -- The proposal labels its numeric progression a constrained fixture. These
    -- two bounds make the C/E identity choice unambiguous without hard-coding it.
    role("v3", 55, 63, 60), role("v4", 64, 81, 69)
  }
  local c = solve({
    {id = "root", pc = 0}, {id = "chord1", pc = 7},
    {id = "chord2", pc = 0}, {id = "chord3", pc = 4}
  }, roles, {bass = {mode = "root", tone_id = "root", direction = "nearest"}})
  luaunit.assert_equals(c.status, "ok")
  luaunit.assert_equals(c.pitches, {48, 55, 60, 64})

  local am = solve({
    {id = "root", pc = 9}, {id = "chord1", pc = 9},
    {id = "chord2", pc = 0}, {id = "chord3", pc = 4}
  }, roles, {
    previous = {v1 = 48, v2 = 55, v3 = 60, v4 = 64},
    bass = {mode = "root", tone_id = "root", direction = "nearest"}
  })
  luaunit.assert_equals(am.status, "ok")
  luaunit.assert_equals(am.pitches, {45, 57, 60, 64})
  luaunit.assert_equals(am.explanation.common_tones, {"v3", "v4"})
end

function test_harmony_voicing_range_beats_common_tone_and_never_clamps()
  local result = solve({{id = "root", pc = 0}}, {role("v1", 48, 59, 55)}, {
    previous = {v1 = 60},
    bass = {mode = "root", tone_id = "root", direction = "nearest"}
  })
  luaunit.assert_equals(result.status, "ok")
  luaunit.assert_equals(result.pitches, {48})
  luaunit.assert_equals(result.explanation.moved.v1, "range")

  local impossible = solve({{id = "root", pc = 0}}, {role("v1", 49, 59, 55)})
  luaunit.assert_equals(impossible.status, "no_solution")
  luaunit.assert_equals(impossible.reason, "range")
end

function test_harmony_voicing_root_and_inversion_bass_are_hard_constraints()
  local material = {{id = "root", pc = 0}, {id = "third", pc = 4}, {id = "fifth", pc = 7}}
  local roles = {role("v1", 36, 59, 48), role("v2", 48, 72, 60), role("v3", 55, 84, 67)}
  local root = solve(material, roles, {bass = {mode = "root", tone_id = "root", direction = "nearest"}})
  local first = solve(material, roles, {bass = {mode = "inversion", tone_id = "third", direction = "nearest"}})
  luaunit.assert_equals(root.assignments.v1, "root")
  luaunit.assert_equals(first.assignments.v1, "third")
  luaunit.assert_equals(first.pitches[1] % 12, 4)
end

function test_harmony_voicing_strict_direction_and_exact_unison_fail_closed()
  local descending = solve({{id = "root", pc = 0}}, {role("v1", 48, 60, 54)}, {
    previous = {v1 = 48},
    bass = {mode = "root", tone_id = "root", direction = "descending", strict_direction = true}
  })
  luaunit.assert_equals(descending.status, "ok")
  luaunit.assert_equals(descending.pitches, {48}) -- equality is a legal common tone

  local no_unison = solve({{id = "a", pc = 0}, {id = "b", pc = 0}},
    {role("v1", 60, 60, 60), role("v2", 60, 60, 60)})
  luaunit.assert_equals(no_unison.status, "no_solution")
  luaunit.assert_equals(no_unison.reason, "crossing")
end

function test_harmony_voicing_is_deterministic_and_preserves_duplicate_sources()
  local material = {{id = "root", pc = 0}, {id = "double", pc = 0}, {id = "fifth", pc = 7}}
  local roles = {role("v1", 36, 60, 48), role("v2", 48, 72, 60), role("v3", 55, 84, 67)}
  local first = solve(material, roles)
  for _ = 1, 20 do luaunit.assert_equals(solve(material, roles), first) end
  luaunit.assert_not_nil(first.source_pitches.root)
  luaunit.assert_not_nil(first.source_pitches.double)
  luaunit.assert_not_equals(first.source_pitches.root, first.source_pitches.double)
end

function test_harmony_voicing_reports_budget_instead_of_partial_optimum()
  local roles = {}
  local material = {}
  for i = 1, 5 do
    roles[i] = role("v" .. i, 0, 127, 60)
    material[i] = {id = "s" .. i, pc = (i - 1) * 2}
  end
  local result = solve(material, roles, {crossing = true, exact_unison = true, node_budget = 5})
  luaunit.assert_equals(result.status, "budget_exceeded")
  luaunit.assert_nil(result.pitches)
end

function test_harmony_voicing_ensemble_covers_required_material_and_allows_doubling()
  local result = voicing.solve({
    mode = "ensemble",
    material = {{id = "root", pc = 0, required = true}, {id = "third", pc = 4, required = true},
      {id = "fifth", pc = 7, required = true}},
    roles = {role("bass", 36, 55, 43, 12), role("inner1", 48, 67, 55),
      role("inner2", 55, 74, 62), role("top", 60, 81, 69)},
    previous = {}, crossing = false, exact_unison = false, doubling = true,
    preset = "smooth", policy_version = 1, node_budget = 200000,
    bass = {mode = "root", tone_id = "root", direction = "nearest"}
  })
  luaunit.assert_equals(result.status, "ok")
  local covered = {}
  for _, id in pairs(result.assignments) do covered[id] = true end
  luaunit.assert_true(covered.root and covered.third and covered.fifth)
end

local function independent_less(left, right)
  if not right then return true end
  for index = 1, #left do
    if left[index] ~= right[index] then return left[index] < right[index] end
  end
  return false
end

local function independent_two_voice(frame)
  local best, best_score
  local permutations = {{1, 2}, {2, 1}}
  for _, order in ipairs(permutations) do
    local choices = {}
    for role_index = 1, 2 do
      choices[role_index] = {}
      local wanted = frame.material[order[role_index]].pc % 12
      for pitch = frame.roles[role_index].min, frame.roles[role_index].max do
        if pitch % 12 == wanted then choices[role_index][#choices[role_index] + 1] = pitch end
      end
    end
    for _, low in ipairs(choices[1]) do
      for _, high in ipairs(choices[2]) do
        if high > low then
          local common, movement, max_upper, excess, centre = 0, 0, 0, 0, 0
          local pitches = {low, high}
          for role_index = 1, 2 do
            local role, previous = frame.roles[role_index], frame.previous[frame.roles[role_index].id]
            if previous then
              local material_has_previous = frame.material[1].pc % 12 == previous % 12 or
                frame.material[2].pc % 12 == previous % 12
              if material_has_previous and pitches[role_index] ~= previous then common = common + 1 end
              local leap = math.abs(pitches[role_index] - previous)
              movement = movement + leap * (role_index == 1 and 2 or 1)
              if role_index == 2 then max_upper = leap end
              excess = excess + math.max(0, leap - role.preferred_leap)
            end
            centre = centre + math.abs(pitches[role_index] - role.centre)
          end
          local spacing = math.max(0, 5 - (high - low))
          local score = {0, common, movement, max_upper, excess, centre, spacing,
            low, high, order[1], order[2]}
          if independent_less(score, best_score) then best, best_score = pitches, score end
        end
      end
    end
  end
  return best
end

function test_harmony_voicing_matches_independent_small_bruteforce_oracle()
  local pitch_classes = {0, 4, 7}
  for _, first in ipairs(pitch_classes) do
    for _, second in ipairs(pitch_classes) do
      if first ~= second then
        for previous_low = 48, 50 do
          local frame = {
            mode = "revoice",
            material = {{id = "a", pc = first}, {id = "b", pc = second}},
            roles = {role("v1", 47, 60, 52, 12), role("v2", 53, 67, 60, 7)},
            previous = {v1 = previous_low, v2 = 60}, crossing = false,
            exact_unison = false, preset = "smooth", policy_version = 1,
            node_budget = 200000, bass = {mode = "smooth", direction = "nearest"}
          }
          local expected = independent_two_voice(frame)
          local actual = voicing.solve(frame)
          luaunit.assert_equals(actual.status, "ok")
          luaunit.assert_equals(actual.pitches, expected,
            string.format("pcs %d/%d previous %d", first, second, previous_low))
        end
      end
    end
  end
end
