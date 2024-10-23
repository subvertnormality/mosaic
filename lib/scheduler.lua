local scheduler = {
  coroutines = {},  -- active coroutines
  to_remove = {},   -- coroutines to remove after iteration
  next_id = 1,
  current_index = nil  -- Track which coroutine we're processing
}

function scheduler.start(co)
  if type(co) ~= "thread" then
    return nil
  end
  local id = scheduler.next_id
  scheduler.coroutines[id] = {
    co = co,
    created_at = os.time()
  }
  scheduler.next_id = scheduler.next_id + 1
  return id
end

function scheduler.update()
  -- Clean up any previously marked coroutines
  for id in pairs(scheduler.to_remove) do
    scheduler.coroutines[id] = nil
  end
  scheduler.to_remove = {}

  -- Find next coroutine to process
  local found = false
  for id, co_data in pairs(scheduler.coroutines) do
    if not found and (scheduler.current_index == nil or id > scheduler.current_index) then
      found = true
      scheduler.current_index = id
      
      if coroutine.status(co_data.co) ~= 'dead' then
        local success, error = coroutine.resume(co_data.co)
        if not success then
          print("Coroutine error: " .. tostring(error))
          scheduler.to_remove[id] = true
        elseif coroutine.status(co_data.co) == 'dead' then
          scheduler.to_remove[id] = true
        end
      else
        scheduler.to_remove[id] = true
      end
      
      break  -- Only process one coroutine per update
    end
  end
  
  -- Reset current_index if we've processed all coroutines
  if not found then
    scheduler.current_index = nil
  end
end

function scheduler.debounce(func)
  local current_co = nil
  
  return function(...)
    -- If there's an existing coroutine, mark it for removal
    if current_co then
      scheduler.to_remove[current_co] = true
    end
    
    local args = {...}
    local co = coroutine.create(function()
      func(table.unpack(args))
    end)
    
    current_co = scheduler.start(co)
  end
end

return scheduler