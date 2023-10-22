local Dial = {}
Dial.__index = Dial

local fn = include("mosaic/lib/functions")

function Dial:new(x, y, name, id, top_label, bottom_label)
  local self = setmetatable({}, Dial)
  self.x = x
  self.y = y
  self.name = name
  self.value = 0
  self.top_label = top_label
  self.bottom_label = bottom_label
  self.selected = false
  self.min_value = nil
  self.max_value = nil
  self.off_value = -1
  self.ui_labels = nil

  return self
end

function Dial:draw()
  if self.selected then
    screen.level(15)
  else
    screen.level(1)
  end
  screen.move(self.x, self.y)
  screen.font_size(8)
  screen.text(self.top_label)
  screen.move(self.x, self.y + 7)

  if (self.min_value and self.value < self.min_value) then
    self.value = self.off_value
  end
  if (self.max_value and self.value > self.max_value) then
    self.value = self.off_value
  end
  
  if self.value == self.off_value then
    screen.text("off")
  else
    if self.ui_labels and self.min_value then
      screen.text(self.ui_labels[self.value - ((self.min_value) - 1)])
    else
      screen.text(self.value)
    end
  end
  screen.move(self.x, self.y + 14)
  screen.text(self.bottom_label)
  screen.font_size(8)
end

function Dial:select()
  self.selected = true
  fn.dirty_screen(true)
end

function Dial:deselect()
  self.selected = false
  fn.dirty_screen(true)
end

function Dial:is_selected()
  return self.selected
end

function Dial:increment()
  self.value = self.value + 1
  fn.dirty_screen(true)
end

function Dial:decrement()
  self.value = self.value - 1
  fn.dirty_screen(true)
end

function Dial:set_value(value)
  if value == nil or (self.min_value and value < self.min_value) or (self.max_value and value > self.max_value) then
    value = self.off_value
  end
  self.value = value
  fn.dirty_screen(true)
end

function Dial:set_top_label(label)
  self.top_label = label
  fn.dirty_screen(true)
end

function Dial:set_bottom_label(label)
  self.bottom_label = label
  fn.dirty_screen(true)
end

function Dial:set_name()
  self.name = name
  fn.dirty_screen(true)
end

function Dial:get_name()
  return self.name
end

function Dial:get_id()
  return self.id
end

function Dial:set_off_value(off_value)
  self.off_value = off_value
end

function Dial:set_ui_labels(ui_labels)
  self.ui_labels = ui_labels
end

function Dial:set_min_value(min_value)
  self.min_value = min_value
end

function Dial:set_max_value(max_value)
  self.max_value = max_value
end


return Dial
