local quantiser = {}


local musicutil = require("musicutil")

local program = program
local params = params
local string = string
local tostring = tostring

-- Pre-compute patterns for pentatonic scales
local pentatonic_patterns = {
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

local scale_transpose_cache = {}
local note_snap_cache = {}

-- Memoization cache
local memoize = {}
setmetatable(memoize, {__mode = "k"})  -- weak keys

local function cached_transpose_scale(scale, transpose)
  local cache_key = tostring(scale) .. "_" .. transpose
  if scale_transpose_cache[cache_key] then
      return scale_transpose_cache[cache_key]
  end
  local result = fn.transpose_scale(scale, transpose)
  scale_transpose_cache[cache_key] = result
  return result
end

function quantiser.filter_pentatonic_scale(scale, scale_type)
    local key = tostring(scale) .. "_" .. scale_type
    if memoize[key] then return memoize[key] end

    local pattern = pentatonic_patterns[scale_type] or pentatonic_patterns.major
    local pentatonic = {}
    local scale_length = 7
    local pentatonic_index = 1

    for octave = 0, (#scale // scale_length - 1) do
        for _, interval in ipairs(pattern) do
            local position = octave * scale_length + interval
            if scale[position] then
                pentatonic[pentatonic_index] = scale[position]
                pentatonic_index = pentatonic_index + 1
            end
        end
    end

    memoize[key] = pentatonic
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
    "C", "D♭", "D", "E♭", "E", "F", "G♭", "G", "A♭", "A", "B♭", "B"
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

  local key = string.format("%d_%d_%d_%d_%d_%d_%s_%s_%s_%s", root_note, chord_rotation, note_number, octave_mod, transpose, scale_number, tostring(do_rotation), tostring(do_degree), tostring(do_pentatonic), tostring(scale_container))
    
  -- Check if result is already memoized
  if memoize[key] then 
      return memoize[key] 
  end

  if scale_container.root_note > -1 then
      root_note = scale_container.root_note + 60
  end

  if scale_container.chord > -1 then
      chord_rotation = scale_container.chord - 1
  end

  local scale = fn.deep_copy(scale_container.scale)
  local pentatonic = fn.deep_copy(scale_container.pentatonic_scale)

  if do_degree and chord_rotation > 0 then
      for _ = 1, chord_rotation do
          scale = fn.rotate_table_left(scale)
      end
  end

  if do_rotation and scale_container.chord_degree_rotation and scale_container.chord_degree_rotation > 0 then
      for index = #scale, 1, -1 do
          for i = 1, scale_container.chord_degree_rotation do
              if (index % 7) == 7 - i then
                  scale[index + 1] = (scale[index + 1] or 0) - 12
              end
          end
      end
  end

  scale = fn.transpose_scale(scale, transpose)
  pentatonic = fn.transpose_scale(pentatonic, transpose)

  local result = nil

  if note_number < 0 then
      local octave = (note_number // 7) + octave_mod
      local note = note_number % 7

      if do_pentatonic and type(scale[note + 1]) == "number" then
        result = musicutil.snap_note_to_array(scale[note + 1], pentatonic) + (12 * octave) + root_note
      else
        result = (scale[note + 1] + (12 * octave)) + root_note
      end
  else
      note_number = math.min(note_number, 69)
      if do_pentatonic and type(scale[note_number + 1]) == "number" then
        result =  musicutil.snap_note_to_array(scale[note_number + 1], pentatonic) + (octave_mod * 12) + root_note
      else
        result = (scale[note_number + 1] + (octave_mod * 12)) + root_note
      end
  end

  -- Cache the result
  -- memoize[key] = result
  return result
end

function quantiser.process(note_number, octave_mod, transpose, scale_number, do_pentatonic)
  return process_handler(note_number, octave_mod, transpose, scale_number, true, true, do_pentatonic)
end

function quantiser.process_chord_note_for_mask(note_mask_value, unscaled_chord_value, octave_mod, transpose, scale_number)
  local scale_container = program.get_scale(scale_number)
  local scale = fn.deep_copy(scale_container.scale)
  local root_note = scale_container.root_note > -1 and scale_container.root_note or program.get().root_note
  
  scale = fn.transpose_scale(scale, root_note + transpose)

  if type(note_mask_value) ~= "number" then return nil end

  local offset_in_scale = fn.find_index_by_value(scale, musicutil.snap_note_to_array(note_mask_value, scale))
  
  local chord_note
  
  if unscaled_chord_value then
    chord_note = scale[unscaled_chord_value + (offset_in_scale or 0)]
  else
    chord_note = scale[offset_in_scale or 0]
  end
  
  return chord_note and (chord_note + (octave_mod * 12)) or nil
end

function quantiser.process_with_global_params(note_number, octave_mod, transpose, scale_number)
  local do_rotation = params:get("midi_honour_rotation") ~= 1
  local do_degree = params:get("midi_honour_degree") ~= 1

  return process_handler(note_number, octave_mod, transpose, scale_number, do_rotation, do_degree)
end

function quantiser.snap_to_scale(note_num, scale_number, transpose)

  local cache_key = note_num .. "_" .. scale_number .. "_" .. (transpose or 0)
  if note_snap_cache[cache_key] then
      return note_snap_cache[cache_key]
  end

  local scale_container = program.get_scale(scale_number)
  local scale = fn.deep_copy(scale_container.scale)
  local root_note = scale_container.root_note > -1 and scale_container.root_note or program.get().root_note

  scale = fn.transpose_scale(scale, root_note + (transpose or 0))

  if type(note_num) ~= "number" then return nil end

  local result = musicutil.snap_note_to_array(note_num, scale)

  note_snap_cache[cache_key] = result
  return result
end

function quantiser.process_to_pentatonic_scale(note_num, scale_number)

  local scale_container = program.get_scale(scale_number)

  if type(note_num) ~= "number" then return nil end

  return musicutil.snap_note_to_array(note_num, scale_container.pentatonic_scale)
end

function quantiser.get_chord_degree(note, chord_one_note, scale_number)
  local scale_container = program.get_scale(scale_number)
  local scale = fn.deep_copy(scale_container.scale)
  local root_note = scale_container.root_note > -1 and scale_container.root_note or program.get().root_note
  
  scale = fn.transpose_scale(scale, root_note)
  
  if type(note) ~= "number" then return nil end
  if type(chord_one_note) ~= "number" then return nil end

  return fn.find_index_by_value(scale, quantiser.snap_to_scale(note, scale_number)) - fn.find_index_by_value(scale, quantiser.snap_to_scale(chord_one_note, scale_number))
end

return quantiser