local quantiser = {}


function quantiser:process(note_number, octave_mod, scale_number)

  local root_note = program.root_note
  local channel = program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel]
  local program_default_scale = program.default_scale
  local channel_default_scale = channel.default_scale
  local channel_step_scale = channel.step_scales[channel.current_step]

  local scale = program.scales[program.default_scale]

  if channel_step_scale > 0 then
    local scale = program.scales[channel_step_scale]
  elseif channel_default_scale > 0 then
    local scale = program.scales[channel_default_scale]
  end



  if note_number >= 7 then

    local octave = math.floor(note_number / 7) + octave_mod
    local note = note_number % 7
    return (scale[note + 1] + (12 * octave)) + root_note

  elseif note_number < 0 then
    local octave = math.floor(note_number / 7) - octave_mod
    local note = note_number % 7
    return (scale[note + 1] - (12 * (octave + 2))) + root_note
    
  else
    return (scale[note_number + 1] + (octave_mod * 12)) + root_note
  end


end

return quantiser