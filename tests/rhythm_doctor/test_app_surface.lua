-- Application-surface regression for Rhythm Doctor.  This exercises the real
-- Trigger Editor and norns-screen modules with their outer dependencies
-- replaced by small recording doubles.  It intentionally stays outside the
-- detector and bank model suites: the contract here is native input ownership.
--
-- Characterisation outside README.  PLAN.md's Rhythm Doctor user contract
-- reserves x1/y2 for Record, x2/y2, and x3..7/y2 for the five lanes.

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

local function sequencer_class()
  local S = {}; S.__index = S
  function S:new() return setmetatable({}, S) end
  function S:is_this() return false end
  function S:draw() end; function S:press() end; function S:dual_press() end
  function S:long_press() end; function S:show_unsaved_grid() end; function S:hide_unsaved_grid() end
  return S
end

local function trigger_page_context()
  fader, button, sequencer = fader_class(), button_class(), sequencer_class()
  local recorded = { normal = {}, pre = {}, post = {}, leds = {}, tips = {}, dirty = 0 }
  press = {
    register = function(_, page, fn) recorded.normal[#recorded.normal + 1] = fn end,
    register_pre = function(_, page, fn) recorded.pre[#recorded.pre + 1] = fn end,
    register_post = function(_, page, fn) recorded.post[#recorded.post + 1] = fn end,
    register_dual = function() end, register_long = function() end,
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
  return page, recorded
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
    select_lane = function(_, lane) calls[#calls + 1] = "lane:" .. lane; return {code = "LANE_SELECTED"} end,
    enc = function(_, n, d) calls[#calls + 1] = "enc:" .. n .. "," .. d; return {code = "SETUP_EDITED"} end,
    screen_model = function() return {worker_ready = true} end,
  }
  page.set_rhythm_doctor(doctor); page.register_draws(); page.register_press()
  invoke(observed.normal, 16, 2)
  equal(page.get_algorithm(), 5); equal(calls[1], "enter")
  for _, draw_fn in ipairs(observed.draw) do draw_fn() end
  equal(observed.leds["1,2"], 15); equal(observed.leds["2,2"], 0)
  equal(observed.leds["3,2"], 15); equal(observed.leds["7,2"], 4)
  local claimed = false
  for _, pre in ipairs(observed.pre) do claimed = pre(1, 2) or claimed end
  check(claimed, "Record must be claimed before normal/long/dual dispatch")
  equal(calls[#calls], "record_down")
  -- The input dispatcher skips normal handlers for a claimed key.  That is the
  -- ownership boundary preventing the old Pattern 1 fader from changing.
  for _, post in ipairs(observed.post) do post(1, 2) end
  equal(calls[#calls], "record_up")
  invoke(observed.normal, 7, 2)
  equal(page.get_rhythm_doctor_lane(), "BASS"); equal(calls[#calls], "lane:BASS")
  invoke(observed.normal, 5, 2)
  equal(page.get_rhythm_doctor_lane(), "CHH"); equal(calls[#calls], "lane:CHH", "x5 selects closed hi-hat")
  invoke(observed.normal, 6, 2)
  equal(page.get_rhythm_doctor_lane(), "OHH"); equal(calls[#calls], "lane:OHH", "x6 selects open hi-hat")
  equal(page.handle_rhythm_doctor_encoder(2, 1).code, "SETUP_EDITED")
  equal(calls[#calls], "enc:2,1")
  invoke(observed.normal, 15, 2)
  equal(calls[#calls], "leave", "leaving algorithm five disconnects the adapter")
end)

test("transport-gated lane selection leaves the displayed lane unchanged", function()
  local page, observed = trigger_page_context()
  local selected = "BD"
  page.set_rhythm_doctor({
    enter = function() end,
    select_lane = function(_, lane) selected = lane; return {code = "STOP_SEQUENCER"} end,
    screen_model = function() return {worker_ready = false} end,
  })
  page.register_press(); invoke(observed.normal, 16, 2)
  invoke(observed.normal, 7, 2)
  equal(selected, "BASS", "adapter must receive the attempted lane for transport gating")
  equal(page.get_rhythm_doctor_lane(), "BD", "gated lane must not alter player-visible selection")
  equal(observed.tips[#observed.tips], "STOP SEQUENCER")
end)

test("K2 and K3 reach Rhythm Doctor only while algorithm five is selected", function()
  local calls, dirty, texts, ui_draw = {}, 0, {}, nil
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
    }
    return assert(modules[path], path)
  end
  draw = {register_ui = function(_, _, fn) ui_draw = fn end}
  screen = {level = function() end, move = function() end, text = function(value) texts[#texts + 1] = value end}
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

test("worker-host cleanup removes only its stale publication files", function()
  local Host = require("rhythm_doctor.worker_host")
  local commands = {}
  local host = Host.new({code_root = "/code/mosaic", runtime_root = "/data/rd",
    execute = function(command) commands[#commands + 1] = command; return true end,
    read_line = function(path) return path:match("/pid$") and "42" or nil end,
    transport_factory = function() error("not reached") end})
  host:close()
  check(commands[1]:find("/data/rd/cancel", 1, true))
  equal(commands[2], "kill 42 2>/dev/null")
  check(commands[3]:find("rm -f '/data/rd/socket' '/data/rd/pid' '/data/rd/error'", 1, true),
        "cleanup must remove only its exact stale socket/PID/error publications")
end)

if #failures > 0 then io.stderr:write(table.concat(failures, "\n") .. "\n"); os.exit(1) end
print("rhythm_doctor app surface: " .. tests .. " tests passed")
