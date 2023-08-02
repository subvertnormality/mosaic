local channel_edit_page_ui_controller = {}

local midi_device_map = include("sinfcommand/lib/midi_device_map")

local quantiser = include("sinfcommand/lib/quantiser")
local Pages = include("sinfcommand/lib/ui_components/Pages")
local Page = include("sinfcommand/lib/ui_components/Page")
local VerticalScrollSelector = include("sinfcommand/lib/ui_components/VerticalScrollSelector")
local Dial = include("sinfcommand/lib/ui_components/Dial")
local ControlScrollSelector = include("sinfcommand/lib/ui_components/ControlScrollSelector")
local ListSelector = include("sinfcommand/lib/ui_components/ListSelector")
local ValueSelector = include("sinfcommand/lib/ui_components/ValueSelector")

local midi_controller = include("sinfcommand/lib/midi_controller")
local clock_controller = include("sinfcommand/lib/clock_controller")

local pages = Pages:new()

local quantizer_vertical_scroll_selector = VerticalScrollSelector:new(30, 25, "Quantizer", quantiser.get_scales())
local romans_vertical_scroll_selector = VerticalScrollSelector:new(105, 25, "Roman Analysis", quantiser.get_scales()[1].romans)
local notes_vertical_scroll_selector = VerticalScrollSelector:new(10, 25, "Notes", quantiser.get_notes())

local clock_mod_list_selector = ListSelector:new(10, 25, "Clock Mod", clock_controller.get_clock_divisions())
local clock_swing_value_selector = ValueSelector:new(70, 25, "Swing", 0, 50)

local midi_device_vertical_scroll_selector = VerticalScrollSelector:new(10, 25, "Midi Device", {})
local midi_channel_vertical_scroll_selector = VerticalScrollSelector:new(45, 25, "Midi Channel", {{name = "CC1", value = 1}, {name = "CC2", value = 2}, {name = "CC3", value = 3}, {name = "CC4", value = 4}, {name = "CC5", value = 5}, {name = "CC6", value = 6}, {name = "CC7", value = 7}, {name = "CC8", value = 8}, {name = "CC9", value = 9}, {name = "CC10", value = 10}, {name = "CC11", value = 11}, {name = "CC12", value = 12}, {name = "CC13", value = 13}, {name = "CC14", value = 14}, {name = "CC15", value = 15}, {name = "CC16", value = 16}})
local midi_device_map_vertical_scroll_selector = VerticalScrollSelector:new(70, 25, "Midi Map", midi_device_map:get_midi_device_map())

local param_select_vertical_scroll_selector = VerticalScrollSelector:new(30, 25, "Params", {})

local param_1 = Dial:new(5, 20, "Param 1", "X", "")
local param_2 = Dial:new(30, 20, "Param 2", "X", "")
local param_3 = Dial:new(55, 20, "Param 3", "X", "")
local param_4 = Dial:new(80, 20, "Param 4", "X", "")
local param_5 = Dial:new(5, 40, "Param 5", "X", "")
local param_6 = Dial:new(30, 40, "Param 6", "X", "")
local param_7 = Dial:new(55, 40, "Param 7", "X", "")
local param_8 = Dial:new(80, 40, "Param 8", "X", "")

local params = {param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8}

local dials = ControlScrollSelector:new(0, 0, {})

local page_to_index = {["Trig Locks"] = 1, ["Clock Mods"] = 2, ["Quantizer"] = 3, ["Midi Config"] = 4}

local quantizer_page = Page:new("", function ()
  quantizer_vertical_scroll_selector:draw()
  romans_vertical_scroll_selector:draw()
  notes_vertical_scroll_selector:draw()
end)

local clock_mods_page = Page:new("Clocks and Swing", function ()
  clock_mod_list_selector:draw()
  clock_swing_value_selector:draw()

end)

local channel_edit_page = Page:new("Config", function ()
  midi_device_vertical_scroll_selector:draw()
  midi_channel_vertical_scroll_selector:draw()
  midi_device_map_vertical_scroll_selector:draw()
end)

local trig_lock_page = Page:new("Trig Locks", function ()
  dials:draw()
end)


