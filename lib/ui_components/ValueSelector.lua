local ValueSelector = {}
ValueSelector.__index = ValueSelector

function ValueSelector:new(x, y, name, min, max)
  local self = setmetatable({}, ValueSelector)
  self.x = x
  self.y = y
  self.name = name
  self.min = min
  self.max = max
  self.value = 0
  self.selected = false

  return self
end



function ValueSelector:draw()
  if self.selected then
    screen.level(15)
  else
    screen.level(1)
  end
  screen.move(self.x, self.y)
  screen.font_size(8)
  screen.text(self.name)
  screen.move(self.x + 5, self.y + 12)
  screen.font_size(14)
  if (self.value) then
    screen.text(self.value)
  else
    screen.text("0")
  end
  screen.font_size(8)
end

function ValueSelector:select() 
  self.selected = true
  fn.dirty_screen(true)
end

function ValueSelector:deselect() 
  self.selected = false
  fn.dirty_screen(true)
end

function ValueSelector:is_selected()
  return self.selected
end

function ValueSelector:increment()
  self.value = self.value + 1
  if self.value > self.max then
    self.value = self.max
  end
  fn.dirty_screen(true)
end

function ValueSelector:decrement()
  self.value = self.value - 1
  if self.value < self.min then
    self.value = self.min
  end
  fn.dirty_screen(true)
end

function ValueSelector:get_value()
  return self.value
end

function ValueSelector:set_name()
  self.name = name
  fn.dirty_screen(true)
end

function ValueSelector:set_value(v)
  self.value = v
  fn.dirty_screen(true)
end

return ValueSelector