local arp_descriptor = {}

function arp_descriptor.new(order_index)
  return function(chord_notes, chord_strum_pattern, mute_root,
                  note_value, octave_mod, transpose, random_shift)
    local sequenced_chord_notes = {}
    local has_mask = false
    for i = 1, 4 do
      local chord_note = chord_notes[order_index(i, 4, chord_strum_pattern)]
      if chord_note and chord_note ~= 0 then
        has_mask = true
        sequenced_chord_notes[i] = {
          note_value = note_value + chord_note + random_shift,
          octave_mod = octave_mod,
          transpose = transpose
        }
      else
        sequenced_chord_notes[i] = false
      end
    end

    local root = not mute_root and {
      note_value = note_value + random_shift,
      octave_mod = octave_mod,
      transpose = transpose
    } or false

    if not has_mask then
      if not root then
        return nil
      end
      return {root}
    end

    if chord_strum_pattern == 2 or chord_strum_pattern == 4 then
      table.insert(sequenced_chord_notes, root)
    else
      table.insert(sequenced_chord_notes, 1, root)
    end
    return sequenced_chord_notes
  end
end

return arp_descriptor
