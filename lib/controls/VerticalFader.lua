VerticalFader = {}
VerticalFader.__index = VerticalFader

function VerticalFader:new(x, y, size)
  local self = setmetatable({}, VerticalFader)
  self.x = x
  self.y = y
  self.size = size
  self.value = 0
  self.vertical_offset = 0
  self.horizontal_offset = 0
  return self
end

function VerticalFader:draw()

  local inactive_led_brightness = 1
  local x = self.x - self.horizontal_offset

  if (x < 1 or x > 16) then
    return
  end

  if (((self.x - 1) % 4) == 0) then
    inactive_led_brightness = 2
  end

  if (((self.x - 1) % 16) == 0) then
    inactive_led_brightness = 3
  end

  for i = self.y, 7 do
    if (i == 7 - self.vertical_offset) then
      g:led(x, i, 3)
    elseif (self.size - i - self.vertical_offset + 1 > 0) then
      g:led(x, i, inactive_led_brightness)
    end
  end

  local active_led = self.y + self.value - 1 - self.vertical_offset
  if (self.value > 0 and active_led < 8) then

    g:led(x, active_led, 15)
  end

end

function VerticalFader:press(x, y)
  if y >= self.y and y <= 7 and x == self.x - self.horizontal_offset then

    self.value = y + self.vertical_offset
  end
  
end

function VerticalFader:set_vertical_offset(o)
  self.vertical_offset = o
end

function VerticalFader:set_horizontal_offset(o)
  self.horizontal_offset = o
end

return VerticalFader