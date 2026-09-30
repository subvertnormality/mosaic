-- Descriptor adapters over the existing UI owners (docs/ui-reimplementation, UI02).
--
-- An adapter wraps an owner's existing getters, edit/action closures, validators
-- and commit boundary. It never reproduces their algorithms. This module holds
-- the protocol shared by every provider: route ownership, generation checks,
-- descriptor normalisation, descriptor_filter views and outcomes. Providers live
-- in lib/ui_adapters/<name>.lua and are registered with ui_adapters.register.

local spec = include("mosaic/lib/ui_spec_data")

local ui_adapters = {spec = spec}

local KINDS = {value = true, readonly = true, action = true, inspection = true, unavailable = true}
local REQUIRES = {held = true, draft = true, pending_confirmation = true}

local registry = {}

-- Outcome ----------------------------------------------------------------------

-- Every protocol call returns one outcome table. Owner return values are kept in
-- `result`; the wrapper only adds read-only identity metadata.
function ui_adapters.outcome(fields)
  local outcome = {ok = true, code = "ok"}
  for key, value in pairs(fields or {}) do outcome[key] = value end
  return outcome
end

function ui_adapters.fail(code, fields)
  local outcome = ui_adapters.outcome(fields)
  outcome.ok, outcome.code = false, code
  outcome.status = outcome.status or code
  return outcome
end

-- Route ownership ----------------------------------------------------------------

local function route_entry(provider)
  local entry = spec.source_route_map[provider]
  if type(entry) ~= "table" then return nil end
  return entry
end

function ui_adapters.is_filter_provider(provider)
  local entry = route_entry(provider)
  return entry ~= nil and entry.route_kind == "descriptor_filter"
end

-- The owner states a provider may describe. For translated providers these are
-- the keys of source_route_map[provider]; for descriptor_filter providers they
-- are view keys; otherwise the existing_route of every screen it provides.
function ui_adapters.owned_routes(provider)
  local routes = {}
  local entry = route_entry(provider)
  if entry and entry.route_kind == "descriptor_filter" then
    for view in pairs(entry.views) do routes[view] = true end
  elseif entry then
    for route in pairs(entry) do routes[route] = true end
  else
    for _, screen in pairs(spec.screens) do
      if screen.provider == provider and screen.existing_route then routes[screen.existing_route] = true end
    end
  end
  return routes
end

local variants = {}
for _, screen_id in ipairs(spec.visual_variants) do variants[screen_id] = true end

function ui_adapters.owns_route(provider, route)
  if type(route) ~= "string" then return false end
  local screen_id = route:match("^snapshot:(.+)$")
  if screen_id then
    local screen = spec.screens[screen_id]
    return variants[screen_id] == true and screen ~= nil and screen.provider == provider
  end
  return ui_adapters.owned_routes(provider)[route] == true
end

-- New visual screen id for an old owner route (Merge/Harmony translation).
function ui_adapters.translate_route(provider, route)
  local entry = route_entry(provider)
  if not entry or entry.route_kind == "descriptor_filter" then return route end
  return entry[route]
end

-- Descriptors ------------------------------------------------------------------

-- Validates and completes one owner descriptor. Owner-local closures (read,
-- edit, invoke, before) stay on the descriptor and are never serialised.
function ui_adapters.descriptor(d)
  assert(type(d) == "table", "descriptor must be a table")
  assert(type(d.id) == "string" and d.id ~= "", "descriptor needs a stable id")
  assert(type(d.label) == "string", "descriptor " .. d.id .. " needs a label")
  assert(KINDS[d.kind], "descriptor " .. d.id .. " has unknown kind " .. tostring(d.kind))
  if d.short_label == nil then d.short_label = d.label end
  if d.visible == nil then d.visible = true end
  if d.enabled == nil then d.enabled = true end
  d.domain = d.domain or {}
  if d.value ~= nil then d.value = tostring(d.value) end
  return d
end

local function check_unique(descriptors)
  local seen = {}
  for _, d in ipairs(descriptors) do
    assert(not seen[d.id], "duplicate descriptor id " .. d.id)
    seen[d.id] = true
  end
end

