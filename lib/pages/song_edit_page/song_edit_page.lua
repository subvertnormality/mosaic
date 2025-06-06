local song_edit_page = {}
local channel_pattern_buttons = {}


local refresh_button = {}

local global_pattern_length_fader = fader:new(1, 7, 8, 64)

function song_edit_page.init()
  for s = 1, 96 do
    channel_pattern_buttons["step" .. s .. "_song_pattern_button"] =
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

  global_pattern_length_fader:set_value(program.get_selected_song_pattern().global_pattern_length)

  channel_pattern_buttons["step" .. program.get().selected_song_pattern .. "_song_pattern_button"]:set_state(
    3
  )
end

function song_edit_page.register_draws()
  draw:register_grid(
    "song_edit_page",
    function()
      local song_pattern = program.get().selected_song_pattern
      for s = 1, 96 do
        if refresh_button[s] then
          if song_pattern == s then
            channel_pattern_buttons["step" .. s .. "_song_pattern_button"]:set_state(3)
          elseif program.is_song_pattern_active(s) then
            channel_pattern_buttons["step" .. s .. "_song_pattern_button"]:set_state(2)
          else
            channel_pattern_buttons["step" .. s .. "_song_pattern_button"]:set_state(1)
          end
          refresh_button[s] = false
        end
        channel_pattern_buttons["step" .. s .. "_song_pattern_button"]:draw()
      end
    end
  )

  draw:register_grid(
    "song_edit_page",
    function()
      global_pattern_length_fader:draw()
    end
  )
end

function song_edit_page.register_press()
  press:register(
    "song_edit_page",
    function(x, y)
      local s = fn.calc_grid_count(x, y) + 48
      local previous_selected_pattern = program.get().selected_song_pattern
      if
        channel_pattern_buttons["step" .. s .. "_song_pattern_button"] and
          channel_pattern_buttons["step" .. s .. "_song_pattern_button"]:is_this(x, y)
       then
        local do_func = function()
          channel_pattern_buttons["step" .. s .. "_song_pattern_button"]:set_state(3)
          program.get().selected_song_pattern = s
          tooltip:show("Song sequence " .. s .. " selected")
          
          for channel_number = 1, 17 do
            local channel = program.get_channel(program.get().selected_song_pattern, channel_number)
            m_clock.set_channel_division(channel_number, m_clock.calculate_divisor(channel.clock_mods))
            m_clock.get_clock_lattice().global_pattern_length = program.get_selected_song_pattern().global_pattern_length
            if channel_number ~= 17 then
              channel_edit_page_ui.align_global_and_local_shuffle_feel_values(channel_number)
              channel_edit_page_ui.align_global_and_local_swing_values(channel_number)
              channel_edit_page_ui.align_global_and_local_swing_shuffle_type_values(channel_number)
              channel_edit_page_ui.align_global_and_local_shuffle_basis_values(channel_number)
              channel_edit_page_ui.align_global_and_local_shuffle_amount_values(channel_number)
            end

          end

          if program.is_song_pattern_active(previous_selected_pattern) then
            channel_pattern_buttons["step" .. s .. "_song_pattern_button"]:set_state(2)
          else
            channel_pattern_buttons["step" .. s .. "_song_pattern_button"]:set_state(1)
          end

          refresh_button[previous_selected_pattern] = true
          refresh_button[s] = true

          pattern.update_working_patterns()
          
          song_edit_page.refresh()
          song_edit_page.refresh_faders()
          channel_edit_page_ui.refresh_clock_mods()
          channel_edit_page_ui.refresh_swing()
          channel_edit_page_ui.refresh_swing_shuffle_type()
          channel_edit_page_ui.refresh_shuffle_feel()
          channel_edit_page_ui.refresh_shuffle_basis()
          channel_edit_page_ui.refresh_shuffle_amount()
          
        end

        local blink_cancel_func = function()
          channel_pattern_buttons["step" .. s .. "_song_pattern_button"]:no_blink()
        end

        if m_clock.is_playing() then
          step.execute_blink_cancel_func()
          step.queue_switch_to_next_song_pattern_func(do_func)
          step.queue_switch_to_next_song_pattern_blink_cancel_func(blink_cancel_func)
          step.queue_next_song_pattern(s)

          channel_pattern_buttons["step" .. s .. "_song_pattern_button"]:blink()
        else
          if params:get("elektron_program_changes") == 2 then
            step.process_elektron_program_change(s)
          end
          do_func()
        end

      end
    end
  )
  press:register(
    "song_edit_page",
    function(x, y)
      if global_pattern_length_fader:is_this(x, y) then
        global_pattern_length_fader:press(x, y)

        local song_pattern = program.get().selected_song_pattern
        local new_pattern_length = global_pattern_length_fader:get_value()
        if m_clock.is_playing() then
          tooltip:show("Q'd: Global pattern length: " .. new_pattern_length)
          step.queue_for_pattern_change(function()
            program.get_song_pattern(song_pattern).global_pattern_length = new_pattern_length
            m_clock.get_clock_lattice().pattern_length = new_pattern_length
            program.get().global_step_accumulator = 0
          end)
        else
          program.get_song_pattern(song_pattern).global_pattern_length = new_pattern_length
          m_clock.get_clock_lattice().pattern_length = new_pattern_length
          tooltip:show("Global pattern length: " .. new_pattern_length)
        end
      end
    end
  )
  press:register_dual(
    "song_edit_page",
    function(x, y, x2, y2)
      local pattern = fn.calc_grid_count(x, y) + 48
      local target_pattern = fn.calc_grid_count(x2, y2) + 48
      if
        channel_pattern_buttons["step" .. pattern .. "_song_pattern_button"] and
          channel_pattern_buttons["step" .. pattern .. "_song_pattern_button"]:is_this(x, y) and
          channel_pattern_buttons["step" .. target_pattern .. "_song_pattern_button"] and
          channel_pattern_buttons["step" .. target_pattern .. "_song_pattern_button"]:is_this(x2, y2)
       then
        program.set_song_pattern(pattern, target_pattern)
        refresh_button[pattern] = true
        refresh_button[target_pattern] = true
      end
      song_edit_page.refresh()
    end
  )
end

function song_edit_page.refresh_faders()
  global_pattern_length_fader:set_value(program.get_selected_song_pattern().global_pattern_length)
end

function song_edit_page.refresh()
  song_edit_page_ui.refresh()

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

  song_edit_page.refresh_faders()
end

return song_edit_page
