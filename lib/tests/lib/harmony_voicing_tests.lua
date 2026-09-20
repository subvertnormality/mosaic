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
  local root = solve(material, roles, {bass = {mode = "root", tone_id = "third", direction = "nearest"}})
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

function test_harmony_voicing_five_voice_preset_reports_measured_bounded_cost()
  local roles,material={},{}
  for i=1,5 do
    roles[i]=role("v"..i,36+(i-1)*5,72+(i-1)*5,48+(i-1)*7)
    material[i]={id="s"..i,pc=({0,4,7,11,2})[i],required=true}
  end
  local result=solve(material,roles,{node_budget=200000})
  luaunit.assert_equals(result.status,"ok")
  luaunit.assert_true(result.nodes>0)
  luaunit.assert_true(result.nodes<=200000)
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

function test_harmony_voicing_pedal_is_exact_and_revoice_cannot_invent_its_pitch_class()
  local roles = {role("v1", 36, 60, 48), role("v2", 48, 72, 60)}
  local exact = voicing.solve({mode="revoice",policy_version=1,
    material={{id="root",pc=0},{id="third",pc=4}},roles=roles,
    crossing=false,exact_unison=false,preset="smooth",node_budget=200000,
    bass={mode="pedal",pedal=48,direction="nearest"}})
  luaunit.assert_equals(exact.status, "ok")
  luaunit.assert_equals(exact.pitches[1], 48)
  local absent = voicing.solve({mode="revoice",policy_version=1,
    material={{id="root",pc=2},{id="third",pc=6}},roles=roles,
    crossing=false,exact_unison=false,preset="smooth",node_budget=200000,
    bass={mode="pedal",pedal=48,direction="nearest"}})
  luaunit.assert_equals(absent.status, "no_solution")
end

function test_harmony_voicing_absolute_pin_is_exact_or_fails_without_clamping()
  local roles = {role("v1", 48, 60, 54), role("v2", 55, 72, 63)}
  local exact = solve({{id="root",pc=0},{id="third",pc=4}}, roles,
    {pins={root=60},bass={mode="smooth",direction="nearest"}})
  luaunit.assert_equals(exact.status, "ok")
  luaunit.assert_equals(exact.source_pitches.root, 60)

  local outside = solve({{id="root",pc=0},{id="third",pc=4}}, roles,
    {pins={root=84},bass={mode="smooth",direction="nearest"}})
  luaunit.assert_equals(outside.status, "no_solution")
  luaunit.assert_equals(outside.reason, "range")
end

function test_harmony_voicing_exact_unison_checks_all_roles_when_crossing_is_allowed()
  local result = solve({{id="a",pc=0},{id="b",pc=4},{id="c",pc=0}},
    {role("v1",60,60,60),role("v2",64,64,64),role("v3",60,60,60)},
    {crossing=true,exact_unison=false})
  luaunit.assert_equals(result.status, "no_solution")
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
  local pitch_classes = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}
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

local function independent_assignment_oracle(frame)
  local ids,ranks,by_id={},{},{}
  for _,item in ipairs(frame.material)do ids[#ids+1]=item.id;by_id[item.id]=item end
  table.sort(ids);for index,id in ipairs(ids)do ranks[id]=index end
  local best,best_score,order={},nil,{}
  local function score(pitches)
    local common_moved,movement,max_upper,excess,centre=0,0,0,0,0
    for index,role_value in ipairs(frame.roles)do
      local previous=frame.previous and frame.previous[role_value.id]
      if previous then
        local available=previous>=role_value.min and previous<=role_value.max
        local wanted=previous%12;local material_has=false
        for _,item in ipairs(frame.material)do if item.pc%12==wanted then material_has=true break end end
        if available and material_has and pitches[index]~=previous then common_moved=common_moved+1 end
        local leap=math.abs(pitches[index]-previous)
        movement=movement+leap*(index==1 and 2 or 1)
        if index>1 and leap>max_upper then max_upper=leap end
        excess=excess+math.max(0,leap-(role_value.preferred_leap or 127))
      end
      centre=centre+math.abs(pitches[index]-(role_value.centre or pitches[index]))
    end
    local spacing=0
    if #pitches>1 then spacing=spacing+math.max(0,5-(pitches[2]-pitches[1]))end
    for index=2,#pitches-1 do spacing=spacing+math.max(0,pitches[index+1]-pitches[index]-12)end
    local values={0,common_moved,movement,max_upper,excess,centre,spacing}
    for _,pitch in ipairs(pitches)do values[#values+1]=pitch end
    for _,id in ipairs(order)do values[#values+1]=ranks[id]end
    return values
  end
  local function visit(index,used,pitches)
    if index>#frame.roles then
      local candidate=score(pitches)
      if independent_less(candidate,best_score)then
        best_score={};for i,v in ipairs(candidate)do best_score[i]=v end
        best={};for i,v in ipairs(pitches)do best[i]=v end
      end
      return
    end
    local role_value=frame.roles[index]
    for _,id in ipairs(ids)do if not used[id]then
      local pitch=role_value.min+((by_id[id].pc-role_value.min)%12)
      if index==1 or pitch>pitches[index-1]then
        used[id]=true;order[index]=id;pitches[index]=pitch
        visit(index+1,used,pitches)
        used[id]=nil;order[index]=nil;pitches[index]=nil
      end
    end end
  end
  visit(1,{},{});return best
end

function test_harmony_voicing_matches_independent_oracle_for_all_pitch_class_sets_one_to_five_voices()
  local checked=0
  for voice_count=1,5 do
    local selected={}
    local function visit(next_pc)
      if #selected==voice_count then
        local material,roles={},{}
        for index,pitch_class in ipairs(selected)do
          material[index]={id="tone"..index,pc=pitch_class}
          local low=36+(index-1)*12
          roles[index]=role("v"..index,low,low+11,low+5,12)
        end
        for previous_case=1,2 do
          local previous={}
          if previous_case==2 then
            for index,role_value in ipairs(roles)do
              previous[role_value.id]=role_value.min+((material[index].pc-role_value.min)%12)
            end
          end
          local frame={mode="revoice",material=material,roles=roles,previous=previous,
            crossing=false,exact_unison=false,preset="smooth",policy_version=1,node_budget=200000,
            bass={mode="smooth",direction="nearest"}}
          local expected=independent_assignment_oracle(frame)
          local actual=voicing.solve(frame)
          luaunit.assert_equals(actual.status,"ok")
          luaunit.assert_equals(actual.pitches,expected,
            string.format("voices %d set %s previous %d",voice_count,table.concat(selected,","),previous_case))
          checked=checked+1
        end
        return
      end
      for pitch_class=next_pc,11 do
        selected[#selected+1]=pitch_class;visit(pitch_class+1);selected[#selected]=nil
      end
    end
    visit(0)
  end
  luaunit.assert_equals(checked,3170)
end
