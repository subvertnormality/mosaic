
local step = include("mosaic/lib/step")
local quantiser = include("mosaic/lib/quantiser")
local divisions = include("mosaic/lib/clock/divisions")

local m_midi = {}

midi_devices = {}
m_midi.note_counts = {}  -- Initialize note counts table

local midi_note_mappings = {
  [1] = 1, [2] = 2, [3] = 2, [4] = 3, [5] = 3,
  [6] = 4, [7] = 5, [8] = 5, [9] = 6, [10] = 6,
  [11] = 7, [12] = 7
}

local midi_tables = {}
local midi_off_store = {}
local chord_number = 0
local chord_one_note = nil
local chord_states = {}

local page_change_clock = nil
local previous_page = nil

for i = 0, 127 do
  local note_value = midi_note_mappings[(i % 12) + 1] or 0
  local octave_value = math.floor(i / 12) - 5

  midi_tables[i + 1] = {note_value-1, octave_value}
end

function handle_midi_event_data(data, midi_device)


  local channel = program.get_selected_channel()

  if channel.number == 17 then 
    return 
  end

  local transpose = step.calculate_step_transpose(program.get().current_step, channel.number)
  local device = program.get().devices[channel.number]
  local d = device_map.get_device(device.device_map)
  local midi_channel = device.midi_channel
  local velocity = data[3]

  if data[1] == 144 then -- note on
    if midi_tables[data[2]] == nil then
      return
    end

    local step_scale_number = channel.step_scale_number
    local pressed_keys = m_grid.get_pressed_keys()

    local start_trig = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
    local end_trig = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])

    local s = program.get_current_step_for_channel(channel.number)

    if #pressed_keys > 0 then
      if (pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8) then
        s = fn.calc_grid_count(pressed_keys[1][1], pressed_keys[1][2])
        step_scale_number = step.manually_calculate_step_scale_number(channel.number, s)
      end
    end

    local note = quantiser.process_with_global_params(midi_tables[data[2] + 1][1], midi_tables[data[2] + 1][2], transpose, step_scale_number)
    if params:get("midi_scale_mapped_to_white_keys") == 1 then
      note = data[2]
    end

    if not chord_states[s] then
      chord_states[s] = {
        chord_one_note = nil,
        chord_number = 0,
        notes = {},
        length_recorded = false
      }
    end

    local chord_state = chord_states[s]

    midi_off_store[data[2]] = {
      note = note,
      step = s,
      start_time = util.time()
    }

    if d.player then
      d.player:note_on(note, ((velocity - 1) / 126) or 0)
    else
      m_midi:note_on(note, velocity, midi_channel, device.midi_device)
    end

    -- Handle chord state for this step
    if chord_state.chord_number == 0 then
      chord_state.chord_one_note = data[2]
      chord_state.chord_number = 1
      chord_state.length_recorded = false
    else
        if midi_off_store[chord_state.chord_one_note] and 
          midi_off_store[chord_state.chord_one_note].step == s then
            chord_state.chord_number = chord_state.chord_number + 1
        else
            -- New step or root note released, start new chord
            chord_state.chord_one_note = data[2]
            chord_state.chord_number = 1
            chord_state.length_recorded = false
        end
    end
    
    -- Store this note
    chord_state.notes[data[2]] = true

    local chord_degree = nil
    if chord_state.chord_one_note and 
      midi_off_store[chord_state.chord_one_note] and 
      midi_off_store[chord_state.chord_one_note].step == s then
        chord_degree = quantiser.get_chord_degree(note, midi_off_store[chord_state.chord_one_note].note, step_scale_number)
        if chord_degree < -14 or chord_degree > 14 then
            chord_degree = nil
        end
    end

    -- If we're on same step as chord root, send as part of chord
    -- Otherwise send as new note
    if chord_state.chord_one_note and midi_off_store[chord_state.chord_one_note] and midi_off_store[chord_state.chord_one_note].step == s then
      recorder.handle_note_midi_message(note, velocity, chord_state.chord_number, chord_degree)
    else
      recorder.handle_note_midi_message(note, velocity, 1, nil)
    end
  elseif data[1] == 128 then -- note off
    local stored = midi_off_store[data[2]]
    if stored == nil then return end
  
    local chord_state = chord_states[stored.step]
    if chord_state then
      chord_state.notes[data[2]] = nil
      chord_state.chord_number = chord_state.chord_number - 1
          
      -- If root note released or no more notes, clear chord state
      if data[2] == chord_state.chord_one_note or chord_state.chord_number <= 0 then
        chord_state.chord_one_note = nil
        chord_state.chord_number = 0
      end
  
      -- Only process the length when we're on the last note of the chord
      if chord_state.chord_number <= 0 and not chord_state.length_recorded then
        chord_state.length_recorded = true
        local duration = util.time() - stored.start_time
        local beats_per_second = clock.get_tempo() / 60
  
        local channel = program.get_selected_channel()
        local clock_mods = channel.clock_mods
        local channel_divisor = m_clock.calculate_divisor(clock_mods)
        local channel_division = 1 / (channel_divisor)
        local duration_in_beats = (duration * beats_per_second) / channel_division
  
        -- Find closest note division value
        local closest_division = divisions.note_division_values[1]
        local smallest_diff = math.abs(duration_in_beats - closest_division)
              
        for _, div in ipairs(divisions.note_division_values) do
          local diff = math.abs(duration_in_beats - div)
          if diff < smallest_diff then
            smallest_diff = diff
            closest_division = div
          end
        end
  
        if stored.step and params:get("record") == 2 then
          recorder.add_note_mask_event_portion(
            channel.number,
            stored.step,
            {
              song_pattern = program.get().selected_song_pattern,
              data = {
                step = stored.step,
                length = closest_division
              }
            }
          )
          recorder.record_stored_note_mask_events(channel.number, stored.step)
        end
      end
  
      -- Clean up if no more notes
      if next(chord_state.notes) == nil then
        chord_states[stored.step] = nil
      end
    end
  
    if d.player then
      d.player:note_off(stored.note)
    else
      m_midi:note_off(stored.note, 0, midi_channel, device.midi_device)
    end

    
    midi_off_store[data[2]] = nil
  elseif data[1] == 176 then -- cc change
    if data[2] >= 1 and data[2] <= 20 then

      if (program.get_selected_page() == 2) then
        if not previous_page then
          previous_page = channel_edit_page_ui.get_selected_page()
        end
        if (page_change_clock) then
          clock.cancel(page_change_clock)
        end
        page_change_clock = clock.run(function()
          clock.sleep(2)
          if previous_page then
            channel_edit_page_ui.select_page(previous_page)
            previous_page = nil
            page_change_clock = nil
          end
        end)
      end

    end
  end 
