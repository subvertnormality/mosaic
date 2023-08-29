local ListSelector = {}
ListSelector.__index = ListSelector

local fn = include("mosaic/lib/functions")

function ListSelector:new(x, y, name, list)
  local self = setmetatable({}, ListSelector)
  self.x = x
  self.y = y
  self.name = name
  self.list = list
  self.selected_value = 1
  self.selected = false

  return self
end

function ListSelector:draw()
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
  screen.text(self.list[self.selected_value].name)
  screen.font_size(8)
end

function ListSelector:select() 
  self.selected = true
  fn.dirty_screen(true)
end

function ListSelector:deselect() 
  self.selected = false
  fn.dirty_screen(true)
end

function ListSelector:is_selected()
  return self.selected
end

function ListSelector:increment()
  self.selected_value = self.selected_value + 1
  if self.selected_value > #self.list then
    self.selected_value = #self.list
  end
  fn.dirty_screen(true)
end

function ListSelector:decrement()
  self.selected_value = self.selected_value - 1
  if self.selected_value < 1 then
    self.selected_value = 1
  end
  fn.dirty_screen(true)
end

function ListSelector:set_selected_value(selected_value)
  self.selected_value = selected_value
  fn.dirty_screen(true)
end

function ListSelector:get_selected()
  return self.list[self.selected_value]
end

function ListSelector:set_name()
  self.name = name
  fn.dirty_screen(true)
end

function ListSelector:set_list(list)
  self.list = list
  fn.dirty_screen(true)
end

return ListSelector