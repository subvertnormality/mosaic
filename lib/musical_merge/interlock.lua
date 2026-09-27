-- MM-09 Interlock admission (docs/musical-merge-extensions-plan.md §1 and §3).
--
-- A follower's additions avoid its leader's anchor onsets in common time. The
-- admission runs inside the follower's working-pattern build for its current
-- cycle j = k_f and reads only song data, merge_state records and the
-- transport-owned counters and cycle logs (§1.2), never another channel's
-- callback-visible runtime state or emitted result. Leader cycle plans come
-- from the same pattern.get_and_merge_patterns code with configuration, cycle
-- and phrase passed explicitly (the `leader_plan` callback).
--
-- The result is a record: status "ok" with the set of blocked playable steps,
-- or a visible bypass ("RESYNC", "PLAN LIMIT") that removes nothing, or
-- "LEADER OFF" / "LEADER MISSING" when no evaluated leader cycle could
-- contribute anchors.
local common_time = include("mosaic/lib/musical_merge/common_time")
local merge_state = include("mosaic/lib/musical_merge/state")
local timeline = include("mosaic/lib/musical_merge/timeline")

local interlock = {}

-- §1.4 budget, checked before any plan is built.
interlock.MAX_LEADER_CYCLES = 64
interlock.MAX_LEADER_PLANS = 8

interlock.RESYNC = "RESYNC"
interlock.PLAN_LIMIT = "PLAN LIMIT"
interlock.LEADER_OFF = "LEADER OFF"
interlock.LEADER_MISSING = "LEADER MISSING"

local checked_mul, checked_add = common_time.checked_mul, common_time.checked_add

function interlock.reason(leader)
  return string.format("INTERLOCK CH%02d", leader)
end

-- The configured leader and window of an active Foundation configuration, or nil.
function interlock.settings(config)
  -- v1 keys never had semantics, whatever their names (plan §0).
  if type(config) ~= "table" or config.schema_version ~= 2 or config.mode ~= "foundation" then return nil end
  local value = config.interlock
  if type(value) ~= "table" or value.leader == nil then return nil end
  return value.leader, value.window or 0
end

local function bypass(leader, window, status)
  return {leader = leader, window = window, status = status, blocked = {}, reason = interlock.reason(leader)}
end

local function floor_div(a, b) return a // b end

-- The governing segment of leader cycle i (§1.2.3): logged when its boundary
-- has been applied (i <= k_l), otherwise predicted by replaying the pending
-- boundaries from a pure copy of the leader's merge_state record. Returns
-- config (false for Off), cycle, phrase; nil when a needed log entry is gone.
local function segment(song, leader, saved, i, k_l, running)
  if running then
    if i <= k_l then return timeline.segment(leader, i) end
    local predicted = merge_state.predict(song, leader, saved, i - k_l)
    return predicted.config or false, predicted.cycle, predicted.phrase
  end
  -- Stopped (§1.3): k_l = 0; the requested (or queued) configuration is the
  -- entry at 0 and later cycles are predicted from it.
  if i == 0 then
    local record = merge_state.peek(song, leader)
    if record then return record.queued or record.active or false, record.cycle, record.phrase end
    return saved or false, 1, 0
  end
  local predicted = merge_state.predict(song, leader, saved, i)
  return predicted.config or false, predicted.cycle, predicted.phrase
end

