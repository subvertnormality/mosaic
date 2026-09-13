local midi_value_domain = include("mosaic/lib/devices/midi_value_domain")
-- channel_edit_page_ui.lua
local channel_edit_page_ui = {}

-- Include necessary modules

local quantiser = include("mosaic/lib/quantiser")
local pages = include("mosaic/lib/ui_components/pages")
local page = include("mosaic/lib/ui_components/page")
local vertical_scroll_selector = include("mosaic/lib/ui_components/vertical_scroll_selector")
local dial = include("mosaic/lib/ui_components/dial")
local control_scroll_selector = include("mosaic/lib/ui_components/control_scroll_selector")
local list_selector = include("mosaic/lib/ui_components/list_selector")
local value_selector = include("mosaic/lib/ui_components/value_selector")
local memory_history_navigator = include("mosaic/lib/ui_components/memory_history_navigator")
local m_midi = include("mosaic/lib/m_midi")
local musicutil = require("musicutil")
local param_manager = include("mosaic/lib/devices/param_manager")
local divisions = include("mosaic/lib/clock/divisions")
local channel_edit_page_ui_handlers = include("mosaic/lib/pages/channel_edit_page/channel_edit_page_ui_handlers")
local channel_edit_page_ui_handlers = include("mosaic/lib/pages/channel_edit_page/channel_edit_page_ui_handlers")
local channel_edit_page_ui_refreshers = include("mosaic/lib/pages/channel_edit_page/channel_edit_page_ui_refreshers")
local channel_edit_masks = include("mosaic/lib/pages/channel_edit_page/channel_edit_masks")
local channel_edit_history = include("mosaic/lib/pages/channel_edit_page/channel_edit_history")
local channel_edit_parameters = include("mosaic/lib/pages/channel_edit_page/channel_edit_parameters")
local channel_edit_clock_controls = include("mosaic/lib/pages/channel_edit_page/channel_edit_clock_controls")

-- UI components
local channel_pages = pages:new()

local swing_shuffle_type_selector = list_selector:new(70, 18, "Swing Type", {{name = "X", value = 1}, {name = "Swing", value = 2}, {name = "Shuffle", value = 3}})
local swing_selector = value_selector:new(0, 40, "Swing", -51, 50)
local shuffle_feel_selector = list_selector:new(0, 40, "Feel", {{name = "X", value = 1}, {name = "Drunk", value = 2}, {name = "Smooth", value = 3}, {name = "Heavy", value = 4}, {name = "Clave", value = 5}})
local shuffle_basis_selector = list_selector:new(40, 40, "Basis", {{name = "X", value = 1}, {name = "9", value = 2}, {name = "7", value = 3}, {name = "5", value = 4}, {name = "6", value = 5}, {name = "8??", value = 6}, {name = "9??", value = 7}})
local shuffle_amount_selector = value_selector:new(70, 40, "Amount", 0, 100)

local channel_edit_clock_controls_controller

function channel_edit_page_ui.get_swing_shuffle_type_selector_value()
  return channel_edit_clock_controls_controller.get_swing_shuffle_type_selector_value()
end

function channel_edit_page_ui.get_shuffle_feel_selector_value()
  return channel_edit_clock_controls_controller.get_shuffle_feel_selector_value()
end

function channel_edit_page_ui.get_shuffle_basis_selector_value()
  return channel_edit_clock_controls_controller.get_shuffle_basis_selector_value()
end

function channel_edit_page_ui.set_swing_shuffle_type_selector_value(value)
  return channel_edit_clock_controls_controller.set_swing_shuffle_type_selector_value(value)
end

function channel_edit_page_ui.set_shuffle_feel_selector_value(value)
  return channel_edit_clock_controls_controller.set_shuffle_feel_selector_value(value)
end

function channel_edit_page_ui.set_shuffle_basis_selector_value(value)
  return channel_edit_clock_controls_controller.set_shuffle_basis_selector_value(value)
end