function channel_edit_page_ui_controller.init()
  quantizer_vertical_scroll_selector:select()
  midi_channel_vertical_scroll_selector:select()
  midi_device_vertical_scroll_selector:set_items(midi_controller.get_midi_outs())
  dials:set_items({param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8})

  quantizer_page:set_sub_name_func(function ()
    return "Quantizer " .. program.get_selected_channel().default_scale .. " "
  end)

  channel_edit_page:set_sub_name_func(function ()
    return "Ch. " .. program.get().selected_channel .. " "
  end)

  clock_mods_page:set_sub_name_func(function ()
    return "Ch. " .. program.get().selected_channel .. " "
  end)

  trig_lock_page:set_sub_name_func(function ()
    return "Ch. " .. program.get().selected_channel .. " "
  end)

  trig_lock_page:set_sub_page_draw_func(function ()
    param_select_vertical_scroll_selector:draw()
  end)

  pages:add_page(trig_lock_page)
  pages:add_page(clock_mods_page)
  pages:add_page(quantizer_page)
  pages:add_page(channel_edit_page)
  pages:select_page(1)
  dials:set_selected_item(1)
  clock_mod_list_selector:set_selected_value(13)
  clock_mod_list_selector:select()
  clock_swing_value_selector:set_value(0)

  channel_edit_page_ui_controller.refresh()
end

function channel_edit_page_ui_controller.register_ui_draw_handlers() 
  
  draw_handler:register_ui(
    "channel_edit_page",
    function()
      pages:draw()
    end
  )

end

function channel_edit_page_ui_controller.update_scale()
  local channel = program.get_selected_channel()
  local scale = quantizer_vertical_scroll_selector:get_selected_item()
  local chord = romans_vertical_scroll_selector:get_selected_index()
  local root_note = notes_vertical_scroll_selector:get_selected_index() - 1

  program.get().scales[channel.default_scale] = {
    number = scale.number,
    scale = scale.scale,
    chord = chord,
    root_note = root_note
  }
end

function channel_edit_page_ui_controller.update_swing()
  local channel = program.get_selected_channel()
  local swing = clock_swing_value_selector:get_value()

  channel.swing = swing
end

function channel_edit_page_ui_controller.update_clock_mods()
  local channel = program.get_selected_channel()
  local clock_mods = clock_mod_list_selector:get_selected()

  channel.clock_mods = clock_mods
end

function channel_edit_page_ui_controller.update_channel_config()
  local channel = program.get_selected_channel()
  local midi_device = midi_device_vertical_scroll_selector:get_selected_item()
  local midi_channel = midi_channel_vertical_scroll_selector:get_selected_item()
  local midi_device_map = midi_device_map_vertical_scroll_selector:get_selected_item()

  channel.midi_device = midi_device.value
  channel.midi_channel = midi_channel.value
  channel.midi_device_map = midi_device_map.value

  channel_edit_page_ui_controller.refresh_device_selector()
end

function channel_edit_page_ui_controller.change_page(page)
  pages:select_page(page)
end

