local config = {}

local modes = {off = true, revoice = true, pattern = true, ensemble = true}
local presets = {smooth = true, compact = true, independent = true}
local fallbacks = {silence = true, legacy = true}
local transitions = {anchor = true, continue = true}
local bass_modes = {root = true, inversion = true, smooth = true, pedal = true}
local directions = {nearest = true, ascending = true, descending = true}
local pattern_roles = {bass = true, inner1 = true, inner2 = true, inner3 = true, top = true}

local function integer(value, low, high)
  return type(value) == "number" and value == value and value % 1 == 0 and
    value >= low and value <= high
end

local function role(low, high, centre, leap)
  return {min = low, max = high, centre = centre, preferred_leap = leap,
    strict_leap = false, enabled = true}
end

local function member_roles(count)
  if count == 1 then return {"bass"} end
  if count == 2 then return {"bass", "top"} end
  if count == 3 then return {"bass", "inner1", "top"} end
  if count == 4 then return {"bass", "inner1", "inner2", "top"} end
  return {"bass", "inner1", "inner2", "inner3", "top"}
end

function config.new_channel(mode)
  return {
    schema_version = 1,
    mode = mode or "off",
    group_id = nil,
    preset = "smooth",
    preset_version = 1,
    fallback = "silence",
    absolute_pitch_policy = "pin",
    transition = "anchor",
    repeat_policy = "continue",
    crossing = mode == "pattern",
    exact_unison = false,
    common_tone_priority = true,
    upper_spacing = 12,
    bass_separation = 5,
    bass = {mode = "root", tone_id = "root", direction = "nearest",
      strict_direction = false, pedal = 48, non_chord_pedal = false},
    roles = {
      v1 = role(24, 60, 48, 12), v2 = role(36, 72, 55, 7),
      v3 = role(43, 79, 62, 7), v4 = role(48, 84, 67, 7),
      v5 = role(55, 96, 72, 7)
    },
    pattern_maps = {}
  }
end

function config.new_group(selected_channel)
  return {
    schema_version = 1,
    enabled = false,
    source = {kind = "global_effective"},
    template = {offsets = {0}, required = {true}},
    members = {{role = "bass", channel = selected_channel}},
    roles = {bass = role(36, 55, 43, 12)},
    bass = {mode = "root", tone_id = "tone1", direction = "nearest",
      strict_direction = false, pedal = 48, non_chord_pedal = false},
    crossing = false,
    pitch_class_doubling = true,
    exact_unison = false,
    common_tone_priority = true,
    upper_spacing = 12,
    bass_separation = 5,
    preset = "smooth",
    preset_version = 1,
    fallback = "silence",
    transition = "anchor",
    repeat_policy = "continue"
  }
end

function config.four_part_smooth(_, channels)
  local value = config.new_group(channels and channels[1])
  value.template = {offsets = {0, 2, 4}, required = {true, true, true}}
  value.members = {
    {role = "bass", channel = channels and channels[1]},
    {role = "inner1", channel = channels and channels[2]},
    {role = "inner2", channel = channels and channels[3]},
    {role = "top", channel = channels and channels[4]}
  }
  value.roles = {
    bass = role(36, 55, 43, 12), inner1 = role(48, 67, 55, 7),
    inner2 = role(55, 74, 62, 7), top = role(60, 81, 69, 7)
  }
  return value
end

local function validate_role(value, label)
  if type(value) ~= "table" or not integer(value.min, 0, 127) or
    not integer(value.max, 0, 127) or value.min > value.max or
    not integer(value.centre, value.min, value.max) or
    not integer(value.preferred_leap, 0, 127) or type(value.strict_leap) ~= "boolean" or
    type(value.enabled) ~= "boolean" then
    return nil, label .. " range"
  end
  return true
end

