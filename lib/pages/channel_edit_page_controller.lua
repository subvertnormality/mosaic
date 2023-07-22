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

function channel_edit_page_controller:update_button_states() 
  local merge_mode = program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode

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
    channel_pattern_number_merge_mode_button:set_state(string.match(program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode, "(%d+)$") + 2)
    subadd_merge_mode_button:set_state(1)
    average_merge_mode_button:set_state(1)
    skip_merge_mode_button:set_state(1)
  end
end

function channel_edit_page_controller:init()
  
  for s = 1, 16 do
    pattern_buttons["step"..s.."_pattern_button"] = Button:new(s, 2)
  end

  channel_edit_page_controller:update_button_states() 
  channel_octave_fader:set_value(program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].octave + 3)
  update_scale_state() 
  channel_edit_page_controller:update_channel_edit_page_ui()
end


function channel_edit_page_controller:update_channel_edit_page_ui()
  local channel = program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel]

  local selected_sequencer_pattern = program.selected_sequencer_pattern

  for s = 1, 16 do  
    if fn.is_in_set(channel.selected_patterns, s) then
      pattern_buttons["step"..s.."_pattern_button"]:set_state(2)
    else
      pattern_buttons["step"..s.."_pattern_button"]:set_state(1)
    end
  end

  channel_scale_fader:set_value(channel.default_scale)
  channel_octave_fader:set_value(channel.octave + 3)
  channel_edit_page_controller:update_button_states() 
end


function channel_edit_page_controller:register_draw_handlers()
  draw_handler:register_grid(
    "channel_edit_page",
    function()

      local selected_sequencer_pattern = program.selected_sequencer_pattern
      local trigs = program.sequencer_patterns[selected_sequencer_pattern].channels[program.selected_channel].working_pattern.trig_values
      local lengths = program.sequencer_patterns[selected_sequencer_pattern].channels[program.selected_channel].working_pattern.lengths

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

function update_scale_state() 
  local channel = program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel]
  local scale_value = channel_scale_fader:get_value()
  local number = program.scales[program.default_scale].number
  if program.scales[scale_value] and program.scales[scale_value].number then
    number = program.scales[scale_value].number

    print("scale value: "..scale_value)
    print("scale number: "..number)

    channel.default_scale = scale_value
    print("scale set here to "..channel.default_scale)
    channel_edit_page_controller:update_channel_edit_page_ui()
    program.sequencer_patterns[program.selected_sequencer_pattern].active = true
    tooltip:show("Channel "..program.selected_channel.." scale: "..quantiser.get_scale_name_from_index(number))
    channel_edit_page_ui_controller:select_quantizer_item(number)
    fn.dirty_screen(true)
  else
    tooltip:show("Channel "..program.selected_channel.." scale: default")
    channel_edit_page_ui_controller:select_quantizer_item(number)
  end
end