function channel_edit_page_ui_controller.enc(n, d)
  local channel = program.get_selected_channel()
  if n == 3 then
    for i=1, math.abs(d) do
      if d > 0 then
        if pages:get_selected_page() == page_to_index["Quantizer"] then
          if quantizer_vertical_scroll_selector:is_selected() then
            quantizer_vertical_scroll_selector:scroll_down()
          end
          if romans_vertical_scroll_selector:is_selected() then
            romans_vertical_scroll_selector:scroll_down()
          end
          if notes_vertical_scroll_selector:is_selected() then
            notes_vertical_scroll_selector:scroll_down()
          end
          channel_edit_page_ui_controller.update_scale()
        elseif pages:get_selected_page() == page_to_index["Clock Mods"] then
          if clock_mod_list_selector:is_selected() then
            clock_mod_list_selector:decrement()
            channel_edit_page_ui_controller.update_clock_mods()
          end
          if clock_swing_value_selector:is_selected() then
            clock_swing_value_selector:increment()
            channel_edit_page_ui_controller.update_swing()
          end
        elseif pages:get_selected_page() == page_to_index["Midi Config"] then
          if midi_device_vertical_scroll_selector:is_selected() then
            midi_device_vertical_scroll_selector:scroll_down()
          end
          if midi_channel_vertical_scroll_selector:is_selected() then
            midi_channel_vertical_scroll_selector:scroll_down()
          end
          if midi_device_map_vertical_scroll_selector:is_selected() then
            midi_device_map_vertical_scroll_selector:scroll_down()
          end
          channel_edit_page_ui_controller.update_channel_config()
        elseif pages:get_selected_page() == page_to_index["Trig Locks"] then
          if trig_lock_page:is_sub_page_enabled() then
            param_select_vertical_scroll_selector:scroll_down()
            if param_select_vertical_scroll_selector:get_selected_item().name == "None/Not in device" then
              channel.trig_lock_params[dials:get_selected_index()] = {}
            else
              channel.trig_lock_params[dials:get_selected_index()] = param_select_vertical_scroll_selector:get_selected_item()
            end
            channel_edit_page_ui_controller.refresh_trig_locks()
          else
            local pressed_keys = grid_controller.get_pressed_keys()
            if #pressed_keys > 0 and channel.trig_lock_params[dials:get_selected_index()].id then
              for i, keys in ipairs(pressed_keys) do
                local step = fn.calc_grid_count(keys[1], keys[2])
                program.add_step_param_trig_lock(step, dials:get_selected_index(), (program.get_step_param_trig_lock(program.get_selected_channel(), step, dials:get_selected_index()) or channel.trig_lock_banks[dials:get_selected_index()]) + d)
                dials:get_selected_item():set_value(program.get_step_param_trig_lock(program.get_selected_channel(), step, dials:get_selected_index()) or channel.trig_lock_banks[dials:get_selected_index()])
              end
            elseif channel.trig_lock_params[dials:get_selected_index()].id then
              if channel.trig_lock_banks[dials:get_selected_index()] == {} then
                channel.trig_lock_banks[dials:get_selected_index()] = 0
              end
              channel.trig_lock_banks[dials:get_selected_index()] = channel.trig_lock_banks[dials:get_selected_index()] + d

              if channel.trig_lock_banks[dials:get_selected_index()] > 127 then
                channel.trig_lock_banks[dials:get_selected_index()] = 127
              end
              dials:get_selected_item():set_value(channel.trig_lock_banks[dials:get_selected_index()])
            end
          end
        end


      else
        if pages:get_selected_page() == page_to_index["Quantizer"] then
          if quantizer_vertical_scroll_selector:is_selected() then
            quantizer_vertical_scroll_selector:scroll_up()
          end
          if romans_vertical_scroll_selector:is_selected() then
            romans_vertical_scroll_selector:scroll_up()
          end
          if notes_vertical_scroll_selector:is_selected() then
            notes_vertical_scroll_selector:scroll_up()
          end
          channel_edit_page_ui_controller.update_scale()
        elseif pages:get_selected_page() == page_to_index["Clock Mods"] then
            if clock_mod_list_selector:is_selected() then
              clock_mod_list_selector:increment()
              channel_edit_page_ui_controller.update_clock_mods()
            end
            if clock_swing_value_selector:is_selected() then
              clock_swing_value_selector:decrement()
              channel_edit_page_ui_controller.update_swing()
            end
        elseif pages:get_selected_page() == page_to_index["Midi Config"] then
          if midi_device_vertical_scroll_selector:is_selected() then
            midi_device_vertical_scroll_selector:scroll_up()
          end
          if midi_channel_vertical_scroll_selector:is_selected() then
            midi_channel_vertical_scroll_selector:scroll_up()
          end
          if midi_device_map_vertical_scroll_selector:is_selected() then
            midi_device_map_vertical_scroll_selector:scroll_up()
          end
          channel_edit_page_ui_controller.update_channel_config()
        elseif pages:get_selected_page() == page_to_index["Trig Locks"] then
          if trig_lock_page:is_sub_page_enabled() then
            param_select_vertical_scroll_selector:scroll_up()
            if param_select_vertical_scroll_selector:get_selected_item().name == "None/Not in device" then
              channel.trig_lock_params[dials:get_selected_index()] = {}
            else
              channel.trig_lock_params[dials:get_selected_index()] = param_select_vertical_scroll_selector:get_selected_item()
            end
            channel_edit_page_ui_controller.refresh_trig_locks()
          elseif channel.trig_lock_params[dials:get_selected_index()] then
            local pressed_keys = grid_controller.get_pressed_keys()
            if #pressed_keys > 0 and channel.trig_lock_params[dials:get_selected_index()].id then
              for i, keys in ipairs(pressed_keys) do
                local step = fn.calc_grid_count(keys[1], keys[2])
                program.add_step_param_trig_lock(step, dials:get_selected_index(), program.get_step_param_trig_lock(program.get_selected_channel(), step, dials:get_selected_index() or channel.trig_lock_banks[dials:get_selected_index()]) + d)
                dials:get_selected_item():set_value(program.get_step_param_trig_lock(program.get_selected_channel(), step, dials:get_selected_index() or channel.trig_lock_banks[dials:get_selected_index()]))
              end

            elseif channel.trig_lock_params[dials:get_selected_index()].id then
              if channel.trig_lock_banks[dials:get_selected_index()] == nil then
                channel.trig_lock_banks[dials:get_selected_index()] = 0
              end
              channel.trig_lock_banks[dials:get_selected_index()] = channel.trig_lock_banks[dials:get_selected_index()] + d
              if channel.trig_lock_banks[dials:get_selected_index()] < 0 then
                channel.trig_lock_banks[dials:get_selected_index()] = 0
              end
              dials:get_selected_item():set_value(channel.trig_lock_banks[dials:get_selected_index()])
            end
          end
        end
      end

    end
  end

  if n == 2 then
    for i=1, math.abs(d) do
      if d > 0 then

        if pages:get_selected_page() == page_to_index["Quantizer"] then
          if quantizer_vertical_scroll_selector:is_selected() then
            quantizer_vertical_scroll_selector:deselect()
            romans_vertical_scroll_selector:select()
          elseif romans_vertical_scroll_selector:is_selected() then
            romans_vertical_scroll_selector:deselect()
            notes_vertical_scroll_selector:select()
          elseif notes_vertical_scroll_selector:is_selected() then
            notes_vertical_scroll_selector:deselect()
            quantizer_vertical_scroll_selector:select()
          end
        elseif pages:get_selected_page() == page_to_index["Clock Mods"] then
          if clock_mod_list_selector:is_selected() then
            clock_mod_list_selector:deselect()
            clock_swing_value_selector:select()
          elseif clock_swing_value_selector:is_selected() then
            clock_swing_value_selector:deselect()
            clock_mod_list_selector:select()
          end
        elseif pages:get_selected_page() == page_to_index["Midi Config"] then
          if midi_device_vertical_scroll_selector:is_selected() then
            midi_device_vertical_scroll_selector:deselect()
            midi_channel_vertical_scroll_selector:select()
          elseif midi_channel_vertical_scroll_selector:is_selected() then
            midi_channel_vertical_scroll_selector:deselect()
            midi_device_map_vertical_scroll_selector:select()
          elseif midi_device_map_vertical_scroll_selector:is_selected() then
            midi_device_map_vertical_scroll_selector:deselect()
            midi_device_vertical_scroll_selector:select()
          end
        elseif pages:get_selected_page() == page_to_index["Trig Locks"] then
          if not trig_lock_page:is_sub_page_enabled() then
            dials:scroll_next() 
          end
        end
      else
        if pages:get_selected_page() == page_to_index["Quantizer"] then
          if quantizer_vertical_scroll_selector:is_selected() then
            quantizer_vertical_scroll_selector:deselect()
            notes_vertical_scroll_selector:select()
          elseif romans_vertical_scroll_selector:is_selected() then
            romans_vertical_scroll_selector:deselect()
            quantizer_vertical_scroll_selector:select()
          elseif notes_vertical_scroll_selector:is_selected() then
            notes_vertical_scroll_selector:deselect()
            romans_vertical_scroll_selector:select()
          end
        elseif pages:get_selected_page() == page_to_index["Clock Mods"] then
          if clock_mod_list_selector:is_selected() then
            clock_mod_list_selector:deselect()
            clock_swing_value_selector:select()
          elseif clock_swing_value_selector:is_selected() then
            clock_swing_value_selector:deselect()
            clock_mod_list_selector:select()
          end
        elseif pages:get_selected_page() == page_to_index["Midi Config"] then
          if midi_device_vertical_scroll_selector:is_selected() then
            midi_device_vertical_scroll_selector:deselect()
            midi_device_map_vertical_scroll_selector:select()
          elseif midi_channel_vertical_scroll_selector:is_selected() then
            midi_channel_vertical_scroll_selector:deselect()
            midi_device_vertical_scroll_selector:select()
          elseif midi_device_map_vertical_scroll_selector:is_selected() then
            midi_device_map_vertical_scroll_selector:deselect()
            midi_channel_vertical_scroll_selector:select()
          end
        elseif pages:get_selected_page() == page_to_index["Trig Locks"] then
          if not trig_lock_page:is_sub_page_enabled() then
            dials:scroll_previous()
          end
        end
      end
    end
  end

  if n == 1 then 
    for i=1, math.abs(d) do
      if d > 0 then
        pages:next_page()
        fn.dirty_screen(true)

      else
        pages:previous_page()
        fn.dirty_screen(true)
      end
    end
  end

