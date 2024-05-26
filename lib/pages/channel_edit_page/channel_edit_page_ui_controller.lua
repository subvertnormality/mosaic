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

-- Value selectors with initial values
local mask_selectors = {
  trig = value_selector:new(5, 18, "Trig", -1, 1),
  note = value_selector:new(30, 18, "Note", -1, 127),
  velocity = value_selector:new(55, 18, "Vel", -1, 127),
  length = value_selector:new(80, 18, "Len", -1, 512),
  chords = {
    value_selector:new(5, 40, "Chd1", -14, 14),
    value_selector:new(30, 40, "Chd2", -14, 14),
    value_selector:new(55, 40, "Chd3", -14, 14),
    value_selector:new(80, 40, "Chd4", -14, 14)
  }
}

-- Clock and MIDI selectors
local clock_mod_list_selector = list_selector:new(5, 25, "Clock Mod", {})
local clock_swing_value_selector = value_selector:new(55, 25, "Swing", 0, 100)
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
  table.insert(m_params, dial:new(5 + (i - 1) % 5 * 25, 18 + math.floor((i - 1) / 5) * 22, "Param " .. i, "param_" .. i, "X", ""))
end

-- Page indices
local channel_page_to_index = {["Notes"] = 1, ["Trig Locks"] = 2, ["Clock Mods"] = 3, ["Midi Config"] = 4}
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
configure_note_value_selector(mask_selectors.note)
configure_note_page_velocity_length_value_selector(mask_selectors.velocity)
configure_note_page_velocity_length_value_selector(mask_selectors.length)
for _, chord_selector in ipairs(mask_selectors.chords) do
  configure_chord_value_selector(chord_selector)
end
configure_note_trig_selector(mask_selectors.trig)

-- Page definitions
local notes_page = page:new("Note Masks", function()
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
    clock_swing_value_selector:draw()
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
  clock_swing_value_selector:set_value(50)

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

function channel_edit_page_ui_controller.update_swing()
  local channel = program.get_selected_channel()
  local swing = clock_swing_value_selector:get_value()
  channel.swing = swing
  clock_controller.set_channel_swing(channel.number, swing)
end

function channel_edit_page_ui_controller.update_clock_mods()
  local channel = program.get_selected_channel()
  local clock_mods = clock_mod_list_selector:get_selected()
  channel.clock_mods = clock_mods
  clock_controller.set_channel_division(channel.number, clock_controller.calculate_divisor(clock_mods))
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
    channel.trig_lock_banks[dial_index] = channel.trig_lock_banks[dial_index] + direction
    if channel.trig_lock_banks[dial_index] > (channel.trig_lock_params[dial_index].cc_max_value or 127) then
      channel.trig_lock_banks[dial_index] = (channel.trig_lock_params[dial_index].cc_max_value or 127)
    elseif channel.trig_lock_banks[dial_index] < (channel.trig_lock_params[dial_index].cc_min_value or -1) then
      channel.trig_lock_banks[dial_index] = (channel.trig_lock_params[dial_index].cc_min_value or -1)
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
      if d > 0 then
        if program.get().selected_channel ~= 17 and channel_pages:get_selected_page() == channel_page_to_index["Notes"] then
          channel_edit_page_ui_controller.handle_note_page_increment()
        elseif program.get().selected_channel == 17 and scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] then
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
        if channel_pages:get_selected_page() == channel_page_to_index["Notes"] and program.get().selected_channel ~= 17 then
          channel_edit_page_ui_controller.handle_note_page_decrement()
        elseif scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] and program.get().selected_channel == 17 then
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
        channel_edit_page_ui_handlers.handle_encoder_two_positive(channel_pages, channel_page_to_index, scales_pages, scales_page_to_index, mask_selectors, quantizer_vertical_scroll_selector, romans_vertical_scroll_selector, notes_vertical_scroll_selector, rotation_vertical_scroll_selector, clock_mod_list_selector, clock_swing_value_selector, midi_device_vertical_scroll_selector, midi_channel_vertical_scroll_selector, device_map_vertical_scroll_selector, dials, trig_lock_page)
      else
        channel_edit_page_ui_handlers.handle_encoder_two_negative(channel_pages, channel_page_to_index, scales_pages, scales_page_to_index, mask_selectors, quantizer_vertical_scroll_selector, romans_vertical_scroll_selector, notes_vertical_scroll_selector, rotation_vertical_scroll_selector, clock_mod_list_selector, clock_swing_value_selector, midi_device_vertical_scroll_selector, midi_channel_vertical_scroll_selector, device_map_vertical_scroll_selector, dials, trig_lock_page)
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
function channel_edit_page_ui_controller.refresh_notes()
  channel_edit_page_ui_refreshers.refresh_notes(mask_selectors)
end

function channel_edit_page_ui_controller.refresh_clock_mods()
  channel_edit_page_ui_refreshers.refresh_clock_mods(clock_mod_list_selector, clock_swing_value_selector)
end

function channel_edit_page_ui_controller.refresh_swing()
  channel_edit_page_ui_refreshers.refresh_swing(clock_swing_value_selector)
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
  channel_edit_page_ui_controller.refresh_notes()
  channel_edit_page_ui_controller.refresh_trig_locks()
  channel_edit_page_ui_controller.refresh_quantiser()
  channel_edit_page_ui_controller.refresh_romans()
  channel_edit_page_ui_controller.refresh_clock_mods()
  channel_edit_page_ui_controller.refresh_swing()
