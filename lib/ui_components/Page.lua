local Page = {}
Page.__index = Page

function Page:new(name, func)
  local self = setmetatable({}, Page)
  self.name = name
  self.draw_func = func
  return self
end

function Page:get_name()
  return self.name
end

function Page:draw()
  self.draw_func()
end


return Page