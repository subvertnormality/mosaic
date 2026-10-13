-- README "UI Motion": names and values too long for their space scroll right
-- to left so they can be read in full (owner request 26 September 2026).
-- lib/ui_render.lua fit() scrolls cut text on the marquee phase ui_motion
-- supplies; lib/ui_motion.lua ticks that phase only while text is cut and asks
-- for a frame only when a text moves.

local ui_render = include("mosaic/lib/ui_render")
local ui_motion = include("mosaic/lib/ui_motion")

local LONG = "Trig probability mod"

-- A screen whose text is 5 px per character; records what text is drawn where.
local function with_screen(body)
  local saved = screen
  local texts = {}
  local x, y = 0, 0
  screen = setmetatable({
    text_extents = function(t) return #tostring(t) * 5, 8 end,
    move = function(nx, ny) x, y = nx, ny end,
    text = function(t) texts[#texts + 1] = {x = x, y = y, text = t} end,
    text_right = function(t) texts[#texts + 1] = {x = x, y = y, text = t, right = true} end,
  }, {__index = function() return function() end end})
  local ok, err = pcall(body, texts)
  screen = saved
  if not ok then error(err, 0) end
end

-- One detail row selected: its label has 72 px of room beside a short value.
local function frame(phase)
  local shown, report
  with_screen(function(texts)
    local _, r = ui_render.draw({screen = "C07", title = "ASSIGN PARAM", scope = "CH01", layout = "detail",
      selected = 1, footer = "", marquee = phase,
      fields = {{id = "a", label = LONG, value = "", kind = "action"}}})
    report = r
    for _, t in ipairs(texts) do if t.y == 27 and t.x == 7 then shown = t.text end end
  end)
  return shown, report
end

function test_ui_marquee_cut_text_scrolls_right_to_left_until_its_end_shows()
  -- 72 px holds 14 characters: the label is cut, statically with a ~.
  local static = frame(nil)
  luaunit.assert_equals(static, "Trig probabil~")
  -- It rests on its start, then drops one character per tick...
  for phase = 0, 7 do luaunit.assert_equals((frame(phase)), static, "rest " .. phase) end
  luaunit.assert_equals((frame(8)), "rig probabili~")
  luaunit.assert_equals((frame(9)), "ig probabilit~")
  -- ...until its end shows (20 characters, 14 fit: 6 steps), rests, restarts.
  luaunit.assert_equals((frame(13)), "robability mod")
  for phase = 13, 20 do luaunit.assert_equals((frame(phase)), "robability mod", "end " .. phase) end
  luaunit.assert_equals((frame(22)), static)
end

function test_ui_marquee_reports_cut_text_and_the_ticks_until_it_moves()
  local _, resting = frame(0)
  luaunit.assert_true(resting.cut)
  luaunit.assert_equals(resting.next_move, 8) -- still for its whole rest
  local _, scrolling = frame(9)
  luaunit.assert_equals(scrolling.next_move, 1)
  local _, at_end = frame(14)
  luaunit.assert_equals(at_end.next_move, 8)
  -- Nothing cut: no tick needed.
  with_screen(function()
    local _, r = ui_render.draw({screen = "C07", title = "ASSIGN PARAM", scope = "CH01", layout = "detail",
      selected = 1, footer = "", marquee = 0, fields = {{id = "a", label = "Cutoff", value = "", kind = "action"}}})
    luaunit.assert_false(r.cut)
    luaunit.assert_nil(r.next_move)
  end)
end

function test_ui_marquee_ticks_only_while_text_is_cut_and_redraws_only_on_a_move()
  local saved_clock, saved_fn, saved_params = clock, fn, params
  local runs, sleeps, dirty = {}, {}, 0
  clock = {run = function(f) local co = coroutine.create(f); runs[#runs + 1] = co; return co end,
    sleep = function(s) sleeps[#sleeps + 1] = s; coroutine.yield() end}
  fn = {dirty_screen = function(v) if v then dirty = dirty + 1 end end}
  params = {lookup = {ui_motion = true}, get = function() return 2 end}
  local ok, err = pcall(with_screen, function()
    local seen = {}
    local report = {cut = true, next_move = 8}
    local function render(vm) seen[#seen + 1] = vm.marquee; return true, report end
    ui_motion.draw({screen = "C07", selected = 1, layout = "detail", fields = {}}, render)
    luaunit.assert_equals(seen[1], 0)
    luaunit.assert_equals(#runs, 1)
    -- The tick sleeps through the whole rest, then moves the phase and asks for one frame.
    local before = dirty
    coroutine.resume(runs[1])
    luaunit.assert_equals(sleeps[1], 0.8)
    coroutine.resume(runs[1])
    luaunit.assert_equals(ui_motion.marquee_phase(), 8)
    luaunit.assert_equals(dirty, before + 1)
    -- No second tick while one runs; a new selection restarts the phase.
    report = {cut = true, next_move = 1}
    ui_motion.draw({screen = "C07", selected = 2, layout = "detail", fields = {}}, render)
    luaunit.assert_equals(#runs, 1)
    luaunit.assert_equals(seen[2], 0)
    -- Nothing cut any more: the tick ends.
    report = {cut = false}
    ui_motion.draw({screen = "C07", selected = 2, layout = "detail", fields = {}}, render)
    for _ = 1, 3 do coroutine.resume(runs[1]) end
    luaunit.assert_equals(coroutine.status(runs[1]), "dead")
  end)
  clock, fn, params = saved_clock, saved_fn, saved_params
  if not ok then error(err, 0) end
end
