local channel_edit_page_ui_controller = {}

local fn = include("mosaic/lib/functions")

local quantiser = include("mosaic/lib/quantiser")
local pages = include("mosaic/lib/ui_components/pages")
local page = include("mosaic/lib/ui_components/page")
local vertical_scroll_selector = include("mosaic/lib/ui_components/vertical_scroll_selector")
local dial = include("mosaic/lib/ui_components/dial")
local control_scroll_selector = include("mosaic/lib/ui_components/control_scroll_selector")
local list_selector = include("mosaic/lib/ui_components/list_selector")
local value_selector = include("mosaic/lib/ui_components/value_selector")

local musicutil = require("musicutil")
local param_manager = include("mosaic/lib/param_manager")

local channel_pages = pages:new()
local scales_pages = pages:new()

local quantizer_vertical_scroll_selector = vertical_scroll_selector:new(20, 25, "Quantizer", quantiser.get_scales())
local romans_vertical_scroll_selector =
  vertical_scroll_selector:new(90, 25, "Roman Analysis", quantiser.get_scales()[1].romans)
local notes_vertical_scroll_selector = vertical_scroll_selector:new(5, 25, "Notes", quantiser.get_notes())
local rotation_vertical_scroll_selector = vertical_scroll_selector:new(110, 25, "Rotation", {"0", "1", "2", "3", "4", "5", "6"})

local note_trig_selector = value_selector:new(5, 18, "Trig", -1, 1)
note_trig_selector:set_value(-1)
local note_value_selector = value_selector:new(30, 18, "Note", -1, 127)
note_value_selector:set_value(-1)
local note_velocity_selector = value_selector:new(55, 18, "Vel", -1, 127)
note_velocity_selector:set_value(-1)
local note_length_selector = value_selector:new(80, 18, "Len", -1, 512)
note_length_selector:set_value(-1)
local note_chord_1 = value_selector:new(5, 40, "Chd1", -14, 14)
note_chord_1:set_value(0)
local note_chord_2 = value_selector:new(30, 40, "Chd2", -14, 14)
note_chord_2:set_value(0)
local note_chord_3 = value_selector:new(55, 40, "Chd3", -14, 14)
note_chord_3:set_value(0)
local note_chord_4 = value_selector:new(80, 40, "Chd4", -14, 14)
note_chord_4:set_value(0)



local clock_mod_list_selector = list_selector:new(5, 25, "Clock Mod", {})
local clock_swing_value_selector = value_selector:new(55, 25, "Swing", 0, 100)

local midi_device_vertical_scroll_selector = vertical_scroll_selector:new(90, 25, "Midi Device", {})
local midi_channel_vertical_scroll_selector =
  vertical_scroll_selector:new(
  65,
  25,
  "Midi Channel",
  {
    {name = "CC1", value = 1},
    {name = "CC2", value = 2},
    {name = "CC3", value = 3},
    {name = "CC4", value = 4},
    {name = "CC5", value = 5},
    {name = "CC6", value = 6},
    {name = "CC7", value = 7},
    {name = "CC8", value = 8},
    {name = "CC9", value = 9},
    {name = "CC10", value = 10},
    {name = "CC11", value = 11},
    {name = "CC12", value = 12},
    {name = "CC13", value = 13},
    {name = "CC14", value = 14},
    {name = "CC15", value = 15},
    {name = "CC16", value = 16}
  }
)
local device_map_vertical_scroll_selector

local param_select_vertical_scroll_selector = vertical_scroll_selector:new(30, 25, "Params", {})

local param_1 = dial:new(5, 18, "Param 1", "param_1", "X", "")
local param_2 = dial:new(30, 18, "Param 2", "param_2", "X", "")
local param_3 = dial:new(55, 18, "Param 3", "param_3", "X", "")
local param_4 = dial:new(80, 18, "Param 4", "param_4", "X", "")
local param_5 = dial:new(105, 18, "Param 5", "param_5", "X", "")
local param_6 = dial:new(5, 40, "Param 6", "param_6", "X", "")
local param_7 = dial:new(30, 40, "Param 7", "param_7", "X", "")
local param_8 = dial:new(55, 40, "Param 8", "param_8", "X", "")
local param_9 = dial:new(80, 40, "Param 9", "param_9", "X", "")
local param_10 = dial:new(105, 40, "Param 10", "param_10", "X", "")

local m_params = {param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8, param_9, param_10}

local dials = control_scroll_selector:new(0, 0, {})

local channel_page_to_index = {["Notes"] = 1, ["Trig Locks"] = 2, ["Clock Mods"] = 3, ["Midi Config"] = 4}
local scales_page_to_index = {["Quantizer"] = 1, ["Clock Mods"] = 2}

local refresh_timer_id = nil
local throttle_time = 0.1

local k2_held = false

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


local notes_page =
  page:new(
  "Note Masks",
  function()
    if program.get().selected_channel ~= 17 then
      note_value_selector:draw()
      note_velocity_selector:draw()
      note_length_selector:draw()
      note_trig_selector:draw()
      note_chord_1:draw()
      note_chord_2:draw()
      note_chord_3:draw()
      note_chord_4:draw()
    else
      print_quant_message_to_screen()
    end
  end
)


