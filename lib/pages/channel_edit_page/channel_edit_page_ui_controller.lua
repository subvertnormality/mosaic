-- channel_edit_page_ui_controller.lua
local channel_edit_page_ui_controller = {}

-- Include necessary modules

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
local quantizer_vertical_scroll_selector = vertical_scroll_selector:new(13, 25, "Quantizer", quantiser.get_scales())
local romans_vertical_scroll_selector = vertical_scroll_selector:new(80, 25, "Roman Analysis", quantiser.get_scales()[1].romans)
local notes_vertical_scroll_selector = vertical_scroll_selector:new(0, 25, "Notes", quantiser.get_notes())
local transpose_vertical_scroll_selector = vertical_scroll_selector:new(103, 25, "Transpose", {"-12", "-11", "-10", "-9", "-8", "-7", "-6", "-5", "-4", "-3", "-2", "-1", "0", "+1", "+2", "+3", "+4", "+5", "+6", "+7", "+8", "+9", "+10", "+11", "+12"})
local rotation_vertical_scroll_selector = vertical_scroll_selector:new(115, 25, "Rotation", {"r0", "r1", "r2", "r3", "r4", "r5", "r6"})
local swing_shuffle_type_selector = list_selector:new(70, 18, "Swing Type", {{name = "X", value = 1}, {name = "Swing", value = 2}, {name = "Shuffle", value = 3}})
local swing_selector = value_selector:new(0, 40, "Swing", -51, 50)
local shuffle_feel_selector = list_selector:new(0, 40, "Feel", {{name = "X", value = 1}, {name = "Drunk", value = 2}, {name = "Smooth", value = 3}, {name = "Heavy", value = 4}, {name = "Clave", value = 5}})
local shuffle_basis_selector = list_selector:new(40, 40, "Basis", {{name = "X", value = 1}, {name = "9", value = 2}, {name = "7", value = 3}, {name = "5", value = 4}, {name = "6", value = 5}, {name = "8??", value = 6}, {name = "9??", value = 7}})
local shuffle_amount_selector = value_selector:new(70, 40, "Amount", 0, 100)



-- Value selectors with initial values
local mask_selectors = {
  trig = value_selector:new(0 + (1 - 1) % 5 * 25, 18 + math.floor((1 - 1) / 5) * 22, "Trig", -1, 1),
  note = value_selector:new(0 + (2 - 1) % 5 * 25, 18 + math.floor((2 - 1) / 5) * 22, "Note", -1, 127),
  velocity = value_selector:new(0 + (3 - 1) % 5 * 25, 18 + math.floor((3 - 1) / 5) * 22, "Vel", -1, 127),
  length = value_selector:new(0 + (4 - 1) % 5 * 25, 18 + math.floor((4 - 1) / 5) * 22, "Len", -1, 92),
  chords = {
    value_selector:new(0 + (6 - 1) % 5 * 25, 18 + math.floor((6 - 1) / 5) * 22, "Chd1", -14, 14),
    value_selector:new(0 + (7 - 1) % 5 * 25, 18 + math.floor((7 - 1) / 5) * 22, "Chd2", -14, 14),
    value_selector:new(0 + (8 - 1) % 5 * 25, 18 + math.floor((8 - 1) / 5) * 22, "Chd3", -14, 14),
    value_selector:new(0 + (9 - 1) % 5 * 25, 18 + math.floor((9 - 1) / 5) * 22, "Chd4", -14, 14)
  }
}

