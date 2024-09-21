-- channel_edit_page_ui_controller.lua
local channel_edit_page_ui_controller = {}

-- Include necessary modules
local fn = include("mosaic/lib/functions")
local quantiser = include("mosaic/lib/quantiser")
local pages = include("mosaic/lib/ui_components/pages")
local page = include("mosaic/lib/ui_components/page")
local vertical_scroll_selector = include("mosaic/lib/ui_components/vertical_scroll_selector")
local dial = include("mosaic/lib/ui_components/dial")
local control_scroll_selector = include("mosaic/lib/ui_components/control_scroll_selector")
local list_selector = include("mosaic/lib/ui_components/list_selector")
local value_selector = include("mosaic/lib/ui_components/value_selector")
local midi_controller = include("mosaic/lib/midi_controller")
local musicutil = require("musicutil")
local param_manager = include("mosaic/lib/param_manager")
local divisions = include("mosaic/lib/divisions")
local channel_edit_page_ui_handlers = include("mosaic/lib/pages/channel_edit_page/channel_edit_page_ui_handlers")
local channel_edit_page_ui_handlers = include("mosaic/lib/pages/channel_edit_page/channel_edit_page_ui_handlers")
local channel_edit_page_ui_refreshers = include("mosaic/lib/pages/channel_edit_page/channel_edit_page_ui_refreshers")

-- UI components
local channel_pages = pages:new()
local scales_pages = pages:new()
local quantizer_vertical_scroll_selector = vertical_scroll_selector:new(20, 25, "Quantizer", quantiser.get_scales())
local romans_vertical_scroll_selector = vertical_scroll_selector:new(90, 25, "Roman Analysis", quantiser.get_scales()[1].romans)
local notes_vertical_scroll_selector = vertical_scroll_selector:new(5, 25, "Notes", quantiser.get_notes())
local rotation_vertical_scroll_selector = vertical_scroll_selector:new(110, 25, "Rotation", {"0", "1", "2", "3", "4", "5", "6"})
local swing_shuffle_type_selector = list_selector:new(70, 18, "Swing Type", {{name = "X", value = 1}, {name = "Swing", value = 2}, {name = "Shuffle", value = 3}})
local swing_selector = value_selector:new(5, 40, "Swing", -51, 50)
local shuffle_feel_selector = list_selector:new(5, 40, "Shuffle Feel", {{name = "X", value = 1}, {name = "Drunk", value = 2}, {name = "Smooth", value = 3}, {name = "Heavy", value = 4}, {name = "Clave", value = 5}})
local shuffle_basis_selector = list_selector:new(70, 40, "Shuffle Basis", {{name = "X", value = 1}, {name = "9", value = 2}, {name = "7", value = 3}, {name = "5", value = 4}, {name = "6", value = 5}, {name = "8??", value = 6}, {name = "9??", value = 7}})

-- Value selectors with initial values
local mask_selectors = {
  trig = value_selector:new(5, 18, "Trig", -1, 1),
  note = value_selector:new(30, 18, "Note", -1, 127),
  velocity = value_selector:new(55, 18, "Vel", -1, 127),
  length = value_selector:new(80, 18, "Len", -1, 92),
  chords = {
    value_selector:new(5, 40, "Chd1", -14, 14),
    value_selector:new(30, 40, "Chd2", -14, 14),
    value_selector:new(55, 40, "Chd3", -14, 14),
    value_selector:new(80, 40, "Chd4", -14, 14)
  }
}

local note_displays = {
  note = value_selector:new(5, 18, "Note", -1, 1),
  velocity = value_selector:new(30, 18, "Vel", -1, 127),
  length = value_selector:new(55, 18, "Len", -1, 127),
  chords = {
    value_selector:new(5, 40, "Chd1", -1, 1),
    value_selector:new(30, 40, "Chd2", -1, 1),
    value_selector:new(55, 40, "Chd3", -1, 1),
    value_selector:new(80, 40, "Chd4", -1, 1)
  }
}

-- Clock and MIDI selectors
local clock_mod_list_selector = list_selector:new(5, 18, "Clock Mod", {})
local midi_device_vertical_scroll_selector = vertical_scroll_selector:new(90, 25, "Midi Device", {})
local midi_channel_vertical_scroll_selector = vertical_scroll_selector:new(65, 25, "Midi Channel", {
  {name = "CC1", value = 1}, {name = "CC2", value = 2}, {name = "CC3", value = 3}, {name = "CC4", value = 4},
  {name = "CC5", value = 5}, {name = "CC6", value = 6}, {name = "CC7", value = 7}, {name = "CC8", value = 8},
  {name = "CC9", value = 9}, {name = "CC10", value = 10}, {name = "CC11", value = 11}, {name = "CC12", value = 12},
  {name = "CC13", value = 13}, {name = "CC14", value = 14}, {name = "CC15", value = 15}, {name = "CC16", value = 16}
})
local device_map_vertical_scroll_selector = nil
local param_select_vertical_scroll_selector = vertical_scroll_selector:new(30, 25, "Params", {})

-- Dials
local dials = control_scroll_selector:new(0, 0, {})
local m_params = {}
for i = 1, 10 do
  table.insert(m_params, dial:new(5 + (i - 1) % 5 * 25, 18 + math.floor((i - 1) / 5) * 22, "Param " .. i, "param_" .. i, "None", "X"))
end

-- Page indices
local channel_page_to_index = {["Note dashboard"] = 1, ["Masks"] = 2, ["Trig Locks"] = 3, ["Clock Mods"] = 4, ["Midi Config"] = 5}
local scales_page_to_index = {["Quantizer"] = 1, ["Clock Mods"] = 2}

-- Helper variables
local refresh_timer_id = nil
local throttle_time = 0.2

-- Utility functions
local function print_no_scale_selected_message_to_screen()
  screen.level(5)
  screen.move(15, 35)
  screen.text("No scale selected")
end

local function print_quant_message_to_screen()
  screen.level(5)
  screen.move(15, 35)
  screen.text("Master quantiser mode")
end

local function configure_note_value_selector(note_value_selector)
  note_value_selector:set_view_transform_func(function(value)
    return value == -1 and "X" or musicutil.note_num_to_name(value, true)
  end)
end

local function configure_note_page_velocity_length_value_selector(selector)
  selector:set_view_transform_func(function(value)
    return value == -1 and "X" or value
  end)
end

local function configure_mask_length_selector(selector)
  mask_selectors.length:set_view_transform_func(function(value)
    return value == 0 and "X" or divisions.note_divisions[value].name
  end)
end

