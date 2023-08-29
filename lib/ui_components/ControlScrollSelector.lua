local ControlScrollSelector = {}
ControlScrollSelector.__index = ControlScrollSelector

local fn = include("mosaic/lib/functions")

function ControlScrollSelector:new(x, y, items)
  local self = setmetatable({}, ControlScrollSelector)
  self.x = x
  self.y = y
  self.name = name
  self.items = items
  self.selected_item = 1
  return self
end

function ControlScrollSelector:select(x)
  self.items[x]:select()
end

function ControlScrollSelector:draw()
  for i = 1, #self.items do
    self.items[i]:draw()
  end
end

function ControlScrollSelector:scroll_next()
  if self.selected_item < #self.items then
    self.selected_item = self.selected_item + 1
  end
  for i = 1, #self.items do
    self.items[i]:deselect()
  end
  self.items[self.selected_item]:select()
  fn.dirty_screen(true)
end

function ControlScrollSelector:scroll_previous()
  if self.selected_item > 1 then
    self.selected_item = self.selected_item - 1
  end
  for i = 1, #self.items do
    self.items[i]:deselect()
  end
  self.items[self.selected_item]:select()
  fn.dirty_screen(true)
end

function ControlScrollSelector:set_items(items)
  self.items = items
  fn.dirty_screen(true)
end

function ControlScrollSelector:get_selected_index()
  return self.selected_item
end

function ControlScrollSelector:get_selected_item()
  return self.items[self.selected_item]
end

function ControlScrollSelector:set_selected_item(item)
  self.items[self.selected_item]:select()
  fn.dirty_screen(true)
end

return ControlScrollSelector