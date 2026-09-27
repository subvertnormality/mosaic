local dependency = include("mosaic/lib/musical_merge/dependency")

local state = {}

local registry = rawget(_G, "__mosaic_merge_runtime_state")
if not registry then
  registry = {songs=setmetatable({}, {__mode="k"})}
  rawset(_G, "__mosaic_merge_runtime_state", registry)
end
local songs = registry.songs

local function deep_copy(value, seen)
  if type(value) ~= "table" then return value end
  seen = seen or {}
  if seen[value] then return seen[value] end
  local result = {}
  seen[value] = result
  for key, item in pairs(value) do result[deep_copy(key, seen)] = deep_copy(item, seen) end
  return result
end

local function channel_states(song)
  local values = songs[song]
  if not values then
    values = {}
    songs[song] = values
  end
  return values
end

local function record_for(song, channel, requested)
  local values = channel_states(song)
  local record = values[channel]
  if not record then
    record = {active = deep_copy(requested), cycle = 1, phrase = 0}
    values[channel] = record
  end
  return record
end

local function same_percentages(left, right)
  left, right = left or {}, right or {}
  if #left ~= #right then return false end
  for index = 1, #left do if left[index] ~= right[index] then return false end end
  return true
end

-- A v1 configuration (no fragments table) has the v2 default size.
local function fragment_size(value)
  return value.fragments and value.fragments.size or 8
end

local function starts_new_epoch(left, right)
  if not left or not right then return true end
  return left.cycles ~= right.cycles or left.variation ~= right.variation or
    left.seed ~= right.seed or not same_percentages(left.percentages, right.percentages) or
    (left.mode or "off") ~= (right.mode or "off") or fragment_size(left) ~= fragment_size(right)
end

local function advance(record)
  local cycles = record.active and record.active.cycles or 1
  if record.cycle >= cycles then
    record.cycle = 1
    record.phrase = record.phrase + 1
  else
    record.cycle = record.cycle + 1
  end
end

local function same(left, right)
  if type(left) ~= "table" or type(right) ~= "table" then return left == right end
  for key, value in pairs(left) do if not same(value, right[key]) then return false end end
  for key in pairs(right) do if left[key] == nil then return false end end
  return true
end

-- Plan §1.5: every intermediate active graph is one-way. Edges are configured
-- leaders, counted whether or not their feature is active.
local function active_of(song, values, number)
  local record = values and values[number]
  if record then return record.active end
  local channel = type(song) == "table" and type(song.channels) == "table" and song.channels[number]
  return type(channel) == "table" and channel.musical_merge or nil
end

-- nil when making `candidate` channel `channel`'s active configuration keeps
-- the active graph one-way; otherwise the rejection reason.
local function activation_violation(song, channel, candidate)
  local values = songs[song]
  local edges = {}
  for number = 1, 16 do
    dependency.add(edges, number, number == channel and candidate or active_of(song, values, number))
  end
  local ok, reason = dependency.check(edges, {[channel] = true})
  if ok then return nil end
  return reason
end
state.activation_violation = activation_violation

function state.reset()
  for song in pairs(songs) do songs[song]=nil end
end

function state.reset_song(song) songs[song]=nil end

function state.request(song, channel, requested, playing)
  local record = record_for(song, channel, requested)
  if playing then
    -- A later request supersedes a pending cross-feature one, but keeps its
    -- shared pattern boundary: landing it at an earlier channel wrap would
    -- activate repaired or restored references before the group change they
    -- pair with (plan §4 Reference lifecycle). One that restores the active
    -- configuration withdraws it without leaving a channel queue: no change
    -- inside the cycle ever happens (plan §1.2.3).
    if record.global_queued then
      record.global_queued = not same(requested, record.active) and deep_copy(requested) or nil
      record.queued = nil
    else
      record.queued = deep_copy(requested)
    end
    return "queued"
  end
  local restart = starts_new_epoch(record.active, requested)
  record.active = deep_copy(requested)
  record.queued = nil
  if restart then record.cycle, record.phrase = 1, 0 end
  return "applied"
end

-- Cross-feature transactions (for example deleting a referenced Harmony group)
-- activate with the shared song-pattern snapshot, not an earlier channel wrap.
function state.request_global(song, channel, requested, playing)
  local record=record_for(song,channel,requested)
  -- The global request replaces a pending per-channel one, so an older queue
  -- cannot land at an earlier channel wrap (plan §4 Reference lifecycle).
  -- Restoring the active configuration (undo before the boundary) withdraws
  -- the pending global change instead of queueing an identical one.
  if playing then
    record.global_queued=not same(requested,record.active)and deep_copy(requested)or nil
    record.queued=nil;return "queued"
  end
  local restart=starts_new_epoch(record.active,requested);record.active=deep_copy(requested)
  record.queued,record.global_queued=nil,nil;if restart then record.cycle,record.phrase=1,0 end
  return "applied"
end