note_value_selector:set_view_transform_func(function(value)

  if value == -1 then 
    return "X"
  end

  return musicutil.note_num_to_name(value, true)
end)

local function note_page_velocity_length_value_selector_func(value)

  if value == -1 then 
    return "X"
  end

  return value
end

local function chord_value_selector_func(value)
  
  local chord_ui_labels = {
    "--oct",
    "--2nd",
    "--3rd",
    "--4th",
    "--5th",
    "--6th",
    "--7th",
    "-oct",
    "-2nd",
    "-3rd",
    "-4th",
    "-5th",
    "-6th",
    "-7th",
    "X",
    "2nd",
    "3rd",
    "4th",
    "5th",
    "6th",
    "7th",
    "+oct",
    "+2nd",
    "+3rd",
    "+4th",
    "+5th", 
    "+6th",
    "+7th",
    "++oct"
  }

  return chord_ui_labels[value + 15]
end


note_velocity_selector:set_view_transform_func(note_page_velocity_length_value_selector_func)
note_length_selector:set_view_transform_func(note_page_velocity_length_value_selector_func)
note_chord_1:set_view_transform_func(chord_value_selector_func)
note_chord_2:set_view_transform_func(chord_value_selector_func)
note_chord_3:set_view_transform_func(chord_value_selector_func)
note_chord_4:set_view_transform_func(chord_value_selector_func)

note_trig_selector:set_view_transform_func(function(value)


  if value == 0 then 
    return "N"
  elseif value == 1 then 
    return "Y"
  end

  return "X"

end)


local quantizer_page =
  page:new(
  "",
  function()
    quantizer_vertical_scroll_selector:draw()
    romans_vertical_scroll_selector:draw()
    notes_vertical_scroll_selector:draw()
    rotation_vertical_scroll_selector:draw()
  end
)

local clock_mods_page =
  page:new(
  "Clocks",
  function()
    if program.get().selected_channel ~= 17 then
      clock_swing_value_selector:draw()
    end

    clock_mod_list_selector:draw()
  end
)

local channel_edit_page =
  page:new(
  "Device Config",
  function()
    if program.get().selected_channel ~= 17 then
      local channel = program.get_selected_channel()
      local device = fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)
      if (device.type == "midi") then
        if (device.default_midi_device == nil) then
          midi_device_vertical_scroll_selector:draw()
        end
        if (device.default_midi_channel == nil) then
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
  end
)

local trig_lock_page =
  page:new(
  "Trig Locks",
  function()
    if program.get().selected_channel ~= 17 then
      dials:draw()
    else
      print_quant_message_to_screen()
    end
  end
)

function channel_edit_page_ui_controller.init()
  note_value_selector:select()
  quantizer_vertical_scroll_selector:select()
  midi_channel_vertical_scroll_selector:select()
  midi_device_vertical_scroll_selector:set_items(midi_controller.get_midi_outs())
  dials:set_items({param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8, param_9, param_10})
  clock_mod_list_selector:set_list(clock_controller.get_clock_divisions())
  device_map_vertical_scroll_selector = vertical_scroll_selector:new(10, 25, "Midi Map", device_map:get_devices())


  notes_page:set_sub_name_func(
    function()
      if program.get().selected_channel ~= 17 then
        return "Ch. " .. program.get().selected_channel .. " "
      else
        return ""
      end
    end
  )

  quantizer_page:set_sub_name_func(
    function()
      if program.get().selected_channel ~= 17 then
        return "Quantizer"
      else
        return "Quantizer " .. program.get().selected_scale .. " "
      end
    end
  )

  channel_edit_page:set_sub_name_func(
    function()
      if program.get().selected_channel ~= 17 then
        return "Ch. " .. program.get().selected_channel .. " "
      else
        return ""
      end
    end
  )

  clock_mods_page:set_sub_name_func(
    function()
      if program.get().selected_channel ~= 17 then
        return "Ch. " .. program.get().selected_channel .. " "
      else
        return ""
      end
    end
  )

  trig_lock_page:set_sub_name_func(
    function()
      if program.get().selected_channel ~= 17 then
        return "Ch. " .. program.get().selected_channel .. " "
      else
        return ""
      end
    end
  )

  trig_lock_page:set_sub_page_draw_func(
    function()
      param_select_vertical_scroll_selector:draw()
    end
  )

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

function channel_edit_page_ui_controller.register_ui_draw_handlers()
  draw_handler:register_ui(
    "channel_edit_page",
    function()
      if program.get().selected_channel ~= 17 then
        channel_pages:draw()
      else
        scales_pages:draw()
      end
    end
  )
end

