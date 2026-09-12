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


function test_hardening_save_across_song_invalidates_warm_caches_and_keeps_linked_scale()
  -- README.md:850-856 defines editable scales and K1+K2 save across the song. The user
  -- confirmed that this route intentionally links the saved scale across existing song
  -- slots (S35 decision, 2026-09-11). Each slot's already-warm quantiser lookup must use
  -- the new root, and a supported linked rotation edit must invalidate every slot's key.
  program.init()
  quantiser_hardening._scale_cache = {}
  quantiser_hardening._scale_cache_size = 0

  for _, song_number in ipairs({1, 48, 96}) do
    program.get_song_pattern(song_number)
    program.set_selected_song_pattern(song_number)
    program.set_scale(16, container(1, song_number % 12))
    quantiser_hardening.process(6, 0, 0, 16, false)
  end

  program.set_all_song_pattern_scales(16, container(1, 2))
  local linked = program.get_song_pattern(1).scales[16]
  for _, song_number in ipairs({1, 48, 96}) do
    program.set_selected_song_pattern(song_number)
    luaunit.assert_true(rawequal(program.get_scale(16), linked), "linked song " .. song_number)
    luaunit.assert_equals(quantiser_hardening.process(0, 0, 0, 16, false), 62,
      "save-across-song root " .. song_number)
  end

  program.set_selected_song_pattern(48)
  program.set_chord_degree_rotation_for_scale(16, 1)
  for _, song_number in ipairs({1, 48, 96}) do
    program.set_selected_song_pattern(song_number)
    luaunit.assert_equals(quantiser_hardening.process(6, 0, 0, 16, false), 61,
      "linked rotation " .. song_number)
  end
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
