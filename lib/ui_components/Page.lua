local Page = {}
Page.__index = Page

function Page:new(name, func)
  local self = setmetatable({}, Page)
  self.name = name
  self.draw_func = func
  self.sub_page_draw_func = function () end
  self.sub_name_func = function() return "" end
  self.sub_page_enabled = false
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

function Page:enable_sub_page()
  self.sub_page_enabled = true
end

function Page:disable_sub_page()
  self.sub_page_enabled = false
end

function Page:set_sub_page_draw_func(func)
  self.sub_page_draw_func = func
end

function Page:draw()
  screen.level(10)
  screen.move(5, 10)
  screen.text(self.sub_name_func()..self.name)
  if self.sub_page_enabled then
    self.sub_page_draw_func()
  else
    self.draw_func()
  end
  
end

function Page:toggle_sub_page()
  self.sub_page_enabled = not self.sub_page_enabled
  fn.dirty_screen(true)
end

function Page:is_sub_page_enabled()
  return self.sub_page_enabled
end

return Page