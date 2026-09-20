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

local function starts_new_epoch(left, right)
  if not left or not right then return true end
  return left.cycles ~= right.cycles or left.variation ~= right.variation or
    left.seed ~= right.seed or not same_percentages(left.percentages, right.percentages)
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

function state.reset()
  for song in pairs(songs) do songs[song]=nil end
end

function state.reset_song(song) songs[song]=nil end

function state.request(song, channel, requested, playing)
  local record = record_for(song, channel, requested)
  if playing then
    record.queued = deep_copy(requested)
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
  if playing then record.global_queued=deep_copy(requested);return "queued"end
  local restart=starts_new_epoch(record.active,requested);record.active=deep_copy(requested)
  record.queued,record.global_queued=nil,nil;if restart then record.cycle,record.phrase=1,0 end
  return "applied"
end

function state.on_pattern_boundary(song)
  local values=songs[song];local affected={};if not values then return affected end
  for channel,record in pairs(values)do if record.global_queued then
    local restart=starts_new_epoch(record.active,record.global_queued)
    record.active=record.global_queued;record.global_queued=nil;record.queued=nil
    if restart then record.cycle,record.phrase=1,0 end
    affected[channel]=true
  end end
  return affected
end

function state.on_cycle_boundary(song, channel, requested)
  local record = record_for(song, channel, requested)
  if record.queued then
    local restart = starts_new_epoch(record.active, record.queued)
    record.active = record.queued
    record.queued = nil
    if restart then
      record.cycle, record.phrase = 1, 0
      return true
    end
  end
  advance(record)
  return false
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

function state.has(song,channel)return songs[song]and songs[song][channel]~=nil end

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