local function configure_swing_selector(selector)
  selector:set_view_transform_func(function(value)
    return value == -51 and "X" or value
  end)
end

local function configure_chord_value_selector(selector)
  local chord_ui_labels = {
    "--oct", "--2nd", "--3rd", "--4th", "--5th", "--6th", "--7th", "-oct", "-2nd", "-3rd", "-4th", "-5th", "-6th", "-7th", "X",
    "2nd", "3rd", "4th", "5th", "6th", "7th", "+oct", "+2nd", "+3rd", "+4th", "+5th", "+6th", "+7th", "++oct"
  }
  selector:set_view_transform_func(function(value)
    return chord_ui_labels[value + 15]
  end)
end

local function configure_note_trig_selector(selector)
  selector:set_view_transform_func(function(value)
    return value == 0 and "N" or value == 1 and "Y" or "X"
  end)
end

-- Configuring selectors
configure_note_value_selector(note_displays.note)
configure_mask_length_selector(note_displays.length)
configure_note_value_selector(note_displays.chords[1])
configure_note_value_selector(note_displays.chords[2])
configure_note_value_selector(note_displays.chords[3])
configure_note_value_selector(note_displays.chords[4])
configure_note_value_selector(mask_selectors.note)
configure_note_page_velocity_length_value_selector(mask_selectors.velocity)
configure_mask_length_selector(mask_selectors.length)
for _, chord_selector in ipairs(mask_selectors.chords) do
  configure_chord_value_selector(chord_selector)
end
configure_note_trig_selector(mask_selectors.trig)
configure_swing_selector(swing_selector)

-- Page definitions
local notes_page = page:new("Note Dashboard", function()
  if program.get().selected_channel ~= 17 then
    for _, selector in pairs(note_displays) do
      if type(selector) == "table" then
        for _, chord_selector in ipairs(selector) do
          chord_selector:draw()
        end
      end
    end
    note_displays.note:draw()
    note_displays.velocity:draw()
    note_displays.length:draw()
  end
end)


local mask_page = page:new("Note Masks", function()
  if program.get().selected_channel ~= 17 then
    for _, selector in pairs(mask_selectors) do
      if type(selector) == "table" then
        for _, chord_selector in ipairs(selector) do
          chord_selector:draw()
        end
      end
    end
    mask_selectors.trig:draw()
    mask_selectors.note:draw()
    mask_selectors.velocity:draw()
    mask_selectors.length:draw()

  else
    print_quant_message_to_screen()
  end
end)

local quantizer_page = page:new("", function()
  quantizer_vertical_scroll_selector:draw()
  romans_vertical_scroll_selector:draw()
  notes_vertical_scroll_selector:draw()
  rotation_vertical_scroll_selector:draw()
end)

local clock_mods_page = page:new("Clocks", function()
  if program.get().selected_channel ~= 17 then
    swing_shuffle_type_selector:draw()
    local value = swing_shuffle_type_selector:get_selected().value
    if value == 1 then 
      value = params:get("global_swing_shuffle_type") + 1
    end
    if value == 2 then
      swing_selector:draw()
    elseif value == 3 then
      shuffle_feel_selector:draw()
      shuffle_basis_selector:draw()
    end
  end
  clock_mod_list_selector:draw()
end)

local channel_edit_page = page:new("Device Config", function()
  if program.get().selected_channel ~= 17 then
    local channel = program.get_selected_channel()
    local device = fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)
    if device.type == "midi" then
      if device.default_midi_device == nil and midi_controller.midi_devices_connected() then
        midi_device_vertical_scroll_selector:draw()
      end
      if device.default_midi_channel == nil then
        midi_channel_vertical_scroll_selector:draw()
      end
    else
      midi_device_vertical_scroll_selector:deselect()
      midi_channel_vertical_scroll_selector:deselect()
      device_map_vertical_scroll_selector:select()
    end
    device_map_vertical_scroll_selector:draw()
  else
    print_quant_message_to_screen()
  end
end)

local trig_lock_page = page:new("Trig Locks", function()
  if program.get().selected_channel ~= 17 then
    dials:draw()
  else
    print_quant_message_to_screen()
  end
end)

-- Initialization function
function channel_edit_page_ui_controller.init()
  mask_selectors.note:select()
  quantizer_vertical_scroll_selector:select()
  midi_channel_vertical_scroll_selector:select()
  midi_device_vertical_scroll_selector:set_items(midi_controller.get_midi_outs())
  dials:set_items(m_params)
  clock_mod_list_selector:set_list(clock_controller.get_clock_divisions())
  device_map_vertical_scroll_selector = vertical_scroll_selector:new(10, 25, "Midi Map", device_map:get_devices())

  local function set_sub_name_func(page, func)
    page:set_sub_name_func(func)
  end


  set_sub_name_func(notes_page, function()
    return program.get().selected_channel ~= 17 and "Ch. " .. program.get().selected_channel .. " " or ""
  end)

  set_sub_name_func(mask_page, function()
    return program.get().selected_channel ~= 17 and "Ch. " .. program.get().selected_channel .. " " or ""
  end)

  set_sub_name_func(quantizer_page, function()
    return program.get().selected_channel ~= 17 and "Quantizer" or "Quantizer " .. program.get().selected_scale .. " "
  end)

  set_sub_name_func(channel_edit_page, function()
    return program.get().selected_channel ~= 17 and "Ch. " .. program.get().selected_channel .. " " or ""
  end)

  set_sub_name_func(clock_mods_page, function()
    return program.get().selected_channel ~= 17 and "Ch. " .. program.get().selected_channel .. " " or ""
  end)

  set_sub_name_func(trig_lock_page, function()
    return program.get().selected_channel ~= 17 and "Ch. " .. program.get().selected_channel .. " " or ""
  end)

  trig_lock_page:set_sub_page_draw_func(function()
    param_select_vertical_scroll_selector:draw()
  end)

  channel_pages:add_page(notes_page)
  channel_pages:add_page(mask_page)
  channel_pages:add_page(trig_lock_page)
  channel_pages:add_page(clock_mods_page)
  channel_pages:add_page(channel_edit_page)
  channel_pages:select_page(1)

  scales_pages:add_page(quantizer_page)
  scales_pages:add_page(clock_mods_page)
  scales_pages:select_page(1)

  dials:set_selected_item(1)
  clock_mod_list_selector:set_selected_value(13)
  clock_mod_list_selector:select()
  swing_selector:set_value(0)

  swing_shuffle_type_selector:set_selected_value(params:get("global_swing_shuffle_type"))
  swing_selector:set_value(params:get("global_swing"))
  shuffle_feel_selector:set_selected_value(params:get("global_shuffle_feel"))
  shuffle_basis_selector:set_selected_value(params:get("global_shuffle_basis"))

  channel_edit_page_ui_controller.refresh_clock_mods()