local note_displays = {
  note = value_selector:new(0 + (1 - 1) % 5 * 25, 18 + math.floor((1 - 1) / 5) * 22, "Note", -1, 1),
  velocity = value_selector:new(0 + (2 - 1) % 5 * 25, 18 + math.floor((2 - 1) / 5) * 22, "Vel", -1, 127),
  length = value_selector:new(0 + (3 - 1) % 5 * 25, 18 + math.floor((3 - 1) / 5) * 22, "Len", -1, 127),
  chords = {
    value_selector:new(0 + (6 - 1) % 5 * 25, 18 + math.floor((6 - 1) / 5) * 22, "Chd1", -1, 1),
    value_selector:new(0 + (7 - 1) % 5 * 25, 18 + math.floor((7 - 1) / 5) * 22, "Chd2", -1, 1),
    value_selector:new(0 + (8 - 1) % 5 * 25, 18 + math.floor((8 - 1) / 5) * 22, "Chd3", -1, 1),
    value_selector:new(0 + (9 - 1) % 5 * 25, 18 + math.floor((9 - 1) / 5) * 22, "Chd4", -1, 1)
  }
}

-- Clock and MIDI selectors
local clock_mod_list_selector = list_selector:new(0, 18, "Clock Mod", {})
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
  table.insert(m_params, dial:new(0 + (i - 1) % 5 * 25, 18 + math.floor((i - 1) / 5) * 22, "Param " .. i, "param_" .. i, "None", "X"))
end