-- Value selectors with initial values
local mask_selectors = {
  trig = value_selector:new(0 + (1 - 1) % 5 * 25, 18 + math.floor((1 - 1) / 5) * 22, "Trig", -1, 1),
  note = value_selector:new(0 + (2 - 1) % 5 * 25, 18 + math.floor((2 - 1) / 5) * 22, "Note", -1, 127),
  velocity = value_selector:new(0 + (3 - 1) % 5 * 25, 18 + math.floor((3 - 1) / 5) * 22, "Vel", -1, 127),
  length = value_selector:new(0 + (4 - 1) % 5 * 25, 18 + math.floor((4 - 1) / 5) * 22, "Len", 0, #divisions.note_divisions),
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

-- Trig Dials
local dials = control_scroll_selector:new(0, 0, {})
local m_params = {}
for i = 1, 10 do
  table.insert(m_params, dial:new(0 + (i - 1) % 5 * 25, 18 + math.floor((i - 1) / 5) * 22, "Param " .. i, "param_" .. i, "None", "X"))
end

local channel_edit_parameters_controller = channel_edit_parameters.new(
  {
    dials = dials,
    m_params = m_params,
    midi_device_vertical_scroll_selector = midi_device_vertical_scroll_selector,
    midi_channel_vertical_scroll_selector = midi_channel_vertical_scroll_selector,
    param_select_vertical_scroll_selector = param_select_vertical_scroll_selector,
    device_map_vertical_scroll_selector = device_map_vertical_scroll_selector
  },
  channel_edit_page_ui,
  channel_edit_page_ui_refreshers,
  {param_manager = param_manager, midi_value_domain = midi_value_domain}
)

channel_edit_clock_controls_controller = channel_edit_clock_controls.new(
  {
    clock_mod_list_selector = clock_mod_list_selector,
    swing_shuffle_type_selector = swing_shuffle_type_selector,
    swing_selector = swing_selector,
    shuffle_feel_selector = shuffle_feel_selector,
    shuffle_basis_selector = shuffle_basis_selector,
    shuffle_amount_selector = shuffle_amount_selector
  },
  channel_edit_page_ui,
  channel_edit_page_ui_refreshers
)

-- History controls
local channel_edit_history_controller = channel_edit_history.new(memory_history_navigator, channel_edit_page_ui)
local memory_controls = {
  navigator = channel_edit_history_controller.navigator
}

-- Page indices
local channel_page_to_index = {["Masks"] = 1, ["Trig Locks"] = 2, ["Memory"] = 3, ["Clock Mods"] = 4, ["Midi Config"] = 5, ["Note Dashboard"] = 6}
local index_to_channel_page = {"Masks", "Trig Locks", "Memory", "Clock Mods", "Midi Config", "Note Dashboard"}

-- Helper variables
local refresh_timer_id = nil
local throttle_time = 0.2


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
configure_note_page_velocity_length_value_selector(note_displays.velocity)
configure_note_page_velocity_length_value_selector(note_displays.length)
configure_note_value_selector(note_displays.chords[1])
configure_note_value_selector(note_displays.chords[2])
configure_note_value_selector(note_displays.chords[3])
configure_note_value_selector(note_displays.chords[4])
-- Chord slots start as "no note played" (X), not MIDI note 0 (bugs.json dashboard-chord-slots).
for _, chord_display in ipairs(note_displays.chords) do chord_display.value = -1 end
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
end)


local memory_page = page:new("Memory", function()
  channel_edit_history_controller.draw()
end)

local mask_page = page:new("Note Masks", function()
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
end)


local clock_mods_page = page:new("Clocks", function()
  channel_edit_clock_controls_controller.draw()
end)

local channel_edit_page = page:new("Device Config", function()
  local channel = program.get_selected_channel()
  local device = fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)
  if device.type == "midi" then
    if device.default_midi_device == nil and m_midi.midi_devices_connected() then
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
end)

local trig_lock_page = page:new("Trig Locks", function()
  channel_edit_parameters_controller.draw_trig_locks()
end)

