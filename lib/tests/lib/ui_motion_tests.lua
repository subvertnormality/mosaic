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
  local ok, err = pcall(ui_motion.draw, model, function() rendered = rendered + 1 end)
  restore()
  assert(ok, err)
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

-- Owner decision 2026-09-25: screens change without a transition.
function test_ui_motion_screen_change_draws_the_new_screen_at_once()
  with_motion(2, function(dirty)
    ui_motion.screen_changed()
    luaunit.assert_false(ui_motion.busy())
    local first, rendered = frame(vm("C02"))
    luaunit.assert_equals(rendered, 1)
    -- The renderer's frame plus the resting mark: nothing covers the screen.
    luaunit.assert_equals(count(first, "rect"), 4)
    luaunit.assert_equals(dirty(), 0)
  end)
end

-- The glide's shadow rectangles, frame by frame, as {x, y}.
local function glide_path(from, to)
  frame(vm("C01", from))
  while ui_motion.busy() do frame(vm("C01", from)) end
  local path = {}
  for _ = 1, 12 do
    local calls = frame(vm("C01", to))
    for index, call in ipairs(calls) do
      if call[1] == "rect" and calls[index + 1] and calls[index + 1][1] == "stroke" then
        path[#path + 1] = {call[2], call[3]}
      end
    end
    if not ui_motion.busy() then break end
  end
  return path
end

function test_ui_motion_selection_shadow_travels_diagonally_between_rows()
  with_motion(2, function()
    -- Cell 4 (top right) to cell 5 (bottom left) on the masks overview.
    local path = glide_path(4, 5)
    luaunit.assert_true(#path >= 4, "a visible glide")
    local start_x, start_y, end_x, end_y = 96, 9, 0, 27
    for index, point in ipairs(path) do
      local x, y = point[1], point[2]
      -- Never parked on the cell it left.
      luaunit.assert_false(x == start_x and y == start_y, "frame " .. index)
      if index > 1 then
        -- x and y move together every frame: a diagonal, never an L.
        luaunit.assert_true(x < path[index - 1][1], "x moves on frame " .. index)
        luaunit.assert_true(y > path[index - 1][2], "y moves on frame " .. index)
      end
      -- On the straight line between the two cells.
      local along = (start_x - x) / (start_x - end_x)
      luaunit.assert_true(math.abs((y - start_y) - along * (end_y - start_y)) < 0.01, "on the line " .. index)
    end
    luaunit.assert_equals(path[#path], {end_x, end_y})
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

-- CI evidence (run 36111246733): leaving a dial or a rolling value mid-motion
-- kept busy() true, so a static screen redrew every frame for ever.
function test_ui_motion_leaving_a_dial_or_roll_mid_motion_lets_the_screen_rest()
  with_motion(2, function(dirty)
    local focused = {screen = "C04", selected = 1, layout = "focused", dial = 0.1, dial_key = "C04:rate",
      fields = {{id = "rate", value = "/2"}}}
    frame(focused)
    focused.dial = 0.9
    focused.fields[1].value = "/6"
    frame(focused)
    luaunit.assert_true(ui_motion.busy(), "dial sweeping and value rolling")
    -- Straight to a static overview with neither.
    local frames = 0
    repeat frames = frames + 1; frame(vm("C02", 1)) until not ui_motion.busy() or frames > 20
    luaunit.assert_false(ui_motion.busy())
    luaunit.assert_true(frames <= 8, "settled in " .. frames .. " frames")
    local before = dirty()
    frame(vm("C02", 1)); frame(vm("C02", 1))
    luaunit.assert_equals(dirty(), before, "a resting screen asks for no more frames")
  end)
end

-- A character keeping time redraws on its own tick (at most 12 a second), not
-- every frame: full redraws must not crowd the sequencer on the norns.
function test_ui_motion_characters_redraw_on_a_capped_tick_not_every_frame()
  with_motion(2, function(dirty)
    local saved_clock = clock
    local runs, sleeps = {}, {}
    clock = {run = function(f) local co = coroutine.create(f); runs[#runs + 1] = co; return co end,
      sleep = function(t) sleeps[#sleeps + 1] = t; coroutine.yield() end}
    local ok, err = pcall(function()
      local dancing = {screen = "R01", selected = 1, layout = "focused", motion = {beat = 1.2},
        fields = {{id = "a", value = "1"}}}
      frame(dancing); frame(dancing)
      while ui_motion.busy() do frame(dancing) end
      local before = dirty()
      frame(dancing)
      luaunit.assert_equals(dirty(), before, "a dancing frame asks for no frame of its own")
      luaunit.assert_equals(#runs, 1)
      coroutine.resume(runs[1]); coroutine.resume(runs[1])
      luaunit.assert_equals(sleeps[1], 1 / 12)
      luaunit.assert_true(dirty() > before, "the tick asks for the next pose")
      frame({screen = "C01", selected = 1, layout = "overview_masks"})
      for _ = 1, 3 do coroutine.resume(runs[1]) end
      luaunit.assert_equals(coroutine.status(runs[1]), "dead")
    end)
    clock = saved_clock
    if not ok then error(err, 0) end
  end)
end
