local strum_descriptor = include("mosaic/lib/musical_resolution/strum_descriptor")
local chord_order = include("mosaic/lib/musical_resolution/chord_order")

local function helpers(delay_result)
  local calls = {}
  local root_now, chord, root_later = strum_descriptor.new(
    function(i, total, pattern)
      table.insert(calls, {"order", i, total, pattern})
      return chord_order.index(i, total, pattern)
    end,
    function(division, spread, acceleration, multiplier)
      table.insert(calls, {"delay", division, spread, acceleration, multiplier})
      if delay_result == false then
        return nil
      end
      return delay_result
    end
  )
  return root_now, chord, root_later, calls
end

-- Characterisation, not manual text: nil/1/3 roots play immediately, 2/4
-- roots play later, and unknown patterns currently omit the root.
function test_strum_descriptor_preserves_root_placement()
  local root_now, _, root_later, calls = helpers(0)

  luaunit.assert_true(root_now(nil, false))
  luaunit.assert_true(root_now(1, false))
  luaunit.assert_false(root_now(2, false))
  luaunit.assert_true(root_now(3, false))
  luaunit.assert_false(root_now(4, false))
  luaunit.assert_false(root_now(0, false))
  luaunit.assert_false(root_now(5, false))
  luaunit.assert_false(root_now(1, true))

  luaunit.assert_equals(root_later(2, false, 1, 2, 3), 0)
  luaunit.assert_equals(root_later(4, false, 1, 2, 3), 0)
  luaunit.assert_nil(root_later(1, false, 1, 2, 3))
  luaunit.assert_nil(root_later(0, false, 1, 2, 3))
  luaunit.assert_nil(root_later(2, true, 1, 2, 3))
  luaunit.assert_equals(calls, {
    {"delay", 1, 2, 3, 4},
    {"delay", 1, 2, 3, 4}
  })
end

-- Characterisation, not manual text: every ordinal consults chord ordering once;
-- reverse patterns start at delay ordinal zero and forward patterns at one.
function test_strum_descriptor_preserves_shape_order_and_delay_ordinals()
  local expected_orders = {
    [1] = {1, 2, 3, 4},
    [2] = {4, 3, 2, 1},
    [3] = {1, 4, 2, 3},
    [4] = {4, 1, 3, 2}
  }

  for pattern = 1, 4 do
    local _, chord, _, calls = helpers(0)
    for i = 1, 4 do
      local chord_number, delay, multiplier =
        chord(i, {10, 20, 30, 40}, pattern, 5, 6, 7)
      local expected_multiplier = (pattern == 2 or pattern == 4) and i - 1 or i
      luaunit.assert_equals(chord_number, expected_orders[pattern][i])
      luaunit.assert_equals(delay, 0)
      luaunit.assert_equals(multiplier, expected_multiplier)
      luaunit.assert_equals(calls[(i - 1) * 2 + 1], {"order", i, 4, pattern})
      luaunit.assert_equals(calls[(i - 1) * 2 + 2], {"delay", 5, 6, 7, expected_multiplier})
    end
    luaunit.assert_equals(#calls, 8)
  end
end

-- Characterisation, not manual text: nil/false/zero slots do not calculate
-- timing; active negative masks do, zero delay schedules, and nil suppresses.
function test_strum_descriptor_preserves_silent_slots_and_nil_delay()
  local _, chord, _, calls = helpers(0)
  local notes = {[1] = nil, [2] = false, [3] = 0, [4] = -1}
  for i = 1, 4 do
    local chord_number, delay = chord(i, notes, 1, nil, 2, 3)
    if i == 4 then
      luaunit.assert_equals(chord_number, 4)
      luaunit.assert_equals(delay, 0)
    else
      luaunit.assert_nil(chord_number)
      luaunit.assert_nil(delay)
    end
  end
  luaunit.assert_equals(#calls, 5)
  luaunit.assert_equals(calls[5], {"delay", nil, 2, 3, 4})

  local _, suppressed, root_later, suppressed_calls = helpers(false)
  luaunit.assert_nil(suppressed(1, {8}, 1, 1, 0, 0))
  luaunit.assert_nil(root_later(2, false, 1, 0, 0))
  luaunit.assert_equals(suppressed_calls, {
    {"order", 1, 4, 1},
    {"delay", 1, 0, 0, 1},
    {"delay", 1, 0, 0, 4}
  })
end