end

function m_midi.init()
  for i = 1, #midi.vports do
    midi_devices[i] = midi.connect(i)
    midi_devices[i].event = function(data) 
      handle_midi_event_data(data, midi_devices[i])
    end
  end

end

function m_midi.get_midi_outs()
  local midi_outs = {}
  for i = 1, #midi.vports do
    if midi_devices[i] and midi_devices[i].name ~= "none" and midi_devices[i].name ~= "Norns2sinfonion" then
      table.insert(
        midi_outs,
        {name = "OUT " .. i, value = i, long_name = util.trim_string_to_width(midi_devices[i].name, 80)}
      )
    end
  end

  return midi_outs
end


function m_midi.send_to_sinfonion(command, value)
  for id = 1, #midi_devices do

    if midi_devices[id] and midi_devices[id].name == "Norns2sinfonion" then
      midi_devices[id]:program_change(value, command)
    end
  end
end

function m_midi:reset_note_counts()
  for device = 1, #midi_devices do
    self.note_counts[device] = nil
  end
end


function m_midi:note_on(note, velocity, channel, device)
  if midi_devices[device] ~= nil then
    -- Initialize tables if necessary
    if not self.note_counts[device] then
      self.note_counts[device] = {}
    end
    if not self.note_counts[device][channel] then
      self.note_counts[device][channel] = {}
    end
    if not self.note_counts[device][channel][note] then
      self.note_counts[device][channel][note] = 0
    end

    -- Increment the note count
    self.note_counts[device][channel][note] = self.note_counts[device][channel][note] + 1

    -- Send the Note On message
    midi_devices[device]:note_on(note, velocity, channel)
  end
