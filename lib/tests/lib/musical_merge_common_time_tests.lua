-- Common musical time (MM-09). Contract: docs/musical-merge-extensions-plan.md
-- §1.1. README "Merge Shape" still defers Interlock to MM-11, so every
-- assertion here is a characterisation of that approved plan, outside the
-- current manual.

local common_time = include("mosaic/lib/musical_merge/common_time")
local divisions = include("mosaic/lib/clock/divisions")

local function mod(name)
  for _, entry in ipairs(divisions.clock_divisions) do
    if entry.name == name then return entry end
  end
  error("missing clock mod " .. name)
end

-- §1.1 acceptance: /1 = 1/16, x2 = 1/32, /1.5 = 3/32, x5.3 = 5/424, /5.3 = 53/160.
function test_common_time_exact_whole_note_step_durations()
  local expected = {["/1"] = {1, 16}, x2 = {1, 32}, ["/1.5"] = {3, 32},
    ["x5.3"] = {5, 424}, ["/5.3"] = {53, 160}}
  for name, value in pairs(expected) do
    luaunit.assert_equals(common_time.step_duration(mod(name)), value, name)
  end
end

function test_common_time_decimal_text_conversions_are_exact()
  luaunit.assert_equals(common_time.multiplier(mod("x5.3")), {53, 10})
  luaunit.assert_equals(common_time.multiplier(mod("x2.6")), {13, 5})
  luaunit.assert_equals(common_time.multiplier(mod("x1.3")), {13, 10})
  luaunit.assert_equals(common_time.multiplier(mod("x1.5")), {3, 2})
  luaunit.assert_equals(common_time.multiplier(mod("/2.6")), {5, 13})
  luaunit.assert_equals(common_time.multiplier(nil), {1, 1})
  luaunit.assert_equals(common_time.step_duration({}), {1, 16})
end

-- The numeric projection of every clock mod equals the division the channel
-- sprocket is built from (m_clock: 1 / (calculate_divisor · 4)).
function test_common_time_projection_matches_calculate_divisor_for_every_clock_mod()
  for _, entry in ipairs(divisions.clock_divisions) do
    local d = common_time.step_duration(entry)
    luaunit.assert_not_nil(d, entry.name)
    local sprocket_division = 1 / (m_clock.calculate_divisor(entry) * 4)
    luaunit.assert_almost_equals(common_time.to_number(d), sprocket_division, 1e-12, entry.name)
  end
  luaunit.assert_equals(common_time.MASTER_STEP, common_time.step_duration({name = "/1", value = 1, type = "clock_division"}))
end

function test_common_time_projection_matches_live_sprocket_divisions()
  program.init(); globals.reset(); params.reset()
  local song = program.get_selected_song_pattern()
  for index, name in ipairs({"/1", "x2", "/1.5", "x5.3", "/5.3", "x16", "/128"}) do
    song.channels[index].clock_mods = mod(name)
  end
  m_clock.init()
  for index, name in ipairs({"/1", "x2", "/1.5", "x5.3", "/5.3", "x16", "/128"}) do
    local sprocket = m_clock["channel_" .. index .. "_clock"]
    luaunit.assert_almost_equals(common_time.to_number(common_time.step_duration(mod(name))),
      sprocket.division, 1e-12, name)
  end
end

function test_common_time_rational_arithmetic_is_reduced_and_exact()
  local a = common_time.rational(6, 8)
  luaunit.assert_equals(a, {3, 4})
  luaunit.assert_equals(common_time.add({1, 16}, {3, 32}), {5, 32})
  luaunit.assert_equals(common_time.sub({1, 16}, {3, 32}), {-1, 32})
  luaunit.assert_equals(common_time.mul({5, 424}, {424, 5}), {1, 1})
  luaunit.assert_equals(common_time.compare({53, 160}, {1, 3}), -1)
  luaunit.assert_equals(common_time.compare({2, 6}, {1, 3}), 0)
  luaunit.assert_equals(common_time.compare({5, 424}, {1, 85}), 1)
  luaunit.assert_equals(common_time.common_denominator({{1, 16}, {5, 424}, {53, 160}}), 8480)
  luaunit.assert_equals(common_time.numerator_over({53, 160}, 8480), 2809)
end

-- An intermediate that cannot be represented returns an explicit unsupported
-- result, never a rounded comparison.
function test_common_time_unrepresentable_intermediate_is_unsupported()
  local huge = common_time.rational(math.maxinteger, 1)
  local result, reason = common_time.add(huge, {1, 1})
  luaunit.assert_nil(result)
  luaunit.assert_equals(reason, "unsupported")
  result, reason = common_time.mul(huge, {3, 1})
  luaunit.assert_nil(result)
  luaunit.assert_equals(reason, "unsupported")
  luaunit.assert_equals({common_time.compare(huge, {-1, 1})}, {nil, "unsupported"})
  luaunit.assert_equals({common_time.multiplier({type = "clock_division", value = 1 / 3})}, {nil, "unsupported"})
  luaunit.assert_equals({common_time.multiplier({type = "clock_division", value = 0})}, {nil, "unsupported"})
  luaunit.assert_equals({common_time.rational(1.5, 2)}, {nil, "unsupported"})
end