end

-- Handlers for specific actions
function channel_edit_page_ui_controller.handle_note_page_increment()
  local pressed_keys = grid_controller.get_pressed_keys()
  if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
    for _, keys in ipairs(pressed_keys) do
      local step = fn.calc_grid_count(keys[1], keys[2])
      if mask_selectors.trig:is_selected() then
        mask_selectors.trig:increment()
        program.get_selected_channel().step_trig_masks[step] = mask_selectors.trig:get_value()
      end
      if mask_selectors.note:is_selected() then
        mask_selectors.note:increment()
        program.get_selected_channel().step_note_masks[step] = mask_selectors.note:get_value()
      end
      if mask_selectors.velocity:is_selected() then
        mask_selectors.velocity:increment()
        program.get_selected_channel().step_velocity_masks[step] = mask_selectors.velocity:get_value()
      end
      if mask_selectors.length:is_selected() then
        mask_selectors.length:increment()
        program.get_selected_channel().step_length_masks[step] = mask_selectors.length:get_value()
      end
      for i, chord_selector in ipairs(mask_selectors.chords) do
        if chord_selector:is_selected() then
          chord_selector:increment()
          program.get_selected_channel().step_chord_masks[step][i] = chord_selector:get_value()
        end
      end
    end
  end
end

function channel_edit_page_ui_controller.handle_note_page_decrement()
  local pressed_keys = grid_controller.get_pressed_keys()
  if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
    for _, keys in ipairs(pressed_keys) do
      local step = fn.calc_grid_count(keys[1], keys[2])
      if mask_selectors.trig:is_selected() then
        mask_selectors.trig:decrement()
        local value = mask_selectors.trig:get_value()
        program.get_selected_channel().step_trig_masks[step] = value == -1 and nil or value
      end
      if mask_selectors.note:is_selected() then
        mask_selectors.note:decrement()
        local value = mask_selectors.note:get_value()
        program.get_selected_channel().step_note_masks[step] = value == -1 and nil or value
      end
      if mask_selectors.velocity:is_selected() then
        mask_selectors.velocity:decrement()
        local value = mask_selectors.velocity:get_value()
        program.get_selected_channel().step_velocity_masks[step] = value == -1 and nil or value
      end
      if mask_selectors.length:is_selected() then
        mask_selectors.length:decrement()
        local value = mask_selectors.length:get_value()
        program.get_selected_channel().step_length_masks[step] = value < 1 and nil or value
        mask_selectors.length:set_value(value < 1 and -1 or value)
      end
      for i, chord_selector in ipairs(mask_selectors.chords) do
        if chord_selector:is_selected() then
          chord_selector:decrement()
          local value = chord_selector:get_value()
          if not program.get_selected_channel().step_chord_masks[step] then
            program.get_selected_channel().step_chord_masks[step] = {}
          end
          program.get_selected_channel().step_chord_masks[step][i] = value < -14 or value == 0 and nil or value
        end
      end
    end
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
  if clock_mod_list_selector:is_selected() then
    clock_mod_list_selector:decrement()
    save_confirm.set_save(channel_edit_page_ui_controller.update_clock_mods)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_clock_mods)
  elseif clock_swing_value_selector:is_selected() then
    clock_swing_value_selector:increment()
    save_confirm.set_save(channel_edit_page_ui_controller.update_swing)
    save_confirm.set_cancel(channel_edit_page_ui_controller.refresh_swing)
  end
end

function channel_edit_page_ui_controller.handle_clock_mods_page_decrement()
  if clock_mod_list_selector:is_selected() then
    clock_mod_list_selector:increment()
    save_confirm.set_save(function()
      channel_edit_page_ui_controller.update_clock_mods()
    end)
    save_confirm.set_cancel(function()
      channel_edit_page_ui_controller.refresh_clock_mods()
    end)
  elseif clock_swing_value_selector:is_selected() then
    clock_swing_value_selector:decrement()
    save_confirm.set_save(function()
      channel_edit_page_ui_controller.update_swing()
    end)
    save_confirm.set_cancel(function()
      channel_edit_page_ui_controller.refresh_swing()
    end)
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
      if channel_pages:get_selected_page() == channel_page_to_index["Notes"] then
        program.clear_masks_for_step(step)
        channel_edit_page_ui_controller.refresh_notes()
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

function channel_edit_page_ui_controller.set_current_note(note)
  local pressed_keys = grid_controller.get_pressed_keys()
  if #pressed_keys > 0 then
    if (pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8) then
      return
    end
  end
  mask_selectors.note:set_value(note.note)
  mask_selectors.velocity:set_value(note.velocity)
  mask_selectors.length:set_value(note.length)
end

function channel_edit_page_ui_controller.sync_param_to_trig_lock(i, channel)

  if not channel.trig_lock_banks[i] then
    return
  end
  
  local param_id = channel.trig_lock_params[i].param_id


  local p = nil
  if param_id ~= nil then
    p = params:lookup_param(channel.trig_lock_params[i].param_id)
    params:set(param_id, channel.trig_lock_banks[i])
  end
end


return channel_edit_page_ui_controller