end

-- Register UI draw handlers
function channel_edit_page_ui_controller.register_ui_draw_handlers()
  draw_handler:register_ui("channel_edit_page", function()
    if program.get().selected_channel ~= 17 then
      channel_pages:draw()
    else
      scales_pages:draw()
    end
  end)
end

-- Update functions
function channel_edit_page_ui_controller.update_scale()
  local scale = quantizer_vertical_scroll_selector:get_selected_item()
  local chord = romans_vertical_scroll_selector:get_selected_index()
  local root_note = notes_vertical_scroll_selector:get_selected_index() - 1
  local rotation = rotation_vertical_scroll_selector:get_selected_index() - 1

  save_confirm.set_cancel_message("Scale not saved.")
  save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_quantiser)

  if is_key2_down then
    save_confirm.set_confirm_message("K2 to save across song.")
    save_confirm.set_ok_message("Scale saved to all.")
    save_confirm.set_save(function()
      program.set_all_sequencer_pattern_scales(
        program.get().selected_scale,
        {number = scale.number, scale = scale.scale, pentatonic_scale = scale.pentatonic_scale, chord = chord, root_note = root_note, chord_degree_rotation = rotation}
      )
    end)
  else
    save_confirm.set_save(function()
      program.set_scale(
        program.get().selected_scale,
        {number = scale.number, scale = scale.scale, pentatonic_scale = scale.pentatonic_scale, chord = chord, root_note = root_note, chord_degree_rotation = rotation}
      )
    end)
  end
end


function channel_edit_page_ui_controller.update_swing_shuffle_type()
  local channel = program.get_selected_channel()
  local value = swing_shuffle_type_selector:get_selected().value
  channel.swing_shuffle_type = value

  if value == 1 or nil then
    value = params:get("global_swing_shuffle_type") + 1 or 1
  end

  if clock_controller.is_playing() then
    step_handler.queue_for_pattern_change(function() 
      local c = channel.number 
      local val = value
      clock_controller.set_swing_shuffle_type(c, val) 
    end)
  else
    clock_controller.set_swing_shuffle_type(channel.number, value)
  end

end

function channel_edit_page_ui_controller.align_global_and_local_swing_shuffle_type_values(c)
  local channel = program.get_channel(c)
  local channel_value = channel.swing_shuffle_type
  local value = channel_value
  if channel_value == 1 or nil then
    value = params:get("global_swing_shuffle_type") + 1 or 1
  end

  clock_controller.set_swing_shuffle_type(channel.number, value)

end


function channel_edit_page_ui_controller.update_swing()
  local channel = program.get_selected_channel()
  local value = swing_selector:get_value()
  channel.swing = value
  if value == -51 or nil then
    value = params:get("global_swing") 
  end
  
  if clock_controller.is_playing() then
    step_handler.queue_for_pattern_change(function() 
      local c = channel.number 
      local val = value
      clock_controller.set_channel_swing(c, val) 
    end)
  else
    clock_controller.set_channel_swing(channel.number, value)
  end
end

function channel_edit_page_ui_controller.align_global_and_local_swing_values(c)
  local channel = program.get_channel(c)
  local channel_value = channel.swing
  local value = channel_value
  if channel_value == -51 or nil then
    value = params:get("global_swing") 
  end

  clock_controller.set_channel_swing(channel.number, value)

end

function channel_edit_page_ui_controller.update_shuffle_feel()
  local channel = program.get_selected_channel()
  local shuffle_feel = shuffle_feel_selector:get_selected().value
  channel.shuffle_feel = shuffle_feel
  if shuffle_feel == 1 or nil then
    shuffle_feel = params:get("global_shuffle_feel") + 1 or 0
  end

  if clock_controller.is_playing() then
    step_handler.queue_for_pattern_change(function() 
      local c = channel.number 
      local sf = shuffle_feel
      clock_controller.set_channel_shuffle_feel(c, sf) 
    end)
  else
    clock_controller.set_channel_shuffle_feel(channel.number, shuffle_feel)
  end
end

function channel_edit_page_ui_controller.align_global_and_local_shuffle_feel_values(c)
  local channel = program.get_channel(c)
  local channel_value = channel.shuffle_feel
  local value = channel_value
  if channel_value == 1 or nil then
    value = params:get("global_shuffle_feel") + 1 or 0
  end
  
  clock_controller.set_channel_shuffle_feel(channel.number, value)

end

function channel_edit_page_ui_controller.update_shuffle_basis()
  local channel = program.get_selected_channel()

  local shuffle_basis = shuffle_basis_selector:get_selected().value
  channel.shuffle_basis = shuffle_basis

  if shuffle_basis == 1 or nil then
    shuffle_basis = params:get("global_shuffle_basis") + 1 or 0
  end

  if clock_controller.is_playing() then
    step_handler.queue_for_pattern_change(function() 
      local c = channel.number 
      local sb = shuffle_basis
      clock_controller.set_channel_shuffle_basis(c, sb) 
    end)
  else
    clock_controller.set_channel_shuffle_basis(channel.number, shuffle_basis)
  end
end

function channel_edit_page_ui_controller.align_global_and_local_shuffle_basis_values(c)
  local channel = program.get_channel(c)
  local channel_value = channel.shuffle_basis
  local value = channel_value
  if channel_value == 1 or nil then
    value = params:get("global_shuffle_basis") + 1 or 0
  end
  
  clock_controller.set_channel_shuffle_basis(channel.number, value)

end

function channel_edit_page_ui_controller.update_clock_mods()
  local channel = program.get_selected_channel()
  local clock_mods = clock_mod_list_selector:get_selected()
  channel.clock_mods = clock_mods

  if clock_controller.is_playing() then
    step_handler.queue_for_pattern_change(function() 
      local c = channel.number 
      local div = clock_controller.calculate_divisor(clock_mods)
      clock_controller.set_channel_division(c, div) 
    end)
  else
    clock_controller.set_channel_division(channel.number, clock_controller.calculate_divisor(clock_mods))
  end
  
end

