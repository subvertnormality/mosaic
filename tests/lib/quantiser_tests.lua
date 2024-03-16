-- local quantiser = include("mosaic/lib/quantiser")

-- function test_note_value_is_quantised_from_0_to_c_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 0
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 60)
-- end

-- function test_note_value_is_quantised_from_1_to_d_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 1
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 62)
-- end


-- function test_note_value_is_quantised_from_2_to_e_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 2
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 64)
-- end


-- function test_note_value_is_quantised_from_3_to_f_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 3
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 65)
-- end


-- function test_note_value_is_quantised_from_4_to_g_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 4
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 67)
-- end

-- function test_note_value_is_quantised_from_5_to_a_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 5
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 69)
-- end


-- function test_note_value_is_quantised_from_6_to_b_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 6
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 71)
-- end


-- function test_note_value_is_quantised_from_7_to_c_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 7
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 72)
-- end

-- function test_note_value_is_quantised_from_0_to_c_72_with_step_octave_mod_1_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 0
--   local octave_mod = 1
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 72)
-- end

-- function test_note_value_is_quantised_from_3_to_f_77_with_step_octave_mod_1_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 3
--   local octave_mod = 1
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 77)
-- end


-- function test_note_value_is_quantised_from_3_to_fsharp_with_transpose_1_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 3
--   local octave_mod = 0
--   local transpose = 1
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 66)
-- end

-- function test_note_value_is_quantised_from_3_to_g_with_transpose_2_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 3
--   local octave_mod = 0
--   local transpose = 2
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 67)
-- end


-- function test_note_value_is_quantised_from_3_to_e_with_transpose_minus1_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 3
--   local octave_mod = 0
--   local transpose = -1
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 64)
-- end

-- function test_note_value_is_quantised_from_3_to_e_with_transpose_minus5_in_c_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 0
--     }
--   )

--   local note_value = 3
--   local octave_mod = 0
--   local transpose = -5
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 60)
-- end

-- function test_note_value_is_quantised_from_0_to_d_in_c_major_with_chord_2()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 2,
--       root_note = 0
--     }
--   )

--   local note_value = 0
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 62)
-- end


-- function test_note_value_is_quantised_from_0_to_c_60_in_c_major_with_chord_8()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 8,
--       root_note = 0
--     }
--   )

--   local note_value = 0
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 60)
-- end

-- function test_note_value_is_quantised_from_0_to_b_71_in_c_major_with_chord_7()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 7,
--       root_note = 0
--     }
--   )

--   local note_value = 0
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 71)
-- end

-- function test_note_value_is_quantised_from_0_to_b_83_in_c_major_with_chord_7_octave_mod_1()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 7,
--       root_note = 0
--     }
--   )

--   local note_value = 0
--   local octave_mod = 1
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 83)
-- end

-- function test_note_value_is_quantised_from_0_to_c_84_in_c_major_with_chord_7_octave_mod_1_transpose_1()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 7,
--       root_note = 0
--     }
--   )

--   local note_value = 0
--   local octave_mod = 1
--   local transpose = 1
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 84)
-- end

-- function test_note_value_is_quantised_from_0_to_csharp_85_in_csharp_major_with_chord_7_octave_mod_1_transpose_1_root_note_1()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 7,
--       root_note = 1
--     }
--   )

--   local note_value = 0
--   local octave_mod = 1
--   local transpose = 1
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 85)
-- end


-- function test_note_value_is_quantised_from_0_to_d_in_d_major()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[1].scale,
--       chord = 1,
--       root_note = 2
--     }
--   )

--   local note_value = 0
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 62)
-- end


-- function test_note_value_is_quantised_from_5_to_bsharp_70_in_d_minor()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     1,
--     {
--       number = 1,
--       scale = quantiser.get_scales()[2].scale,
--       chord = 1,
--       root_note = 2
--     }
--   )

--   local note_value = 5
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 1


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 70)
-- end


-- function test_note_value_is_quantised_from_5_to_bsharp_70_in_d_minor_when_using_scale_2()
--   program.init()
--   program.get_sequencer_pattern(1).root_note = 0

--   program.set_scale(
--     2,
--     {
--       number = 2,
--       scale = quantiser.get_scales()[2].scale,
--       chord = 1,
--       root_note = 2
--     }
--   )

--   local note_value = 5
--   local octave_mod = 0
--   local transpose = 0
--   local step_scale_number = 2


--   luaunit.assert_equals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 70)
-- end