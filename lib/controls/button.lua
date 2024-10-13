button = {}
button.__index = button

function button:new(x, y, states)
  local self = setmetatable({}, button)
  self.x = x
  self.y = y
  self.blink_active = false
  if (states) then
    self.states = states
  else
    self.states = {}
    self.states[1] = {"off", 2}
    self.states[2] = {"on", 15}
  end
  self.state = 1
  self.bright_mod = 6
  return self
end

function button:draw()
  if self.blink_active and fn.get_blink_state() then
    grid_abstraction.led(self.x, self.y, self.states[self.state][2] - self.bright_mod)
  else
    grid_abstraction.led(self.x, self.y, self.states[self.state][2])
  end
end

function button:get_state()
  return self.state
end

function button:set_state(val)
  self.state = val
end

function button:blink()
  self.blink_active = true
end

function button:no_blink()
  self.blink_active = false
end

function button:press(x, y)
  if (self.x == x and self.y == y) then
    if self.state == #self.states then
      self.state = 1
    else
      self.state = self.state + 1
    end
  end
end

function button:is_this(x, y)
  if (self.x == x and self.y == y) then
    return true
  end
  return false
end

return button
