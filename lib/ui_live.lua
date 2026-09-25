-- Live norns UI (docs/ui-reimplementation, UI03-UI06).
--
-- Grid first: grid callbacks run once through their original path and then
-- notify this module (m_grid emits hold.* and grid.outcome). Norns keys and
-- encoders become router events. The router (lib/ui_router.lua) selects one
-- rule per event; its presentation effects move the screen, and every adapter
-- command below reaches the original owner exactly once, either through a
-- descriptor closure (lib/ui_adapters) or through the owner's own key handler
-- with its legacy workspace positioned to match the screen. The screen is a
-- ViewModel drawn by lib/ui_render.lua; nothing here evaluates music.

local spec = include("mosaic/lib/ui_spec_data")
local ui_adapters = include("mosaic/lib/ui_adapters")
local ui_router = include("mosaic/lib/ui_router")
local ui_render = include("mosaic/lib/ui_render")
local ui_motion = include("mosaic/lib/ui_motion")

local ui_live = {}

local router
local focus = {}          -- screen id -> focused field id
local installed = false

local CONTEXT_OF_PAGE = {}
local PAGE_OF_CONTEXT = {}

local function page_numbers()
  local p = pages.pages
  CONTEXT_OF_PAGE = {
    [p.channel_edit_page] = "Channel", [p.scale_edit_page] = "Scale", [p.trigger_edit_page] = "Trig",
    [p.note_edit_page] = "Note", [p.velocity_edit_page] = "Velocity", [p.song_edit_page] = "Song"
  }
  for page, context in pairs(CONTEXT_OF_PAGE) do PAGE_OF_CONTEXT[context] = page end
end

-- Legacy workspaces ---------------------------------------------------------------
-- Grid gestures and owner key handlers read the old per-page workspace (for
-- example a held step + E3 edits masks or trig locks by Channel sub-page), so
-- the workspace always matches the screen the player sees.

local CHANNEL_WORKSPACE = {
  C01 = 1, C12 = 1, F05 = 1, F06 = 1,
  C02 = 2, C07 = 2, C10 = 2, C13 = 2, F08 = 2,
  C03 = 3,
  C04 = 4, F01 = 4, F02 = 4,
  C05 = 5, C11 = 5,
  C06 = 6, C08 = 6, C09 = 6, S03 = 6, S04 = 6,
}
local SCALE_WORKSPACE = {S01 = 1, S04 = 1, S05 = 1, S02 = 2, S03 = 3, P05 = 3}
local SONG_WORKSPACE = {A01 = 1, A02 = 2, A03 = 3, P05 = 3}
local TRIG_WORKSPACE = {P02 = 2}

local function screen_entry(id) return spec.screens[id or router.state.screen] end

local function feature_editor(provider)
  local owners = channel_edit_page_ui.adapter_owners()
  return owners.feature_editors[provider]
end

local function sync_workspace()
  local s = router.state
  local screen = screen_entry()
  if s.context == "Channel" then
    local owners = channel_edit_page_ui.adapter_owners()
    local current = owners.channel_pages:get_selected_page()
    local wanted = CHANNEL_WORKSPACE[s.screen]
    if screen.provider == "merge" then wanted = 7 elseif screen.provider == "harmony" then wanted = 8 end
    if s.screen == "M10" then wanted = 8 end
    if wanted and wanted ~= current then channel_edit_page_ui.select_channel_page_by_index(wanted) end
    -- C07 is the Trig Locks assignment sub-page; any other Trig Locks screen is not.
    if wanted == 2 then
      local parameters = owners.parameters
      local page = parameters.adapter_controls and parameters.adapter_controls().trig_lock_page
      local open = page and page:is_sub_page_enabled()
      if (s.screen == "C07") ~= (open == true) then parameters.toggle_assignment_subpage() end
    end
  elseif s.context == "Scale" then
    local wanted = SCALE_WORKSPACE[s.screen]
    local owners = scale_edit_page_ui.adapter_owners()
    if wanted and owners.pages:get_selected_page() ~= wanted then owners.pages:select_page(wanted) end
  elseif s.context == "Song" then
    local wanted = SONG_WORKSPACE[s.screen]
    local owners = song_edit_page_ui.adapter_owners()
    if wanted and owners.pages:get_selected_page() ~= wanted then owners.pages:select_page(wanted) end
  elseif s.context == "Trig" then
    local wanted = TRIG_WORKSPACE[s.screen] or 1
    local owners = trigger_edit_page_ui.adapter_owners()
    if owners.pages:get_selected_page() ~= wanted then owners.pages:select_page(wanted) end
  end
