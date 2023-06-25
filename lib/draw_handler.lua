

draw_handler = {}

-- Create a table for the handlers
draw_handler.handlers = {}

-- Register a function with a page
function draw_handler:register(page, func)
  -- If no functions have been registered for this page yet, create a new list
  if self.handlers[page] == nil then
    self.handlers[page] = {}
  end

  -- Add the function to the list of handlers for this page
  table.insert(self.handlers[page], func)
end

-- Call all functions registered with a page
function draw_handler:handle(page)
  -- If no functions have been registered for this page, do nothing
  if self.handlers[page] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.handlers[page]) do
    func()
  end
end

return draw_handler