end

function m_midi:note_off(note, velocity, channel, device)
  if midi_devices[device] ~= nil then
    -- Check if the note is currently on
    if self.note_counts[device] and self.note_counts[device][channel] and self.note_counts[device][channel][note] then
      -- Decrement the note count
      self.note_counts[device][channel][note] = self.note_counts[device][channel][note] - 1
      if self.note_counts[device][channel][note] <= 0 then
        -- Send Note Off only when count reaches zero
        midi_devices[device]:note_off(note, velocity, channel)
        -- Remove the note from the table
        self.note_counts[device][channel][note] = nil
      end
    else
      -- Note is not currently on, but we received a Note Off.
      -- For safety, send Note Off anyway
      midi_devices[device]:note_off(note, velocity, channel)
    end
  end
end

function m_midi.cc(cc_msb, cc_lsb, value, channel, device)
  if midi_devices[device] ~= nil then
    -- Send MSB
    local cc_msb_value = cc_lsb and math.floor(value / 128) or value
    midi_devices[device]:cc(cc_msb, cc_msb_value, channel)

    -- Send LSB
    if cc_lsb ~= nil then
      midi_devices[device]:cc(cc_lsb, value % 128, channel)
    end
  end
end

function m_midi.nrpn(nrpn_msb, nrpn_lsb, value, channel, device)
  -- Select NRPN (LSB and MSB)
  m_midi.cc(99, nil, nrpn_msb, channel, device)
  m_midi.cc(98, nil, nrpn_lsb, channel, device)


  -- Calculate MSB and LSB from value
  local msb_value = math.floor(value / 128) -- MSB
  local lsb_value = value % 128  -- LSB

  -- Send MSB and LSB values
  m_midi.cc(6, nil, msb_value, channel, device)
  m_midi.cc(38, nil, lsb_value/2, channel, device)

end


function m_midi:program_change(program_id, channel, device)
  if midi_devices[device] ~= nil then
    midi_devices[device]:program_change(program_id, channel)
  end
end

function m_midi.start()

  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      midi_devices[id]:start()
    end
  end

end

function m_midi:all_notes_off()
  for device, channels in pairs(self.note_counts) do
    if midi_devices[device] ~= nil then
      for channel, notes in pairs(channels) do
        for note, count in pairs(notes) do
          if count > 0 then
            -- Send Note Off for the active note
            midi_devices[device]:note_off(note, 0, channel)
            -- Reset the note count for this note
            self.note_counts[device][channel][note] = nil
          end
        end
        -- Clean up empty channel tables
        if next(self.note_counts[device][channel]) == nil then
          self.note_counts[device][channel] = nil
        end
      end
      -- Clean up empty device tables
      if next(self.note_counts[device]) == nil then
        self.note_counts[device] = nil
      end
    end
  end
end

-- Modify the stop function
function m_midi.stop()
  -- Turn off all active notes
  m_midi:all_notes_off()

  -- Stop MIDI devices
  for id = 1, #midi.vports do
    if midi_devices[id] and midi_devices[id].device ~= nil then
      midi_devices[id]:stop()
    end
  end

  -- Reset note counts
  m_midi.note_counts = {}
  chord_number = 0
end


m_midi.all_off = scheduler.debounce(function (id)
  for note = 0, 127 do
    for channel = 1, 16 do
      midi_devices[id]:note_off(note, 0, channel)
    end
    coroutine.yield()
  end
  -- Reset note counts for this device
  m_midi.note_counts[id] = nil
  chord_number = 0
end)

function m_midi.panic()
  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      m_midi.all_off(id)
    end
  end
  -- Clear all note counts
  m_midi.note_counts = {}
  chord_number = 0
end

function m_midi.midi_devices_connected() 
  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      return true
    end
  end
  return false
end