-- Initialization function
function channel_edit_page_ui.init()
  mask_selectors.note:select()
  midi_channel_vertical_scroll_selector:select()
  midi_device_vertical_scroll_selector:set_items(m_midi.get_midi_outs())
  dials:set_items(m_params)

  for i, dial in ipairs(dials:get_items()) do
    dial:set_display_modifier(function(x, y)
      local pressed_keys = m_grid.get_pressed_keys()
      
      if program.get_channel_param_slide(program.get_selected_channel(), i) then
        -- Draw top line
        screen.move(x-1, y-6) 
        screen.line(x+23, y-6)
        screen.stroke()
        -- Draw right line
        screen.move(x+23, y-6)  
        screen.line(x+23, y+13)  
        screen.stroke()
      elseif #pressed_keys > 0 then
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          if program.get_step_param_slide(program.get_selected_channel(), s, i) then
            -- Draw top line
            screen.move(x, y-6)  
            screen.line(x+23, y-6)  
            screen.stroke()
            -- Draw right line
            screen.move(x+23, y-6)  
            screen.line(x+23, y+13)  
            screen.stroke()
          end
        end
      end
    end)
  end


  channel_edit_clock_controls_controller.initialize_clock_mod_list()
  device_map_vertical_scroll_selector = vertical_scroll_selector:new(5, 25, "Midi Map", device_map:get_devices())
  channel_edit_parameters_controller.set_device_map_selector(device_map_vertical_scroll_selector)
  channel_edit_parameters_controller.set_trig_lock_page(trig_lock_page)

  local function set_sub_name_func(page, func)
    page:set_sub_name_func(func)
  end

  set_sub_name_func(notes_page, function()
    return "Ch. " .. program.get().selected_channel .. " " or ""
  end)

  set_sub_name_func(memory_page, function()
    return "Ch. " .. program.get().selected_channel .. " " or ""
  end)

  set_sub_name_func(mask_page, function()
    return "Ch. " .. program.get().selected_channel .. " " or ""
  end)

  set_sub_name_func(channel_edit_page, function()
    return "Ch. " .. program.get().selected_channel .. " " or ""
  end)

  set_sub_name_func(clock_mods_page, function()
    return "Ch. " .. program.get().selected_channel .. " " or ""
  end)

  set_sub_name_func(trig_lock_page, function()
    return "Ch. " .. program.get().selected_channel .. " " or ""
  end)

  trig_lock_page:set_sub_page_draw_func(function()
    channel_edit_parameters_controller.draw_assignment_subpage()
  end)

  channel_pages:add_page(mask_page)
  channel_pages:add_page(trig_lock_page)
  channel_pages:add_page(memory_page)
  channel_pages:add_page(clock_mods_page)
  channel_pages:add_page(channel_edit_page)
  channel_pages:add_page(notes_page)


  channel_edit_page_ui.select_mask_page()

  dials:set_selected_item(1)
  channel_edit_clock_controls_controller.initialize_values()

  channel_edit_history_controller.initialize()

  channel_edit_page_ui.refresh_clock_mods()
end

-- Register UI draw handlers
function channel_edit_page_ui.register_ui_draws()
  draw:register_ui("channel_edit_page", function()
    channel_pages:draw()
  end)
end

-- Update functions
function channel_edit_page_ui.update_swing_shuffle_type()
  return channel_edit_clock_controls_controller.update_swing_shuffle_type()
end

function channel_edit_page_ui.align_global_and_local_swing_shuffle_type_values(c)
  return channel_edit_clock_controls_controller.align_global_and_local_swing_shuffle_type_values(c)
end

function channel_edit_page_ui.update_swing()
  return channel_edit_clock_controls_controller.update_swing()
end

function channel_edit_page_ui.align_global_and_local_swing_values(c)
  return channel_edit_clock_controls_controller.align_global_and_local_swing_values(c)
end

function channel_edit_page_ui.update_shuffle_feel()
  return channel_edit_clock_controls_controller.update_shuffle_feel()
end

function channel_edit_page_ui.align_global_and_local_shuffle_feel_values(c)
  return channel_edit_clock_controls_controller.align_global_and_local_shuffle_feel_values(c)
end

function channel_edit_page_ui.update_shuffle_basis()
  return channel_edit_clock_controls_controller.update_shuffle_basis()
