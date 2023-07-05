FadeButton = {}
FadeButton.__index = FadeButton

function FadeButton:new(x, y, min, max)
  local self = setmetatable({}, FadeButton)
  self.x = x
  self.y = y
  self.min = min
  self.max = max
  self.value = min

  return self
end


function FadeButton:draw()

  local brightness = 3

  -- TODO: Fade logic for in-between values

  if self.value + 1 == self.min then
    brightness = 15
  end

  if self.value + 1 >= self.max then 
    brightness = 3
  end

  g:led(self.x, self.y, brightness)

end

function FadeButton:set_value(val)
  self.value = val
end

function FadeButton:press(x, y)
  if (self.x == x and self.y == y) then
    -- self.value = self.min - 1
  end
end

function FadeButton:is_this(x, y)
  if (self.x == x and self.y == y) then
    return true
  end
  return false
end



return FadeButton