local pages = {}
pages.__index = pages

local fn = include("mosaic/lib/functions")

function pages:new()
  local self = setmetatable({}, pages)
  self.pages = {}
  self.selected_page = 0
  return self
end

function pages:draw()
  local x = 0

  for i = 1, fn.table_count(self.pages) do
    screen.move(x, 1)
    if self.selected_page == i then
      screen.level(10)
    else
      screen.level(1)
    end
    screen.text("_")
    x = x + 10
  end

  if (self.selected_page == nil) then
    if self.pages[1] then
      self.pages[1]:draw()
    end
  else
    if self.selected_page > 0 and self.pages[self.selected_page] then
      self.pages[self.selected_page]:draw()
    end
  end
end

function pages:add_page(page)
  table.insert(self.pages, page)
end

function pages:select_page(page)
  self.selected_page = page
end

function pages:get_selected_page()
  return self.selected_page
end

function pages:next_page()
  self.selected_page = self.selected_page + 1
  if self.selected_page > fn.table_count(self.pages) then
    self.selected_page = fn.table_count(self.pages)
  end
end

function pages:previous_page()
  self.selected_page = self.selected_page - 1
  if self.selected_page < 1 then
    self.selected_page = 1
  end
end

return pages
