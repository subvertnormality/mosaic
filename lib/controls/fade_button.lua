fade_button = {}
fade_button.__index = fade_button

function fade_button:new(x, y, min, max)
  local self = setmetatable({}, fade_button)
  self.x = x
  self.y = y
  self.min = min
  self.max = max
  self.value = min

  return self
end

function fade_button:draw()
  local brightness = 3

  -- TODO: Fade logic for in-between values

  if self.value + 1 == self.min then
    brightness = 15
  end

  if self.value + 1 >= self.max then
    brightness = 3
  end

  grid_abstraction.led(self.x, self.y, brightness)
end

function fade_button:set_value(val)
  self.value = val
end

function fade_button:press(x, y)
  if (self.x == x and self.y == y) then
  -- self.value = self.min - 1
  end
end

function fade_button:is_this(x, y)
  if (self.x == x and self.y == y) then
    return true
  end
  return false
end

return fade_button
