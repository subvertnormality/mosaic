local descriptors = {}
local json = require("mosaic/lib/helpers/json")
local nb_device_param_maps = include("mosaic/lib/devices/nb_device_param_maps")
local function get_none_param()
  return {id = "none", param_id = "none", name = "None", short_descriptor_1 = "None", short_descriptor_2 = ""}
end

local tested_note_players = {"ansible 4","emplait 3","emplait 2","emplait 4","ansible 3","jf kit","jf n 1","emplait 1","jf n 2","jf poly","jf unison","jf n 5","jf mpe","crow 1/2","crow 3/4","jf n 4","jf n 3","jf n 6","ansible 1","ansible 2","crow para","drumcrow 1","drumcrow 2","drumcrow 3","drumcrow 4","rudiments 1","rudiments 2","rudiments 3","rudiments 4","polyperc 1","doubledecker","Oilcan 1","Oilcan 2","Oilcan 3","Oilcan 4"}

local function read_json_file(path)
  local file, err = io.open(path, "r")
  if not file then print("Error opening file:", err); return nil end
  local content = file:read("*a")
  file:close()
  if content == "" then print("Warning: File is empty -", path); return nil end
  if pcall(json.decode, content) then
    print("Device config loaded successfully: ", path)
    return json.decode(content)
  end
  print("Error: JSON is invalid:", path)
end

local function load_config_devices(directory)
  local devices = {}
  for filename in io.popen('ls "' .. directory .. '"'):lines() do
    if filename:match("%.json$") then
      local path = directory .. "/" .. filename
      local config = read_json_file(path)
      if config then
        local device = config[1]
        if type(device) == "table" and type(device.id) == "string" and type(device.name) == "string" then
          table.insert(devices, device)
        else
          print("Error: device config needs a string id and name:", path)
        end
      end
    end
  end
  return devices
end

local function create_cc_device()
  local params = {}
  for i = 1, 127 do
    table.insert(params, {id = "cc_" .. i, param_id = "cc_" .. i, name = "CC " .. i, cc_msb = i, cc_lsb = nil, off_value = -1, cc_min_value = -1, cc_max_value = 127, nrpn_msb = nil, nrpn_lsb = nil, nrpn_min_value = nil, nrpn_max_value = nil, short_descriptor_1 = "CC" .. i, short_descriptor_2 = ""})
  end
  return {type = "midi", name = "CC Device", id = "cc_device", map_params_automatically = false, default_midi_channel = nil, params = params}
end

local function append_note_players(devices)
  if not note_players then return end
  for index, device in pairs(note_players) do
    if fn.appears_in_table(tested_note_players, index) and string.find(index, "midi", 1, true) ~= 1 then
      local device_params = {}
      table.insert(devices, {type = "norns", name = fn.title_case(index), id = index, unique = true, map_params_automatically = nb_device_param_maps.get_default_params_for_device(index), default_midi_channel = nil, player = device, params = device_params, supports_slew = device.describe().supports_slew})
      local names = device.describe().params or nb_device_param_maps.get_params_for_device(index)
      if type(names) == "table" and next(names) then
        for i = 1, #names do
          local param_id = params.lookup[names[i]]
          local p = params:lookup_param(param_id)
          params:show(param_id)
          local quantum, step = 0.01, 0
          local minval, maxval = params:get_range(param_id)[1], params:get_range(param_id)[2]
          if p.controlspec then quantum = p.controlspec.quantum or 0.01; quantum = p.controlspec.step or 0 end
          if p.min then minval = p.min end
          if p.max then maxval = p.max end
          table.insert(device_params, {id = names[i], param_id = param_id, name = fn.title_case(p.name), unique = true, short_descriptor_1 = fn.format_first_descriptor(p.name), short_descriptor_2 = fn.format_last_descriptor(p.name), cc_min_value = minval, cc_max_value = maxval, quantum = quantum, step = step, default = p.controlspec and p.controlspec.default or 0})
        end
      end
      if device.describe().supports_slew then table.insert(device_params, {id = "nb_slew", name = "Slew", short_descriptor_1 = "SLEW", short_descriptor_2 = "", off_value = -1, cc_min_value = -1, cc_max_value = 60, quantum = 1, default = -1}) end
    else
      print("Skipping untested device: ", index)
    end
  end
end

function descriptors.get_none_param()
  return get_none_param()
end

function descriptors.load_devices(directory)
  local devices = load_config_devices(directory)
  table.insert(devices, create_cc_device())
  table.insert(devices, {type = "none", name = "None", id = "none", map_params_automatically = false, default_midi_channel = nil, params = {}})
  append_note_players(devices)
  for index, device in ipairs(devices) do device.value = index end
  table.sort(devices, function(a, b)
    if a.name:lower() == "none" then return true elseif b.name:lower() == "none" then return false else return a.name:lower() < b.name:lower() end
  end)
  return devices
end

function descriptors.merge_params(device_params, stock_params, none_param)
  local merged, seen, index = {}, {}, 1
  if not (stock_params[1] and stock_params[1].id == "none") then merged[index] = none_param; seen[none_param.id] = true; index = index + 1 end
  for _, source_params in ipairs({stock_params, device_params}) do
    for i = 1, #source_params do
      local source = source_params[i]
      if not seen[source.id] then
        local copy = {}
        for key, value in pairs(source) do copy[key] = value end
        copy.index = index
        merged[index], seen[source.id], index = copy, true, index + 1
      end
    end
  end
  return merged
end

return descriptors

