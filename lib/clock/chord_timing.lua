-- Musical spacing in channel-step units, before swing/pulse quantisation.
local timing = {}

function timing.gap(division, spread, acceleration, ordinal)
  local value = division + spread * (1 + (ordinal - 1) * acceleration)
  if value <= 0 then return nil end
  return value
end

function timing.delay(division, spread, acceleration, ordinal)
  -- Disabled articulation remains an ordinary simultaneous chord.
  if not division or division == 0 or ordinal == 0 then return 0 end
  if not timing.gap(division, spread, acceleration, ordinal) then return nil end
  return ordinal * (division + spread) + spread * acceleration * ordinal * (ordinal - 1) / 2
end

return timing
