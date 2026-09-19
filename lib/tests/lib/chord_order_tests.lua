local chord_order = include("mosaic/lib/musical_resolution/chord_order")

local function sequence_for(pattern)
  local sequence = {}
  for i = 1, 4 do
    sequence[i] = chord_order.index(i, 4, pattern)
  end
  return sequence
end

-- Characterisation, not manual text: these are the exact four-voice orderings
-- used by both arpeggiated and strummed chord playback before extraction.
function test_chord_order_preserves_each_existing_pattern()
  luaunit.assert_equals(sequence_for(nil), {1, 2, 3, 4})
  luaunit.assert_equals(sequence_for(1), {1, 2, 3, 4})
  luaunit.assert_equals(sequence_for(2), {4, 3, 2, 1})
  luaunit.assert_equals(sequence_for(3), {1, 4, 2, 3})
  luaunit.assert_equals(sequence_for(4), {4, 1, 3, 2})
end

function test_chord_order_preserves_default_for_unknown_pattern()
  luaunit.assert_equals(sequence_for(5), {1, 2, 3, 4})
end
