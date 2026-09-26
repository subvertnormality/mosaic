-- Shared UI02 adapter over one channel_feature_editor instance (Merge Shape or
-- Harmony). lib/ui_adapters/merge.lua and harmony.lua are thin factories over
-- this module; see those files for the owner they expect.
--
-- The editor keeps every closure, validator, delta policy and commit boundary:
--   * a value/inspection descriptor edits by selecting its row and calling the
--     editor's own enc(3, delta) (the path ui.enc reaches today);
--   * an action descriptor selects its row and calls key(3), so `before`, the
--     inline `invoke`, open(route) with its return frame, and the HARMONY_LINK
--     reload + select_harmony_page run exactly as today;
--   * apply wraps editor:apply(); cancel wraps the K2 path, editor:key(2).
-- The adapter describes only the editor's live route (editor.screen). The
-- source_route a caller passes is an OLD owner route (source_route_map keys);
-- a new visual screen id is never written into editor.screen.
-- `snapshot:<screen>` routes (spec.visual_variants) read an immutable snapshot
-- taken by impl.snapshot and are never passed to get_fields.

local feature_editor = include("mosaic/lib/pages/channel_edit_page/channel_feature_editor")
local optional_transaction = include("mosaic/lib/optional_config_transaction")

local shared = {}

local function copy(value, seen)
  if type(value) ~= "table" then return value end
  seen = seen or {}
  if seen[value] then return seen[value] end
  local result = {}; seen[value] = result
  for key, item in pairs(value) do result[copy(key, seen)] = copy(item, seen) end
  return result
end

-- Read-only proxy: reads, # and pairs work; any write raises.
local function freeze(value, seen)
  if type(value) ~= "table" then return value end
  seen = seen or {}
  if seen[value] then return seen[value] end
  local proxy = {}
  seen[value] = proxy
  local inner = {}
  for key, item in pairs(value) do inner[key] = freeze(item, seen) end
  return setmetatable(proxy, {
    __index = inner,
    __newindex = function() error("immutable owner snapshot", 2) end,
    __len = function() return #inner end,
    __pairs = function() return next, inner, nil end,
    __metatable = "frozen"
  })
end
shared.freeze = freeze

function shared.format(value)
  return feature_editor.field_value({value = value})
end
local format = shared.format

local function domain_of(field)
  local domain = {delta_policy = "direction", step = 1}
  if field.boolean then
    domain.boolean, domain.enum = true, {false, true}
  elseif field.values then
    domain.enum = copy(field.values)
  else
    domain.min, domain.max = field.min, field.max
  end
  return domain
end

