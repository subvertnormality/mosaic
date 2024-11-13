local draw = {}
local table_insert = table.insert
local ipairs = ipairs

-- Create a table for the handlers
draw.grid_handlers = {}
draw.ui_handlers = {}

-- Register a function with a page
function draw:register_grid(page, func)
  -- If no functions have been registered for this page yet, create a new list
  if self.grid_handlers[page] == nil then
    self.grid_handlers[page] = {}
  end

  -- Add the function to the list of handlers for this page
  table_insert(self.grid_handlers[page], func)
end

-- Call all functions registered with a page
function draw:handle_grid(page)

  local found_page = fn.find_key(pages.pages, page)
  
  -- Call all menu press handlers
  for _, func in ipairs(self.grid_handlers["menu"]) do
    func(x, y)
  end

  -- If no functions have been registered for this page, do nothing
  if self.grid_handlers[found_page] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.grid_handlers[found_page]) do
    func()
  end
end

-- Register a function with a page
function draw:register_ui(page, func)
  -- If no functions have been registered for this page yet, create a new list
  if self.ui_handlers[page] == nil then
    self.ui_handlers[page] = {}
  end

  -- Add the function to the list of ui_handlers for this page
  table_insert(self.ui_handlers[page], func)
end

-- Call all functions registered with a page
function draw:handle_ui(page)

  local found_page = fn.find_key(pages.pages, page)

  -- Call all menu press handlers
  for _, func in ipairs(self.ui_handlers["tooltip"]) do
    func(x, y)
  end

  -- If no functions have been registered for this page, do nothing
  if self.ui_handlers[found_page] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.ui_handlers[found_page]) do
    func()
  end
end

return draw
