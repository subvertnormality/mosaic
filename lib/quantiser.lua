local quantiser = {}


function quantiser:process(note_number, octave_mod)

  local root_note = program.root_note
  local scale = program.default_scale


  if note_number >= 7 then

    local octave = math.floor(note_number / 7) + octave_mod
    local note = note_number % 7
    return scale[note + 1] + (12 * octave)

  elseif note_number < 0 then
    local octave = math.floor(note_number / 7) - octave_mod
    local note = note_number % 7
    return scale[note + 1] - (12 * (octave + 2))
    
  else
    return scale[note_number + 1] + (octave_mod * 12)
  end


end

return quantiser