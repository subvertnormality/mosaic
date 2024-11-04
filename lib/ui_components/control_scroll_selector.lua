local control_scroll_selector = {}
control_scroll_selector.__index = control_scroll_selector



function control_scroll_selector:new(x, y, items)
  local self = setmetatable({}, control_scroll_selector)
  self.x = x
  self.y = y
  self.name = name
  self.items = items
  self.selected_item = 1
  return self
end

function control_scroll_selector:select(x)
  self.items[x]:select()
end

function control_scroll_selector:draw()
  for i = 1, #self.items do
    self.items[i]:draw()
  end
end

function control_scroll_selector:scroll_next()
  if self.selected_item < #self.items then
    self.selected_item = self.selected_item + 1
  end
  for i = 1, #self.items do
    self.items[i]:deselect()
  end
  self.items[self.selected_item]:select()
  fn.dirty_screen(true)
end

function control_scroll_selector:scroll_previous()
  if self.selected_item > 1 then
    self.selected_item = self.selected_item - 1
  end
  for i = 1, #self.items do
    self.items[i]:deselect()
  end
  self.items[self.selected_item]:select()
  fn.dirty_screen(true)
end

function control_scroll_selector:set_items(items)
  self.items = items
  fn.dirty_screen(true)
end

function control_scroll_selector:get_selected_index()
  return self.selected_item
end

function control_scroll_selector:get_selected_item()
  return self.items[self.selected_item]
end

function control_scroll_selector:set_selected_item(item)
  self.items[self.selected_item]:select()
  fn.dirty_screen(true)
end

return control_scroll_selector