function shared.new(ui_adapters, provider, editor, options)
  assert(type(editor) == "table" and editor.get_fields, provider .. " adapter needs its feature editor owner")
  local impl = {}

  local function live_route() return editor.screen end
  local function translate(route) return ui_adapters.translate_route(provider, route) end

  local function is_snapshot_route(route) return type(route) == "string" and route:match("^snapshot:") ~= nil end

  local function target_valid(target)
    if type(target) ~= "table" or editor.draft == nil then return false end
    if target.channel_number ~= nil and target.channel_number ~= editor.channel_number then return false end
    local route = target.source_route
    if type(route) == "string" and not is_snapshot_route(route) and route ~= live_route() then return false end
    return true
  end

  local function result_of(extra)
    local result = {route = live_route(), screen = translate(live_route()), dirty = editor.dirty,
      status = editor.status, owner_generation = editor.generation}
    for key, value in pairs(extra or {}) do result[key] = value end
    return result
  end

  -- Descriptors for the live route, built from the fields get_fields returns.
  local function live_descriptors()
    local descriptors = {}
    for index, field in ipairs(editor:get_fields()) do
      assert(type(field.id) == "string", provider .. " field '" .. tostring(field.label) .. "' on " ..
        tostring(editor.screen) .. " has no stable id")
      local d = {id = field.id, label = field.label, repeat_key = field.repeat_key, selected = index == editor.selected}
      if field.action then
        d.kind, d.value = "action", ">"
        local edge = field.route == "HARMONY_LINK" and "cross_owner_link" or (field.route and "route" or "inline")
        d.domain = {edge = edge, route = field.route,
          destination = edge == "route" and translate(field.route) or (edge == "cross_owner_link" and "H01" or nil),
          target_owner = edge == "cross_owner_link" and "harmony" or nil}
        d.invoke = function()
          local was_dirty = editor.dirty
          editor.selected = index
          local handled = editor:key(3)
          if edge == "cross_owner_link" then
            -- owner.cancel_unapplied (reload), return.invalidate, owner.enter_root:
            -- the owner already did all three; no return frame to Merge exists.
            return result_of({handled = handled, edge = edge, target_owner = "harmony",
              cancel_unapplied = was_dirty, return_frame = false})
          end
          return result_of({handled = handled, edge = edge})
        end
      elseif field.readonly then
        d.kind, d.value, d.domain = "readonly", feature_editor.field_value(field), {}
      else
        d.kind = field.kind or "value"
        d.value = feature_editor.field_value(field)
        d.domain = domain_of(field)
        d.edit = function(delta)
          editor.selected = index
          editor:enc(3, delta)
          return result_of()
        end
      end
      descriptors[#descriptors + 1] = d
    end
    return descriptors
  end

  -- Snapshot -------------------------------------------------------------------

  local function take_snapshot(event_id)
    local fields, order = {}, {}
    for _, d in ipairs(live_descriptors()) do
      fields[d.id] = {label = d.label, value = d.value, kind = d.kind}
      order[#order + 1] = d.id
    end
    local value = {provider = provider, event_id = event_id, owner_generation = editor.generation,
      channel_number = editor.channel_number, route = live_route(), screen = translate(live_route()),
      status = editor.status, dirty = editor.dirty, gesture = editor.gesture, selected_step = editor.selected_step,
      draft = copy(editor.draft), fields = fields, order = order}
    if options.capture then options.capture(editor, value) end
    return freeze(value)
  end

  local function snapshot_descriptors(screen_id, snap)
    local rows = options.variants[screen_id]
    if not rows then return nil, "no_variant" end
    local descriptors = {}
    for _, row in ipairs(rows) do
      local value = row.read(snap)
      descriptors[#descriptors + 1] = {id = row.id, label = row.label,
        kind = value == nil and "unavailable" or "readonly", value = value,
        domain = {snapshot = true, event_id = snap.event_id}}
    end
    return descriptors
  end

  -- Protocol -------------------------------------------------------------------

  impl.generation = function() return editor.generation end
  impl.target_valid = target_valid
  impl.has_draft = function() return editor.dirty == true end
  impl.pending_confirmation = function()
    return options.confirmation_routes ~= nil and options.confirmation_routes[live_route()] == true
  end
  impl.revisions = function() return {draft = editor.generation, dirty = editor.dirty} end

  impl.describe = function(route, target)
    if editor.draft == nil then return nil, "not_entered" end
    local variant = type(route) == "string" and route:match("^snapshot:(.+)$")
    if variant then
      local snap = type(target) == "table" and target.snapshot
      if snap and (getmetatable(snap) ~= "frozen" or snap.provider ~= provider) then return nil, "foreign_snapshot" end
      return snapshot_descriptors(variant, snap or take_snapshot(target and target.event_id))
    end
    if route ~= live_route() then return nil, "route_not_live" end
    return live_descriptors()
  end

  impl.snapshot = function(target, event_id)
    if editor.draft == nil then return ui_adapters.fail("not_entered", {provider = provider}) end
    return ui_adapters.outcome({provider = provider, target = target, owner_generation = editor.generation,
      snapshot = take_snapshot(event_id)})
  end

  local function token_stale(token)
    return type(token) == "table" and ((token.generation ~= nil and token.generation ~= editor.generation) or
      (token.channel_number ~= nil and token.channel_number ~= editor.channel_number))
  end

  impl.apply = function(token, target, draft_revision)
    local identity = {provider = provider, target = target, owner_generation = editor.generation,
      commit_boundary = options.commit_boundary}
    if editor.draft == nil then return ui_adapters.fail("not_entered", identity) end
    if token_stale(token) then return ui_adapters.fail("stale_generation", identity) end
    if draft_revision ~= nil and draft_revision ~= editor.generation then return ui_adapters.fail("stale_revision", identity) end
    if target ~= nil and not target_valid(target) then return ui_adapters.fail("stale_target", identity) end
    local ok = editor:apply()
    local status = editor.status
    local code = not ok and "invalid" or status == "UNCHANGED" and "unchanged" or status == "APPLIED" and "applied" or "queued"
    local outcome = ok and ui_adapters.outcome(identity) or ui_adapters.fail(code, identity)
    outcome.code, outcome.status, outcome.result = code, status, ok
    outcome.queued = code == "queued"
    outcome.owner_generation = editor.generation
    outcome.revision = impl.revisions()
    return outcome
  end

  impl.cancel = function(token)
    local identity = {provider = provider, owner_generation = editor.generation}
    if editor.draft == nil then return ui_adapters.fail("not_entered", identity) end
    if token_stale(token) then return ui_adapters.fail("stale_generation", identity) end
    local was_dirty = editor.dirty
    editor:key(2)
    local outcome = ui_adapters.outcome(identity)
    outcome.result = result_of({cancelled = was_dirty})
    outcome.owner_generation = editor.generation
    outcome.source_route = live_route()
    return outcome
  end

  local adapter = ui_adapters.new(provider, impl)
  -- Opaque owner token for apply/cancel: the identity captured when a draft or
  -- confirmation was shown. A later reload/apply makes it stale.
  function adapter.owner_token()
    return {provider = provider, generation = editor.generation, channel_number = editor.channel_number, route = live_route()}
  end
  function adapter.live_route() return live_route() end
  adapter.editor = editor
  return adapter
end

-- Snapshot row helpers ------------------------------------------------------------

function shared.field(route, id)
  return function(snap)
    if snap.route ~= route then return nil end
    local field = snap.fields[id]
    return field and field.value or nil
  end
end

function shared.equivalent(left, right) return optional_transaction.equivalent(left, right) end

shared.copy = copy
return shared