end

-- Target ---------------------------------------------------------------------------

local function held_steps()
  local steps = {}
  local keys = m_grid.get_pressed_keys and m_grid.get_pressed_keys() or {}
  for _, key in ipairs(keys) do
    if key[2] >= 4 and key[2] <= 7 then steps[#steps + 1] = fn.calc_grid_count(key[1], key[2]) end
  end
  return steps
end

-- The route an adapter describes for the current screen.
local variant = {}
for _, id in ipairs(spec.visual_variants) do variant[id] = true end

local function source_route(screen_id)
  local screen = spec.screens[screen_id]
  if variant[screen_id] and screen.provider ~= "read_only" then return "snapshot:" .. screen_id end
  return screen.existing_route
end

local function capture_target()
  local s = router.state
  local selected = program.get()
  return {
    channel = selected.selected_channel, song_slot = selected.selected_song_pattern,
    held = held_steps(), step_set = s.target.step_set, context = s.context,
    screen = s.screen, source_route = source_route(s.screen)
  }
end

-- Descriptors ------------------------------------------------------------------------

local function describe(screen_id)
  screen_id = screen_id or router.state.screen
  local screen = spec.screens[screen_id]
  local adapter = ui_adapters.get(screen.provider)
  if not adapter then return {}, "no_adapter" end
  local target = capture_target()
  target.screen, target.source_route = screen_id, source_route(screen_id)
  local outcome = adapter:describe(screen_id, target.source_route, target)
  if not outcome.ok then return {}, outcome.code, target end
  local visible = {}
  for _, d in ipairs(outcome.descriptors) do
    if d.visible then visible[#visible + 1] = d end
  end
  return visible, nil, target
end

local function focused(descriptors, screen_id)
  screen_id = screen_id or router.state.screen
  if #descriptors == 0 then return nil, 0 end
  -- The assignment picker's owner moves its own list cursor with E3.
  if spec.screens[screen_id].profile == "assignment" then
    for index, d in ipairs(descriptors) do
      if d.kind == "value" then focus[screen_id] = d.id; return d, index end
    end
  end
  local id = focus[screen_id]
  for index, d in ipairs(descriptors) do
    if d.id == id then return d, index end
  end
  -- A screen's first focus is the owner's own current selection (for example
  -- the Masks page starts on Note), so a player's first E3 edits what it did.
  if id == nil then
    for index, d in ipairs(descriptors) do
      if d.selected then focus[screen_id] = d.id; return d, index end
    end
  end
  -- A removed focus clamps to the first field; the pending delta is consumed.
  focus[screen_id] = descriptors[1].id
  return descriptors[1], 1
end

local function sync_field_state()
  local descriptors = describe()
  local d = focused(descriptors)
  router.state.field_id = d and d.id or nil
  local kind = d and d.kind or "unavailable"
  if screen_entry().profile == "read_only" and kind ~= "action" and kind ~= "inspection" then kind = "readonly" end
  router.state.field_kind = kind
end

-- Feedback ----------------------------------------------------------------------------

local FEEDBACK = {
  confirmation_owns_input = "K3 CONFIRM  K2 CANCEL",
  read_only = "READ ONLY",
  stale_target = "TARGET CHANGED",
  grid_offline = "GRID OFFLINE",
}

-- Feedback uses the existing tooltip, which the footer shows for its lifetime.
local function say(text)
  tooltip:show(text)
  ui_motion.nudge("status")
  fn.dirty_screen(true)
end

-- Owner key forwarding --------------------------------------------------------------------

local LEGACY_UI = {
  Channel = function() return channel_edit_page_ui end, Scale = function() return scale_edit_page_ui end,
  Trig = function() return trigger_edit_page_ui end, Song = function() return song_edit_page_ui end,
}

local function legacy_key(n)
  -- Effects earlier in the same rule (scope.restore_family) may have moved the
  -- screen; the owner reads the workspace that matches it.
  sync_workspace()
  local legacy = LEGACY_UI[router.state.context]
  if legacy then
    local page_ui = legacy()
    if page_ui.key then page_ui.key(n, 1) end
  end
end

local function legacy_enc(n, d)
  local legacy = LEGACY_UI[router.state.context]
  if legacy then legacy().enc(n, d) end
end

local current = {event = nil, delta = 0}

local function key_number(event) return tonumber(event:match("^K(%d)")) end

local function feature_adapter()
  local provider = screen_entry().provider
  if provider == "merge" or provider == "harmony" then return ui_adapters.get(provider), provider end
end

-- Adapter commands (router hooks) ------------------------------------------------------

local hooks = {}

hooks["owner.cancel_unapplied"] = function(_, event)
  local adapter, provider = feature_adapter()
  if adapter then
    local editor = feature_editor(provider)
    if event == "K2.down" then
      -- The feature's own K2: discard an unapplied draft, then back out of a
      -- child route (channel_feature_editor key(2)).
      editor:key(2)
    elseif editor and editor.dirty then
      editor:reload()
    end
  elseif save_confirm.has_pending() then
    save_confirm.cancel()
  end
end

-- E1 on a feature screen: a draft or child returns to the clean root; the
-- clean root moves on to Channel tasks (the router already chose which).
hooks["feature.return_then_tasks"] = function()
  local screen = spec.screens[router.state.screen]
  if screen.provider == "merge" or screen.provider == "harmony" then
    feature_editor(screen.provider):enter()
  end
end

hooks["family.edit"] = function(_, event)
  local family = router.state.family == "parameters" and "C02" or "C01"
  local descriptors, _, target = describe(family)
  local d = focused(descriptors, family)
  if d then ui_adapters.get(spec.screens[family].provider):edit(d.id, current.delta, target) end
  ui_motion.nudge("value")
end

hooks["family.clear"] = function() legacy_key(2) end
hooks["family.slide_if_parameters"] = function()
  if router.state.family == "parameters" then legacy_key(3) end
end
hooks["owner.clear_channel_step_locks"] = function() legacy_key(2) end
hooks["owner.clear_channel_step_masks_keep_defaults"] = function() legacy_key(2) end
hooks["owner.dispatch_key"] = function(_, event) legacy_key(key_number(event)) end

-- Screens whose owner keeps its own field selection (the page's selectors,
-- the trig-lock dial): E2 reaches the owner's handler, which moves, clamps and
-- skips exactly as before, and focus follows the owner's selection.
local OWNER_SELECTION = {masks = true, parameters = true, clock = true, device = true, scale = true,
  scale_clock = true, song = true, song_clock = true}

hooks["focus.move_clamped"] = function(_, event)
  local screen = screen_entry()
  if OWNER_SELECTION[screen.profile] and event:match("^E2") and LEGACY_UI[router.state.context] then
    sync_workspace()
    legacy_enc(2, current.delta)
    for _, d in ipairs(describe()) do
      if d.selected then focus[router.state.screen] = d.id; break end
    end
    ui_motion.nudge("focus")
    return
  end
  local descriptors = describe()
  if #descriptors == 0 then return end
  local _, index = focused(descriptors)
  local step = event:match("^E1") and (event == "E1+" and 1 or -1) or current.delta
  index = math.max(1, math.min(#descriptors, index + step))
  focus[router.state.screen] = descriptors[index].id
  ui_motion.nudge("focus")
end

hooks["owner.edit_existing"] = function()
  local descriptors, _, target = describe()
  local d = focused(descriptors)
  if not d then return end
  local outcome = ui_adapters.get(screen_entry().provider):edit(d.id, current.delta, target)
  if not outcome.ok and outcome.code ~= "zero_delta" then say(outcome.status or outcome.code) end
  ui_motion.nudge("value")
end
hooks["inspection.change_without_mutation"] = hooks["owner.edit_existing"]

hooks["feedback.read_only"] = function() say(FEEDBACK.read_only) end
hooks["feedback.confirmation_owns_input"] = function() say(FEEDBACK.confirmation_owns_input) end
hooks["feedback.stale_target"] = function() say(FEEDBACK.stale_target) end
hooks["feedback.grid_offline"] = function() say(FEEDBACK.grid_offline) end
-- Where each Norns settings row lives in the norns menu, opened by a short K1
-- (the script never opens the system menu itself). Compact to fit the footer.
local NATIVE_ROUTES = {
  X01 = "PARAMS>MOSAIC>PROJECT", X04 = "PARAMS>MOSAIC>SEQUENCER",
  X09 = "PARAMS>MOSAIC>PARAM LOCKS", X05 = "PARAMS>MOSAIC>QUANTISER",
  X06 = "PARAMS>MIDI MAPS", X07 = "PARAMS>MOSAIC CH n", X08 = "PARAMS>CLOCK + SYSTEM>MODS",
}

hooks["feedback.native_route"] = function()
  local descriptors = describe()
  local d = focused(descriptors)
  local destination = d and d.domain and d.domain.destination
  say(NATIVE_ROUTES[destination] or "PARAMS")
end

hooks["owner.invoke_selected"] = function()
  local descriptors, _, target = describe()
  local d = focused(descriptors)
  if not d then return end
  local outcome = ui_adapters.get(screen_entry().provider):invoke(d.id, target)
  if not outcome.ok then say(outcome.status or outcome.code) end
end

hooks["owner.validate_apply"] = function()
  local adapter = feature_adapter()
  if not adapter then return end
  local outcome = adapter:apply(adapter.owner_token and adapter.owner_token(), capture_target())
  if outcome.status then say(outcome.status) end
  ui_motion.nudge("apply")
end

hooks["doctor.dispatch"] = function(_, event)
  if event:match("^E") then
    legacy_enc(tonumber(event:sub(2, 2)), current.delta)
  else
    legacy_key(key_number(event))
  end
end

hooks["modal.confirm_once"] = function() ui_live.answer_modal(3) end
hooks["modal.cancel"] = function() ui_live.answer_modal(2) end

hooks["route.C07"] = function() end

-- Read-only feature screens (Merge result, Harmony result/failure) belong to
-- the feature editor's stack: K2 backs out through the editor, and leaving
-- for tasks returns the editor to its root, so neither is pulled back.
hooks["return.parent"] = function(_, event)
  local screen = spec.screens[current.before or ""]
  if event == "K2.down" and screen and screen.profile == "read_only"
    and (screen.provider == "merge" or screen.provider == "harmony") and not variant[current.before] then
    feature_editor(screen.provider):key(2)
  end
end
hooks["tasks.open"] = function()
  local screen = spec.screens[current.before or ""]
  if screen and (screen.provider == "merge" or screen.provider == "harmony") then
    feature_editor(screen.provider):enter()
  end
end

-- Modal questions stay with their owners; K3/K2 reach the owner once.
function ui_live.answer_modal(n)
  local id = router.state.screen
  if id == "H17" or id == "H19" then
    local editor = feature_editor("harmony")
    editor:key(n)
  elseif id == "S05" then
    legacy_key(n)
  elseif id == "R03" or id == "R10" or id == "R16" then
    legacy_key(n)
  end
end

-- State synchronisation --------------------------------------------------------------------

local MODAL_SCREENS = {H17 = true, H19 = true, S05 = true, R03 = true, R10 = true, R16 = true}

local function doctor_active()
  return trigger_edit_page and trigger_edit_page.get_algorithm and trigger_edit_page.get_algorithm() == 5
end

-- Owners stay authoritative for their own routes: the feature editors for
-- Merge/Harmony child screens and doctor_routes for the Rhythm Doctor.
local function reconcile_owner_routes()
  local s = router.state
  local screen = screen_entry()
  if s.context == "Channel" and (screen.provider == "merge" or screen.provider == "harmony") and not variant[s.screen] then
    local editor = feature_editor(screen.provider)
    local route = editor and editor:get_screen()
    local mapped = route and ui_adapters.translate_route(screen.provider, route)
    if mapped and spec.screens[mapped] and mapped ~= s.screen then s.screen = mapped end
    -- Back at the editor's clean root, frames pushed by its child routes and
    -- questions are spent: the next E1 leaves for tasks.
    if editor and #(editor.stack or {}) == 0 and (s.screen == "M02" or s.screen == "H01") then s.return_stack = {} end
  end
  if s.context == "Trig" and doctor_active() and (screen.provider == "doctor" or MODAL_SCREENS[s.screen]) then
    local adapter = ui_adapters.get("doctor")
    local route = adapter and adapter.current_route and adapter.current_route()
    if route and spec.screens[route] then s.screen = route end
    -- The Doctor owner moves its own field selection with E2: focus follows it.
    for _, d in ipairs(describe()) do
      if d.selected then focus[s.screen] = d.id; break end
    end
  end
  -- K2 in the assignment picker closes the owner's sub-page: follow it back.
  if s.screen == "C07" then
    local parameters = channel_edit_page_ui.adapter_owners().parameters
    local page = parameters.adapter_controls and parameters.adapter_controls().trig_lock_page
    if page and not page:is_sub_page_enabled() and current.event == "K2.down" and current.before == "C07" then
      local frame = table.remove(s.return_stack)
      s.screen = frame and frame.screen or "C02"
    end
  end
  s.modal = MODAL_SCREENS[s.screen] == true
  local adapter, provider = feature_adapter()
  s.dirty = adapter ~= nil and feature_editor(provider).dirty == true
  s.shift = is_key1_down == true
end

-- A page change made by the grid (or by a setter outside the router) moves the
-- context; the grid outcome for that press sets the screen in the same step.
local function sync_context()
  local context = CONTEXT_OF_PAGE[program.get_selected_page()]
  if context and context ~= router.state.context then
    router.state.context = context
    local screen = spec.screens[router.state.screen]
    local ok = false
    for _, c in ipairs(screen.context) do if c == context then ok = true end end
    if not ok then router.state.screen = spec.contexts[context] end
  end
end

local function after_event()
  -- A follow made while already on its screen (a second merge gesture on
  -- Merge detail) must not leave a frame that returns to the same screen.
  -- (A hold keeps its own frame: release returns to where it began.)
  local stack = router.state.return_stack
  while current.event == "grid.outcome" and #stack > 0 and stack[#stack].screen == router.state.screen do
    table.remove(stack)
  end
  reconcile_owner_routes()
  sync_workspace()
  sync_field_state()
  fn.dirty_screen(true)
end

local dispatch_event

-- Input handling never raises into norns or the grid path: a failure is
-- logged and the screen is re-synchronised with its owners.
local function dispatch(event, payload)
  if not installed then return end
  local ok, err = pcall(dispatch_event, event, payload)
  if not ok then
    print("ui_live: " .. tostring(err))
    pcall(after_event)
  end
end

dispatch_event = function(event, payload)
  sync_context()
  reconcile_owner_routes()
  -- A screen whose fields cannot be read still takes navigation input.
  local read, problem = pcall(sync_field_state)
  if not read then
    print("ui_live: " .. tostring(problem))
    router.state.field_id, router.state.field_kind = nil, "unavailable"
  end
  local s = router.state
  if screen_entry().profile == "tasks" and (event == "K3.down") then
    payload = payload or {}
    payload.task = payload.task or s.field_id
    -- Rows such as Rhythm Doctor are shown only for the current algorithm.
    if payload.algorithm == nil and trigger_edit_page and trigger_edit_page.get_algorithm then
      payload.algorithm = trigger_edit_page.get_algorithm()
    end
  end
  local before = s.screen
  current.event, current.before = event, before
  local ok, err = pcall(router.step, router, event, payload)
  if not ok then
    print("ui_live: " .. tostring(err))
  end
  after_event()
  current.event = nil
  if router.state.screen ~= before then ui_motion.screen_changed(before, router.state.screen) end
end

-- Norns input ------------------------------------------------------------------------------

function ui_live.enc(n, d)
  if d == 0 then return end
  current.delta = d
  if n == 1 then
    -- A large E1 turn moves one family boundary only.
    dispatch(d > 0 and "E1+" or "E1-")
  else
    dispatch("E" .. n .. (d > 0 and "+" or "-"), {delta = d})
  end
  current.delta = 0
end

function ui_live.key(n, z)
  dispatch("K" .. n .. (z == 1 and ".down" or ".up"))
end

-- Grid notifications (lib/m_grid.lua) --------------------------------------------------------

local presentation_held = false

function ui_live.grid_hold(steps)
  if #steps > 0 and not presentation_held then
    presentation_held = true
    dispatch("hold.begin", {steps = steps})
  elseif #steps > 0 then
    dispatch("hold.change", {steps = steps})
  elseif presentation_held then
    presentation_held = false
    dispatch("hold.end")
  end
end

function ui_live.grid_outcome(flow_id, extra)
  local payload = {flow_id = flow_id}
  for key, value in pairs(extra or {}) do payload[key] = value end
  -- Flow alternatives read the page as its context name and the Trig algorithm.
  payload.page = CONTEXT_OF_PAGE[program.get_selected_page()] or payload.page
  if payload.algorithm == nil and trigger_edit_page and trigger_edit_page.get_algorithm then
    payload.algorithm = trigger_edit_page.get_algorithm()
  end
  -- Choosing a song slot while stopped opens its setup (G36 selected_stopped).
  if flow_id == "G36" and payload.outcome == nil and not m_clock.is_playing() then
    payload.outcome = "selected_stopped"
  end
  local flow = spec.flows[flow_id]
  if flow and flow.routes == "doctor_routes" then
    local adapter = ui_adapters.get("doctor")
    local inputs = adapter and adapter.inputs and adapter.inputs()
    if not inputs then return end
    for key, value in pairs(inputs) do if payload[key] == nil then payload[key] = value end end
  end
  local selected = program.get()
  payload.target = payload.target or {channel = selected.selected_channel, song_slot = selected.selected_song_pattern,
    step_set = held_steps()}
  dispatch("grid.outcome", payload)
end

function ui_live.grid_disconnect()
  presentation_held = false
  dispatch("grid.disconnect")
end

function ui_live.native_changed(open)
  if not installed then return end
  if open and not router.state.native then
    dispatch("K1.short")
  elseif not open and router.state.native then
    dispatch("native.return")
  end
end

function ui_live.async_update()
  if installed then dispatch("async.update") end
end

-- View model -------------------------------------------------------------------------------

local function two(n) return string.format("%02d", n or 0) end

-- The grid viewer each context's pattern screens show (P01, P03, P04, P05).
local VIEWER_OWNER = {
  Trig = function() return trigger_edit_page_ui end, Note = function() return note_edit_page_ui end,
  Velocity = function() return velocity_edit_page_ui end, Scale = function() return scale_edit_page_ui end,
  Song = function() return song_edit_page_ui end,
}

local function viewer()
  local owner = VIEWER_OWNER[router.state.context]
  local page_ui = owner and owner()
  return page_ui and page_ui.adapter_owners and page_ui.adapter_owners().grid_viewer
end

-- Compact identity for the title row: CH03, CH03 S02, CH03 ST05, CH03 4ST,
-- SLOT 02 (Scale) or SONG 04 (Song).
local function scope_text(target)
  local s = router.state
  local parts = {}
  if s.context == "Scale" then
    parts[#parts + 1] = "SLOT " .. two(program.get().selected_scale)
  elseif s.context == "Song" then
    parts[#parts + 1] = "SONG " .. two(target.song_slot)
  else
    -- Pattern screens name the channel their viewer shows.
    local view = spec.screens[s.screen].layout == "pattern64" and viewer()
    parts[#parts + 1] = "CH" .. two(view and view.selected_channel or target.channel)
    if (target.song_slot or 1) ~= 1 then parts[#parts + 1] = "S" .. two(target.song_slot) end
  end
  local held = target.held or {}
  if #held == 1 then
    parts[#parts + 1] = "ST" .. two(held[1])
  elseif #held > 1 then
    parts[#parts + 1] = #held .. "ST"
  end
  return table.concat(parts, " ")
end

local FOOTER = {
  masks = "E2 MASK  E3 SET", parameters = "E2 SLOT  E3 SET  K2 ASSIGN", history = "E3 MOVE  K2 UNDO  K3 REDO",
  clock = "E3 SET  K3 APPLY  K2 CANCEL", device = "E3 SET  K3 APPLY  K2 CANCEL",
  assignment = "E3 PICK  K3 SET  K2 BACK", scale = "E3 SET  K3 APPLY  K2 CANCEL",
  scale_clock = "E3 SET  K3 APPLY  K2 CANCEL", song = "E3 SET  K3 APPLY  K2 CANCEL",
  song_clock = "E3 SET  K3 APPLY  K2 CANCEL", trig_options = "E3 SET  K3 APPLY",
  feature = "E3 SET  K3 APPLY  K2 BACK", tasks = "E2 CHOOSE  K3 OPEN", read_only = "E1 TASKS",
  doctor = "E2 FIELD  E3 SET", confirmation = "K3 CONFIRM  K2 CANCEL", native = "K1 PARAMS",
}

-- 64 cells of the viewed channel exactly as the grid viewer draws its steps,
-- with held steps outlined and the playing step underlined.
local function cells(target)
  local view = viewer()
  local levels = view and view:levels() or {}
  local held = {}
  for _, s in ipairs(target.held or {}) do held[s] = true end
  local playing_step
  if view and m_clock and m_clock.is_playing and m_clock.is_playing() then
    local channel = program.get_channel(program.get().selected_song_pattern, view.selected_channel)
    playing_step = channel and channel.current_step
  end
  local result = {}
  for k = 1, 64 do
    result[k] = {level = levels[k] or 0, selected = held[k] == true, playing = playing_step == k}
  end
  return result
end

-- Where a focused value is a plain number in a range, its position (0..1) for
-- the value dial; lists, Off and Inherit sentinels get no dial.
local function dial_fraction(d)
  if not d or d.kind ~= "value" then return nil end
  local domain = d.domain or {}
  local raw, low, high = tonumber(domain.raw), tonumber(domain.min), tonumber(domain.max)
  if not (raw and low and high) or high <= low or domain.enum or domain.values then return nil end
  if (domain.off ~= nil and raw == domain.off) or (domain.inherit ~= nil and raw == domain.inherit) then return nil end
  return math.max(0, math.min(1, (raw - low) / (high - low)))
end

-- A beat for the characters: the Doctor dances to the analysed tempo (a
-- steady 96 without one); the others keep time only while the sequencer runs.
local function art_motion(art)
  if not art or not ui_motion.enabled() then return nil end
  if art == "doctor" or art == "window" then
    local model = trigger_edit_page and trigger_edit_page.get_rhythm_doctor_model and trigger_edit_page.get_rhythm_doctor_model()
    local tempo = model and tonumber(model.tempo) or 96
    return {beat = util.time() * tempo / 60}
  end
  if m_clock and m_clock.is_playing and m_clock.is_playing() and clock and clock.get_beats then
    return {beat = clock.get_beats()}
  end
  return nil
end

function ui_live.view_model()
  local s = router.state
  local screen = screen_entry()
  local descriptors, code, target = describe()
  target = target or capture_target()
  local fields = {}
  -- Overview grids hold exactly the screen's declared cells (8 masks, 10 slots);
  -- scope/steps descriptors are already summarised in the title row.
  local only
  if screen.layout == "overview_masks" or screen.layout == "overview_params" then
    only = {}
    for _, id in ipairs(screen.fields) do only[id] = true end
  end
  for _, d in ipairs(descriptors) do
    if only and not only[d.id] then goto continue end
    local kind = d.kind
    if screen.profile == "read_only" and kind ~= "action" and kind ~= "inspection" then kind = "readonly" end
    -- Task rows are destinations, not values: their screen ids stay internal.
    local value = screen.profile == "tasks" and "" or (d.value or "")
    fields[#fields + 1] = {id = d.id, label = d.label, short_label = d.short_label, value = value,
      compact_value = d.compact_value, kind = kind, visible = true, enabled = d.enabled, marker = d.marker}
    ::continue::
  end
  local index = 1
  local focus_id = focus[s.screen]
  for i, f in ipairs(fields) do if f.id == focus_id then index = i end end
  local footer = FOOTER[screen.profile] or ""
  -- Detail inspectors ignore E1; K2 returns to where they were opened from.
  if s.screen == "C08" or s.screen == "C09" or s.screen == "S04" then footer = "K2 BACK" end
  -- A focused screen shows one field: the footer names its neighbours instead.
  if screen.layout == "focused" and #fields > 1 then
    -- Owner-selection screens move E2 over their editable fields only.
    local reach, at = fields, index
    if OWNER_SELECTION[screen.profile] then
      reach = {}
      for _, f in ipairs(fields) do if f.kind == "value" or f.kind == "action" or f.id == fields[index].id then reach[#reach + 1] = f end end
      for i, f in ipairs(reach) do if f.id == fields[index].id then at = i end end
    end
    local previous, following = reach[at - 1], reach[at + 1]
    footer = {left = previous and ("< " .. previous.label) or "| START",
      right = following and (following.label .. " >") or "END |"}
  end
  if tooltip and tooltip.text then footer = tostring(tooltip.text) end
  local status = code and (code:upper():gsub("_", " ")) or ""
  -- Every Rhythm Doctor screen keeps the owner's lane and status visible
  -- (providers.doctor.readouts): SETUP / field while setting up, else LANE / status.
  if s.context == "Trig" and doctor_active() and trigger_edit_page.get_rhythm_doctor_model then
    local model = trigger_edit_page.get_rhythm_doctor_model()
    if model and model.setup and model.setup.active then
      status = "SETUP / " .. tostring(model.setup.field)
    elseif model then
      status = (model.lane and (model.lane .. " / ") or "") .. tostring(model.status or model.state or "")
    end
  end
  local vm = {
    screen = s.screen, title = screen.title, scope = scope_text(target), fields = fields,
    selected = math.max(1, index), layout = screen.layout, footer = footer, status = status,
    art = screen.art, pose = ui_motion.pose()
  }
  if screen.layout == "pattern64" then vm.cells = cells(target) end
  vm.motion = art_motion(screen.art)
  vm.active = s.dirty ~= true
  if screen.layout == "focused" and not screen.art then
    local d = focused(descriptors)
    vm.dial = dial_fraction(d)
    vm.dial_key = d and (s.screen .. ":" .. d.id)
  end
  return vm
end

function ui_live.redraw()
  if not installed then return end
  local vm = ui_live.view_model()
  ui_motion.draw(vm, ui_render.draw)
end

-- Installation -----------------------------------------------------------------------------

local function adapter_factory(name) return include("mosaic/lib/ui_adapters/" .. name) end

function ui_live.install()
  page_numbers()
  ui_adapters.reset()
  local channel = channel_edit_page_ui.adapter_owners()
  for _, name in ipairs({"masks", "parameters", "device", "clock", "history", "assignment", "merge", "harmony"}) do
    ui_adapters.register(name, adapter_factory(name)(ui_adapters, channel))
  end
  ui_adapters.register("scale", adapter_factory("scale")(ui_adapters, scale_edit_page_ui.adapter_owners()))
  ui_adapters.register("scale_clock", adapter_factory("scale_clock")(ui_adapters, scale_edit_page_ui.adapter_owners()))
  ui_adapters.register("song", adapter_factory("song")(ui_adapters, song_edit_page_ui.adapter_owners()))
  ui_adapters.register("song_clock", adapter_factory("song_clock")(ui_adapters, song_edit_page_ui.adapter_owners()))
  ui_adapters.register("trig_options", adapter_factory("trig_options")(ui_adapters, trigger_edit_page_ui.adapter_owners()))
  ui_adapters.register("native", adapter_factory("native")(ui_adapters, {}))
  ui_adapters.register("doctor", adapter_factory("doctor")(ui_adapters, {trigger_edit_page = trigger_edit_page}))
  ui_adapters.register("read_only", adapter_factory("read_only")(ui_adapters, {}))
  ui_adapters.register("tasks", adapter_factory("tasks")(ui_adapters, {
    state = function() return {algorithm = trigger_edit_page and trigger_edit_page.get_algorithm and trigger_edit_page.get_algorithm()} end
  }))
  local harmony = feature_editor("harmony")
  ui_adapters.register("confirmation", adapter_factory("confirmation")(ui_adapters, {
    harmony = {
      pending = function(_, contract) return harmony:get_screen() == contract.source_route end,
      confirm = function() harmony:key(3) end,
      cancel = function() harmony:key(2) end,
      generation = function() return harmony.generation end,
    }
  }))
  local context = CONTEXT_OF_PAGE[program.get_selected_page()] or "Channel"
  router = ui_router.new(spec, hooks, ui_router.initial(spec.contexts[context], context))
  installed = true
  after_event()
end

function ui_live.state() return router and router.state end
function ui_live.installed() return installed end
function ui_live.describe(screen_id) return describe(screen_id) end
function ui_live.set_focus(screen_id, field_id) focus[screen_id] = field_id end

return ui_live
