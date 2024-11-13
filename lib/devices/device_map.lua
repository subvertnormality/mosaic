local device_map = {}
device_map.params_cache = {}

local json = require("mosaic/lib/helpers/json")
local nb_device_param_maps = include("mosaic/lib/devices/nb_device_param_maps")

local device_map_keyed_by_id = {}

local function read_json_file(file_path)
  local file, err = io.open(file_path, "r")
  if not file then
      print("Error opening file:", err)
      error("Cannot open file: " .. file_path)
  else
      local content = file:read("*a")
      file:close()
      if content == "" then
          print("Warning: File is empty -", file_path)
          return nil
      else
          if pcall(json.decode, content) then
            print("Device config loaded successfully: ", file_path)
            return json.decode(content)
          else
            print("Error: JSON is invalid:", file_path)
            return nil
          end
      end
  end
end

local function list_json_files_in_directory(directory)
    local i, t, popen = 0, {}, io.popen
    for filename in popen('ls "'..directory..'"'):lines() do
        if filename:match("%.json$") then -- Filters only JSON files
            table.insert(t, directory .. '/' .. filename)
        end
    end
    return t
end

local function combine_json_files_into_table(directory)
    local devices = {}
    local files = list_json_files_in_directory(directory)
    for _, file_path in ipairs(files) do
        local table_from_file = read_json_file(file_path)
        if table_from_file then
          table.insert(devices, table_from_file[1])
        end
    end
    return devices
end


local function create_cc_device()
  local cc_midi_device = {}

  for i = 1, 127 do
    table.insert(
      cc_midi_device,
      {
        ["id"] = "cc_" .. i,
        ["param_id"] = "cc_" .. i,
        ["name"] = "CC " .. i,
        ["cc_msb"] = i,
        ["cc_lsb"] = nil,
        ["off_value"] = -1,
        ["cc_min_value"] = -1,
        ["cc_max_value"] = 127,
        ["nrpn_msb"] = nil,
        ["nrpn_lsb"] = nil,
        ["nrpn_min_value"] = nil,
        ["nrpn_max_value"] = nil,
        ["short_descriptor_1"] = "CC"..i,
        ["short_descriptor_2"] = ""
      }
    )
  end

  return {
    ["type"] = "midi",
    ["name"] = "CC Device",
    ["id"] = "cc_device",
    ["map_params_automatically"] = false,
    ["default_midi_channel"] = nil,
    ["params"] = cc_midi_device
  }
end

local function get_none_param()
  return {
    ["id"] = "none",
    ["param_id"] = "none",
    ["name"] = "None",
    ["short_descriptor_1"] = "None",
    ["short_descriptor_2"] = ""
  }
end

local function get_none_device()
  return {
    ["type"] = "none",
    ["name"] = "None",
    ["id"] = "none",
    ["map_params_automatically"] = false,
    ["default_midi_channel"] = nil,
    ["params"] = {}
  }
end

local devices

local note_division_labels = include("mosaic/lib/clock/divisions").note_division_labels