end

function channel_edit_page_ui.align_global_and_local_shuffle_basis_values(c)
  return channel_edit_clock_controls_controller.align_global_and_local_shuffle_basis_values(c)
end

function channel_edit_page_ui.update_shuffle_amount()
  return channel_edit_clock_controls_controller.update_shuffle_amount()
end

function channel_edit_page_ui.align_global_and_local_shuffle_amount_values(c)
  return channel_edit_clock_controls_controller.align_global_and_local_shuffle_amount_values(c)
end

function channel_edit_page_ui.update_clock_mods()
  return channel_edit_clock_controls_controller.update_clock_mods()
end

function channel_edit_page_ui.update_channel_config()
  return channel_edit_parameters_controller.update_channel_config()
end

function channel_edit_page_ui.handle_trig_lock_param_change_by_direction(direction, channel, dial_index)
  return channel_edit_parameters_controller.handle_trig_lock_param_change_by_direction(direction, channel, dial_index)
end

-- Encoder and key handling
function channel_edit_page_ui.enc(n, d)
  local channel = program.get_selected_channel()
  if n == 3 then
    for _ = 1, math.abs(d) do
      if channel_pages:get_selected_page() == channel_page_to_index["Masks"] then
        channel_edit_page_ui.handle_mask_page_change(d)
      elseif channel_pages:get_selected_page() == channel_page_to_index["Memory"] then
        channel_edit_page_ui.handle_memory_page_change(d)
      end
      if d > 0 then
        if channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] then
          channel_edit_page_ui.handle_clock_mods_page_increment()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] then
          channel_edit_page_ui.handle_midi_config_page_increment()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] then
          channel_edit_page_ui_handlers.handle_trig_locks_page_change(d, channel_edit_parameters_controller)
        end
      else
        if channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] then
          channel_edit_page_ui.handle_clock_mods_page_decrement()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] then
          channel_edit_page_ui.handle_midi_config_page_decrement()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] then
          channel_edit_page_ui_handlers.handle_trig_locks_page_change(d, channel_edit_parameters_controller)
        end
      end
    end
  elseif n == 2 then
    for _ = 1, math.abs(d) do
      
      local pages = {
        channel_pages = channel_pages,
        channel_page_to_index = channel_page_to_index
      }

      local selectors = {
        mask_selectors = mask_selectors,
        clock_mod_list_selector = clock_mod_list_selector,
        midi_device_vertical_scroll_selector = midi_device_vertical_scroll_selector,
        midi_channel_vertical_scroll_selector = midi_channel_vertical_scroll_selector,
        device_map_vertical_scroll_selector = device_map_vertical_scroll_selector,
        swing_shuffle_type_selector = swing_shuffle_type_selector,
        swing_selector = swing_selector,
        shuffle_feel_selector = shuffle_feel_selector,
        shuffle_basis_selector = shuffle_basis_selector,
        shuffle_amount_selector = shuffle_amount_selector,
        memory_controls = memory_controls,
      }

      if d > 0 then
        channel_edit_page_ui_handlers.handle_encoder_two_positive(pages, selectors, dials, trig_lock_page, channel_edit_parameters_controller, channel_edit_clock_controls_controller)
      else
        channel_edit_page_ui_handlers.handle_encoder_two_negative(pages, selectors, dials, trig_lock_page, channel_edit_parameters_controller, channel_edit_clock_controls_controller)
      end
    end
  elseif n == 1 then
    for _ = 1, math.abs(d) do
      if d > 0 then
        channel_edit_page_ui.handle_encoder_one_positive()
      else
        channel_edit_page_ui.handle_encoder_one_negative()
      end
    end
  end
end

function channel_edit_page_ui.key(n, z)
  if n == 2 and z == 1 then
    channel_edit_page_ui.handle_key_two_pressed()
  elseif n == 3 and z == 1 then
    channel_edit_page_ui.handle_key_three_pressed()
  end
end

-- Refresh functions
function channel_edit_page_ui.refresh_masks()
  channel_edit_page_ui_refreshers.refresh_masks(mask_selectors)