end


function channel_edit_page_ui_controller.key(n, z) 
  if n == 2 and z == 1 then
    channel_edit_page_ui_controller.refresh_device_selector()
    trig_lock_page:toggle_sub_page()
  end
  if n == 3 and z == 1 then
    local pressed_keys = grid_controller.get_pressed_keys()
    if #pressed_keys > 0 then
      for i, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        program.clear_trig_locks_for_step(step)
        dials:get_selected_item():set_value(program.get_step_param_trig_lock(program.get_selected_channel(), step, dials:get_selected_index()) or program.get_selected_channel().trig_lock_banks[dials:get_selected_index()])
        channel_edit_page_ui_controller.refresh_trig_locks()
      end
    end
  end
end

function channel_edit_page_ui_controller.refresh_clock_mods()
  local channel = program.get_selected_channel()
  local clock_mods = channel.clock_mods
  local i = fn.find_index_in_table_by_value(clock_controller.get_clock_divisions(), channel.clock_mods)
  clock_mod_list_selector:set_selected_value(i)

end


function channel_edit_page_ui_controller.refresh_swing()
  local channel = program.get_selected_channel()
  clock_swing_value_selector:set_value(channel.swing)
end

function channel_edit_page_ui_controller.refresh_device_selector()
  local channel = program.get_selected_channel()

  local device = midi_device_map.get_midi_device(channel.midi_device_map)

  param_select_vertical_scroll_selector:set_items(device)