-- Page indices
local channel_page_to_index = {["Note Dashboard"] = 1, ["Masks"] = 2, ["Trig Locks"] = 3, ["Clock Mods"] = 4, ["Midi Config"] = 5}
local index_to_channel_page = {"Note Dashboard", "Masks", "Trig Locks", "Clock Mods", "Midi Config"}
local scales_page_to_index = {["Quantizer"] = 1, ["Clock Mods"] = 2}
local index_to_scales_page = {"Quantizer", "Clock Mods"}

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
    local v = value
    if type(value) == "table" then
      v = value.note_value
    end
    if not v then return "X" end
    local named_note = musicutil.note_num_to_name(v, true)
    return v == -1 and "X" or named_note
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
  transpose_vertical_scroll_selector:draw()
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
      shuffle_amount_selector:draw()
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
  device_map_vertical_scroll_selector = vertical_scroll_selector:new(5, 25, "Midi Map", device_map:get_devices())

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

  channel_edit_page_ui_controller.select_note_dashboard_page()

  scales_pages:add_page(quantizer_page)
  scales_pages:add_page(clock_mods_page)
  channel_edit_page_ui_controller.select_scales_quantizer_page()

  dials:set_selected_item(1)
  clock_mod_list_selector:set_selected_value(13)
  clock_mod_list_selector:select()
  swing_selector:set_value(0)

  swing_shuffle_type_selector:set_selected_value(params:get("global_swing_shuffle_type"))
  swing_selector:set_value(params:get("global_swing"))
  shuffle_feel_selector:set_selected_value(params:get("global_shuffle_feel"))
  shuffle_basis_selector:set_selected_value(params:get("global_shuffle_basis"))
  shuffle_amount_selector:set_value(params:get("global_shuffle_amount"))

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
  local transpose = transpose_vertical_scroll_selector:get_selected_index() - 13
  local rotation = rotation_vertical_scroll_selector:get_selected_index() - 1

  save_confirm.set_cancel_message("Scale not saved.")
  save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_quantiser)

  if is_key3_down then
    save_confirm.set_confirm_message("K2 to save across song.")
    save_confirm.set_ok_message("Scale saved to all.")
    save_confirm.set_save(function()
      program.set_all_sequencer_pattern_scales(
        program.get().selected_scale,
        {number = scale.number, scale = scale.scale, pentatonic_scale = scale.pentatonic_scale, chord = chord, root_note = root_note, chord_degree_rotation = rotation, transpose = transpose}
      )
    end)
  else
    save_confirm.set_save(function()
      program.set_scale(
        program.get().selected_scale,
        {number = scale.number, scale = scale.scale, pentatonic_scale = scale.pentatonic_scale, chord = chord, root_note = root_note, chord_degree_rotation = rotation, transpose = transpose}
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

function channel_edit_page_ui_controller.update_shuffle_amount()
  local channel = program.get_selected_channel()
  local shuffle_amount = shuffle_amount_selector:get_value()
  channel.shuffle_amount = shuffle_amount

  if shuffle_amount == 0 or nil then
    shuffle_amount = params:get("global_shuffle_amount") or 0
  end

  if clock_controller.is_playing() then
    step_handler.queue_for_pattern_change(function() 
      local c = channel.number 
      local sa = shuffle_amount
      clock_controller.set_channel_shuffle_amount(c, sa) 
    end)
  else
    clock_controller.set_channel_shuffle_amount(channel.number, shuffle_amount)
  end
end

function channel_edit_page_ui_controller.align_global_and_local_shuffle_amount_values(c)
  local channel = program.get_channel(c)
  local channel_value = channel.shuffle_amount
  local value = channel_value
  if channel_value == 0 or nil then
    value = params:get("global_shuffle_amount") or 0
  end
  
  clock_controller.set_channel_shuffle_amount(channel.number, value)

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

  if device_m.id == "jf kit" or
    device_m.id == "jf n 1" or
    device_m.id == "jf n 2" or
    device_m.id == "jf poly" or
    device_m.id == "jf unison" or
    device_m.id == "jf n 5" or
    device_m.id == "jf mpe" or
    device_m.id == "jf n 4" or
    device_m.id == "jf n 3" or
    device_m.id == "jf n 6"
  then
    crow.ii.jf.mode(1)
  end

  param_manager.add_device_params(
    channel.number,
    device_m,
    program.get().devices[channel.number].midi_channel,
    program.get().devices[channel.number].midi_device,
    true
  )
  for i = 1, 10 do
    program.increment_trig_lock_calculator_id(channel, i)
  end

  channel_edit_page_ui_controller.refresh_trig_locks()
  
end

-- Trig lock functions
function channel_edit_page_ui_controller.handle_trig_lock_param_change_by_direction(direction, channel, dial_index)

  local pressed_keys = grid_controller.get_pressed_keys()
  local trig_lock_param = channel.trig_lock_params[dial_index]

  if not trig_lock_param then
    return
  end

  local param_id = trig_lock_param.param_id

  local p, p_index
  if param_id then
    p = params:lookup_param(param_id)
    p_index = params.lookup[param_id]
  else
    return
  end

  if not p then
    return
  end

  local p_value = params:get(param_id)

  local total_range = 0
  local old_quantum = 1

  if p.controlspec then 

    if p.controlspec.quantum then
      old_quantum = p.controlspec.quantum
    end

    total_range = ((p.controlspec.maxval - p.controlspec.minval) / p.controlspec.quantum)

    if trig_lock_param.nrpn_min_value and trig_lock_param.nrpn_max_value and trig_lock_param.nrpn_lsb and trig_lock_param.nrpn_msb then
      p.controlspec.quantum = 1 / (trig_lock_param.nrpn_max_value - trig_lock_param.nrpn_min_value) 
      total_range = p.controlspec.maxval - p.controlspec.minval

    elseif trig_lock_param.cc_min_value and trig_lock_param.cc_max_value and trig_lock_param.cc_msb then
      p.controlspec.quantum = 1 / (trig_lock_param.cc_max_value - trig_lock_param.cc_min_value)
      total_range = p.controlspec.maxval - p.controlspec.minval
    elseif trig_lock_param.cc_min_value and trig_lock_param.cc_max_value and trig_lock_param.type == "midi" then
      p.controlspec.quantum = 1 / (trig_lock_param.cc_max_value - trig_lock_param.cc_min_value)
      total_range = p.controlspec.maxval - p.controlspec.minval
    elseif trig_lock_param.cc_min_value and trig_lock_param.cc_max_value and trig_lock_param.type == "norns" then
      p.controlspec.quantum = 1 / (trig_lock_param.cc_max_value - trig_lock_param.cc_min_value)
      total_range = p.controlspec.maxval - p.controlspec.minval
    end
  elseif p.count then
    total_range = p.count
  elseif p.maxval and p.minval then
    total_range = p.maxval - p.minval
  else
    total_range = 127
  end

  local d = direction

  if total_range > 126 and is_key3_down == false then
    if math.abs(direction) > 0 then
      d = direction * math.floor(total_range / 127) or 1
    end

    if math.abs(direction) > 2 then
      d = direction * math.floor(total_range / 64) or 1
    end

    if math.abs(direction) > 5 then
      d = direction * math.floor(total_range / 32) or 1
    end

    if math.abs(direction) > 8 then
      d = direction * math.floor(total_range / 16) or 1
    end

    if math.abs(direction) > 10 then
      d = direction * math.floor(total_range / 8) or 1
    end

    if math.abs(direction) > 13 then
      d = direction * math.floor(total_range / 4) or 1
    end

    if math.abs(direction) > 15 then
      d = direction * math.floor(total_range / 2) or 1
    end
  end

  if #pressed_keys > 0 and trig_lock_param and trig_lock_param.id then
    for _, keys in ipairs(pressed_keys) do
      local step = fn.calc_grid_count(keys[1], keys[2])
      local param_args = {}

      for key, arg in pairs(p) do
        param_args[key] = arg
      end

      local handler_param_id = channel.number .. "_lock_calculator_" .. dial_index .. "_" .. program.get_trig_lock_calculator_id(channel, dial_index)

      param_args.id = handler_param_id
      param_args.type = fn.get_param_type_from_id(params:t(param_id))
      param_args.controlspec = p.controlspec

      local handler_param_id_index = params.lookup[handler_param_id]

      if not handler_param_id_index then
        params:add(param_args)
        handler_param_id_index = params.lookup[handler_param_id]
        params:hide(handler_param_id_index)
        params:set_action(handler_param_id_index, function() end)
        params:set(handler_param_id_index, p_value, true)
      end

      
      params:delta(handler_param_id_index, d)

      local value = params:get(handler_param_id_index)

      program.add_step_param_trig_lock(step, dial_index, value)
      m_params[dial_index]:set_value(value)
    end
  elseif p_value and trig_lock_param and trig_lock_param.id then
    p:delta(d)

    channel_edit_page_ui_controller.refresh_trig_lock_value(dial_index)
  end

  m_params[dial_index]:temp_display_value()
  if p.controlspec and p.controlspec.quantum then
    p.controlspec.quantum = old_quantum
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
      
      local pages = {
        channel_pages = channel_pages,
        channel_page_to_index = channel_page_to_index,
        scales_pages = scales_pages,
        scales_page_to_index = scales_page_to_index,
      }

      local selectors = {
        mask_selectors = mask_selectors,
        quantizer_vertical_scroll_selector = quantizer_vertical_scroll_selector,
        romans_vertical_scroll_selector = romans_vertical_scroll_selector,
        notes_vertical_scroll_selector = notes_vertical_scroll_selector,
        transpose_vertical_scroll_selector = transpose_vertical_scroll_selector,
        rotation_vertical_scroll_selector = rotation_vertical_scroll_selector,
        clock_mod_list_selector = clock_mod_list_selector,
        midi_device_vertical_scroll_selector = midi_device_vertical_scroll_selector,
        midi_channel_vertical_scroll_selector = midi_channel_vertical_scroll_selector,
        device_map_vertical_scroll_selector = device_map_vertical_scroll_selector,
        swing_shuffle_type_selector = swing_shuffle_type_selector,
        swing_selector = swing_selector,
        shuffle_feel_selector = shuffle_feel_selector,
        shuffle_basis_selector = shuffle_basis_selector,
        shuffle_amount_selector = shuffle_amount_selector,
      }

      if d > 0 then
        channel_edit_page_ui_handlers.handle_encoder_two_positive(pages, selectors, dials, trig_lock_page)
      else
        channel_edit_page_ui_handlers.handle_encoder_two_negative(pages, selectors, dials, trig_lock_page)
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

function channel_edit_page_ui_controller.refresh_shuffle_amount()
  channel_edit_page_ui_refreshers.refresh_shuffle_amount(shuffle_amount_selector)
end

function channel_edit_page_ui_controller.refresh_device_selector()
  channel_edit_page_ui_refreshers.refresh_device_selector(device_map_vertical_scroll_selector, param_select_vertical_scroll_selector)
end

function channel_edit_page_ui_controller.refresh_romans()
  channel_edit_page_ui_refreshers.refresh_romans(quantizer_vertical_scroll_selector, romans_vertical_scroll_selector)
end

function channel_edit_page_ui_controller.refresh_quantiser()
  channel_edit_page_ui_refreshers.refresh_quantiser(quantizer_vertical_scroll_selector, notes_vertical_scroll_selector, romans_vertical_scroll_selector, transpose_vertical_scroll_selector, rotation_vertical_scroll_selector)
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

channel_edit_page_ui_controller.refresh_channel_config = scheduler.debounce(function()
  -- Initial checks
  local channel = program.get_selected_channel()
  if channel.number == 17 then return end
  
  -- Cache program data to avoid repeated lookups
  local program_data = program.get()
  local channel_device = program_data.devices[channel.number]
  
  -- First batch: Basic device setup
  device_map_vertical_scroll_selector:set_items(
    device_map.get_available_devices_for_channel(program_data.selected_channel)
  )
  midi_channel_vertical_scroll_selector:set_selected_item(
    channel_device.midi_channel
  )
  midi_device_vertical_scroll_selector:set_selected_item(
    channel_device.midi_device
  )
  coroutine.yield()

  -- Second batch: Complex device map lookup and setting
  device_map_vertical_scroll_selector:set_selected_item(
    fn.get_index_by_id(
      device_map_vertical_scroll_selector:get_items(), 
      channel_device.device_map
    )
  )
  coroutine.yield()

  -- Third batch: Complex param selection
  param_select_vertical_scroll_selector:set_selected_item(
    fn.get_index_by_id(
      param_select_vertical_scroll_selector:get_items(),
      channel.trig_lock_params[dials:get_selected_index()].id
    ) or 1
  )
  coroutine.yield()

  -- Final batch: Selection states
  device_map_vertical_scroll_selector:select()
  midi_channel_vertical_scroll_selector:deselect()
  midi_device_vertical_scroll_selector:deselect()
end)



function channel_edit_page_ui_controller.refresh()
  if program.get().selected_channel ~= 17 then
    channel_edit_page_ui_controller.select_channel_page_by_index(channel_pages:get_selected_page() or 1)
  else
    channel_edit_page_ui_controller.select_scale_page_by_index(scales_pages:get_selected_page() or 1)
  end
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
    pattern_controller.update_working_pattern(channel.number)
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
    pattern_controller.update_working_pattern(channel.number)
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
    pattern_controller.update_working_pattern(channel.number)
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
        program.set_length_mask(channel, nil)
      end
    end
    pattern_controller.update_working_pattern(channel.number)
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
  elseif transpose_vertical_scroll_selector:is_selected() then
    transpose_vertical_scroll_selector:scroll_down()
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
  elseif transpose_vertical_scroll_selector:is_selected() then
    transpose_vertical_scroll_selector:scroll_up()
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
    save_confirm.set_save(channel_edit_page_ui_controller.update_shuffle_amount)
    save_confirm.set_save(channel_edit_page_ui_controller.update_swing)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_swing_shuffle_type)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_swing)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_shuffle_feel)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_shuffle_basis)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_shuffle_amount)
    
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
  elseif shuffle_amount_selector:is_selected() then
    shuffle_amount_selector:increment()
    save_confirm.set_save(channel_edit_page_ui_controller.update_shuffle_amount)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_shuffle_amount)
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
  elseif shuffle_amount_selector:is_selected() then
    shuffle_amount_selector:decrement()
    save_confirm.set_save(channel_edit_page_ui_controller.update_shuffle_amount)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_shuffle_amount)
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

  local device = fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)

  save_confirm.clear()

  save_confirm.set_save(function()
    channel_edit_page_ui_controller.update_channel_config()
    
    param_manager.update_default_params(program.get_selected_channel(), device)
    param_select_vertical_scroll_selector:set_selected_item(1)
    channel_edit_page_ui_controller.refresh_trig_locks()
  end)
  save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_channel_config)
