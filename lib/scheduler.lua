local scheduler = {
  coroutines = {},
  active_count = 0,
  next_id = 1
}

-- Pre-allocate a reusable removal set
local INITIAL_REMOVAL_SET_SIZE = 32
local removal_set = {}
for i = 1, INITIAL_REMOVAL_SET_SIZE do
  removal_set[i] = false
end

function scheduler.start(co)
  if type(co) ~= "thread" then
    return nil
  end

  local id = scheduler.next_id
  scheduler.coroutines[id] = {
    co = co,
    created_at = os.time(),
    active = true
  }
  scheduler.active_count = scheduler.active_count + 1
  scheduler.next_id = id + 1
  return id
end

-- Reuse this table to avoid allocations
local sorted_ids = {}
-- Keep the current map when no entry needs reclaiming.
local cleanup_pending = false

local function snapshot_active_ids()
  -- Get sorted list of active coroutine IDs
  local idx = 1
  for id, co_data in pairs(scheduler.coroutines) do
    if co_data.active then
      sorted_ids[idx] = id
      idx = idx + 1
    end
  end
  -- Clear any remaining old entries
  for i = idx, #sorted_ids do
    sorted_ids[i] = nil
  end
  table.sort(sorted_ids)

end

local function retire_snapshot_ids(removal_count)
  if removal_count > 0 then cleanup_pending = true end
  -- Process removals
  for i = 1, removal_count do
    local id = removal_set[i]
    scheduler.coroutines[id].active = false
    removal_set[i] = false  -- Reset for reuse
  end
  scheduler.active_count = scheduler.active_count - removal_count

  -- Periodic cleanup of inactive coroutines
  if cleanup_pending and scheduler.active_count < scheduler.next_id / 2 then
    local new_coroutines = {}
    for id, co_data in pairs(scheduler.coroutines) do
      if co_data.active then
        new_coroutines[id] = co_data
      end
    end
    scheduler.coroutines = new_coroutines
    cleanup_pending = false
  end
end

function scheduler.update()
  snapshot_active_ids()
  -- Membership is frozen for this pass: cancellation during a callback does
  -- not remove a later snapshot member. Preserve that existing policy here.
  -- Process coroutines in order
  local removal_count = 0
  for i, id in ipairs(sorted_ids) do
    local co_data = scheduler.coroutines[id]

    if coroutine.status(co_data.co) ~= 'dead' then
      local success, error = coroutine.resume(co_data.co)
      if not success then
        print("Coroutine error: " .. tostring(error))
        removal_count = removal_count + 1
        removal_set[removal_count] = id
      elseif coroutine.status(co_data.co) == 'dead' then
        removal_count = removal_count + 1
        removal_set[removal_count] = id
      end
    else
      removal_count = removal_count + 1
      removal_set[removal_count] = id
    end
  end

  retire_snapshot_ids(removal_count)
end

function scheduler.debounce(func)
  local current_co = nil

  return function(...)
    -- Deactivate existing coroutine if it exists
    if current_co and scheduler.coroutines[current_co] and scheduler.coroutines[current_co].active then
      cleanup_pending = true
      scheduler.coroutines[current_co].active = false
      scheduler.active_count = scheduler.active_count - 1
    end

    local args = {...}
    local co = coroutine.create(function()
      func(table.unpack(args))
    end)

    current_co = scheduler.start(co)
  end
end

return scheduler