local stock_params = {
  get_none_param(),
  {
    ["id"] = "fixed_note",
    ["name"] = "Fixed Note",
    ["short_descriptor_1"] = "FIXD",
    ["short_descriptor_2"] = "NOTE",
    ["off_value"] = -1,
    ["cc_min_value"] = -1,
    ["cc_max_value"] = 127,
    ["param_type"] = "stock",
    ["ui_labels"] = {
      "X", "C0", "C#0", "D0", "D#0", "E0", "F0", "F#0", "G0", "G#0", "A0", "A#0", "B0",
      "C1", "C#1", "D1", "D#1", "E1", "F1", "F#1", "G1", "G#1", "A1", "A#1", "B1",
      "C2", "C#2", "D2", "D#2", "E2", "F2", "F#2", "G2", "G#2", "A2", "A#2", "B2",
      "C3", "C#3", "D3", "D#3", "E3", "F3", "F#3", "G3", "G#3", "A3", "A#3", "B3",
      "C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4",
      "C5", "C#5", "D5", "D#5", "E5", "F5", "F#5", "G5", "G#5", "A5", "A#5", "B5",
      "C6", "C#6", "D6", "D#6", "E6", "F6", "F#6", "G6", "G#6", "A6", "A#6", "B6",
      "C7", "C#7", "D7", "D#7", "E7", "F7", "F#7", "G7", "G#7", "A7", "A#7", "B7",
      "C8", "C#8", "D8", "D#8", "E8", "F8", "F#8", "G8", "G#8", "A8", "A#8", "B8",
      "C9", "C#9", "D9", "D#9", "E9", "F9", "F#9", "G9", "G#9", "A9", "A#9", "B9",
      "C10", "C#10", "D10", "D#10", "E10", "F10", "F#10", "G10"
    }
  },
  {
    ["id"] = "quantised_fixed_note",
    ["name"] = "Quantised Fixed Note",
    ["short_descriptor_1"] = "QUAN",
    ["short_descriptor_2"] = "NOTE",
    ["off_value"] = -1,
    ["cc_min_value"] = -1,
    ["cc_max_value"] = 127,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "bipolar_random_note",
    ["name"] = "Random Note",
    ["short_descriptor_1"] = "RAND",
    ["short_descriptor_2"] = "NOTE",
    ["off_value"] = 0,
    ["cc_min_value"] = 0,
    ["cc_max_value"] = 200,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "random_velocity",
    ["name"] = "Random Velocity",
    ["short_descriptor_1"] = "RAND",
    ["short_descriptor_2"] = "VELO",
    ["off_value"] = 0,
    ["cc_min_value"] = 0,
    ["cc_max_value"] = 254,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "trig_probability",
    ["name"] = "Trig Probability",
    ["short_descriptor_1"] = "TRIG",
    ["short_descriptor_2"] = "PROB",
    ["off_value"] = -1,
    ["cc_min_value"] = -1,
    ["cc_max_value"] = 100,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "twos_random_note",
    ["name"] = "Twos Random Note",
    ["short_descriptor_1"] = "2RND",
    ["short_descriptor_2"] = "NOTE",
    ["off_value"] = 0,
    ["cc_min_value"] = 0,
    ["cc_max_value"] = 200,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "chord_strum",
    ["name"] = "Chord Note Strum",
    ["short_descriptor_1"] = "CHRD",
    ["short_descriptor_2"] = "STRM",
    ["off_value"] = 0,
    ["cc_min_value"] = 0,
    ["cc_max_value"] = 92,
    ["ui_labels"] = note_division_labels,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "chord_arp",
    ["name"] = "Chord Note Arpeggio",
    ["short_descriptor_1"] = "CHRD",
    ["short_descriptor_2"] = "ARP",
    ["off_value"] = 0,
    ["cc_min_value"] = 0,
    ["cc_max_value"] = 92,
    ["ui_labels"] = note_division_labels,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "chord_spread",
    ["name"] = "Chord Spread",
    ["short_descriptor_1"] = "CHRD",
    ["short_descriptor_2"] = "SPRD",
    ["off_value"] = 0,
    ["cc_min_value"] = 0,
    ["cc_max_value"] = 92,
    ["ui_labels"] = note_division_labels,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "chord_acceleration",
    ["name"] = "Chord Accel Mod",
    ["short_descriptor_1"] = "CHRD",
    ["short_descriptor_2"] = "ACCL",
    ["off_value"] = 0,
    ["cc_min_value"] = -5,
    ["cc_max_value"] = 5,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "chord_velocity_modifier",
    ["name"] = "Chord Velocity Mod",
    ["short_descriptor_1"] = "CHRD",
    ["short_descriptor_2"] = "VEL",
    ["off_value"] = 0,
    ["cc_min_value"] = -40,
    ["cc_max_value"] = 40,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "chord_strum_pattern",
    ["name"] = "Chord Pattern",
    ["short_descriptor_1"] = "CHRD",
    ["short_descriptor_2"] = "PTRN",
    ["off_value"] = 0,
    ["cc_min_value"] = 0,
    ["cc_max_value"] = 4,
    ["ui_labels"] = {
      "X",
      "->",
      "<-",
      "-><-",
      "<-->"
    },
    ["param_type"] = "stock"
  }
}


