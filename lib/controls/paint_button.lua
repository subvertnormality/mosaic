button = {}
button.__index = button

function button:new(x, y, states)
  local self = setmetatable({}, button)
  self.x = x
  self.y = y
  if (states) then
    self.states = states
  else
    self.states = {}
    self.states[1] = {"inactive", 3}
    self.states[2] = {"save", 15}
  end
  self.state = 1

  return self
end

function button:draw()
  grid_abstraction.led(self.x, self.y, self.states[self.state][2])
end

function button:get_state()
  return self.value
end

function button:set_state(val)
  self.value = val
end

function button:press(x, y)
  if (self.x == x and self.y == y) then
    if self.state == 1 then
      self.state = self.state + 1
    elseif self.state == #states then
      self.state = 1
    end
  end
end

return button
