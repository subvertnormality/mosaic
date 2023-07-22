local quantiser = {}

local musicutil = require("musicutil")

local scales = { 
  {name = "Major", value = musicutil.generate_scale(0, "major", 1), romans = {"I", "ii", "iii", "IV", "V", "vi", "vii°"}},
  {name = "Harmonic Major", value = musicutil.generate_scale(0, "harmonic_major", 1), romans = {"I", "ii", "iii", "IV", "V", "♭VI+", "vii°"}},
  {name = "Minor", value = musicutil.generate_scale(0, "minor", 1), romans = {"i", "ii°", "♭III", "iv", "v", "♭VI", "♭VII"}},
  {name = "Harmonic Minor", value = musicutil.generate_scale(0, "harmonic_minor", 1), romans = {"i", "ii°", "♭III+", "iv", "V", "♭VI", "vii°"}},
  {name = "Melodic Minor", value = musicutil.generate_scale(0, "melodic_minor", 1), romans = {"i", "ii", "♭III+", "IV", "V", "vi°", "vii°"}},
  {name = "Dorian", value = musicutil.generate_scale(0, "dorian", 1), romans = {"i", "ii", "♭III", "IV", "v", "vi°", "♭VII"}},
  {name = "Phrygian", value = musicutil.generate_scale(0, "phrygian", 1), romans = {"i", "♭II", "♭III", "iv", "v°", "♭VI", "♭VII"}},
  {name = "Lydian", value = musicutil.generate_scale(0, "lydian", 1), romans = {"I", "II", "iii", "#IV°", "V", "vi", "vii"}},
  {name = "Lydian Minor", value = musicutil.generate_scale(0, "lydian_minor", 1), romans = {"I", "II", "iii", "#IV°", "v", "♭VI", "♭VII"}},
  {name = "Mixolydian", value = musicutil.generate_scale(0, "mixolydian", 1), romans = {"I", "ii", "iii°", "IV", "v", "vi", "♭VII"}},
  {name = "Locrian", value = musicutil.generate_scale(0, "locrian", 1), romans = {"i°", "♭II", "♭iii", "iv", "♭V", "♭VI", "♭VII"}},
  {name = "Locrian Major", value = musicutil.generate_scale(0, "major_locrian", 1), romans = {"I", "ii°", "♭iii", "IV", "♭V", "♭VI", "♭VII"}},
}

local notes = {
  "C",
  "D♭",
  "D",
  "E♭",
  "E",
  "F",
  "G♭",
  "G",
  "A♭",
  "A",
  "B♭",
  "B"
}

function quantiser.get_scales()
  return scales
end

function quantiser.get_notes()
  return notes
end

function quantiser.get_scale_name_from_index(i)
  return scales[i].name
end

function quantiser:process(note_number, octave_mod, scale_number, channel)

  local root_note = program.root_note

  if channel.root_note > -1 then
    root_note = channel.root_note
  end

  local chord_rotation = program.chord - 1

  if channel.chord > -1 then
    chord_rotation = channel.chord - 1
  end
  
  local program_default_scale = program.default_scale
  local channel_default_scale = channel.default_scale
  local channel_step_scale = channel.step_scales[channel.current_step]

  local scale = program.scales[program.default_scale].scale

  if channel_step_scale > 0 then
    scale = program.scales[channel_step_scale].scale
  elseif channel_default_scale > 0 then
    scale = program.scales[channel_default_scale].scale
  end

  if chord_rotation > 0 then
    scale = fn.rotate_table_left(scale, chord_rotation)
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