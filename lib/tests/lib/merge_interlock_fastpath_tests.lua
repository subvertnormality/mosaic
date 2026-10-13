-- Differential tests for the Interlock admission fast path
-- (docs/musical-merge-extensions-plan.md §1.4 performance): the admission
-- reads only each evaluated leader cycle's governing configuration
-- (leader_query.segment_configs, merge_state predictor config_at with the
-- closed-form fast-forward) and answers anchor counts and window checks from
-- per-configuration prefix counts instead of materialising every anchor onset.
-- Each optimised path is compared, over seeded random inputs, with a
-- reference kept here: the pre-change code (the materialising admission,
-- query.segments, the one-boundary-at-a-time predictor walk and the uncached
-- multiplier). Bounded and deterministic so the suite stays fast.

local common_time = include("mosaic/lib/musical_merge/common_time")
local merge_config = include("mosaic/lib/musical_merge/config")
local merge_state = include("mosaic/lib/musical_merge/state")
local query_module = include("mosaic/lib/musical_merge/leader_query")
local interlock_module = include("mosaic/lib/musical_merge/interlock")

local function upvalue(fn, name)
  for index = 1, 200 do
    local key, value = debug.getupvalue(fn, index)
    if key == nil then return nil end
    if key == name then return value end
  end
end

-- Equal tables and scalars, numbers also by subtype.
local function deep_equal(left, right)
  if type(left) ~= "table" or type(right) ~= "table" then
    return left == right and math.type(left) == math.type(right)
  end
  for key, value in pairs(left) do if not deep_equal(value, right[key]) then return false end end
  for key in pairs(right) do if left[key] == nil then return false end end
  return true
end

-- Reference: the admission before the fast path (materialises every anchor
-- onset of every evaluated cycle, then binary-searches each follower onset).
local function reference_admission(interlock, query, ctx)
  local checked_mul, checked_add = query.checked_mul, query.checked_add
  local function record(leader, window, status, cycles)
    return {leader = leader, window = window, status = status, blocked = {}, reason = interlock.reason(leader),
      cycles = cycles or 0, anchors = 0, plan_builds = 0, prediction_replays = 0}
  end
  local leader, window = interlock.settings(ctx.config)
  if not leader then return nil end
  local frame, status = query.frame(ctx, leader)
  if not frame then return record(leader, window, status) end
  local df, dl, pl, start = frame.df, frame.dl, frame.pl, frame.start
  local w = checked_mul(window, df)
  if not w then return record(leader, window, interlock.PLAN_LIMIT) end
  local last_onset = frame.finish - df
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
  if not segments then
    local bypassed = record(leader, window, failure, counted)
    bypassed.prediction_replays = frame.predictor and frame.predictor.replays or 0
    return bypassed
  end
  result.cycles = #segments
  result.prediction_replays = frame.predictor.replays
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
  local count = #anchors
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

