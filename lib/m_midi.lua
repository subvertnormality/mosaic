
local step = include("mosaic/lib/step")
local quantiser = include("mosaic/lib/quantiser")
local divisions = include("mosaic/lib/clock/divisions")

local nrpn_codec = include("mosaic/lib/devices/nrpn_codec")
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
  -- Keyboard notes target the selected Mosaic channel, regardless of input channel.
  local message_type = data[1] & 0xf0
  local input_notes
  if message_type == 0x80 or message_type == 0x90 then
    local source = midi_device or false
    local input_channel = data[1] & 0x0f
    midi_off_store[source] = midi_off_store[source] or {}
    local source_channels = midi_off_store[source]
    source_channels[input_channel] = source_channels[input_channel] or {}
    input_notes = source_channels[input_channel]
    data = {message_type, data[2], data[3]}
  end
  -- MIDI Note On with zero velocity is a release, as in norns midi.to_msg.
  -- Use a new packet so other listeners retain the original input bytes.
  if data[1] == 144 and data[3] == 0 then
    data = {128, data[2], 0}
  end


  local pending_note = data[1] == 128 and input_notes[data[2]]
  local channel = pending_note and program.get_channel(program.get().selected_song_pattern, pending_note.channel_number) or program.get_selected_channel()

  if channel.number == 17 then 
    return 
  end

  local transpose = step.calculate_step_transpose(channel.number)
  local device = program.get().devices[channel.number]
  local d = device_map.get_device(device.device_map)
  local midi_channel = device.midi_channel
  local velocity = data[3]

  if data[1] == 144 then -- note on
    if midi_tables[data[2] + 1] == nil then
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
    else
      step_scale_number = step.calculate_step_scale_number(channel.number, s)
    end

    local note = quantiser.process_with_global_params(midi_tables[data[2] + 1][1], midi_tables[data[2] + 1][2], transpose, step_scale_number)
    if params:get("midi_scale_mapped_to_white_keys") == 1 then
      note = data[2]
    end

    local recording = params:get("record") == 2
    chord_states[channel.number] = chord_states[channel.number] or {}
    local recording_groups = chord_states[channel.number]
    recording_groups[recording] = recording_groups[recording] or {}
    local channel_chords = recording_groups[recording]
    if not channel_chords[s] then
      channel_chords[s] = {
        chord_one_note = nil,
        chord_number = 0,
        notes = {},
        length_recorded = false
      }
    end

    local chord_state = channel_chords[s]

    input_notes[data[2]] = {
      note = note,
      step = s,
      start_time = util.time(),
      recording = recording,
      channel_number = channel.number,
      midi_channel = midi_channel,
      midi_device = device.midi_device,
      player = d.player
    }

    if d.player then
      d.player:note_on(note, ((velocity - 1) / 126) or 0)
    else
      m_midi:note_on(note, velocity, midi_channel, device.midi_device)
    end

    -- The chord survives individual releases while another voice is held.
    -- Preserve its root and onset independently of the root key's lifetime.
    if chord_state.chord_number == 0 then
      chord_state.chord_one_note = data[2]
      chord_state.root_note = note
      chord_state.start_time = input_notes[data[2]].start_time
      chord_state.voice_count = 0
      chord_state.length_recorded = false
    end
    chord_state.chord_number = chord_state.chord_number + 1
    -- Recorded voice slots do not become reusable when a key is released.
    chord_state.voice_count = chord_state.voice_count + 1
    chord_state.notes[data[2]] = true

    local chord_degree = quantiser.get_chord_degree(note, chord_state.root_note, step_scale_number)
    if chord_degree < -14 or chord_degree > 14 then
      chord_degree = nil
    end
    recorder.handle_note_midi_message(note, velocity, chord_state.voice_count, chord_degree)
  elseif data[1] == 128 then -- note off
    local stored = input_notes[data[2]]
    if stored == nil then return end
  
    local recording_groups = chord_states[stored.channel_number] or {}
    local channel_chords = recording_groups[stored.recording] or {}
    local chord_state = channel_chords[stored.step]
    if chord_state then
      chord_state.notes[data[2]] = nil
      chord_state.chord_number = chord_state.chord_number - 1
          
      -- Retain the active chord until every held voice has been released.
      if chord_state.chord_number <= 0 then
        chord_state.chord_one_note = nil
        chord_state.chord_number = 0
      end
  
      -- Only process the length when we're on the last note of the chord
      if chord_state.chord_number <= 0 and not chord_state.length_recorded then
        chord_state.length_recorded = true
        local duration = util.time() - chord_state.start_time
        local beats_per_second = clock.get_tempo() / 60
  
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
  
        if stored.step and stored.recording then
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
        channel_chords[stored.step] = nil
      end
    end
  
    if stored.player then
      stored.player:note_off(stored.note)
    else
      m_midi:note_off(stored.note, 0, stored.midi_channel, stored.midi_device)
    end

    
    input_notes[data[2]] = nil
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
    -- Composed scale/chord/merge/octave operations may exceed MIDI's
    -- seven-bit note domain. Normalize at the final MIDI-only boundary.
    note = fn.constrain(0, 127, note)
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
    -- Use the same normalized key as note_on so ownership cannot strand.
    note = fn.constrain(0, 127, note)
    -- Check if the note is currently on
    if self.note_counts[device] and self.note_counts[device][channel] and self.note_counts[device][channel][note] then
      -- Decrement the note count
      self.note_counts[device][channel][note] = self.note_counts[device][channel][note] - 1
      -- Every emitted Note On owns a Note Off, including overlapping pitches.
      -- Retain counts for bookkeeping without collapsing receiver releases.
      midi_devices[device]:note_off(note, velocity, channel)
      if self.note_counts[device][channel][note] <= 0 then
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

