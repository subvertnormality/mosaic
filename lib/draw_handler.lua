local draw_handler = {}
local fn = include("mosaic/lib/functions")

-- Create a table for the handlers
draw_handler.grid_handlers = {}
draw_handler.ui_handlers = {}

-- Register a function with a page
function draw_handler:register_grid(page, func)
  -- If no functions have been registered for this page yet, create a new list
  if self.grid_handlers[page] == nil then
    self.grid_handlers[page] = {}
  end

  -- Add the function to the list of handlers for this page
  table.insert(self.grid_handlers[page], func)
end

-- Call all functions registered with a page
function draw_handler:handle_grid(page)

  -- Call all menu press handlers
  for _, func in ipairs(self.grid_handlers["menu"]) do
    func(x, y)
  end

  -- If no functions have been registered for this page, do nothing
  if self.grid_handlers[fn.find_key(program.get_pages(), page)] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.grid_handlers[fn.find_key(program.get_pages(), page)]) do
    func()
  end
end

-- Register a function with a page
function draw_handler:register_ui(page, func)
  -- If no functions have been registered for this page yet, create a new list
  if self.ui_handlers[page] == nil then
    self.ui_handlers[page] = {}
  end

  -- Add the function to the list of ui_handlers for this page
  table.insert(self.ui_handlers[page], func)
end

-- Call all functions registered with a page
function draw_handler:handle_ui(page)

  -- Call all menu press handlers
  for _, func in ipairs(self.ui_handlers["tooltip"]) do
    func(x, y)
  end

  -- If no functions have been registered for this page, do nothing
  if self.ui_handlers[fn.find_key(program.get_pages(), page)] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.ui_handlers[fn.find_key(program.get_pages(), page)]) do
    func()
  end
end


return draw_handler