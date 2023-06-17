Fader = {}
Fader.__index = Fader

function Fader:new(x, y, length, size)
  local self = setmetatable({}, Fader)
  self.x = x
  self.y = y
  self.length = length
  self.size = size
  self.value = -1

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
  
end

function Fader:draw()
  if self.length < self.size then
    -- fine grain
  else
    self:draw_simple()
    
    
  end
end

function Fader:get_value()
  return self.value
end

function Fader:press_simple(val)
  self.value = val
end

function Fader:press(x, y)
  if x >= self.x and x <= self.x + self.length - 1 and y == self.y then


    if self.length < self.size then
      -- fine grain
    else
      self:press_simple(x - self.x + 1)
    end
  end
  
end


return Fader