function channel_edit_page_ui_controller.update_channel_config()
  local channel = program.get_selected_channel()
  local midi_device = midi_device_vertical_scroll_selector:get_selected_item()
  local midi_channel = midi_channel_vertical_scroll_selector:get_selected_item()
  local device_m = device_map_vertical_scroll_selector:get_selected_item()

  if not midi_device then
    if device_m.type == "midi" then
      tooltip:error("No midi devices connected")
      return
    end
  end

  program.get().devices[channel.number].midi_device = midi_device and midi_device.value or nil
  program.get().devices[channel.number].midi_channel = midi_channel and midi_channel.value or nil
  program.get().devices[channel.number].device_map = device_m and device_m.id or nil

  local device = device_map.get_device(program.get().devices[channel.number].device_map)
  if device.default_midi_channel then
    program.get().devices[channel.number].midi_channel = device.default_midi_channel
  end

  if device.default_midi_device then
    program.get().devices[channel.number].midi_device = device.default_midi_device
  end

  channel_edit_page_ui_controller.refresh_device_selector()

  param_manager.add_device_params(
    channel.number,
    device_m,
    program.get().devices[channel.number].midi_channel,
    program.get().devices[channel.number].midi_device,
    true
  )
end

function channel_edit_page_ui_controller.change_page(page)
  if program.get().selected_channel ~= 17 then
    channel_pages:select_page(page)
  else
    scales_pages:select_page(page)
  end
end

-- Trig lock functions
function channel_edit_page_ui_controller.handle_trig_lock_param_change_by_direction(direction, channel, dial_index)
  local pressed_keys = grid_controller.get_pressed_keys()
  local param_id = channel.trig_lock_params[dial_index].param_id
  local p_value = nil
  if param_id then
    local p = params:lookup_param(param_id)
    if p.name ~= "undefined" then
      p_value = p.value
    end
  end

  if #pressed_keys > 0 and channel.trig_lock_params[dial_index] and channel.trig_lock_params[dial_index].id then
    for _, keys in ipairs(pressed_keys) do
      local step = fn.calc_grid_count(keys[1], keys[2])
      program.add_step_param_trig_lock(
        step,
        dial_index,
        (program.get_step_param_trig_lock(channel, step, dial_index) or p_value or channel.trig_lock_banks[dial_index]) + direction
      )
      m_params[dial_index]:set_value(
        program.get_step_param_trig_lock(channel, step, dial_index) or p_value or channel.trig_lock_banks[dial_index]
      )
    end
  elseif channel.trig_lock_params[dial_index] and channel.trig_lock_params[dial_index].id then

    local max_value = channel.trig_lock_params[dial_index].cc_max_value or 127
    local min_value = channel.trig_lock_params[dial_index].cc_min_value or -1

    if channel.trig_lock_params[dial_index].nrpn_min_value and channel.trig_lock_params[dial_index].nrpn_max_value and channel.trig_lock_params[dial_index].nrpn_lsb and channel.trig_lock_params[dial_index].nrpn_msb then
      max_value = math.floor(channel.trig_lock_params[dial_index].nrpn_max_value / 129)
      min_value = channel.trig_lock_params[dial_index].nrpn_min_value == -1 and -1 or math.floor(channel.trig_lock_params[dial_index].nrpn_min_value / 129)
    end
    channel.trig_lock_banks[dial_index] = channel.trig_lock_banks[dial_index] + direction
    if channel.trig_lock_banks[dial_index] > (max_value) then
      channel.trig_lock_banks[dial_index] = (max_value)
    elseif channel.trig_lock_banks[dial_index] < (min_value) then
      channel.trig_lock_banks[dial_index] = (min_value)
    end


    channel_edit_page_ui_controller.sync_param_to_trig_lock(dial_index, channel)
    channel_edit_page_ui_controller.refresh_trig_lock_value(dial_index)
  end
end

-- Encoder and key handling
function channel_edit_page_ui_controller.enc(n, d)
  local channel = program.get_selected_channel()
  if n == 3 then
    for _ = 1, math.abs(d) do
      if program.get().selected_channel ~= 17 and channel_pages:get_selected_page() == channel_page_to_index["Masks"] then
        channel_edit_page_ui_controller.handle_mask_page_change(d)
      end
      if d > 0 then
        if program.get().selected_channel == 17 and scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] then
          channel_edit_page_ui_controller.handle_quantizer_page_increment()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] and program.get().selected_channel ~= 17 then
          channel_edit_page_ui_controller.handle_clock_mods_page_increment()
        elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] and program.get().selected_channel == 17 then
          channel_edit_page_ui_controller.handle_scales_clock_mods_page_increment()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] and program.get().selected_channel ~= 17 then
          channel_edit_page_ui_controller.handle_midi_config_page_increment()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] and program.get().selected_channel ~= 17 then
          channel_edit_page_ui_handlers.handle_trig_locks_page_change(d, trig_lock_page, param_select_vertical_scroll_selector, dials)
        end
      else
        if scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] and program.get().selected_channel == 17 then
          channel_edit_page_ui_controller.handle_quantizer_page_decrement()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] and program.get().selected_channel ~= 17 then
          channel_edit_page_ui_controller.handle_clock_mods_page_decrement()
        elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] and program.get().selected_channel == 17 then
          channel_edit_page_ui_controller.handle_scales_clock_mods_page_decrement()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] and program.get().selected_channel ~= 17 then
          channel_edit_page_ui_controller.handle_midi_config_page_decrement()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] and program.get().selected_channel ~= 17 then
          channel_edit_page_ui_handlers.handle_trig_locks_page_change(d, trig_lock_page, param_select_vertical_scroll_selector, dials)
        end
      end
    end
  elseif n == 2 then
    for _ = 1, math.abs(d) do
      if d > 0 then
        channel_edit_page_ui_handlers.handle_encoder_two_positive(channel_pages, channel_page_to_index, scales_pages, scales_page_to_index, mask_selectors, quantizer_vertical_scroll_selector, romans_vertical_scroll_selector, notes_vertical_scroll_selector, rotation_vertical_scroll_selector, clock_mod_list_selector, swing_selector, midi_device_vertical_scroll_selector, midi_channel_vertical_scroll_selector, device_map_vertical_scroll_selector, dials, trig_lock_page, swing_shuffle_type_selector, swing_selector, shuffle_feel_selector, shuffle_basis_selector)
      else
        channel_edit_page_ui_handlers.handle_encoder_two_negative(channel_pages, channel_page_to_index, scales_pages, scales_page_to_index, mask_selectors, quantizer_vertical_scroll_selector, romans_vertical_scroll_selector, notes_vertical_scroll_selector, rotation_vertical_scroll_selector, clock_mod_list_selector, swing_selector, midi_device_vertical_scroll_selector, midi_channel_vertical_scroll_selector, device_map_vertical_scroll_selector, dials, trig_lock_page, swing_shuffle_type_selector, swing_selector, shuffle_feel_selector, shuffle_basis_selector)
      end
    end
  elseif n == 1 then
    for _ = 1, math.abs(d) do
      if d > 0 then
        channel_edit_page_ui_controller.handle_encoder_one_positive()
      else
        channel_edit_page_ui_controller.handle_encoder_one_negative()
      end
    end
  end
