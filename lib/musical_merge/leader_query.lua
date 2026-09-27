-- The leader query shared by Interlock (MM-09) and Space (MM-12):
-- docs/musical-merge-extensions-plan.md §1.2.3 (evaluating a leader cycle) and
-- §1.4 (query support and bounded work).
--
-- A follower's admission runs inside its working-pattern build for its current
-- cycle j = k_f and reads only song data, merge_state records and the
-- transport-owned counters and cycle logs (§1.2), never another channel's
-- callback-visible runtime state or emitted result. Each filter asks for the
-- leader cycles over its own support; the budget (64 leader cycles, 8 distinct
-- leader plans) is checked before any plan is built, and leader plans are
-- memoised only within one working-pattern build (ctx.plan_memo).
local common_time = include("mosaic/lib/musical_merge/common_time")
local merge_state = include("mosaic/lib/musical_merge/state")
local timeline = include("mosaic/lib/musical_merge/timeline")

local query = {}

-- §1.4 budget, checked before any plan is built.
query.MAX_LEADER_CYCLES = 64
query.MAX_LEADER_PLANS = 8

query.RESYNC = "RESYNC"
query.PLAN_LIMIT = "PLAN LIMIT"

local checked_mul, checked_add = common_time.checked_mul, common_time.checked_add
query.checked_mul, query.checked_add = checked_mul, checked_add

-- Whether a status is an unsupported admission (§1.2): it bypasses both
-- filters for the follower's cycle.
function query.unsupported(status)
  return status == query.RESYNC or status == query.PLAN_LIMIT
end

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

-- The distinct-plan identity (§1.4): configuration entry × cycle_in_phrase ×
-- ranking phrase. An Off (or legacy) cycle's plan never depends on the phrase.
function query.plan_key(config, cycle, phrase)
  if not config then return "off" end
  local ranking = config.variation == "per_phrase" and phrase or 0
  return tostring(config) .. "|" .. tostring(cycle) .. "|" .. tostring(ranking)
end

-- The common frame of one follower/leader query, or nil and the bypass status.
-- All nominal times are integers over one common denominator `scale`.
function query.frame(ctx, leader)
  local song, follower = ctx.song, ctx.channel

  -- §1.2.3: from the moment a global (pattern-boundary) activation is queued
  -- for the leader or the follower, every admission of the follower is
  -- unsupported until it lands (then the sticky resync continues it) or is
  -- withdrawn.
  local follower_record, leader_record = merge_state.peek(song, follower), merge_state.peek(song, leader)
  if (follower_record and follower_record.global_queued) or (leader_record and leader_record.global_queued) then
    return nil, query.RESYNC
  end

  local running = timeline.running()
  local j, k_l = 0, 0
  if running then
    -- Either check sets the sticky resync on a changed timing.
    local follower_ok = timeline.check_timing(song, follower)
    local leader_ok = timeline.check_timing(song, leader)
    if not follower_ok or not leader_ok then return nil, query.RESYNC end
    j, k_l = timeline.k(follower), timeline.k(leader)
    -- Between a realign and the forced wrap (k = -1) the next onset starts cycle 0.
    if j < 0 then j = 0 end
  end

  local leader_channel = song.channels[leader]
  local follower_channel = song.channels[follower]
  local length = song.global_pattern_length or 64
  local d_f = common_time.step_duration(follower_channel.clock_mods)
  local d_l = common_time.step_duration(leader_channel.clock_mods)
  if not d_f or not d_l then return nil, query.PLAN_LIMIT end
  local l_first, l_last = timeline.bounds(leader_channel, length)
  local f_count = ctx.last - ctx.first + 1
  local l_count = l_last - l_first + 1
  if f_count < 1 or l_count < 1 then return nil, query.PLAN_LIMIT end

  local scale = common_time.common_denominator({d_f, d_l, common_time.MASTER_STEP})
  if not scale then return nil, query.PLAN_LIMIT end
  local df = common_time.numerator_over(d_f, scale)
  local dl = common_time.numerator_over(d_l, scale)
  local master = common_time.numerator_over(common_time.MASTER_STEP, scale)
  local pf = df and checked_mul(f_count, df)
  local pl = dl and checked_mul(l_count, dl)
  local start = pf and checked_mul(j, pf)
  local finish = start and checked_add(start, pf)
  if not (pf and pl and start and finish and master) then return nil, query.PLAN_LIMIT end

  -- §1.2.3: a pattern boundary that will change the slot or realign ends the
  -- origin; leader onsets at or after it are excluded.
  local ending
  local transition = step and step.origin_end_boundary
  local boundary = transition and transition(timeline.elapsed_master()) or nil
  if boundary then
    ending = checked_mul(checked_mul(boundary, length) or 0, master)
    if not ending then return nil, query.PLAN_LIMIT end
  end

  return {
    song = song, follower = follower, leader = leader, running = running, j = j, k_l = k_l,
    first = ctx.first, f_count = f_count, l_first = l_first, l_last = l_last, l_count = l_count,
    scale = scale, df = df, dl = dl, pf = pf, pl = pl, start = start, finish = finish, ending = ending,
    saved = leader_channel.musical_merge
  }
end

-- Clip a support [low, high] at the origin and at the origin's end.
function query.clip(frame, low, high)
  if low < 0 then low = 0 end
  if frame.ending and high > frame.ending - 1 then high = frame.ending - 1 end
  return low, high
end

-- The leader cycles meeting [low, high] with their governing segments. A
-- segment gets a plan key when `counts(config)` is true; distinct keys are
-- budgeted. Returns the list, or nil and PLAN LIMIT.
function query.segments(frame, low, high, counts)
  local pl = frame.pl
  local first_cycle, last_cycle = low // pl, high // pl
  if last_cycle - first_cycle + 1 > query.MAX_LEADER_CYCLES then return nil, query.PLAN_LIMIT end
  local segments, keys, distinct = {}, {}, 0
  for i = first_cycle, last_cycle do
    local config, cycle, phrase = segment(frame.song, frame.leader, frame.saved, i, frame.k_l, frame.running)
    if config == nil then return nil, query.PLAN_LIMIT end
    local entry = {i = i, config = config, cycle = cycle, phrase = phrase}
    if counts(config) then
      local key = query.plan_key(config, cycle, phrase)
      entry.key = key
      if not keys[key] then
        keys[key] = true
        distinct = distinct + 1
        if distinct > query.MAX_LEADER_PLANS then return nil, query.PLAN_LIMIT end
      end
    end
    segments[#segments + 1] = entry
  end
  return segments
end

-- The leader cycle plan of a segment, memoised within the working-pattern
-- build that owns ctx.plan_memo (shared by both filters for one leader).
function query.plan(ctx, frame, entry)
  local memo = ctx.plan_memo
  if not memo then memo = {}; ctx.plan_memo = memo end
  local key = frame.leader .. "|" .. entry.key
  local plan = memo[key]
  if plan == nil then
    plan = ctx.leader_plan(frame.leader, entry.config or nil, entry.cycle, entry.phrase) or false
    memo[key] = plan
    ctx.plan_builds = (ctx.plan_builds or 0) + 1
  end
  return plan or nil
end

return query
