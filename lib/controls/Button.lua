button = {}
button.__index = button

local fn = include("mosaic/lib/functions")

function button:new(x, y, states)
  local self = setmetatable({}, button)
  self.x = x
  self.y = y
  self.bclock = false
  self.bstate = true
  if (states) then
    self.states = states
  else
    self.states = {}
    self.states[1] = {"off", 2}
    self.states[2] = {"on", 15}
  end
  self.state = 1
  self.bright_mod = 0
  return self
end

function button:draw()
  grid_abstraction.led(self.x, self.y, self.states[self.state][2] - self.bright_mod)
end

function button:get_state()
  return self.state
end

function button:set_state(val)
  self.state = val
end

function button:blink()
  self.bclock =
    clock.run(
    function()
      while true do
        if self.bstate then
          self.bright_mod = 0
          self.bstate = false
        else
          self.bright_mod = 6
          self.bstate = true
        end
        fn.dirty_grid(true)
        clock.sleep(0.3)
      end
    end
  )
end

function button:no_blink()
  if self.bclock then
    self.bright_mod = 0
    clock.cancel(self.bclock)
  end
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
