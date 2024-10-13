local press_handler = {}


-- Create a table for the handlers
press_handler.handlers = {}
press_handler.dual_handlers = {}
press_handler.long_handlers = {}
press_handler.pre_handlers = {}
press_handler.post_handlers = {}

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

function press_handler:register_long(page, func)
  -- If no functions have been registered for this page yet, create a new list
  if self.long_handlers[page] == nil then
    self.long_handlers[page] = {}
  end

  -- Add the function to the list of handlers for this page
  table.insert(self.long_handlers[page], func)
end

function press_handler:register_pre(page, func)
  -- If no functions have been registered for this page yet, create a new list
  if self.pre_handlers[page] == nil then
    self.pre_handlers[page] = {}
  end

  -- Add the function to the list of handlers for this page
  table.insert(self.pre_handlers[page], func)
end

function press_handler:register_post(page, func)
  -- If no functions have been registered for this page yet, create a new list
  if self.post_handlers[page] == nil then
    self.post_handlers[page] = {}
  end

  -- Add the function to the list of handlers for this page
  table.insert(self.post_handlers[page], func)
end

-- Call all functions registered with a page
function press_handler:handle(page, x, y)

  local found_page = fn.find_key(program.get_pages(), page)
  
  -- Call all menu press handlers
  for _, func in ipairs(self.handlers["menu"]) do
    func(x, y)
  end

  -- If no functions have been registered for this page, do nothing
  if self.handlers[found_page] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.handlers[found_page]) do
    func(x, y)
  end

  save_confirm.cancel()
  autosave_reset()
end

-- Call all functions registered with a page
function press_handler:handle_dual(page, x, y, x2, y2)

  local found_page = fn.find_key(program.get_pages(), page)

  -- If no functions have been registered for this page, do nothing
  if self.dual_handlers[found_page] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.dual_handlers[found_page]) do
    func(x, y, x2, y2)
  end

  autosave_reset()
end

function press_handler:handle_long(page, x, y)

  local found_page = fn.find_key(program.get_pages(), page)

  -- Call all menu press handlers
  for _, func in ipairs(self.long_handlers["menu"]) do
    func(x, y)
  end

  -- If no functions have been registered for this page, do nothing
  if self.long_handlers[found_page] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.long_handlers[found_page]) do
    func(x, y)
  end

  autosave_reset()
end

function press_handler:handle_pre(page, x, y)

  local found_page = fn.find_key(program.get_pages(), page)

  -- If no functions have been registered for this page, do nothing
  if self.pre_handlers[found_page] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.pre_handlers[fn.find_key(program.get_pages(), page)]) do
    func(x, y)
  end
end

function press_handler:handle_post(page, x, y)

  local found_page = fn.find_key(program.get_pages(), page)

  -- If no functions have been registered for this page, do nothing
  if self.post_handlers[found_page] == nil then
    return
  end

  -- Otherwise, call all functions registered for this page
  for _, func in ipairs(self.post_handlers[found_page]) do
    func(x, y)
  end
end

return press_handler
