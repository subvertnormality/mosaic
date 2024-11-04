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

function fader:get_middle_button_position()
  -- For odd length, return the middle position
  -- For even length, return the lower of the two middle positions
  return math.floor((self.length + 1) / 2)
end

function fader:get_middle_value()
  -- Returns the middle value of the size range
  return math.floor((self.size + 1) / 2)
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
  grid_abstraction.led(self.x, self.y, 7)  -- Decrement button
  grid_abstraction.led(self.length + self.x - 1, self.y, 7)  -- Increment button
  
  -- Draw the fader background
  for i = self.x + 1, self.length + self.x - 2 do
    grid_abstraction.led(i, self.y, 2)
  end
  
  if self.value == nil then return end
  
  -- Calculate the position and brightness of the lit LEDs
  local total_steps = self.size
  local num_leds = self.length - 2
  local step_size = total_steps / num_leds
  local current_led = math.floor((self.value - 1) / step_size)
  local remainder = (self.value - 1) - current_led * step_size

  -- Ensure current_led is within bounds
  if current_led >= num_leds then
    current_led = num_leds - 1
    remainder = step_size
  end

  -- Handle the case when the value is at maximum
  if self.value == self.size then
    grid_abstraction.led(self.length + self.x - 2, self.y, 15)
    return
  end

  -- Calculate brightness
  local brightness = math.max(5, math.floor((remainder / step_size) * (15 - 5) + 5))
  grid_abstraction.led(self.x + current_led + 1, self.y, brightness)

  -- Ensure the middle button is highlighted when the middle value is selected
  local middle_button = self:get_middle_button_position()
  if self.value == self:get_middle_value() then
    grid_abstraction.led(self.x + middle_button - 1, self.y, 15)
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

function fader:press_simple(val)
  self.value = val
end

function fader:press_fine_grain(val)
  local relative_pos = val - 1  -- Convert to 0-based position
  local middle_button = self:get_middle_button_position() - 1  -- Convert to 0-based position
  
  if relative_pos == 0 and self.value > 1 then
    -- First button: decrease value
    self.value = self.value - 1
  elseif relative_pos == self.length - 1 and self.value < self.size then
    -- Last button: increase value
    self.value = self.value + 1
  elseif relative_pos == middle_button then
    -- Middle button: jump to middle value
    self.value = self:get_middle_value()
  elseif relative_pos ~= 0 and relative_pos ~= self.length - 1 then
    -- Other positions: calculate proportional value
    local num_positions = self.length - 2
    local position = relative_pos - 1
    local value = math.floor((position / (num_positions - 1)) * (self.size - 1)) + 1
    self.value = value
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

-- [Rest of the methods remain unchanged]
function fader:get_value()
  if self.is_disabled then
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