local function validate_group(id, group)
  local prefix = "group " .. id
  if type(group) ~= "table" or group.schema_version ~= 1 then
    return nil, prefix .. " schema version"
  end
  if type(group.enabled) ~= "boolean" then return nil, prefix .. " enabled" end
  if type(group.source) ~= "table" or
    (group.source.kind ~= "global_effective" and group.source.kind ~= "scale_slot") then
    return nil, prefix .. " source"
  end
  if group.source.kind == "scale_slot" and not integer(group.source.scale_slot, 1, 16) then
    return nil, prefix .. " source slot"
  end
  if type(group.template) ~= "table" or type(group.template.offsets) ~= "table" or
    type(group.template.required) ~= "table" or #group.template.offsets < 1 or
    #group.template.offsets > 5 or #group.template.required ~= #group.template.offsets then
    return nil, prefix .. " template"
  end
  local required = 0
  for index, offset in ipairs(group.template.offsets) do
    if not integer(offset, -14, 14) then return nil, prefix .. " template offset" end
    if type(group.template.required[index]) ~= "boolean" then return nil, prefix .. " required mask" end
    if group.template.required[index] then required = required + 1 end
  end
  if group.template.offsets[1] ~= 0 then return nil, prefix .. " root offset" end
  if required < 1 then return nil, prefix .. " required mask" end
  if type(group.members) ~= "table" or #group.members < 1 or #group.members > 5 then
    return nil, prefix .. " members"
  end
  if required > #group.members then return nil, prefix .. " coverage" end
  local expected, seen = member_roles(#group.members), {}
  for index, member in ipairs(group.members) do
    if type(member) ~= "table" or member.role ~= expected[index] then
      return nil, prefix .. " member role"
    end
    if not integer(member.channel, 1, 16) then return nil, prefix .. " member channel" end
    if seen[member.channel] then return nil, prefix .. " duplicate member" end
    seen[member.channel] = true
    local ok, reason = validate_role(group.roles and group.roles[member.role], prefix .. " " .. member.role)
    if not ok then return nil, reason end
  end
  if type(group.bass) ~= "table" or not bass_modes[group.bass.mode] or
    not directions[group.bass.direction] or type(group.bass.strict_direction) ~= "boolean" or
    not integer(group.bass.pedal, 0, 127) or type(group.bass.non_chord_pedal) ~= "boolean" then
    return nil, prefix .. " bass"
  end
  if group.bass.mode == "pedal" then
    local bass_role = group.roles and group.roles.bass
    if not bass_role or group.bass.pedal < bass_role.min or group.bass.pedal > bass_role.max then
      return nil, prefix .. " pedal range"
    end
  end
  if type(group.crossing) ~= "boolean" or type(group.pitch_class_doubling) ~= "boolean" or
    type(group.exact_unison) ~= "boolean" or type(group.common_tone_priority) ~= "boolean" or
    not integer(group.upper_spacing, 0, 127) or not integer(group.bass_separation, 0, 127) or
    not presets[group.preset] or group.preset_version ~= 1 or not fallbacks[group.fallback] or
    not transitions[group.transition] or not transitions[group.repeat_policy] then
    return nil, prefix .. " policy"
  end
  return true
end

local function validate_channel(number, channel, groups)
  local value = channel.voicing
  if value == nil then return true end
  local prefix = "channel " .. number
  if number == 17 then return nil, prefix .. " cannot use voicing" end
  if type(value) ~= "table" or value.schema_version ~= 1 then return nil, prefix .. " voicing version" end
  if not modes[value.mode] then return nil, prefix .. " voicing mode" end
  if not presets[value.preset] or value.preset_version ~= 1 or not fallbacks[value.fallback] or
    not transitions[value.transition] or not transitions[value.repeat_policy] or
    (value.absolute_pitch_policy ~= "pin" and value.absolute_pitch_policy ~= "allow_octave_move") or
    type(value.crossing) ~= "boolean" or type(value.exact_unison) ~= "boolean" or
    type(value.common_tone_priority) ~= "boolean" or not integer(value.upper_spacing,0,127) or
    not integer(value.bass_separation,0,127) then
    return nil, prefix .. " voicing policy"
  end
  if value.mode == "ensemble" then
    if not integer(value.group_id, 1, 16) or not groups[value.group_id] then
      return nil, prefix .. " missing group"
    end
    local found = false
    for _, member in ipairs(groups[value.group_id].members) do
      if member.channel == number then found = true break end
    end
    if not found then return nil, prefix .. " not a group member" end
  end
  if type(value.roles) ~= "table" then return nil, prefix .. " roles" end
  for index = 1, 5 do
    local ok, reason = validate_role(value.roles["v" .. index], prefix .. " v" .. index)
    if not ok then return nil, reason end
  end
  if type(value.bass) ~= "table" or not bass_modes[value.bass.mode] or
    not directions[value.bass.direction] or type(value.bass.strict_direction) ~= "boolean" or
    not integer(value.bass.pedal, 0, 127) or value.bass.non_chord_pedal ~= false then
    return nil, prefix .. " bass"
  end
  if value.bass.mode == "pedal" then
    local bass_role = value.roles.v1
    if value.bass.pedal < bass_role.min or value.bass.pedal > bass_role.max then
      return nil, prefix .. " pedal range"
    end
  end
  if type(value.pattern_maps) ~= "table" then return nil, prefix .. " pattern maps" end
  for binding, map in pairs(value.pattern_maps) do
    if type(binding) ~= "string" or type(map) ~= "table" or map.schema_version ~= 1 or
      type(map.assignments) ~= "table" then
      return nil, prefix .. " pattern map"
    end
    for source, assigned_role in pairs(map.assignments) do
      local number_value = tonumber(source)
      if not integer(number_value, -7, 13) then return nil, prefix .. " pattern map value" end
      if not pattern_roles[assigned_role] then return nil, prefix .. " pattern map role" end
    end
  end
  return true
end

function config.validate_song(song)
  if type(song) ~= "table" then return nil, "song" end
  local groups = {}
  if song.voicing ~= nil then
    if type(song.voicing) ~= "table" or song.voicing.schema_version ~= 1 then
      return nil, "voicing schema version"
    end
    if type(song.voicing.groups) ~= "table" then return nil, "voicing groups" end
    for id, group in pairs(song.voicing.groups) do
      if not integer(id, 1, 16) then return nil, "group id" end
      local ok, reason = validate_group(id, group)
      if not ok then return nil, reason end
      groups[id] = group
    end
    local claims = {}
    for id, group in pairs(groups) do
      if group.enabled then
        for _, member in ipairs(group.members) do
          if claims[member.channel] then
            return nil, "channel " .. member.channel .. " belongs to multiple groups"
          end
          claims[member.channel] = id
        end
      end
    end
  end
  if type(song.channels) ~= "table" then return nil, "channels" end
  for number = 1, 17 do
    local channel = song.channels[number]
    if type(channel) ~= "table" then return nil, "channel " .. number .. " missing" end
    local ok, reason = validate_channel(number, channel, groups)
    if not ok then return nil, reason end
  end
  return true
end

config.member_roles = member_roles

return config
