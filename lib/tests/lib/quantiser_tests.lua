local quantiser = include("mosaic/lib/quantiser")
local musicutil = require("musicutil")

local function setup() 
  quantiser._scale_cache = {}
  quantiser._scale_cache_size = 0
  quantiser._scale_cache_max_size = 100
  program.init()
end

function test_note_value_is_quantised_from_0_to_c_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 0
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 60)
end

function test_note_value_is_quantised_from_1_to_d_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 1
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 62)
end


function test_note_value_is_quantised_from_2_to_e_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 2
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 64)
end


function test_note_value_is_quantised_from_3_to_f_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 3
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 65)
end


function test_note_value_is_quantised_from_4_to_g_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 4
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 67)
end

function test_note_value_is_quantised_from_5_to_a_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 5
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 69)
end


function test_note_value_is_quantised_from_6_to_b_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 6
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 71)
end


function test_note_value_is_quantised_from_7_to_c_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 7
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 72)
end

function test_note_value_is_quantised_from_0_to_c_72_with_step_octave_mod_1_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 0
  local octave_mod = 1
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 72)
end

function test_note_value_is_quantised_from_3_to_f_77_with_step_octave_mod_1_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 3
  local octave_mod = 1
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 77)
end


function test_note_value_is_quantised_from_3_to_fsharp_with_transpose_1_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 3
  local octave_mod = 0
  local transpose = 1
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 66)
end

function test_note_value_is_quantised_from_3_to_g_with_transpose_2_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 3
  local octave_mod = 0
  local transpose = 2
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 67)
end


function test_note_value_is_quantised_from_3_to_e_with_transpose_minus1_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 3
  local octave_mod = 0
  local transpose = -1
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 64)
end

function test_note_value_is_quantised_from_3_to_e_with_transpose_minus5_in_c_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 3
  local octave_mod = 0
  local transpose = -5
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 60)
end

function test_note_value_is_quantised_from_0_to_d_in_c_major_with_chord_2()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 2,
      root_note = 0
    }
  )

  local note_value = 0
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 62)
end


function test_note_value_is_quantised_from_0_to_c_72_in_c_major_with_chord_8()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 8,
      root_note = 0
    }
  )

  local note_value = 0
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 72)
end

function test_note_value_is_quantised_from_0_to_b_71_in_c_major_with_chord_7()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 7,
      root_note = 0
    }
  )

  local note_value = 0
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 71)
end

function test_note_value_is_quantised_from_0_to_b_83_in_c_major_with_chord_7_octave_mod_1()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 7,
      root_note = 0
    }
  )

  local note_value = 0
  local octave_mod = 1
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 83)
end

function test_note_value_is_quantised_from_0_to_c_84_in_c_major_with_chord_7_octave_mod_1_transpose_1()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 7,
      root_note = 0
    }
  )

  local note_value = 0
  local octave_mod = 1
  local transpose = 1
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 84)
end

function test_note_value_is_quantised_from_0_to_csharp_85_in_csharp_major_with_chord_7_octave_mod_1_transpose_1_root_note_1()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 7,
      root_note = 1
    }
  )

  local note_value = 0
  local octave_mod = 1
  local transpose = 1
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 85)
end


function test_note_value_is_quantised_from_0_to_d_in_d_major()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 2
    }
  )

  local note_value = 0
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 62)
end


function test_note_value_is_quantised_from_5_to_bsharp_70_in_d_minor()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[2].scale,
      pentatonic_scale = quantiser.get_scales()[2].pentatonic_scale,
      chord = 1,
      root_note = 2
    }
  )

  local note_value = 5
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 70)
end


function test_note_value_is_quantised_from_5_to_bsharp_70_in_d_minor_when_using_scale_2()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    2,
    {
      number = 2,
      scale = quantiser.get_scales()[2].scale,
      pentatonic_scale = quantiser.get_scales()[2].pentatonic_scale,
      chord = 1,
      root_note = 2
    }
  )

  local note_value = 5
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 2


  luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 70)
