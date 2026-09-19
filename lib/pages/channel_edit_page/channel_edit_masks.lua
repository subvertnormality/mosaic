local channel_edit_masks = {}

function channel_edit_masks.new(mask_selectors, public_handlers, divisions)
  local handlers = {}
  local function held_step_keys()
    local keys = {}
    for _, key in ipairs(m_grid.get_pressed_keys()) do
      if key[2] > 3 and key[2] < 8 then
        table.insert(keys, key)
      end
    end
    return keys
  end
  
  function handlers.handle_trig_mask_change(channel, direction, song_pattern_number)
    local target_song_number = song_pattern_number or program.get().selected_song_pattern
    local pressed_keys = held_step_keys()
    -- Held steps belong to the selected channel's page; a fixed map for another channel edits its
    -- channel mask from its own value (arbitrated 2026-09-11, fixed-map-ignores-held-steps).
    if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 and channel.number == program.get_selected_channel().number then
      if direction > 0 then
        mask_selectors.trig:increment()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                trig = mask_selectors.trig:get_value()
              }
            }
        )
        end
      else
        mask_selectors.trig:decrement()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                trig = mask_selectors.trig:get_value() == -1 and nil or mask_selectors.trig:get_value()
              }
            }
          )
        end
      end
    else
      mask_selectors.trig:set_value(channel.trig_mask or -1)
      if direction > 0 then
        mask_selectors.trig:increment()
        program.set_trig_mask(channel, mask_selectors.trig:get_value())
      else
        mask_selectors.trig:decrement()
        program.set_trig_mask(channel, mask_selectors.trig:get_value() == -1 and nil or mask_selectors.trig:get_value())
      end
      pattern.update_working_pattern(channel.number, program.get_song_pattern(target_song_number))
    end
  end
  
  
  function handlers.handle_note_mask_change(channel, direction, song_pattern_number)
    local target_song_number = song_pattern_number or program.get().selected_song_pattern
    local pressed_keys = held_step_keys()
    -- Held steps belong to the selected channel's page; a fixed map for another channel edits its
    -- channel mask from its own value (arbitrated 2026-09-11, fixed-map-ignores-held-steps).
    if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 and channel.number == program.get_selected_channel().number then
      if direction > 0 then
        mask_selectors.note:increment()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                note = mask_selectors.note:get_value()
              }
            }
          )
        end
      else
        mask_selectors.note:decrement()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                note = mask_selectors.note:get_value() == -1 and nil or mask_selectors.note:get_value()
              }
            }
          )
        end
      end
    else
      mask_selectors.note:set_value(channel.note_mask or -1)
      if direction > 0 then
        mask_selectors.note:increment()
        program.set_note_mask(channel, mask_selectors.note:get_value())
      else
        mask_selectors.note:decrement()
        program.set_note_mask(channel, mask_selectors.note:get_value() == -1 and nil or mask_selectors.note:get_value())
      end
      pattern.update_working_pattern(channel.number, program.get_song_pattern(target_song_number))
    end
  end
  
  function handlers.handle_velocity_mask_change(channel, direction, song_pattern_number)
    local target_song_number = song_pattern_number or program.get().selected_song_pattern
    local pressed_keys = held_step_keys()
    -- Held steps belong to the selected channel's page; a fixed map for another channel edits its
    -- channel mask from its own value (arbitrated 2026-09-11, fixed-map-ignores-held-steps).
    if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 and channel.number == program.get_selected_channel().number then
      if direction > 0 then
        mask_selectors.velocity:increment()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                velocity = mask_selectors.velocity:get_value()
              }
            }
          )
        end
      else
        mask_selectors.velocity:decrement()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                velocity = mask_selectors.velocity:get_value() == -1 and nil or mask_selectors.velocity:get_value()
              }
            }
          )
        end
      end
    else
      mask_selectors.velocity:set_value(channel.velocity_mask or -1)
      if direction > 0 then
        mask_selectors.velocity:increment()
        program.set_velocity_mask(channel, mask_selectors.velocity:get_value())
      else
        mask_selectors.velocity:decrement()
        program.set_velocity_mask(channel, mask_selectors.velocity:get_value() == -1 and nil or mask_selectors.velocity:get_value())
      end
      pattern.update_working_pattern(channel.number, program.get_song_pattern(target_song_number))
    end
  end
  
  function handlers.handle_length_mask_change(channel, direction, song_pattern_number)
    local target_song_number = song_pattern_number or program.get().selected_song_pattern
    local pressed_keys = held_step_keys()
    -- Held steps belong to the selected channel's page; a fixed map for another channel edits its
    -- channel mask from its own value (arbitrated 2026-09-11, fixed-map-ignores-held-steps).
    if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 and channel.number == program.get_selected_channel().number then
      if direction > 0 then
        mask_selectors.length:increment()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                length = divisions.note_division_values[mask_selectors.length:get_value()]
              }
            }
          )
        end
      else
        if mask_selectors.length:get_value() ~= 0 then
          mask_selectors.length:decrement()
          for _, keys in ipairs(pressed_keys) do
            local s = fn.calc_grid_count(keys[1], keys[2])
            recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                  step = s,
                  length = divisions.note_division_values[mask_selectors.length:get_value()]
                }
              }
            )
          end
        else
          for _, keys in ipairs(pressed_keys) do
            local s = fn.calc_grid_count(keys[1], keys[2])
            mask_selectors.length:set_value(0)
            recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                  step = s,
                  length = 0
                }
              }
            )
          end
        end
      end
    else
      mask_selectors.length:set_value(divisions.note_division_index(channel.length_mask) or 0)
      if direction > 0 then
        mask_selectors.length:increment()
        program.set_length_mask(channel, divisions.note_division_values[mask_selectors.length:get_value()])
      else
        if mask_selectors.length:get_value() ~= 0 then
          mask_selectors.length:decrement()
          program.set_length_mask(channel, divisions.note_division_values[mask_selectors.length:get_value()])
        else
          mask_selectors.length:set_value(0)
          program.set_length_mask(channel, nil)
        end
      end
      pattern.update_working_pattern(channel.number, program.get_song_pattern(target_song_number))
    end
  end
  
  function handlers.handle_chord_mask_one_change(channel, direction, song_pattern_number)
    local target_song_number = song_pattern_number or program.get().selected_song_pattern
    local pressed_keys = held_step_keys()
    -- Held steps belong to the selected channel's page; a fixed map for another channel edits its
    -- channel mask from its own value (arbitrated 2026-09-11, fixed-map-ignores-held-steps).
    if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 and channel.number == program.get_selected_channel().number then
      if direction > 0 then
        mask_selectors.chords[1]:increment()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                chord_degrees = {mask_selectors.chords[1]:get_value(), nil, nil, nil}
              }
            }
          )
        end
      else
        mask_selectors.chords[1]:decrement()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                chord_degrees = {mask_selectors.chords[1]:get_value() == -1 and nil or mask_selectors.chords[1]:get_value(), nil, nil, nil}
              }
            }
          )
        end
      end
    else
      -- An unset chord mask is X (0), as displayed (bugs.json chord-mask-unset-start-x).
      mask_selectors.chords[1]:set_value(channel.chord_one_mask or 0)
      if direction > 0 then
        mask_selectors.chords[1]:increment()
        program.set_chord_one_mask(channel, mask_selectors.chords[1]:get_value())
      else
        mask_selectors.chords[1]:decrement()
        program.set_chord_one_mask(channel, mask_selectors.chords[1]:get_value() == -1 and nil or mask_selectors.chords[1]:get_value())
      end
    end
  end
  
  function handlers.handle_chord_mask_two_change(channel, direction, song_pattern_number)
    local target_song_number = song_pattern_number or program.get().selected_song_pattern
    local pressed_keys = held_step_keys()
    -- Held steps belong to the selected channel's page; a fixed map for another channel edits its
    -- channel mask from its own value (arbitrated 2026-09-11, fixed-map-ignores-held-steps).
    if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 and channel.number == program.get_selected_channel().number then
      if direction > 0 then
        mask_selectors.chords[2]:increment()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                chord_degrees = {nil, mask_selectors.chords[2]:get_value(), nil, nil}
              }
            }
          )
        end
      else
        mask_selectors.chords[2]:decrement()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                chord_degrees = {nil, mask_selectors.chords[2]:get_value() == -1 and nil or mask_selectors.chords[2]:get_value(), nil, nil}
              }
            }
          )
        end
      end
    else
      mask_selectors.chords[2]:set_value(channel.chord_two_mask or 0)
      if direction > 0 then
        mask_selectors.chords[2]:increment()
        program.set_chord_two_mask(channel, mask_selectors.chords[2]:get_value())
      else
        mask_selectors.chords[2]:decrement()
        program.set_chord_two_mask(channel, mask_selectors.chords[2]:get_value() == -1 and nil or mask_selectors.chords[2]:get_value())
      end
    end
  end
  
  function handlers.handle_chord_mask_three_change(channel, direction, song_pattern_number)
    local target_song_number = song_pattern_number or program.get().selected_song_pattern
    local pressed_keys = held_step_keys()
    -- Held steps belong to the selected channel's page; a fixed map for another channel edits its
    -- channel mask from its own value (arbitrated 2026-09-11, fixed-map-ignores-held-steps).
    if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 and channel.number == program.get_selected_channel().number then
      if direction > 0 then
        mask_selectors.chords[3]:increment()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                chord_degrees = {nil, nil, mask_selectors.chords[3]:get_value(), nil}
              }
            }
          )
        end
      else
        mask_selectors.chords[3]:decrement()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number,
            s,
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                chord_degrees = {nil, nil, mask_selectors.chords[3]:get_value() == -1 and nil or mask_selectors.chords[3]:get_value(), nil}
              }
            }
          )
        end
      end
    else
      mask_selectors.chords[3]:set_value(channel.chord_three_mask or 0)
      if direction > 0 then
        mask_selectors.chords[3]:increment()
        program.set_chord_three_mask(channel, mask_selectors.chords[3]:get_value())
      else
        mask_selectors.chords[3]:decrement()
        program.set_chord_three_mask(channel, mask_selectors.chords[3]:get_value() == -1 and nil or mask_selectors.chords[3]:get_value())
      end
    end
  end
  
  function handlers.handle_chord_mask_four_change(channel, direction, song_pattern_number)
    local target_song_number = song_pattern_number or program.get().selected_song_pattern
    local pressed_keys = held_step_keys()
    -- Held steps belong to the selected channel's page; a fixed map for another channel edits its
    -- channel mask from its own value (arbitrated 2026-09-11, fixed-map-ignores-held-steps).
    if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 and channel.number == program.get_selected_channel().number then
      if direction > 0 then
        mask_selectors.chords[4]:increment()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                chord_degrees = {nil, nil, nil, mask_selectors.chords[4]:get_value()}
              }
            }
          )
        end
      else
        mask_selectors.chords[4]:decrement()
        for _, keys in ipairs(pressed_keys) do
          local s = fn.calc_grid_count(keys[1], keys[2])
          recorder.add_note_mask_event_portion(
            channel.number, 
            s, 
            {
              song_pattern = target_song_number,
              data = {
                step = s,
                chord_degrees = {nil, nil, nil, mask_selectors.chords[4]:get_value() == -1 and nil or mask_selectors.chords[4]:get_value()}
              }
            }
          )
        end
      end
    else
      mask_selectors.chords[4]:set_value(channel.chord_four_mask or 0)
      if direction > 0 then
        mask_selectors.chords[4]:increment()
        program.set_chord_four_mask(channel, mask_selectors.chords[4]:get_value())
      else
        mask_selectors.chords[4]:decrement()
        program.set_chord_four_mask(channel, mask_selectors.chords[4]:get_value() == -1 and nil or mask_selectors.chords[4]:get_value())
      end
    end
  end
  
  -- Handlers for specific actions
  function handlers.handle_mask_page_change(direction)
      if mask_selectors.trig:is_selected() then
        public_handlers.handle_trig_mask_change(program.get_selected_channel(), direction)
      end
      if mask_selectors.note:is_selected() then
        public_handlers.handle_note_mask_change(program.get_selected_channel(), direction)
      end
      if mask_selectors.velocity:is_selected() then
        public_handlers.handle_velocity_mask_change(program.get_selected_channel(), direction)
      end
      if mask_selectors.length:is_selected() then
        public_handlers.handle_length_mask_change(program.get_selected_channel(), direction)
      end
      if mask_selectors.chords[1]:is_selected() then
        public_handlers.handle_chord_mask_one_change(program.get_selected_channel(), direction)
      end
      if mask_selectors.chords[2]:is_selected() then
        public_handlers.handle_chord_mask_two_change(program.get_selected_channel(), direction)
      end
      if mask_selectors.chords[3]:is_selected() then
        public_handlers.handle_chord_mask_three_change(program.get_selected_channel(), direction)
      end
      if mask_selectors.chords[4]:is_selected() then
        public_handlers.handle_chord_mask_four_change(program.get_selected_channel(), direction)
      end
  end

  return handlers
end

return channel_edit_masks
