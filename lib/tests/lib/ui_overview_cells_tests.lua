-- Overview dial cells (Trig params C02, Note masks C01), lib/ui_render.lua.
-- README "Trig Parameters": each dial shows the parameter's two short
-- descriptors from the device spec, the first above the value and the second
-- below, as the old dial did (owner decision 27 September 2026: the scrolling
-- joined name was distracting; the two purpose-written labels together replace
-- the long name). The cell text never scrolls: a label wider than its cell is
-- trimmed statically like the old dial's screen.text_trim. The geometry below
-- (row tops 9 and 33, baselines +6/+13/+20, the value in the footer only when
-- the selected cell shows the more-marker) is a characterisation of
-- docs/ui-reimplementation spec.json layout_contract, outside the manual.

local ui_render = include("mosaic/lib/ui_render")
local ui_motion = include("mosaic/lib/ui_motion")

-- A screen whose text is 5 px per character; records texts and rectangles.
local function with_screen(body)
  local saved = screen
  local log = {texts = {}, rects = {}}
  local x, y, level = 0, 0, 0
  local pending
  screen = setmetatable({
    text_extents = function(t) return #tostring(t) * 5, 8 end,
    move = function(nx, ny) x, y = nx, ny end,
    level = function(l) level = l end,
    rect = function(rx, ry, rw, rh) pending = {x = rx, y = ry, w = rw, h = rh, level = level} end,
    stroke = function() if pending then pending.outline = true; log.rects[#log.rects + 1] = pending; pending = nil end end,
    fill = function() if pending then log.rects[#log.rects + 1] = pending; pending = nil end end,
    text = function(t) log.texts[#log.texts + 1] = {x = x, y = y, text = t, level = level} end,
    text_right = function(t) log.texts[#log.texts + 1] = {x = x, y = y, text = t, right = true, level = level} end,
  }, {__index = function() return function() end end})
  local ok, err = pcall(body, log)
  screen = saved
  if not ok then error(err, 0) end
end

local function text_at(log, x, y)
  for _, t in ipairs(log.texts) do if t.x == x and t.y == y and not t.right then return t.text end end
end

local function texts_on_row(log, y)
  local found = {}
  for _, t in ipairs(log.texts) do if t.y == y then found[#found + 1] = t end end
  return found
end

local function params_vm(fields, selected, phase)
  local list = {}
  for n = 1, 10 do
    list[n] = fields[n] or {id = "slot_" .. n, label = "None", short_label = "None", bottom_label = "", value = "X", kind = "value"}
  end
  return {screen = "C02", title = "TRIG PARAMS", scope = "CH01", layout = "overview_params",
    selected = selected or 1, footer = "E2 SLOT  E3 SET", marquee = phase, fields = list}
end

local function draw(vm)
  local log, ok, report
  with_screen(function(l) ok, report = ui_render.draw(vm); log = l end)
  return log, ok, report
end

function test_ui_overview_params_cell_shows_top_label_value_and_bottom_label_on_three_lines()
  local vm = params_vm({[1] = {id = "slot_1", label = "Amp Envelope", short_label = "Amp", bottom_label = "Env",
    value = "64", kind = "value"},
    [7] = {id = "slot_7", label = "Resonance", short_label = "Rsn", bottom_label = "", value = "12", kind = "value"}}, 1)
  local log, ok = draw(vm)
  luaunit.assert_true(ok)
  -- Cell 1 (x 0, row top 9): top label, value, bottom label.
  luaunit.assert_equals(text_at(log, 2, 15), "Amp")
  luaunit.assert_equals(text_at(log, 2, 22), "64")
  luaunit.assert_equals(text_at(log, 2, 29), "Env")
  -- Cell 7 is on the second row (x 25, row top 33); its empty bottom label draws nothing.
  luaunit.assert_equals(text_at(log, 27, 39), "Rsn")
  luaunit.assert_equals(text_at(log, 27, 46), "12")
  luaunit.assert_nil(text_at(log, 27, 53))
  -- The selected label lines are bright, the value level 13; unselected labels level 9.
  for _, t in ipairs(log.texts) do
    if t.x == 2 and (t.y == 15 or t.y == 29) then luaunit.assert_equals(t.level, 15) end
    if t.x == 2 and t.y == 22 then luaunit.assert_equals(t.level, 13) end
    if t.x == 27 and t.y == 39 then luaunit.assert_equals(t.level, 9) end
  end
end

function test_ui_overview_params_selection_outline_encloses_the_three_lines()
  local log = draw(params_vm({}, 7))
  local outlines = {}
  for _, r in ipairs(log.rects) do if r.outline then outlines[#outlines + 1] = r end end
  luaunit.assert_equals(#outlines, 1)
  luaunit.assert_equals({outlines[1].x, outlines[1].y, outlines[1].w, outlines[1].h, outlines[1].level}, {25, 33, 23, 24, 15})
  -- The native stroke draws rows y-1..y+h-1 and columns x-1..x+w-1. The bottom
  -- line (baseline 53: capitals 48..52, descenders 53..54) keeps a blank row 55
  -- above the edge at 56, the footer (58..62) a blank row 57 below it, and the
  -- first line (capitals 34..38) a blank row 33 below the top edge at 32.
  local o = outlines[1]
  luaunit.assert_equals(o.y + o.h - 1, 56)
  luaunit.assert_equals(o.y - 1, 32)
  -- Text starts at x+2 (blank x, x+1); the right edge is column x+w-3, so text
  -- ending by x+w-5 (room w-6 from x+2) keeps a blank column x+w-4.
  luaunit.assert_equals(o.x + o.w - 1, 25 + 25 - 3)
end

function test_ui_overview_params_labels_are_trimmed_statically_never_scrolled()
  local vm = params_vm({[1] = {id = "slot_1", label = "Long", short_label = "Abcdefgh", bottom_label = "Qrstuvwx",
    value = "1", kind = "value"}}, 1)
  local seen
  for _, phase in ipairs({false, 0, 8, 9, 12, 30}) do
    vm.marquee = phase or nil
    local log, _, report = draw(vm)
    -- 19 px of room: three characters, cut from the end with no marker (screen.text_trim).
    luaunit.assert_equals(text_at(log, 2, 15), "Abc")
    luaunit.assert_equals(text_at(log, 2, 29), "Qrs")
    -- Nothing on this screen is cut, so the marquee has nothing to tick.
    luaunit.assert_false(report.cut, "phase " .. tostring(phase))
    luaunit.assert_nil(report.next_move)
    seen = true
  end
  luaunit.assert_true(seen)
end

function test_ui_overview_params_marker_keeps_the_top_right_corner()
  local vm = params_vm({[2] = {id = "slot_2", label = "Long", short_label = "Abcdefgh", bottom_label = "Qrstuvwx",
    value = "1", kind = "value", marker = "S"}}, 1)
  local log = draw(vm)
  -- 14 px beside the marker: two characters; the bottom label keeps the full 19.
  -- The marker (x+w-8) keeps a blank column before the outline at x+w-3.
  luaunit.assert_equals(text_at(log, 27, 15), "Ab")
  luaunit.assert_equals(text_at(log, 42, 15), "S")
  luaunit.assert_equals(text_at(log, 27, 29), "Qrs")
  local cleared
  for _, r in ipairs(log.rects) do
    if r.x == 42 and r.y == 10 and r.w == 4 and r.h == 6 and r.level == 0 then cleared = true end
  end
  luaunit.assert_true(cleared)
end

function test_ui_overview_params_selected_value_line_is_gone_and_footer_is_the_owners()
  local log = draw(params_vm({}, 3))
  -- The old selected-value line (label at x1, value right-aligned at x127, baseline 53).
  for _, t in ipairs(log.texts) do
    luaunit.assert_false(t.right == true and t.y ~= 7, "right-aligned text at " .. t.y)
    luaunit.assert_false(t.x == 1 and t.y == 53)
  end
  luaunit.assert_equals(text_at(log, 1, 63), "E2 SLOT  E3 SET")
end

function test_ui_overview_params_selected_more_cell_puts_its_whole_value_in_the_footer()
  local wide = {id = "slot_4", label = "Waveform", short_label = "Wave", bottom_label = "Shpe", value = "Sawtooth", kind = "value"}
  -- Selected: the cell shows the more-marker and the footer line carries label and whole value.
  local log, ok, report = draw(params_vm({[4] = wide}, 4))
  luaunit.assert_true(ok)
  luaunit.assert_equals(text_at(log, 77, 22), "...")
  luaunit.assert_equals(report.marked, {"slot_4"})
  local footer = texts_on_row(log, 63)
  local right, left
  for _, t in ipairs(footer) do if t.right then right = t else left = t end end
  luaunit.assert_equals(right.text, "Sawtooth")
  luaunit.assert_equals(right.x, 127)
  luaunit.assert_equals(left.text, "Waveform")
  luaunit.assert_equals(#footer, 2)
  -- Not selected: the more-marker only, and the owner's footer stays.
  log = draw(params_vm({[4] = wide}, 1))
  luaunit.assert_equals(text_at(log, 77, 22), "...")
  luaunit.assert_equals(text_at(log, 1, 63), "E2 SLOT  E3 SET")
end

function test_ui_overview_masks_cells_show_the_old_short_names_statically()
  local fields = {}
  local names = {"Trig", "Note", "Vel", "Len", "Chd1", "Chd2", "Chd3", "Chd4"}
  for n, name in ipairs(names) do
    fields[n] = {id = "m" .. n, label = "Mask " .. n, short_label = name, value = tostring(n), kind = "value"}
  end
  fields[3].short_label = "Abcdefghijk" -- 26 px of room: five characters
  local log, _, report = draw({screen = "C01", title = "NOTE MASKS", scope = "CH01", layout = "overview_masks",
    selected = 5, footer = "E2 MASK  E3 SET", marquee = 9, fields = fields})
  luaunit.assert_equals(text_at(log, 2, 15), "Trig")
  luaunit.assert_equals(text_at(log, 2, 22), "1")
  luaunit.assert_equals(text_at(log, 66, 15), "Abcde")
  luaunit.assert_equals(text_at(log, 2, 39), "Chd1")
  luaunit.assert_equals(text_at(log, 2, 46), "5")
  -- Masks have one label: nothing on the third line.
  luaunit.assert_equals(#texts_on_row(log, 29), 0)
  luaunit.assert_equals(#texts_on_row(log, 53), 0)
  luaunit.assert_false(report.cut)
  local outline
  for _, r in ipairs(log.rects) do if r.outline then outline = r end end
  luaunit.assert_equals({outline.x, outline.y, outline.w, outline.h}, {0, 33, 30, 24})
end

-- The glide shadow uses the same cells as the outline.
function test_ui_overview_glide_shadow_lands_on_the_new_row_geometry()
  local saved_params, saved_fn = params, fn
  params = {lookup = {ui_motion = true}, get = function() return 2 end}
  fn = {dirty_screen = function() end}
  local ok, err = pcall(with_screen, function(log)
    local vm = {screen = "C01", layout = "overview_masks", selected = 4, fields = {}}
    ui_motion.draw(vm, function() return true, {} end)
    vm = {screen = "C01", layout = "overview_masks", selected = 5, fields = {}}
    local last
    for _ = 1, 12 do
      log.rects = {}
      ui_motion.draw(vm, function() return true, {} end)
      for _, r in ipairs(log.rects) do if r.outline and r.level == 5 then last = r end end
    end
    luaunit.assert_equals({last.x, last.y, last.w, last.h}, {0, 33, 30, 24})
  end)
  params, fn = saved_params, saved_fn
  if not ok then error(err, 0) end
end
