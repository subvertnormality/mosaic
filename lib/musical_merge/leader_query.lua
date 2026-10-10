-- The leader query of MM-09 Interlock: docs/musical-merge-extensions-plan.md
-- §1.2.3 (evaluating a leader cycle, leader anchors for cycle i) and §1.4
-- (query support and bounded work).
--
-- A follower's admission runs inside its working-pattern build for its current
-- cycle j = k_f and reads only song data, merge_state records and the
-- transport-owned counters and cycle logs (§1.2), never another channel's
-- callback-visible runtime state or emitted result. No leader plan or working
-- pattern is ever built: a leader cycle's anchors are read directly from the
-- currently stored anchor pattern under the cycle's governing configuration
-- (§1.2.3). The single budget is 64 leader cycles per admission (§1.4).
local common_time = include("mosaic/lib/musical_merge/common_time")
local merge_state = include("mosaic/lib/musical_merge/state")
local timeline = include("mosaic/lib/musical_merge/timeline")

local query = {}

-- §1.4 budget (single authority): leader cycles per admission.
query.MAX_LEADER_CYCLES = 64

query.RESYNC = "RESYNC"
query.PLAN_LIMIT = "PLAN LIMIT"

local checked_mul, checked_add = common_time.checked_mul, common_time.checked_add
query.checked_mul, query.checked_add = checked_mul, checked_add

-- RESYNC and PLAN LIMIT are the unsupported admissions (§1.2): they bypass
-- Interlock only, for the follower's cycle; the rest of the Foundation
-- pipeline runs as with Interlock off.

-- The governing segment of leader cycle i (§1.2.3): logged when its boundary
-- has been applied (i <= k_l), otherwise predicted by replaying the pending
-- boundaries from a pure copy of the leader's merge_state record. `predictor`
-- is the admission's one incremental walk (merge_state.predictor): segments
-- are asked for in ascending i, so each pending boundary is replayed once.
-- Returns config (false for Off), cycle, phrase; nil when a needed log entry
-- is gone.
local function segment(song, leader, saved, i, k_l, running, predictor)
  if running then
    if i <= k_l then return timeline.segment(leader, i) end
    local predicted = predictor.at(i - k_l)
    return predicted.config or false, predicted.cycle, predicted.phrase
  end
  -- Stopped (§1.3): k_l = 0; the requested (or queued) configuration is the
  -- entry at 0 and later cycles are predicted from it.
  if i == 0 then
    local record = merge_state.peek(song, leader)
    if record then return record.queued or record.active or false, record.cycle, record.phrase end
    return saved or false, 1, 0
  end
  local predicted = predictor.at(i)
  return predicted.config or false, predicted.cycle, predicted.phrase
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

-- The number of leader cycles meeting the closed interval [low, high] (§1.4):
-- floor(high / P_l) − floor(low / P_l) + 1 (low >= 0 after clipping).
function query.cycle_count(frame, low, high)
  return high // frame.pl - low // frame.pl + 1
end

-- The leader cycles meeting [low, high] with their governing segments
-- ({i, config, cycle, phrase}; config false for Off), in ascending i, with
-- frame.predictor holding the walk (its `replays` count). Returns the list, or
-- nil, PLAN LIMIT and the counted cycles when the 64-cycle budget would be
-- exceeded or a needed log entry is gone. The admission uses
-- query.segment_configs; this full form is kept for diagnostics and as the
-- reference the differential tests compare it with.
function query.segments(frame, low, high)
  local count = query.cycle_count(frame, low, high)
  if count > query.MAX_LEADER_CYCLES then return nil, query.PLAN_LIMIT, count end
  local first_cycle = low // frame.pl
  local segments = {}
  -- One incremental prediction walk per admission (not shared across
  -- followers: a boundary replay reads the song-wide dependency edges, so a
  -- complete cross-admission cache key is not available).
  local predictor = merge_state.predictor(frame.song, frame.leader, frame.saved)
  frame.predictor = predictor
  for i = first_cycle, first_cycle + count - 1 do
    local config, cycle, phrase = segment(frame.song, frame.leader, frame.saved, i, frame.k_l, frame.running, predictor)
    if config == nil then return nil, query.PLAN_LIMIT, count end
    segments[#segments + 1] = {i = i, config = config, cycle = cycle, phrase = phrase}
  end
  return segments
end

-- The governing configuration alone of leader cycle i (segment's first
-- value, without the predictor's result table).
local function segment_config(song, leader, saved, i, k_l, running, predictor)
  if running then
    if i <= k_l then return (timeline.segment(leader, i)) end
    return predictor.config_at(i - k_l) or false
  end
  if i == 0 then
    local record = merge_state.peek(song, leader)
    if record then return record.queued or record.active or false end
    return saved or false
  end
  return predictor.config_at(i) or false
end

-- query.segments reduced to what the admission reads: the governing
-- configurations of cycles first_cycle .. first_cycle + count - 1 as a
-- 1-based array (false for Off), with the same budget, failure and predictor
-- walk. Returns configs, nil, count, first_cycle; or nil, PLAN LIMIT, count.
function query.segment_configs(frame, low, high)
  local count = query.cycle_count(frame, low, high)
  if count > query.MAX_LEADER_CYCLES then return nil, query.PLAN_LIMIT, count end
  local first_cycle = low // frame.pl
  local configs = {}
  local predictor = merge_state.predictor(frame.song, frame.leader, frame.saved)
  frame.predictor = predictor
  local song, leader, saved, k_l, running = frame.song, frame.leader, frame.saved, frame.k_l, frame.running
  for n = 1, count do
    local i = first_cycle + n - 1
    local config = segment_config(song, leader, saved, i, k_l, running, predictor)
    if config == nil then return nil, query.PLAN_LIMIT, count end
    configs[n] = config
    -- Once a cycle is predicted every later one is; with nothing queued they
    -- all keep this configuration. One walk to the last replays the rest.
    if n < count and (running and i > k_l or not running and i > 0) and predictor.settled() then
      local last = first_cycle + count - 1
      predictor.config_at(running and last - k_l or last)
      for rest = n + 1, count do configs[rest] = config end
      break
    end
  end
  return configs, nil, count, first_cycle
end

-- Leader anchors for a cycle governed by `config` (§1.2.3, the one
-- authoritative definition): when the configuration is Foundation with a valid
-- anchor pattern (assigned to the leader, as foundation.plan requires), the
-- 1-based indices n into the leader's playable range where the currently
-- stored anchor pattern has a trig; before masks and probability. Returns the
-- ascending index list; false for a non-Foundation (Off) configuration; nil
-- for Foundation with a missing anchor. This equals the set foundation.plan
-- marks `anchor` for the same configuration and stored data, and reads
-- nothing else of the leader; its phrase position cannot change it.
function query.anchors(frame, config)
  if type(config) ~= "table" or config.mode ~= "foundation" or
    (config.schema_version ~= 1 and config.schema_version ~= 2) then return false end
  if (config.ranking_version or 1) ~= 1 then return nil end
  local anchor = config.anchor
  local leader_channel = frame.song.channels[frame.leader]
  local assigned = leader_channel.selected_patterns
  local source = anchor ~= nil and assigned and assigned[anchor] and frame.song.patterns[anchor]
  local trigs = source and source.trig_values
  if type(trigs) ~= "table" then return nil end
  local result = {}
  for index = 1, frame.l_count do
    local value = trigs[frame.l_first + index - 1]
    if value == 1 or value == true then result[#result + 1] = index end
  end
  return result
end

return query
