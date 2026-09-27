-- Owner decision 27 September 2026: while a row that opens a child screen is
-- selected the footer names it (K3 OPEN RHYTHM) and keeps the screen's other
-- hints that fit. lib/ui_render.lua draws a {hints = {...}} footer: the first
-- hint always, each later one after two spaces only while the line fits 126 px.
-- Characterisation outside the manual (renderer layout rule).

local ui_render = include("mosaic/lib/ui_render")

-- A screen whose text is 5 px per character; records what text is drawn where.
local function footer_of(hints)
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
    selected = 1, footer = {hints = hints}, fields = {{id = "reason", label = "Reason", value = "OPEN >", kind = "action"}}})
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