function m_midi.nrpn(nrpn_msb, nrpn_lsb, value, channel, device, mode)
  -- Validate the whole message before selecting a receiver parameter.
  local msb, lsb = nrpn_codec.encode(value, mode)
  for _,address in ipairs({nrpn_msb, nrpn_lsb}) do
    assert(type(address) == "number" and address % 1 == 0 and address >= 0 and address <= 127,
      "NRPN address must contain two 7-bit integers")
  end
  assert(nrpn_msb ~= nil and nrpn_lsb ~= nil, "NRPN address is required")
  assert(type(channel) == "number" and channel % 1 == 0 and channel >= 1 and channel <= 16,
    "NRPN channel must be from 1 to 16")
  m_midi.cc(99, nil, nrpn_msb, channel, device)
  m_midi.cc(98, nil, nrpn_lsb, channel, device)
  m_midi.cc(6, nil, msb, channel, device)
  m_midi.cc(38, nil, lsb, channel, device)
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
            -- Preserve one release for every owned onset, including distinct
            -- internal notes that clamp to the same MIDI endpoint.
            for _ = 1, count do
              midi_devices[device]:note_off(note, 0, channel)
            end
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
function m_midi.stop(send_transport)
  -- Turn off all active notes
  m_midi:all_notes_off()

  -- Restart cleanup releases voices without sending Stop back to the clock
  -- source. Ordinary Stop retains its transport output on every device.
  if send_transport ~= false then
    for id = 1, #midi.vports do
      if midi_devices[id] and midi_devices[id].device ~= nil then
        midi_devices[id]:stop()
      end
    end
  end

  -- Reset note counts
  m_midi.note_counts = {}
  chord_number = 0
end


local all_off_by_device = {}
function m_midi.all_off(id)
  if not all_off_by_device[id] then
    all_off_by_device[id] = scheduler.debounce(function()
      for note = 0, 127 do
        for channel = 1, 16 do
          midi_devices[id]:note_off(note, 0, channel)
          -- Forget only notes actually cleared by this sweep position.
          -- Notes played behind it still need ownership for transport Stop.
          local channels = m_midi.note_counts[id]
          if channels and channels[channel] then
            channels[channel][note] = nil
          end
        end
        coroutine.yield()
      end
      chord_number = 0
    end)
  end
  all_off_by_device[id]()
end

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


return m_midi