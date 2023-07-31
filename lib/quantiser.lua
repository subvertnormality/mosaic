local quantiser = {}

local musicutil = require("musicutil")

local scales = { 
  {name = "Major", number = 1, scale = musicutil.generate_scale(0, "major", 1), romans = {"I", "ii", "iii", "IV", "V", "vi", "vii°"}},
  {name = "Harmonic Major", number = 2, scale = musicutil.generate_scale(0, "harmonic major", 1), romans = {"I", "ii", "iii", "IV", "V", "♭VI+", "vii°"}},
  {name = "Minor", number = 3, scale = musicutil.generate_scale(0, "minor", 1), romans = {"i", "ii°", "♭III", "iv", "v", "♭VI", "♭VII"}},
  {name = "Harmonic Minor", number = 4, scale = musicutil.generate_scale(0, "harmonic minor", 1), romans = {"i", "ii°", "♭III+", "iv", "V", "♭VI", "vii°"}},
  {name = "Melodic Minor", number = 5, scale = musicutil.generate_scale(0, "melodic minor", 1), romans = {"i", "ii", "♭III+", "IV", "V", "vi°", "vii°"}},
  {name = "Dorian", number = 6, scale = musicutil.generate_scale(0, "dorian", 1), romans = {"i", "ii", "♭III", "IV", "v", "vi°", "♭VII"}},
  {name = "Phrygian", number = 7, scale = musicutil.generate_scale(0, "phrygian", 1), romans = {"i", "♭II", "♭III", "iv", "v°", "♭VI", "♭VII"}},
  {name = "Lydian", number = 8, scale = musicutil.generate_scale(0, "lydian", 1), romans = {"I", "II", "iii", "#IV°", "V", "vi", "vii"}},
  {name = "Lydian Minor", number = 9, scale = musicutil.generate_scale(0, "lydian minor", 1), romans = {"I", "II", "iii", "#IV°", "v", "♭VI", "♭VII"}},
  {name = "Mixolydian", number = 10, scale = musicutil.generate_scale(0, "mixolydian", 1), romans = {"I", "ii", "iii°", "IV", "v", "vi", "♭VII"}},
  {name = "Locrian", number = 11, scale = musicutil.generate_scale(0, "locrian", 1), romans = {"i°", "♭II", "♭iii", "iv", "♭V", "♭VI", "♭VII"}},
  {name = "Locrian Major", number = 12, scale = musicutil.generate_scale(0, "major locrian", 1), romans = {"I", "ii°", "♭iii", "IV", "♭V", "♭VI", "♭VII"}},
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

function quantiser.process(note_number, octave_mod, scale_number, channel)

  local root_note = program.get().root_note + 60
  local chord_rotation = program.get().chord - 1
  local scale_container = program.get().scales[scale_number]

  if scale_container.root_note > -1 then
    root_note = scale_container.root_note + 60
  end

  if scale_container.chord > -1 then
    chord_rotation = scale_container.chord - 1
  end

  local scale = scale_container.scale

  if chord_rotation > 0 then
    for i=1, chord_rotation do
      scale = fn.rotate_table_left(scale)
    end
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