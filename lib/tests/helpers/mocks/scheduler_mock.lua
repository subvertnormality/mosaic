local scheduler = {}

-- Track active coroutines
scheduler.coroutines = {}

function scheduler.start(co)
  if type(co) == "thread" then
    table.insert(scheduler.coroutines, co)
  end
end

-- Execute coroutine until completion
function scheduler.update()
  for i, co in ipairs(scheduler.coroutines) do
    while coroutine.status(co) ~= 'dead' do
      local success = coroutine.resume(co)
      if not success then break end
    end
  end
  -- Clear completed coroutines
  scheduler.coroutines = {}
end

function scheduler.debounce(func)
  return function(...)
    local args = {...}
    local co = coroutine.create(function()
      func(table.unpack(args))
    end)
    
    -- Start and immediately execute the coroutine
    scheduler.start(co)
    scheduler.update()
  end
end

return scheduler