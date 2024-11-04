local page = {}
page.__index = page



function page:new(name, func)
  local self = setmetatable({}, page)
  self.name = name
  self.draw_func = func
  self.sub_page_draw_func = function()
  end
  self.sub_name_func = function()
    return ""
  end
  self.sub_page_enabled = false
  return self
end

function page:get_name()
  return self.name
end

function page:set_name(name)
  self.name = name
end

function page:set_sub_name_func(func)
  self.sub_name_func = func
end

function page:enable_sub_page()
  self.sub_page_enabled = true
end

function page:disable_sub_page()
  self.sub_page_enabled = false
end

function page:set_sub_page_draw_func(func)
  self.sub_page_draw_func = func
end

function page:draw()
  screen.font_size(8)
  screen.level(10)
  screen.move(0, 9)
  screen.text(self.sub_name_func() .. self.name)
  if self.sub_page_enabled then
    self.sub_page_draw_func()
  else
    self.draw_func()
  end
end

function page:toggle_sub_page()
  self.sub_page_enabled = not self.sub_page_enabled
  fn.dirty_screen(true)
end

function page:is_sub_page_enabled()
  return self.sub_page_enabled
end

return page