end

function channel_edit_page_ui_controller.key(n, z)
  if n == 2 and z == 1 then
    channel_edit_page_ui_controller.handle_key_two_pressed()
  elseif n == 3 and z == 1 then
    channel_edit_page_ui_controller.handle_key_three_pressed()
  end
end

-- Refresh functions
function channel_edit_page_ui_controller.refresh_masks()
  channel_edit_page_ui_refreshers.refresh_masks(mask_selectors)
end

function channel_edit_page_ui_controller.refresh_clock_mods()
  channel_edit_page_ui_refreshers.refresh_clock_mods(clock_mod_list_selector, swing_selector)
end

function channel_edit_page_ui_controller.refresh_swing()
  channel_edit_page_ui_refreshers.refresh_swing(swing_selector)
end

function channel_edit_page_ui_controller.refresh_swing_shuffle_type()
  channel_edit_page_ui_refreshers.refresh_swing_shuffle_type(swing_shuffle_type_selector)
end

function channel_edit_page_ui_controller.refresh_shuffle_feel()
  channel_edit_page_ui_refreshers.refresh_shuffle_feel(shuffle_feel_selector)
end

function channel_edit_page_ui_controller.refresh_shuffle_basis()
  channel_edit_page_ui_refreshers.refresh_shuffle_basis(shuffle_basis_selector)
end

function channel_edit_page_ui_controller.refresh_device_selector()
  channel_edit_page_ui_refreshers.refresh_device_selector(device_map_vertical_scroll_selector, param_select_vertical_scroll_selector)
end

function channel_edit_page_ui_controller.refresh_romans()
  channel_edit_page_ui_refreshers.refresh_romans(quantizer_vertical_scroll_selector, romans_vertical_scroll_selector)
end

function channel_edit_page_ui_controller.refresh_quantiser()
  channel_edit_page_ui_refreshers.refresh_quantiser(quantizer_vertical_scroll_selector, notes_vertical_scroll_selector, romans_vertical_scroll_selector, rotation_vertical_scroll_selector)
end

function channel_edit_page_ui_controller.refresh_trig_lock_value(i)
  channel_edit_page_ui_refreshers.refresh_trig_lock_value(i, m_params)
end

function channel_edit_page_ui_controller.refresh_trig_lock_values()
  for i = 1, 10 do
    channel_edit_page_ui_controller.refresh_trig_lock_value(i)
  end
end

function channel_edit_page_ui_controller.refresh_trig_locks()
  channel_edit_page_ui_refreshers.refresh_trig_locks(m_params)
end

function channel_edit_page_ui_controller.refresh_param_list()
  local channel = program.get_selected_channel()
  param_select_vertical_scroll_selector:set_items(device_map.get_available_params_for_channel(program.get().selected_channel, dials:get_selected_index()))
end

function channel_edit_page_ui_controller.refresh_channel_config()
  local channel = program.get_selected_channel()
  if channel.number == 17 then return end
  device_map_vertical_scroll_selector:set_items(device_map.get_available_devices_for_channel(program.get().selected_channel))
  midi_channel_vertical_scroll_selector:set_selected_item(program.get().devices[channel.number].midi_channel)
  midi_device_vertical_scroll_selector:set_selected_item(program.get().devices[channel.number].midi_device)
  device_map_vertical_scroll_selector:set_selected_item(fn.get_index_by_id(device_map_vertical_scroll_selector:get_items(), program.get().devices[channel.number].device_map))
  param_select_vertical_scroll_selector:set_selected_item(fn.get_index_by_id(param_select_vertical_scroll_selector:get_items(), channel.trig_lock_params[dials:get_selected_index()].id) or 1)
  device_map_vertical_scroll_selector:select()
  midi_channel_vertical_scroll_selector:deselect()
  midi_device_vertical_scroll_selector:deselect()
end




function channel_edit_page_ui_controller.throttled_refresh_channel_config()
  if refresh_timer_id then
    clock.cancel(refresh_timer_id)
  end
  refresh_timer_id = clock.run(function()
    clock.sleep(throttle_time)
    channel_edit_page_ui_controller.refresh_channel_config()
    refresh_timer_id = nil
  end)
end

function channel_edit_page_ui_controller.refresh()
  channel_edit_page_ui_controller.refresh_device_selector()
  channel_edit_page_ui_controller.throttled_refresh_channel_config()
  channel_edit_page_ui_controller.refresh_masks()
  channel_edit_page_ui_controller.refresh_trig_locks()
  channel_edit_page_ui_controller.refresh_quantiser()
  channel_edit_page_ui_controller.refresh_romans()
  channel_edit_page_ui_controller.refresh_clock_mods()
  channel_edit_page_ui_controller.refresh_swing()
  channel_edit_page_ui_controller.refresh_swing_shuffle_type()
  channel_edit_page_ui_controller.refresh_shuffle_feel()
  channel_edit_page_ui_controller.refresh_shuffle_basis()
end


function channel_edit_page_ui_controller.handle_trig_mask_change(direction)
  local pressed_keys = grid_controller.get_pressed_keys()
  local channel = program.get_selected_channel()
  if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
    if direction > 0 then
      mask_selectors.trig:increment()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        channel.step_trig_masks[step] = mask_selectors.trig:get_value()
      end
    else
      mask_selectors.trig:decrement()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        channel.step_trig_masks[step] = mask_selectors.trig:get_value() == -1 and nil or mask_selectors.trig:get_value()
      end
    end
  else
    mask_selectors.trig:set_value(channel.trig_mask or -1)
    if direction > 0 then
      mask_selectors.trig:increment()
      program.set_trig_mask(channel, mask_selectors.trig:get_value())
    else
      mask_selectors.trig:decrement()
      program.set_trig_mask(channel, mask_selectors.trig:get_value() == -1 and nil or mask_selectors.trig:get_value())
    end
    pattern_controller.throttled_update_working_pattern(channel.number)
  end
end


