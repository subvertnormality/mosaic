-- Owner decision 27 September 2026: while a row that opens a child screen is
-- selected the footer names it (K3 OPEN RHYTHM) and keeps the screen's other
-- hints that fit. lib/ui_render.lua draws a {hints = {...}} footer: the first
-- hint always, each later one after two spaces only while the line fits 126 px.
-- Characterisation outside the manual (renderer layout rule).

local ui_render = include("mosaic/lib/ui_render")

-- A screen whose text is 5 px per character; records what text is drawn where.
local function footer_of(hints, short)
  local saved = screen
  local texts = {}
  local x, y = 0, 0
  screen = setmetatable({
    text_extents = function(t) return #tostring(t) * 5, 8 end,
    move = function(nx, ny) x, y = nx, ny end,
    text = function(t) texts[#texts + 1] = {x = x, y = y, text = t} end,
    text_right = function(t) texts[#texts + 1] = {x = x, y = y, text = t, right = true} end,
  }, {__index = function() return function() end end})
  local ok, r = pcall(ui_render.draw, {screen = "M05", title = "MERGE RESULT", scope = "CH01", layout = "detail",
    selected = 1, footer = {hints = hints, short = short}, fields = {{id = "reason", label = "Reason", value = "OPEN >", kind = "action"}}})
  screen = saved
  if not ok then error(r, 0) end
  local line = {}
  for _, t in ipairs(texts) do if t.y == 63 then line[#line + 1] = t end end
  return line
end

function test_ui_render_footer_hints_keep_the_other_hints_that_fit()
  local line = footer_of({"K3 OPEN RHYTHM", "K2 BACK"})
  luaunit.assert_equals(#line, 1)
  luaunit.assert_equals(line[1].text, "K3 OPEN RHYTHM  K2 BACK") -- 115 px
  luaunit.assert_equals(line[1].x, 1)
  luaunit.assert_nil(line[1].right)
end

-- Owner decision 27 September 2026: the row name is the first thing to go.
-- If K3 OPEN <NAME> and every other hint do not fit, the footer reads K3 OPEN
-- with every other hint; only if even that is too wide are later hints dropped.
function test_ui_render_footer_hints_drop_the_row_name_before_any_hint()
  -- 23 + 2 + 8 characters = 165 px; K3 OPEN  E1 TASKS = 85 px.
  luaunit.assert_equals(footer_of({"K3 OPEN FAILURE DETAILS", "E1 TASKS"}, "K3 OPEN")[1].text, "K3 OPEN  E1 TASKS")
  -- 19 + 2 + 9 = 30 characters (150 px); without the name 18 (90 px).
  luaunit.assert_equals(footer_of({"K3 OPEN TRIG PARAMS", "K1 PARAMS"}, "K3 OPEN")[1].text, "K3 OPEN  K1 PARAMS")
  -- 23 + 2 + 4 + 2 + 4 = 35 characters (175 px); without the name 19 (95 px): both later hints stay.
  luaunit.assert_equals(footer_of({"K3 OPEN FAILURE DETAILS", "K2 X", "E1 Y"}, "K3 OPEN")[1].text,
    "K3 OPEN  K2 X  E1 Y")
  -- Everything fits with the name: the name stays.
  luaunit.assert_equals(footer_of({"K3 OPEN RHYTHM", "K2 BACK"}, "K3 OPEN")[1].text, "K3 OPEN RHYTHM  K2 BACK")
  -- Even without the name the hints are too wide: later ones drop as before.
  luaunit.assert_equals(footer_of({"K3 OPEN REASON", "K2 BACK TO THE VERY START", "E1 TASKS"}, "K3 OPEN")[1].text,
    "K3 OPEN  E1 TASKS")
end

function test_ui_render_footer_hints_drop_a_hint_that_does_not_fit()
  -- 23 + 2 + 8 characters = 165 px: E1 TASKS is left out, the name stays whole.
  luaunit.assert_equals(footer_of({"K3 OPEN FAILURE DETAILS", "E1 TASKS"})[1].text, "K3 OPEN FAILURE DETAILS")
  -- A later short hint still joins when an earlier one was too wide.
  luaunit.assert_equals(footer_of({"K3 OPEN REASON", "K2 BACK TO THE VERY START", "E1 TASKS"})[1].text,
    "K3 OPEN REASON  E1 TASKS")
end

function test_ui_render_footer_hints_cut_a_first_hint_wider_than_the_row()
  luaunit.assert_equals(footer_of({"K3 OPEN A NAME WIDER THAN THE FOOTER", "K2 BACK"})[1].text, "K3 OPEN A NAME WIDER THA~") -- 125 px
end
