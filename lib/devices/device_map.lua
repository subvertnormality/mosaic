local device_map = {}
device_map.params_cache = {}

local descriptors = include("mosaic/lib/devices/device_descriptors")

local device_map_keyed_by_id = {}
local function get_none_param()
  return descriptors.get_none_param()
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
    ["cc_max_value"] = #note_division_labels - 1,
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
    ["cc_max_value"] = #note_division_labels - 1,
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
    ["cc_max_value"] = #note_division_labels - 1,
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
  },
  {
    ["id"] = "mute_root_note",
    ["name"] = "Mute Chord Root",
    ["short_descriptor_1"] = "CHRD",
    ["short_descriptor_2"] = "1NMT",
    ["off_value"] = 0,
    ["cc_min_value"] = 0,
    ["cc_max_value"] = 1,
    ["ui_labels"] = {
      "OFF",
      "ON"
    },
    ["param_type"] = "stock"
  },
  {
    ["id"] = "fully_quantise_mask",
    ["name"] = "Quantise Note Mask",
    ["short_descriptor_1"] = "QUAN",
    ["short_descriptor_2"] = "MASK",
    ["off_value"] = 0,
    ["cc_min_value"] = 0,
    ["cc_max_value"] = 2,
    ["ui_labels"] = {
      "X",
      "OFF",
      "ON"
    },
    ["param_type"] = "stock"
  },
}




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
  local merged_params = descriptors.merge_params(device_params, stock_params, get_none_param())
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
  local channel = program.get_channel(program.get().selected_song_pattern, c)
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
  devices = descriptors.load_devices(norns.state.data .. "config")
  device_map_keyed_by_id = create_device_map_keyed_by_id(devices)
end

return device_map
