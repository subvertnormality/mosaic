-- Mutation killers for lib/clock/divisions.lua.
--
-- divisions_tests.lua pins that the clock-division labels and names line up, but not that each
-- entry's VALUE is the rate its name promises: the channel editor's Clock Mod list shows
-- `name` (list_selector draws list[i].name) while m_clock.calculate_divisor applies `value` and
-- `type` (m_clock.lua:182-190), and the channel page finds a saved channel's entry again by
-- value (channel_edit_page_ui_refreshers.lua:71-76). README.md:683: clock division and
-- multiplication are set per channel on the channel editor page.
--
-- It also pins the relative tolerance of note_division_index (divisions.lua:474-484), which the
-- round-trip test there exercises only with 14-significant-digit values.

local divisions = include("mosaic/lib/clock/divisions")

function test_w3c_clock_division_values_are_the_rates_their_names_show()
  -- README.md:683; the "x"/"/" naming is the one the Clock Mod list shows (characterisation)
  for _, division in ipairs(divisions.clock_divisions) do
    local prefix, number = division.name:match("^([x/])([%d.]+)$")
    luaunit.assert_not_nil(prefix, division.name)
    luaunit.assert_equals(division.value, tonumber(number), division.name)
    luaunit.assert_equals(division.type, prefix == "x" and "clock_multiplication" or "clock_division", division.name)
  end
end

function test_w3c_note_division_index_tolerance_is_relative_one_in_a_billion()
  -- characterisation (divisions.lua:481): a value matches a division when it is within 1e-9 of
  -- it RELATIVE to the division, at the small end and at the large end of the table alike.
  local first, last = divisions.note_division_values[1], divisions.note_division_values[89]
  luaunit.assert_equals(first, 1/24)
  luaunit.assert_equals(last, 128)
  luaunit.assert_equals(divisions.note_division_index(first * (1 + 1e-10)), 1)
  luaunit.assert_equals(divisions.note_division_index(first * (1 - 1e-10)), 1)
  luaunit.assert_equals(divisions.note_division_index(last * (1 + 1e-10)), 89)
  luaunit.assert_equals(divisions.note_division_index(last * (1 - 1e-10)), 89)
  -- ...and not when it is 1e-8 away (about 4e-10 absolute for 1/24, 1.3e-6 for 128)
  luaunit.assert_nil(divisions.note_division_index(first * (1 + 1e-8)))
  luaunit.assert_nil(divisions.note_division_index(first * (1 - 1e-8)))
  luaunit.assert_nil(divisions.note_division_index(last * (1 + 1e-8)))
  luaunit.assert_nil(divisions.note_division_index(last * (1 - 1e-8)))
end