-- ctx: song, channel (follower), config (follower's active configuration),
-- first/last (follower playable steps), leader_plan(leader, config, cycle,
-- phrase) -> merged pattern with .foundation.
function interlock.admission(ctx)
  local leader, window = interlock.settings(ctx.config)
  if not leader then return nil end
  local song, follower = ctx.song, ctx.channel

  -- §1.2.3: from the moment a global (pattern-boundary) activation is queued
  -- for the leader or the follower, every admission of the follower is
  -- unsupported until it lands (then the sticky resync continues it) or is
  -- withdrawn.
  local follower_record, leader_record = merge_state.peek(song, follower), merge_state.peek(song, leader)
  if (follower_record and follower_record.global_queued) or (leader_record and leader_record.global_queued) then
    return bypass(leader, window, interlock.RESYNC)
  end

  local running = timeline.running()
  local j, k_l = 0, 0
  if running then
    -- Either check sets the sticky resync on a changed timing.
    local follower_ok = timeline.check_timing(song, follower)
    local leader_ok = timeline.check_timing(song, leader)
    if not follower_ok or not leader_ok then return bypass(leader, window, interlock.RESYNC) end
    j, k_l = timeline.k(follower), timeline.k(leader)
    -- Between a realign and the forced wrap (k = -1) the next onset starts cycle 0.
    if j < 0 then j = 0 end
  end

  local leader_channel = song.channels[leader]
  local follower_channel = song.channels[follower]
  local length = song.global_pattern_length or 64
  local d_f = common_time.step_duration(follower_channel.clock_mods)
  local d_l = common_time.step_duration(leader_channel.clock_mods)
  if not d_f or not d_l then return bypass(leader, window, interlock.PLAN_LIMIT) end
  local l_first, l_last = timeline.bounds(leader_channel, length)
  local f_count = ctx.last - ctx.first + 1
  local l_count = l_last - l_first + 1
  if f_count < 1 or l_count < 1 then return bypass(leader, window, interlock.PLAN_LIMIT) end

  -- Every nominal time of the query as an integer over one common denominator.
  local scale = common_time.common_denominator({d_f, d_l, common_time.MASTER_STEP})
  if not scale then return bypass(leader, window, interlock.PLAN_LIMIT) end
  local df = common_time.numerator_over(d_f, scale)
  local dl = common_time.numerator_over(d_l, scale)
  local master = common_time.numerator_over(common_time.MASTER_STEP, scale)
  local pf = df and checked_mul(f_count, df)
  local pl = dl and checked_mul(l_count, dl)
  local w = df and checked_mul(window, df)
  local start = pf and checked_mul(j, pf)
  local finish = start and checked_add(start, pf)
  if not (pf and pl and w and start and finish and master) then
    return bypass(leader, window, interlock.PLAN_LIMIT)
  end

  -- §1.4 support [j·P_f − B, (j+1)·P_f + window·d_f], B = window·d_f with
  -- Space off, clipped at the origin.
  local low = start - w
  if low < 0 then low = 0 end
  local high = checked_add(finish, w)
  if not high then return bypass(leader, window, interlock.PLAN_LIMIT) end
  -- §1.2.3: a pattern boundary that will change the slot or realign ends the
  -- origin; leader onsets at or after it are excluded.
  local transition = step and step.origin_end_boundary
  local boundary = transition and transition(timeline.elapsed_master()) or nil
  if boundary then
    local ending = checked_mul(checked_mul(boundary, length) or 0, master)
    if not ending then return bypass(leader, window, interlock.PLAN_LIMIT) end
    if high > ending - 1 then high = ending - 1 end
  end

  local result = {leader = leader, window = window, status = "ok", blocked = {},
    reason = interlock.reason(leader), anchors = 0, cycles = 0}
  if high < low then
    result.status = interlock.LEADER_OFF
    return result
  end
  local first_cycle, last_cycle = floor_div(low, pl), floor_div(high, pl)
  if last_cycle - first_cycle + 1 > interlock.MAX_LEADER_CYCLES then
    return bypass(leader, window, interlock.PLAN_LIMIT)
  end

  -- Governing segments and the distinct plans they need, before any plan.
  local saved = leader_channel.musical_merge
  local segments, keys, distinct = {}, {}, 0
  for i = first_cycle, last_cycle do
    local config, cycle, phrase = segment(song, leader, saved, i, k_l, running)
    if config == nil then return bypass(leader, window, interlock.PLAN_LIMIT) end
    local entry = {i = i, config = config, cycle = cycle, phrase = phrase}
    if config and config.mode == "foundation" then
      local ranking = config.variation == "per_phrase" and phrase or 0
      local key = tostring(config) .. "|" .. tostring(cycle) .. "|" .. tostring(ranking)
      entry.key = key
      if not keys[key] then
        keys[key] = true
        distinct = distinct + 1
        if distinct > interlock.MAX_LEADER_PLANS then return bypass(leader, window, interlock.PLAN_LIMIT) end
      end
    end
    segments[#segments + 1] = entry
  end

  -- Leader plans, memoised only within this admission.
  local plans, anchors, contributed, missing = {}, {}, 0, false
  for _, entry in ipairs(segments) do
    if entry.key then
      local plan = plans[entry.key]
      if plan == nil then
        local merged = ctx.leader_plan(leader, entry.config, entry.cycle, entry.phrase)
        local foundation = merged and merged.foundation
        if foundation and foundation.status == "ok" then
          plan = {}
          for index = 1, l_count do
            if foundation.roles[l_first + index - 1] == "anchor" then plan[#plan + 1] = index end
          end
        else
          plan = false
        end
        plans[entry.key] = plan
      end
      if plan then
        contributed = contributed + 1
        local base = checked_mul(entry.i, pl)
        if not base then return bypass(leader, window, interlock.PLAN_LIMIT) end
        for _, index in ipairs(plan) do
          local onset = base + (index - 1) * dl
          if onset >= low and onset <= high then anchors[#anchors + 1] = onset end
        end
      else
        missing = true
      end
    end
  end
  result.cycles = #segments
  result.anchors = #anchors
  if contributed == 0 then
    result.status = missing and interlock.LEADER_MISSING or interlock.LEADER_OFF
    return result
  end

  -- |a − o| <= window·d_f for any anchor a blocks the candidate at onset o.
  table.sort(anchors)
  for index = 1, f_count do
    local onset = start + (index - 1) * df
    -- The first anchor >= onset − w.
    local lo, hi = 1, #anchors + 1
    while lo < hi do
      local mid = (lo + hi) // 2
      if anchors[mid] < onset - w then lo = mid + 1 else hi = mid end
    end
    if lo <= #anchors and anchors[lo] <= onset + w then
      result.blocked[ctx.first + index - 1] = true
    end
  end
  return result
end

return interlock