end

function channel_edit_page_ui_controller.handle_midi_config_page_decrement()
  if midi_device_vertical_scroll_selector:is_selected() then
    midi_device_vertical_scroll_selector:scroll_up()
  elseif midi_channel_vertical_scroll_selector:is_selected() then
    midi_channel_vertical_scroll_selector:scroll_up()
  elseif device_map_vertical_scroll_selector:is_selected() then
    device_map_vertical_scroll_selector:scroll_up()
  end

  local device = fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)

  save_confirm.clear()

  save_confirm.set_save(function()
    channel_edit_page_ui_controller.update_channel_config()
    param_manager.update_default_params(program.get_selected_channel(), device)
    param_select_vertical_scroll_selector:set_selected_item(1)
    channel_edit_page_ui_controller.refresh_trig_locks()
  end)

  save_confirm.set_cancel(function()
    channel_edit_page_ui_controller.refresh_channel_config()
  end)
end

function channel_edit_page_ui_controller.handle_encoder_one_positive()
  if program.get().selected_channel ~= 17 then
    channel_edit_page_ui_controller.select_channel_page_by_index((channel_pages:get_selected_page() or 1) + 1)
  else
    channel_edit_page_ui_controller.select_scale_page_by_index((scales_pages:get_selected_page() or 1) + 1)
  end
  fn.dirty_screen(true)
  save_confirm.cancel()
