-- Application-surface regression for Rhythm Doctor.  This exercises the real
-- Trigger Editor and norns-screen modules with their outer dependencies
-- replaced by small recording doubles.  It intentionally stays outside the
-- detector and bank model suites: the contract here is native input ownership.
--
-- Characterisation outside README.  PLAN.md's Rhythm Doctor user contract
-- reserves x1/y2 for Record and x2/y2, and gives the lanes a block of five
-- columns from x3 on each of rows 2 and 3.

package.preload.er = function() return { gen = function() return {} end } end

local root = "./"
local function check(value, message) assert(value, message or "expected true") end
local function equal(actual, expected, message)
  assert(actual == expected, (message or "values differ") .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual))
end

local function fader_class()
  local F = {}; F.__index = F
  function F:new(x, y, length, size)
    return setmetatable({ x = x, y = y, length = length, size = size, value = 1, disabled_value = false }, F)
  end
  function F:is_this(x, y) return y == self.y and x >= self.x and x < self.x + self.length end
  function F:press(x, y) if self:is_this(x, y) then self.value = x - self.x + 1 end end
  function F:get_value() return self.value end
  function F:set_value(value) self.value = value end
  function F:set_size(value) self.size = value end
  function F:set_length(value) self.length = value end
  function F:enabled() self.disabled_value = false end
  function F:disabled() self.disabled_value = true end
  function F:draw() end
  return F
end

local function button_class()
  local B = {}; B.__index = B
  function B:new(x, y) return setmetatable({x = x, y = y, state = 1}, B) end
  function B:is_this(x, y) return x == self.x and y == self.y end
  function B:press(x, y) if self:is_this(x, y) then self.state = self.state == 1 and 2 or 1 end end
  function B:get_state() return self.state end
  function B:set_state(value) self.state = value end
  function B:blink() end; function B:no_blink() end; function B:draw() end
  return B
end

-- The unsaved grid is the only thing that tells a player what the recording
-- holds at the current window, so the double records it rather than
-- discarding it. A no-op here is what let phrase navigation blank the grid
-- with every adapter-level test still passing.
local function sequencer_class()
  local S = {}; S.__index = S
  function S:new()
    local instance = setmetatable({ unsaved = nil, unsaved_shows = 0, unsaved_hides = 0 }, S)
    S.last = instance
    return instance
  end
  function S:is_this() return false end
  function S:draw() end; function S:press() end; function S:dual_press() end
  function S:long_press() end
  function S:show_unsaved_grid(grid) self.unsaved = grid; self.unsaved_shows = self.unsaved_shows + 1 end
  function S:hide_unsaved_grid() self.unsaved = nil; self.unsaved_hides = self.unsaved_hides + 1 end
  return S
end

