-- Differential test for the Foundation rank key (docs/musical-merge-extensions-plan.md
-- §1.4 performance): foundation.plan hashes the per-plan identity prefix
-- "version|seed|slot|channel|binding|phrase|" once and continues FNV-1a with
-- each candidate step, instead of hashing the whole identity per candidate.
-- The reference below is the pre-change planner, verbatim; the plans must be
-- identical (ranks decide the admitted steps) over seeded random inputs,
-- including float identity fields, whose text form (luaO_tostring) both
-- table.concat and tostring produce.

local foundation = include("mosaic/lib/musical_merge/foundation")

local reference = (function()
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

    -- Ordered candidate filters; nil when none is configured (Off stays exact).
    local filters = args.filters
    if filters then result.reason_lists = {} end

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
          -- Plan §3 candidate pipeline: gap, then each candidate filter
          -- (Interlock) evaluated independently against the same
          -- immutable inputs; every applicable reason is kept, in that order.
          local list
          if filters then
            list = blocked and {"gap"} or {}
            for _, filter in ipairs(filters) do
              if filter.blocked[step] then list[#list + 1] = filter.reason end
            end
            blocked = #list > 0
          end
          if blocked then
            result.reasons[step] = list and list[1] or "gap"
            if list then result.reason_lists[step] = list end
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
        if filters then result.reason_lists[step] = {result.reasons[step]} end
      end
    end

    return result
  end
  foundation.fnv1a = fnv1a
  return foundation
end)()

local function deep_equal(left, right)
  if type(left) ~= "table" or type(right) ~= "table" then
    return left == right and math.type(left) == math.type(right)
  end
  for key, value in pairs(left) do if not deep_equal(value, right[key]) then return false end end
  for key in pairs(right) do if left[key] == nil then return false end end
  return true
end

function test_merge_foundation_rank_prefix_plan_matches_whole_identity_hash()
  local random = math.random
  math.randomseed(11)
  local seeds = {0, 1, 65535, -3, 1.0, 2.5, 1e15, math.maxinteger}
  local phrases = {0, 1, 2.0, 49, 7.5}
  for case = 1, 3000 do
    local source_trigs, source_velocities = {}, {}
    for _ = 1, random(1, 4) do
      local trigs, velocities = {}, {}
      for s = 1, 64 do
        local draw = random()
        trigs[s] = draw < 0.35 and 1 or draw < 0.4 and true or 0
        velocities[s] = random(1, 127)
      end
      local number = random(1, 16)
      source_trigs[number], source_velocities[number] = trigs, velocities
    end
    local keys = {}
    for number in pairs(source_trigs) do keys[#keys + 1] = number end
    table.sort(keys)
    local merged = {}
    for s = 1, 64 do merged[s] = random(1, 127) end
    local args = {
      start_step = random(1, 64), end_step = random(1, 64), anchor = keys[random(#keys)],
      source_trigs = source_trigs, source_velocities = source_velocities, merged_velocities = merged,
      amount = random(0, 100), accent = random(0, 100), gap = random(0, 3),
      seed = random(3) == 1 and seeds[random(#seeds)] or random(0, 65535),
      song_slot = random(5) == 1 and nil or random(1, 8), channel = random(1, 16),
      binding = random(6) == 1 and nil or (tostring(random(1, 99)) .. ",3|average|nil|pattern_number_2"),
      phrase = random(3) == 1 and phrases[random(#phrases)] or random(0, 50),
      ranking_version = random(6) == 1 and nil or 1,
      filters = random(2) == 1 and {{reason = "INTERLOCK CH02", blocked = {[random(1, 64)] = true}}} or nil
    }
    local expected, actual = reference.plan(args), foundation.plan(args)
    luaunit.assert_true(deep_equal(actual, expected), "case " .. case)
  end
end

function test_merge_foundation_rank_prefix_hash_is_unchanged()
  luaunit.assert_equals(foundation.fnv1a(""), reference.fnv1a(""))
  luaunit.assert_equals(foundation.fnv1a("1|0|1|1||0|17"), reference.fnv1a("1|0|1|1||0|17"))
end