function channel_edit_page_controller:register_press_handlers()

  press_handler:register(
    "channel_edit_page",
    function(x, y)
      return channel_edit_page_sequencer:press(x, y)
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)
      channel_select_fader:press(x, y)
      if channel_select_fader:is_this(x, y) then
        program.selected_channel = channel_select_fader:get_value()
        pattern_controller:update_working_patterns()
        channel_edit_page_controller:update_channel_edit_page_ui()
        tooltip:show("Channel "..program.selected_channel.." selected")
      end
    end
  )
  press_handler:register_dual(
    "channel_edit_page",
    function(x, y, x2, y2)
      local selected_sequencer_pattern = program.selected_sequencer_pattern
      channel_edit_page_sequencer:dual_press(x, y, x2, y2)
      if channel_edit_page_sequencer:is_this(x2, y2) then
        pattern_controller:update_working_patterns()
        program.sequencer_patterns[program.selected_sequencer_pattern].active = true
        tooltip:show("Channel "..program.selected_channel.." length changed")
      end
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)
      if channel_scale_fader:is_this(x, y) then
        print("scale fader pressed")
        channel_scale_fader:press(x, y)
        if channel_scale_fader:is_this(x, y) then
          update_scale_state()
        end

      end
    end
  )
  for s = 1, 16 do  
    press_handler:register(
      "channel_edit_page",
      function(x, y)
        local selected_sequencer_pattern = program.selected_sequencer_pattern
        pattern_buttons["step"..s.."_pattern_button"]:press(x, y)
        if pattern_buttons["step"..s.."_pattern_button"]:is_this(x, y) then
          if pattern_buttons["step"..s.."_pattern_button"]:get_state() == 2 then
            fn.add_to_set(program.sequencer_patterns[selected_sequencer_pattern].channels[program.selected_channel].selected_patterns, x)
            program.sequencer_patterns[program.selected_sequencer_pattern].active = true
            tooltip:show("Pattern "..x.." added to ch. "..program.selected_channel)
          else
            fn.remove_from_set(program.sequencer_patterns[selected_sequencer_pattern].channels[program.selected_channel].selected_patterns, x)
            program.sequencer_patterns[program.selected_sequencer_pattern].active = true
            tooltip:show("Pattern "..x.." removed from ch. "..program.selected_channel)
          end
        end
        if pattern_buttons["step"..s.."_pattern_button"]:is_this(x, y) then
          pattern_controller:update_working_patterns()
          program.sequencer_patterns[program.selected_sequencer_pattern].active = true
        end
      end
    )
  end
  press_handler:register(
    "channel_edit_page",
    function(x, y)

      if channel_pattern_number_merge_mode_button:is_this(x, y) then
        channel_pattern_number_merge_mode_button:press(x, y)

        local merge_mode = program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode
        if string.match(merge_mode, "pattern_number_") and channel_pattern_number_merge_mode_button:get_state() == 1 then
          channel_pattern_number_merge_mode_button:set_state(2)
        end

        program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode = "pattern_number_"..channel_pattern_number_merge_mode_button:get_state() - 1
        program.sequencer_patterns[program.selected_sequencer_pattern].active = true
        pattern_controller:update_working_patterns()
        skip_merge_mode_button:set_state(1)
        average_merge_mode_button:set_state(1)
        subadd_merge_mode_button:set_state(1)
        tooltip:show("Ch. "..program.selected_channel.." merge mode: pattern "..channel_pattern_number_merge_mode_button:get_state() - 1)


      end
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)

      if skip_merge_mode_button:is_this(x, y) then

        local merge_mode = program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode
        if merge_mode == "skip" then
          return
        end

        program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode = "skip"
        program.sequencer_patterns[program.selected_sequencer_pattern].active = true
        pattern_controller:update_working_patterns()
        channel_pattern_number_merge_mode_button:set_state(1)
        average_merge_mode_button:set_state(1)
        subadd_merge_mode_button:set_state(1)
        skip_merge_mode_button:press(x, y)
        tooltip:show("Ch. "..program.selected_channel.." merge mode: "..program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode)
      end
      
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)

      if average_merge_mode_button:is_this(x, y) then

        local merge_mode = program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode
        if merge_mode == "average" then
          return
        end
  
        program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode = "average"
        program.sequencer_patterns[program.selected_sequencer_pattern].active = true
        pattern_controller:update_working_patterns()
        skip_merge_mode_button:set_state(1)
        channel_pattern_number_merge_mode_button:set_state(1)
        subadd_merge_mode_button:set_state(1)
        average_merge_mode_button:press(x, y)
        tooltip:show("Ch. "..program.selected_channel.." merge mode: "..program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode)
      end
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)

      if subadd_merge_mode_button:is_this(x, y) then

        subadd_merge_mode_button:press(x, y)

        local merge_mode = program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode
        if (merge_mode == "add" or merge_mode == "subtract") and subadd_merge_mode_button:get_state() == 1 then
          subadd_merge_mode_button:set_state(2)
        end

        if subadd_merge_mode_button:get_state() == 3 then
          program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode = "add"
        elseif subadd_merge_mode_button:get_state() == 2 then
          program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode = "subtract"
        end
        program.sequencer_patterns[program.selected_sequencer_pattern].active = true
        pattern_controller:update_working_patterns()
        skip_merge_mode_button:set_state(1)
        channel_pattern_number_merge_mode_button:set_state(1)
        average_merge_mode_button:set_state(1)
        tooltip:show("Ch. "..program.selected_channel.." merge mode: "..program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode)
      end
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)

      if channel_octave_fader:is_this(x, y) then
        channel_octave_fader:press(x, y)
        program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].octave = channel_octave_fader:get_value() - 3
        program.sequencer_patterns[program.selected_sequencer_pattern].active = true
        tooltip:show("Ch. "..program.selected_channel.." octave: "..channel_octave_fader:get_value() - 3)
      end

    end
  )
  press_handler:register_dual(
    "channel_edit_page",
    function(x, y, x2, y2)
      if pattern_buttons["step"..x.."_pattern_button"]:is_this(x, y) then
        if channel_pattern_number_merge_mode_button:is_this(x2, y2) then
          channel_pattern_number_merge_mode_button:set_state(x + 1)
          program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].merge_mode = "pattern_number_"..x
          program.sequencer_patterns[program.selected_sequencer_pattern].active = true
          pattern_controller:update_working_patterns()
          skip_merge_mode_button:set_state(1)
          average_merge_mode_button:set_state(1)
          subadd_merge_mode_button:set_state(1)
          tooltip:show("Ch. "..program.selected_channel.." merge mode: pattern "..channel_pattern_number_merge_mode_button:get_state() - 1)
        end
      end
    end
  )
end



return channel_edit_page_controller
