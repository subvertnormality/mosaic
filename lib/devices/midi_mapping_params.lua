-- Registration owns its per-setup shared acceleration state.
local mapping = {}

function mapping.setup()
  local last_action_time = 0
  local action_count = 0
  local scaling_factor = 1
  local MIN_TIME_BETWEEN_ACTIONS = 0.15 -- 100ms threshold for fast scrolling


  params:add_separator("MOSAIC MIDI MAPPING")

  params:add_group("mosaic_mask_midi_maps", "MASK MIDI MAPS", 138)
  params:add_separator("SELECTED CHANNEL MASKS")

  for param = 1, 8 do
    params:add_control(
      "sel_ch_" .. (param == 1 and "trig" or param == 2 and "note" or param == 3 and "vel" or param == 4 and "len" or param == 5 and "ch1" or param == 6 and "ch2" or param == 7 and "ch3" or param == 8 and "ch4"),
      "Selected Ch. " .. (param == 1 and "Trig" or param == 2 and "Note" or param == 3 and "Velocity" or param == 4 and "Length" or param == 5 and "Chord 1" or param == 6 and "Chord 2" or param == 7 and "Chord 3" or param == 8 and "Chord 4"),
      controlspec.new(-1,1, 'lin', 1, 0, '', 1, false),
      function() return "MAP" end
    )
    params:set_action(
      "sel_ch_" .. (param == 1 and "trig" or param == 2 and "note" or param == 3 and "vel" or param == 4 and "len" or param == 5 and "ch1" or param == 6 and "ch2" or param == 7 and "ch3" or param == 8 and "ch4"),
      function(d)
        local current_time = util.time()
        local time_diff = current_time - last_action_time

        if time_diff > MIN_TIME_BETWEEN_ACTIONS then
          action_count = 0
          scaling_factor = 1
        else
          action_count = action_count + 1
          if action_count > 3 then
            scaling_factor = math.min(10, 1 + ((action_count - 3) * 0.5))
          end
        end

        local scaled_d = d * scaling_factor
        local target_song_number = program.get().selected_song_pattern
        local target_channel = program.get_channel(target_song_number, program.get().selected_channel)
        if param == 1 then
          channel_edit_page_ui.handle_trig_mask_change(target_channel, scaled_d, target_song_number)
        elseif param == 2 then
          channel_edit_page_ui.handle_note_mask_change(target_channel, scaled_d, target_song_number)
        elseif param == 3 then
          channel_edit_page_ui.handle_velocity_mask_change(target_channel, scaled_d, target_song_number)
        elseif param == 4 then
          channel_edit_page_ui.handle_length_mask_change(target_channel, scaled_d, target_song_number)
        elseif param == 5 then
          channel_edit_page_ui.handle_chord_mask_one_change(target_channel, scaled_d, target_song_number)
        elseif param == 6 then
          channel_edit_page_ui.handle_chord_mask_two_change(target_channel, scaled_d, target_song_number)
        elseif param == 7 then
          channel_edit_page_ui.handle_chord_mask_three_change(target_channel, scaled_d, target_song_number)
        elseif param == 8 then
          channel_edit_page_ui.handle_chord_mask_four_change(target_channel, scaled_d, target_song_number)
        end
        params:set("sel_ch_" .. (param == 1 and "trig" or param == 2 and "note" or param == 3 and "vel" or param == 4 and "len" or param == 5 and "ch1" or param == 6 and "ch2" or param == 7 and "ch3" or param == 8 and "ch4"), 0, true)

        if (program.get_selected_page() == 2) and (channel_edit_page_ui.get_selected_page() ~= 1) then
          channel_edit_page_ui.select_mask_page()
        end

        last_action_time = current_time
      end
    )
  end

  params:add_separator("CHANNEL MASKS")

  for channel = 1, 16 do
    for param = 1, 8 do
      params:add_control(
        "ch" .. channel .. "_" .. (param == 1 and "trig" or param == 2 and "note" or param == 3 and "vel" or param == 4 and "len" or param == 5 and "chd1" or param == 6 and "chd2" or param == 7 and "chd3" or param == 8 and "chd4"),
        "Ch." .. channel .. " " .. (param == 1 and "Trig" or param == 2 and "Note" or param == 3 and "Vel" or param == 4 and "Len" or param == 5 and "Chd 1" or param == 6 and "Chd 2" or param == 7 and "Chd 3" or param == 8 and "Chd 4") .. " Mask",
        controlspec.new(-1,1, 'lin', 1, 0, '', 1, false),
        function() return "MAP" end
      )
      params:set_action(
        "ch" .. channel .. "_" .. (param == 1 and "trig" or param == 2 and "note" or param == 3 and "vel" or param == 4 and "len" or param == 5 and "chd1" or param == 6 and "chd2" or param == 7 and "chd3" or param == 8 and "chd4"),
        function(d)
          local current_time = util.time()
          local time_diff = current_time - last_action_time

          if time_diff > MIN_TIME_BETWEEN_ACTIONS then
            action_count = 0
            scaling_factor = 1
          else
            action_count = action_count + 1
            if action_count > 3 then
              scaling_factor = math.min(10, 1 + ((action_count - 3) * 0.5))
            end
          end

          local scaled_d = d * scaling_factor
          local target_song_number = program.get().selected_song_pattern
          local target_channel = program.get_channel(target_song_number, channel)
          if param == 1 then
            channel_edit_page_ui.handle_trig_mask_change(target_channel, scaled_d, target_song_number)
          elseif param == 2 then
            channel_edit_page_ui.handle_note_mask_change(target_channel, scaled_d, target_song_number)
          elseif param == 3 then
            channel_edit_page_ui.handle_velocity_mask_change(target_channel, scaled_d, target_song_number)
          elseif param == 4 then
            channel_edit_page_ui.handle_length_mask_change(target_channel, scaled_d, target_song_number)
          elseif param == 5 then
            channel_edit_page_ui.handle_chord_mask_one_change(target_channel, scaled_d, target_song_number)
          elseif param == 6 then
            channel_edit_page_ui.handle_chord_mask_two_change(target_channel, scaled_d, target_song_number)
          elseif param == 7 then
            channel_edit_page_ui.handle_chord_mask_three_change(target_channel, scaled_d, target_song_number)
          elseif param == 8 then
            channel_edit_page_ui.handle_chord_mask_four_change(target_channel, scaled_d, target_song_number)
          end
          params:set("ch" .. channel .. "_" .. (param == 1 and "trig" or param == 2 and "note" or param == 3 and "vel" or param == 4 and "len" or param == 5 and "chd1" or param == 6 and "chd2" or param == 7 and "chd3" or param == 8 and "chd4"), 0, true)

          last_action_time = current_time
        end
      )
    end
  end


  params:add_group("mosaic_trig_param_midi_maps", "TRIG PARAM MIDI MAPS", 172)

  params:add_separator("SELECTED CHANNEL TRIG PARAMS")

  for param = 1, 10 do
    params:add_control(
      "sel_ch_trig_param_" .. param,
      "Selected Ch. Trig Param " .. param,
      controlspec.new(-1,1, 'lin', 1, 0, '', 1, false),
      function() return "MAP" end
    )
    params:set_action(
      "sel_ch_trig_param_" .. param,
      function(d)
        local current_time = util.time()
        local time_diff = current_time - last_action_time

        -- Reset counter if more than threshold between actions
        if time_diff > MIN_TIME_BETWEEN_ACTIONS then
          action_count = 0
          scaling_factor = 1
        else
          -- Only increment counter for rapid movements
          action_count = action_count + 1
          -- Scale up more gradually, starting after several quick movements
          if action_count > 3 then
            scaling_factor = math.min(10, 1 + ((action_count - 3) * 0.5))
          end
        end

        if (program.get_selected_page() == 2) and (channel_edit_page_ui.get_selected_page() ~= 2) then
          channel_edit_page_ui.select_trig_page()
        end

        local scaled_d = d * scaling_factor
        channel_edit_page_ui.handle_trig_lock_param_change_by_direction(scaled_d, program.get_selected_channel(), param)
        params:set("sel_ch_trig_param_" .. param, 0, true)

        last_action_time = current_time
      end
    )
  end

  params:add_separator("CHANNEL TRIG PARAMS")

  for channel = 1, 16 do
    for param = 1, 10 do
      params:add_control(
        "ch_" .. channel .. "_trig_param_" .. param,
        "Ch." .. channel .. " Trig Param " .. param,
        controlspec.new(-1,1, 'lin', 1, 0, '', 1, false),
        function() return "MAP" end
      )
      params:set_action(
        "ch_" .. channel .. "_trig_param_" .. param,
        function(d)
          local current_time = util.time()
          local time_diff = current_time - last_action_time

          -- Reset counter if more than threshold between actions
          if time_diff > MIN_TIME_BETWEEN_ACTIONS then
            action_count = 0
            scaling_factor = 1
          else
            -- Only increment counter for rapid movements
            action_count = action_count + 1
            -- Scale up more gradually, starting after several quick movements
            if action_count > 3 then
              scaling_factor = math.min(10, 1 + ((action_count - 3) * 0.5))
            end
          end

          local scaled_d = d * scaling_factor
          channel_edit_page_ui.handle_trig_lock_param_change_by_direction(scaled_d, program.get_channel(program.get().selected_song_pattern, channel), param)
          params:set("ch_" .. channel .. "_trig_param_" .. param, 0, true)
          last_action_time = current_time
        end
      )
    end
  end


  params:add_group("mosaic_recorder_midi_maps", "MEMORY MIDI MAPS", 19)

  params:add_separator("SELECTED CHANNEL MEMORY")

  -- Add memory navigation parameter
  params:add_control(
    "sel_ch_memory",
    "Selected Ch. Memory",
    controlspec.new(-1,1, 'lin', 1, 0, '', 1, false),
    function() return "MAP" end
  )
  params:set_action(
    "sel_ch_memory",
    function(d)
      local current_time = util.time()
      local time_diff = current_time - last_action_time

      if time_diff > MIN_TIME_BETWEEN_ACTIONS then
        action_count = 0
        scaling_factor = 1
      else
        action_count = action_count + 1
        if action_count > 3 then
          scaling_factor = math.min(10, 1 + ((action_count - 3) * 0.5))
        end
      end

      if (program.get_selected_page() == 2) and (channel_edit_page_ui.get_selected_page() ~= 3) then
        channel_edit_page_ui.select_memory_page()
      end

      local scaled_d = d * scaling_factor
      channel_edit_page_ui.handle_memory_navigator(program.get_selected_channel().number, scaled_d)
      params:set("sel_ch_memory", 0, true)

      last_action_time = current_time
    end
  )

  params:add_separator("CHANNEL MEMORY")

  for channel = 1, 16 do
    params:add_control(
      "ch" .. channel .. "_memory",
      "Ch." .. channel .. " Memory",
      controlspec.new(-1,1, 'lin', 1, 0, '', 1, false),
      function() return "MAP" end
    )
    params:set_action(
      "ch" .. channel .. "_memory",
      function(d)
        local current_time = util.time()
        local time_diff = current_time - last_action_time

        if time_diff > MIN_TIME_BETWEEN_ACTIONS then
          action_count = 0
          scaling_factor = 1
        else
          action_count = action_count + 1
          if action_count > 3 then
            scaling_factor = math.min(10, 1 + ((action_count - 3) * 0.5))
          end
        end

        local scaled_d = d * scaling_factor
        channel_edit_page_ui.handle_memory_navigator(channel, scaled_d)
        params:set("ch" .. channel .. "_memory", 0, true)

        last_action_time = current_time
      end
    )
  end



end


return mapping