end


function channel_edit_page_ui_controller.refresh_quantiser()
  local channel = program.get_selected_channel()
  if (program.get().scales[channel.default_scale]) then
    local number = program.get().scales[channel.default_scale].number
    local chord = program.get().scales[channel.default_scale].chord
    local root_note = program.get().scales[channel.default_scale].root_note
    program.get_selected_sequencer_pattern().active = true
    quantizer_vertical_scroll_selector:set_selected_item(number)
    notes_vertical_scroll_selector:set_selected_item(root_note + 1)
    romans_vertical_scroll_selector:set_selected_item(chord)

    fn.dirty_screen(true)
  end
end


function channel_edit_page_ui_controller.refresh_trig_locks()
  local channel = program.get_selected_channel()

  for i=1,8 do
    params[i]:set_value(channel.trig_lock_banks[i])
    if channel.trig_lock_params[i].id ~= nil then
      params[i]:set_name(channel.trig_lock_params[i].name)
      params[i]:set_top_label(channel.trig_lock_params[i].short_descriptor_1)
      params[i]:set_bottom_label(channel.trig_lock_params[i].short_descriptor_2)

      local pressed_keys = grid_controller.get_pressed_keys()
      if #pressed_keys > 0 then
        local step = fn.calc_grid_count(pressed_keys[1][1], pressed_keys[1][2])
        params[i]:set_value(program.get_step_param_trig_lock(program.get_selected_channel(), step, i) or channel.trig_lock_banks[i])
      else
        local step = program.get_selected_channel().current_step
        local step_trig_lock = program.get_step_param_trig_lock(program.get_selected_channel(), step, i)

        if (step_trig_lock and clock_controller.is_playing()) then
          params[i]:set_value(step_trig_lock)
        else
          params[i]:set_value(channel.trig_lock_banks[i])
        end
      end

    else
      params[i]:set_name("")
      params[i]:set_top_label("X")
      params[i]:set_bottom_label("")
    end
  end
  
end

function channel_edit_page_ui_controller.refresh_channel_config()
  local channel = program.get_selected_channel()
  midi_channel_vertical_scroll_selector:set_selected_item(channel.midi_channel)
  midi_device_vertical_scroll_selector:set_selected_item(channel.midi_device)
  midi_device_map_vertical_scroll_selector:set_selected_item(channel.midi_device_map)
end


function channel_edit_page_ui_controller.refresh()
  channel_edit_page_ui_controller.refresh_device_selector()
  channel_edit_page_ui_controller.refresh_channel_config()
  channel_edit_page_ui_controller.refresh_trig_locks()
  channel_edit_page_ui_controller.refresh_quantiser()
  channel_edit_page_ui_controller.refresh_clock_mods()
  channel_edit_page_ui_controller.refresh_swing()
end

return channel_edit_page_ui_controller