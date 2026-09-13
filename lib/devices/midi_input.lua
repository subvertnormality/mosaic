local midi_input = {}

function midi_input.new(m_midi, step, quantiser, divisions)
  local input = {}
  local midi_note_mappings = {
    [1] = 1, [2] = 2, [3] = 2, [4] = 3, [5] = 3,
    [6] = 4, [7] = 5, [8] = 5, [9] = 6, [10] = 6,
    [11] = 7, [12] = 7
  }

  local midi_tables = {}
  local midi_off_store = {}
  local chord_states = {}

  local page_change_clock = nil
  local previous_page = nil

  for i = 0, 127 do
    local note_value = midi_note_mappings[(i % 12) + 1] or 0
    local octave_value = math.floor(i / 12) - 5

    midi_tables[i + 1] = {note_value-1, octave_value}
  end

  function input.handle(data, midi_device)
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
    local channel = pending_note and program.get_channel(pending_note.song_pattern, pending_note.channel_number) or program.get_selected_channel()

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
        song_pattern = program.get().selected_song_pattern,
        midi_channel = midi_channel,
        midi_device = device.midi_device,
        player = d.player,
        -- A repeated Note On for a held key keeps the earlier onset's release.
        previous = input_notes[data[2]]
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
      -- Count holders: the same key may be held from several sources.
      chord_state.notes[data[2]] = (chord_state.notes[data[2]] or 0) + 1

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
      -- A key held across a Stop no longer belongs to the (reset) chord on its step.
      if chord_state and chord_state.notes[data[2]] then
        local holders = (chord_state.notes[data[2]] or 1) - 1
        chord_state.notes[data[2]] = holders > 0 and holders or nil
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
                song_pattern = stored.song_pattern,
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


      input_notes[data[2]] = stored.previous
    elseif (data[1] & 0xf0) == 176 then -- cc change on any MIDI channel
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

  function input.reset_chords()
    chord_states = {}
  end

  return input
end

return midi_input