function channel_edit_page_ui_controller.update_scale()

  local scale = quantizer_vertical_scroll_selector:get_selected_item()
  local chord = romans_vertical_scroll_selector:get_selected_index()
  local root_note = notes_vertical_scroll_selector:get_selected_index() - 1
  local rotation = rotation_vertical_scroll_selector:get_selected_index() - 1


  save_confirm.set_cancel_message("Scale not saved.")
  save_confirm.set_cancel(
    function()
      channel_edit_page_ui_controller.refresh_quantiser()
    end
  )


  if k2_held then
    save_confirm.set_confirm_message("K2 to save across song.")
    save_confirm.set_ok_message("Scale saved to all.")
    save_confirm.set_save(
      function()
        program.set_all_sequencer_pattern_scales(
          program.get().selected_scale,
          {
            number = scale.number,
            scale = scale.scale,
            pentatonic_scale = scale.pentatonic_scale,
            chord = chord,
            root_note = root_note,
            chord_degree_rotation = rotation
          }
        )
      end
    )
  else
    save_confirm.set_save(
      function()
        program.set_scale(
          program.get().selected_scale,
          {
            number = scale.number,
            scale = scale.scale,
            pentatonic_scale = scale.pentatonic_scale,
            chord = chord,
            root_note = root_note,
            chord_degree_rotation = rotation
          }
        )
      end
    )
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

  program.get().devices[channel.number].midi_device = midi_device.value
  program.get().devices[channel.number].midi_channel = midi_channel.value
  program.get().devices[channel.number].device_map = device_m.id

  local device = device_map.get_device(program.get().devices[channel.number].device_map)
  if device.default_midi_channel ~= nil then
    program.get().devices[channel.number].midi_channel = device.default_midi_channel
  end

  if device.default_midi_device ~= nil then
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

function channel_edit_page_ui_controller.handle_trig_lock_param_change_by_direction(direction, channel, dial_index)

  local pressed_keys = grid_controller.get_pressed_keys()
  local param_id = channel.trig_lock_params[dial_index].param_id
  local p_value = nil
  local p = nil
  if param_id ~= nil then
    p = params:lookup_param(param_id)
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

    channel_edit_page_ui_controller.refresh_trig_lock_value(dial_index)

  end

end


