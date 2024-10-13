local list_selector = {}
list_selector.__index = list_selector



function list_selector:new(x, y, name, list)
  local self = setmetatable({}, list_selector)
  self.x = x
  self.y = y
  self.name = name
  self.list = list
  self.selected_value = 1
  self.selected = false

  return self
end

function list_selector:draw()
  if self.selected then
    screen.level(15)
  else
    screen.level(1)
  end
  screen.move(self.x, self.y)
  screen.font_size(8)
  screen.text(self.name)
  screen.move(self.x, self.y + 8)
  screen.text(self.list[self.selected_value].name)
  screen.font_size(8)
end

function list_selector:select()
  self.selected = true
  fn.dirty_screen(true)
end

function list_selector:deselect()
  self.selected = false
  fn.dirty_screen(true)
end

function list_selector:is_selected()
  return self.selected
end

function list_selector:increment()
  self.selected_value = self.selected_value + 1
  if self.selected_value > #self.list then
    self.selected_value = #self.list
  end
  fn.dirty_screen(true)
end

function list_selector:decrement()
  self.selected_value = self.selected_value - 1
  if self.selected_value < 1 then
    self.selected_value = 1
  end
  fn.dirty_screen(true)
end

function list_selector:set_selected_value(selected_value)
  self.selected_value = selected_value
  fn.dirty_screen(true)
end

function list_selector:get_selected()
  return self.list[self.selected_value]
end

function list_selector:set_name()
  self.name = name
  fn.dirty_screen(true)
end

function list_selector:set_list(list)
  self.list = list
  fn.dirty_screen(true)
end

return list_selector
