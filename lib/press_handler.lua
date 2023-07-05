local press_handler = {}

-- Create a table for the handlers
press_handler.handlers = {}
press_handler.dual_handlers = {}

-- Register a function with a page
function press_handler:register(page, func)
  -- If no functions have been registered for this page yet, create a new list
  if self.handlers[page] == nil then
    self.handlers[page] = {}
  end

  -- Add the function to the list of handlers for this page
  table.insert(self.handlers[page], func)
end

-- Register a function with a page
function press_handler:register_dual(page, func)
  -- If no functions have been registered for this page yet, create a new list
  if self.dual_handlers[page] == nil then
    self.dual_handlers[page] = {}
  end

  -- Add the function to the list of handlers for this page
  table.insert(self.dual_handlers[page], func)
end


-- Call all functions registered with a page
function press_handler:handle(page, x, y)

  -- Call all menu press handlers
  for _, func in ipairs(self.handlers["menu"]) do
    func(x, y)
  end

  -- If no functions have been registered for this page, do nothing
  if self.handlers[fn.find_key(pages, page)] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.handlers[fn.find_key(pages, page)]) do
    func(x, y)
  end

end

-- Call all functions registered with a page
function press_handler:handle_dual(page, x, y, x2, y2)

  -- If no functions have been registered for this page, do nothing
  if self.dual_handlers[fn.find_key(pages, page)] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.dual_handlers[fn.find_key(pages, page)]) do
    func(x, y, x2, y2)
  end

end

return press_handler