function test_merge_fastpath_admission_matches_the_materialising_reference()
  local query = upvalue(interlock_module.admission, "query")
  local saved = {frame = query.frame, segments = query.segments, segment_configs = query.segment_configs,
    anchors = query.anchors}
  local random = math.random
  math.randomseed(20260927)
  local scenario
  -- The leader side is scripted: the frame, each cycle's configuration and
  -- each configuration's anchor indices. segments and segment_configs serve
  -- the same script (their own equivalence is tested below).
  query.frame = function() return scenario.frame_copy(), nil end
  query.segments = function(frame, low, high)
    local count = query.cycle_count(frame, low, high)
    if count > 64 then return nil, "PLAN LIMIT", count end
    frame.predictor = {replays = scenario.replays}
    local first = low // frame.pl
    local list = {}
    for i = first, first + count - 1 do
      local config = scenario.config_of(i)
      if config == nil then return nil, "PLAN LIMIT", count end
      list[#list + 1] = {i = i, config = config}
    end
    return list
  end
  query.segment_configs = function(frame, low, high)
    local count = query.cycle_count(frame, low, high)
    if count > 64 then return nil, "PLAN LIMIT", count end
    frame.predictor = {replays = scenario.replays}
    local first = low // frame.pl
    local list = {}
    for n = 1, count do
      local config = scenario.config_of(first + n - 1)
      if config == nil then return nil, "PLAN LIMIT", count end
      list[n] = config
    end
    return list, nil, count, first
  end
  query.anchors = function(_, config) return scenario.anchors[config] end

  local ok, failure = pcall(function()
    local statuses = {}
    for case = 1, 4000 do
      -- Occasionally durations near 2^55, so cycle bases and anchor onsets
      -- overflow (the checked PLAN LIMIT and the wrapped-onset path).
      local huge = random(50) == 1
      local df, dl = random(1, 40), random(1, 40)
      if huge then df, dl = random(1, 3) * (1 << 55), random(1, 3) * (1 << 55) end
      local l_count, f_count = random(1, 64), random(1, 64)
      if random(3) == 1 then l_count = random(1, 4) end
      local pl, pf = l_count * dl, f_count * df
      local j = random(0, 6)
      local start = j * pf
      if huge and start // pf ~= j then start = 0; j = 0 end
      local ending
      if random(3) == 1 then
        local top = (j + 2) * pf
        if top < 0 then top = math.maxinteger end
        ending = random(0, top)
      end
      local A, B, C = {}, {}, {}
      local function subset(p)
        local t = {}
        for n = 1, l_count do if random() < p then t[#t + 1] = n end end
        return t
      end
      local anchors = {[A] = subset(({0, 0.05, 0.3, 1})[random(4)]), [B] = subset(({0, 0.1, 0.5, 1})[random(4)])}
      local pool = {A, A, B, false, C} -- C: Foundation with a missing anchor
      local per = {}
      local missing_log = random(10) == 1 and random(0, 10) or -1
      local frame = {df = df, dl = dl, pl = pl, pf = pf, start = start, finish = start + pf, ending = ending,
        f_count = f_count, l_count = l_count, first = 1}
      scenario = {
        replays = random(0, 64),
        anchors = anchors,
        config_of = function(i)
          if i == missing_log then return nil end
          if per[i] == nil then per[i] = pool[random(#pool)] end
          return per[i]
        end,
        frame_copy = function()
          local copy = {}
          for key, value in pairs(frame) do copy[key] = value end
          return copy
        end,
      }
      local first = random(1, 64 - f_count + 1)
      local ctx = {config = {schema_version = 2, mode = "foundation", interlock = {leader = 1, window = random(0, 8)}},
        first = first, last = first + f_count - 1}
      local ok_reference, expected = pcall(reference_admission, interlock_module, query, ctx)
      local ok_fast, actual = pcall(interlock_module.admission, ctx)
      luaunit.assert_equals(ok_fast, ok_reference, "case " .. case)
      if not deep_equal(actual, expected) then
        luaunit.fail(string.format("case %d: huge %s df %s dl %s l_count %d f_count %d j %d ending %s window %d",
          case, tostring(huge), df, dl, l_count, f_count, j, tostring(ending), ctx.config.interlock.window))
      end
      local key = ok_reference and expected.status or "error"
      statuses[key] = (statuses[key] or 0) + 1
    end
    -- The script reaches every outcome the fast path distinguishes.
    for _, status in ipairs({"ok", "PLAN LIMIT", "LEADER OFF", "LEADER MISSING"}) do
      luaunit.assert_true((statuses[status] or 0) > 0, status)
    end
  end)
  for key, value in pairs(saved) do query[key] = value end
  if not ok then error(failure, 0) end
end

local function state_config(cycles, variation)
  local result = merge_config.new()
  result.mode = "foundation"
  result.anchor = 1
  result.cycles = cycles or 4
  result.shape = "build"
  result.percentages = merge_config.curve("build", result.cycles)
  result.variation = variation or "fixed"
  return result
end

local function random_state_config(random)
  local kind = random(6)
  if kind == 1 then return nil end
  if kind == 2 then return merge_config.new() end
  local result = state_config(({1, 2, 4, 8})[random(4)], random(2) == 1 and "fixed" or "per_phrase")
  result.seed = random(3) - 1
  if kind == 3 then result.mode = "fragments" end
  if kind == 4 then result.interlock = {leader = random(2) == 1 and 3 or 4, window = 0} end
  return result
end

-- A leader record in every shape the predictor distinguishes: none, active
-- only, queued (sometimes rejected: an edge back to the follower), odd live
-- counters.
local function random_leader(random, song, leader)
  merge_state.reset()
  if random(2) == 1 then
    local follower = state_config(1)
    follower.interlock = {leader = leader, window = 0}
    merge_state.effective(song, 3, follower)
  end
  local saved = random_state_config(random)
  if random(4) > 1 then
    local initial = random_state_config(random) or saved or state_config(2)
    merge_state.effective(song, leader, initial)
    for _ = 1, random(11) - 1 do merge_state.on_cycle_boundary(song, leader, initial) end
    if random(2) == 1 then
      local queued = random_state_config(random) or merge_config.new()
      if random(3) == 1 then queued = state_config(2); queued.interlock = {leader = 3, window = 0} end
      merge_state.request(song, leader, queued, true)
    end
    local live = merge_state.peek(song, leader)
    if random(8) == 1 then live.cycle = random(0, 12) end
    if random(12) == 1 then live.cycle = live.cycle + 0.0 end
  end
  return saved
end

local function empty_song()
  local song = {channels = {}}
  for c = 1, 16 do song.channels[c] = {} end
  return song
end

-- Reference walk: one boundary per call (the pre-change predictor walked every
-- pending boundary singly; asking for walked + 1 still does).
local function reference_at(song, leader, saved, boundaries)
  local predictor = merge_state.predictor(song, leader, saved)
  for b = 1, boundaries do predictor.at(b) end
  local result = predictor.at(boundaries)
  return result, predictor.replays
end

function test_merge_fastpath_predictor_fast_forward_matches_single_boundary_replay()
  local random = math.random
  math.randomseed(71)
  local LEADER, checks = 4, 0
  for case = 1, 1500 do
    local song = empty_song()
    local saved = random_leader(random, song, LEADER)
    local at_walk = merge_state.predictor(song, LEADER, saved)
    local config_walk = merge_state.predictor(song, LEADER, saved)
    local boundaries = 0
    for _ = 1, random(1, 6) do
      boundaries = boundaries + random(0, 40)
      local expected, replays = reference_at(song, LEADER, saved, boundaries)
      local actual = at_walk.at(boundaries)
      local label = "case " .. case .. " boundaries " .. boundaries
      luaunit.assert_true(deep_equal(actual, expected), label)
      luaunit.assert_true(config_walk.config_at(boundaries) == expected.config, label)
      luaunit.assert_equals(at_walk.replays, replays, label)
      luaunit.assert_equals(config_walk.replays, replays, label)
      checks = checks + 1
    end
  end
  merge_state.reset()
  luaunit.assert_true(checks > 3000)
end

function test_merge_fastpath_segment_configs_match_segments()
  local random = math.random
  math.randomseed(5)
  local registry = rawget(_G, "__mosaic_merge_timeline")
  local saved_running, saved_channels = registry.running, registry.channels
  local ok, failure = pcall(function()
    local LEADER = 4
    for case = 1, 3000 do
      local song = empty_song()
      local saved = random_leader(random, song, LEADER)
      local running = random(2) == 1
      local k_l = running and random(0, 200) or 0
      registry.running = running
      -- Logged cycles, with occasional gaps (a needed entry gone: PLAN LIMIT).
      local log = {k = k_l, log_index = {}, log_config = {}, log_cycle = {}, log_phrase = {}}
      local configs = {state_config(1), false, merge_config.new()}
      for i = math.max(0, k_l - 63), k_l do
        if random(20) > 1 then
          local slot = i % 64 + 1
          log.log_index[slot] = i
          log.log_config[slot] = configs[random(3)]
          log.log_cycle[slot], log.log_phrase[slot] = 1, 0
        end
      end
      registry.channels = {[LEADER] = log}
      local pl = random(1, 50)
      local low = random(0, (k_l + 70) * pl)
      local high = low + random(0, 70 * pl)
      local frame_a = {song = song, leader = LEADER, saved = saved, k_l = k_l, running = running, pl = pl}
      local frame_b = {song = song, leader = LEADER, saved = saved, k_l = k_l, running = running, pl = pl}
      local segments, failure_a, count_a = query_module.segments(frame_a, low, high)
      local list, failure_b, count_b, first = query_module.segment_configs(frame_b, low, high)
      local label = "case " .. case
      luaunit.assert_equals(list == nil, segments == nil, label)
      luaunit.assert_equals(failure_b, failure_a, label)
      if segments then
        luaunit.assert_equals(count_b, #segments, label)
        luaunit.assert_equals(first, segments[1].i, label)
        for n = 1, #segments do luaunit.assert_true(list[n] == segments[n].config, label .. " n " .. n) end
        luaunit.assert_nil(list[#segments + 1], label)
      else
        luaunit.assert_equals(count_b, count_a, label)
      end
      luaunit.assert_equals(frame_b.predictor and frame_b.predictor.replays,
        frame_a.predictor and frame_a.predictor.replays, label)
    end
  end)
  registry.running, registry.channels = saved_running, saved_channels
  merge_state.reset()
  if not ok then error(failure, 0) end
end

function test_merge_fastpath_multiplier_cache_matches_exact_conversion()
  local random = math.random
  math.randomseed(13)
  local values = {1, 2, 3, 4, 8, 16, 0.5, 1.5, 2.6, 5.3, 1 / 3, 1.25, 7, 0.001, 1e-7, 12.0, 3.0}
  for case = 1, 2000 do
    local kind = random(2) == 1 and "clock_multiplication" or "clock_division"
    local value = values[random(#values)]
    if random(4) == 1 then value = random(1, 4000) / 100 end
    if random(5) == 1 and math.type(value) == "integer" then value = value + 0.0 end
    local expected = {common_time.exact_multiplier(kind, value)}
    local actual = {common_time.multiplier({type = kind, value = value})}
    luaunit.assert_true(deep_equal(actual, expected), string.format("case %d %s %s", case, kind, tostring(value)))
    -- Each call returns its own rational: a caller writing it changes no
    -- later result.
    if actual[1] then actual[1][1], actual[1][2] = -1, -1 end
  end
  -- Integer and float keys of equal value share one entry; both convert the same.
  luaunit.assert_equals(common_time.multiplier({type = "clock_division", value = 4.0}),
    common_time.multiplier({type = "clock_division", value = 4}))
end