end

function channel_edit_page_ui_controller.handle_encoder_one_negative()
  if program.get().selected_channel ~= 17 then
    channel_edit_page_ui_controller.select_channel_page_by_index((channel_pages:get_selected_page() or 1) - 1)

  else
    channel_edit_page_ui_controller.select_scale_page_by_index((scales_pages:get_selected_page() or 1) - 1)
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
        tooltip:show("Masks for ch " .. program.get_selected_channel() .. " cleared")
        channel_edit_page_ui_controller.refresh_masks()
        pattern_controller.update_working_pattern(program.get_selected_channel().number)
      end
      if channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] then
        program.clear_trig_locks_for_step(step)
        tooltip:show("Trig locks for step " .. step .. " cleared")
        channel_edit_page_ui_controller.refresh_trig_locks()
      end
    end
  else
    if channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] then
      if is_key3_down then
        program.clear_trig_locks_for_channel(program.get_selected_channel())
        tooltip:show("Trig locks for ch " .. program.get_selected_channel().number .. " cleared")
        channel_edit_page_ui_controller.refresh_trig_locks()
      else
        if not trig_lock_page:is_sub_page_enabled() then
          channel_edit_page_ui_controller.refresh_device_selector()
          channel_edit_page_ui_controller.refresh_param_list()
        end
        channel_edit_page_ui_controller.refresh_channel_config()
        trig_lock_page:toggle_sub_page()
      end
    elseif channel_pages:get_selected_page() == channel_page_to_index["Masks"] then
      if is_key3_down then
        program.clear_masks_for_channel(program.get_selected_channel())
        tooltip:show("Masks for ch " .. program.get_selected_channel().number .. " cleared")
        channel_edit_page_ui_controller.refresh_masks()
        pattern_controller.update_working_pattern(program.get_selected_channel().number)
      end
    end
    save_confirm.cancel()
  end