function channel_edit_page_ui_controller.handle_note_mask_change(direction)
  local pressed_keys = grid_controller.get_pressed_keys()
  local channel = program.get_selected_channel()
  if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
    if direction > 0 then
      mask_selectors.note:increment()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        channel.step_note_masks[step] = mask_selectors.note:get_value()
      end
    else
      mask_selectors.note:decrement()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        channel.step_note_masks[step] = mask_selectors.note:get_value() == -1 and nil or mask_selectors.note:get_value()
      end
    end
  else
    mask_selectors.note:set_value(channel.note_mask or -1)
    if direction > 0 then
      mask_selectors.note:increment()
      program.set_note_mask(channel, mask_selectors.note:get_value())
    else
      mask_selectors.note:decrement()
      program.set_note_mask(channel, mask_selectors.note:get_value() == -1 and nil or mask_selectors.note:get_value())
    end
    pattern_controller.throttled_update_working_pattern(channel.number)
  end
end

function channel_edit_page_ui_controller.handle_velocity_mask_change(direction)
  local pressed_keys = grid_controller.get_pressed_keys()
  local channel = program.get_selected_channel()
  if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
    if direction > 0 then
      mask_selectors.velocity:increment()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        channel.step_velocity_masks[step] = mask_selectors.velocity:get_value()
      end
    else
      mask_selectors.velocity:decrement()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        channel.step_velocity_masks[step] = mask_selectors.velocity:get_value() == -1 and nil or mask_selectors.velocity:get_value()
      end
    end
  else
    mask_selectors.velocity:set_value(channel.velocity_mask or -1)
    if direction > 0 then
      mask_selectors.velocity:increment()
      program.set_velocity_mask(channel, mask_selectors.velocity:get_value())
    else
      mask_selectors.velocity:decrement()
      program.set_velocity_mask(channel, mask_selectors.velocity:get_value() == -1 and nil or mask_selectors.velocity:get_value())
    end
    pattern_controller.throttled_update_working_pattern(channel.number)
  end
end

function channel_edit_page_ui_controller.handle_length_mask_change(direction)
  local pressed_keys = grid_controller.get_pressed_keys()
  local channel = program.get_selected_channel()
  if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
    if direction > 0 then
      mask_selectors.length:increment()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        program.set_step_length_mask(channel, step, divisions.note_division_values[mask_selectors.length:get_value()])
      end
    else
      if mask_selectors.length:get_value() ~= 0 then
        mask_selectors.length:decrement()
        for _, keys in ipairs(pressed_keys) do
          local step = fn.calc_grid_count(keys[1], keys[2])
          program.set_step_length_mask(channel, step, divisions.note_division_values[mask_selectors.length:get_value()])
        end
      else
        for _, keys in ipairs(pressed_keys) do
          local step = fn.calc_grid_count(keys[1], keys[2])
          program.set_step_length_mask(channel, step, 0)
          mask_selectors.length:set_value(0)
        end
      end
    end
  else
    mask_selectors.length:set_value(divisions.note_division_indexes[channel.length_mask] or 0)
    if direction > 0 then
      mask_selectors.length:increment()
      program.set_length_mask(channel, divisions.note_division_values[mask_selectors.length:get_value()])
    else
      if mask_selectors.length:get_value() ~= 0 then
        mask_selectors.length:decrement()
        program.set_length_mask(channel, divisions.note_division_values[mask_selectors.length:get_value()])
      else
        mask_selectors.length:set_value(0)
        program.set_length_mask(channel, 0)
      end
    end
    pattern_controller.throttled_update_working_pattern(channel.number)
  end
end

function channel_edit_page_ui_controller.handle_chord_mask_one_change(direction)
  local pressed_keys = grid_controller.get_pressed_keys()
  local channel = program.get_selected_channel()
  if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
    if direction > 0 then
      mask_selectors.chords[1]:increment()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        program.set_step_chord_mask(channel.number, 1, step, mask_selectors.chords[1]:get_value())
      end
    else
      mask_selectors.chords[1]:decrement()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        program.set_step_chord_mask(channel.number, 1, step, mask_selectors.chords[1]:get_value() == -1 and nil or mask_selectors.chords[1]:get_value())
      end
    end
  else
    mask_selectors.chords[1]:set_value(channel.chord_one_mask or -1)
    if direction > 0 then
      mask_selectors.chords[1]:increment()
      program.set_chord_one_mask(channel, mask_selectors.chords[1]:get_value())
    else
      mask_selectors.chords[1]:decrement()
      program.set_chord_one_mask(channel, mask_selectors.chords[1]:get_value() == -1 and nil or mask_selectors.chords[1]:get_value())
    end
  end
end

function channel_edit_page_ui_controller.handle_chord_mask_two_change(direction)
  local pressed_keys = grid_controller.get_pressed_keys()
  local channel = program.get_selected_channel()
  if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
    if direction > 0 then
      mask_selectors.chords[2]:increment()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        program.set_step_chord_mask(channel.number, 2, step, mask_selectors.chords[2]:get_value())
      end
    else
      mask_selectors.chords[2]:decrement()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        program.set_step_chord_mask(channel.number, 2, step, mask_selectors.chords[2]:get_value() == -1 and nil or mask_selectors.chords[2]:get_value())
      end
    end
  else
    mask_selectors.chords[2]:set_value(channel.chord_two_mask or -1)
    if direction > 0 then
      mask_selectors.chords[2]:increment()
      program.set_chord_two_mask(channel, mask_selectors.chords[2]:get_value())
    else
      mask_selectors.chords[2]:decrement()
      program.set_chord_two_mask(channel, mask_selectors.chords[2]:get_value() == -1 and nil or mask_selectors.chords[2]:get_value())
    end
  end
end

function channel_edit_page_ui_controller.handle_chord_mask_three_change(direction)
  local pressed_keys = grid_controller.get_pressed_keys()
  local channel = program.get_selected_channel()
  if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
    if direction > 0 then
      mask_selectors.chords[3]:increment()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        program.set_step_chord_mask(channel.number, 3, step, mask_selectors.chords[3]:get_value())
      end
    else
      mask_selectors.chords[3]:decrement()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        program.set_step_chord_mask(channel.number, 3, step, mask_selectors.chords[3]:get_value() == -1 and nil or mask_selectors.chords[3]:get_value())
      end
    end
  else
    mask_selectors.chords[3]:set_value(channel.chord_three_mask or -1)
    if direction > 0 then
      mask_selectors.chords[3]:increment()
      program.set_chord_three_mask(channel, mask_selectors.chords[3]:get_value())
    else
      mask_selectors.chords[3]:decrement()
      program.set_chord_three_mask(channel, mask_selectors.chords[3]:get_value() == -1 and nil or mask_selectors.chords[3]:get_value())
    end
  end
end

