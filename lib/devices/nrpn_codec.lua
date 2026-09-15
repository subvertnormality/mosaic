-- Numeric NRPN transport policy. Receiver scaling belongs in device maps.
local codec = {}

function codec.resolve(override, parameter, device)
  local mode = override
  if mode == nil and parameter then mode = parameter.nrpn_lsb_mode end
  if mode == nil and device then mode = device.nrpn_lsb_mode end
  if mode == nil then mode = "standard" end
  assert(mode == "standard" or mode == "legacy-half", "Unknown NRPN LSB mode: "..tostring(mode))
  return mode
end

function codec.encode(value, mode)
  mode = codec.resolve(mode)
  assert(type(value) == "number" and value >= 0 and value <= 16383 and value % 1 == 0,
    "NRPN value must be an integer from 0 to 16383")
  local msb, lsb = math.floor(value / 128), value % 128
  if mode == "legacy-half" then
    -- Historical Mosaic divided ONLY the low byte by two. The pinned norns
    -- Lua5.3 serializer converts fractional numbers to zero, not to floor.
    -- Preserve those historical bytes explicitly; this is not numeric scaling
    -- or a claim about any physical receiver's response.
    lsb = lsb % 2 == 0 and lsb / 2 or 0
  end
  return msb, lsb
end

-- Persist the mode independently of a lock slot: unassigned stored controls
-- are also recalled on Play. Device/parameter identity prevents switch leakage.
function codec.stored_mode(data, channel, parameter, device)
  local by_channel = data.nrpn_stored_modes and data.nrpn_stored_modes[channel]
  local by_device = by_channel and device and by_channel[device.id]
  local override = by_device and by_device[parameter.id]
  if override == nil and by_device then override = by_device["*"] end
  return codec.resolve(override, parameter, device)
end

function codec.migrate(data, get_device)
  if data.nrpn_policy_version ~= nil then
    assert(data.nrpn_policy_version == 1, "Unsupported NRPN policy version")
    return data
  end
  -- Include serialized undo/redo and copied song/channel state. Visit each table
  -- once because in-memory snapshots can share tables or contain cycles.
  local seen = {}
  local function migrate_assignments(value)
    if type(value) ~= "table" or seen[value] then return end
    seen[value] = true
    if value.nrpn_msb ~= nil and value.nrpn_lsb ~= nil then
      if value.nrpn_lsb_mode == nil then value.nrpn_lsb_mode = "legacy-half" end
      codec.resolve(value.nrpn_lsb_mode)
    end
    for _,child in pairs(value) do migrate_assignments(child) end
  end
  migrate_assignments(data)
  data.nrpn_stored_modes = data.nrpn_stored_modes or {}
  for channel,route in pairs(data.devices or {}) do
    local device = get_device and get_device(route.device_map)
    if device and device.type == "midi" then
      local channel_modes = data.nrpn_stored_modes[channel] or {}
      data.nrpn_stored_modes[channel] = channel_modes
      local modes = channel_modes[device.id] or {}
      channel_modes[device.id] = modes
      for _,parameter in ipairs(device.params or {}) do
        if parameter.nrpn_msb ~= nil and parameter.nrpn_lsb ~= nil then
          if modes[parameter.id] == nil then modes[parameter.id] = "legacy-half" end
          codec.resolve(modes[parameter.id])
        end
      end
    elseif not device and route.device_map and route.device_map ~= "none" then
      -- A temporarily missing map cannot enumerate historical stored controls.
      -- Keep a device-scoped history fallback, never a generic receiver rule.
      local channel_modes = data.nrpn_stored_modes[channel] or {}
      data.nrpn_stored_modes[channel] = channel_modes
      local modes = channel_modes[route.device_map] or {}
      channel_modes[route.device_map] = modes
      if modes["*"] == nil then modes["*"] = "legacy-half" end
      codec.resolve(modes["*"])
    end
  end
  data.nrpn_policy_version = 1
  return data
end

-- Explicit whole-project conversion changes metadata only. The CLI writes a
-- new project/PSET pair; it never replaces the input project.
function codec.convert(data, mode)
  assert(mode ~= nil, "An explicit NRPN mode is required")
  mode = codec.resolve(mode)
  assert(data.nrpn_policy_version == nil or data.nrpn_policy_version == 1,
    "Unsupported NRPN policy version")
  local seen = {}
  local function convert_assignments(value)
    if type(value) ~= "table" or seen[value] then return end
    seen[value] = true
    if value.nrpn_msb ~= nil and value.nrpn_lsb ~= nil then value.nrpn_lsb_mode = mode end
    for _,child in pairs(value) do convert_assignments(child) end
  end
  convert_assignments(data)
  data.nrpn_stored_modes = data.nrpn_stored_modes or {}
  for _,devices in pairs(data.nrpn_stored_modes) do
    for id in pairs(devices) do devices[id] = {["*"]=mode} end
  end
  for channel,route in pairs(data.devices or {}) do
    if route.device_map and route.device_map ~= "none" then
      local devices = data.nrpn_stored_modes[channel] or {}
      data.nrpn_stored_modes[channel] = devices
      devices[route.device_map] = {["*"]=mode}
    end
  end
  data.nrpn_policy_version = 1
  return data
end

return codec
