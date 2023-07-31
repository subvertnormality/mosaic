Fader = {}
Fader.__index = Fader

function Fader:new(x, y, length, size)
  local self = setmetatable({}, Fader)
  self.x = x
  self.y = y
  self.length = length
  self.size = size
  self.value = 1
  self.is_disabled = false

  return self
end



function Fader:draw_simple()
  
  g:led(self.x, self.y, 2)
  for i = self.x, self.length + self.x - 1 do
    g:led(i, self.y, 2)
  end
  if (self.value > 0) then
    g:led(self.x + self.value - 1, self.y, 15)
  end
end


function Fader:draw_fine_grain()
  g:led(self.x, self.y, 7)
  g:led(self.length + self.x - 1, self.y, 7)
  for i = self.x + 1, self.length + self.x - 2 do
    g:led(i, self.y, 2)
  end
  local selected_led = math.floor(self.value / (self.size / (self.length - 2))) + 1
  
  if (self.value == self.size) then
    selected_led = self.length - 2
  end

  if (selected_led > 0 and selected_led < self.length - 1) then

    local modulator = math.floor(self.value % (self.size / (self.length - 2))) + 1
    local scaled_brightness = math.floor(fn.scale(modulator, 1, self.size / (self.length - 2), 4, 15))
    if (self.value == self.size) then -- hacky
      scaled_brightness = 15
    end
    g:led(self.x + selected_led, self.y, scaled_brightness)
  end
end

function Fader:draw()
  if self.is_disabled then return end
  if self.length < self.size and self.length > 2 then
    self:draw_fine_grain()
  else
    self:draw_simple()
  end
end

function Fader:get_value()
  if is_disabled then return 0 end
  return self.value
end

function Fader:set_value(val)
  self.value = val
end

function Fader:set_size(size)
  if self.value > size then
    self.value = size
  end
  self.size = size
end

function Fader:set_length(length)
  self.length = length
end

function Fader:disabled()
  self.is_disabled = true
end

function Fader:enabled()
  self.is_disabled = false
end

function Fader:press_simple(val)
  self.value = val
end

function Fader:press_fine_grain(val)
  if (val == 1 and self.value > 1) then
    self.value = self.value - 1
  elseif (val == self.length and self.value < self.size) then
    self.value = self.value + 1
  elseif (val ~= 1 and val ~= self.length) then
    self.value = math.floor((self.size / (self.length - 2)) * (val - 2)) + 1
  end
end

function Fader:press(x, y)
  
  if x >= self.x and x <= self.x + self.length - 1 and y == self.y then
    if self.length < self.size then
      self:press_fine_grain(x - self.x + 1)
    else
      self:press_simple(x - self.x + 1)
    end
  end
  
end

function Fader:is_this(x, y)
  if x >= self.x and x <= self.x + self.length - 1 and y == self.y then
    return true
  end
  return false
end

return Fader