local channel_sequencer_page_controller = {}
local channel_pattern_buttons = {}

local fn = include("mosaic/lib/functions")
local refresh_button = {}

local global_pattern_length_fader = fader:new(1, 7, 16, 64)

function channel_sequencer_page_controller.init()
  for s = 1, 96 do
    channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"] =
      button:new(
      (s - 1) % 16 + 1,
      math.floor((s - 1) / 16) + 1,
      {
        {"Song sequence " .. s .. " off", 2},
        {"Song sequence " .. s .. " on", 7},
        {"Song sequence " .. s .. " active", 15}
      }
    )
    refresh_button[s] = true
  end

  global_pattern_length_fader:set_value(program.get_selected_sequencer_pattern().global_pattern_length)

  channel_pattern_buttons["step" .. program.get().selected_sequencer_pattern .. "_sequencer_pattern_button"]:set_state(
    3
  )
end

function channel_sequencer_page_controller.register_draw_handlers()
  draw_handler:register_grid(
    "channel_sequencer_page",
    function()
      local sequencer_pattern = program.get().selected_sequencer_pattern
      for s = 1, 96 do
        if refresh_button[s] then
          if sequencer_pattern == s then
            channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"]:set_state(3)
          elseif program.is_sequencer_pattern_active(s) then
            channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"]:set_state(2)
          else
            channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"]:set_state(1)
          end
          refresh_button[s] = false
        end
        channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"]:draw()
      end
    end
  )

  draw_handler:register_grid(
    "channel_sequencer_page",
    function()
      global_pattern_length_fader:draw()
    end
  )
end

function channel_sequencer_page_controller.register_press_handlers()
  press_handler:register(
    "channel_sequencer_page",
    function(x, y)
      local s = fn.calc_grid_count(x, y) + 48
      local previous_selected_pattern = program.get().selected_sequencer_pattern
      if
        channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"] and
          channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"]:is_this(x, y)
       then
        local do_func = function()
          channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"]:set_state(3)
          program.get().selected_sequencer_pattern = s
          tooltip:show("Song sequence " .. s .. " selected")
          
          for channel_number = 1, 17 do
            local channel = program.get_channel(channel_number)
            clock_controller.set_channel_division(channel_number, clock_controller.calculate_divisor(channel.clock_mods))
            if channel_number ~= 17 then
              clock_controller.set_channel_swing(channel_number, channel.swing)
            end

            for i = 1, 10 do
              channel_edit_page_ui_controller.sync_param_to_trig_lock(i, program.get_channel(channel_number))
            end
          end

          if program.is_sequencer_pattern_active(previous_selected_pattern) then
            channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"]:set_state(2)
          else
            channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"]:set_state(1)
          end

          refresh_button[previous_selected_pattern] = true
          refresh_button[s] = true
          
          channel_sequencer_page_controller.refresh()
          channel_sequencer_page_controller.refresh_faders()
          channel_edit_page_ui_controller.refresh_clock_mods()
          channel_edit_page_ui_controller.refresh_swing()
        end

        local blink_cancel_func = function()
          channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"]:no_blink()
        end

        if clock_controller.is_playing() then
          step_handler.execute_blink_cancel_func()
          step_handler.queue_switch_to_next_song_pattern_func(do_func)
          step_handler.queue_switch_to_next_song_pattern_blink_cancel_func(blink_cancel_func)
          step_handler.queue_next_song_pattern(s)

          channel_pattern_buttons["step" .. s .. "_sequencer_pattern_button"]:blink()
        else
          if params:get("elektron_program_changes") == 2 then
            step_handler.process_elektron_program_change(s)
          end
          do_func()
        end

      end
    end
  )
  press_handler:register(
    "channel_sequencer_page",
    function(x, y)
      if global_pattern_length_fader:is_this(x, y) then
        global_pattern_length_fader:press(x, y)
        program.get_selected_sequencer_pattern().global_pattern_length = global_pattern_length_fader:get_value()
        tooltip:show("Global pattern length: " .. global_pattern_length_fader:get_value())
      end
    end
  )
  press_handler:register_dual(
    "channel_sequencer_page",
    function(x, y, x2, y2)
      local pattern = fn.calc_grid_count(x, y) + 48
      local target_pattern = fn.calc_grid_count(x2, y2) + 48
      if
        channel_pattern_buttons["step" .. pattern .. "_sequencer_pattern_button"] and
          channel_pattern_buttons["step" .. pattern .. "_sequencer_pattern_button"]:is_this(x, y) and
          channel_pattern_buttons["step" .. target_pattern .. "_sequencer_pattern_button"] and
          channel_pattern_buttons["step" .. target_pattern .. "_sequencer_pattern_button"]:is_this(x2, y2)
       then
        program.set_sequencer_pattern(pattern, target_pattern)
        refresh_button[pattern] = true
        refresh_button[target_pattern] = true
      end
      channel_sequencer_page_controller.refresh()
    end
  )
end

function channel_sequencer_page_controller.refresh_faders()
  global_pattern_length_fader:set_value(program.get_selected_sequencer_pattern().global_pattern_length)
end

function channel_sequencer_page_controller.refresh()
  channel_sequencer_page_ui_controller.refresh()

  refresh_button = {
    true, true, true, true, true, true, true, true, true, true, 
    true, true, true, true, true, true, true, true, true, true, 
    true, true, true, true, true, true, true, true, true, true,
    true, true, true, true, true, true, true, true, true, true, 
    true, true, true, true, true, true, true, true, true, true,
    true, true, true, true, true, true, true, true, true, true,
    true, true, true, true, true, true, true, true, true, true,
    true, true, true, true, true, true, true, true, true, true,
    true, true, true, true, true, true, true, true, true, true,
    true, true, true, true, true, true
  }

  channel_sequencer_page_controller.refresh_faders()
end

return channel_sequencer_page_controller