-- These are tested NB note players that do not break Mosaic
local tested_note_players = {
  "ansible 4",
  "emplait 3",
  "emplait 2",
  "emplait 4",
  "ansible 3",
  "jf kit",
  "jf n 1",
  "emplait 1",
  "jf n 2",
  "jf poly",
  "jf unison",
  "jf n 5",
  "jf mpe",
  "crow 1/2",
  "crow 3/4",
  "jf n 4",
  "jf n 3",
  "jf n 6",
  "ansible 1",
  "ansible 2",
  "crow para",
  "drumcrow 1",
  "drumcrow 2",
  "drumcrow 3",
  "drumcrow 4",
  "rudiments 1",
  "rudiments 2",
  "rudiments 3",
  "rudiments 4",
  "polyperc 1",
  "doubledecker",
  "Oilcan 1",
  "Oilcan 2",
  "Oilcan 3",
  "Oilcan 4"
}

local function merge_devices()

  local stock_device_map = {}
 
  local directory = norns.state.data .. "config"
  local stock_device_map = combine_json_files_into_table(directory)

  table.insert(stock_device_map, create_cc_device())
  table.insert(stock_device_map, get_none_device())

  if (note_players) then
    for index, device in pairs(note_players) do

      if fn.appears_in_table(tested_note_players, index) and string.find(index, "midi", 1, true) ~= 1 then
        local new_device_params = {}

        table.insert(
          stock_device_map,
          {
            ["type"] = "norns",
            ["name"] = fn.title_case(index),
            ["id"] = index,
            ["unique"] = true,
            ["map_params_automatically"] = nb_device_param_maps.get_default_params_for_device(index),
            ["default_midi_channel"] = nil,
            ["player"] = device,
            ["params"] = new_device_params,
            ["supports_slew"] = device.describe().supports_slew
          }
        )

        local device_param_names = device.describe().params or nb_device_param_maps.get_params_for_device(index)

        if type(device_param_names) == "table" and next(device_param_names) then

          for i = 1, #device_param_names do

            local param_id = params.lookup[device_param_names[i]]
            local p = params:lookup_param(param_id)

            params:show(param_id)


            local quantum = 0.01
            local s = 0
            local minval = params:get_range(param_id)[1]
            local maxval = params:get_range(param_id)[2]
            local warp = "lin"

            if p["controlspec"] then
              quantum = p["controlspec"].quantum or 0.01
              quantum = p["controlspec"].step or 0
              warp = p["controlspec"].warp or "lin"
            end
            if p.min then
              minval = p.min
            end
            if p.max then
              maxval = p.max
            end

            table.insert(
              new_device_params,
              {
                ["id"] = device_param_names[i],
                ["param_id"] = param_id,
                ["name"] = fn.title_case(p.name),
                ["unique"] = true,
                ["short_descriptor_1"] = fn.format_first_descriptor(p.name),
                ["short_descriptor_2"] = fn.format_last_descriptor(p.name),
                ["cc_min_value"] = minval,
                ["cc_max_value"] = maxval,
                ["quantum"] = quantum,
                ["step"] = s,
                ["default"] = p["controlspec"] and p["controlspec"].default or 0
              }
            )

          end
        end

        if device.describe().supports_slew then
          table.insert(
            new_device_params,
            {
              ["id"] = "nb_slew",
              ["name"] = "Slew",
              ["short_descriptor_1"] = "SLEW",
              ["short_descriptor_2"] = "",
              ["off_value"] = -1,
              ["cc_min_value"] = -1,
              ["cc_max_value"] = 60,
              ["quantum"] = 1,
              ["default"] = -1
            }
          )
        end
      else
        print("Skipping untested device: ", index)
      end
    end
  end

  -- Update the 'value' field for all devices
  for index, device in ipairs(stock_device_map) do
    device["value"] = index
  end

  table.sort(stock_device_map, function(a, b) 
    if a.name:lower() == "none" then
      return true 
    elseif b.name:lower() == "none" then
      return false
    else
      return a.name:lower() < b.name:lower()  -- standard alphabetical comparison
    end
  end)

  return stock_device_map
end

