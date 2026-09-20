local config_state = {}
local registry = rawget(_G, "__mosaic_harmony_config_state")
if not registry then
  registry = {songs=setmetatable({}, {__mode="k"})}
  rawset(_G, "__mosaic_harmony_config_state", registry)
end
local songs = registry.songs

local function copy(value, seen)
  if type(value) ~= "table" then return value end
  seen = seen or {}
  if seen[value] then return seen[value] end
  local result = {}
  seen[value] = result
  for key, item in pairs(value) do result[copy(key, seen)] = copy(item, seen) end
  return result
end

local function records(song)
  local result = songs[song]
  if not result then result={}; songs[song]=result end
  return result
end

local function record(song, channel, requested)
  local values = records(song)
  local result = values[channel]
  if not result then
    result = {active=copy(requested), requested=copy(requested)}
    values[channel] = result
  end
  return result
end

function config_state.effective_channel(song, channel, requested)
  return record(song, channel, requested).active
end

function config_state.request_channel(song, channel, requested, playing)
  local value = record(song, channel, requested)
  value.requested = copy(requested)
  if playing then
    value.queued = copy(requested)
    return "queued"
  end
  value.active = copy(requested)
  value.queued = nil
  return "applied"
end

local function song_record(song, requested)
  local values = records(song)
  if not values._song then
    values._song = {active=copy(requested), requested=copy(requested)}
  end
  return values._song
end

function config_state.effective_song(song, requested)
  return song_record(song, requested).active
end

function config_state.request_song(song, requested, playing)
  local value = song_record(song, requested)
  value.requested = copy(requested)
  if playing then value.queued=copy(requested); return "queued" end
  value.active=copy(requested); value.queued=nil; return "applied"
end

function config_state.on_pattern_boundary(song)
  for _, value in pairs(records(song)) do
    if value.queued then value.active=value.queued; value.queued=nil end
  end
end

function config_state.status(song, channel)
  return copy(records(song)[channel] or {})
end

function config_state.stop(song)
  config_state.on_pattern_boundary(song)
end

function config_state.stop_all()
  for song in pairs(songs) do config_state.stop(song) end
end

function config_state.enter_song(song)
  local values=records(song)
  values._song={active=copy(song.voicing or{schema_version=1,groups={}}),requested=copy(song.voicing or{schema_version=1,groups={}})}
  for channel=1,16 do
    local requested=song.channels[channel].voicing
    if requested then values[channel]={active=copy(requested),requested=copy(requested)} else values[channel]=nil end
  end
end

function config_state.reset_song(song)
  songs[song] = nil
end

function config_state.reset()
  for song in pairs(songs) do songs[song]=nil end
end

return config_state
