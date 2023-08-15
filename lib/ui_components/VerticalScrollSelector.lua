local VerticalScrollSelector = {}
VerticalScrollSelector.__index = VerticalScrollSelector

  -- items = {{name: "name", value: {}}, {name: "name", value: {}}}
function VerticalScrollSelector:new(x, y, name, items)
  local self = setmetatable({}, VerticalScrollSelector)
  self.name = name
  self.x = x
  self.y = y

  self.items = items
  self.meta_items = nil
  self.selected_item = 1

  self.selected = false

  return self
end

function VerticalScrollSelector:get_selected_index()
  return self.selected_item
end

function VerticalScrollSelector:get_selected_item()
  return self.items[self.selected_item]
end

function VerticalScrollSelector:set_selected_item(selected_item)
  self.selected_item = selected_item
end

function VerticalScrollSelector:set_items(items)
  self.items = items
end

function VerticalScrollSelector:get_meta_item()
  return self.meta_items
end

function VerticalScrollSelector:set_meta_item(items)
  self.meta_items = items
end


function VerticalScrollSelector:draw()
  if not self.items then return end

  screen.move(self.x, self.y)

  if self.selected_item and self.items[self.selected_item - 1] then
    screen.level(1)
    if self.items[self.selected_item - 1].name then 
      screen.text(self.items[self.selected_item - 1].name)
    else
      screen.text(self.items[self.selected_item - 1])
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
      screen.text(self.items[self.selected_item].name)
    else
      screen.text(self.items[self.selected_item])
    end
  end


  screen.move(self.x, self.y + 20)

  if self.selected_item and self.items[self.selected_item + 1] then
    screen.level(1)
    if self.items[self.selected_item + 1].name then 
      screen.text(self.items[self.selected_item + 1].name) 
    else
      screen.text(self.items[self.selected_item + 1])
    end
  end

end

function VerticalScrollSelector:scroll_down()
  if self.selected_item < #self.items then
    self.selected_item = self.selected_item + 1
  end
  fn.dirty_screen(true)
end

function VerticalScrollSelector:scroll_up()
  if self.selected_item > 1 then
    self.selected_item = self.selected_item - 1
  end
  fn.dirty_screen(true)
end

function VerticalScrollSelector:select() 
  self.selected = true
  fn.dirty_screen(true)
end

function VerticalScrollSelector:deselect() 
  self.selected = false
  fn.dirty_screen(true)
end

function VerticalScrollSelector:is_selected()
  return self.selected
end

return VerticalScrollSelector