end

function channel_edit_page_ui_controller.handle_key_three_pressed()
  local pressed_keys = grid_controller.get_pressed_keys()
  if #pressed_keys < 1 then
    save_confirm.confirm()
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
  channel_edit_page_ui_controller.refresh_masks()
  channel_pages:select_page(channel_page_to_index["Masks"])
  fn.dirty_screen(true)
end

function channel_edit_page_ui_controller.select_trig_page()
  channel_edit_page_ui_controller.refresh_trig_locks()
  channel_pages:select_page(channel_page_to_index["Trig Locks"])
end

function channel_edit_page_ui_controller.select_scales_page()
  channel_edit_page_ui_controller.refresh_quantiser()
  channel_edit_page_ui_controller.refresh_romans()
  channel_pages:select_page(channel_page_to_index["Scales"])
end

function channel_edit_page_ui_controller.select_clock_mods_page()
  channel_edit_page_ui_controller.refresh_clock_mods()
  channel_edit_page_ui_controller.refresh_swing()
  channel_edit_page_ui_controller.refresh_swing_shuffle_type()
  channel_edit_page_ui_controller.refresh_shuffle_feel()
  channel_edit_page_ui_controller.refresh_shuffle_basis()
  channel_edit_page_ui_controller.refresh_shuffle_amount()
  channel_pages:select_page(channel_page_to_index["Clock Mods"])
