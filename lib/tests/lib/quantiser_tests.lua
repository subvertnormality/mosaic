local quantiser = include("mosaic/lib/quantiser")

function test_note_value_is_quantised_from_0_to_c_in_c_major()
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  luaunit.assert_equals(quantiser.get_chord_degree(62, 60, 1), -1)  -- D to C = 1
  luaunit.assert_equals(quantiser.get_chord_degree(64, 60, 1), -2)  -- E to C = 2
  luaunit.assert_equals(quantiser.get_chord_degree(65, 60, 1), -3)  -- F to C = 3
  luaunit.assert_equals(quantiser.get_chord_degree(67, 60, 1), -4)  -- G to C = 4
  luaunit.assert_equals(quantiser.get_chord_degree(69, 60, 1), -5)  -- A to C = 5
  luaunit.assert_equals(quantiser.get_chord_degree(71, 60, 1), -6)  -- B to C = 6
end

function test_get_chord_degree_in_c_major_across_octaves()
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

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
  luaunit.assert_equals(quantiser.get_chord_degree(72, 60, 1), -7)   -- C+1 octave to C = 7
  luaunit.assert_equals(quantiser.get_chord_degree(74, 60, 1), -8)   -- D+1 octave to C = 8
  luaunit.assert_equals(quantiser.get_chord_degree(48, 60, 1), 7)  -- C-1 octave to C = -7
  luaunit.assert_equals(quantiser.get_chord_degree(50, 60, 1), 6)  -- D-1 octave to C = -6
end

function test_get_chord_degree_basics()
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

  -- Set up C major scale
  program.set_scale(
    1,
    {
      number = 1,
      scale = {0, 2, 4, 5, 7, 9, 11}, -- C D E F G A B
      pentatonic_scale = {0, 2, 4, 7, 9}, -- C D E G A
      chord = 1,
      root_note = 0
    }
  )

  -- Test basic degree calculations (no snapping needed)
  -- C major scale: C(60), D(62), E(64), F(65), G(67), A(69), B(71)
  
  luaunit.assert_equals(quantiser.get_chord_degree(62, 60, 1), -1)  -- D to C = 1
  luaunit.assert_equals(quantiser.get_chord_degree(64, 60, 1), -2)  -- E to C = 2
  luaunit.assert_equals(quantiser.get_chord_degree(65, 60, 1), -3)  -- F to C = 3
  luaunit.assert_equals(quantiser.get_chord_degree(67, 60, 1), -4)  -- G to C = 4
  
  luaunit.assert_equals(quantiser.get_chord_degree(65, 67, 1), 1)  -- F to G = -1
  luaunit.assert_equals(quantiser.get_chord_degree(64, 67, 1), 2)  -- E to G = -2
  luaunit.assert_equals(quantiser.get_chord_degree(62, 67, 1), 3)  -- D to G = -3
end

function test_get_chord_degree_octaves()
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = {0, 2, 4, 5, 7, 9, 11},
      pentatonic_scale = {0, 2, 4, 7, 9},
      chord = 1,
      root_note = 0
    }
  )

  -- Test crossing octave boundaries
  luaunit.assert_equals(quantiser.get_chord_degree(72, 67, 1), -3)
  luaunit.assert_equals(quantiser.get_chord_degree(74, 67, 1), -4)
  luaunit.assert_equals(quantiser.get_chord_degree(60, 67, 1), 4)
  luaunit.assert_equals(quantiser.get_chord_degree(48, 60, 1), 7)
end

function test_get_chord_degree_with_different_root()
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

  -- Set up D major 
  program.set_scale(
    1,
    {
      number = 1,
      scale = {0, 2, 4, 5, 7, 9, 11},
      pentatonic_scale = {0, 2, 4, 7, 9},
      chord = 1,
      root_note = 2  -- D
    }
  )

  -- D major scale: D(62), E(64), F#(66), G(67), A(69), B(71), C#(73)
  luaunit.assert_equals(quantiser.get_chord_degree(62, 64, 1), 1)   -- E to D = 1
  luaunit.assert_equals(quantiser.get_chord_degree(66, 62, 1), -2)   -- F# to D = 2
  luaunit.assert_equals(quantiser.get_chord_degree(62, 67, 1), 3)  -- D to G = -3
end

function test_get_chord_degree_snapping()
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = {0, 2, 4, 5, 7, 9, 11},
      pentatonic_scale = {0, 2, 4, 7, 9},
      chord = 1,
      root_note = 0
    }
  )

  -- Test notes that need snapping
  -- C major scale: C(60), D(62), E(64), F(65), G(67), A(69), B(71)
  luaunit.assert_equals(quantiser.get_chord_degree(60, 61, 1), 0)
  luaunit.assert_equals(quantiser.get_chord_degree(60, 63, 1), 1)
  luaunit.assert_equals(quantiser.get_chord_degree(67, 66, 1), -1)
  luaunit.assert_equals(quantiser.get_chord_degree(69, 68, 1), -1)
end

function test_get_chord_degree_intervals()
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = {0, 2, 4, 5, 7, 9, 11},
      pentatonic_scale = {0, 2, 4, 7, 9},
      chord = 1,
      root_note = 0
    }
  )

  -- Test cases where we need to pick shortest path
  luaunit.assert_equals(quantiser.get_chord_degree(65, 69, 1), 2)
  luaunit.assert_equals(quantiser.get_chord_degree(71, 65, 1), -3)
  luaunit.assert_equals(quantiser.get_chord_degree(60, 71, 1), 6)
  luaunit.assert_equals(quantiser.get_chord_degree(67, 60, 1), -4)
end


-- Scale type variations
function test_get_chord_degree_in_melodic_minor()
  program.init()
  program.set_scale(1, {
      number = 1,
      scale = quantiser.get_scales()[5].scale,  -- Melodic Minor
      chord = 1,
      root_note = 0
  })
  
  luaunit.assert_equals(quantiser.get_chord_degree(63, 60, 1), -2)  -- E♭ to C
  luaunit.assert_equals(quantiser.get_chord_degree(67, 60, 1), -4)  -- G to C
end

-- Extreme octave tests
function test_get_chord_degree_extreme_octaves()
  program.init()
  program.set_scale(1, {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      chord = 1,
      root_note = 0
  })
  
  luaunit.assert_equals(quantiser.get_chord_degree(0, 60, 1), 35)   -- Very low C
  luaunit.assert_equals(quantiser.get_chord_degree(127, 60, 1), -39)  -- Very high G
end

-- Invalid input handling
function test_get_chord_degree_invalid_input()
  program.init()
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
  program.init()
  program.set_scale(1, {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      chord = 1,
      root_note = 0
  })
  
  luaunit.assert_equals(quantiser.get_chord_degree(84, 60, 1), -14)  -- C+2 octaves to C
  luaunit.assert_equals(quantiser.get_chord_degree(36, 60, 1), 14)   -- C-2 octaves to C
end