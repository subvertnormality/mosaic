local vertical_scroll_selector = {}
vertical_scroll_selector.__index = vertical_scroll_selector



function vertical_scroll_selector:new(x, y, name, items)
  local self = setmetatable({}, vertical_scroll_selector)
  self.name = name
  self.x = x
  self.y = y

  self.items = items
  self.meta_items = nil
  self.selected_item = 1

  self.selected = false

  return self
end

function vertical_scroll_selector:get_selected_index()
  return self.selected_item
end

function vertical_scroll_selector:get_selected_item()
  return self.items[self.selected_item]
end

function vertical_scroll_selector:set_selected_item(selected_item)
  self.selected_item = selected_item
end

function vertical_scroll_selector:set_items(items)
  self.items = items
end

function vertical_scroll_selector:get_items()
  return self.items
end

function vertical_scroll_selector:get_meta_item()
  return self.meta_items
end

function vertical_scroll_selector:set_meta_item(items)
  self.meta_items = items
end

function vertical_scroll_selector:draw()
  if not self.items then
    return
  end

  screen.move(self.x, self.y)

  if self.selected_item and self.items[self.selected_item - 1] then
    screen.level(1)
    if self.items[self.selected_item - 1].name then
      screen.text(self.items[self.selected_item - 1].name, 12)
    else
      screen.text(self.items[self.selected_item - 1], 12)
    end
  end

  screen.move(self.x + 5, self.y + 10)

  if self.items[self.selected_item] then
    if self.selected then
      screen.level(15)
    else
      screen.level(5)
    end
    if self.items[self.selected_item].name then
      screen.text(self.items[self.selected_item].name, 12)
    else
      screen.text(self.items[self.selected_item], 12)
    end
  end

  screen.move(self.x, self.y + 20)

  if self.selected_item and self.items[self.selected_item + 1] then
    screen.level(1)
    if self.items[self.selected_item + 1].name then
      screen.text(self.items[self.selected_item + 1].name, 12)
    else
      screen.text(self.items[self.selected_item + 1], 12)
    end
  end
end

function vertical_scroll_selector:scroll_down()
  if self.selected_item < #self.items then
    self.selected_item = self.selected_item + 1
  end
  fn.dirty_screen(true)
end

function vertical_scroll_selector:scroll_up()
  if self.selected_item > 1 then
    self.selected_item = self.selected_item - 1
  end
  fn.dirty_screen(true)
end

function vertical_scroll_selector:scroll(direction) -- 1 for down, -1 for up
  if direction > 0 then
    for i = 1, direction do
      self:scroll_down()
    end
  elseif direction < 0 then
    for i = 1, math.abs(direction) do
      self:scroll_up()
    end
  end
end

function vertical_scroll_selector:select()
  self.selected = true
  fn.dirty_screen(true)
end

function vertical_scroll_selector:deselect()
  self.selected = false
  fn.dirty_screen(true)
end

function vertical_scroll_selector:is_selected()
  return self.selected
end

return vertical_scroll_selector
