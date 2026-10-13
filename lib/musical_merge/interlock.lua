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
--   prediction_replays  pending leader boundaries replayed by the admission's
--               one incremental prediction walk (at most `cycles`).
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
    cycles = cycles or 0, anchors = 0, plan_builds = 0, prediction_replays = 0}
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

  local configs, failure, counted, first_cycle = query.segment_configs(frame, low, high)
  if not configs then
    local bypassed = record(leader, window, failure, counted)
    bypassed.prediction_replays = frame.predictor and frame.predictor.replays or 0
    return bypassed
  end
  local cycle_count = counted
  result.cycles = cycle_count
  result.prediction_replays = frame.predictor.replays

  -- Leader anchor onsets of every evaluated cycle i are i·P_l + (n − 1)·d_l
  -- for the anchor indices n of its governing configuration (read once per
  -- configuration), before the origin end. They are not materialised: per
  -- configuration a prefix count over the indices answers "how many anchors
  -- with index in [a, b]" in O(1), which gives both the anchor count and,
  -- per follower onset, whether an anchor lies within the window.
  local l_count, ending = frame.l_count, frame.ending
  local span = (l_count - 1) * dl
  local by_config, prefixes, contributed, missing, total = {}, {}, 0, false, 0
  local materialise = false
  -- When the last cycle's last onset is representable every earlier one is
  -- (i >= 0, P_l > 0): the per-cycle checks below cannot fail.
  local last_base = checked_mul(first_cycle + cycle_count - 1, pl)
  local checked = not (last_base and checked_add(last_base, span))
  for n = 1, cycle_count do
    local config = configs[n]
    local prefix = by_config[config]
    if prefix == nil then
      local indices = query.anchors(frame, config)
      if indices == nil then
        prefix = "missing"
      elseif indices then
        prefix = {0}
        local have, next_index = 0, 1
        for index = 1, l_count do
          if indices[next_index] == index then have = have + 1; next_index = next_index + 1 end
          prefix[index + 1] = have
        end
      else
        prefix = false
      end
      by_config[config] = prefix
    end
    if prefix == "missing" then
      missing = true
    elseif prefix then
      contributed = contributed + 1
      local base
      if checked then
        base = checked_mul(first_cycle + n - 1, pl)
        if not base then return record(leader, window, interlock.PLAN_LIMIT, cycle_count) end
        -- An onset past maxinteger wraps in the materialised form; keep it.
        if not checked_add(base, span) then materialise = true end
      else
        base = (first_cycle + n - 1) * pl
      end
      local limit = l_count
      if ending then
        local before = (ending - base - 1) // dl + 1
        if before < limit then limit = before end
      end
      if limit > 0 then total = total + prefix[limit + 1] end
      prefixes[n] = prefix
    end
  end
  result.anchors = total
  if contributed == 0 then
    result.status = missing and interlock.LEADER_MISSING or interlock.LEADER_OFF
    return result
  end

  if materialise then
    local anchors = {}
    for n = 1, cycle_count do
      local prefix = prefixes[n]
      if prefix then
        local base = (first_cycle + n - 1) * pl
        for index = 1, l_count do
          if prefix[index + 1] ~= prefix[index] then
            local onset = base + (index - 1) * dl
            if not ending or onset < ending then anchors[#anchors + 1] = onset end
          end
        end
      end
    end
    local count = #anchors
    result.anchors = count
    for index = 1, frame.f_count do
      local onset = start + (index - 1) * df
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

  -- |a − o| <= window·d_f for any anchor a blocks the candidate at onset o.
  -- Cycle i holds onsets [i·P_l, (i + 1)·P_l), so only cycles
  -- floor((o − w) / P_l) .. floor((o + w) / P_l) can hold such an anchor.
  local last_cycle = first_cycle + cycle_count - 1
  local blocked, first = result.blocked, ctx.first
  for index = 1, frame.f_count do
    local onset = start + (index - 1) * df
    local from, to = onset - w, onset + w
    local i_low, i_high = from // pl, to // pl
    if i_low < first_cycle then i_low = first_cycle end
    if i_high > last_cycle then i_high = last_cycle end
    for i = i_low, i_high do
      local prefix = prefixes[i - first_cycle + 1]
      if prefix then
        local base = i * pl
        -- Indices n (1-based) with from <= base + (n − 1)·d_l <= to.
        local n_low = -((base - from) // dl) + 1
        local n_high = (to - base) // dl + 1
        if n_low < 1 then n_low = 1 end
        if n_high > l_count then n_high = l_count end
        if ending then
          local before = (ending - base - 1) // dl + 1
          if before < n_high then n_high = before end
        end
        if n_low <= n_high and prefix[n_high + 1] > prefix[n_low] then
          blocked[first + index - 1] = true
          break
        end
      end
    end
  end
  return result
end

return interlock
