local channel_edit_page_controller = {}
local pattern_buttons = {}

local quantiser = include("sinfcommand/lib/quantiser")

local channel_edit_page_sequencer = Sequencer:new(4, "channel")
local channel_select_fader = Fader:new(1, 1, 16, 16)
local channel_pattern_number_merge_mode_button = Button:new(13, 8, {
  {"Pattern number merge mode off", 2},
  {"Pattern number 1 merge mode on", 3}, 
  {"Pattern number 2 merge mode on", 4},
  {"Pattern number 3 merge mode on", 5},  
  {"Pattern number 4 merge mode on", 6}, 
  {"Pattern number 5 merge mode on", 7},  
  {"Pattern number 6 merge mode on", 8},  
  {"Pattern number 7 merge mode on", 9},  
  {"Pattern number 8 merge mode on", 10},  
  {"Pattern number 9 merge mode on", 11},  
  {"Pattern number 10 merge mode on", 12},
  {"Pattern number 11 merge mode on", 13},  
  {"Pattern number 12 merge mode on", 14},  
  {"Pattern number 13 merge mode on", 15},  
  {"Pattern number 14 merge mode on", 15},  
  {"Pattern number 15 merge mode on", 15},  
  {"Pattern number 16 merge mode on", 15},  
})
local skip_merge_mode_button = Button:new(14, 8, {
  {"Skip merge mode off", 2},  
  {"Skip merge mode on", 15},  
})
local average_merge_mode_button = Button:new(15, 8, {
  {"Average merge mode off", 2},  
  {"Average merge mode on", 15},  
})
local subadd_merge_mode_button = Button:new(16, 8, {
  {"Add/subtract merge mode off", 2},  
  {"Subtract merge mode on", 7},  
  {"Add merge mode on", 15},  
})
local channel_octave_fader = Fader:new(7, 8, 5, 5)
local channel_scale_fader = Fader:new(1, 3, 16, 16)


function channel_edit_page_controller.init()
  
  for s = 1, 16 do
    pattern_buttons["step"..s.."_pattern_button"] = Button:new(s, 2)
  end

  channel_octave_fader:set_value(program.get_selected_channel().octave + 3)
  channel_edit_page_controller.refresh()
end

function channel_edit_page_controller.register_draw_handlers()
  draw_handler:register_grid(
    "channel_edit_page",
    function()

      local selected_sequencer_pattern = program.get().selected_sequencer_pattern
      local trigs = program.get_selected_channel().working_pattern.trig_values
      local lengths = program.get_selected_channel().working_pattern.lengths

      channel_edit_page_sequencer:draw(trigs, lengths)
    end
  )

  draw_handler:register_grid(
    "channel_edit_page",
    function()

      return channel_select_fader:draw()

    end
  )
  draw_handler:register_grid(
    "channel_edit_page",
    function()

      return channel_scale_fader:draw()

    end
  )
  for s = 1, 16 do  
    draw_handler:register_grid(
      "channel_edit_page",
      function()
        pattern_buttons["step"..s.."_pattern_button"]:draw()
      end
    )
  end
  draw_handler:register_grid(
    "channel_edit_page",
    function()
      return channel_pattern_number_merge_mode_button:draw()
    end
  )
  draw_handler:register_grid(
    "channel_edit_page",
    function()
      return skip_merge_mode_button:draw()
    end
  )
  draw_handler:register_grid(
    "channel_edit_page",
    function()
      return average_merge_mode_button:draw()
    end
  )
  draw_handler:register_grid(
    "channel_edit_page",
    function()
      return subadd_merge_mode_button:draw()
    end
  )
  draw_handler:register_grid(
    "channel_edit_page",
    function()
      return channel_octave_fader:draw()
    end
  )
end


