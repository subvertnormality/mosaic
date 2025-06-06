local recorder = {}

-- Stores portions of mask events for consolidation
recorder.mask_events = {}
recorder.trig_lock_events = {}
recorder.trig_lock_dirty = {}

local function init_trig_lock_dirty()
  for i = 1, 16 do
    recorder.trig_lock_dirty[i] = {}
    for j = 1, 10 do
      recorder.trig_lock_dirty[i][j] = false
    end
  end
end

init_trig_lock_dirty()

function recorder.add_note_mask_event_portion(c, step, event_portion)
  if not recorder.mask_events[c] then
    recorder.mask_events[c] = {}
  end
  if not recorder.mask_events[c][step] then
    recorder.mask_events[c][step] = {}
  end

  recorder.mask_events[c][step] = fn.deep_merge_tables(recorder.mask_events[c][step], event_portion)

end

function recorder.record_stored_note_mask_events(c, step)
  if recorder.mask_events and recorder.mask_events[c] and recorder.mask_events[c][step] then
    local event = recorder.mask_events[c][step]

    if not event.data then
      return
    end

    memory.record_event(c, "note_mask", event.data)
    recorder.mask_events[c][step] = nil

  end
end

function recorder.add_trig_lock_event_portion(c, step, event_portion)
  if not recorder.trig_lock_events[c] then
    recorder.trig_lock_events[c] = {}
  end
  if not recorder.trig_lock_events[c][step] then
    recorder.trig_lock_events[c][step] = {}
  end

  recorder.trig_lock_events[c][step] = fn.deep_merge_tables(recorder.trig_lock_events[c][step], event_portion)

end

function recorder.record_stored_trig_lock_events(c, step)
  if recorder.trig_lock_events and recorder.trig_lock_events[c] and recorder.trig_lock_events[c][step] then
    local event = recorder.trig_lock_events[c][step]

    if not event.data then
      return
    end

    memory.record_event(c, "trig_lock", event.data)
    recorder.trig_lock_events[c][step] = nil

  end
end

function recorder.handle_note_midi_message(note, velocity, chord_number, chord_degree)
  local pressed_keys = m_grid.get_pressed_keys()
  local channel = program.get_selected_channel()
  if #pressed_keys > 0 then
    if (pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8) then

      local s = fn.calc_grid_count(pressed_keys[1][1], pressed_keys[1][2])
      if chord_number == 1 then
        recorder.add_note_mask_event_portion(
          channel.number, 
          s, 
          {
            song_pattern = program.get().selected_song_pattern,
            data = {
              trig = 1,
              note = note,
              velocity = velocity,
              length = 1,
              chord_degrees = {nil, nil, nil, nil},
              step = s
            }
          }
        )
      elseif (chord_degree) then
        local chord = {}
        chord[chord_number - 1] = chord_degree 
        recorder.add_note_mask_event_portion(
          channel.number, 
          s, 
          {
            song_pattern = program.get().selected_song_pattern,
            data = {
              step = s,
              chord_degrees = chord
            }
          }
        )
      end

    end
  elseif params:get("record") == 2 then
    local s = program.get_current_step_for_channel(channel.number)
    if chord_number == 1 then
      recorder.add_note_mask_event_portion(
          channel.number, 
          s, 
          {
            song_pattern = program.get().selected_song_pattern,
            data = {
              trig = 1,
              note = note,
              velocity = velocity,
              length = 1,
              chord_degrees = {nil, nil, nil, nil},
              step = s
            }
          }
        )
    elseif (chord_degree) then
      local chord = {}
      chord[chord_number - 1] = chord_degree 
      recorder.add_note_mask_event_portion(
          channel.number, 
          s, 
          {
            song_pattern = program.get().selected_song_pattern,
            data = {
              step = s,
              chord_degrees = chord
            }
          }
        )
    end
  end
end

function recorder.record_trig_event(c, step, parameter)
  if recorder.trig_lock_dirty[c] and recorder.trig_lock_dirty[c][parameter] then
    memory.record_event(c, "trig_lock", {
      parameter = parameter, 
      step = step,
      value = recorder.trig_lock_dirty[c][parameter]
    })
  end
end

function recorder.trig_lock_is_dirty(c, parameter)
  return recorder.trig_lock_dirty[c] and recorder.trig_lock_dirty[c][parameter]
end

function recorder.set_trig_lock_dirty(c, parameter, value)
    recorder.trig_lock_dirty[c][parameter] = value
end

function recorder.clear_trig_lock_dirty(c, parameter)
  recorder.trig_lock_dirty[c][parameter] = false
end

function recorder.clear_all_trig_lock_dirty()
  init_trig_lock_dirty()
end

return recorder