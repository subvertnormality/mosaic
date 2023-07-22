local VerticalScrollSelector = {}
VerticalScrollSelector.__index = VerticalScrollSelector

  -- items = {{name: "name", value: {}}, {name: "name", value: {}}}
function VerticalScrollSelector:new(x, y, name, items)
  local self = setmetatable({}, VerticalScrollSelector)
  self.name = name
  self.x = x
  self.y = y

  self.items = items
  self.selected_item = 1

  return self
end

function VerticalScrollSelector:get_selected_item()
  return self.items[self.selected_item]
end

function VerticalScrollSelector:set_selected_item(selected_item)
  self.selected_item = selected_item
end


function VerticalScrollSelector:draw()
  if not self.items then return end

  screen.move(self.x, self.y)

  if self.items[self.selected_item - 1] then
    screen.level(1)
    screen.text(self.items[self.selected_item - 1].name)
  end

  screen.move(self.x + 5, self.y + 12)

  if self.items[self.selected_item] then
    screen.level(10)
    screen.text(self.items[self.selected_item].name)
  end


  screen.move(self.x, self.y + 24)

  if self.items[self.selected_item + 1] then
    screen.level(1)
    screen.text(self.items[self.selected_item + 1].name)
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


return VerticalScrollSelector