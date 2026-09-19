local pitch_resolution = {}

function pitch_resolution.new(translate_mask, process, snap_to_scale, read_global_full, read_snap)
  return function(note_value, note_mask_value, octave_mod, transpose, scale_number,
                  random_shift, do_pentatonic, fully_quantise_mask)
    if note_mask_value and note_mask_value > -1 then
      local is_mask = true
      fully_quantise_mask =
        (read_global_full() and
          (fully_quantise_mask == 0 or fully_quantise_mask == -1 or fully_quantise_mask == nil)) or
        fully_quantise_mask == 2
      local relative_note_mask_value, octave_mod_offset = translate_mask(note_mask_value, scale_number)

      local note
      if fully_quantise_mask then
        local final_octave = octave_mod + octave_mod_offset
        note = process(
          relative_note_mask_value + random_shift,
          final_octave,
          transpose,
          scale_number,
          do_pentatonic
        )
      elseif read_snap() then
        note = snap_to_scale(note_mask_value + octave_mod * 12 + random_shift, scale_number, transpose)
      else
        note = note_mask_value + random_shift + octave_mod * 12
      end

      return note, relative_note_mask_value, octave_mod_offset, is_mask, fully_quantise_mask
    end

    local shifted_note_value = note_value + random_shift
    local note = process(shifted_note_value, octave_mod, transpose, scale_number, do_pentatonic)
    return note, nil, 0, false, fully_quantise_mask
  end
end

return pitch_resolution