end



function test_note_values_are_quantised_a_to_a_with_correct_ascending_octave()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 6,
      root_note = 0
    }
  )

  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assert_equals(quantiser.process(0, octave_mod, transpose, step_scale_number), 69) -- A
  luaunit.assert_equals(quantiser.process(1, octave_mod, transpose, step_scale_number), 71) -- B
  luaunit.assert_equals(quantiser.process(2, octave_mod, transpose, step_scale_number), 72) -- C (octave up)
  luaunit.assert_equals(quantiser.process(3, octave_mod, transpose, step_scale_number), 74) -- D (octave up)
  luaunit.assert_equals(quantiser.process(4, octave_mod, transpose, step_scale_number), 76) -- E (octave up)
  luaunit.assert_equals(quantiser.process(5, octave_mod, transpose, step_scale_number), 77) -- F (octave up)
  luaunit.assert_equals(quantiser.process(6, octave_mod, transpose, step_scale_number), 79) -- G (octave up)
end


function test_get_chord_degree_in_c_major_one_octave()
  setup()
  program.get_song_pattern(1).root_note = 0

  -- Set up C major scale
  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  -- Test all degrees in C major scale (C=60 is reference)
  luaunit.assert_equals(quantiser.get_chord_degree(60, 60, 1), 0)  -- C to C = 0
  luaunit.assert_equals(quantiser.get_chord_degree(62, 60, 1), 1)  -- D to C = 1
  luaunit.assert_equals(quantiser.get_chord_degree(64, 60, 1), 2)  -- E to C = 2
  luaunit.assert_equals(quantiser.get_chord_degree(65, 60, 1), 3)  -- F to C = 3
  luaunit.assert_equals(quantiser.get_chord_degree(67, 60, 1), 4)  -- G to C = 4
  luaunit.assert_equals(quantiser.get_chord_degree(69, 60, 1), 5)  -- A to C = 5
  luaunit.assert_equals(quantiser.get_chord_degree(71, 60, 1), 6)  -- B to C = 6
end

function test_get_chord_degree_in_c_major_across_octaves()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  -- Test notes in different octaves
  luaunit.assert_equals(quantiser.get_chord_degree(72, 60, 1), 7)   -- C+1 octave to C = 7
  luaunit.assert_equals(quantiser.get_chord_degree(74, 60, 1), 8)   -- D+1 octave to C = 8
  luaunit.assert_equals(quantiser.get_chord_degree(48, 60, 1), -7)  -- C-1 octave to C = -7
  luaunit.assert_equals(quantiser.get_chord_degree(50, 60, 1), -6)  -- D-1 octave to C = -6
end

function test_get_chord_degree_basics()
  setup()
  program.get_song_pattern(1).root_note = 0

  -- Set up C major scale
  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  -- Test basic degree calculations (no snapping needed)
  -- C major scale: C(60), D(62), E(64), F(65), G(67), A(69), B(71)
  
  luaunit.assert_equals(quantiser.get_chord_degree(62, 60, 1), 1)  -- D to C = 1
  luaunit.assert_equals(quantiser.get_chord_degree(64, 60, 1), 2)  -- E to C = 2
  luaunit.assert_equals(quantiser.get_chord_degree(65, 60, 1), 3)  -- F to C = 3
  luaunit.assert_equals(quantiser.get_chord_degree(67, 60, 1), 4)  -- G to C = 4
  
  luaunit.assert_equals(quantiser.get_chord_degree(65, 67, 1), -1)  -- F to G = -1
  luaunit.assert_equals(quantiser.get_chord_degree(64, 67, 1), -2)  -- E to G = -2
  luaunit.assert_equals(quantiser.get_chord_degree(62, 67, 1), -3)  -- D to G = -3
end

