local voicing = include("mosaic/lib/harmony/voicing")
local harmony_config = include("mosaic/lib/harmony/config")

local harmony_state = {}
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

local function solve(record, revision, frame)
  frame.previous = record.consumed and deep_copy(record.consumed.role_pitches) or nil
  local result = voicing.solve(frame)
  result.revision = revision
  if result.status == "ok" then
    result.role_pitches = {}
    for index, role in ipairs(frame.roles) do result.role_pitches[role.id] = result.pitches[index] end
  end
  record.prepared = result
  return result
end

function harmony_state.prepare_revoice(song, channel_number, revision, material, channel)
  local state = state_for(song)
  local record = state.channels[channel_number] or {consumed_count = 0}
  state.channels[channel_number] = record
  return solve(record, revision, {
    policy_version = 1,
    mode = "revoice",
    material = material,
    roles = enabled_roles(channel, #material),
    preset = channel.preset,
    crossing = channel.crossing,
    exact_unison = channel.exact_unison,
    node_budget = channel.node_budget
  })
end

function harmony_state.prepare_group(song, group_id, revision, material, group)
  local state = state_for(song)
  local record = state.groups[group_id] or {consumed_count = 0}
  state.groups[group_id] = record
  if record.prepared and record.prepared.revision == revision then return record.prepared end
  return solve(record, revision, {
    policy_version = 1,
    mode = "ensemble",
    material = material,
    roles = group_roles(group),
    preset = group.preset,
    bass = deep_copy(group.bass),
    crossing = group.crossing,
    exact_unison = group.exact_unison,
    doubling = group.pitch_class_doubling,
    upper_spacing = group.upper_spacing,
    bass_separation = group.bass_separation,
    node_budget = group.node_budget
  })
end

function harmony_state.prepare_pattern(song, channel_number, revision, material, roles, channel)
  local state = state_for(song)
  local record = state.channels[channel_number] or {consumed_count = 0}
  state.channels[channel_number] = record
  if record.prepared and record.prepared.revision == revision then return record.prepared end
  return solve(record, revision, {
    policy_version = 1,
    mode = "ensemble",
    material = material,
    roles = roles,
    preset = channel.preset,
    crossing = channel.crossing,
    exact_unison = channel.exact_unison,
    doubling = false,
    node_budget = channel.node_budget
  })
end

local function consume(record, result)
  if not record or not result or result.status ~= "ok" then return false end
  if record.consumed_revision == result.revision then return false end
  record.consumed = deep_copy(result)
  record.consumed_revision = result.revision
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

function harmony_state.reset()
  songs = setmetatable({}, {__mode = "k"})
end

return harmony_state
