VerticalFader = {}
VerticalFader.__index = VerticalFader

local fn = include("mosaic/lib/functions")

local shared_bright_mod = 0

local bclock = clock.run(function()
  while true do
    if shared_bright_mod < 0 then
      shared_bright_mod = 1
    else
      shared_bright_mod = -1
    end
    fn.dirty_grid(true)
    clock.sleep(0.3)
  end
end)


function VerticalFader:new(x, y, size)
  local self = setmetatable({}, VerticalFader)
  self.x = x
  self.y = y
  self.size = size
  self.value = 0
  self.vertical_offset = 0
  self.horizontal_offset = 0
  self.led_brightness = 3
  return self
end

function VerticalFader:draw()

  local x = self.x - self.horizontal_offset

  if (x < 1 or x > 16) then
    return
  end

  local bright_mod = 0


  for i = self.y, 7 do
    bright_mod = 0

    if x == program.get().selected_pattern then
      if i == 1 then
        bright_mod = shared_bright_mod
      end
    end
    if (i == math.abs(7 - self.vertical_offset)) then
      grid_abstraction.led(x, i, 3 + bright_mod) -- mark the bottom of each page
    elseif ((i == 7) and (math.abs(7 - self.vertical_offset) == 0)) then
      grid_abstraction.led(x, i, 4 + bright_mod) -- mark the zero line stronger
    elseif (self.size - i - self.vertical_offset + 1 > 0) then
      grid_abstraction.led(x, i, self.led_brightness + bright_mod)
    end
  end
  

  local active_led = self.y + self.value - 1 - self.vertical_offset
  if (self.value > 0 and active_led < 8) then
    if self.x == program.get().selected_pattern then
      if self.y == active_led then
        bright_mod = shared_bright_mod
      else
        bright_mod = 0
      end
    end
    grid_abstraction.led(x, active_led, 12 + bright_mod)
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

function VerticalFader:get_horizontal_offset()
  return self.horizontal_offset
end

function VerticalFader:get_value()
  return self.value
end

function VerticalFader:set_value(val)
  self.value = val
end

function VerticalFader:set_dark()
  self.led_brightness = 1
end

function VerticalFader:set_light()
  self.led_brightness = 3
end

function VerticalFader:is_this(x, y)
  if (self.x == x + self.horizontal_offset and y <= 7) then
    return true
  end
  return false
end


return VerticalFader