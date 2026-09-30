local voicing = include("mosaic/lib/harmony/voicing")
local harmony_config = include("mosaic/lib/harmony/config")

local harmony_state = {}
local registry = rawget(_G, "__mosaic_harmony_runtime_state")
if not registry then
  registry = {songs=setmetatable({}, {__mode="k"})}
  rawset(_G, "__mosaic_harmony_runtime_state", registry)
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

local function fingerprint(value)
  if type(value) ~= "table" then return tostring(value) end
  local keys = {}; for key in pairs(value) do keys[#keys+1]=key end
  table.sort(keys,function(a,b)return tostring(a)<tostring(b)end)
  local parts={"{"};for _,key in ipairs(keys)do parts[#parts+1]=tostring(key);parts[#parts+1]="=";parts[#parts+1]=fingerprint(value[key]);parts[#parts+1]=";"end
  parts[#parts+1]="}";return table.concat(parts)
end

local function state_for(song)
  local state = songs[song]
  if not state then
    state = {groups = {}, channels = {}}
    songs[song] = state
  end
  return state
end

local function enabled_roles(channel, count)
  local roles = {}
  for index = 1, 5 do
    local value = channel.roles["v" .. index]
    if value and value.enabled and #roles < count then
      value = deep_copy(value)
      value.id = "v" .. index
      roles[#roles + 1] = value
    end
  end
  return roles
end

local function group_roles(group)
  local roles = {}
  for _, id in ipairs(harmony_config.member_roles(#group.members)) do
    local value = deep_copy(group.roles[id])
    value.id = id
    roles[#roles + 1] = value
  end
  return roles
end

local function solve(record, revision, frame, cache_key)
  frame.previous = record.consumed and deep_copy(record.consumed.role_pitches) or
    deep_copy(frame.entry_previous)
  local result = voicing.solve(frame)
  result.revision = revision
  result.cache_key = cache_key or revision
  record.next_generation=(record.next_generation or 0)+1
  result.generation=record.next_generation
  if result.status == "ok" then
    result.role_pitches = {}
    for index, role in ipairs(frame.roles) do result.role_pitches[role.id] = result.pitches[index] end
  end
  record.prepared = result
  return result
end

function harmony_state.prepare_revoice(song, channel_number, revision, material, channel, pins)
  local state = state_for(song)
  local record = state.channels[channel_number] or {consumed_count = 0}
  state.channels[channel_number] = record
  local cache_key=revision .. "|" .. fingerprint(channel) .. "|pins=" .. fingerprint(pins or {})
  if record.prepared and record.prepared.cache_key==cache_key then return record.prepared end
  return solve(record, revision, {
    policy_version = 1,
    mode = "revoice",
    material = material,
    roles = enabled_roles(channel, #material),
    preset = channel.preset,
    bass = deep_copy(channel.bass),
    crossing = channel.crossing,
    exact_unison = channel.exact_unison,
    common_tone_priority = channel.common_tone_priority,
    upper_spacing = channel.upper_spacing,
    bass_separation = channel.bass_separation,
    node_budget = channel.node_budget,
    pins = deep_copy(pins)
  }, cache_key)
end

function harmony_state.prepare_group(song, group_id, revision, material, group)
  local state = state_for(song)
  local record = state.groups[group_id] or {consumed_count = 0}
  state.groups[group_id] = record
  local cache_key = revision .. "|" .. fingerprint(group)
  if record.prepared and record.prepared.cache_key == cache_key then return record.prepared end
  local solve_material = deep_copy(material)
  local bass = deep_copy(group.bass)
  if bass.mode == "pedal" and bass.non_chord_pedal then
    local found = false
    for _, item in ipairs(solve_material) do
      if item.pc % 12 == bass.pedal % 12 then found=true; bass.tone_id=item.id; break end
    end
    if not found then
      solve_material[#solve_material + 1] = {id="non_chord_pedal",pc=bass.pedal % 12,required=false}
      bass.tone_id = "non_chord_pedal"
    end
  end
  return solve(record, revision, {
    policy_version = 1,
    mode = "ensemble",
    material = solve_material,
    roles = group_roles(group),
    preset = group.preset,
    bass = bass,
    crossing = group.crossing,
    exact_unison = group.exact_unison,
    common_tone_priority = group.common_tone_priority,
    doubling = group.pitch_class_doubling,
    upper_spacing = group.upper_spacing,
    bass_separation = group.bass_separation,
    node_budget = group.node_budget
  }, cache_key)
end

function harmony_state.prepare_pattern(song, channel_number, revision, material, roles, channel, entry_previous, has_bass)
  local state = state_for(song)
  local record = state.channels[channel_number] or {consumed_count = 0}
  state.channels[channel_number] = record
  local cache_key = revision .. "|" .. fingerprint(channel)
  if record.prepared and record.prepared.cache_key == cache_key then return record.prepared end
  return solve(record, revision, {
    policy_version = 1,
    mode = "ensemble",
    material = material,
    roles = roles,
    preset = channel.preset,
    crossing = channel.crossing,
    exact_unison = channel.exact_unison,
    common_tone_priority = channel.common_tone_priority,
    upper_spacing = channel.upper_spacing,
    bass_separation = channel.bass_separation,
    bass = has_bass and deep_copy(channel.bass) or nil,
    has_bass = has_bass == true,
    entry_previous = deep_copy(entry_previous),
    doubling = false,
    node_budget = channel.node_budget
  }, cache_key)
end

local function consume(record, result)
  if not record or not result or result.status ~= "ok" then return false end
  if record.prepared and result.generation ~= record.prepared.generation then return false end
  if record.consumed_key == result.cache_key then return false end
  if record.consumed_generation and (result.generation or 0)<record.consumed_generation then return false end
  record.consumed = deep_copy(result)
  record.consumed_revision = result.revision
  record.consumed_key = result.cache_key
  record.consumed_generation=result.generation or record.consumed_generation
  record.consumed_count = (record.consumed_count or 0) + 1
  return true
end

function harmony_state.consume_revoice(song, channel_number, result)
  return consume(state_for(song).channels[channel_number], result)
end

function harmony_state.consume_group(song, group_id, result)
  return consume(state_for(song).groups[group_id], result)
end

function harmony_state.snapshot(song)
  return deep_copy(state_for(song))
end

function harmony_state.reset_song(song)
  songs[song] = {groups = {}, channels = {}}
end

function harmony_state.enter_song(previous_song, next_song, same_slot)
  local previous = previous_song and state_for(previous_song) or {channels={},groups={}}
  local next_state = {channels={},groups={}}
  for channel_number=1,16 do
    local config = next_song.channels[channel_number].voicing
    local policy = same_slot and config and config.repeat_policy or config and config.transition
    if policy == "continue" and previous.channels[channel_number] then
      next_state.channels[channel_number] = deep_copy(previous.channels[channel_number])
    end
  end
  local next_groups = next_song.voicing and next_song.voicing.groups or {}
  for id,group in pairs(next_groups) do
    local policy = same_slot and group.repeat_policy or group.transition
    if policy == "continue" and previous.groups[id] then next_state.groups[id]=deep_copy(previous.groups[id]) end
  end
  songs[next_song] = next_state
end

function harmony_state.reset()
  for song in pairs(songs) do songs[song]=nil end
end

return harmony_state