end

function channel_edit_page_ui.refresh_clock_mods()
  return channel_edit_clock_controls_controller.refresh_clock_mods()
end

function channel_edit_page_ui.refresh_swing()
  return channel_edit_clock_controls_controller.refresh_swing()
end

function channel_edit_page_ui.refresh_swing_shuffle_type()
  return channel_edit_clock_controls_controller.refresh_swing_shuffle_type()
end

function channel_edit_page_ui.refresh_shuffle_feel()
  return channel_edit_clock_controls_controller.refresh_shuffle_feel()
end

function channel_edit_page_ui.refresh_shuffle_basis()
  return channel_edit_clock_controls_controller.refresh_shuffle_basis()
end

function channel_edit_page_ui.refresh_shuffle_amount()
  return channel_edit_clock_controls_controller.refresh_shuffle_amount()
end

function channel_edit_page_ui.refresh_device_selector()
  return channel_edit_parameters_controller.refresh_device_selector()
end
function channel_edit_page_ui.refresh_trig_lock_value(i)
  return channel_edit_parameters_controller.refresh_trig_lock_value(i)
end
function channel_edit_page_ui.refresh_trig_lock_values()
  return channel_edit_parameters_controller.refresh_trig_lock_values()
end
function channel_edit_page_ui.refresh_trig_locks()
  return channel_edit_parameters_controller.refresh_trig_locks()
end
function channel_edit_page_ui.refresh_param_list()
  return channel_edit_parameters_controller.refresh_param_list()
end
function channel_edit_page_ui.refresh_memory()
  return channel_edit_history_controller.refresh()
end

channel_edit_page_ui.refresh_channel_config = channel_edit_parameters_controller.create_config_refresh()


function channel_edit_page_ui.refresh()
  channel_edit_page_ui.select_channel_page_by_index(channel_pages:get_selected_page() or 1)
end

function channel_edit_page_ui.handle_memory_navigator(c, d)
  return channel_edit_history_controller.navigate(c, d)
end
-- (bugs.json held-mask-extra-key).
local mask_handlers = channel_edit_masks.new(mask_selectors, channel_edit_page_ui, divisions)

function channel_edit_page_ui.handle_trig_mask_change(channel, direction, song_pattern_number)
  return mask_handlers.handle_trig_mask_change(channel, direction, song_pattern_number)
end

function channel_edit_page_ui.handle_note_mask_change(channel, direction, song_pattern_number)
  return mask_handlers.handle_note_mask_change(channel, direction, song_pattern_number)
end

function channel_edit_page_ui.handle_velocity_mask_change(channel, direction, song_pattern_number)
  return mask_handlers.handle_velocity_mask_change(channel, direction, song_pattern_number)
end

function channel_edit_page_ui.handle_length_mask_change(channel, direction, song_pattern_number)
  return mask_handlers.handle_length_mask_change(channel, direction, song_pattern_number)
end

function channel_edit_page_ui.handle_chord_mask_one_change(channel, direction, song_pattern_number)
  return mask_handlers.handle_chord_mask_one_change(channel, direction, song_pattern_number)
end

function channel_edit_page_ui.handle_chord_mask_two_change(channel, direction, song_pattern_number)
  return mask_handlers.handle_chord_mask_two_change(channel, direction, song_pattern_number)
end

function channel_edit_page_ui.handle_chord_mask_three_change(channel, direction, song_pattern_number)
  return mask_handlers.handle_chord_mask_three_change(channel, direction, song_pattern_number)
end

function channel_edit_page_ui.handle_chord_mask_four_change(channel, direction, song_pattern_number)
  return mask_handlers.handle_chord_mask_four_change(channel, direction, song_pattern_number)
end

function channel_edit_page_ui.handle_mask_page_change(direction)
  return mask_handlers.handle_mask_page_change(direction)
end


function channel_edit_page_ui.handle_memory_page_change(d)
  return channel_edit_history_controller.handle_page_change(d)
end
function channel_edit_page_ui.handle_clock_mods_page_increment()
  return channel_edit_clock_controls_controller.handle_increment()
