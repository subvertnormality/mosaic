-- MM-09 Interlock admission (docs/musical-merge-extensions-plan.md §1 and §3).
--
-- A follower's additions avoid its leader's anchor onsets in common time. The
-- admission runs inside the follower's working-pattern build for its current
-- cycle j = k_f and reads only song data, merge_state records and the
-- transport-owned counters and cycle logs (§1.2), never another channel's
-- callback-visible runtime state or emitted result. Leader anchors are read
-- directly from the currently stored anchor pattern under each leader cycle's
-- governing configuration (§1.2.3); no leader plan or working pattern is built.
--
-- The admission record, published by pattern.get_and_merge_patterns as
-- working_pattern.foundation.interlock (the stable place the Result/Reason
-- screens and the device timing oracle of §1.4 read):
--   status      "ok" (supported: Interlock filters), or a visible bypass:
--               "RESYNC" / "PLAN LIMIT" (unsupported: Interlock only is
--               bypassed, §1.2 fallback), "LEADER OFF" / "LEADER MISSING"
--               (no evaluated leader cycle contributed anchors, §1.5).
--   cycles      leader cycles counted over the clipped support (§1.4); for
--               PLAN LIMIT the count that exceeded the budget, 0 when the
--               admission bypassed before the support was known.
--   anchors     leader anchors in the evaluated cycles (before the origin end).
--   plan_builds leader plans built by the admission: always 0 (§1.2.3).
--   blocked     {[step] = true} for follower playable steps within the window
--               of a leader anchor; empty for every status but "ok".
--   leader, window, reason ("INTERLOCK CHnn").
local query = include("mosaic/lib/musical_merge/leader_query")

local interlock = {}

-- §1.4 budget (single authority): leader cycles per admission.
interlock.MAX_LEADER_CYCLES = query.MAX_LEADER_CYCLES

interlock.SUPPORTED = "ok"
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

local function record(leader, window, status, cycles)
  return {leader = leader, window = window, status = status, blocked = {}, reason = interlock.reason(leader),
    cycles = cycles or 0, anchors = 0, plan_builds = 0}
end

-- ctx: song, channel (follower), config (follower's active configuration),
-- first/last (follower playable steps).
function interlock.admission(ctx)
  local leader, window = interlock.settings(ctx.config)
  if not leader then return nil end

  local frame, status = query.frame(ctx, leader)
  if not frame then return record(leader, window, status) end
  local df, dl, pl, start = frame.df, frame.dl, frame.pl, frame.start
  local w = checked_mul(window, df)
  if not w then return record(leader, window, interlock.PLAN_LIMIT) end
  -- The follower's last onset j·P_f + (N_f − 1)·d_f (finish = (j+1)·P_f).
  local last_onset = frame.finish - df

  -- §1.4 support [j·P_f − window·d_f, j·P_f + (N_f − 1)·d_f + window·d_f]:
  -- first to last follower onset widened by the window, clipped at the origin
  -- and at a known origin end.
  local high = checked_add(last_onset, w)
  if not high then return record(leader, window, interlock.PLAN_LIMIT) end
  local low
  low, high = query.clip(frame, start - w, high)

  local result = record(leader, window, interlock.SUPPORTED)
  if high < low then
    result.status = interlock.LEADER_OFF
    return result
  end

  local segments, failure, counted = query.segments(frame, low, high)
  if not segments then return record(leader, window, failure, counted) end
  result.cycles = #segments

  -- Leader anchor onsets of every evaluated cycle, ascending (cycles ascend
  -- and each cycle's onsets lie inside it). Anchor indices depend only on
  -- the governing configuration's anchor, read once per configuration.
  local by_config, anchors, contributed, missing = {}, {}, 0, false
  local ending = frame.ending
  for _, entry in ipairs(segments) do
    local indices = by_config[entry.config]
    if indices == nil then
      indices = query.anchors(frame, entry.config)
      if indices == nil then indices = "missing" end
      by_config[entry.config] = indices
    end
    if indices == "missing" then
      missing = true
    elseif indices then
      contributed = contributed + 1
      local base = checked_mul(entry.i, pl)
      if not base then return record(leader, window, interlock.PLAN_LIMIT, #segments) end
      for _, index in ipairs(indices) do
        local onset = base + (index - 1) * dl
        if not ending or onset < ending then anchors[#anchors + 1] = onset end
      end
    end
  end
  result.anchors = #anchors
  if contributed == 0 then
    result.status = missing and interlock.LEADER_MISSING or interlock.LEADER_OFF
    return result
  end

  -- |a − o| <= window·d_f for any anchor a blocks the candidate at onset o.
  local count = #anchors
  for index = 1, frame.f_count do
    local onset = start + (index - 1) * df
    -- The first anchor >= onset − w.
    local lo, hi = 1, count + 1
    while lo < hi do
      local mid = (lo + hi) // 2
      if anchors[mid] < onset - w then lo = mid + 1 else hi = mid end
    end
    if lo <= count and anchors[lo] <= onset + w then
      result.blocked[ctx.first + index - 1] = true
    end
  end
  return result
end

return interlock
