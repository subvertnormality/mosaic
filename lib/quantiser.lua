local quantiser = {}

local fn = include("mosaic/lib/functions")
local musicutil = require("musicutil")

function quantiser.filter_pentatonic_scale(scale, scale_type)
  -- Define interval patterns for pentatonic versions of various scales
  local patterns = {
      major = {1, 2, 3, 5, 6},
      minor = {1, 3, 4, 5, 7},
      harmonic_major = {1, 2, 3, 5, 6},
      harmonic_minor = {1, 3, 4, 5, 7},
      melodic_minor = {1, 3, 4, 5, 7},
      dorian = {1, 2, 4, 5, 7},
      phrygian = {1, 3, 4, 6, 7},
      lydian = {2, 3, 5, 6, 7},
      mixolydian = {1, 2, 4, 5, 6},
      locrian = {2, 3, 4, 6, 7}
  }

  -- Default to major if the scale type is not specified or not in the patterns
  local pattern = patterns[scale_type] or patterns.major

  local pentatonic = {}
  local scale_length = 7  -- Base diatonic scale length
  local pentatonic_index = 1

  -- Extract pentatonic scale based on the pattern
  for octave = 0, (math.floor(#scale / scale_length) - 1) do
      for _, interval in ipairs(pattern) do
          local position = octave * scale_length + interval
          if scale[position] then
              pentatonic[pentatonic_index] = scale[position]
              pentatonic_index = pentatonic_index + 1
          end
      end
  end

  return pentatonic
end

local scales = {
  {
    name = "Major",
    number = 1,
    scale = musicutil.generate_scale(0, "major", 20),
    pentatonic_scale = quantiser.filter_pentatonic_scale(musicutil.generate_scale(0, "major", 20), "major"),
    romans = {"I", "ii", "iii", "IV", "V", "vi", "vii°"},
    sinf_degrees = {0, 2, 4, 5, 7, 9, 11},
    sinf_mode = 3,
    sinf_root_mod = 0
  },
  {
    name = "Harmonic Major",
    number = 2,
    scale = musicutil.generate_scale(0, "harmonic major", 20),
    pentatonic_scale = quantiser.filter_pentatonic_scale(musicutil.generate_scale(0, "harmonic major", 20), "harmonic_major"),
    romans = {"I", "ii", "iii", "IV", "V", "♭VI+", "vii°"},
    sinf_degrees = {0, 2, 4, 5, 7, 8, 11},
    sinf_mode = 7,
    sinf_root_mod = 0
  },
  {
    name = "Minor",
    number = 3,
    scale = musicutil.generate_scale(0, "minor", 20),
    pentatonic_scale = quantiser.filter_pentatonic_scale(musicutil.generate_scale(0, "minor", 20), "minor"),
    romans = {"i", "ii°", "♭III", "iv", "v", "♭VI", "♭VII"},
    sinf_degrees = {0, 2, 3, 5, 7, 8, 10},
    sinf_mode = 4,
    sinf_root_mod = 0
  },
  {
    name = "Harmonic Minor",
    number = 4,
    scale = musicutil.generate_scale(0, "harmonic minor", 20),
    pentatonic_scale = quantiser.filter_pentatonic_scale(musicutil.generate_scale(0, "harmonic minor", 20), "harmonic_minor"),
    romans = {"i", "ii°", "♭III+", "iv", "V", "♭VI", "vii°"},
    sinf_degrees = {0, 2, 3, 5, 7, 8, 11},
    sinf_mode = 6,
    sinf_root_mod = 0
  },
  {
    name = "Melodic Minor",
    number = 5,
    scale = musicutil.generate_scale(0, "melodic minor", 20),
    pentatonic_scale = quantiser.filter_pentatonic_scale(musicutil.generate_scale(0, "melodic minor", 20), "melodic_minor"),
    romans = {"i", "ii", "♭III+", "IV", "V", "vi°", "vii°"},
    sinf_degrees = {0, 2, 3, 5, 7, 9, 11},
    sinf_mode = 5,
    sinf_root_mod = 0
  },
  {
    name = "Dorian",
    number = 6,
    scale = musicutil.generate_scale(0, "dorian", 20),
    pentatonic_scale = quantiser.filter_pentatonic_scale(musicutil.generate_scale(0, "dorian", 20), "dorian"),
    romans = {"i", "ii", "♭III", "IV", "v", "vi°", "♭VII"},
    sinf_degrees = {2, 4, 5, 7, 9, 11, 0},
    sinf_mode = 3,
    sinf_root_mod = 10
  },
  {
    name = "Phrygian",
    number = 7,
    scale = musicutil.generate_scale(0, "phrygian", 20),
    pentatonic_scale = quantiser.filter_pentatonic_scale(musicutil.generate_scale(0, "phrygian", 20), "phrygian"),
    romans = {"i", "♭II", "♭III", "iv", "v°", "♭VI", "♭VII"},
    sinf_degrees = {4, 5, 7, 9, 11, 0, 2},
    sinf_mode = 3,
    sinf_root_mod = 8
  },
  {
    name = "Lydian",
    number = 8,
    scale = musicutil.generate_scale(0, "lydian", 20),
    pentatonic_scale = quantiser.filter_pentatonic_scale(musicutil.generate_scale(0, "lydian", 20), "lydian"),
    romans = {"I", "II", "iii", "#IV°", "V", "vi", "vii"},
    sinf_degrees = {5, 7, 9, 11, 0, 2, 4},
    sinf_mode = 3,
    sinf_root_mod = 7
  },
  {
    name = "Mixolydian",
    number = 9,
    scale = musicutil.generate_scale(0, "mixolydian", 20),
    pentatonic_scale = quantiser.filter_pentatonic_scale(musicutil.generate_scale(0, "mixolydian", 20), "mixolydian"),
    romans = {"I", "ii", "iii°", "IV", "v", "vi", "♭VII"},
    sinf_degrees = {7, 9, 11, 0, 2, 4, 5},
    sinf_mode = 3,
    sinf_root_mod = 5
  },
  {
    name = "Locrian",
    number = 10,
    scale = musicutil.generate_scale(0, "locrian", 20),
    pentatonic_scale = quantiser.filter_pentatonic_scale(musicutil.generate_scale(0, "locrian", 20), "locrian"),
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

function quantiser.get_scale(s)
  return scales[s]
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

local function process_handler(note_number, octave_mod, transpose, scale_number, do_rotation, do_degree, do_pentatonic)
  local root_note = program.get().root_note + 60
  local chord_rotation = program.get().chord - 1
  local scale_container = program.get_scale(scale_number)

  if scale_container.root_note > -1 then
    root_note = scale_container.root_note + 60
  end

  if scale_container.chord > -1 then
    chord_rotation = scale_container.chord - 1
  end

  local scale = fn.deep_copy(scale_container.scale)
  local pentatonic = fn.deep_copy(scale_container.pentatonic_scale)

  if (do_degree) then
    if chord_rotation > 0 then
      for i = 1, chord_rotation do
        scale = fn.rotate_table_left(scale)
      end
    end
  end

  if (do_rotation) then
    if scale_container.chord_degree_rotation and scale_container.chord_degree_rotation > 0 then
      for index = #scale, 1, -1 do
        local value = scale[index]
        for i = 1, scale_container.chord_degree_rotation do
          if (index % 7) == 7 - i then
            scale[index + 1] = (scale[index + 1] or 0) - 12
          end
        end
      end
    end
  end

  scale = fn.transpose_scale(scale, transpose)
  pentatonic = fn.transpose_scale(pentatonic, transpose)

  if note_number < 0 then
    local octave = math.floor(note_number / 7) + octave_mod
    local note = note_number % 7

    if (do_pentatonic) then
      return musicutil.snap_note_to_array(scale[note + 1], pentatonic) + (12 * octave) + root_note
    end

    return (scale[note + 1] + (12 * octave)) + root_note
  else
    if note_number > 69 then
      note_number = 69
    end

    if (do_pentatonic) then
      return musicutil.snap_note_to_array(scale[note_number + 1], pentatonic) + (octave_mod * 12) + root_note
    end

    return (scale[note_number + 1] + (octave_mod * 12)) + root_note
  end

end

function quantiser.process(note_number, octave_mod, transpose, scale_number, do_pentatonic)
  return process_handler(note_number, octave_mod, transpose, scale_number, true, true, do_pentatonic)
end

function quantiser.process_chord_note_for_mask(note_mask_value, unscaled_chord_value, octave_mod, transpose, scale_number)
  local scale_container = program.get_scale(scale_number)
  local scale = fn.deep_copy(scale_container.scale)
  
  return (note_mask_value) + (12 * octave_mod) + (scale[unscaled_chord_value + 14 + 1] - 24) + transpose
end

function quantiser.process_with_global_params(note_number, octave_mod, transpose, scale_number)
  local do_rotation = true
  local do_degree = true

  if params:get("midi_honour_rotation") == 1 then
    do_rotation = false
  end

  if params:get("midi_honour_degree") == 1 then
    do_degree = false
  end

  return process_handler(note_number, octave_mod, transpose, scale_number, do_rotation, do_degree)
end

function quantiser.snap_to_scale(note_num, scale_number)
  local scale_container = program.get_scale(scale_number)
  return musicutil.snap_note_to_array(note_num, scale_container.scale)
end

function quantiser.process_to_pentatonic_scale(note_num, scale_number)
  local scale_container = program.get_scale(scale_number)
  return musicutil.snap_note_to_array(note_num, scale_container.pentatonic_scale)
end


return quantiser