end

function channel_edit_page_ui.handle_clock_mods_page_decrement()
  return channel_edit_clock_controls_controller.handle_decrement()
end

function channel_edit_page_ui.handle_midi_config_page_increment()
  return channel_edit_parameters_controller.handle_midi_config_page_increment()
end

function channel_edit_page_ui.handle_midi_config_page_decrement()
  return channel_edit_parameters_controller.handle_midi_config_page_decrement()
end

function channel_edit_page_ui.handle_encoder_one_positive()

  channel_edit_page_ui.select_channel_page_by_index((channel_pages:get_selected_page() or 1) + 1)
  fn.dirty_screen(true)
  save_confirm.cancel()
end

function channel_edit_page_ui.handle_encoder_one_negative()
  channel_edit_page_ui.select_channel_page_by_index((channel_pages:get_selected_page() or 1) - 1)
  fn.dirty_screen(true)
  save_confirm.cancel()
end

function channel_edit_page_ui.handle_key_two_pressed()
  local pressed_keys = m_grid.get_pressed_keys()
  if #pressed_keys > 0 then
    local selected = program.get()
    local song_pattern = selected.selected_song_pattern or 1
    if not selected.selected_song_pattern then selected.selected_song_pattern = song_pattern end
    local channel = program.get_channel(song_pattern, selected.selected_channel)
    for _, keys in ipairs(pressed_keys) do
      local s = fn.calc_grid_count(keys[1], keys[2])
      if channel_pages:get_selected_page() == channel_page_to_index["Masks"] then
        program.clear_masks_for_step_for_channel(channel, s)
        tooltip:show("Masks for step " .. s .. " cleared")
        channel_edit_page_ui.refresh_masks()
        pattern.update_working_pattern(channel.number, program.get_song_pattern(song_pattern))
      end
      if channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] then
        program.clear_trig_locks_for_step_for_channel(channel, s)
        tooltip:show("Trig locks for step " .. s .. " cleared")
        channel_edit_page_ui.refresh_trig_locks()
      end
    end
  else
    if channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] then
      if is_key1_down then
        program.clear_trig_locks_for_channel(program.get_selected_channel())
        tooltip:show("Trig locks for ch " .. program.get_selected_channel().number .. " cleared")
        channel_edit_page_ui.refresh_trig_locks()
      else
        channel_edit_parameters_controller.toggle_assignment_subpage()
      end
    elseif channel_pages:get_selected_page() == channel_page_to_index["Masks"] then
      if is_key1_down then
        program.clear_masks_for_channel(program.get_selected_channel())
        tooltip:show("Masks for ch " .. program.get_selected_channel().number .. " cleared")
        channel_edit_page_ui.refresh_masks()
        pattern.update_working_pattern(program.get_selected_channel().number, program.get_selected_song_pattern())
      end
    elseif channel_pages:get_selected_page() == channel_page_to_index["Memory"] then
      if is_key1_down then
        memory.undo_all(program.get_selected_channel().number)
        memory.clear(program.get_selected_channel().number)
        tooltip:show("Memory undone and forgotten")
      else
        memory.undo_all(program.get_selected_channel().number)
        tooltip:show("Ch. " .. program.get_selected_channel().number .. " memory undone")
      end
      channel_edit_page_ui.refresh_memory()
      pattern.update_working_pattern(program.get_selected_channel().number, program.get_selected_song_pattern())
    end
    save_confirm.cancel()
  end
end

function channel_edit_page_ui.handle_key_three_pressed()
  local pressed_keys = m_grid.get_pressed_keys()
  if channel_pages:get_selected_page() == channel_page_to_index["Memory"] then
    if is_key1_down then
      memory.redo_all(program.get_selected_channel().number)
      memory.clear(program.get_selected_channel().number)
      tooltip:show("Memory applied and forgotten")
    else
      memory.redo_all(program.get_selected_channel().number)
      tooltip:show("Ch. " .. program.get_selected_channel().number .. " memory applied")
    end
    channel_edit_page_ui.refresh_memory()
    pattern.update_working_pattern(program.get_selected_channel().number, program.get_selected_song_pattern())
  elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] and not trig_lock_page:is_sub_page_enabled() then
    local pressed_keys = m_grid.get_pressed_keys()
    if #pressed_keys > 0 then
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        program.toggle_step_param_slide(program.get_selected_channel(), step, dials:get_selected_index())
      end
    elseif not is_key1_down then
      program.toggle_channel_param_slide(program.get_selected_channel(), dials:get_selected_index())
    end
    fn.dirty_screen(true)
  elseif #pressed_keys < 1 then
    save_confirm.confirm()
  end