function state.on_pattern_boundary(song)
  local values=songs[song];local affected={};if not values then return affected end
  for channel,record in pairs(values)do if record.global_queued then
    -- Plan §1.5: verify the invariant before mutation; a violation retains the
    -- previous active snapshot with the rejection reason.
    local violation=activation_violation(song,channel,record.global_queued)
    record.rejected=violation
    if not violation then
      local restart=starts_new_epoch(record.active,record.global_queued)
      record.active=record.global_queued;record.global_queued=nil;record.queued=nil
      if restart then record.cycle,record.phrase=1,0 end
      affected[channel]=true
    end
  end end
  return affected
end

-- One channel boundary, exactly as the clock applies it at a wrap. Shared by
-- the live boundary and the pure replay used for prediction (plan §1.2.3).
local function cycle_boundary(song, channel, record)
  if record.queued then
    local violation = activation_violation(song, channel, record.queued)
    record.rejected = violation
    if not violation then
      local restart = starts_new_epoch(record.active, record.queued)
      record.active = record.queued
      record.queued = nil
      if restart then
        record.cycle, record.phrase = 1, 0
        return true
      end
    end
  end
  advance(record)
  return false
end

function state.on_cycle_boundary(song, channel, requested)
  return cycle_boundary(song, channel, record_for(song, channel, requested))
end

-- The existing record, without creating one (effective creates records).
function state.peek(song, channel)
  local values = songs[song]
  return values and values[channel] or nil
end

-- Whether the clock runs on_cycle_boundary for this record at a wrap: a saved
-- configuration, or merge state it owes work to (state.has; m_clock wrap).
local function owes_boundary(saved, record)
  if saved ~= nil then return true end
  if not record then return false end
  if record.queued ~= nil then return true end
  local active = record.active
  return active ~= nil and active.mode ~= nil and active.mode ~= "off"
end

-- An incremental predictor over a channel's pending boundaries (plan
-- §1.2.3): a pure copy of the channel's record, carried forward one boundary
-- at a time, each exactly as m_clock applies it (on_cycle_boundary runs only
-- when the channel has a saved configuration or merge state). `at(n)` returns
-- {config, cycle, phrase} after n boundaries; n must not decrease between
-- calls, so walking the pending boundaries of one query in ascending order
-- replays each boundary once (O(n), not O(n²)). `replays` counts the
-- boundaries walked. Nothing live is changed. Each boundary is the same
-- deterministic step state.predict replays, and the live song state it reads
-- (activation_violation's edge union) does not change during a query, so the
-- result for every n equals state.predict(song, channel, saved, n).
function state.predictor(song, channel, saved)
  local live = state.peek(song, channel)
  local record
  if live then
    record = {active = live.active, queued = live.queued, cycle = live.cycle, phrase = live.phrase}
  else
    record = {active = saved, cycle = 1, phrase = 0}
  end
  local predictor = {walked = 0, replays = 0}
  function predictor.at(boundaries)
    if boundaries < predictor.walked then error("merge_state predictor: boundaries decreased", 2) end
    while predictor.walked < boundaries do
      if owes_boundary(saved, record) then cycle_boundary(song, channel, record) end
      predictor.walked = predictor.walked + 1
      predictor.replays = predictor.replays + 1
    end
    return {config = record.active, cycle = record.cycle, phrase = record.phrase}
  end
  return predictor
end

-- A pure copy of a channel's record after replaying `boundaries` pending
-- channel boundaries (a fresh predictor walked once). Returns {config, cycle,
-- phrase}.
function state.predict(song, channel, saved, boundaries)
  return state.predictor(song, channel, saved).at(boundaries)
end

function state.effective(song, channel, requested)
  local record = record_for(song, channel, requested)
  return {
    config = record.active,
    queued = record.queued,
    cycle = record.cycle,
    phrase = record.phrase,
    ranking_phrase = record.active and record.active.variation == "per_phrase" and record.phrase or 0
  }
end

-- Whether this channel has merge state the clock owes work to.
--
-- A record is NOT evidence of that. pattern.get_and_merge_patterns calls
-- state.effective for every channel it merges, including channels with no
-- merge configured, and effective creates a record as a side effect. Treating
-- a bare record as merge state made the clock run on_cycle_boundary and
-- invalidate the lookahead scheduler for every channel in the song; under a
-- lead time the lookahead has already sent the upcoming step, so invalidating
-- it re-resolved and re-emitted that step and the note at the wrap sounded
-- twice.
--
-- A queued change still counts: merge turned off mid-play owes its wind-down
-- at the next boundary.
function state.has(song, channel)
  local record = songs[song] and songs[song][channel]
  if not record then return false end
  if record.queued ~= nil then return true end
  local active = record.active
  return active ~= nil and active.mode ~= nil and active.mode ~= "off"
end

function state.stop(song)
  local values = songs[song]
  if not values then return {} end
  local affected={}
  for channel, record in pairs(values) do
    if record.global_queued or record.queued then
      record.active = record.global_queued or record.queued
      record.queued,record.global_queued = nil,nil
    end
    record.cycle, record.phrase = 1, 0
    affected[channel]=true
  end
  return affected
end

function state.stop_all()
  local affected={};for song in pairs(songs)do affected[song]=state.stop(song)end;return affected
end

return state
