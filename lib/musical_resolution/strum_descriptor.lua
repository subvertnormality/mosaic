local strum_descriptor = {}

function strum_descriptor.new(order_index, delay_for)
  local function play_root_now(chord_strum_pattern, mute_root)
    return not mute_root and
      (not chord_strum_pattern or chord_strum_pattern == 1 or chord_strum_pattern == 3)
  end

  local function resolve_chord(i, chord_notes, chord_strum_pattern,
                               chord_division, chord_spread, chord_acceleration)
    local chord_number = order_index(i, 4, chord_strum_pattern)
    local chord_note = chord_notes[chord_number]
    local delay_multiplier =
      (chord_strum_pattern == 2 or chord_strum_pattern == 4) and i - 1 or i

    if chord_note and chord_note ~= 0 then
      local delay = delay_for(
        chord_division,
        chord_spread,
        chord_acceleration,
        delay_multiplier
      )
      if delay ~= nil then
        return chord_number, delay, delay_multiplier
      end
    end
    return nil
  end

  local function resolve_root_later(chord_strum_pattern, mute_root,
                                    chord_division, chord_spread, chord_acceleration)
    if not mute_root and (chord_strum_pattern == 2 or chord_strum_pattern == 4) then
      return delay_for(chord_division, chord_spread, chord_acceleration, 4)
    end
    return nil
  end

  return play_root_now, resolve_chord, resolve_root_later
end

return strum_descriptor