end

function channel_edit_page_ui.select_page(page) 
    channel_pages:select_page(page)
    fn.dirty_screen(true)
end

function channel_edit_page_ui.get_selected_page() 
    return channel_pages:get_selected_page()
end

function channel_edit_page_ui.select_mask_page()
  channel_edit_page_ui.refresh_masks()
  channel_pages:select_page(channel_page_to_index["Masks"])
  fn.dirty_screen(true)
end

function channel_edit_page_ui.select_trig_page()
  channel_edit_page_ui.refresh_trig_locks()
  channel_pages:select_page(channel_page_to_index["Trig Locks"])
end

function channel_edit_page_ui.select_memory_page()
  channel_edit_page_ui.refresh_memory()
  channel_pages:select_page(channel_page_to_index["Memory"])
end

function channel_edit_page_ui.select_clock_mods_page()
  channel_edit_page_ui.refresh_clock_mods()
  channel_edit_page_ui.refresh_swing()
  channel_edit_page_ui.refresh_swing_shuffle_type()
  channel_edit_page_ui.refresh_shuffle_feel()
  channel_edit_page_ui.refresh_shuffle_basis()
  channel_edit_page_ui.refresh_shuffle_amount()
  channel_pages:select_page(channel_page_to_index["Clock Mods"])
end

function channel_edit_page_ui.select_midi_config_page()
  channel_edit_page_ui.refresh_channel_config()
  channel_pages:select_page(channel_page_to_index["Midi Config"])
end

function channel_edit_page_ui.select_note_dashboard_page()
  channel_pages:select_page(channel_page_to_index["Note Dashboard"])
end


function channel_edit_page_ui.select_scales_quantizer_page()
  channel_edit_page_ui.refresh_quantiser()
  channel_edit_page_ui.refresh_romans()
  scales_pages:select_page(scales_page_to_index["Quantizer"])
end

function channel_edit_page_ui.select_channel_page_by_index(index)
  if index == 1 then
    channel_edit_page_ui.select_mask_page()
  elseif index == 2 then
    channel_edit_page_ui.select_trig_page()
  elseif index == 3 then
    channel_edit_page_ui.select_memory_page()
  elseif index == 4 then
    channel_edit_page_ui.select_clock_mods_page()
  elseif index == 5 then
    channel_edit_page_ui.select_midi_config_page()
  elseif index == 6 then
    channel_edit_page_ui.select_note_dashboard_page()
  end
end

function channel_edit_page_ui.set_note_dashboard_values(values)
  if values and values.note then
    note_displays.note:set_value(values.note)
  end
  if values and values.velocity then
    note_displays.velocity:set_value(values.velocity)
  end
  if values and values.length then
    note_displays.length:set_value(
      math.floor(values.length * 100 + 0.5) / 100
    )
  end

  if (values and values.chords) then

    for i = 1, 4 do
      
      -- MIDI note 0 is a played chord voice, not "no chord" (bugs.json dashboard-chord-slots).
      if values.chords[i] then
        note_displays.chords[i]:set_value(values.chords[i])
      elseif note_displays.chords[i]:get_value() ~= -1 then
        note_displays.chords[i]:set_value(note_displays.chords[i]:get_value())
      else
        note_displays.chords[i]:set_value(-1)
      end
    end
  end
end