function channel_edit_page_controller.register_press_handlers()

  press_handler:register(
    "channel_edit_page",
    function(x, y)
      if channel_edit_page_sequencer:is_this(x, y) then
        channel_edit_page_ui_controller.refresh_trig_locks()
        channel_edit_page_sequencer:press(x, y)
      end
    end
  )
  press_handler:register_post(
    "channel_edit_page",
    function(x, y)
      if channel_edit_page_sequencer:is_this(x, y) then
        channel_edit_page_ui_controller.refresh_trig_locks()
        channel_edit_page_controller.refresh_faders()
      end
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)
      channel_select_fader:press(x, y)
      if channel_select_fader:is_this(x, y) then
        program.get().selected_channel = channel_select_fader:get_value()
        pattern_controller.update_working_patterns()
        tooltip:show("Channel "..program.get().selected_channel.." selected")
        channel_edit_page_controller.refresh()
      end
    end
  )
  press_handler:register_dual(
    "channel_edit_page",
    function(x, y, x2, y2)
      local selected_sequencer_pattern = program.get().selected_sequencer_pattern
      channel_edit_page_sequencer:dual_press(x, y, x2, y2)
      if channel_edit_page_sequencer:is_this(x2, y2) then
        pattern_controller.update_working_patterns()
        program.get_selected_sequencer_pattern().active = true
        tooltip:show("Channel "..program.get().selected_channel.." length changed")
      end
      if channel_octave_fader:is_this(x2, y2) then
        channel_octave_fader:press(x2, y2)
        local step = fn.calc_grid_count(x, y)
        local channel = program.get_selected_channel()
        local octave_value = channel_octave_fader:get_value()
        if octave_value == channel.octave + 3 then
          program.add_step_octave_trig_lock(step, nil)
        else     
          program.add_step_octave_trig_lock(step, octave_value - 3)
        end
        channel_edit_page_controller.refresh_faders()
      end
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)
      if channel_scale_fader:is_this(x, y) then
        channel_scale_fader:press(x, y)
        if channel_scale_fader:is_this(x, y) then
          local channel = program.get_selected_channel()
          local scale_value = channel_scale_fader:get_value()
          local number = program.get().scales[scale_value].number
          channel.default_scale = scale_value
          channel_edit_page_ui_controller.refresh_quantiser()
          tooltip:show("Ch. "..program.get().selected_channel.." scale: "..quantiser.get_scale_name_from_index(number))
        end
      end
    end
  )
  for s = 1, 16 do  
    press_handler:register(
      "channel_edit_page",
      function(x, y)
        local selected_sequencer_pattern = program.get().selected_sequencer_pattern
        pattern_buttons["step"..s.."_pattern_button"]:press(x, y)
        if pattern_buttons["step"..s.."_pattern_button"]:is_this(x, y) then
          if pattern_buttons["step"..s.."_pattern_button"]:get_state() == 2 then
            fn.add_to_set(program.get_selected_channel().selected_patterns, x)
            program.get_selected_sequencer_pattern().active = true
            tooltip:show("Pattern "..x.." added to ch. "..program.get().selected_channel)
          else
            fn.remove_from_set(program.get_selected_channel().selected_patterns, x)
            program.get_selected_sequencer_pattern().active = true
            tooltip:show("Pattern "..x.." removed from ch. "..program.get().selected_channel)
          end
          pattern_controller.update_working_patterns()
          program.get_selected_sequencer_pattern().active = true
        end
      end
    )
  end
  press_handler:register(
    "channel_edit_page",
    function(x, y)

      if channel_pattern_number_merge_mode_button:is_this(x, y) then
        channel_pattern_number_merge_mode_button:press(x, y)

        local merge_mode = program.get_selected_channel().merge_mode
        if string.match(merge_mode, "pattern_number_") and channel_pattern_number_merge_mode_button:get_state() == 1 then
          channel_pattern_number_merge_mode_button:set_state(2)
        end

        program.get_selected_channel().merge_mode = "pattern_number_"..channel_pattern_number_merge_mode_button:get_state() - 1
        program.get_selected_sequencer_pattern().active = true
        pattern_controller.update_working_patterns()
        skip_merge_mode_button:set_state(1)
        average_merge_mode_button:set_state(1)
        subadd_merge_mode_button:set_state(1)
        tooltip:show("Ch. "..program.get().selected_channel.." merge mode: pattern "..channel_pattern_number_merge_mode_button:get_state() - 1)


      end
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)

      if skip_merge_mode_button:is_this(x, y) then

        local merge_mode = program.get_selected_channel().merge_mode
        if merge_mode == "skip" then
          return
        end

        program.get_selected_channel().merge_mode = "skip"
        program.get_selected_sequencer_pattern().active = true
        pattern_controller.update_working_patterns()
        channel_pattern_number_merge_mode_button:set_state(1)
        average_merge_mode_button:set_state(1)
        subadd_merge_mode_button:set_state(1)
        skip_merge_mode_button:press(x, y)
        tooltip:show("Ch. "..program.get().selected_channel.." merge mode: "..program.get_selected_channel().merge_mode)
      end
      
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)

      if average_merge_mode_button:is_this(x, y) then

        local merge_mode = program.get_selected_channel().merge_mode
        if merge_mode == "average" then
          return
        end
  
        program.get_selected_channel().merge_mode = "average"
        program.get_selected_sequencer_pattern().active = true
        pattern_controller.update_working_patterns()
        skip_merge_mode_button:set_state(1)
        channel_pattern_number_merge_mode_button:set_state(1)
        subadd_merge_mode_button:set_state(1)
        average_merge_mode_button:press(x, y)
        tooltip:show("Ch. "..program.get().selected_channel.." merge mode: "..program.get_selected_channel().merge_mode)
      end
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)

      if subadd_merge_mode_button:is_this(x, y) then

        subadd_merge_mode_button:press(x, y)

        local merge_mode = program.get_selected_channel().merge_mode
        if (merge_mode == "add" or merge_mode == "subtract") and subadd_merge_mode_button:get_state() == 1 then
          subadd_merge_mode_button:set_state(2)
        end

        if subadd_merge_mode_button:get_state() == 3 then
          program.get_selected_channel().merge_mode = "add"
        elseif subadd_merge_mode_button:get_state() == 2 then
          program.get_selected_channel().merge_mode = "subtract"
        end
        program.get_selected_sequencer_pattern().active = true
        pattern_controller.update_working_patterns()
        skip_merge_mode_button:set_state(1)
        channel_pattern_number_merge_mode_button:set_state(1)
        average_merge_mode_button:set_state(1)
        tooltip:show("Ch. "..program.get().selected_channel.." merge mode: "..program.get_selected_channel().merge_mode)
      end
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)

      if channel_octave_fader:is_this(x, y) then
        channel_octave_fader:press(x, y)
        program.get_selected_channel().octave = channel_octave_fader:get_value() - 3
        program.get_selected_sequencer_pattern().active = true
        tooltip:show("Ch. "..program.get().selected_channel.." octave: "..channel_octave_fader:get_value() - 3)
      end

    end
  )
  press_handler:register_dual(
    "channel_edit_page",
    function(x, y, x2, y2)
      if pattern_buttons["step"..x.."_pattern_button"]:is_this(x, y) then
        if channel_pattern_number_merge_mode_button:is_this(x2, y2) then
          channel_pattern_number_merge_mode_button:set_state(x + 1)
          program.get_selected_channel().merge_mode = "pattern_number_"..x
          program.get_selected_sequencer_pattern().active = true
          pattern_controller.update_working_patterns()
          skip_merge_mode_button:set_state(1)
          average_merge_mode_button:set_state(1)
          subadd_merge_mode_button:set_state(1)
          tooltip:show("Ch. "..program.get().selected_channel.." merge mode: pattern "..channel_pattern_number_merge_mode_button:get_state() - 1)
        end
      end
    end
  )
  press_handler:register_pre(
    "channel_edit_page",
    function(x, y)
      if channel_edit_page_sequencer:is_this(x, y) then
        channel_edit_page_ui_controller.refresh_trig_locks()
        channel_edit_page_controller.refresh_faders()
      end
    end
  )