function test_get_chord_degree_octaves()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  -- Test crossing octave boundaries
  luaunit.assert_equals(quantiser.get_chord_degree(72, 67, 1), 3)
  luaunit.assert_equals(quantiser.get_chord_degree(74, 67, 1), 4)
  luaunit.assert_equals(quantiser.get_chord_degree(60, 67, 1), -4)
  luaunit.assert_equals(quantiser.get_chord_degree(48, 60, 1), -7)
end

function test_get_chord_degree_with_different_root()
  setup()
  program.get_song_pattern(1).root_note = 0

  -- Set up D major 
  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 2  -- D
    }
  )

  -- D major scale: D(62), E(64), F#(66), G(67), A(69), B(71), C#(73)
  luaunit.assert_equals(quantiser.get_chord_degree(62, 64, 1), -1)   -- E to D = 1
  luaunit.assert_equals(quantiser.get_chord_degree(66, 62, 1), 2)   -- F# to D = 2
  luaunit.assert_equals(quantiser.get_chord_degree(62, 67, 1), -3)  -- D to G = -3
end

function test_get_chord_degree_snapping()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  -- Test notes that need snapping
  -- C major scale: C(60), D(62), E(64), F(65), G(67), A(69), B(71)
  luaunit.assert_equals(quantiser.get_chord_degree(60, 61, 1), 0)
  luaunit.assert_equals(quantiser.get_chord_degree(60, 63, 1), -1)
  luaunit.assert_equals(quantiser.get_chord_degree(67, 66, 1), 1)
  luaunit.assert_equals(quantiser.get_chord_degree(69, 68, 1), 1)
end

function test_get_chord_degree_intervals()
  setup()
  program.get_song_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      pentatonic_scale = quantiser.get_scales()[1].pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  -- Test cases where we need to pick shortest path
  luaunit.assert_equals(quantiser.get_chord_degree(65, 69, 1), -2)
  luaunit.assert_equals(quantiser.get_chord_degree(71, 65, 1), 3)
  luaunit.assert_equals(quantiser.get_chord_degree(60, 71, 1), -6)
  luaunit.assert_equals(quantiser.get_chord_degree(67, 60, 1), 4)
end


-- Scale type variations
function test_get_chord_degree_in_melodic_minor()
  setup()
  program.set_scale(1, {
      number = 1,
      scale = quantiser.get_scales()[5].scale,  -- Melodic Minor
      chord = 1,
      root_note = 0
  })
  
  luaunit.assert_equals(quantiser.get_chord_degree(63, 60, 1), 2)  -- E♭ to C
  luaunit.assert_equals(quantiser.get_chord_degree(67, 60, 1), 4)  -- G to C
end

-- Extreme octave tests
function test_get_chord_degree_extreme_octaves()
  setup()
  program.set_scale(1, {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      chord = 1,
      root_note = 0
  })
  
  luaunit.assert_equals(quantiser.get_chord_degree(0, 60, 1), -35)   -- Very low C
  luaunit.assert_equals(quantiser.get_chord_degree(127, 60, 1), 39)  -- Very high G
end

-- Invalid input handling
function test_get_chord_degree_invalid_input()
  setup()
  program.set_scale(1, {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      chord = 1,
      root_note = 0
  })
  
  luaunit.assert_equals(quantiser.get_chord_degree(nil, 60, 1), nil)
  luaunit.assert_equals(quantiser.get_chord_degree(60, nil, 1), nil)
  luaunit.assert_equals(quantiser.get_chord_degree("60", 60, 1), nil)
end

-- Multiple octave spans
function test_get_chord_degree_multiple_octaves()
  setup()
  program.set_scale(1, {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      chord = 1,
      root_note = 0
  })
  
  luaunit.assert_equals(quantiser.get_chord_degree(84, 60, 1), 14)  -- C+2 octaves to C
  luaunit.assert_equals(quantiser.get_chord_degree(36, 60, 1), -14)   -- C-2 octaves to C
end