function channel_edit_page_ui_controller.enc(n, d)
  local channel = program.get_selected_channel()
  if n == 3 then
    for i = 1, math.abs(d) do
      if d > 0 then
        if program.get().selected_channel ~= 17 and channel_pages:get_selected_page() == channel_page_to_index["Notes"] then
          local pressed_keys = grid_controller.get_pressed_keys()
          if #pressed_keys > 0 then
            if (pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8) then
              for i, keys in ipairs(pressed_keys) do
                local step = fn.calc_grid_count(keys[1], keys[2])
                if note_trig_selector:is_selected() then
                  note_trig_selector:increment()
                  channel.step_trig_masks[step] = note_trig_selector:get_value()
                  if channel.step_trig_masks[step] > 1 then
                    channel.step_trig_masks[step] = 1
                  end
                end
                if note_value_selector:is_selected() then
                  note_value_selector:increment()
                  channel.step_note_masks[step] = note_value_selector:get_value()
                  if channel.step_note_masks[step] > 127 then
                    channel.step_note_masks[step] = 127
                  end
                end
                if note_velocity_selector:is_selected() then
                  note_velocity_selector:increment()
                  channel.step_velocity_masks[step] = note_velocity_selector:get_value()
                  if channel.step_velocity_masks[step] > 127 then
                    channel.step_velocity_masks[step] = 127
                  end
                end
                if note_length_selector:is_selected() then
                  note_length_selector:increment()
                  if note_length_selector:get_value() == 0 then 
                    note_length_selector:set_value(1)
                  end
                  channel.step_length_masks[step] = note_length_selector:get_value()
                  if channel.step_length_masks[step] > 512 then
                    channel.step_length_masks[step] = 512
                  end
                end
                if note_chord_1:is_selected() then
                  note_chord_1:increment()
                  if channel.step_chord_masks[step] == nil then
                    channel.step_chord_masks[step] = {}
                  end
                  if note_chord_1:get_value() > 14 then
                    channel.step_chord_masks[step][1] = 14
                  elseif note_chord_1:get_value() == 0 then
                    channel.step_chord_masks[step][1] = nil
                  else
                    channel.step_chord_masks[step][1] = note_chord_1:get_value()
                  end
                end
                if note_chord_2:is_selected() then
                  note_chord_2:increment()
                  if channel.step_chord_masks[step] == nil then
                    channel.step_chord_masks[step] = {}
                  end
                  if note_chord_2:get_value() > 14 then
                    channel.step_chord_masks[step][2] = 14
                  elseif note_chord_2:get_value() == 0 then
                    channel.step_chord_masks[step][2] = nil
                  else
                    channel.step_chord_masks[step][2] = note_chord_2:get_value()
                  end
                end
                if note_chord_3:is_selected() then
                  note_chord_3:increment()
                  if channel.step_chord_masks[step] == nil then
                    channel.step_chord_masks[step] = {}
                  end
                  if note_chord_3:get_value() > 14 then
                    channel.step_chord_masks[step][3] = 14
                  elseif note_chord_3:get_value() == 0 then
                    channel.step_chord_masks[step][3] = nil
                  else
                    channel.step_chord_masks[step][3] = note_chord_3:get_value()
                  end
                end
                if note_chord_4:is_selected() then
                  note_chord_4:increment()
                  if channel.step_chord_masks[step] == nil then
                    channel.step_chord_masks[step] = {}
                  end
                  if note_chord_4:get_value() > 14 then
                    channel.step_chord_masks[step][4] = 14
                  elseif note_chord_4:get_value() == 0  then
                    channel.step_chord_masks[step][4] = nil
                  else
                    channel.step_chord_masks[step][4] = note_chord_4:get_value()
                  end
                end
              end
            end
          end
        elseif program.get().selected_channel == 17 and scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] then
          if quantizer_vertical_scroll_selector:is_selected() then
            quantizer_vertical_scroll_selector:scroll_down()
            channel_edit_page_ui_controller.refresh_romans()
          end
          if romans_vertical_scroll_selector:is_selected() then
            romans_vertical_scroll_selector:scroll_down()
          end
          if notes_vertical_scroll_selector:is_selected() then
            notes_vertical_scroll_selector:scroll_down()
          end
          if rotation_vertical_scroll_selector:is_selected() then
            rotation_vertical_scroll_selector:scroll_down()
          end
          channel_edit_page_ui_controller.update_scale()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] and program.get().selected_channel ~= 17 then
          if clock_mod_list_selector:is_selected() then
            clock_mod_list_selector:decrement()
            save_confirm.set_save(
              function()
                channel_edit_page_ui_controller.update_clock_mods()
              end
            )
            save_confirm.set_cancel(
              function()
                channel_edit_page_ui_controller.refresh_clock_mods()
              end
            )
          end
          if clock_swing_value_selector:is_selected() then
            clock_swing_value_selector:increment()
            save_confirm.set_save(
              function()
                channel_edit_page_ui_controller.update_swing()
              end
            )
            save_confirm.set_cancel(
              function()
                channel_edit_page_ui_controller.refresh_swing()
              end
            )
          end
        elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] and program.get().selected_channel == 17 then
          if clock_mod_list_selector:is_selected() then
            clock_mod_list_selector:decrement()
            save_confirm.set_save(
              function()
                channel_edit_page_ui_controller.update_clock_mods()
              end
            )
            save_confirm.set_cancel(
              function()
                channel_edit_page_ui_controller.refresh_clock_mods()
              end
            )
          end
        elseif channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] and program.get().selected_channel ~= 17 then
          if midi_device_vertical_scroll_selector:is_selected() then
            midi_device_vertical_scroll_selector:scroll_down()
          end
          if midi_channel_vertical_scroll_selector:is_selected() then
            midi_channel_vertical_scroll_selector:scroll_down()
          end
          if device_map_vertical_scroll_selector:is_selected() then
            device_map_vertical_scroll_selector:scroll_down()
          end
          save_confirm.set_save(
            function()
              channel_edit_page_ui_controller.update_channel_config()
              param_manager.update_default_params(
                program.get_selected_channel(), device_map_vertical_scroll_selector:get_selected_item()
              )
              param_select_vertical_scroll_selector:set_selected_item(1)
            end
          )
          save_confirm.set_cancel(
            function()
              channel_edit_page_ui_controller.throttled_refresh_channel_config()
            end
          )
        elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] and program.get().selected_channel ~= 17 then
          if trig_lock_page:is_sub_page_enabled() then
            param_select_vertical_scroll_selector:scroll_down()
            save_confirm.set_save(
              function()
                param_manager.update_param(
                  dials:get_selected_index(), 
                  channel, 
                  param_select_vertical_scroll_selector:get_selected_item(), 
                  param_select_vertical_scroll_selector:get_meta_item()
                )
                channel_edit_page_ui_controller.refresh_trig_locks()
              end
            )
            save_confirm.set_cancel(
              function()
              end
            )
          else
            channel_edit_page_ui_controller.handle_trig_lock_param_change_by_direction(d, program.get_selected_channel(), dials:get_selected_index())
          end
        end
      else
        if channel_pages:get_selected_page() == channel_page_to_index["Notes"] and program.get().selected_channel ~= 17 then
          local pressed_keys = grid_controller.get_pressed_keys()
          if #pressed_keys > 0 then
            if (pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8) then
              for i, keys in ipairs(pressed_keys) do
                local step = fn.calc_grid_count(keys[1], keys[2])
                if note_trig_selector:is_selected() then
                  note_trig_selector:decrement()
                  channel.step_trig_masks[step] = note_trig_selector:get_value()
                  if channel.step_trig_masks[step] < 0 then
                    channel.step_trig_masks[step] = nil
                  end
                end
                if note_value_selector:is_selected() then
                  note_value_selector:decrement()
                  channel.step_note_masks[step] = note_value_selector:get_value()
                  if channel.step_note_masks[step] < 0 then
                    channel.step_note_masks[step] = nil
                  end
                end
                if note_velocity_selector:is_selected() then
                  note_velocity_selector:decrement()
                  channel.step_velocity_masks[step] = note_velocity_selector:get_value()
                  if channel.step_velocity_masks[step] < 0 then
                    channel.step_velocity_masks[step] = nil
                  end
                end
                if note_length_selector:is_selected() then
                  note_length_selector:decrement()
                  channel.step_length_masks[step] = note_length_selector:get_value()
                  if note_length_selector:get_value() < 1 then 
                    channel.step_length_masks[step] = nil
                    note_length_selector:set_value(-1)
                  end
                end
                if note_chord_1:is_selected() then
                  note_chord_1:decrement()
                  if channel.step_chord_masks[step] == nil then
                    channel.step_chord_masks[step] = {}
                  end
                  print(note_chord_1:get_value() )
                  if note_chord_1:get_value() < -14 or note_chord_1:get_value() == 0 then
                    channel.step_chord_masks[step][1] = nil
                  else
                    channel.step_chord_masks[step][1] = note_chord_1:get_value()
                  end
                end
                if note_chord_2:is_selected() then
                  note_chord_2:decrement()
                  if channel.step_chord_masks[step] == nil then
                    channel.step_chord_masks[step] = {}
                  end
                  if note_chord_2:get_value() < -14 or note_chord_2:get_value() == 0 then
                    channel.step_chord_masks[step][2] = nil
                  else
                    channel.step_chord_masks[step][2] = note_chord_2:get_value()
                  end
                end
                if note_chord_3:is_selected() then
                  note_chord_3:decrement()
                  if channel.step_chord_masks[step] == nil then
                    channel.step_chord_masks[step] = {}
                  end
                  
                  if note_chord_3:get_value() < -14 or note_chord_3:get_value() == 0 then
                    channel.step_chord_masks[step][3] = nil
                  else
                    channel.step_chord_masks[step][3] = note_chord_3:get_value()
                  end
                end
                if note_chord_4:is_selected() then
                  note_chord_4:decrement()
                  if channel.step_chord_masks[step] == nil then
                    channel.step_chord_masks[step] = {}
                  end
                  
                  if note_chord_4:get_value() < -14 or note_chord_4:get_value() == 0 then
                    channel.step_chord_masks[step][4] = nil
                  else
                    channel.step_chord_masks[step][4] = note_chord_4:get_value()
                  end
                end
              end
            end
          end
        elseif scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] and program.get().selected_channel == 17 then
          if quantizer_vertical_scroll_selector:is_selected() then
            quantizer_vertical_scroll_selector:scroll_up()
            channel_edit_page_ui_controller.refresh_romans()
          end
          if romans_vertical_scroll_selector:is_selected() then
            romans_vertical_scroll_selector:scroll_up()
          end
          if notes_vertical_scroll_selector:is_selected() then
            notes_vertical_scroll_selector:scroll_up()
          end
          if rotation_vertical_scroll_selector:is_selected() then
            rotation_vertical_scroll_selector:scroll_up()
          end
          channel_edit_page_ui_controller.update_scale()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] and program.get().selected_channel ~= 17 then
          if clock_mod_list_selector:is_selected() then
            clock_mod_list_selector:increment()
            save_confirm.set_save(
              function()
                channel_edit_page_ui_controller.update_clock_mods()
              end
            )
            save_confirm.set_cancel(
              function()
                channel_edit_page_ui_controller.refresh_clock_mods()
              end
            )
          end
          if clock_swing_value_selector:is_selected() then
            clock_swing_value_selector:decrement()
            save_confirm.set_save(
              function()
                channel_edit_page_ui_controller.update_swing()
              end
            )
            save_confirm.set_cancel(
              function()
                channel_edit_page_ui_controller.refresh_swing()
              end
            )
          end
        elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] and program.get().selected_channel == 17 then
          if clock_mod_list_selector:is_selected() then
            clock_mod_list_selector:increment()
            save_confirm.set_save(
              function()
                channel_edit_page_ui_controller.update_clock_mods()
              end
            )
            save_confirm.set_cancel(
              function()
                channel_edit_page_ui_controller.refresh_clock_mods()
              end
            )
          end

        elseif  channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] and program.get().selected_channel ~= 17 then
          if midi_device_vertical_scroll_selector:is_selected() then
            midi_device_vertical_scroll_selector:scroll_up()
          end
          if midi_channel_vertical_scroll_selector:is_selected() then
            midi_channel_vertical_scroll_selector:scroll_up()
          end
          if device_map_vertical_scroll_selector:is_selected() then
            device_map_vertical_scroll_selector:scroll_up()
          end
          save_confirm.set_save(
            function()
              channel_edit_page_ui_controller.update_channel_config()
              param_manager.update_default_params(
                program.get_selected_channel(), device_map_vertical_scroll_selector:get_selected_item()
              )
              param_select_vertical_scroll_selector:set_selected_item(1)
            end
          )
          save_confirm.set_cancel(
            function()
              channel_edit_page_ui_controller.throttled_refresh_channel_config()
            end
          )
        elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] and program.get().selected_channel ~= 17then
          if trig_lock_page:is_sub_page_enabled() then
            param_select_vertical_scroll_selector:scroll_up()
            save_confirm.set_save(
              function()
                param_manager.update_param(
                  dials:get_selected_index(), 
                  channel, 
                  param_select_vertical_scroll_selector:get_selected_item(), 
                  param_select_vertical_scroll_selector:get_meta_item()
                )                
                channel_edit_page_ui_controller.refresh_trig_locks()
              end
            )
            save_confirm.set_cancel(
              function()
              end
            )
          else
            channel_edit_page_ui_controller.handle_trig_lock_param_change_by_direction(d, program.get_selected_channel(), dials:get_selected_index())
          end
        end
      end
    end
  end

  if n == 2 then
    for i = 1, math.abs(d) do
      if d > 0 then
        if channel_pages:get_selected_page() == channel_page_to_index["Notes"] and program.get().selected_channel ~= 17 then
          if note_trig_selector:is_selected() then
            note_trig_selector:deselect()
            note_value_selector:select()
          elseif note_value_selector:is_selected() then
            note_value_selector:deselect()
            note_velocity_selector:select()
          elseif note_velocity_selector:is_selected() then
            note_velocity_selector:deselect()
            note_length_selector:select()
          elseif note_length_selector:is_selected() then
            note_length_selector:deselect()
            note_chord_1:select()
          elseif note_chord_1:is_selected() then
            note_chord_1:deselect()
            note_chord_2:select()
          elseif note_chord_2:is_selected() then
            note_chord_2:deselect()
            note_chord_3:select()
          elseif note_chord_3:is_selected() then
            note_chord_3:deselect()
            note_chord_4:select()
          end
      
        elseif scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] and program.get().selected_channel == 17 then
          if quantizer_vertical_scroll_selector:is_selected() then
            quantizer_vertical_scroll_selector:deselect()
            romans_vertical_scroll_selector:select()
          elseif romans_vertical_scroll_selector:is_selected() then
            romans_vertical_scroll_selector:deselect()
            rotation_vertical_scroll_selector:select()
          elseif notes_vertical_scroll_selector:is_selected() then
            notes_vertical_scroll_selector:deselect()
            quantizer_vertical_scroll_selector:select()
          end
        elseif channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] and program.get().selected_channel ~= 17 then
          if clock_mod_list_selector:is_selected() then
            clock_mod_list_selector:deselect()
            clock_swing_value_selector:select()
          end
        elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] and program.get().selected_channel == 17 then
          clock_mod_list_selector:select()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] and program.get().selected_channel ~= 17 then
          local device =
            fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)
          if midi_channel_vertical_scroll_selector:is_selected() then
            if (device.default_midi_device == nil) then
              midi_channel_vertical_scroll_selector:deselect()
              midi_device_vertical_scroll_selector:select()
            end
          elseif device_map_vertical_scroll_selector:is_selected() then
            if (device.default_midi_channel == nil) then
              device_map_vertical_scroll_selector:deselect()
              midi_channel_vertical_scroll_selector:select()
            else
              if (device.default_midi_device == nil) then
                device_map_vertical_scroll_selector:deselect()
                midi_device_vertical_scroll_selector:select()
              end
            end
          end
        elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] and program.get().selected_channel ~= 17 then
          if not trig_lock_page:is_sub_page_enabled() then
            dials:scroll_next()
          end
        end
      else
        if channel_pages:get_selected_page() == channel_page_to_index["Notes"] and program.get().selected_channel ~= 17 then
          if note_value_selector:is_selected() then
            note_value_selector:deselect()
            note_trig_selector:select()
          elseif note_velocity_selector:is_selected() then
            note_velocity_selector:deselect()
            note_value_selector:select()
          elseif note_length_selector:is_selected() then
            note_length_selector:deselect()
            note_velocity_selector:select()
          elseif note_chord_1:is_selected() then
            note_chord_1:deselect()
            note_length_selector:select()
          elseif note_chord_2:is_selected() then
            note_chord_2:deselect()
            note_chord_1:select()
          elseif note_chord_3:is_selected() then
            note_chord_3:deselect()
            note_chord_2:select()
          elseif note_chord_4:is_selected() then
            note_chord_4:deselect()
            note_chord_3:select()
          end
        elseif scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] and program.get().selected_channel == 17 then
          if quantizer_vertical_scroll_selector:is_selected() then
            quantizer_vertical_scroll_selector:deselect()
            notes_vertical_scroll_selector:select()
          elseif romans_vertical_scroll_selector:is_selected() then
            romans_vertical_scroll_selector:deselect()
            quantizer_vertical_scroll_selector:select()
          elseif rotation_vertical_scroll_selector:is_selected() then
            rotation_vertical_scroll_selector:deselect()
            romans_vertical_scroll_selector:select()
          end
        elseif channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] and program.get().selected_channel ~= 17 then
          if clock_swing_value_selector:is_selected() then
            clock_swing_value_selector:deselect()
            clock_mod_list_selector:select()
          end
        elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] and program.get().selected_channel == 17 then
          clock_mod_list_selector:select()
        elseif channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] and program.get().selected_channel ~= 17 then
          local device =
            fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)
          if midi_device_vertical_scroll_selector:is_selected() then
            if (device.default_midi_channel == nil) then
              midi_device_vertical_scroll_selector:deselect()
              midi_channel_vertical_scroll_selector:select()
            elseif (device.default_midi_device == nil) then
              midi_device_vertical_scroll_selector:deselect()
              device_map_vertical_scroll_selector:select()
            end
          elseif midi_channel_vertical_scroll_selector:is_selected() then
              midi_channel_vertical_scroll_selector:deselect()
              device_map_vertical_scroll_selector:select()
          end
        elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] and program.get().selected_channel ~= 17 then
          if not trig_lock_page:is_sub_page_enabled() then
            dials:scroll_previous()
          end
        end
      end
    end
  end

  if n == 1 then
    for i = 1, math.abs(d) do
      if d > 0 then
        if program.get().selected_channel ~= 17 then
          channel_pages:next_page()
        else
          scales_pages:next_page()
        end
        fn.dirty_screen(true)
        save_confirm.cancel()
      else
        if program.get().selected_channel ~= 17 then
          channel_pages:previous_page()
        else
          scales_pages:previous_page()
        end
        fn.dirty_screen(true)
        save_confirm.cancel()
      end
    end
  end
