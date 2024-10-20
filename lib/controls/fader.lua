fader = {}
fader.__index = fader



function fader:new(x, y, length, size)
  local self = setmetatable({}, fader)
  self.x = x
  self.y = y
  self.length = length
  self.size = size
  self.value = 1
  self.is_disabled = false
  self.dimmed = {}

  self.pre_func = function()
  end

  for i = 1, self.length do
    self.dimmed[i] = false
  end

  return self
end

function fader:draw_simple()
  grid_abstraction.led(self.x, self.y, 2)

  for i = self.x, self.length + self.x - 1 do
    if self.dimmed[i] then
      grid_abstraction.led(i, self.y, 0)
    else
      grid_abstraction.led(i, self.y, 2)
    end
  end

  self.pre_func(self.x, self.y, self.length)
  
  if (self.value ~= nil and self.value > 0) then
    if self.dimmed[self.x + self.value - 1] then
      grid_abstraction.led(self.x + self.value - 1, self.y, 7)
    else
      grid_abstraction.led(self.x + self.value - 1, self.y, 15)
    end
  end
end

function fader:draw_fine_grain()
  -- Draw the fader ends
  grid_abstraction.led(self.x, self.y, 7)
  grid_abstraction.led(self.length + self.x - 1, self.y, 7)
  
  -- Draw the fader background
  for i = self.x + 1, self.length + self.x - 2 do
    grid_abstraction.led(i, self.y, 2)
  end
  
  if self.value == nil then return end
  
  -- Calculate the position and brightness of the lit LEDs
  local total_steps = self.size
  local num_leds = self.length - 2
  local step_size = total_steps / num_leds
  local current_led = math.floor(self.value / step_size)
  local remainder = self.value % step_size
  
  -- Handle the case when the value is at maximum
  if self.value == self.size then
    grid_abstraction.led(self.length + self.x - 2, self.y, 15)
    return
  end
  
  -- Handle the transitioning LED
  if remainder > 0 and current_led < num_leds then
    local brightness = math.floor(fn.scale(remainder, 0, step_size, 4, 15))
    grid_abstraction.led(self.x + current_led + 1, self.y, brightness)
  end
end

function fader:draw()
  if self.is_disabled then
    return
  end
  if self.length < self.size and self.length > 2 then
    self:draw_fine_grain()
  else
    self:draw_simple()
  end
end

function fader:get_value()
  if is_disabled then
    return 0
  end
  return self.value
end

function fader:set_value(val)
  self.value = val
end

function fader:set_size(size)
  if self.value > size then
    self.value = size
  end
  self.size = size
end

function fader:set_length(length)
  self.length = length
end

function fader:set_pre_func(func)
  self.pre_func = func
end

function fader:disabled()
  self.is_disabled = true
end

function fader:enabled()
  self.is_disabled = false
end

function fader:press_simple(val)
  self.value = val
end

function fader:press_fine_grain(val)
  if (val == 1 and self.value > 1) then
    self.value = self.value - 1
  elseif (val == self.length and self.value < self.size) then
    self.value = self.value + 1
  elseif (val ~= 1 and val ~= self.length) then
    self.value = math.floor((self.size / (self.length - 2)) * (val - 2)) + 1
  end
end

function fader:press(x, y)
  if x >= self.x and x <= self.x + self.length - 1 and y == self.y then
    if self.length < self.size then
      self:press_fine_grain(x - self.x + 1)
    else
      self:press_simple(x - self.x + 1)
    end
  end
end

function fader:is_this(x, y)
  if x >= self.x and x <= self.x + self.length - 1 and y == self.y then
    return true
  end
  return false
end

function fader:dim(x)
  self.dimmed[x] = true
end

function fader:light(x)
  self.dimmed[x] = false
end

return fader
