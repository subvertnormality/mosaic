-- local processed_note =
-- quantiser.process(
-- unprocessed_note_container.note_value,
-- unprocessed_note_container.octave_mod,
-- unprocessed_note_container.transpose,
-- channel.step_scale_number
-- )


-- local root_note = program.get().root_note + 60
-- local chord_rotation = program.get().chord - 1
-- local scale_container = program.get_scale(scale_number)


local quantiser = include("mosaic/lib/quantiser")


function test_note_value_is_quantised_from_0_to_c_in_c_major()
  program.init()
  program.get_sequencer_pattern(1).root_note = 0

  program.set_scale(
    1,
    {
      number = 1,
      scale = quantiser.get_scales()[1].scale,
      chord = 1,
      root_note = 0
    }
  )

  local note_value = 0
  local octave_mod = 0
  local transpose = 0
  local step_scale_number = 1


  luaunit.assertEquals(quantiser.process(note_value, octave_mod, transpose, step_scale_number), 60)
end
