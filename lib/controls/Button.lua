Button = {}
Button.__index = Button

function Button:new(x, y, states)
  local self = setmetatable({}, Button)
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


function Button:draw()
  g:led(self.x, self.y, self.states[self.state][2] - self.bright_mod)
end

function Button:get_state()
  return self.state
end

function Button:set_state(val)
  self.state = val
end



function Button:blink()
  self.bclock = clock.run(function()
    while true do
      if self.bstate then
        self.bright_mod = 0
        self.bstate = false
      else
        self.bright_mod = 5
        self.bstate = true
      end
      fn.dirty_grid(true)
      clock.sleep(0.3)
    end
  end)
end

function Button:no_blink()
  if self.bclock then
    self.bright_mod = 0
    clock.cancel(self.bclock)
  end
end

function Button:press(x, y)
  if (self.x == x and self.y == y) then
    if self.state == #self.states
      then self.state = 1 
    else
      self.state = self.state + 1
    end
  end
end

function Button:is_this(x, y)
  if (self.x == x and self.y == y) then
    return true
  end
  return false
end

return Button