end

function channel_edit_page_ui_controller.key(n, z)
  if n == 2 and z == 1 then
    local pressed_keys = grid_controller.get_pressed_keys()
    if #pressed_keys > 0 then
      for i, keys in ipairs(pressed_keys) do
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
      else
        k2_held = true
      end
      save_confirm.cancel()
    end
  end
  if n == 2 and z == 0 then
    k2_held = false
  end
  if n == 3 and z == 1 then
    local pressed_keys = grid_controller.get_pressed_keys()
    if #pressed_keys > 0 then
      for i, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        local step_trig_lock_banks = program.get_selected_channel().step_trig_lock_banks
        local channel = program.get_selected_channel()
        if channel.number ~= 17 and step_trig_lock_banks and step_trig_lock_banks[step] then
          local parameter = dials:get_selected_index()
          step_trig_lock_banks[step][parameter] = nil
          tooltip:show("Param trig lock " .. parameter .. " cleared")
          local has_active_parameter = false
          for i = 1, 10 do
            if step_trig_lock_banks[step][i] ~= nil then
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
end


function channel_edit_page_ui_controller.refresh_notes()
  local pressed_keys = grid_controller.get_pressed_keys()
  local channel = program.get_selected_channel()
  local note_value = -1
  local velocity_value = -1
  local length_value = -1
  local micro_time_value = -1
  local trig_value = -1
  local chord_1_value = 0
  local chord_2_value = 0
  local chord_3_value = 0
  local chord_4_value = 0

  
  if #pressed_keys > 0 then
    if (pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8) then
      for i, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        note_value = channel.step_note_masks[step] or -1
        velocity_value = channel.step_velocity_masks[step] or -1
        length_value = channel.step_length_masks[step] or -1
        micro_time_value = channel.step_micro_time_masks[step] or -1
        trig_value = channel.step_trig_masks[step] or -1
        if channel.step_chord_masks[step] then
          chord_1_value = channel.step_chord_masks[step][1] or 0
          chord_2_value = channel.step_chord_masks[step][2] or 0
          chord_3_value = channel.step_chord_masks[step][3] or 0
          chord_4_value = channel.step_chord_masks[step][4] or 0
        end
      end
    end
  end

  note_value_selector:set_value(note_value)
  note_velocity_selector:set_value(velocity_value)
  note_length_selector:set_value(length_value)
  note_trig_selector:set_value(trig_value)
  note_chord_1:set_value(chord_1_value)
  note_chord_2:set_value(chord_2_value)
  note_chord_3:set_value(chord_3_value)
  note_chord_4:set_value(chord_4_value)

