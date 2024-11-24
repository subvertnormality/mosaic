
local step = include("mosaic/lib/step")
local quantiser = include("mosaic/lib/quantiser")
local divisions = include("mosaic/lib/clock/divisions")

local m_midi = {}

midi_devices = {}
m_midi.note_counts = {}  -- Initialize note counts table

midi_devices = {}

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

    m_midi:note_on(note, velocity, midi_channel, device.midi_device)

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
      channel_edit_page.handle_note_midi_message(note, velocity, chord_state.chord_number, chord_degree)
    else
      channel_edit_page.handle_note_midi_message(note, velocity, 1, nil)
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
  
        -- Add length and record event only on final note
        if stored.step then
          channel_edit_page_ui.add_note_mask_event_portion(
            channel,
            stored.step,
            {
              song_pattern = program.get().selected_song_pattern,
              data = {
                step = stored.step,
                length = closest_division
              }
            }
          )
          channel_edit_page_ui.record_note_mask_event(channel, stored.step)
        end
      end
  
      -- Clean up if no more notes
      if next(chord_state.notes) == nil then
        chord_states[stored.step] = nil
      end
    end
  
    m_midi:note_off(stored.note, 0, midi_channel, device.midi_device)
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



      if data[2] >= 11 and data[2] <= 20 then
        channel_edit_page_ui.select_trig_page()
        channel_edit_page_ui.handle_trig_lock_param_change_by_direction(data[3] - 64, channel, data[2] - 10)
      elseif data[2] >= 1 and data[2] <= 10 then
        channel_edit_page_ui.select_mask_page()
        if data[2] == 1 then
          channel_edit_page_ui.handle_trig_mask_change(data[3] - 64)
        elseif data[2] == 2 then
          channel_edit_page_ui.handle_note_mask_change(data[3] - 64)
        elseif data[2] == 3 then
          channel_edit_page_ui.handle_velocity_mask_change(data[3] - 64)
        elseif data[2] == 4 then
          channel_edit_page_ui.handle_length_mask_change(data[3] - 64)
        elseif data[2] == 5 then
          -- reserved
        elseif data[2] == 6 then
          channel_edit_page_ui.handle_chord_mask_one_change(data[3] - 64)
        elseif data[2] == 7 then
          channel_edit_page_ui.handle_chord_mask_two_change(data[3] - 64)
        elseif data[2] == 8 then
          channel_edit_page_ui.handle_chord_mask_three_change(data[3] - 64)
        elseif data[2] == 9 then
          channel_edit_page_ui.handle_chord_mask_four_change(data[3] - 64)
        elseif data[2] == 10 then
          -- reserved
        end
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

return m_midi