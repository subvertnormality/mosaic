local chord_order = {}

function chord_order.index(i, total_notes, chord_strum_pattern)
  if chord_strum_pattern == 2 then
    return total_notes + 1 - i
  end

  if chord_strum_pattern == 3 then
    local half_i = i // 2
    return i % 2 == 1 and (half_i + 1) or (total_notes - half_i + 1)
  end

  if chord_strum_pattern == 4 then
    local half_i = i // 2
    return i % 2 == 1 and (total_notes - half_i) or half_i
  end

  return i
end

return chord_order
