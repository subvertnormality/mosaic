local stock_parameter = {}

local function resolve_slot(assignments, index, type, read_step_lock, read_assigned, read_fallback, context, current_step)
  if index then
    local param = assignments[index]
    local step_lock = read_step_lock(index, context, current_step)
    if step_lock == param.off_value then
      return nil
    end
    if step_lock then
      return step_lock
    end
    return read_assigned(param.param_id) or nil
  end

  local value, read_default, default_context = read_fallback(type, context)
  if value and value ~= read_default(default_context) then
    return value
  end

  -- Also report the stock value that was read, so a caller needing it need not reread it.
  return nil, value
end

function stock_parameter.resolve(assignments, type, read_step_lock, read_assigned, read_fallback, context, current_step)
  local index
  for i = 1, 10 do
    local param = assignments[i]
    if param and param.id == type then
      index = i
      break
    end
  end
  return (resolve_slot(assignments, index, type, read_step_lock, read_assigned, read_fallback, context, current_step))
end

-- Slot assignments change when the user assigns a parameter, not between steps,
-- so keep the map a scan produced and reuse it while every slot's id is the
-- same. An unassigned slot is remembered as false, which no id can equal.
local scanned = setmetatable({}, {__mode = "k"})

local function first_slots(assignments)
  local cached = scanned[assignments]
  if cached then
    local ids = cached.ids
    local unchanged = true
    for i = 1, 10 do
      local param = assignments[i]
      if (param and param.id or false) ~= ids[i] then
        unchanged = false
        break
      end
    end
    if unchanged then return cached.first end
  end
  local ids, first = {}, {}
  for i = 1, 10 do
    local param = assignments[i]
    local id = param and param.id
    ids[i] = id or false
    if id ~= nil and first[id] == nil then
      first[id] = i
    end
  end
  scanned[assignments] = {ids = ids, first = first}
  return first
end

-- Resolve several kinds for one step from a single scan of the assignment slots.
-- Each kind keeps its first matching slot, exactly as resolve does.
function stock_parameter.resolver(assignments, read_step_lock, read_assigned, read_fallback, context, current_step)
  local first = first_slots(assignments)
  return function(type)
    return resolve_slot(assignments, first[type], type, read_step_lock, read_assigned, read_fallback, context, current_step)
  end
end

-- A resolver that answers each kind from its first resolution, for a caller
-- that resolves one step after another. reset starts a step; its answers are
-- then remembered until the next reset, so a kind resolved early is not read
-- again when the caller asks for it. It allocates only when first made, so a
-- clock resolving every channel on every step leaves nothing to collect.
function stock_parameter.new_remembering_resolver(read_step_lock, read_assigned, read_fallback)
  local resolver = {}
  local resolved, values, reads = {}, {}, {}
  local generation = 0
  local assignments, first, context, current_step

  function resolver.reset(step_assignments, step_context, step)
    assignments, first, context, current_step = step_assignments, first_slots(step_assignments), step_context, step
    generation = generation + 1
  end

  function resolver.stock(type)
    if resolved[type] ~= generation then
      values[type], reads[type] = resolve_slot(assignments, first[type], type, read_step_lock, read_assigned,
        read_fallback, context, current_step)
      resolved[type] = generation
    end
    return values[type], reads[type]
  end

  return resolver
end

return stock_parameter
