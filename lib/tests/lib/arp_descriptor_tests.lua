local arp_descriptor = include("mosaic/lib/musical_resolution/arp_descriptor")
local chord_order = include("mosaic/lib/musical_resolution/chord_order")

local function builder_with_calls()
  local calls = {}
  local build = arp_descriptor.new(function(i, total, pattern)
    table.insert(calls, {i, total, pattern})
    return chord_order.index(i, total, pattern)
  end)
  return build, calls
end

local function note_values(sequence)
  local values = {}
  for i = 1, 5 do
    values[i] = sequence[i] and sequence[i].note_value or false
  end
  return values
end

-- Characterisation, not manual text: each arp shape orders four chord slots
-- before placing the root, and consults the order selector exactly four times.
function test_arp_descriptor_preserves_shapes_and_order_lookup_count()
  local expected = {
    [1] = {62, 63, 64, 65, 66},
    [2] = {66, 65, 64, 63, 62},
    [3] = {62, 63, 66, 64, 65},
    [4] = {66, 63, 65, 64, 62}
  }

  for pattern = 1, 4 do
    local build, calls = builder_with_calls()
    local sequence = build({1, 2, 3, 4}, pattern, false, 60, -1, 5, 2)
    luaunit.assert_equals(note_values(sequence), expected[pattern])
    luaunit.assert_equals(#calls, 4)
    for i = 1, 4 do
      luaunit.assert_equals(calls[i], {i, 4, pattern})
    end
  end
end

-- Characterisation, not manual text: sparse and muted slots are explicit false
-- entries, so they continue consuming arp time, acceleration and velocity ordinal.
function test_arp_descriptor_preserves_sparse_slots_and_muted_root_position()
  local build = arp_descriptor.new(chord_order.index)
  local chords = {[1] = 1, [2] = 0, [4] = 4}

  local forward = build(chords, 1, false, 60, 0, 0, 0)
  luaunit.assert_equals(note_values(forward), {60, 61, false, false, 64})

  local reverse_muted = build(chords, 2, true, 60, 0, 0, 0)
  luaunit.assert_equals(note_values(reverse_muted), {64, false, false, 61, false})
end

-- Characterisation, not manual text: without chord masks an unmuted root is a
-- one-slot ratchet; with a muted root there is no playable arp descriptor.
function test_arp_descriptor_preserves_root_only_and_empty_muted_results()
  local build, calls = builder_with_calls()
  local root_only = build({}, 4, false, 60, -2, 7, 3)
  luaunit.assert_equals(#root_only, 1)
  luaunit.assert_equals(root_only[1], {
    note_value = 63,
    octave_mod = -2,
    transpose = 7
  })
  luaunit.assert_equals(#calls, 4)

  local empty_muted = build({}, 1, true, 60, -2, 7, 3)
  luaunit.assert_nil(empty_muted)
  luaunit.assert_equals(#calls, 8)
end