function channel_edit_page_ui_controller.handle_chord_mask_four_change(direction)
  local pressed_keys = grid_controller.get_pressed_keys()
  local channel = program.get_selected_channel()
  if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
    if direction > 0 then
      mask_selectors.chords[4]:increment()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        program.set_step_chord_mask(channel.number, 4, step, mask_selectors.chords[4]:get_value())
      end
    else
      mask_selectors.chords[4]:decrement()
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        program.set_step_chord_mask(channel.number, 4, step, mask_selectors.chords[4]:get_value() == -1 and nil or mask_selectors.chords[4]:get_value())
      end
    end
  else
    mask_selectors.chords[4]:set_value(channel.chord_four_mask or -1)
    if direction > 0 then
      mask_selectors.chords[4]:increment()
      program.set_chord_four_mask(channel, mask_selectors.chords[4]:get_value())
    else
      mask_selectors.chords[4]:decrement()
      program.set_chord_four_mask(channel, mask_selectors.chords[4]:get_value() == -1 and nil or mask_selectors.chords[4]:get_value())
    end
  end
end

-- Handlers for specific actions
function channel_edit_page_ui_controller.handle_mask_page_change(direction)
    if mask_selectors.trig:is_selected() then
      channel_edit_page_ui_controller.handle_trig_mask_change(direction)
    end
    if mask_selectors.note:is_selected() then
      channel_edit_page_ui_controller.handle_note_mask_change(direction)
    end
    if mask_selectors.velocity:is_selected() then
      channel_edit_page_ui_controller.handle_velocity_mask_change(direction)
    end
    if mask_selectors.length:is_selected() then
      channel_edit_page_ui_controller.handle_length_mask_change(direction)
    end
    if mask_selectors.chords[1]:is_selected() then
      channel_edit_page_ui_controller.handle_chord_mask_one_change(direction)
    end
    if mask_selectors.chords[2]:is_selected() then
      channel_edit_page_ui_controller.handle_chord_mask_two_change(direction)
    end
    if mask_selectors.chords[3]:is_selected() then
      channel_edit_page_ui_controller.handle_chord_mask_three_change(direction)
    end
    if mask_selectors.chords[4]:is_selected() then
      channel_edit_page_ui_controller.handle_chord_mask_four_change(direction)
    end
end

function channel_edit_page_ui_controller.handle_quantizer_page_increment()
  if quantizer_vertical_scroll_selector:is_selected() then
    quantizer_vertical_scroll_selector:scroll_down()
    channel_edit_page_ui_controller.refresh_romans()
  elseif romans_vertical_scroll_selector:is_selected() then
    romans_vertical_scroll_selector:scroll_down()
  elseif notes_vertical_scroll_selector:is_selected() then
    notes_vertical_scroll_selector:scroll_down()
  elseif rotation_vertical_scroll_selector:is_selected() then
    rotation_vertical_scroll_selector:scroll_down()
  end
  channel_edit_page_ui_controller.update_scale()
end

function channel_edit_page_ui_controller.handle_quantizer_page_decrement()
  if quantizer_vertical_scroll_selector:is_selected() then
    quantizer_vertical_scroll_selector:scroll_up()
    channel_edit_page_ui_controller.refresh_romans()
  elseif romans_vertical_scroll_selector:is_selected() then
    romans_vertical_scroll_selector:scroll_up()
  elseif notes_vertical_scroll_selector:is_selected() then
    notes_vertical_scroll_selector:scroll_up()
  elseif rotation_vertical_scroll_selector:is_selected() then
    rotation_vertical_scroll_selector:scroll_up()
  end
  channel_edit_page_ui_controller.update_scale()
end


function channel_edit_page_ui_controller.handle_clock_mods_page_increment()
  if swing_shuffle_type_selector:is_selected() then
    swing_shuffle_type_selector:increment()
    save_confirm.set_save(channel_edit_page_ui_controller.update_swing_shuffle_type)
    save_confirm.set_save(channel_edit_page_ui_controller.update_shuffle_feel)
    save_confirm.set_save(channel_edit_page_ui_controller.update_shuffle_basis)
    save_confirm.set_save(channel_edit_page_ui_controller.update_swing)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_swing_shuffle_type)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_swing)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_shuffle_feel)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_shuffle_basis)
    fn.dirty_screen(true)
  elseif swing_selector:is_selected() then
    swing_selector:increment()
    save_confirm.set_save(channel_edit_page_ui_controller.update_swing)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_swing)
  elseif shuffle_feel_selector:is_selected() then
    shuffle_feel_selector:increment()
    save_confirm.set_save(channel_edit_page_ui_controller.update_shuffle_feel)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_shuffle_feel)
  elseif shuffle_basis_selector:is_selected() then
    shuffle_basis_selector:increment()
    save_confirm.set_save(channel_edit_page_ui_controller.update_shuffle_basis)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_shuffle_basis)
  elseif clock_mod_list_selector:is_selected() then
    clock_mod_list_selector:decrement()
    save_confirm.set_save(channel_edit_page_ui_controller.update_clock_mods)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_clock_mods)
  end
end

function channel_edit_page_ui_controller.handle_clock_mods_page_decrement()
  if swing_shuffle_type_selector:is_selected() then
    swing_shuffle_type_selector:decrement()
    save_confirm.set_save(channel_edit_page_ui_controller.update_swing_shuffle_type)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_swing_shuffle_type)
  elseif swing_selector:is_selected() then
    swing_selector:decrement()
    save_confirm.set_save(channel_edit_page_ui_controller.update_swing)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_swing)
  elseif shuffle_feel_selector:is_selected() then
    shuffle_feel_selector:decrement()
    save_confirm.set_save(channel_edit_page_ui_controller.update_shuffle_feel)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_shuffle_feel)
  elseif shuffle_basis_selector:is_selected() then
    shuffle_basis_selector:decrement()
    save_confirm.set_save(channel_edit_page_ui_controller.update_shuffle_basis)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_shuffle_basis)
  elseif clock_mod_list_selector:is_selected() then
    clock_mod_list_selector:increment()
    save_confirm.set_save(channel_edit_page_ui_controller.update_clock_mods)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_clock_mods)
  end
end

function channel_edit_page_ui_controller.handle_scales_clock_mods_page_increment()
  if clock_mod_list_selector:is_selected() then
    clock_mod_list_selector:decrement()
    save_confirm.set_save(channel_edit_page_ui_controller.update_clock_mods)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_clock_mods)
  end
end

function channel_edit_page_ui_controller.handle_scales_clock_mods_page_decrement()
  if clock_mod_list_selector:is_selected() then
    clock_mod_list_selector:increment()
    save_confirm.set_save(function()
      channel_edit_page_ui_controller.update_clock_mods()
    end)
    save_confirm.set_cancel(function()
      channel_edit_page_ui_controller.refresh_clock_mods()
    end)
  end
end

