local Page = {}
Page.__index = Page

function Page:new(name, func)
  local self = setmetatable({}, Page)
  self.name = name
  self.draw_func = func
  self.sub_name_func = function() return "" end
  return self
end

function Page:get_name()
  return self.name
end

function Page:set_name(name)
  self.name = name
end

function Page:set_sub_name_func(func)
  self.sub_name_func = func
end

function Page:draw()
  screen.level(1)
  screen.move(5, 10)
  screen.text(self.sub_name_func()..self.name)
  self.draw_func()
end


return Page