local function merge_params(device_params, stock_params)
  local merged_params = {}
  local seen_ids = {}
  local insert_index = 1

  -- Cache get_none_param() result
  local none_param = get_none_param()

  -- Check if 'none' param should be added
  if not (stock_params[1] and stock_params[1].id == "none") then
    merged_params[insert_index] = none_param
    seen_ids[none_param.id] = true
    insert_index = insert_index + 1
  end

  -- Function to copy all necessary fields
  local function copy_param_fields(source_param)
    local new_param = {}
    for key, value in pairs(source_param) do
      new_param[key] = value
    end
    new_param.index = insert_index
    return new_param
  end

  -- Merge stock_params
  for i = 1, #stock_params do
    local sp = stock_params[i]
    local sp_id = sp.id
    if not seen_ids[sp_id] then
      local new_param = copy_param_fields(sp)
      merged_params[insert_index] = new_param
      seen_ids[sp_id] = true
      insert_index = insert_index + 1
    end
  end

  -- Merge device_params
  for i = 1, #device_params do
    local dp = device_params[i]
    local dp_id = dp.id
    if not seen_ids[dp_id] then
      local new_param = copy_param_fields(dp)
      merged_params[insert_index] = new_param
      seen_ids[dp_id] = true
      insert_index = insert_index + 1
    end
  end

  return merged_params
end

function device_map.get_devices()
  return devices
end

function device_map.get_device_by_name(name)
  for _, device in ipairs(devices) do
    if device.name == name then
      return device
    end
  end
  return nil
end

function device_map.get_device(id)
  return device_map_keyed_by_id[id]
end

function device_map.get_available_devices_for_channel(c)
  -- Build a set of device IDs that are currently used by other channels
  local active_devices_set = {}
  local prog = program.get()
  local prog_devices = prog.devices

  for i = 1, 16 do
    if i ~= c then
      local device_map_id = prog_devices[i].device_map
      if device_map_id ~= "none" then
        active_devices_set[device_map_id] = true
      end
    end
  end

  -- Build a list of available devices
  local available_devices = {}
  for _, device in ipairs(devices) do
    local device_id = device.id
    if not (device.unique and active_devices_set[device_id]) then
      table.insert(available_devices, device)
    end
  end

  return available_devices
end

function device_map.get_params(device_id)
  -- Check if the merged parameters for this device_id are cached
  if device_map.params_cache[device_id] then
    return device_map.params_cache[device_id]
  end

  -- Retrieve the device and its parameters
  local device = fn.get_by_id(devices, device_id)
  local device_params = device and device.params or {}

  -- Call merge_params and cache the result
  local merged_params = merge_params(device_params, stock_params)
  device_map.params_cache[device_id] = merged_params

  return merged_params
end

function device_map.invalidate_params_cache(device_id)
  device_map.params_cache[device_id] = nil
end

function device_map.invalidate_all_params_cache()
  device_map.params_cache = {}
end

function device_map.get_available_params_for_channel(c, selected_param)
  local channel = program.get_channel(c)
  local active_params = {}
  local params_copy = fn.deep_copy(device_map.get_params(program.get().devices[channel.number].device_map))

  -- Populating active_params with ids from channels 1 through 10
  for i = 1, 10 do
    if selected_param ~= i and channel.trig_lock_params[i].id ~= "none" then
      table.insert(active_params, channel.trig_lock_params[i].id)
    end
  end

  -- Convert active_params into a set for O(1) lookups
  local active_params_set = {}
  for _, param_id in ipairs(active_params) do
    active_params_set[param_id] = true
  end

  -- Filtering params_copy to remove any table whose id is present in active_params_set
  local filtered_params = {}
  for _, inner_table in ipairs(params_copy) do
    if not active_params_set[inner_table.id] then
      table.insert(filtered_params, inner_table)
    end
  end

  return filtered_params
end

function device_map.validate_devices()

  for i = 1, 16 do
    local device = device_map.get_device(program.get().devices[i].device_map)

    if device == nil then
      program.get().devices[i] = {midi_channel = 1, midi_device = 1, device_map = "none"}
    end

  end
end

function device_map.get_stock_params()
  return stock_params
end

local function create_device_map_keyed_by_id(devices)
  local device_map_keyed_by_id = {}
  for _, device in ipairs(devices) do
    device_map_keyed_by_id[device.id] = device
  end
  return device_map_keyed_by_id
end

function device_map.init()
  devices = merge_devices()
  device_map_keyed_by_id = create_device_map_keyed_by_id(devices)
end

return device_map
