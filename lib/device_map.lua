local device_map = {}

local fn = include("mosaic/lib/functions")
local json = require("mosaic/lib/json")

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
        ["short_descriptor_1"] = "CC",
        ["short_descriptor_2"] = i
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

local clock_divisions_ui_labels = {
  "x16",
  "x12",
  "x8",
  "x6",
  "x5.3",
  "x5",
  "x4",
  "x3",
  "x2.6",
  "x2",
  "x1.5",
  "x1.3",
  "/1",
  "/1.5",
  "/2",
  "/2.6",
  "/3",
  "/4",
  "/5",
  "/5.3",
  "/6",
  "/7",
  "/8",
  "/9",
  "/10", 
  "/11", 
  "/12", 
  "/13", 
  "/14", 
  "/15", 
  "/16", 
  "/17", 
  "/19", 
  "/21", 
  "/23", 
  "/24", 
  "/25", 
  "/27", 
  "/29", 
  "/32", 
  "/40", 
  "/48", 
  "/56", 
  "/64", 
  "/96", 
  "/101",
  "/128",
  "/192",
  "/256",
  "/384",
  "/512" 
}

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
    ["param_type"] = "stock"
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
    ["off_value"] = -1,
    ["cc_min_value"] = -1,
    ["cc_max_value"] = 200,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "random_velocity",
    ["name"] = "Random Velocity",
    ["short_descriptor_1"] = "RAND",
    ["short_descriptor_2"] = "VELO",
    ["off_value"] = -1,
    ["cc_min_value"] = -1,
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
    ["off_value"] = -1,
    ["cc_min_value"] = -1,
    ["cc_max_value"] = 200,
    ["param_type"] = "stock"
  },
  {
    ["id"] = "chord_strum",
    ["name"] = "Chord Note Strum",
    ["short_descriptor_1"] = "CHRD",
    ["short_descriptor_2"] = "STRM",
    ["off_value"] = 13,
    ["cc_min_value"] = 1,
    ["cc_max_value"] = 51,
    ["ui_labels"] = clock_divisions_ui_labels,
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
    ["name"] = "Chord Strum Pattern",
    ["short_descriptor_1"] = "CHRD",
    ["short_descriptor_2"] = "PTRN",
    ["off_value"] = 0,
    ["cc_min_value"] = 0,
    ["cc_max_value"] = 4,
    ["ui_labels"] = {
      "off",
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
}

local function merge_devices()

  local stock_device_map = {}
 
  local directory = norns.state.data .. "config"
  local stock_device_map = combine_json_files_into_table(directory)



  for _, device in pairs(stock_device_map) do
    local has_none_id = false


    for _, param in pairs(device.params) do
        if param.id == "none" then
          has_none_id = true
            break -- Stop checking more params if we found a param with id "none"
        end
    end

    -- Perform an action if no param with id "none" was found
    if not has_none_id then
      table.insert(device.params, 1, get_none_param())
    end
  end

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
            ["map_params_automatically"] = false,
            ["default_midi_channel"] = nil,
            ["player"] = device,
            ["params"] = new_device_params
          }
        )

        if device.describe().params then
          local device_param_names = device.describe().params
          for i = 1, #device_param_names do
            local param_id = params.lookup[device_param_names[i]]
            local p = params:lookup_param(param_id)

            params:show(param_id)

            local minval = 0
            local maxval = 127
            local quantum = 1

            if p.count then
              minval = 1
              maxval = p.count
            elseif p["controlspec"] then
              quantum = p["controlspec"].quantum or 1
              minval = params:get_range(param_id)[1]
              maxval = params:get_range(param_id)[2]
            end

            local quantum_modifier = 1 / quantum

            table.insert(
              new_device_params,
              {
                ["id"] = device_param_names[i],
                ["name"] = fn.title_case(p.name),
                ["short_descriptor_1"] = fn.format_first_descriptor(p.name),
                ["short_descriptor_2"] = fn.format_second_descriptor(p.name),
                ["cc_min_value"] = minval * quantum_modifier,
                ["cc_max_value"] = maxval * quantum_modifier,
                ["quantum_modifier"] = quantum_modifier,
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
              ["quantum_modifier"] = 60,
              ["default"] = -1
            }
          )
        end
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
  local seen_ids = {} -- hash set for fast id lookup

  if (merged_params[1] and merged_params[1].id ~= "none") then
    table.insert(merged_params, get_none_param())

    seen_ids[get_none_param().id] = true
  end

  -- Copy the contents of stock_params into merged_params
  for index, sp in ipairs(stock_params) do
    if not seen_ids[sp.id] then
      sp.index = index
      table.insert(merged_params, sp)
      seen_ids[sp.id] = true
      param_index = index + 1
    end
  end

  -- Add the contents of device_params into merged_params
  for index, dp in ipairs(device_params) do
    if not seen_ids[dp.id] then
      dp.index = index
      table.insert(merged_params, dp)
      seen_ids[dp.id] = true
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
  local active_devices_set = {}
  local devices_copy = fn.deep_copy(devices)

  -- Populating active_devices_set with ids from channels 1 through 16
  for i = 1, 16 do
    local device_map_id = program.get().devices[i].device_map
    if i ~= c and device_map_id ~= "none" then
      active_devices_set[device_map_id] = true
    end
  end

  -- Filtering devices_copy to remove any table whose id is present in active_devices_set
  local filtered_devices = {}
  for _, inner_table in ipairs(devices_copy) do
    if not (inner_table.id and inner_table.unique and active_devices_set[inner_table.id]) then
      table.insert(filtered_devices, inner_table)
    end
  end

  return filtered_devices
end

function device_map.get_params(device_id)
  local device = fn.get_by_id(devices, device_id)

  local device_params = device and device.params or {}
  return merge_params(device_params, stock_params)
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
