local Pages = {}
Pages.__index = Pages

function Pages:new()
  local self = setmetatable({}, Pages)
  self.pages = {}
  self.selected_pages = nil
  return self
end


function Pages:draw()
  if (self.selected_page == nil) then 
    if self.pages[0] then 
      self.pages[0]:draw()
    end
  else
    self.selected_page:draw()
  end
end

function Pages:add_page(page)
  self.pages[page:get_name()] = page
end

function Pages:select_page(page_name) 
  self.selected_page = self.pages[page_name]
end

return Pages