end


function channel_edit_page_controller.refresh_merge_buttons() 
  local merge_mode = program.get_selected_channel().merge_mode

  if merge_mode == "skip" then
    skip_merge_mode_button:set_state(2)
    channel_pattern_number_merge_mode_button:set_state(1)
    average_merge_mode_button:set_state(1)
    subadd_merge_mode_button:set_state(1)
  elseif merge_mode == "average" then
    average_merge_mode_button:set_state(2)
    skip_merge_mode_button:set_state(1)
    channel_pattern_number_merge_mode_button:set_state(1)
    subadd_merge_mode_button:set_state(1)
  elseif merge_mode == "subtract" then
    subadd_merge_mode_button:set_state(2)
    average_merge_mode_button:set_state(1)
    skip_merge_mode_button:set_state(1)
    channel_pattern_number_merge_mode_button:set_state(1)
  elseif merge_mode == "add" then
    subadd_merge_mode_button:set_state(3)
    average_merge_mode_button:set_state(1)
    skip_merge_mode_button:set_state(1)
    channel_pattern_number_merge_mode_button:set_state(1)
  elseif string.match(merge_mode, "pattern_number_") then
    channel_pattern_number_merge_mode_button:set_state(string.match(program.get_selected_channel().merge_mode, "(%d+)$") + 2)
    subadd_merge_mode_button:set_state(1)
    average_merge_mode_button:set_state(1)
    skip_merge_mode_button:set_state(1)
  end

  channel_select_fader:set_value(program.get().selected_channel)
end


function channel_edit_page_controller.refresh_faders()
  local channel = program.get_selected_channel()

  channel_scale_fader:set_value(channel.default_scale)

  local pressed_keys = grid_controller.get_pressed_keys()
  if #pressed_keys > 0 then
    local step = fn.calc_grid_count(pressed_keys[1][1], pressed_keys[1][2])
    local step_octave_trig_lock = program.get_step_octave_trig_lock(step)
    if step_octave_trig_lock then
      channel_octave_fader:set_value(step_octave_trig_lock + 3)
    else
      channel_octave_fader:set_value(channel.octave + 3)
    end
  else
    channel_octave_fader:set_value(channel.octave + 3)
  end
end

function channel_edit_page_controller.refresh_step_buttons()
  local channel = program.get_selected_channel()

  local selected_sequencer_pattern = program.get().selected_sequencer_pattern

  for s = 1, 16 do  
    if pattern_buttons["step"..s.."_pattern_button"] then
      if fn.is_in_set(channel.selected_patterns, s) then
        pattern_buttons["step"..s.."_pattern_button"]:set_state(2)
      else
        pattern_buttons["step"..s.."_pattern_button"]:set_state(1)
      end
    end
  end

end

function channel_edit_page_controller.refresh()
  channel_edit_page_controller.refresh_faders()
  channel_edit_page_controller.refresh_step_buttons()
  channel_edit_page_controller.refresh_merge_buttons()
  channel_edit_page_ui_controller.refresh()
end

return channel_edit_page_controller