local function apply_view(descriptors, view)
  if not view or view.filter == nil or view.filter == "all" then return descriptors end
  local result = {}
  for _, d in ipairs(descriptors) do
    local keep
    if view.filter == "selected" then
      keep = d.selected == true
    elseif view.filter == "assigned_parameter_id_prefix" then
      local assigned = d.domain.assigned_parameter_id
      keep = type(assigned) == "string" and assigned:sub(1, #view.value) == view.value
    else
      error("unknown descriptor filter " .. tostring(view.filter))
    end
    if keep then result[#result + 1] = d end
  end
  return result
end

-- Adapter ----------------------------------------------------------------------

local Adapter = {}
Adapter.__index = Adapter

-- impl fields (all optional except describe):
--   describe(route, target) -> descriptors | nil, code
--   generation(target) -> comparable owner generation
--   target_valid(target) -> boolean
--   has_draft(target), pending_confirmation(target) -> boolean
--   apply(token, target, revision), cancel(token), snapshot(target, event_id) -> outcome
--   revisions(target) -> {active=, queued=, draft=}
function ui_adapters.new(provider, impl)
  assert(type(impl.describe) == "function", provider .. " adapter needs describe")
  return setmetatable({provider = provider, impl = impl}, Adapter)
end

function Adapter:generation(target)
  return self.impl.generation and self.impl.generation(target) or 0
end

function Adapter:identity(target, source_route)
  local fields = {provider = self.provider, target = target, owner_generation = self:generation(target), source_route = source_route}
  if self.impl.revisions then fields.revision = self.impl.revisions(target) end
  return fields
end

function Adapter:validate(route, target, generation)
  if not ui_adapters.owns_route(self.provider, route) then
    return ui_adapters.fail("foreign_route", self:identity(target, route))
  end
  if self.impl.target_valid and not self.impl.target_valid(target) then
    return ui_adapters.fail("stale_target", self:identity(target, route))
  end
  if generation ~= nil and generation ~= self:generation(target) then
    return ui_adapters.fail("stale_generation", self:identity(target, route))
  end
end

local function requirement_met(impl, requires, target)
  if requires == nil then return true end
  assert(REQUIRES[requires], "unknown view requirement " .. tostring(requires))
  if requires == "held" then return type(target) == "table" and type(target.held) == "table" and #target.held > 0 end
  if requires == "draft" then return impl.has_draft ~= nil and impl.has_draft(target) == true end
  return impl.pending_confirmation ~= nil and impl.pending_confirmation(target) == true
end

-- describe(screen_id, source_route, target, generation) -> outcome{descriptors}
function Adapter:describe(screen_id, source_route, target, generation)
  local invalid = self:validate(source_route, target, generation)
  if invalid then return invalid end
  -- A descriptor_filter view key is never passed to the owner: it describes its
  -- single descriptor set (route nil) and the view filters the result.
  local view
  local owner_route = source_route
  if ui_adapters.is_filter_provider(self.provider) and not source_route:match("^snapshot:") then
    view = spec.source_route_map[self.provider].views[source_route]
    if not requirement_met(self.impl, view.requires, target) then
      return ui_adapters.fail("requires_" .. view.requires, self:identity(target, source_route))
    end
    owner_route = nil
  end
  local descriptors, code = self.impl.describe(owner_route, target)
  if descriptors == nil then return ui_adapters.fail(code or "describe_failed", self:identity(target, source_route)) end
  for index, d in ipairs(descriptors) do descriptors[index] = ui_adapters.descriptor(d) end
  check_unique(descriptors)
  local outcome = ui_adapters.outcome(self:identity(target, source_route))
  outcome.screen = screen_id
  outcome.descriptors = apply_view(descriptors, view)
  return outcome
end

function Adapter:find(field_id, target)
  local route = target and target.source_route
  local described = self:describe(target and target.screen, route, target)
  if not described.ok then return nil, described end
  for _, d in ipairs(described.descriptors) do
    if d.id == field_id then return d, described end
  end
  return nil, ui_adapters.fail("unknown_field", self:identity(target, route))
end

local function run(self, field_id, target, generation, kind_ok, call)
  local route = target and target.source_route
  local invalid = self:validate(route, target, generation)
  if invalid then return invalid end
  local d, failure = self:find(field_id, target)
  if not d then return failure end
  local identity = self:identity(target, route)
  identity.field = field_id
  if not d.visible or not d.enabled then return ui_adapters.fail("disabled", identity) end
  if not kind_ok(d) then return ui_adapters.fail("wrong_kind", identity) end
  local result = call(d)
  local outcome
  if type(result) == "table" and result.ok ~= nil and result.code ~= nil then
    outcome = result
    for key, value in pairs(identity) do if outcome[key] == nil then outcome[key] = value end end
  else
    outcome = ui_adapters.outcome(identity)
    outcome.result = result
  end
  outcome.revision = self.impl.revisions and self.impl.revisions(target) or outcome.revision
  return outcome
end

-- edit(field_id, delta, target, generation, modifiers). Zero delta is ignored.
function Adapter:edit(field_id, delta, target, generation, modifiers)
  if delta == 0 then return ui_adapters.fail("zero_delta", self:identity(target, target and target.source_route)) end
  return run(self, field_id, target, generation,
    function(d) return (d.kind == "value" or d.kind == "inspection") and type(d.edit) == "function" end,
    function(d) return d.edit(delta, modifiers or {}) end)
end

function Adapter:invoke(field_id, target, generation, modifiers)
  return run(self, field_id, target, generation,
    function(d) return d.kind == "action" and type(d.invoke) == "function" end,
    function(d)
      if d.before then d.before(modifiers or {}) end
      return d.invoke(modifiers or {})
    end)
end

local function forward(self, name, target, ...)
  local handler = self.impl[name]
  if not handler then return ui_adapters.fail("unsupported", self:identity(target)) end
  local result = handler(...)
  if type(result) == "table" and result.ok ~= nil and result.code ~= nil then return result end
  local outcome = ui_adapters.outcome(self:identity(target))
  outcome.result = result
  return outcome
end

function Adapter:apply(owner_token, target, draft_revision)
  return forward(self, "apply", target, owner_token, target, draft_revision)
end

function Adapter:cancel(owner_token)
  return forward(self, "cancel", nil, owner_token)
end

function Adapter:snapshot(target, event_id)
  return forward(self, "snapshot", target, target, event_id)
end

-- Registry ---------------------------------------------------------------------

function ui_adapters.register(provider, adapter)
  assert(getmetatable(adapter) == Adapter, "register an adapter built by ui_adapters.new")
  registry[provider] = adapter
  return adapter
end

function ui_adapters.get(provider)
  return registry[provider]
end

function ui_adapters.reset()
  registry = {}
end

function ui_adapters.providers()
  local names = {}
  for name in pairs(registry) do names[#names + 1] = name end
  table.sort(names)
  return names
end

return ui_adapters