function test_major_pentatonic_scale_generation()
  setup()
  local major_scale = musicutil.generate_scale(0, "major", 128)
  local pentatonic = quantiser.filter_pentatonic_scale(major_scale, "major")
  
  -- C major pentatonic should contain C(0), D(2), E(4), G(7), A(9) pattern
  -- Testing first octave
  luaunit.assert_equals(pentatonic[1], 0)  -- C
  luaunit.assert_equals(pentatonic[2], 2)  -- D
  luaunit.assert_equals(pentatonic[3], 4)  -- E
  luaunit.assert_equals(pentatonic[4], 7)  -- G
  luaunit.assert_equals(pentatonic[5], 9)  -- A
  
  -- Test second octave notes exist and follow pattern
  luaunit.assert_equals(pentatonic[6], 12)  -- C
  luaunit.assert_equals(pentatonic[7], 14)  -- D
  luaunit.assert_equals(pentatonic[8], 16)  -- E
  luaunit.assert_equals(pentatonic[9], 19)  -- G
end

function test_minor_pentatonic_scale_generation()
  setup()
  local minor_scale = musicutil.generate_scale(0, "minor", 128)
  local pentatonic = quantiser.filter_pentatonic_scale(minor_scale, "minor")
  
  -- C minor pentatonic should contain C(0), E♭(3), F(5), G(7), B♭(10) pattern
  -- Testing first octave
  luaunit.assert_equals(pentatonic[1], 0)   -- C
  luaunit.assert_equals(pentatonic[2], 3)   -- E♭
  luaunit.assert_equals(pentatonic[3], 5)   -- F
  luaunit.assert_equals(pentatonic[4], 7)   -- G
  luaunit.assert_equals(pentatonic[5], 10)  -- B♭
  
  -- Test second octave notes exist and follow pattern
  luaunit.assert_equals(pentatonic[6], 12)  -- C
  luaunit.assert_equals(pentatonic[7], 15)  -- E♭
  luaunit.assert_equals(pentatonic[8], 17)  -- F
end

function test_dorian_pentatonic_scale_generation()
  setup()
  local dorian_scale = musicutil.generate_scale(0, "dorian", 128)
  local pentatonic = quantiser.filter_pentatonic_scale(dorian_scale, "dorian")
  
  -- C dorian pentatonic should contain C(0), D(2), F(5), G(7), B♭(10) pattern
  luaunit.assert_equals(pentatonic[1], 0)   -- C
  luaunit.assert_equals(pentatonic[2], 2)   -- D
  luaunit.assert_equals(pentatonic[3], 5)   -- F
  luaunit.assert_equals(pentatonic[4], 7)   -- G
  luaunit.assert_equals(pentatonic[5], 10)  -- B♭
end

function test_pentatonic_with_invalid_scale_type()
  setup()
  local major_scale = musicutil.generate_scale(0, "major", 128)
  local pentatonic = quantiser.filter_pentatonic_scale(major_scale, "nonexistent_scale")
  
  -- Should default to major pentatonic pattern
  luaunit.assert_equals(pentatonic[1], 0)  -- C
  luaunit.assert_equals(pentatonic[2], 2)  -- D
  luaunit.assert_equals(pentatonic[3], 4)  -- E
  luaunit.assert_equals(pentatonic[4], 7)  -- G
  luaunit.assert_equals(pentatonic[5], 9)  -- A
end

function test_pentatonic_scale_generation_full_midi_range()
  setup()
  -- Generate scales for the full MIDI range (0-127)
  local full_major_scale = musicutil.generate_scale(0, "major", 128)
  
  -- Test major pentatonic
  local major_pentatonic = quantiser.filter_pentatonic_scale(full_major_scale, "major")
  
  -- Expected notes for the major pentatonic scale starting from MIDI note 0 (C-1)
  local expected_notes = {}
  local pentatonic_intervals = {0, 2, 4, 7, 9}  -- Intervals in semitones
  
  -- Generate expected notes
  for octave = -1, 9 do  -- MIDI octaves from C-1 to C9
    local base_note = (octave + 1) * 12  -- Adjust for octave numbering
    for _, interval in ipairs(pentatonic_intervals) do
      local note = base_note + interval
      if note >= 0 and note <= 127 then
        table.insert(expected_notes, note)
      end
    end
  end
  
  -- Now compare the generated pentatonic scale with the expected notes
  luaunit.assert_equals(major_pentatonic, expected_notes)
