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
local query = include("mosaic/lib/musical_merge/leader_query")

local interlock = {}

-- §1.4 budget, checked before any plan is built (shared with Space).
interlock.MAX_LEADER_CYCLES = query.MAX_LEADER_CYCLES
interlock.MAX_LEADER_PLANS = query.MAX_LEADER_PLANS

interlock.RESYNC = query.RESYNC
interlock.PLAN_LIMIT = query.PLAN_LIMIT
interlock.LEADER_OFF = "LEADER OFF"
interlock.LEADER_MISSING = "LEADER MISSING"

local checked_mul, checked_add = query.checked_mul, query.checked_add

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

local function is_foundation(config)
  return config and config.mode == "foundation"
end

-- ctx: song, channel (follower), config (follower's active configuration),
-- first/last (follower playable steps), leader_plan(leader, config, cycle,
-- phrase) -> merged pattern with .foundation, plan_memo (optional, shared
-- with Space within one build).
function interlock.admission(ctx)
  local leader, window = interlock.settings(ctx.config)
  if not leader then return nil end

  local frame, status = query.frame(ctx, leader)
  if not frame then return bypass(leader, window, status) end
  local df, dl, pl, start, finish = frame.df, frame.dl, frame.pl, frame.start, frame.finish
  local w = checked_mul(window, df)
  if not w then return bypass(leader, window, interlock.PLAN_LIMIT) end

  -- §1.4 support [j·P_f − B, (j+1)·P_f + window·d_f], B = window·d_f for
  -- Interlock (Space extends its own support by G), clipped at the origin.
  local high = checked_add(finish, w)
  if not high then return bypass(leader, window, interlock.PLAN_LIMIT) end
  local low
  low, high = query.clip(frame, start - w, high)

  local result = {leader = leader, window = window, status = "ok", blocked = {},
    reason = interlock.reason(leader), anchors = 0, cycles = 0}
  if high < low then
    result.status = interlock.LEADER_OFF
    return result
  end

  -- Governing segments and the distinct plans they need, before any plan.
  local segments, failure = query.segments(frame, low, high, is_foundation)
  if not segments then return bypass(leader, window, failure) end

  -- Leader anchors per plan, derived once per plan key.
  local l_first, l_count = frame.l_first, frame.l_count
  local derived, anchors, contributed, missing = {}, {}, 0, false
  for _, entry in ipairs(segments) do
    if entry.key then
      local plan = derived[entry.key]
      if plan == nil then
        local merged = query.plan(ctx, frame, entry)
        local foundation = merged and merged.foundation
        if foundation and foundation.status == "ok" then
          plan = {}
          for index = 1, l_count do
            if foundation.roles[l_first + index - 1] == "anchor" then plan[#plan + 1] = index end
          end
        else
          plan = false
        end
        derived[entry.key] = plan
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
  for index = 1, frame.f_count do
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
