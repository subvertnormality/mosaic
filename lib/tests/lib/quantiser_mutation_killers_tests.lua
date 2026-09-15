-- Mutation killers for lib/quantiser.lua (wave 3 over mutation-bc0570c survivors).
--
-- Each test builds a fresh quantiser instance, so its scale cache starts empty and is
-- exercised by the test itself (the cache is a performance target: results must be
-- identical whether a lookup hits or misses it). Expected notes come from an
-- independent scale-degree oracle where the musical rule is clear; golden values are
-- labelled characterisation.

-- Semitone intervals of the ten scales, in quantiser.get_scales() order.
local INTERVALS = {
  {0, 2, 4, 5, 7, 9, 11},  -- Major
  {0, 2, 4, 5, 7, 8, 11},  -- Harmonic Major
  {0, 2, 3, 5, 7, 8, 10},  -- Minor
  {0, 2, 3, 5, 7, 8, 11},  -- Harmonic Minor
  {0, 2, 3, 5, 7, 9, 11},  -- Melodic Minor
  {0, 2, 3, 5, 7, 9, 10},  -- Dorian
  {0, 1, 3, 5, 7, 8, 10},  -- Phrygian
  {0, 2, 4, 6, 7, 9, 11},  -- Lydian
  {0, 2, 4, 5, 7, 9, 10},  -- Mixolydian
  {0, 1, 3, 5, 6, 8, 10},  -- Locrian
}

-- The five pitch classes of each scale's pentatonic selection.
local PENTATONIC = {
  {0, 2, 4, 7, 9}, {0, 2, 4, 7, 8}, {0, 3, 5, 7, 10}, {0, 3, 5, 7, 11}, {0, 3, 5, 7, 11},
  {0, 2, 5, 7, 10}, {0, 3, 5, 8, 10}, {2, 4, 7, 9, 11}, {0, 2, 5, 7, 9}, {1, 3, 5, 8, 10},
}

-- A fresh module instance. The module captures `params` at load, so the global is
-- replaced only for the load and restored even if the load fails.
local function fresh_quantiser(param_values)
  local saved_params = params
  params = {get = function(_, id) return (param_values or {})[id] end}
  local ok, loaded = pcall(include, "mosaic/lib/quantiser")
  params = saved_params
  if not ok then error(loaded, 0) end
  return loaded
end

local function use_scale(q, slot, number, root_note, chord, rotation)
  local source = q.get_scales()[number]
  local container = {number = number, scale = source.scale, pentatonic_scale = source.pentatonic_scale,
    chord = chord, root_note = root_note, chord_degree_rotation = rotation}
  program.set_scale(slot, container)
  return container
end