end

function channel_edit_page_ui_controller.refresh_clock_mods()
  local channel = program.get_selected_channel()
  local clock_mods = channel.clock_mods

  local divisions = fn.filter_by_type(clock_controller.get_clock_divisions(), clock_mods.type)

  local i = fn.find_index_in_table_by_value(divisions, clock_mods.value)

  if clock_mods.type == "clock_division" then
    i = i + 12
  end

  clock_mod_list_selector:set_selected_value(i)

  if channel.number == 17 then
    clock_mod_list_selector:select()
    clock_swing_value_selector:deselect()
  end
end

function channel_edit_page_ui_controller.refresh_swing()
  local channel = program.get_selected_channel()
  clock_swing_value_selector:set_value(channel.swing)
end

function channel_edit_page_ui_controller.refresh_device_selector()
  local channel = program.get_selected_channel()
  if channel.number == 17 then
    return
  end
  local device = device_map.get_device(program.get().devices[channel.number].device_map)
  local device_params = device_map.get_params(program.get().devices[channel.number].device_map)

  param_select_vertical_scroll_selector:set_items(device_params)
  param_select_vertical_scroll_selector:set_meta_item(device)
end

function channel_edit_page_ui_controller.refresh_romans()
  local scale = quantizer_vertical_scroll_selector:get_selected_item()

  if (scale) then
    local number = scale.number
    program.get_selected_sequencer_pattern().active = true
    romans_vertical_scroll_selector:set_items(quantiser.get_scales()[number].romans)

    fn.dirty_screen(true)
  end
