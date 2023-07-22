local quantiser = {}

local musicutil = require("musicutil")

local scales = { 
  {name = "Chromatic", value = musicutil.generate_scale(0, "chromatic", 1)}, 
  {name = "Major", value = musicutil.generate_scale(0, "major", 1)},
  {name = "Harmonic Major", value = musicutil.generate_scale(0, "harmonic_major", 1)},
  {name = "Minor", value = musicutil.generate_scale(0, "minor", 1)}, 
  {name = "Harmonic Minor", value = musicutil.generate_scale(0, "harmonic_minor", 1)},
  {name = "Melodic Minor", value = musicutil.generate_scale(0, "melodic_minor", 1)},
  {name = "Dorian", value = musicutil.generate_scale(0, "dorian", 1)}, 
  {name = "Phrygian", value = musicutil.generate_scale(0, "phrygian", 1)}, 
  {name = "Lydian", value = musicutil.generate_scale(0, "lydian", 1)}, 
  {name = "Lydian Minor", value = musicutil.generate_scale(0, "lydian_minor", 1)},
  {name = "Mixolydian", value = musicutil.generate_scale(0, "mixolydian", 1)},
  {name = "Locrian", value = musicutil.generate_scale(0, "locrian", 1)}, 
  {name = "Whole Tone", value = musicutil.generate_scale(0, "whole_tone", 1)}, 
  {name = "Pentatonic Major", value = musicutil.generate_scale(0, "major_pentatonic", 1)}, 
  {name = "Pentatonic Minor", value = musicutil.generate_scale(0, "minor_pentatonic", 1)},
  {name = "Major Bebop", value = musicutil.generate_scale(0, "major_bebop", 1)},
  {name = "Altered Scale", value = musicutil.generate_scale(0, "altered_scale", 1)},
  {name = "Dorian Bebop", value = musicutil.generate_scale(0, "dorian_bebop", 1)},
  {name = "Mixolydian Bebop", value = musicutil.generate_scale(0, "mixolydian_bebop", 1)},
  {name = "Blues Scale", value = musicutil.generate_scale(0, "blues_scale", 1)},
  {name = "Diminished Whole Half", value = musicutil.generate_scale(0, "diminished_whole_half", 1)},
  {name = "Diminished Half Whole", value = musicutil.generate_scale(0, "diminished_half_whole", 1)},
  {name = "Neapolitan Major", value = musicutil.generate_scale(0, "neapolitan_major", 1)},
  {name = "Hungarian Major", value = musicutil.generate_scale(0, "hungarian_major", 1)},
  {name = "Harmonic Major", value = musicutil.generate_scale(0, "harmonic_major", 1)},
  {name = "Hungarian Minor", value = musicutil.generate_scale(0, "hungarian_minor", 1)},
  {name = "Neapolitan Minor", value = musicutil.generate_scale(0, "neapolitan_minor", 1)},
  {name = "Major Locrian", value = musicutil.generate_scale(0, "major_locrian", 1)},
  {name = "Leading Whole Tone", value = musicutil.generate_scale(0, "leading_whole_tone", 1)},
  {name = "Six Tone Symmetrical", value = musicutil.generate_scale(0, "six_tone_symmetrical", 1)},
  {name = "Balinese", value = musicutil.generate_scale(0, "balinese", 1)},
  {name = "Persian", value = musicutil.generate_scale(0, "persian", 1)},
  {name = "East Indian Purvi", value = musicutil.generate_scale(0, "east_indian_purvi", 1)},
  {name = "Oriental", value = musicutil.generate_scale(0, "oriental", 1)},
  {name = "Double Harmonic", value = musicutil.generate_scale(0, "double_harmonic", 1)},
  {name = "Enigmatic", value = musicutil.generate_scale(0, "enigmatic", 1)},
  {name = "Overtone", value = musicutil.generate_scale(0, "overtone", 1)},
  {name = "Eight Tone Spanish", value = musicutil.generate_scale(0, "eight_tone_spanish", 1)},
  {name = "Prometheus", value = musicutil.generate_scale(0, "prometheus", 1)},
  {name = "Gagaku Rittsu Sen Pou", value = musicutil.generate_scale(0, "gagaku_rittsu_sen_pou", 1)},
  {name = "In Sen Pou", value = musicutil.generate_scale(0, "in_sen_pou", 1)},
  {name = "Okinawa", value = musicutil.generate_scale(0, "okinawa", 1)},
}

function quantiser.get_scales()
  return scales
end

function quantiser.get_scale_name_from_index(i)
  return scales[i].name
end

function quantiser:process(note_number, octave_mod, scale_number, channel)

  local root_note = program.root_note
  local program_default_scale = program.default_scale
  local channel_default_scale = channel.default_scale
  local channel_step_scale = channel.step_scales[channel.current_step]

  local scale = program.scales[program.default_scale].scale

  if channel_step_scale > 0 then
    scale = program.scales[channel_step_scale].scale
  elseif channel_default_scale > 0 then
    scale = program.scales[channel_default_scale].scale
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