end

function test_pentatonic_scale_size_full_midi_range()
  setup()
  -- Generate full range scales
  local scales = {
      major = musicutil.generate_scale(0, "major", 128),
      minor = musicutil.generate_scale(0, "minor", 128),
      dorian = musicutil.generate_scale(0, "dorian", 128),
      phrygian = musicutil.generate_scale(0, "phrygian", 128),
      lydian = musicutil.generate_scale(0, "lydian", 128),
      mixolydian = musicutil.generate_scale(0, "mixolydian", 128),
      locrian = musicutil.generate_scale(0, "locrian", 128)
  }
  
  for scale_type, scale in pairs(scales) do
      local pentatonic = quantiser.filter_pentatonic_scale(scale, scale_type)
      
      -- Calculate expected size:
      -- MIDI range is 128 notes (0-127)
      -- Each octave has 5 pentatonic notes
      -- Expected size should be (number of complete octaves * 5) + remaining notes
      local complete_octaves = math.floor(128 / 12)
      local expected_min_size = complete_octaves * 5
      local expected_max_size = expected_min_size + 5  -- Allow for partial final octave
      
      luaunit.assert_true(#pentatonic >= expected_min_size,
          string.format("%s pentatonic scale size %d should be >= %d", 
                       scale_type, #pentatonic, expected_min_size))
      luaunit.assert_true(#pentatonic <= expected_max_size,
          string.format("%s pentatonic scale size %d should be <= %d", 
                       scale_type, #pentatonic, expected_max_size))
  end
end

function test_pentatonic_intervals_consistent_across_all_octaves()
  setup()
  local full_major_scale = musicutil.generate_scale(0, "major", 128)
  local major_pentatonic = quantiser.filter_pentatonic_scale(full_major_scale, "major")
  
  -- Test that intervals between consecutive notes are consistent across all octaves
  local expected_intervals = {
      2,  -- C to D
      2,  -- D to E
      3,  -- E to G
      2,  -- G to A
      3   -- A to C (next octave)
  }
  
  local notes_per_octave = 5
  local num_complete_octaves = math.floor(#major_pentatonic / notes_per_octave)
  
  for octave = 0, num_complete_octaves - 1 do
      local octave_start_idx = (octave * notes_per_octave) + 1
      
      for i = 0, notes_per_octave - 2 do
          local current_note = major_pentatonic[octave_start_idx + i]
          local next_note = major_pentatonic[octave_start_idx + i + 1]
          local interval = next_note - current_note
          
          luaunit.assert_equals(interval, expected_intervals[i + 1],
              string.format("Wrong interval at octave %d, position %d: expected %d, got %d",
                          octave, i, expected_intervals[i + 1], interval))
      end
      
      -- Check interval to first note of next octave if not in last octave
      if octave < num_complete_octaves - 1 then
          local last_note = major_pentatonic[octave_start_idx + notes_per_octave - 1]
          local first_note_next_octave = major_pentatonic[octave_start_idx + notes_per_octave]
          local interval = first_note_next_octave - last_note
          
          luaunit.assert_equals(interval, expected_intervals[5],
              string.format("Wrong interval between octaves %d and %d: expected %d, got %d",
                          octave, octave + 1, expected_intervals[5], interval))
      end
  end
end

function test_translate_note_mask_to_relative_scale_position_basic_c_major()
  setup()


  program.get().root_note = 60
  local scale_number = 1 -- C Major
  
  -- Test notes in C major scale (C D E F G A B)
  local pos, oct = quantiser.translate_note_mask_to_relative_scale_position(60, scale_number)
  luaunit.assert_equals(pos, 1) -- C4 -> position 1
  luaunit.assert_equals(oct, 0) -- C4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(62, scale_number)
  luaunit.assert_equals(pos, 2) -- D4 -> position 2
  luaunit.assert_equals(oct, 0) -- D4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(64, scale_number)
  luaunit.assert_equals(pos, 3) -- E4 -> position 3
  luaunit.assert_equals(oct, 0) -- E4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(65, scale_number)
  luaunit.assert_equals(pos, 4) -- F4 -> position 4
  luaunit.assert_equals(oct, 0) -- F4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(67, scale_number)
  luaunit.assert_equals(pos, 5) -- G4 -> position 5
  luaunit.assert_equals(oct, 0) -- G4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(69, scale_number)
  luaunit.assert_equals(pos, 6) -- A4 -> position 6
  luaunit.assert_equals(oct, 0) -- A4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(71, scale_number)
  luaunit.assert_equals(pos, 7) -- B4 -> position 7
  luaunit.assert_equals(oct, 0) -- B4 -> octave 0
end

function test_translate_note_mask_to_relative_scale_position_snapping()
  setup()
  program.get().root_note = 60
  local scale_number = 1 -- C Major
  
  -- Test notes that need to be snapped to C major scale
  local pos, oct = quantiser.translate_note_mask_to_relative_scale_position(61, scale_number)
  luaunit.assert_equals(pos, 1) -- C#4 snaps to C -> position 1
  luaunit.assert_equals(oct, 0) -- C#4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(63, scale_number)
  luaunit.assert_equals(pos, 2) -- D#4 snaps to D -> position 2
  luaunit.assert_equals(oct, 0) -- D#4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(66, scale_number)
  luaunit.assert_equals(pos, 4) -- F#4 snaps to F -> position 4
  luaunit.assert_equals(oct, 0) -- F#4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(68, scale_number)
  luaunit.assert_equals(pos, 5) -- G#4 snaps to G -> position 5
  luaunit.assert_equals(oct, 0) -- G#4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(70, scale_number)
  luaunit.assert_equals(pos, 6) -- A#4 snaps to A -> position 6
  luaunit.assert_equals(oct, 0) -- A#4 -> octave 0
end

function test_translate_note_mask_to_relative_scale_position_octaves()
  setup()
  program.get().root_note = 60
  local scale_number = 1 -- C Major
  
  -- Test notes in different octaves
  local pos, oct = quantiser.translate_note_mask_to_relative_scale_position(48, scale_number)
  luaunit.assert_equals(pos, 1) -- C3 -> position 1
  luaunit.assert_equals(oct, -1) -- C3 -> octave -1
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(72, scale_number)
  luaunit.assert_equals(pos, 1) -- C5 -> position 1
  luaunit.assert_equals(oct, 1) -- C5 -> octave 1
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(84, scale_number)
  luaunit.assert_equals(pos, 1) -- C6 -> position 1
  luaunit.assert_equals(oct, 2) -- C6 -> octave 2
  
  -- Test non-root notes in different octaves
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(74, scale_number)
  luaunit.assert_equals(pos, 2) -- D5 -> position 2
  luaunit.assert_equals(oct, 1) -- D5 -> octave 1
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(76, scale_number)
  luaunit.assert_equals(pos, 3) -- E5 -> position 3
  luaunit.assert_equals(oct, 1) -- E5 -> octave 1
end

function test_translate_note_mask_to_relative_scale_position_minor_scale()
  setup()
  program.get().root_note = 60
  program.set_scale(1, { -- Minor scale
    number = 1,
    scale = quantiser.get_scales()[3].scale,
    chord = 1,
    root_note = 0
  })

  local scale_number = 1 -- Minor scale
  
  -- Test notes in C minor scale (C D Eb F G Ab Bb)
  local pos, oct = quantiser.translate_note_mask_to_relative_scale_position(60, scale_number)
  luaunit.assert_equals(pos, 1) -- C4 -> position 1
  luaunit.assert_equals(oct, 0) -- C4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(62, scale_number)
  luaunit.assert_equals(pos, 2) -- D4 -> position 2
  luaunit.assert_equals(oct, 0) -- D4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(63, scale_number)
  luaunit.assert_equals(pos, 3) -- Eb4 -> position 3
  luaunit.assert_equals(oct, 0) -- Eb4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(65, scale_number)
  luaunit.assert_equals(pos, 4) -- F4 -> position 4
  luaunit.assert_equals(oct, 0) -- F4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(67, scale_number)
  luaunit.assert_equals(pos, 5) -- G4 -> position 5
  luaunit.assert_equals(oct, 0) -- G4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(68, scale_number)
  luaunit.assert_equals(pos, 6) -- Ab4 -> position 6
  luaunit.assert_equals(oct, 0) -- Ab4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(70, scale_number)
  luaunit.assert_equals(pos, 7) -- Bb4 -> position 7
  luaunit.assert_equals(oct, 0) -- Bb4 -> octave 0
end

function test_translate_note_mask_to_relative_scale_position_edge_cases()
  setup()
  program.get().root_note = 60
  local scale_number = 1 -- C Major
  
  -- Test very low and high notes
  local pos, oct = quantiser.translate_note_mask_to_relative_scale_position(0, scale_number)
  luaunit.assert_equals(pos, 1) -- C-1 -> position 1
  luaunit.assert_equals(oct, -5) -- C-1 -> octave -5
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(127, scale_number)
  luaunit.assert_equals(pos, 5) -- G9 -> position 5
  luaunit.assert_equals(oct, 5) -- G9 -> octave 5
  
  -- Test invalid inputs
  luaunit.assert_equals(quantiser.translate_note_mask_to_relative_scale_position(nil, scale_number), nil)
  luaunit.assert_equals(quantiser.translate_note_mask_to_relative_scale_position("60", scale_number), nil)
  luaunit.assert_equals(quantiser.translate_note_mask_to_relative_scale_position(60, nil), nil)
  luaunit.assert_equals(quantiser.translate_note_mask_to_relative_scale_position(60, 99), nil)
end

function test_translate_note_mask_to_relative_scale_position_with_root_note()
  setup()
  program.get().root_note = 60
  local scale_number = 1 -- C Major
  local scale = program.get_scale(scale_number)
  scale.root_note = 2 -- Set root note to D
  
  -- Test notes in D major scale (D E F# G A B C#)
  local pos, oct = quantiser.translate_note_mask_to_relative_scale_position(62, scale_number)
  luaunit.assert_equals(pos, 1) -- D4 -> position 1
  luaunit.assert_equals(oct, 0) -- D4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(64, scale_number)
  luaunit.assert_equals(pos, 2) -- E4 -> position 2
  luaunit.assert_equals(oct, 0) -- E4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(66, scale_number)
  luaunit.assert_equals(pos, 3) -- F#4 -> position 3
  luaunit.assert_equals(oct, 0) -- F#4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(67, scale_number)
  luaunit.assert_equals(pos, 4) -- G4 -> position 4
  luaunit.assert_equals(oct, 0) -- G4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(69, scale_number)
  luaunit.assert_equals(pos, 5) -- A4 -> position 5
  luaunit.assert_equals(oct, 0) -- A4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(71, scale_number)
  luaunit.assert_equals(pos, 6) -- B4 -> position 6
  luaunit.assert_equals(oct, 0) -- B4 -> octave 0
  
  pos, oct = quantiser.translate_note_mask_to_relative_scale_position(73, scale_number)
  luaunit.assert_equals(pos, 7) -- C#5 -> position 7
  luaunit.assert_equals(oct, 0) -- C#5 -> octave 0
end