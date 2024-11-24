

local recorder = {}




function recorder.handle_note_midi_message(note, velocity, chord_number, chord_degree)
  local pressed_keys = m_grid.get_pressed_keys()
  local channel = program.get_selected_channel()
  if #pressed_keys > 0 then
    if (pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8) then

      local s = fn.calc_grid_count(pressed_keys[1][1], pressed_keys[1][2])
      if chord_number == 1 then
        channel_edit_page_ui.add_note_mask_event_portion(
          channel, 
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
        channel_edit_page_ui.add_note_mask_event_portion(
          channel, 
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
      channel_edit_page_ui.add_note_mask_event_portion(
          channel, 
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
      channel_edit_page_ui.add_note_mask_event_portion(
          channel, 
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