-- Pitch (relative to the root) of zero-based scale degree k.
local function degree_pitch(number, k)
  return 12 * (k // 7) + INTERVALS[number][k % 7 + 1]
end

-- Nearest pentatonic pitch; an exact tie selects the lower pitch.
local function nearest_pentatonic(number, pitch)
  local best, distance
  for octave = -6, 12 do
    for _, offset in ipairs(PENTATONIC[number]) do
      local candidate = 12 * octave + offset
      local delta = math.abs(candidate - pitch)
      if not distance or delta < distance then best, distance = candidate, delta end
    end
  end
  return best
end

-- Degree n of a scale whose chord (degree) is `chord`: the chord shifts the scale's
-- starting degree to chord - 1. Rotation r lowers the top r positions of every
-- seven-degree block by an octave. Transpose and the octave shift are added last.
local function expected_note(number, root, chord, rotation, transpose, n, octave, pentatonic)
  local pitch = degree_pitch(number, n + chord - 1)
  if rotation > 0 and n % 7 >= 7 - rotation then pitch = pitch - 12 end
  if pentatonic then pitch = nearest_pentatonic(number, pitch) end
  return 60 + root + transpose + 12 * octave + pitch
end

local DEGREES = {-15, -9, -8, -7, -1, 0, 1, 2, 3, 4, 5, 6, 7, 13, 20}

function test_quantiser_killer_process_follows_degree_arithmetic_for_every_scale_chord_and_rotation()
  program.init()
  local q = fresh_quantiser()
  for number = 1, 10 do
    for chord = 1, 7 do
      for rotation = 0, 6 do
        for _, root in ipairs({0, 11}) do
          use_scale(q, 1, number, root, chord, rotation)
          for _, transpose in ipairs({0, 2}) do
            for _, n in ipairs(DEGREES) do
              for _, pentatonic in ipairs({false, true}) do
                local octave = (n == 1) and 1 or 0
                local expected = expected_note(number, root, chord, rotation, transpose, n, octave, pentatonic)
                local actual = q.process(n, octave, transpose, 1, pentatonic)
                if actual ~= expected then
                  luaunit.fail(string.format("scale %d chord %d rotation %d root %d transpose %d degree %d pentatonic %s: expected %s, got %s",
                    number, chord, rotation, root, transpose, n, tostring(pentatonic), tostring(expected), tostring(actual)))
                end
              end
            end
          end
        end
      end
    end
  end
end

-- README "Fully Quantise Mask": on, the mask follows degree, rotation and transposition;
-- off, it keeps its plain scale position.
function test_quantiser_killer_mask_params_apply_rotation_degree_and_transpose_only_when_fully_quantised()
  program.init()
  local q = fresh_quantiser()
  use_scale(q, 1, 1, 0, 3, 2)
  for _, n in ipairs({-8, -1, 0, 4, 5, 6, 12}) do
    luaunit.assert_equals(q.process_with_mask_params(n, 0, 5, 1, true), expected_note(1, 0, 3, 2, 5, n, 0, false))
    luaunit.assert_equals(q.process_with_mask_params(n, 0, 5, 1, false), expected_note(1, 0, 1, 0, 0, n, 0, false))
    luaunit.assert_equals(q.process_with_mask_params(n, 0, 5, 1, true), expected_note(1, 0, 3, 2, 5, n, 0, false))
  end
end

-- The midi_honour_* params switch rotation, degree and transposition independently (a
-- param value of 1 means "do not honour"); every combination is served from one cache.
function test_quantiser_killer_global_params_select_each_combination_without_cache_crosstalk()
  program.init()
  local combos = {}
  for _, rotation in ipairs({false, true}) do
    for _, degree in ipairs({false, true}) do
      for _, transpose in ipairs({false, true}) do
        table.insert(combos, {rotation = rotation, degree = degree, transpose = transpose})
      end
    end
  end
  local values = {}
  local q = fresh_quantiser(values)
  use_scale(q, 1, 1, 0, 3, 2)
  for pass = 1, 2 do
    for index = 1, #combos do
      local combo = combos[pass == 1 and index or #combos + 1 - index]
      values.midi_honour_rotation = combo.rotation and 2 or 1
      values.midi_honour_degree = combo.degree and 2 or 1
      values.midi_honour_transpose = combo.transpose and 2 or 1
      for _, n in ipairs({0, 4, 5, 6}) do
        local expected = expected_note(1, 0, combo.degree and 3 or 1, combo.rotation and 2 or 0,
          combo.transpose and 5 or 0, n, 0, false)
        luaunit.assert_equals(q.process_with_global_params(n, 0, 5, 1), expected,
          string.format("rotation %s degree %s transpose %s degree %d", tostring(combo.rotation),
            tostring(combo.degree), tostring(combo.transpose), n))
      end
    end
  end
end

-- A scale slot with root -1 and chord -1 has no root or chord of its own: it follows the
-- song's root note (C at init) and the song's chord (1). README "Quantised Fixed Note":
-- "at its configured root (or the song root when unset)".
function test_quantiser_killer_unset_slot_root_and_chord_follow_the_song()
  program.init()
  local q = fresh_quantiser()
  use_scale(q, 1, 1, -1, -1, 0)
  for n = 0, 6 do
    luaunit.assert_equals(q.process(n, 0, 0, 1), 60 + INTERVALS[1][n + 1])
  end
  luaunit.assert_equals(q.snap_to_scale(61, 1), 60)
  luaunit.assert_equals(q.snap_to_scale(66, 1), 65)
  luaunit.assert_equals(q.snap_to_scale(66, 1, 0, true), 65)
  luaunit.assert_equals(q.get_chord_degree(67, 60, 1), 4)
  luaunit.assert_equals(q.get_chord_degree(64, 72, 1), -5)
end

-- The note-mask translation also treats root -1 as C (the song root is C at init).
function test_quantiser_killer_translate_with_unset_root_uses_c()
  program.init()
  local q = fresh_quantiser()
  use_scale(q, 1, 1, -1, 1, 0)
  local cases = {{60, 0, 0}, {62, 1, 0}, {64, 2, 0}, {65, 3, 0}, {71, 6, 0}, {72, 0, 1}, {59, 6, -1}}
  for _, case in ipairs(cases) do
    local position, octave = q.translate_note_mask_to_relative_scale_position(case[1], 1)
    luaunit.assert_equals({position, octave}, {case[2], case[3]}, "note " .. case[1])
  end
end

-- Scale transposition moves the snapping grid up: C major + 2 is D major.
function test_quantiser_killer_snap_to_scale_adds_transpose_to_the_root()
  program.init()
  local q = fresh_quantiser()
  use_scale(q, 1, 1, 0, 1, 0)
  luaunit.assert_equals(q.snap_to_scale(66, 1, 2), 66)   -- F# is in D major
  luaunit.assert_equals(q.snap_to_scale(60, 1, 2), 59)   -- C lies between C#61 and B59; the tie takes B
  luaunit.assert_equals(q.snap_to_scale(65, 1, -2), 65)  -- F is in B flat major
  luaunit.assert_equals(q.snap_to_scale(64, 1, -2), 63)  -- E lies between E flat63 and F65; the tie takes E flat
end

-- Positive degrees are clamped to degree 69 (characterisation: degree 69 of C major is
-- B, nine octaves above the scale's first C, i.e. 60 + 108 + 11 = 179).
function test_quantiser_killer_degrees_above_69_clamp_to_degree_69()
  program.init()
  local q = fresh_quantiser()
  use_scale(q, 1, 1, 0, 1, 0)
  luaunit.assert_equals(q.process(69, 0, 0, 1), 60 + degree_pitch(1, 69))
  luaunit.assert_equals(q.process(69, 0, 0, 1), 179)
  luaunit.assert_equals(q.process(70, 0, 0, 1), 179)
  luaunit.assert_equals(q.process(74, 0, 0, 1), 179)
end

-- Changing a slot's rotation in place (no new scale version) takes effect at once, also
-- when the slot had no rotation set before.
function test_quantiser_killer_rotation_set_on_an_unrotated_slot_takes_effect()
  program.init()
  local q = fresh_quantiser()
  use_scale(q, 1, 1, 0, 1, nil)
  luaunit.assert_equals(q.process(6, 0, 0, 1), 71)
  program.set_chord_degree_rotation_for_scale(1, 1)
  luaunit.assert_equals(q.process(6, 0, 0, 1), 59)
  luaunit.assert_equals(q.process(5, 0, 0, 1), 69)
end

-- Memory bound of the scale cache (performance target): however many distinct lookups,
-- the cache never holds more entries than its maximum, and results are unaffected.
function test_quantiser_killer_scale_cache_entry_count_stays_within_its_maximum()
  program.init()
  local q = fresh_quantiser()
  use_scale(q, 1, 1, 0, 1, 0)
  for transpose = 1, 600 do
    luaunit.assert_equals(q.process(0, 0, transpose, 1), 60 + transpose)
    local entries = 0
    for _ in pairs(q._scale_cache) do entries = entries + 1 end
    if entries > q._scale_cache_max_size then
      luaunit.fail(string.format("%d cache entries after %d lookups (maximum %d)", entries, transpose, q._scale_cache_max_size))
    end
  end
end

-- get_scales() is indexed by scale number, and step.lua looks a slot's scale up by it.
function test_quantiser_killer_scale_numbers_match_their_positions()
  local q = fresh_quantiser()
  for i, scale in ipairs(q.get_scales()) do
    luaunit.assert_equals(scale.number, i)
    luaunit.assert_is(q.get_scale(i), scale)
  end
  luaunit.assert_equals(#q.get_scales(), 10)
end

-- step.lua sends the Sinfonion a root (slot root + sinf_root_mod) and a degree
-- (sinf_degrees[chord]). Whatever mode is sent, the chord root pitch class they name
-- must be the scale's own degree: (sinf_root_mod + sinf_degrees[k]) mod 12 equals the
-- k-th interval of the scale.
function test_quantiser_killer_sinfonion_root_and_degree_name_each_chord_root()
  local q = fresh_quantiser()
  for number, scale in ipairs(q.get_scales()) do
    luaunit.assert_equals(#scale.sinf_degrees, 7)
    for k = 1, 7 do
      local degree = scale.sinf_degrees[k]
      luaunit.assert_true(degree >= 0 and degree <= 11, scale.name .. " degree " .. k)
      luaunit.assert_equals((scale.sinf_root_mod + degree) % 12, INTERVALS[number][k], scale.name .. " degree " .. k)
    end
  end
end

-- Characterisation of the Sinfonion mode numbers: the church modes are sent as their
-- parent major (mode 3, with the root offset checked above); the others have their own
-- Sinfonion mode. step.lua's minor-fifth workaround relies on Minor being mode 4.
function test_quantiser_killer_sinfonion_mode_numbers()
  local q = fresh_quantiser()
  local modes = {}
  for i, scale in ipairs(q.get_scales()) do modes[i] = scale.sinf_mode end
  luaunit.assert_equals(modes, {3, 7, 4, 6, 5, 3, 3, 3, 3, 3})
  for i = 1, 5 do luaunit.assert_equals(q.get_scales()[i].sinf_root_mod, 0) end
end