end

function channel_edit_page_ui_controller.refresh_quantiser()
  local channel = program.get_selected_channel()

  local number = program.get_scale(program.get().selected_scale).number
  local chord = program.get_scale(program.get().selected_scale).chord
  local root_note = program.get_scale(program.get().selected_scale).root_note
  local rotation = program.get_scale(program.get().selected_scale).chord_degree_rotation or 0
  program.get_selected_sequencer_pattern().active = true

  quantizer_vertical_scroll_selector:set_selected_item(number)
  notes_vertical_scroll_selector:set_selected_item(root_note + 1)
  romans_vertical_scroll_selector:set_selected_item(chord)
  rotation_vertical_scroll_selector:set_selected_item((rotation or 0) + 1)
  channel_edit_page_ui_controller.refresh_romans()

end

function channel_edit_page_ui_controller.set_current_note(note)

  local pressed_keys = grid_controller.get_pressed_keys()
  local value = -1
  if #pressed_keys > 0 then
    if (pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8) then
      return
    end
  end
  note_value_selector:set_value(note.note)
  note_velocity_selector:set_value(note.velocity)
  note_length_selector:set_value(note.length)
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

function channel_edit_page_ui_controller.refresh_trig_lock_value(i)
  local channel = program.get_selected_channel()
  local param_id = channel.trig_lock_params[i].param_id

  channel_edit_page_ui_controller.sync_param_to_trig_lock(i, channel)

  if channel.trig_lock_banks[i] then
    m_params[i]:set_value(channel.trig_lock_banks[i])
  end
