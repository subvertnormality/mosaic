-- Hardening for all editable scale slots and cache-invalidating save/copy paths.
-- README.md:850-856 defines 16 editable scales and their application/lock precedence.

local quantiser_hardening = include("mosaic/lib/quantiser")

local function container(scale_type, root)
  local source = quantiser_hardening.get_scales()[scale_type]
  return {
    number = scale_type,
    scale = source.scale,
    pentatonic_scale = source.pentatonic_scale,
    romans = source.romans,
    root_note = root,
    chord = 1,
    chord_degree_rotation = 0,
    transpose = 0
  }
end

function test_hardening_all_sixteen_scale_slots_invalidate_cached_pitch_after_save()
  program.init()
  quantiser_hardening._scale_cache = {}
  quantiser_hardening._scale_cache_size = 0

  for slot = 1, 16 do
    local scale_type = ((slot - 1) % 10) + 1
    local first_root = (slot - 1) % 11
    program.set_scale(slot, container(scale_type, first_root))
    luaunit.assert_equals(quantiser_hardening.process(0, 0, 0, slot, false), 60 + first_root)
    luaunit.assert_equals(quantiser_hardening.process(0, 0, 0, slot, false), 60 + first_root)

    local second_root = first_root + 1
    program.set_scale(slot, container(scale_type, second_root))
    luaunit.assert_equals(program.get_scale(slot).version, 3, "slot " .. slot)
    luaunit.assert_equals(quantiser_hardening.process(0, 0, 0, slot, false), 60 + second_root, "slot " .. slot)
    luaunit.assert_equals(quantiser_hardening.process(0, 0, 0, slot, false), 60 + second_root, "cached slot " .. slot)
  end
end

function test_hardening_song_copy_has_independent_scale_data_and_cache_keys()
  program.init()
  quantiser_hardening._scale_cache = {}
  quantiser_hardening._scale_cache_size = 0

  program.set_selected_song_pattern(1)
  program.set_scale(16, container(3, 2))
  luaunit.assert_equals(quantiser_hardening.process(0, 0, 0, 16, true), 62)

  program.set_song_pattern(1, 96)
  program.set_selected_song_pattern(96)
  luaunit.assert_equals(quantiser_hardening.process(0, 0, 0, 16, true), 62)

  program.set_selected_song_pattern(1)
  program.set_scale(16, container(3, 5))
  luaunit.assert_equals(quantiser_hardening.process(0, 0, 0, 16, true), 65)

  program.set_selected_song_pattern(96)
  luaunit.assert_equals(quantiser_hardening.process(0, 0, 0, 16, true), 62)
  luaunit.assert_false(rawequal(program.get_song_pattern(1).scales[16], program.get_song_pattern(96).scales[16]))
end

function test_hardening_production_scale_type_names_and_numbers_are_stable()
  local expected = {
    "Major", "Harmonic Major", "Minor", "Harmonic Minor", "Melodic Minor",
    "Dorian", "Phrygian", "Lydian", "Mixolydian", "Locrian"
  }
  luaunit.assert_equals(#quantiser_hardening.get_scales(), #expected)
  for number, name in ipairs(expected) do
    luaunit.assert_equals(quantiser_hardening.get_scale_name_from_index(number), name)
    luaunit.assert_equals(quantiser_hardening.get_scale(number).number, number)
  end
  luaunit.assert_equals(quantiser_hardening.get_scale_name_from_index(0), "Chromatic")
end
