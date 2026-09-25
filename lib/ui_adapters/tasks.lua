-- Tasks provider (docs/ui-reimplementation spec.json#/tasks, UI02).
--
-- New presentation code: there is no legacy owner. Rows, their order, labels
-- and destinations come only from spec.tasks. describe(route) returns one
-- action descriptor per visible row of that navigator; invoke returns an
-- outcome naming the destination and never navigates (the router does).
--
-- owners (all optional):
--   state(target) -> table   values tested by a row's visible_when, e.g.
--                            function() return {algorithm = trigger_edit_page.get_algorithm()} end
--                            Without it target.state is used; a row with
--                            visible_when and no state is hidden.
--
-- target fields read: context (a spec context name: Channel, Scale, Trig,
-- Note, Velocity, Song). When absent, a navigator whose screen declares a
-- single context uses that context.
return function(ui_adapters, owners)
  owners = owners or {}
  local spec = ui_adapters.spec
  local tasks = spec.tasks

  local function contains(list, value)
    for _, item in ipairs(list) do if item == value then return true end end
    return false
  end

  -- Rows for a route. Navigators are keys of spec.tasks.rows. A tasks screen
  -- without its own rows (M01, the rework route under N01) lists the rows of
  -- its parent navigator named by its own field ids, in its own field order.
  local function rows_for(route)
    if tasks.rows[route] then return tasks.rows[route] end
    local screen = spec.screens[route]
    local parent_rows = screen and screen.parent and tasks.rows[screen.parent]
    if not parent_rows then return nil end
    local by_id = {}
    for _, row in ipairs(parent_rows) do by_id[row.id] = row end
    local rows = {}
    for _, field in ipairs(screen.fields) do
      local row = by_id[type(field) == "table" and field.id or field]
      if not row then return nil end
      rows[#rows + 1] = row
    end
    return rows
  end

  local function context_of(route, target)
    if type(target) == "table" and target.context ~= nil then return target.context end
    local screen = spec.screens[route]
    local declared = screen and screen.context
    if type(declared) == "string" then return declared end
    if type(declared) == "table" and #declared == 1 then return declared[1] end
    return nil
  end

  local function state_of(target)
    if owners.state then return owners.state(target) end
    return type(target) == "table" and target.state or nil
  end

  local function visible(row, context, target)
    if row.contexts and not contains(row.contexts, context) then return false end
    if row.visible_when then
      local state = state_of(target)
      if type(state) ~= "table" then return false end
      for key, value in pairs(row.visible_when) do
        if state[key] ~= value then return false end
      end
    end
    return true
  end

  -- The screen a row opens.
  local function destination(row, context)
    if type(row.screen) == "table" then return row.screen[context] end
    return row.screen
  end

  local function descriptor(row, context)
    local dest = destination(row, context)
    if dest == nil then return nil end
    return {
      id = row.id,
      label = row.label,
      kind = "action",
      value = dest,
      domain = {destination = dest, context = context},
      invoke = function()
        return ui_adapters.outcome({code = "open_screen", destination = dest, context = context})
      end
    }
  end

  local impl = {}

  function impl.describe(route, target)
    local rows = rows_for(route)
    if not rows then return nil, "no_task_rows" end
    local context = context_of(route, target)
    local needs_context = false
    for _, row in ipairs(rows) do
      if type(row.screen) == "table" or row.contexts then needs_context = true end
    end
    if needs_context and context == nil then return nil, "missing_context" end
    local descriptors = {}
    for _, row in ipairs(rows) do
      if visible(row, context, target) then
        local d = descriptor(row, context)
        if d then descriptors[#descriptors + 1] = d end
      end
    end
    return descriptors
  end

  return ui_adapters.new("tasks", impl)
end
