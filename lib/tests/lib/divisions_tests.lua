-- The division tables are parallel arrays read by different modules: the length
-- selectors (labels, indexes), recording (values) and step processing (note_divisions).
-- A refactor that edits one table must keep them aligned.
local divisions = include("mosaic/lib/clock/divisions")

function test_clock_division_labels_match_their_divisions()
  luaunit.assert_equals(#divisions.clock_divisions_labels, #divisions.clock_divisions)
  for i, division in ipairs(divisions.clock_divisions) do
    luaunit.assert_equals(divisions.clock_divisions_labels[i], division.name)
    luaunit.assert_true(division.type == "clock_multiplication" or division.type == "clock_division", division.name)
  end
  luaunit.assert_equals(divisions.clock_divisions[1].name, "x16")
  luaunit.assert_equals(#divisions.clock_divisions, 47)
end

function test_note_division_tables_are_aligned()
  luaunit.assert_equals(#divisions.note_divisions, 89)
  luaunit.assert_equals(divisions.note_division_labels[1], "X")
  luaunit.assert_equals(#divisions.note_division_labels, #divisions.note_divisions + 1)
  luaunit.assert_equals(#divisions.note_division_values, #divisions.note_divisions)
  local previous = 0
  for i, division in ipairs(divisions.note_divisions) do
    luaunit.assert_equals(divisions.note_division_labels[i + 1], division.name)
    luaunit.assert_equals(divisions.note_division_values[i], division.value)
    luaunit.assert_equals(divisions.note_division_indexes[division.value], i, division.name)
    luaunit.assert_true(division.value > previous, division.name)
    previous = division.value
  end
  local count = 0
  for _ in pairs(divisions.note_division_indexes) do count = count + 1 end
  luaunit.assert_equals(count, #divisions.note_divisions)
end

-- norns tab.save writes numbers with tostring (14 significant digits in Lua 5.3), so a
-- saved 1/3 reloads as 0.33333333333333. The selector index must still be found.
function test_note_division_index_finds_values_after_a_tab_save_round_trip()
  for i, value in ipairs(divisions.note_division_values) do
    local restored = load("return " .. tostring(value))()
    luaunit.assert_equals(divisions.note_division_index(restored), i, tostring(value))
    luaunit.assert_equals(divisions.note_division_index(value), i, tostring(value))
  end
  luaunit.assert_nil(divisions.note_division_index(nil))
  luaunit.assert_nil(divisions.note_division_index(0.3))
  luaunit.assert_nil(divisions.note_division_index(-1))
end