local function trigger_page_context()
  fader, button, sequencer = fader_class(), button_class(), sequencer_class()
  local recorded = { normal = {}, pre = {}, post = {}, long = {}, leds = {}, tips = {}, dirty = 0 }
  press = {
    register = function(_, page, fn) recorded.normal[#recorded.normal + 1] = fn end,
    register_pre = function(_, page, fn) recorded.pre[#recorded.pre + 1] = fn end,
    register_post = function(_, page, fn) recorded.post[#recorded.post + 1] = fn end,
    register_dual = function() end,
    register_long = function(_, page, fn) recorded.long[#recorded.long + 1] = fn end,
  }
  draw = { register_grid = function(_, page, fn) recorded.draw = recorded.draw or {}; recorded.draw[#recorded.draw + 1] = fn end }
  grid_abstraction = { led = function(x, y, value) recorded.leds[x .. "," .. y] = value end }
  scheduler = { debounce = function(fn) return fn end }
  tooltip = { show = function(_, value) recorded.tips[#recorded.tips + 1] = value end }
  fn = { dirty_grid = function() recorded.dirty = recorded.dirty + 1 end }
  params = { string = function() return "8" end }
  pattern = { update_source_working_patterns = function() end }
  program = {
    get = function() return { selected_pattern = 1 } end,
    get_selected_channel = function() return 1 end,
    get_selected_song_pattern = function() return { patterns = {[1] = {trig_values = {}, lengths = {}}} } end,
  }
  local old_include = include
  include = function(path)
    if path == "mosaic/lib/helpers/drum_ops" then return { drum = function() return false end, tresillo = function() return false end, nr = function() return false end } end
    error("unexpected include " .. path)
  end
  local page = dofile(root .. "lib/pages/trigger_edit_page/trigger_edit_page.lua")
  include = old_include
  recorded.sequencer = sequencer.last
  return page, recorded
end

-- Mirrors Adapter:lane_cells -- five columns from 3 on each of rows 2 and 3.
-- The doubles carry it so a page test exercises the same addressing the real
-- adapter hands the page.
local function lane_layout(names)
  local cells = {}
  for index, lane in ipairs(names) do
    cells[index] = { lane = lane, x = 3 + ((index - 1) % 5), y = index <= 5 and 2 or 3 }
  end
  return cells
end

local function give_lane_layout(doctor, names)
  doctor.lane_cells = function() return lane_layout(names) end
  doctor.lane_at = function(_, x, y)
    for _, cell in ipairs(lane_layout(names)) do if cell.x == x and cell.y == y then return cell.lane end end
    return nil
  end
  return doctor
end

local function invoke(functions, x, y)
  for _, fn in ipairs(functions) do fn(x, y) end
end

local tests, failures = 0, {}
local function test(name, body)
  tests = tests + 1
  local ok, problem = pcall(body)
  if not ok then failures[#failures + 1] = name .. ": " .. tostring(problem) end
end

test("fifth algorithm has exact LEDs and its Record key is claimed on key-down", function()
  local page, observed = trigger_page_context()
  local calls = {}
  local doctor = {
    enter = function() calls[#calls + 1] = "enter" end,
    leave = function() calls[#calls + 1] = "leave" end,
    record_pressed = function() calls[#calls + 1] = "record_down" end,
    record_released = function() calls[#calls + 1] = "record_up" end,
    lanes = function() return { "BD", "SD", "CYM" } end,
    lane_cells = function() return lane_layout({ "BD", "SD", "CYM" }) end,
    lane_at = function(_, x, y)
      for _, cell in ipairs(lane_layout({ "BD", "SD", "CYM" })) do
        if cell.x == x and cell.y == y then return cell.lane end
      end
      return nil
    end,
    select_lane = function(_, lane) calls[#calls + 1] = "lane:" .. lane; return {code = "LANE_SELECTED"} end,
    enc = function(_, n, d) calls[#calls + 1] = "enc:" .. n .. "," .. d; return {code = "SETUP_EDITED"} end,
    screen_model = function() return {worker_ready = true} end,
  }
  page.set_rhythm_doctor(doctor); page.register_draws(); page.register_press()
  invoke(observed.normal, 16, 2)
  equal(page.get_algorithm(), 5); equal(calls[1], "enter")
  for _, draw_fn in ipairs(observed.draw) do draw_fn() end
  equal(observed.leds["1,2"], 15); equal(observed.leds["2,2"], 0)
  equal(observed.leds["3,2"], 15); equal(observed.leds["5,2"], 4)
  -- Columns 6 and 7 lit lane LEDs before the set shrank to three. They must go
  -- dark rather than leave lanes the player cannot select.
  equal(observed.leds["6,2"], nil)
  equal(observed.leds["7,2"], nil)
  local claimed = false
  for _, pre in ipairs(observed.pre) do claimed = pre(1, 2) or claimed end
  check(claimed, "Record must be claimed before normal/long/dual dispatch")
  equal(calls[#calls], "record_down")
  -- The input dispatcher skips normal handlers for a claimed key.  That is the
  -- ownership boundary preventing the old Pattern 1 fader from changing.
  for _, post in ipairs(observed.post) do post(1, 2) end
  equal(calls[#calls], "record_up")
  invoke(observed.normal, 4, 2)
  equal(page.get_rhythm_doctor_lane(), "SD"); equal(calls[#calls], "lane:SD")
  invoke(observed.normal, 5, 2)
  equal(page.get_rhythm_doctor_lane(), "CYM"); equal(calls[#calls], "lane:CYM", "x5 selects the cymbal lane")
  -- x6 and x7 held BASS and OHH before those lanes were withdrawn; pressing
  -- there must leave the selection alone rather than pick a neighbour.
  invoke(observed.normal, 6, 2)
  equal(page.get_rhythm_doctor_lane(), "CYM", "the withdrawn BASS column does not change the selection")
  invoke(observed.normal, 7, 2)
  equal(page.get_rhythm_doctor_lane(), "CYM", "retired lane column does not change the selection")
  equal(page.handle_rhythm_doctor_encoder(2, 1).code, "SETUP_EDITED")
  equal(calls[#calls], "enc:2,1")
  invoke(observed.normal, 15, 2)
  equal(calls[#calls], "leave", "leaving algorithm five disconnects the adapter")
end)

test("transport-gated lane selection leaves the displayed lane unchanged", function()
  local page, observed = trigger_page_context()
  local selected = "BD"
  page.set_rhythm_doctor(give_lane_layout({
    enter = function() end,
    lanes = function() return { "BD", "SD", "CYM" } end,
    select_lane = function(_, lane) selected = lane; return {code = "STOP_SEQUENCER"} end,
    screen_model = function() return {worker_ready = false} end,
  }, { "BD", "SD", "CYM" }))
  page.register_press(); invoke(observed.normal, 16, 2)
  invoke(observed.normal, 5, 2)
  equal(selected, "CYM", "adapter must receive the attempted lane for transport gating")
  equal(page.get_rhythm_doctor_lane(), "BD", "gated lane must not alter player-visible selection")
  equal(observed.tips[#observed.tips], "STOP SEQUENCER")
end)

test("K2 and K3 reach Rhythm Doctor only while algorithm five is selected", function()
  local calls, dirty, texts, ui_draw, rects = {}, 0, {}, nil, 0
  local old_include = include
  local pages_component = { new = function() return {add_page = function() end, select_page = function() end, draw = function() end, next_page = function() end, previous_page = function() end, get_selected_page = function() return 1 end} end }
  local page_component = { new = function() return {} end }
  local viewer = { new = function() return {draw = function() end, next_channel = function() end, prev_channel = function() end} end }
  local selector = { new = function() return {select = function() end, draw = function() end, increment = function() end, decrement = function() end, get_selected = function() return {id = 1} end, set_selected_value = function() end} end }
  include = function(path)
    local modules = {
      ["mosaic/lib/ui_components/pages"] = pages_component,
      ["mosaic/lib/ui_components/page"] = page_component,
      ["mosaic/lib/ui_components/grid_viewer"] = viewer,
      ["mosaic/lib/ui_components/list_selector"] = selector,
      -- The real sprite, so a page that draws it is exercised, not stubbed out.
      ["mosaic/lib/rhythm_doctor/dancing_doctor"] = dofile(root .. "lib/rhythm_doctor/dancing_doctor.lua"),
    }
    return assert(modules[path], path)
  end
  draw = {register_ui = function(_, _, fn) ui_draw = fn end}
  screen = {level = function() end, move = function() end, text = function(value) texts[#texts + 1] = value end,
    rect = function() rects = rects + 1 end, fill = function() end}
  fn = {dirty_screen = function() dirty = dirty + 1 end, dirty_grid = function() dirty = dirty + 1 end}
  params = {get = function() return 1 end, set = function() end}
  local algorithm = 4
  trigger_edit_page = {
    get_algorithm = function() return algorithm end,
    handle_rhythm_doctor_key = function(n, z) calls[#calls + 1] = {n, z}; return {code = "OK"} end,
    handle_rhythm_doctor_encoder = function(n, d) calls[#calls + 1] = {n, d}; return {code = "SETUP_EDITED"} end,
    get_rhythm_doctor_model = function()
      return { lane = "BD", status = "EMPTY", hit_count = 0, state = "EMPTY", worker_ready = true,
        setup = {active = true, field = "MANUAL BPM"}, capture_mode = "manual", manual_bpm = 127, input_source = "L" }
    end,
  }
  local ui = dofile(root .. "lib/pages/trigger_edit_page/trigger_edit_page_ui.lua")
  include = old_include
  check(not ui.key(2, 1)); check(not ui.key(3, 1)); equal(#calls, 0)
  algorithm = 5
  check(ui.key(2, 1)); check(ui.key(3, 1)); equal(#calls, 2)
  equal(calls[1][1], 2); equal(calls[2][1], 3); check(dirty >= 4)
  ui.enc(2, 1); equal(#calls, 3); equal(calls[3][1], 2); equal(calls[3][2], 1)
  ui.register_ui_draws(); ui_draw()
  check(table.concat(texts, " "):find("TEMPO MANUAL", 1, true))
  check(table.concat(texts, " "):find("MANUAL BPM 127", 1, true))
  check(table.concat(texts, " "):find("INPUT L", 1, true))
end)

test("the screen shows a refused correction rather than the ordinary alignment label", function()
  -- The adapter records the refusal, but this renderer drew
  -- "ALIGNMENT / <field>" straight from the sub-model and never consulted
  -- status, so the refusal never reached the framebuffer: the player pressed
  -- K3, the screen was unchanged, and nothing appeared to happen.
  local texts, ui_draw = {}, nil
  local old_include = include
  local pages_component = { new = function() return {add_page = function() end, select_page = function() end, draw = function() end, next_page = function() end, previous_page = function() end, get_selected_page = function() return 1 end} end }
  local page_component = { new = function() return {} end }
  local viewer = { new = function() return {draw = function() end, next_channel = function() end, prev_channel = function() end} end }
  local selector = { new = function() return {select = function() end, draw = function() end, increment = function() end, decrement = function() end, get_selected = function() return {id = 1} end, set_selected_value = function() end} end }
  include = function(path)
    local modules = {
      ["mosaic/lib/ui_components/pages"] = pages_component,
      ["mosaic/lib/ui_components/page"] = page_component,
      ["mosaic/lib/ui_components/grid_viewer"] = viewer,
      ["mosaic/lib/ui_components/list_selector"] = selector,
      -- The real sprite, so a page that draws it is exercised, not stubbed out.
      ["mosaic/lib/rhythm_doctor/dancing_doctor"] = dofile(root .. "lib/rhythm_doctor/dancing_doctor.lua"),
    }
    return assert(modules[path], path)
  end
  draw = {register_ui = function(_, _, fn) ui_draw = fn end}
  screen = {level = function() end, move = function() end, text = function(value) texts[#texts + 1] = value end,
    rect = function() rects = rects + 1 end, fill = function() end}
  fn = {dirty_screen = function() end, dirty_grid = function() end}
  params = {get = function() return 1 end, set = function() end}
  local alignment = {active = true, field = "HALF TEMPO", bpm = 120, start_beat = 1, fine_start_ms = 0}
  trigger_edit_page = {
    get_algorithm = function() return 5 end,
    handle_rhythm_doctor_key = function() return {code = "OK"} end,
    handle_rhythm_doctor_encoder = function() return {code = "OK"} end,
    get_rhythm_doctor_model = function()
      return { lane = "BD", status = "CAPTURE AUDIO UNAVAILABLE", hit_count = 0, state = "READY",
        worker_ready = true, alignment = alignment }
    end,
  }
  local ui = dofile(root .. "lib/pages/trigger_edit_page/trigger_edit_page_ui.lua")
  include = old_include
  ui.register_ui_draws()

  -- Refused: the screen must say so.
  alignment.error = "CAPTURE AUDIO UNAVAILABLE"
  texts = {}; ui_draw()
  local drawn = table.concat(texts, " ")
  check(drawn:find("CAPTURE AUDIO UNAVAILABLE", 1, true),
    "the refusal never reached the screen: " .. drawn)
  check(not drawn:find("ALIGNMENT / HALF TEMPO", 1, true),
    "the refusal must replace the ordinary alignment label, not sit beside it")
  -- The draft is kept, so its editable fields stay on screen.
  check(drawn:find("HALF 120 BPM", 1, true), "the draft must remain editable")

  -- Not refused: the ordinary label is shown.
  alignment.error = nil
  texts = {}; ui_draw()
  check(table.concat(texts, " "):find("ALIGNMENT / HALF TEMPO", 1, true))
end)

test("the window position is left to the grid rather than spelled out", function()
  -- "START 1.1.1-4.4.4" told the player what the grid already shows, on the
  -- row the modal and the dancing doctor also use.
  local texts, ui_draw = {}, nil
  local old_include = include
  local pages_component = { new = function() return {add_page = function() end, select_page = function() end, draw = function() end, next_page = function() end, previous_page = function() end, get_selected_page = function() return 1 end} end }
  local page_component = { new = function() return {} end }
  local viewer = { new = function() return {draw = function() end, next_channel = function() end, prev_channel = function() end} end }
  local selector = { new = function() return {select = function() end, draw = function() end, increment = function() end, decrement = function() end, get_selected = function() return {id = 1} end, set_selected_value = function() end} end }
  include = function(path)
    local modules = {
      ["mosaic/lib/ui_components/pages"] = pages_component,
      ["mosaic/lib/ui_components/page"] = page_component,
      ["mosaic/lib/ui_components/grid_viewer"] = viewer,
      ["mosaic/lib/ui_components/list_selector"] = selector,
      ["mosaic/lib/rhythm_doctor/dancing_doctor"] = dofile(root .. "lib/rhythm_doctor/dancing_doctor.lua"),
    }
    return assert(modules[path], path)
  end
  draw = {register_ui = function(_, _, fn) ui_draw = fn end}
  screen = {level = function() end, move = function() end, text = function(value) texts[#texts + 1] = value end,
    rect = function() end, fill = function() end}
  fn = {dirty_screen = function() end, dirty_grid = function() end}
  params = {get = function() return 1 end, set = function() end}
  local ready = {active = true, field = "WINDOW BAR"}
  trigger_edit_page = {
    get_algorithm = function() return 5 end,
    handle_rhythm_doctor_key = function() return {code = "OK"} end,
    handle_rhythm_doctor_encoder = function() return {code = "OK"} end,
    get_rhythm_doctor_model = function()
      return { lane = "BD", status = "READY", hit_count = 12, state = "READY", worker_ready = true,
        tempo = 126.0, tempo_source = "auto", ready = ready,
        window_start_label = "1.1.1", window_end_label = "4.4.4", sensitivity = 0.4, paint_policy = "toggle" }
    end,
  }
  local ui = dofile(root .. "lib/pages/trigger_edit_page/trigger_edit_page_ui.lua")
  include = old_include
  ui.register_ui_draws()

  texts = {}; ui_draw()
  local drawn = table.concat(texts, " ")
  check(not drawn:find("START", 1, true), "the window label must be gone: " .. drawn)
  check(not drawn:find("1.1.1", 1, true), "and not spelled any other way: " .. drawn)

  -- The fields that do say something still do.
  ready.field = "SENSITIVITY"
  texts = {}; ui_draw()
  check(table.concat(texts, " "):find("SENS", 1, true), "sensitivity still reports its value")
  ready.field = "PAINT POLICY"
  texts = {}; ui_draw()
  check(table.concat(texts, " "):find("PAINT", 1, true), "paint policy still reports its value")
end)

test("a paint preview does not outlive the destination it was built for", function()
  -- A preview commits to the target it was built for. Leaving it armed after
  -- the selection moves means Paint writes to the pattern the player navigated
  -- away from while the screen shows the new one. Both the pattern fader and
  -- the page draw consult this, the draw because the song slot changes from
  -- another page entirely.
  local page = trigger_page_context()
  local moved = page.paint_target_moved
  check(moved({song_slot = 1, pattern_id = 1}, {song_slot = 1, pattern_id = 2}), "a new pattern is a new destination")
  check(moved({song_slot = 1, pattern_id = 1}, {song_slot = 2, pattern_id = 1}), "so is a new song slot")
  check(not moved({song_slot = 1, pattern_id = 1}, {song_slot = 1, pattern_id = 1}), "the same destination has not moved")
  check(not moved(nil, {song_slot = 1, pattern_id = 1}), "nothing armed is nothing to discard")
  check(not moved({song_slot = 1, pattern_id = 1}, nil), "an unknown destination is not a move")
end)

test("the dancing doctor holds the free space and yields it to an overlay", function()
  -- The right-hand third is only free while no editor or modal is open: the
  -- overlays write text straight across it, so he has to step aside rather
  -- than be drawn underneath them.
  local texts, ui_draw, rects = {}, nil, 0
  local old_include = include
  local pages_component = { new = function() return {add_page = function() end, select_page = function() end, draw = function() end, next_page = function() end, previous_page = function() end, get_selected_page = function() return 1 end} end }
  local page_component = { new = function() return {} end }
  local viewer = { new = function() return {draw = function() end, next_channel = function() end, prev_channel = function() end} end }
  local selector = { new = function() return {select = function() end, draw = function() end, increment = function() end, decrement = function() end, get_selected = function() return {id = 1} end, set_selected_value = function() end} end }
  include = function(path)
    local modules = {
      ["mosaic/lib/ui_components/pages"] = pages_component,
      ["mosaic/lib/ui_components/page"] = page_component,
      ["mosaic/lib/ui_components/grid_viewer"] = viewer,
      ["mosaic/lib/ui_components/list_selector"] = selector,
      ["mosaic/lib/rhythm_doctor/dancing_doctor"] = dofile(root .. "lib/rhythm_doctor/dancing_doctor.lua"),
    }
    return assert(modules[path], path)
  end
  draw = {register_ui = function(_, _, fn) ui_draw = fn end}
  local left, top = 128, 64
  screen = {level = function() end, move = function() end, text = function(value) texts[#texts + 1] = value end,
    rect = function(x, y, w)
      rects = rects + 1
      if x < left then left = x end
      if y < top then top = y end
      check(x >= 0 and x + w <= 128, "the sprite must stay on the 128 pixel screen")
      check(y >= 0 and y < 64, "the sprite must stay on the 64 pixel screen")
    end,
    fill = function() end}
  fn = {dirty_screen = function() end, dirty_grid = function() end}
  params = {get = function() return 1 end, set = function() end}
  local model = { lane = "BD", status = "READY", hit_count = 24, state = "READY",
    worker_ready = true, tempo = 124.0, tempo_source = "AUTO" }
  trigger_edit_page = {
    get_algorithm = function() return 5 end,
    handle_rhythm_doctor_key = function() return {code = "OK"} end,
    handle_rhythm_doctor_encoder = function() return {code = "OK"} end,
    get_rhythm_doctor_model = function() return model end,
  }
  local ui = dofile(root .. "lib/pages/trigger_edit_page/trigger_edit_page_ui.lua")
  include = old_include
  ui.register_ui_draws()

  texts = {}; rects = 0; ui_draw()
  check(rects > 40, "the ordinary view must show him dancing: " .. rects .. " runs")
  -- The longest ordinary status is about eighteen glyphs at five pixels each,
  -- so he starts past the text rather than through it.
  check(left >= 95, "the sprite crowds the status text at x=" .. left)
  check(top > 12, "the sprite overlaps the title row at y=" .. top)
  check(table.concat(texts, " "):find("124.0 BPM", 1, true), "the page still draws its own text")

  for _, overlay in ipairs({ {alignment = {active = true, field = "HALF TEMPO", bpm = 120}},
                             {setup = {active = true, field = "TEMPO"}},
                             {modal = {detail = "K2 NO / K3 YES"}} }) do
    model.alignment, model.setup, model.modal = overlay.alignment, overlay.setup, overlay.modal
    rects = 0; ui_draw()
    check(rects == 0, "he must yield the space to an overlay, not draw beneath it")
  end
end)

test("the application encoder route opens stopped setup from Rhythm Doctor", function()
  -- This covers the same public norns route as `enc(2, -1)`: application UI,
  -- Trigger Editor UI, Trigger Editor ownership, then the adapter.  The exact
  -- negative delta selects INPUT from the initial TEMPO field.
  local page, observed = trigger_page_context()
  trigger_edit_page = page
  package.path = "./lib/?.lua;" .. package.path
  local Adapter = require("rhythm_doctor.ui_adapter")
  local runtime = {
    machine = { state = "EMPTY" },
    start_capture = function() return {code = "OK"} end,
    record_action = function() return {code = "OK"} end,
    confirm_modal = function() return {code = "OK"} end,
    finish = function() return {code = "OK"} end,
    enter = function() return {ok = true, code = "CAPTURE_WORKER_READY"} end,
  }
  local doctor = Adapter.new({ runtime = runtime, transport_stopped = function() return true end })
  page.set_rhythm_doctor(doctor)
  page.register_press()
  invoke(observed.normal, 16, 2)
  equal(page.get_algorithm(), 5)

  local old_include = include
  local pages_component = { new = function()
    return {add_page = function() end, select_page = function() end, draw = function() end,
      next_page = function() end, previous_page = function() end, get_selected_page = function() return 1 end}
  end }
  local page_component = { new = function() return {} end }
  local viewer = { new = function()
    return {draw = function() end, next_channel = function() end, prev_channel = function() end}
  end }
  local selector = { new = function()
    return {select = function() end, draw = function() end, increment = function() end,
      decrement = function() end, get_selected = function() return {id = 1} end,
      set_selected_value = function() end}
  end }
  include = function(path)
    local modules = {
      ["mosaic/lib/ui_components/pages"] = pages_component,
      ["mosaic/lib/ui_components/page"] = page_component,
      ["mosaic/lib/ui_components/grid_viewer"] = viewer,
      ["mosaic/lib/ui_components/list_selector"] = selector,
      -- The real sprite, so a page that draws it is exercised, not stubbed out.
      ["mosaic/lib/rhythm_doctor/dancing_doctor"] = dofile(root .. "lib/rhythm_doctor/dancing_doctor.lua"),
    }
    return assert(modules[path], path)
  end
  fn.dirty_screen = function() observed.dirty = observed.dirty + 1 end
  local trigger_ui = dofile(root .. "lib/pages/trigger_edit_page/trigger_edit_page_ui.lua")
  pages = { pages = {channel_edit_page = 2, scale_edit_page = 3, trigger_edit_page = 4,
    note_edit_page = 5, velocity_edit_page = 6, song_edit_page = 7} }
  program.get_selected_page = function() return pages.pages.trigger_edit_page end
  include = function(path)
    local modules = {
      ["mosaic/lib/pages/channel_edit_page/channel_edit_page_ui"] = {},
      ["mosaic/lib/pages/scale_edit_page/scale_edit_page_ui"] = {},
      ["mosaic/lib/pages/velocity_edit_page/velocity_edit_page_ui"] = {},
      ["mosaic/lib/pages/note_edit_page/note_edit_page_ui"] = {},
      ["mosaic/lib/pages/trigger_edit_page/trigger_edit_page_ui"] = trigger_ui,
      ["mosaic/lib/pages/song_edit_page/song_edit_page_ui"] = {},
      ["mosaic/lib/ui_components/tooltip"] = {},
      ["mosaic/lib/ui_components/save_confirm"] = {},
    }
    return assert(modules[path], path)
  end
  local application_ui = dofile(root .. "lib/ui.lua")
  include = old_include

  application_ui.enc(2, -1)
  local model = doctor:screen_model()
  check(model.setup.active, "public encoder input must open the setup draft")
  equal(model.setup.field, "INPUT")
end)

test("cleanup closes a worker that was still starting and never retries it", function()
  package.path = "./lib/?.lua;" .. package.path
  local Runtime = require("rhythm_doctor.runtime")
  local opens, closes = 0, 0
  local worker = {
    open = function() opens = opens + 1; return nil, "worker starting" end,
    close = function() closes = closes + 1 end,
  }
  local runtime = Runtime.new({project_id = "startup.ptn", worker = worker, now = function() return 0 end,
    transport_stopped = function() return true end})
  equal(runtime:enter().code, "WORKER_UNAVAILABLE")
  equal(opens, 1)
  equal(runtime:cleanup().code, "CLOSED")
  equal(closes, 1, "shutdown owns and closes a pre-transport worker")
  runtime:poll(); equal(opens, 1, "closed runtime cannot revive a detached startup worker")
end)

-- Phrase navigation on the grid.  The adapter suite already proves the window
-- moves; what it cannot see is what the player is shown afterwards, which is
-- where this feature was broken: every move retired the paint preview and
-- nothing took a new one, so the grid went dark until an unrelated press
-- happened to rebuild it.
local function window_doctor(options)
  options = options or {}
  local doctor = {
    window = options.window or 128,
    phrase = options.phrase or 37,
    low = options.low or 0,
    high = options.high or 239,
    calls = {},
  }
  local function label(cell)
    return string.format("%d.%d.%d", math.floor(cell / 16) + 1, math.floor(cell % 16 / 4) + 1, cell % 4 + 1)
  end
  local function land(target)
    local before = doctor.window
    doctor.window = math.max(doctor.low, math.min(doctor.high, target))
    return { code = "WINDOW_MOVED", window_start = doctor.window,
             window_label = label(doctor.window), moved = doctor.window ~= before }
  end
  function doctor:enter() end
  function doctor:leave() end
  function doctor:lanes() return { "KICK", "SNARE" } end
  give_lane_layout(doctor, { "KICK", "SNARE" })
  function doctor:select_lane(lane) self.calls[#self.calls + 1] = "lane:" .. lane; return { code = "LANE_SELECTED" } end
  function doctor:screen_model() return { worker_ready = true, window_start = self.window } end
  function doctor:invalidate_paint_preview() self.calls[#self.calls + 1] = "invalidate" end
  function doctor:nudge_window(delta)
    self.calls[#self.calls + 1] = "nudge:" .. delta
    if options.refuse then return { code = "NOT_READY" } end
    return land(self.window + delta)
  end
  function doctor:page_window(delta)
    self.calls[#self.calls + 1] = "page:" .. delta
    if options.refuse then return { code = "NOT_READY" } end
    return land(self.window + delta * 64)
  end
  function doctor:jump_to_phrase_start()
    self.calls[#self.calls + 1] = "phrase"
    if options.refuse then return { code = "WINDOW_UNAVAILABLE" } end
    return land(self.phrase)
  end
  -- A preview describes one window, so its cells carry that window's number.
  -- A grid still showing the old number after a move is a stale preview.
  function doctor:paint_preview()
    self.calls[#self.calls + 1] = "preview:" .. self.window
    if options.no_preview then return nil, { code = "NOTHING_TO_PAINT" } end
    return { shifted_cells = { [1] = { window = self.window } }, target = {} }
  end
  return doctor
end

local function arm_paint(page, observed, doctor)
  page.set_rhythm_doctor(doctor); page.register_press(); page.register_draws()
  invoke(observed.normal, 16, 2)
  invoke(observed.normal, 16, 8)
  return observed.sequencer
end

test("a single left or right press moves the window one step and says where it landed", function()
  local page, observed = trigger_page_context()
  local doctor = window_doctor()
  arm_paint(page, observed, doctor)
  invoke(observed.normal, 12, 8)
  equal(doctor.window, 129, "one press of the right button advances a single step")
  equal(observed.tips[#observed.tips], "Step right 9.1.2", "the move reports the position it reached")
  invoke(observed.normal, 10, 8)
  equal(doctor.window, 128, "one press of the left button retreats a single step")
  equal(observed.tips[#observed.tips], "Step left 9.1.1")
end)

test("holding left or right moves a whole phrase", function()
  local page, observed = trigger_page_context()
  local doctor = window_doctor()
  arm_paint(page, observed, doctor)
  invoke(observed.long, 12, 8)
  equal(doctor.window, 192, "a held right button pages a whole phrase forward")
  equal(observed.tips[#observed.tips], "Next phrase 13.1.1")
  invoke(observed.long, 10, 8)
  equal(doctor.window, 128, "a held left button pages a whole phrase back")
  equal(observed.tips[#observed.tips], "Previous phrase 9.1.1")
end)

test("the centre button returns to the phrase marker", function()
  local page, observed = trigger_page_context()
  local doctor = window_doctor()
  arm_paint(page, observed, doctor)
  invoke(observed.normal, 11, 8)
  equal(doctor.window, 37, "the centre button lands on the detected phrase start")
  equal(observed.tips[#observed.tips], "Phrase start 3.2.2")
  invoke(observed.normal, 11, 8)
  equal(observed.tips[#observed.tips], "At phrase start",
    "a second press must not claim a move that did not happen")
end)

test("navigating while painting keeps the recording on the grid", function()
  local page, observed = trigger_page_context()
  local doctor = window_doctor()
  local seq = arm_paint(page, observed, doctor)
  check(seq.unsaved ~= nil, "arming paint shows the recording")
  equal(seq.unsaved[1], true, "the armed preview lights its cell")

  invoke(observed.normal, 12, 8)
  check(seq.unsaved ~= nil, "a step must not blank the grid the player is browsing")
  equal(doctor.calls[#doctor.calls], "preview:129", "the preview is retaken at the window reached")

  invoke(observed.long, 12, 8)
  check(seq.unsaved ~= nil, "paging a phrase must not blank the grid")
  equal(doctor.calls[#doctor.calls], "preview:193")

  invoke(observed.normal, 11, 8)
  check(seq.unsaved ~= nil, "returning to the phrase start must not blank the grid")
  equal(doctor.calls[#doctor.calls], "preview:37")
end)

test("navigating without an armed paint leaves the grid alone", function()
  local page, observed = trigger_page_context()
  local doctor = window_doctor()
  page.set_rhythm_doctor(doctor); page.register_press(); page.register_draws()
  invoke(observed.normal, 16, 2)
  local seq = observed.sequencer
  invoke(observed.normal, 12, 8)
  equal(doctor.window, 129, "browsing works before paint is armed")
  equal(seq.unsaved, nil, "an unarmed page must not start showing a preview")
  for _, call in ipairs(doctor.calls) do
    check(call:sub(1, 8) ~= "preview:", "no preview may be taken while paint is disarmed")
  end
end)

test("a refused move reports the refusal and shows nothing stale", function()
  local page, observed = trigger_page_context()
  local doctor = window_doctor({ refuse = true })
  local seq = arm_paint(page, observed, doctor)
  invoke(observed.normal, 12, 8)
  equal(observed.tips[#observed.tips], "NOT_READY", "a refusal names its reason")
  equal(seq.unsaved, nil, "a preview from the old window must not survive a refused move")
end)

test("a move that clamps at the end of the recording says so", function()
  local page, observed = trigger_page_context()
  local doctor = window_doctor({ window = 239 })
  arm_paint(page, observed, doctor)
  invoke(observed.normal, 12, 8)
  equal(doctor.window, 239)
  equal(observed.tips[#observed.tips], "End of recording",
    "a clamped move must not claim the player moved")
  doctor.window = 0
  invoke(observed.normal, 10, 8)
  equal(observed.tips[#observed.tips], "Start of recording")
end)

test("the browse buttons stay out of the other algorithms", function()
  local page, observed = trigger_page_context()
  local doctor = window_doctor()
  page.set_rhythm_doctor(doctor); page.register_press(); page.register_draws()
  invoke(observed.normal, 15, 2)
  invoke(observed.normal, 12, 8)
  invoke(observed.long, 12, 8)
  invoke(observed.long, 10, 8)
  invoke(observed.normal, 11, 8)
  equal(doctor.window, 128, "paint shift owns these buttons for every other algorithm")
  equal(#doctor.calls, 0, "no algorithm but the fifth may reach the recording window")
end)

-- Ten lanes on one row reached column 12, where the algorithm fader starts:
-- selecting the tenth lane also moved the fader and left Rhythm Doctor. The
-- page must take the layout from the adapter rather than assume a row.
local function ten_lane_doctor()
  local names = { "KICK", "SNARE", "HIHAT", "TOMS", "CYMBALS", "RIDE", "CLAP", "PERC", "BASS", "OTHER" }
  local doctor = { selected = nil }
  function doctor:enter() end
  function doctor:leave() end
  function doctor:lanes() return names end
  give_lane_layout(doctor, names)
  function doctor:select_lane(lane) self.selected = lane; return { code = "LANE_SELECTED" } end
  function doctor:screen_model() return { worker_ready = true } end
  return doctor
end

test("ten lanes light two rows of five and never touch the faders", function()
  local page, observed = trigger_page_context()
  local doctor = ten_lane_doctor()
  page.set_rhythm_doctor(doctor); page.register_draws(); page.register_press()
  invoke(observed.normal, 16, 2)
  for _, draw_fn in ipairs(observed.draw) do draw_fn() end
  for _, cell in ipairs(doctor:lane_cells()) do
    check(observed.leds[cell.x .. "," .. cell.y] ~= nil, cell.lane .. " must light its cell")
  end
  -- Columns 12..16 of rows 2 and 3 are the algorithm and bank-mask faders.
  for x = 12, 16 do
    for y = 2, 3 do
      equal(observed.leds[x .. "," .. y], nil,
        "column " .. x .. " row " .. y .. " belongs to a fader and must stay unlit by lanes")
    end
  end
end)

test("the tenth lane is selectable and does not move the algorithm fader", function()
  local page, observed = trigger_page_context()
  local doctor = ten_lane_doctor()
  page.set_rhythm_doctor(doctor); page.register_draws(); page.register_press()
  invoke(observed.normal, 16, 2)
  equal(page.get_algorithm(), 5)
  invoke(observed.normal, 7, 3)
  equal(doctor.selected, "OTHER", "the tenth lane is reachable on the second row")
  equal(page.get_rhythm_doctor_lane(), "OTHER")
  equal(page.get_algorithm(), 5, "selecting a lane must not disturb the algorithm")
  invoke(observed.normal, 3, 3)
  equal(doctor.selected, "RIDE", "the sixth lane opens the second row")
  equal(page.get_algorithm(), 5)
end)

test("a press outside the lane block is not taken as a lane", function()
  local page, observed = trigger_page_context()
  local doctor = ten_lane_doctor()
  page.set_rhythm_doctor(doctor); page.register_draws(); page.register_press()
  invoke(observed.normal, 16, 2)
  doctor.selected = nil
  invoke(observed.normal, 8, 2)
  equal(doctor.selected, nil, "the column past the block selects nothing")
  invoke(observed.normal, 8, 3)
  equal(doctor.selected, nil)
end)

if #failures > 0 then io.stderr:write(table.concat(failures, "\n") .. "\n"); os.exit(1) end
print("rhythm_doctor app surface: " .. tests .. " tests passed")