end

function channel_edit_page_ui_controller.refresh_trig_lock_values()
  for i = 1, 10 do
    channel_edit_page_ui_controller.refresh_trig_lock_value(i)
  end
end

function channel_edit_page_ui_controller.refresh_trig_lock(i)
  local channel = program.get_selected_channel()
  local pressed_keys = grid_controller.get_pressed_keys()

  channel_edit_page_ui_controller.refresh_trig_lock_value(i)

  if channel.trig_lock_params[i].id ~= nil then
    m_params[i]:set_name(channel.trig_lock_params[i].name)
    m_params[i]:set_top_label(channel.trig_lock_params[i].short_descriptor_1)
    m_params[i]:set_bottom_label(channel.trig_lock_params[i].short_descriptor_2)
    m_params[i]:set_off_value(channel.trig_lock_params[i].off_value)
    m_params[i]:set_min_value(channel.trig_lock_params[i].cc_min_value)
    m_params[i]:set_max_value(channel.trig_lock_params[i].cc_max_value)
    m_params[i]:set_ui_labels(channel.trig_lock_params[i].ui_labels)

    local step_trig_lock =
      program.get_step_param_trig_lock(program.get_selected_channel(), program.get_selected_channel().current_step, i)

    if #pressed_keys > 0 then
      if (pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8) then
        step_trig_lock =
          program.get_step_param_trig_lock(
          program.get_selected_channel(),
          fn.calc_grid_count(pressed_keys[1][1], pressed_keys[1][2]),
          i
        )
        local default_param = channel.trig_lock_banks[i]
        if channel.trig_lock_params[i].type == "midi" and channel.trig_lock_params[i].param_id then
          default_param = params:lookup_param(channel.trig_lock_params[i].param_id).value
        end
        m_params[i]:set_value(step_trig_lock or default_param)
      end
    else
      if (step_trig_lock and clock_controller.is_playing()) then
        m_params[i]:set_value(step_trig_lock)
      end
    end
  else
    m_params[i]:set_name("")
    m_params[i]:set_top_label("X")
    m_params[i]:set_bottom_label("")
  end
end


function channel_edit_page_ui_controller.refresh_trig_locks()
  for i = 1, 10 do
    channel_edit_page_ui_controller.refresh_trig_lock(i)
  end
end

function channel_edit_page_ui_controller.refresh_param_list()
  local channel = program.get_selected_channel()
  param_select_vertical_scroll_selector:set_items(
    device_map.get_available_params_for_channel(program.get().selected_channel, dials:get_selected_index())
  )
end

function channel_edit_page_ui_controller.refresh_channel_config()
  local channel = program.get_selected_channel()

  if channel.number == 17 then
    return
  end

  device_map_vertical_scroll_selector:set_items(
    device_map.get_available_devices_for_channel(program.get().selected_channel)
  )
  midi_channel_vertical_scroll_selector:set_selected_item(program.get().devices[channel.number].midi_channel)
  midi_device_vertical_scroll_selector:set_selected_item(program.get().devices[channel.number].midi_device)
  device_map_vertical_scroll_selector:set_selected_item(
    fn.get_index_by_id(
      device_map_vertical_scroll_selector:get_items(),
      program.get().devices[channel.number].device_map
    )
  )

  param_select_vertical_scroll_selector:set_selected_item(
    fn.get_index_by_id(
      param_select_vertical_scroll_selector:get_items(),
      channel.trig_lock_params[dials:get_selected_index()].id
    ) or 1
  )

  device_map_vertical_scroll_selector:select()
  midi_channel_vertical_scroll_selector:deselect()
  midi_device_vertical_scroll_selector:deselect()
end

function channel_edit_page_ui_controller.throttled_refresh_channel_config()
  -- Cancel the existing timer if it's running
  if refresh_timer_id then
    clock.cancel(refresh_timer_id)
  end

  -- Set a new timer
  refresh_timer_id =
    clock.run(
    function()
      -- Wait for the throttle time
      clock.sleep(throttle_time)

      -- Perform the actual refresh
      channel_edit_page_ui_controller.refresh_channel_config()

      -- Reset the timer id
      refresh_timer_id = nil
    end
  )
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

return channel_edit_page_ui_controller