end

function channel_edit_page_ui_controller.select_midi_config_page()
  channel_edit_page_ui_controller.refresh_channel_config()
  channel_pages:select_page(channel_page_to_index["Midi Config"])
end

function channel_edit_page_ui_controller.select_quantizer_page()
  channel_edit_page_ui_controller.refresh_quantiser()
  channel_edit_page_ui_controller.refresh_romans()
  channel_pages:select_page(channel_page_to_index["Quantizer"])
end

function channel_edit_page_ui_controller.select_note_dashboard_page()
  channel_pages:select_page(channel_page_to_index["Note Dashboard"])
end


function channel_edit_page_ui_controller.select_scales_quantizer_page()
  channel_edit_page_ui_controller.refresh_quantiser()
  channel_edit_page_ui_controller.refresh_romans()
  scales_pages:select_page(scales_page_to_index["Quantizer"])
end

function channel_edit_page_ui_controller.select_scales_clock_mods_page()
  channel_edit_page_ui_controller.refresh_clock_mods()
  channel_edit_page_ui_controller.refresh_swing()
  channel_edit_page_ui_controller.refresh_swing_shuffle_type()
  channel_edit_page_ui_controller.refresh_shuffle_feel()
  channel_edit_page_ui_controller.refresh_shuffle_basis()
  channel_edit_page_ui_controller.refresh_shuffle_amount()
  scales_pages:select_page(scales_page_to_index["Clock Mods"])
end

function channel_edit_page_ui_controller.select_channel_page_by_index(index)
  if index == 1 then
    channel_edit_page_ui_controller.select_note_dashboard_page()
  elseif index == 2 then
    channel_edit_page_ui_controller.select_mask_page()
  elseif index == 3 then
    channel_edit_page_ui_controller.select_trig_page()
  elseif index == 4 then
    channel_edit_page_ui_controller.select_clock_mods_page()
  elseif index == 5 then
    channel_edit_page_ui_controller.select_midi_config_page()
  end
end

function channel_edit_page_ui_controller.select_scale_page_by_index(index)
  if index == 1 then
    channel_edit_page_ui_controller.select_scales_quantizer_page()
  elseif index == 2 then
    channel_edit_page_ui_controller.select_scales_clock_mods_page()
  end
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
      elseif note_displays.chords[i]:get_value() ~= -1 then
        note_displays.chords[i]:set_value(note_displays.chords[i]:get_value())
      else
        note_displays.chords[i]:set_value(-1)
      end
    end
  end
end

return channel_edit_page_ui_controller
