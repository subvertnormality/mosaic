local quantiser = {}

local fn = include("mosaic/lib/functions")
local musicutil = require("musicutil")

local scales = {
  {
    name = "Major",
    number = 1,
    scale = musicutil.generate_scale(0, "major", 1),
    romans = {"I", "ii", "iii", "IV", "V", "vi", "vii°"},
    sinf_degrees = {0, 2, 4, 5, 7, 9, 11},
    sinf_mode = 3,
    sinf_root_mod = 0
  },
  {
    name = "Harmonic Major",
    number = 2,
    scale = musicutil.generate_scale(0, "harmonic major", 1),
    romans = {"I", "ii", "iii", "IV", "V", "♭VI+", "vii°"},
    sinf_degrees = {0, 2, 4, 5, 7, 8, 11},
    sinf_mode = 7,
    sinf_root_mod = 0
  },
  {
    name = "Minor",
    number = 3,
    scale = musicutil.generate_scale(0, "minor", 1),
    romans = {"i", "ii°", "♭III", "iv", "v", "♭VI", "♭VII"},
    sinf_degrees = {0, 2, 3, 5, 7, 8, 10},
    sinf_mode = 4,
    sinf_root_mod = 0
  },
  {
    name = "Harmonic Minor",
    number = 4,
    scale = musicutil.generate_scale(0, "harmonic minor", 1),
    romans = {"i", "ii°", "♭III+", "iv", "V", "♭VI", "vii°"},
    sinf_degrees = {0, 2, 3, 5, 7, 8, 11},
    sinf_mode = 6,
    sinf_root_mod = 0
  },
  {
    name = "Melodic Minor",
    number = 5,
    scale = musicutil.generate_scale(0, "melodic minor", 1),
    romans = {"i", "ii", "♭III+", "IV", "V", "vi°", "vii°"},
    sinf_degrees = {0, 2, 3, 5, 7, 9, 11},
    sinf_mode = 5,
    sinf_root_mod = 0
  },
  {
    name = "Dorian",
    number = 6,
    scale = musicutil.generate_scale(0, "dorian", 1),
    romans = {"i", "ii", "♭III", "IV", "v", "vi°", "♭VII"},
    sinf_degrees = {2, 4, 5, 7, 9, 11, 0},
    sinf_mode = 3,
    sinf_root_mod = 10
  },
  {
    name = "Phrygian",
    number = 7,
    scale = musicutil.generate_scale(0, "phrygian", 1),
    romans = {"i", "♭II", "♭III", "iv", "v°", "♭VI", "♭VII"},
    sinf_degrees = {4, 5, 7, 9, 11, 0, 2},
    sinf_mode = 3,
    sinf_root_mod = 8
  },
  {
    name = "Lydian",
    number = 8,
    scale = musicutil.generate_scale(0, "lydian", 1),
    romans = {"I", "II", "iii", "#IV°", "V", "vi", "vii"},
    sinf_degrees = {5, 7, 9, 11, 0, 2, 4},
    sinf_mode = 3,
    sinf_root_mod = 7
  },
  {
    name = "Mixolydian",
    number = 9,
    scale = musicutil.generate_scale(0, "mixolydian", 1),
    romans = {"I", "ii", "iii°", "IV", "v", "vi", "♭VII"},
    sinf_degrees = {7, 9, 11, 0, 2, 4, 5},
    sinf_mode = 3,
    sinf_root_mod = 5
  },
  {
    name = "Locrian",
    number = 10,
    scale = musicutil.generate_scale(0, "locrian", 1),
    romans = {"i°", "♭II", "♭iii", "iv", "♭V", "♭VI", "♭VII"},
    sinf_degrees = {11, 0, 2, 4, 5, 7, 9},
    sinf_mode = 3,
    sinf_root_mod = 1
  }
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
  if i == 0 then
    return "Chromatic"
  end

  return scales[i].name
end

function quantiser.process(note_number, octave_mod, transpose, scale_number)

  local root_note = program.get().root_note + 60
  local chord_rotation = program.get().chord - 1
  local scale_container = program.get_scale(scale_number)

  if scale_container.root_note > -1 then
    root_note = scale_container.root_note + 60
  end

  if scale_container.chord > -1 then
    chord_rotation = scale_container.chord - 1
  end

  local scale = scale_container.scale

  if chord_rotation > 0 then
    for i = 1, chord_rotation do
      scale = fn.rotate_table_left(scale)
    end
  end

  scale = fn.transpose_scale(scale, transpose)

  if note_number >= 7 then
    local octave = math.floor(note_number / 7) + octave_mod
    local note = note_number % 7
    return (scale[note + 1] + (12 * octave)) + root_note
  elseif note_number < 0 then
    local octave = math.floor(note_number / 7) + octave_mod
    local note = note_number % 7
    return (scale[note + 1] + (12 * octave)) + root_note
  else
    return (scale[note_number + 1] + (octave_mod * 12)) + root_note
  end
end

return quantiser
