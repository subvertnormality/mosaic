local value_selector = {}
value_selector.__index = value_selector

local fn = include("mosaic/lib/functions")

function value_selector:new(x, y, name, min, max)
  local self = setmetatable({}, value_selector)
  self.x = x
  self.y = y
  self.name = name
  self.min = min
  self.max = max
  self.value = 0
  self.selected = false
  self.view_transform_func = function(value) return value end

  return self
end

function value_selector:draw()
  if self.selected then
    screen.level(15)
  else
    screen.level(1)
  end
  screen.move(self.x, self.y)
  screen.font_size(8)
  screen.text(self.name)
  screen.move(self.x, self.y + 12)
  screen.font_size(14)
  if (self.value) then
    screen.text(self.view_transform_func(self.value))
  else
    screen.text("0")
  end
  screen.font_size(8)
end

function value_selector:select()
  self.selected = true
  fn.dirty_screen(true)
end

function value_selector:deselect()
  self.selected = false
  fn.dirty_screen(true)
end

function value_selector:is_selected()
  return self.selected
end

function value_selector:increment()
  self.value = self.value + 1
  if self.value > self.max then
    self.value = self.max
  end
  fn.dirty_screen(true)
end

function value_selector:decrement()
  self.value = self.value - 1
  if self.value < self.min then
    self.value = self.min
  end
  fn.dirty_screen(true)
end

function value_selector:get_value()
  return self.value
end

function value_selector:set_name()
  self.name = name
  fn.dirty_screen(true)
end

function value_selector:set_value(v)
  self.value = v
  fn.dirty_screen(true)
end

function value_selector:set_view_transform_func(func)
  self.view_transform_func = func
end

return value_selector
