local foundation = {}

local function round_half_up(value)
  return math.floor(value + 0.5)
end

local function fnv1a(text)
  local hash = 2166136261
  for index = 1, #text do
    hash = ((hash ~ string.byte(text, index)) * 16777619) & 0xffffffff
  end
  return hash
end

local function loop_steps(first, last)
  local steps = {}
  local step = first
  while true do
    steps[#steps + 1] = step
    if step == last then break end
    step = step == 64 and 1 or step + 1
    if #steps > 64 then error("invalid Foundation loop") end
  end
  return steps
end

local function circular_distance(index_a, index_b, length)
  local distance = math.abs(index_a - index_b)
  return math.min(distance, length - distance)
end

local function rank_key(args, step)
  local identity = table.concat({
    args.ranking_version or 1,
    args.seed or 0,
    args.song_slot or 1,
    args.channel or 1,
    args.binding or "",
    args.phrase or 0,
    step
  }, "|")
  return fnv1a(identity)
end

local function addition_velocity(value, accent)
  if value == nil then value = 100 end
  if value <= 0 then return value end
  local scaled = round_half_up(value * accent / 100)
  if scaled < 1 then scaled = 1 end
  if scaled > 127 then scaled = 127 end
  return scaled
end

function foundation.plan(args)
  args = args or {}
  if (args.ranking_version or 1) ~= 1 then
    return {status = "unsupported_version", reason = "ranking_version"}
  end
  local source_trigs = args.source_trigs or {}
  local anchor_trigs = source_trigs[args.anchor]
  if type(anchor_trigs) ~= "table" then
    return {status = "anchor_missing", reason = "anchor_missing"}
  end

  local steps = loop_steps(args.start_step or 1, args.end_step or 64)
  local position = {}
  for index, step in ipairs(steps) do position[step] = index end

  local result = {
    status = "ok",
    trigs = {},
    roles = {},
    reasons = {},
    velocities = {},
    sources = {},
    eligible_count = 0,
    admitted_count = 0
  }
  for step = 1, 64 do result.trigs[step] = 0 end

  local anchors = {}
  for _, step in ipairs(steps) do
    if anchor_trigs[step] == true or anchor_trigs[step] == 1 then
      anchors[#anchors + 1] = step
      result.trigs[step] = 1
      result.roles[step] = "anchor"
      result.sources[step] = {args.anchor}
      local velocities = args.source_velocities and args.source_velocities[args.anchor]
      result.velocities[step] = velocities and velocities[step] or
        (args.merged_velocities and args.merged_velocities[step])
    end
  end

  local candidates = {}
  for _, step in ipairs(steps) do
    if not result.roles[step] then
      local contributors = {}
      for source, trigs in pairs(source_trigs) do
        if source ~= args.anchor and (trigs[step] == true or trigs[step] == 1) then
          contributors[#contributors + 1] = source
        end
      end
      table.sort(contributors)
      if #contributors > 0 then
        local blocked = false
        local gap = args.gap or 0
        if gap > 0 then
          for _, anchor_step in ipairs(anchors) do
            if circular_distance(position[step], position[anchor_step], #steps) <= gap then
              blocked = true
              break
            end
          end
        end
        if blocked then
          result.reasons[step] = "gap"
          result.sources[step] = contributors
        else
          candidates[#candidates + 1] = {
            step = step,
            rank = rank_key(args, step),
            sources = contributors
          }
        end
      end
    end
  end

  result.eligible_count = #candidates
  table.sort(candidates, function(left, right)
    if left.rank ~= right.rank then return left.rank < right.rank end
    return left.step < right.step
  end)

  local accent = args.accent == nil and 70 or args.accent
  local amount = args.amount == nil and 100 or args.amount
  local admitted = accent == 0 and 0 or round_half_up(amount * #candidates / 100)
  if admitted < 0 then admitted = 0 end
  if admitted > #candidates then admitted = #candidates end
  result.admitted_count = admitted

  for index, candidate in ipairs(candidates) do
    local step = candidate.step
    result.sources[step] = candidate.sources
    if index <= admitted then
      result.trigs[step] = 1
      result.roles[step] = "addition"
      result.velocities[step] = addition_velocity(
        args.merged_velocities and args.merged_velocities[step], accent)
    else
      result.reasons[step] = accent == 0 and "accent" or "amount"
    end
  end

  return result
end

foundation.round_half_up = round_half_up
foundation.fnv1a = fnv1a

return foundation
