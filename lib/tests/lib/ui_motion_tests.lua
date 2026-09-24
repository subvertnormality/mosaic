-- README "UI Motion" (Screen Options): decorative motion is on by default,
-- turned off by MOSAIC > UI motion, and never changes what the screen settles on.

local ui_motion = include("mosaic/lib/ui_motion")

local function recording_screen()
  local calls = {}
  local saved = screen
  screen = setmetatable({}, {__index = function(_, name)
    return function(...) calls[#calls + 1] = {name, ...} end
  end})
  return calls, function() screen = saved end
end

local function with_motion(setting, body)
  local saved_params, saved_fn = params, fn
  local dirty = 0
  params = {lookup = {ui_motion = true}, get = function(_, id) return id == "ui_motion" and setting or nil end}
  fn = {dirty_screen = function(value) if value then dirty = dirty + 1 end end}
  local ok, err = pcall(body, function() return dirty end)
  params, fn = saved_params, saved_fn
  if not ok then error(err, 0) end
end

local function vm(screen_id, selected)
  return {screen = screen_id or "C01", selected = selected or 1, layout = "overview_masks"}
end

local function frame(model)
  local calls, restore = recording_screen()
  local rendered = 0
  local ok = pcall(ui_motion.draw, model, function() rendered = rendered + 1 end)
  restore()
  assert(ok)
  return calls, rendered
end

local function count(calls, name)
  local n = 0
  for _, call in ipairs(calls) do if call[1] == name then n = n + 1 end end
  return n
end

function test_ui_motion_off_draws_only_the_resting_mark_and_asks_for_no_frames()
  with_motion(1, function(dirty)
    ui_motion.screen_changed(); ui_motion.nudge("apply")
    luaunit.assert_false(ui_motion.enabled())
    local calls, rendered = frame(vm())
    luaunit.assert_equals(rendered, 1)
    -- The four mark tiles and nothing else.
    luaunit.assert_equals(count(calls, "rect"), 4)
    luaunit.assert_equals(dirty(), 0)
    luaunit.assert_false(ui_motion.busy())
  end)
end

function test_ui_motion_screen_change_reveals_then_settles_on_the_plain_frame()
  with_motion(2, function(dirty)
    ui_motion.screen_changed()
    local first = frame(vm("C02"))
    luaunit.assert_true(count(first, "rect") > 4)
    local frames = 1
    while ui_motion.busy() do frame(vm("C02")); frames = frames + 1 end
    luaunit.assert_true(frames <= 8)
    -- The settled frame is the renderer's plus the resting mark only.
    local settled = frame(vm("C02"))
    luaunit.assert_equals(count(settled, "rect"), 4)
    luaunit.assert_true(dirty() >= frames - 1)
  end)
end

function test_ui_motion_selection_glides_between_overview_cells_then_stops()
  with_motion(2, function()
    frame(vm("C01", 1))
    while ui_motion.busy() do frame(vm("C01", 1)) end
    local moved = frame(vm("C01", 2))
    luaunit.assert_true(count(moved, "stroke") >= 1)
    local frames = 0
    repeat frames = frames + 1; frame(vm("C01", 2)) until count(frame(vm("C01", 2)), "stroke") == 0 or frames > 10
    luaunit.assert_true(frames <= 6)
  end)
end

function test_ui_motion_nudge_lights_the_mark_for_a_few_frames()
  with_motion(2, function()
    ui_motion.nudge("value")
    luaunit.assert_true(ui_motion.busy())
    local frames = 0
    while ui_motion.busy() do frame(vm()); frames = frames + 1 end
    luaunit.assert_true(frames >= 3 and frames <= 8)
  end)
end
