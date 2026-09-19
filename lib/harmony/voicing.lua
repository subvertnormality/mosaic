local voicing = {}

local function pc(value)
  return ((value % 12) + 12) % 12
end

local function copy(values)
  local result = {}
  for key, value in pairs(values or {}) do result[key] = value end
  return result
end

local function lex_less(left, right)
  if right == nil then return true end
  for index = 1, math.max(#left, #right) do
    local a, b = left[index], right[index]
    if a ~= b then return a < b end
  end
  return false
end

local function legal_pitches(material_pc, role)
  local result = {}
  local low, high = role.min, role.max
  local first = low + ((material_pc - low) % 12)
  for pitch = first, high, 12 do result[#result + 1] = pitch end
  return result
end

local function material_lookup(material)
  local by_id, ranks, ids = {}, {}, {}
  for index, item in ipairs(material) do
    by_id[item.id] = item
    ids[index] = item.id
  end
  table.sort(ids)
  for index, id in ipairs(ids) do ranks[id] = index end
  return by_id, ranks
end

local function assignment_options(frame, role_index, by_id)
  local role = frame.roles[role_index]
  if role.material_id then return by_id[role.material_id] and {role.material_id} or {} end
  if role_index == 1 then
    local bass = frame.bass or {}
    if bass.mode == "root" or bass.mode == "inversion" then
      return by_id[bass.tone_id] and {bass.tone_id} or {}
    end
  end
  local options = {}
  for _, item in ipairs(frame.material) do options[#options + 1] = item.id end
  table.sort(options)
  return options
end

local function exact_previous_is_available(frame, role_index, pitch)
  local role = frame.roles[role_index]
  if pitch < role.min or pitch > role.max then return false end
  local wanted = pc(pitch)
  for _, item in ipairs(frame.material) do
    if pc(item.pc) == wanted then return true end
  end
  return false
end

local function direction_violation(frame, pitches)
  local bass = frame.bass or {}
  local previous = frame.previous and frame.previous[frame.roles[1].id]
  if not previous or bass.direction == nil or bass.direction == "nearest" then return 0 end
  if bass.direction == "ascending" and pitches[1] < previous then return 1 end
  if bass.direction == "descending" and pitches[1] > previous then return 1 end
  return 0
end

local function score(frame, pitches, assignments, ranks)
  local common_moved, movement, max_upper, leap_excess, centre = 0, 0, 0, 0, 0
  local common = {}
  for index, role in ipairs(frame.roles) do
    local previous = frame.previous and frame.previous[role.id]
    if previous then
      local leap = math.abs(pitches[index] - previous)
      movement = movement + leap * (index == 1 and 2 or 1)
      if index > 1 and leap > max_upper then max_upper = leap end
      if leap > (role.preferred_leap or 127) then
        leap_excess = leap_excess + leap - (role.preferred_leap or 127)
      end
      if exact_previous_is_available(frame, index, previous) then
        if pitches[index] == previous then
          common[#common + 1] = role.id
        else
          common_moved = common_moved + 1
        end
      end
    end
    centre = centre + math.abs(pitches[index] - (role.centre or pitches[index]))
  end

  local spacing = 0
  local upper_spacing = frame.upper_spacing == nil and 12 or frame.upper_spacing
  local bass_separation = frame.bass_separation == nil and 5 or frame.bass_separation
  if #pitches > 1 and bass_separation > 0 then
    spacing = spacing + math.max(0, bass_separation - (pitches[2] - pitches[1]))
  end
  if upper_spacing > 0 then
    for index = 2, #pitches - 1 do
      spacing = spacing + math.max(0, pitches[index + 1] - pitches[index] - upper_spacing)
    end
  end

  local values = {direction_violation(frame, pitches)}
  local preset = frame.preset or "smooth"
  if preset == "compact" then
    values[#values + 1] = centre
    values[#values + 1] = spacing
    values[#values + 1] = common_moved
    values[#values + 1] = movement
    values[#values + 1] = max_upper
    values[#values + 1] = leap_excess
  elseif preset == "independent" then
    values[#values + 1] = movement
    values[#values + 1] = max_upper
    values[#values + 1] = leap_excess
    values[#values + 1] = centre
    values[#values + 1] = spacing
  else
    values[#values + 1] = common_moved
    values[#values + 1] = movement
    values[#values + 1] = max_upper
    values[#values + 1] = leap_excess
    values[#values + 1] = centre
    values[#values + 1] = spacing
  end
  for _, pitch in ipairs(pitches) do values[#values + 1] = pitch end
  for _, id in ipairs(assignments) do values[#values + 1] = ranks[id] or 0 end
  return values, common
end

local function hard_legal(frame, pitches, assignments, by_id)
  for index = 2, #pitches do
    if frame.exact_unison == false and pitches[index] == pitches[index - 1] then
      return false, "crossing"
    end
    if frame.crossing == false and pitches[index] <= pitches[index - 1] then
      return false, "crossing"
    end
  end
  if #pitches > 1 then
    for index = 2, #pitches do
      if pitches[index] < pitches[1] then return false, "inversion" end
    end
  end

  local bass = frame.bass or {}
  local previous_bass = frame.previous and frame.previous[frame.roles[1].id]
  if bass.strict_direction and previous_bass then
    if bass.direction == "ascending" and pitches[1] < previous_bass then
      return false, "strict_direction"
    end
    if bass.direction == "descending" and pitches[1] > previous_bass then
      return false, "strict_direction"
    end
  end
  for index, role in ipairs(frame.roles) do
    local previous = frame.previous and frame.previous[role.id]
    if role.strict_leap and previous and
      math.abs(pitches[index] - previous) > (role.preferred_leap or 127) then
      return false, "strict_leap"
    end
  end

  if frame.mode == "ensemble" then
    local covered = {}
    for _, id in ipairs(assignments) do covered[id] = true end
    for _, item in ipairs(frame.material) do
      if item.required and not covered[item.id] then return false, "coverage" end
    end
  end
  return true
end

function voicing.solve(frame)
  frame = frame or {}
  if frame.policy_version ~= 1 then
    return {status = "invalid", reason = "policy_version"}
  end
  if type(frame.material) ~= "table" or type(frame.roles) ~= "table" or
    #frame.roles < 1 or #frame.roles > 5 then
    return {status = "invalid", reason = "voice_count"}
  end
  if frame.mode == "revoice" and #frame.material ~= #frame.roles then
    return {status = "no_solution", reason = "coverage"}
  end

  local by_id, ranks = material_lookup(frame.material)
  local options = {}
  for index = 1, #frame.roles do
    options[index] = assignment_options(frame, index, by_id)
    if #options[index] == 0 then return {status = "no_solution", reason = "inversion"} end
  end

  local budget = frame.node_budget or 200000
  local nodes = 0
  local exceeded = false
  local best, best_score, best_common
  local assignments, pitches, used = {}, {}, {}
  local failure = {range = false, crossing = false, inversion = false, coverage = false,
    strict_direction = false, strict_leap = false}

  local function visit(role_index)
    if exceeded then return end
    if role_index > #frame.roles then
      local legal, reason = hard_legal(frame, pitches, assignments, by_id)
      if not legal then
        failure[reason] = true
        return
      end
      local candidate_score, common = score(frame, pitches, assignments, ranks)
      if lex_less(candidate_score, best_score) then
        best_score = candidate_score
        best_common = common
        best = {pitches = copy(pitches), assignments = copy(assignments)}
      end
      return
    end

    for _, id in ipairs(options[role_index]) do
      local may_reuse = frame.mode == "ensemble" and frame.doubling ~= false
      if may_reuse or not used[id] then
        local item = by_id[id]
        local candidates = legal_pitches(pc(item.pc), frame.roles[role_index])
        if #candidates == 0 then failure.range = true end
        for _, pitch in ipairs(candidates) do
          nodes = nodes + 1
          if nodes > budget then
            exceeded = true
            return
          end
          if frame.crossing == false and role_index > 1 and pitch <= pitches[role_index - 1] then
            failure.crossing = true
          elseif frame.exact_unison == false and role_index > 1 and pitch == pitches[role_index - 1] then
            failure.crossing = true
          else
            assignments[role_index] = id
            pitches[role_index] = pitch
            local was_used = used[id]
            used[id] = true
            visit(role_index + 1)
            used[id] = was_used
            assignments[role_index] = nil
            pitches[role_index] = nil
          end
        end
      end
    end
  end

  visit(1)
  if exceeded then return {status = "budget_exceeded", reason = "budget", nodes = nodes} end
  if not best then
    local order = {"strict_direction", "strict_leap", "inversion", "coverage", "crossing", "range"}
    for _, reason in ipairs(order) do
      if failure[reason] then return {status = "no_solution", reason = reason, nodes = nodes} end
    end
    return {status = "no_solution", reason = "range", nodes = nodes}
  end

  local role_assignments, source_pitches = {}, {}
  for index, role in ipairs(frame.roles) do
    local id = best.assignments[index]
    role_assignments[role.id] = id
    source_pitches[id] = best.pitches[index]
  end
  local moved = {}
  for index, role in ipairs(frame.roles) do
    local previous = frame.previous and frame.previous[role.id]
    if previous and pc(previous) == pc(best.pitches[index]) and previous ~= best.pitches[index] and
      (previous < role.min or previous > role.max) then
      moved[role.id] = "range"
    end
  end
  table.sort(best_common)
  return {
    status = "ok",
    pitches = best.pitches,
    assignments = role_assignments,
    source_pitches = source_pitches,
    score = best_score,
    nodes = nodes,
    explanation = {common_tones = best_common, moved = moved}
  }
end

return voicing