function channel_edit_page_ui.should_show_step_has_trig_lock(channel, step)

  local current_page = channel_edit_page_ui.get_selected_page()
  local is_trig_locks_page = current_page == channel_page_to_index["Trig Locks"]
  local is_masks_page = current_page == channel_page_to_index["Masks"]
  local is_memory_page = current_page == channel_page_to_index["Memory"]
  local is_clock_mods_page = current_page == channel_page_to_index["Clock Mods"]
  local is_midi_config_page = current_page == channel_page_to_index["Midi Config"]
  local is_note_dashboard_page = current_page == channel_page_to_index["Note Dashboard"]

  -- Check trig locks page conditions
  if is_trig_locks_page then
    return program.step_has_param_trig_lock(channel, step) or
           program.step_has_param_slide(channel, step) or 
           program.step_scale_has_trig_lock(channel, step) or
           program.step_transpose_has_trig_lock(step)
  end

  -- Check masks page conditions 
  if is_masks_page then
    return program.step_has_trig_mask(step) or
           program.step_has_note_mask(step) or
           program.step_has_velocity_mask(step) or
           program.step_has_length_mask(step) or
           program.step_has_micro_time_mask(step) or
           program.step_has_chord_1_mask(step) or
           program.step_has_chord_2_mask(step) or
           program.step_has_chord_3_mask(step) or
           program.step_has_chord_4_mask(step) or 
           program.step_scale_has_trig_lock(channel, step) or
           program.step_transpose_has_trig_lock(step)
  end

  if is_memory_page then
    return program.step_has_param_trig_lock(channel, step) or
           program.step_has_trig_mask(step) or
           program.step_has_note_mask(step) or
           program.step_has_velocity_mask(step) or
           program.step_has_length_mask(step) or
           program.step_has_micro_time_mask(step) or
           program.step_has_chord_1_mask(step) or
           program.step_has_chord_2_mask(step) or
           program.step_has_chord_3_mask(step) or
           program.step_has_chord_4_mask(step)
  end

  if is_clock_mods_page then
    return program.step_has_param_trig_lock(channel, step) or 
          program.step_octave_has_trig_lock(channel, step) or 
          program.step_scale_has_trig_lock(channel, step) or 
          program.step_transpose_has_trig_lock(step) or 
          program.step_has_trig_mask(step) or 
          program.step_has_note_mask(step) or 
          program.step_has_velocity_mask(step) or 
          program.step_has_length_mask(step) or 
          program.step_has_micro_time_mask(step) or 
          program.step_has_chord_1_mask(step) or 
          program.step_has_chord_2_mask(step) or 
          program.step_has_chord_3_mask(step) or 
          program.step_has_chord_4_mask(step) or
          program.step_has_param_slide(channel, step)
  end 

  if is_midi_config_page then
    return program.step_has_param_trig_lock(channel, step) or 
          program.step_octave_has_trig_lock(channel, step) or 
          program.step_scale_has_trig_lock(channel, step) or 
          program.step_transpose_has_trig_lock(step) or 
          program.step_has_trig_mask(step) or 
          program.step_has_note_mask(step) or 
          program.step_has_velocity_mask(step) or 
          program.step_has_length_mask(step) or 
          program.step_has_micro_time_mask(step) or 
          program.step_has_chord_1_mask(step) or 
          program.step_has_chord_2_mask(step) or 
          program.step_has_chord_3_mask(step) or 
          program.step_has_chord_4_mask(step) or
          program.step_has_param_slide(channel, step)
  end 

  if is_note_dashboard_page then
    return program.step_has_param_trig_lock(channel, step) or 
          program.step_octave_has_trig_lock(channel, step) or 
          program.step_scale_has_trig_lock(channel, step) or 
          program.step_transpose_has_trig_lock(step) or 
          program.step_has_trig_mask(step) or 
          program.step_has_note_mask(step) or 
          program.step_has_velocity_mask(step) or 
          program.step_has_length_mask(step) or 
          program.step_has_micro_time_mask(step) or 
          program.step_has_chord_1_mask(step) or 
          program.step_has_chord_2_mask(step) or 
          program.step_has_chord_3_mask(step) or 
          program.step_has_chord_4_mask(step) or
          program.step_has_param_slide(channel, step)
  end

  return true
end


return channel_edit_page_ui