function m_midi.set_up_midi_mapping_params()
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
      controlspec.new(-1,1, 'lin', 1, 1, '', 1, false), 
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
        if param == 1 then
          channel_edit_page_ui.handle_trig_mask_change(program.get_selected_channel(), scaled_d)
        elseif param == 2 then
          channel_edit_page_ui.handle_note_mask_change(program.get_selected_channel(), scaled_d)
        elseif param == 3 then
          channel_edit_page_ui.handle_velocity_mask_change(program.get_selected_channel(), scaled_d)
        elseif param == 4 then
          channel_edit_page_ui.handle_length_mask_change(program.get_selected_channel(), scaled_d)
        elseif param == 5 then
          channel_edit_page_ui.handle_chord_mask_one_change(program.get_selected_channel(), scaled_d)
        elseif param == 6 then
          channel_edit_page_ui.handle_chord_mask_two_change(program.get_selected_channel(), scaled_d)
        elseif param == 7 then
          channel_edit_page_ui.handle_chord_mask_three_change(program.get_selected_channel(), scaled_d)
        elseif param == 8 then
          channel_edit_page_ui.handle_chord_mask_four_change(program.get_selected_channel(), scaled_d)
        end
        params:set("sel_ch_" .. (param == 1 and "trig" or param == 2 and "note" or param == 3 and "vel" or param == 4 and "len" or param == 5 and "ch1" or param == 6 and "ch2" or param == 7 and "ch3" or param == 8 and "ch4"), 0, true)

        channel_edit_page_ui.select_mask_page()
        
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
        controlspec.new(-1,1, 'lin', 1, 1, '', 1, false),
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
          if param == 1 then
            channel_edit_page_ui.handle_trig_mask_change(program.get_channel(program.get().selected_song_pattern, channel), scaled_d)
          elseif param == 2 then
            channel_edit_page_ui.handle_note_mask_change(program.get_channel(program.get().selected_song_pattern, channel), scaled_d)
          elseif param == 3 then
            channel_edit_page_ui.handle_velocity_mask_change(program.get_channel(program.get().selected_song_pattern, channel), scaled_d)
          elseif param == 4 then
            channel_edit_page_ui.handle_length_mask_change(program.get_channel(program.get().selected_song_pattern, channel), scaled_d)
          elseif param == 5 then
            channel_edit_page_ui.handle_chord_mask_one_change(program.get_channel(program.get().selected_song_pattern, channel), scaled_d)
          elseif param == 6 then
            channel_edit_page_ui.handle_chord_mask_two_change(program.get_channel(program.get().selected_song_pattern, channel), scaled_d)
          elseif param == 7 then
            channel_edit_page_ui.handle_chord_mask_three_change(program.get_channel(program.get().selected_song_pattern, channel), scaled_d)
          elseif param == 8 then
            channel_edit_page_ui.handle_chord_mask_four_change(program.get_channel(program.get().selected_song_pattern, channel), scaled_d)
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
      controlspec.new(-1,1, 'lin', 1, 1, '', 1, false),
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

        local scaled_d = d * scaling_factor
        channel_edit_page_ui.handle_trig_lock_param_change_by_direction(scaled_d, program.get_selected_channel(), param)
        params:set("sel_ch_trig_param_" .. param, 0, true)
        channel_edit_page_ui.refresh_trig_locks()
        channel_edit_page_ui.select_trig_page()
        
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
        controlspec.new(-1,1, 'lin', 1, 1, '', 1, false),
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
          channel_edit_page_ui.refresh_trig_locks()
          
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
    controlspec.new(-1,1, 'lin', 1, 1, '', 1, false),
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

      local scaled_d = d * scaling_factor
      channel_edit_page_ui.handle_memory_navigator(program.get_selected_channel().number, scaled_d)
      params:set("sel_ch_memory", 0, true)
      channel_edit_page_ui.select_memory_page()
      
      last_action_time = current_time
    end
  )

  params:add_separator("CHANNEL MEMORY")
  
  for channel = 1, 16 do
    params:add_control(
      "ch" .. channel .. "_memory",
      "Ch." .. channel .. " Memory",
      controlspec.new(-1,1, 'lin', 1, 1, '', 1, false),
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


return m_midi