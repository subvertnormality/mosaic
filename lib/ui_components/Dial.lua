local Dial = {}
Dial.__index = Dial

function Dial:new(x, y, name, top_label, bottom_label)
  local self = setmetatable({}, Dial)
  self.x = x
  self.y = y
  self.name = name
  self.value = 0
  self.top_label = top_label
  self.bottom_label = bottom_label
  self.selected = false
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
  screen.text(self.value)
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


return Dial