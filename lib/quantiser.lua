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

local pentatonic_positions_cache = {}

local function calculate_pentatonic_positions(mode, max_notes)
    -- Get pattern or default to major if invalid
    local pattern = pentatonic_patterns[mode] or pentatonic_patterns.major
    
    local positions = {}
    local max_octaves = math.ceil(max_notes / 7)
    
    for octave = 0, max_octaves do
        for _, interval in ipairs(pattern) do
            local position = octave * 7 + interval
            if position <= max_notes then
                table.insert(positions, position)
            end
        end
    end
    
    return positions
end

local function get_pentatonic_positions(mode, scale_length)
    local cache_key = mode .. "_" .. scale_length
    if not pentatonic_positions_cache[cache_key] then
        pentatonic_positions_cache[cache_key] = calculate_pentatonic_positions(mode, scale_length)
    end
    return pentatonic_positions_cache[cache_key]
end

function quantiser.filter_pentatonic_scale(scale, scale_type)
  local positions = get_pentatonic_positions(scale_type, #scale)
  local pentatonic = {}
  
  for i, position in ipairs(positions) do
      if scale[position] then
          pentatonic[i] = scale[position]
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

quantiser._scale_cache = {}
quantiser._scale_cache_size = 0
quantiser._scale_cache_max_size = 100

local function cleanup_old_cache_entries()
  -- Convert cache to array of {key, timestamp} pairs
  local cache_entries = {}
  for k, v in pairs(quantiser._scale_cache) do
      table.insert(cache_entries, {
          key = k,
          timestamp = v.timestamp
      })
  end
  
  -- Sort by timestamp (oldest first)
  table.sort(cache_entries, function(a, b)
      return a.timestamp < b.timestamp
  end)
  
  -- Remove oldest 25% of entries
  local entries_to_remove = math.floor(quantiser._scale_cache_size * 0.25)
  for i = 1, entries_to_remove do
      quantiser._scale_cache[cache_entries[i].key] = nil
  end
  
  quantiser._scale_cache_size = quantiser._scale_cache_size - entries_to_remove
end

local function hash_scale(scale)
  local hash = 0
  for i, v in ipairs(scale) do
    -- Use XOR operation to combine values in a way that's sensitive to order
    -- Multiply by i to make position matter
    hash = hash ~ (v * i)
  end
  return hash
end

local function make_cache_key(root_note, chord_rotation, scale_number, transpose, do_rotation, do_degree, do_transpose, do_pentatonic, scale_container)
  -- Use bit operations to pack booleans into a single number
  local flags = (do_rotation and 1 or 0) +
               (do_degree and 2 or 0) +
               (do_transpose and 4 or 0) +
               (do_pentatonic and 8 or 0)
  
  -- Hash the scale table
  scale_hash = hash_scale(scale_container.scale)

  -- Create a more efficient key using string format
  return string.format("%d:%d:%d:%d:%x:%d:%d:%d",
      root_note,
      chord_rotation,
      scale_number,
      transpose,
      flags,
      scale_container.chord_degree_rotation or 0,
      scale_container.version or 0,
      scale_hash
  )
end

local function process_handler(note_number, octave_mod, transpose, scale_number, do_rotation, do_degree, do_transpose, do_pentatonic)
  
  
  local root_note = program.get().root_note + 60
  local chord_rotation = program.get().chord - 1

  local scale_container = program.get_scale(scale_number)

  if scale_container.root_note > -1 then
    root_note = scale_container.root_note + 60
  end

  if scale_container.chord > -1 then
      chord_rotation = scale_container.chord - 1
  end

  local cache_key = make_cache_key(
    root_note,
    chord_rotation,
    scale_number,
    transpose,
    do_rotation,
    do_degree,
    do_transpose,
    do_pentatonic,
    scale_container
  )


  local cache_entry = quantiser._scale_cache[cache_key]
  local scale, pentatonic

  if cache_entry then
    cache_entry.timestamp = os.time()  -- Update timestamp on access
    scale = cache_entry.scale
    pentatonic = cache_entry.pentatonic
  else
    scale = fn.deep_copy(scale_container.scale)
    pentatonic = fn.deep_copy(scale_container.pentatonic_scale)

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
    
    if do_transpose then
      scale = fn.transpose_scale(scale, transpose)
      pentatonic = fn.transpose_scale(pentatonic, transpose)
    end

    -- Store processed scales in cache
    quantiser._scale_cache[cache_key] = {
      scale = scale,
      pentatonic = pentatonic
    }
    quantiser._scale_cache_size = quantiser._scale_cache_size + 1

    if quantiser._scale_cache_size > quantiser._scale_cache_max_size then
      cleanup_old_cache_entries()
    end
  end

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
      result = musicutil.snap_note_to_array(scale[note_number + 1], pentatonic) + (octave_mod * 12) + root_note
    else
      result = (scale[note_number + 1] + (octave_mod * 12)) + root_note
    end
  end

  return result
end

function quantiser.process(note_number, octave_mod, transpose, scale_number, do_pentatonic)
  return process_handler(note_number, octave_mod, transpose, scale_number, true, true, true, do_pentatonic)
end

function quantiser.translate_note_mask_to_relative_scale_position(note_mask_value, scale_number)

  local scale_container = program.get_scale(scale_number)
  if not scale_container then return nil end
  if type(note_mask_value) ~= "number" then return nil end

  -- Get root note
  local root_note = scale_container.root_note > -1 and scale_container.root_note or 0
  local octave = math.floor((note_mask_value - 60 - root_note) / 12)

  -- Create a transposed scale
  local scale = fn.deep_copy(scale_container.scale)
  scale = fn.transpose_scale(scale, root_note)

  local snapped_note = musicutil.snap_note_to_array(note_mask_value, scale)
  local position = fn.find_index_by_value(scale, snapped_note)
  local position_in_octave = (position - 1) % 7

  return position_in_octave, octave

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
  local do_transpose = params:get("midi_honour_transpose") ~= 1


  return process_handler(note_number, octave_mod, transpose, scale_number, do_rotation, do_degree, do_transpose)
end

function quantiser.process_with_mask_params(note_number, octave_mod, transpose, scale_number, fully_quantise_mask)
  if fully_quantise_mask then
    return process_handler(note_number, octave_mod, transpose, scale_number, true, true, true)
  else
    return process_handler(note_number, octave_mod, transpose, scale_number, false, false, false)
  end
end


function quantiser.snap_to_scale(note_num, scale_number, transpose)

  local scale_container = program.get_scale(scale_number)
  local scale = fn.deep_copy(scale_container.scale)
  local root_note = scale_container.root_note > -1 and scale_container.root_note or program.get().root_note

  scale = fn.transpose_scale(scale, root_note + (transpose or 0))

  if type(note_num) ~= "number" then return nil end

  return musicutil.snap_note_to_array(note_num, scale)
end

function quantiser.process_to_pentatonic_scale(note_num, scale_number)

  local scale_container = program.get_scale(scale_number)

  if type(note_num) ~= "number" then return nil end

  return musicutil.snap_note_to_array(note_num, scale_container.pentatonic_scale)
end

function quantiser.get_chord_degree(note, chord_one_note, scale_number)

  -- Early return for invalid inputs
  if type(note) ~= "number" or type(chord_one_note) ~= "number" then return nil end

  -- Get and prepare scale
  local scale_container = program.get_scale(scale_number)
  local scale = scale_container.scale
  local root_note = scale_container.root_note > -1 and scale_container.root_note or program.get().root_note
  scale = fn.transpose_scale(scale, root_note)

  -- Create a degree lookup table
  local degree_lookup = {}
  for i, scale_note in ipairs(scale) do
    degree_lookup[scale_note] = i - 1
  end

  -- Snap notes to the scale
  local snapped_note = quantiser.snap_to_scale(note, scale_number)
  local snapped_chord_one_note = quantiser.snap_to_scale(chord_one_note, scale_number)

  -- Get degrees within the scale
  local snapped_note_degree = degree_lookup[snapped_note]
  local snapped_chord_one_note_degree = degree_lookup[snapped_chord_one_note]

  -- Return total interval in scale steps
  return snapped_note_degree - snapped_chord_one_note_degree
end

return quantiser