function channel_edit_page_ui_controller.handle_midi_config_page_increment()
  if midi_device_vertical_scroll_selector:is_selected() then
    midi_device_vertical_scroll_selector:scroll_down()
  elseif midi_channel_vertical_scroll_selector:is_selected() then
    midi_channel_vertical_scroll_selector:scroll_down()
  elseif device_map_vertical_scroll_selector:is_selected() then
    device_map_vertical_scroll_selector:scroll_down()
  end
  save_confirm.set_save(function()
    channel_edit_page_ui_controller.update_channel_config()
    
    param_manager.update_default_params(program.get_selected_channel(), device_map_vertical_scroll_selector:get_selected_item())
    param_select_vertical_scroll_selector:set_selected_item(1)
  end)
  save_confirm.set_cancel(channel_edit_page_ui_controller.throttled_refresh_channel_config)
end

function channel_edit_page_ui_controller.handle_midi_config_page_decrement()
  local device = fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)
  
  if midi_device_vertical_scroll_selector:is_selected() then
    midi_device_vertical_scroll_selector:scroll_up()
  elseif midi_channel_vertical_scroll_selector:is_selected() then
    midi_channel_vertical_scroll_selector:scroll_up()
  elseif device_map_vertical_scroll_selector:is_selected() then
    device_map_vertical_scroll_selector:scroll_up()
  end

  save_confirm.set_save(function()
    channel_edit_page_ui_controller.update_channel_config()
    param_manager.update_default_params(program.get_selected_channel(), device_map_vertical_scroll_selector:get_selected_item())
    param_select_vertical_scroll_selector:set_selected_item(1)
  end)

  save_confirm.set_cancel(function()
    channel_edit_page_ui_controller.throttled_refresh_channel_config()
  end)
end

function channel_edit_page_ui_controller.handle_encoder_one_positive()
  if program.get().selected_channel ~= 17 then
    channel_pages:next_page()
  else
    scales_pages:next_page()
  end
  fn.dirty_screen(true)
  save_confirm.cancel()
end

function channel_edit_page_ui_controller.handle_encoder_one_negative()
  if program.get().selected_channel ~= 17 then
    channel_pages:previous_page()
  else
    scales_pages:previous_page()
  end
  fn.dirty_screen(true)
  save_confirm.cancel()
end

function channel_edit_page_ui_controller.handle_key_two_pressed()
  local pressed_keys = grid_controller.get_pressed_keys()
  if #pressed_keys > 0 then
    for _, keys in ipairs(pressed_keys) do
      local step = fn.calc_grid_count(keys[1], keys[2])
      if channel_pages:get_selected_page() == channel_page_to_index["Masks"] then
        program.clear_masks_for_step(step)
        channel_edit_page_ui_controller.refresh_masks()
        tooltip:show("Note masks for step " .. step .. " cleared")
      end
      if channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] then
        program.clear_trig_locks_for_step(step)
        channel_edit_page_ui_controller.refresh_trig_locks()
        tooltip:show("Trig locks for step " .. step .. " cleared")
      end
    end
  else
    if channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] then
      if not trig_lock_page:is_sub_page_enabled() then
        channel_edit_page_ui_controller.refresh_device_selector()
        channel_edit_page_ui_controller.refresh_param_list()
      end
      channel_edit_page_ui_controller.refresh_channel_config()
      trig_lock_page:toggle_sub_page()
    end
    save_confirm.cancel()
  end
end

function channel_edit_page_ui_controller.handle_key_three_pressed()
  local pressed_keys = grid_controller.get_pressed_keys()
  if #pressed_keys > 0 then
    for _, keys in ipairs(pressed_keys) do
      local step = fn.calc_grid_count(keys[1], keys[2])
      local step_trig_lock_banks = program.get_selected_channel().step_trig_lock_banks
      local channel = program.get_selected_channel()
      if channel.number ~= 17 and step_trig_lock_banks and step_trig_lock_banks[step] then
        local parameter = dials:get_selected_index()
        step_trig_lock_banks[step][parameter] = nil
        tooltip:show("Param trig lock " .. parameter .. " cleared")
        local has_active_parameter = false
        for i = 1, 10 do
          if step_trig_lock_banks[step][i] then
            has_active_parameter = true
          end
        end
        if not has_active_parameter then
          step_trig_lock_banks[step] = nil
        end
      end
      dials:get_selected_item():set_value(
        program.get_step_param_trig_lock(program.get_selected_channel(), step, dials:get_selected_index()) or
        program.get_selected_channel().trig_lock_banks[dials:get_selected_index()]
      )
      channel_edit_page_ui_controller.refresh_trig_locks()
    end
  else
    save_confirm.confirm()
  end
end

function channel_edit_page_ui_controller.sync_param_to_trig_lock(i, channel)

  if not channel.trig_lock_banks[i] then
    return
  end
  
  local param_id = channel.trig_lock_params[i].param_id

  local p = nil
  if param_id ~= nil then
    p = params:lookup_param(channel.trig_lock_params[i].param_id)

    local value = channel.trig_lock_banks[i]

    if channel.trig_lock_params[i].nrpn_min_value and channel.trig_lock_params[i].nrpn_max_value and channel.trig_lock_params[i].nrpn_lsb and channel.trig_lock_params[i].nrpn_msb then
      value = channel.trig_lock_banks[i] * 129
    end

    params:set(param_id, value)
  end
end

function channel_edit_page_ui_controller.select_page(page) 
    channel_pages:select_page(page)
    fn.dirty_screen(true)
end

function channel_edit_page_ui_controller.get_selected_page() 
    return channel_pages:get_selected_page()
end

function channel_edit_page_ui_controller.select_mask_page()
  channel_pages:select_page(channel_page_to_index["Masks"])
  fn.dirty_screen(true)
end

function channel_edit_page_ui_controller.select_trig_page()
  channel_pages:select_page(channel_page_to_index["Trig Locks"])
end

function channel_edit_page_ui_controller.set_note_dashboard_values(values)
  if values and values.note then
    note_displays.note:set_value(values.note)
  end
  if values and values.velocity then
    note_displays.velocity:set_value(values.velocity)
  end
  if values and values.length then
    note_displays.length:set_value(
      values.length
    )
  end
  if values and values.trig then
    note_displays.trig:set_value(values.trig)
  end

  if (values and values.chords) then

    for i = 1, 4 do
      
      if values.chords[i] and values.chords[i] ~= 0 then
        note_displays.chords[i]:set_value(values.chords[i])
      else
        note_displays.chords[i]:set_value(-1)
      end
    end
  end
end

return channel_edit_page_ui_controller
