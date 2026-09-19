local state = {}

local songs = setmetatable({}, {__mode = "k"})

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
  songs = setmetatable({}, {__mode = "k"})
end

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

function state.stop(song)
  local values = songs[song]
  if not values then return end
  for _, record in pairs(values) do
    if record.queued then
      record.active = record.queued
      record.queued = nil
    end
    record.cycle, record.phrase = 1, 0
  end
end

function state.stop_all()
  for song in pairs(songs) do state.stop(song) end
end

return state
