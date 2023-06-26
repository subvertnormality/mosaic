VerticalFader = {}
VerticalFader.__index = VerticalFader

function VerticalFader:new(x, y, size)
  local self = setmetatable({}, VerticalFader)
  self.x = x
  self.y = y
  self.size = size
  self.value = 0
  return self
end

function VerticalFader:draw()
  g:led(self.x, self.y, 2)
  for i = self.x, self.size + self.y - 1 do
    g:led(self.x, i, 2)
  end
  if (self.value > 0) then
    g:led(self.x, self.y + self.value - 1, 15)
  end
end

return VerticalFader