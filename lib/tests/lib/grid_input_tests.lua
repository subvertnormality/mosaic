-- Unit tests for the REAL lib/m_grid.lua (grid key state machine, menu row,
-- redraw, disconnect) and the REAL lib/press.lua (handler registration and
-- dispatch by page).
--
-- The rest of the suite uses the global m_grid stub from
-- lib/tests/helpers/globals.lua. These tests never touch that stub: each test
-- loads fresh copies of the real modules with dofile (so their file-local
-- pressed_keys / press order / dual flag / handler tables start empty),
-- replaces every collaborator global with a recording fake, and restores every
-- replaced global afterwards even when an assertion fails.
--
-- Clocks are driven explicitly: the fake clock.run starts the long-press
-- coroutine immediately (as norns does) and it stops at clock.sleep; a test
-- "fires" a key's timer by resuming that coroutine, i.e. the sleep elapsed.
--
-- Every collaborator call is appended to one event log, so the tests assert
-- the exact calls, their arguments and their order.
--
-- README references are to README.md line numbers:
--   316 MIDI panic (hold a non-selected page button; releasing does not change page)
--   397 trig length (press and hold a trig, then choose its ending step)
--   722 channel length (hold start, press and release end, release start)
--   738 hold a channel select button for one second
--   903 song slot copy (hold source, then destination)
--   1066 stop safety (play/stop stops only on long press or with K1 held)
-- Press order for song slot copy: SEM-016 in docs/testing/decisions.md.

local ROOT = "../../../mosaic/lib/"

local SAVED_GLOBALS = {
  "include", "press", "draw", "grid_abstraction",
  "channel_edit_page", "song_edit_page", "scale_edit_page",
  "trigger_edit_page", "note_edit_page", "velocity_edit_page",
  "g", "grid", "grid_connected", "clock", "fn", "program", "params",
  "m_clock", "tooltip", "recorder", "save_confirm", "autosave_reset",
  "is_key1_down", "print", "button"
}

local PAGE_GLOBALS = {
  "channel_edit_page", "scale_edit_page", "trigger_edit_page",
  "note_edit_page", "velocity_edit_page", "song_edit_page"
}

-- Page numbers (lib/pages/pages.lua).
local CHANNEL, SCALE, TRIG, NOTE, VELOCITY, SONG = 2, 3, 4, 5, 6, 7

local function fmt(name, ...)
  local parts = {}
  for i = 1, select("#", ...) do parts[i] = tostring((select(i, ...))) end
  return name .. "(" .. table.concat(parts, ",") .. ")"
end

local function concat(...)
  local out = {}
  for _, list in ipairs({...}) do
    for _, v in ipairs(list) do out[#out + 1] = v end
  end
  return out
end

-- Run body with every SAVED_GLOBALS entry (and the pages mapping fields that
-- pages.initialise_page_controller_mappings writes) restored afterwards.
local function with_saved_globals(body)
  local saved = {}
  for i, name in ipairs(SAVED_GLOBALS) do saved[i] = rawget(_G, name) end
  local saved_ptc = pages.page_to_controller_mappings
  local saved_gmb = pages.grid_menu_buttons_to_controller_mappings
  local ok, err = pcall(body)
  for i, name in ipairs(SAVED_GLOBALS) do rawset(_G, name, saved[i]) end
  pages.page_to_controller_mappings = saved_ptc
  pages.grid_menu_buttons_to_controller_mappings = saved_gmb
  if not ok then error(err, 0) end
end

local function fake_clock(env)
  local c = {runs = {}}
  function c.run(f, ...)
    local entry = {f = f, args = {...}, co = coroutine.create(f)}
    c.runs[#c.runs + 1] = entry
    local name = (env.m_grid and f == env.m_grid.long_press) and "long_press" or "?"
    env.record("clock.run", name, ...)
    local ok, err = coroutine.resume(entry.co, ...)
    assert(ok, err)
    return #c.runs
  end
  function c.sleep(...)
    env.record("clock.sleep", ...)
    coroutine.yield()
  end
  function c.cancel(id)
    env.record("clock.cancel", id)
    if c.runs[id] then c.runs[id].cancelled = true end
  end
  c.transport = {}
  function c.transport.stop(self)
    assert(self == c.transport, "clock.transport:stop must be a method call")
    env.record("clock.transport:stop")
    env.playing = false
  end
  return c
end

-- The sleep of clock id elapsed: resume the long-press coroutine.
local function fire(env, id)
  local entry = env.clock.runs[id]
  assert(entry ~= nil, "no clock " .. tostring(id))
  assert(not entry.cancelled, "clock " .. id .. " was cancelled")
  assert(coroutine.status(entry.co) == "suspended", "clock " .. id .. " is not sleeping")
  local ok, err = coroutine.resume(entry.co)
  assert(ok, err)
end

local function recording_press(env)
  local p = {registered = {}}
  for _, kind in ipairs({"register", "register_long", "register_dual", "register_pre", "register_post"}) do
    p.registered[kind] = {}
    p[kind] = function(self, page, f)
      assert(self == p, "press:" .. kind .. " must be a method call")
      local list = p.registered[kind]
      list[#list + 1] = {page = page, f = f}
      env.record("press:" .. kind, page)
    end
  end
  for _, kind in ipairs({"handle", "handle_pre", "handle_post", "handle_long", "handle_dual"}) do
    p[kind] = function(self, ...)
      assert(self == p, "press:" .. kind .. " must be a method call")
      env.record("press:" .. kind, ...)
      if env.on_press then env.on_press(kind, ...) end
    end
  end
  return p
end

local function fake_page(env, name)
  local page = {}
  for _, method in ipairs({"init", "register_draws", "refresh", "refresh_faders"}) do
    page[method] = function(...)
      assert(select("#", ...) == 0, name .. "." .. method .. " takes no arguments")
      env.record(name .. "." .. method)
    end
  end
  page.register_press = function(...)
    assert(select("#", ...) == 0)
    env.record(name .. ".register_press")
    if env.on_register_press then env.on_register_press(name) end
  end
  return page
end

-- Build the fakes, load the real module(s), run body(env).
-- opts.real_press: load the real press.lua instead of the recording fake.
-- opts.init == false: do not call m_grid.init.  opts.keep_init_log: keep log.
-- opts.page: initially selected page (default TRIG).
-- opts.on_register_press(env, page_name): register page handlers on press.
local function with_grid(opts, body)
  with_saved_globals(function()
    local env = {
      log = {}, selected_page = opts.page or TRIG, dirty_grid = false,
      playing = false, blink = false, params = {record = 1, stop_safety = 1},
      program = {selected_channel = 1, previous_channel = 1}, draws = {}
    }
    function env.record(...) env.log[#env.log + 1] = fmt(...) end
    if opts.setup then opts.setup(env) end

    local real_fn = fn
    fn = setmetatable({
      dirty_grid = function(...)
        if select("#", ...) == 0 then env.record("fn.dirty_grid"); return env.dirty_grid end
        env.record("fn.dirty_grid", ...); env.dirty_grid = (...); return env.dirty_grid
      end,
      dirty_screen = function(...)
        env.record("fn.dirty_screen", ...); return (...)
      end
    }, {__index = real_fn})

    env.clock = fake_clock(env)
    clock = env.clock
    program = {
      get = function() return env.program end,
      get_selected_page = function() return env.selected_page end,
      set_selected_page = function(p) env.record("program.set_selected_page", p); env.selected_page = p end,
      get_blink_state = function() return env.blink end
    }
    params = {
      get = function(self, k) assert(self == params); return env.params[k] end,
      set = function(self, k, v) assert(self == params); env.record("params:set", k, v); env.params[k] = v end
    }
    m_clock = {
      is_playing = function() return env.playing end,
      start = function(self) assert(self == m_clock); env.record("m_clock:start"); env.playing = true end,
      panic = function(...) env.record("m_clock.panic", ...) end
    }
    tooltip = {show = function(self, msg) assert(self == tooltip); env.record("tooltip:show", msg) end}
    recorder = {clear_all_trig_lock_dirty = function(...) env.record("recorder.clear_all_trig_lock_dirty", ...) end}
    save_confirm = {cancel = function(...) env.record("save_confirm.cancel", ...) end}
    autosave_reset = function(...) env.record("autosave_reset", ...) end
    print = function(...) env.record("print", ...) end
    is_key1_down = false
    grid_connected = nil

    env.g = {
      all = function(self, v) assert(self == env.g); env.record("g:all", v) end,
      refresh = function(self) assert(self == env.g); env.record("g:refresh") end
    }
    env.vports = {env.g, {name = "vport2"}}
    g = env.g
    grid = {connect = function(port) env.record("grid.connect", port); return env.vports[port] end}

    env.pages = {}
    for _, name in ipairs(PAGE_GLOBALS) do env.pages[name] = fake_page(env, name) end
    env.draw = {
      register_grid = function(self, name, f)
        assert(self == env.draw); env.draws[name] = f; env.record("draw:register_grid", name)
      end,
      handle_grid = function(self, page) assert(self == env.draw); env.record("draw:handle_grid", page) end
    }
    env.grid_abstraction = {
      init = function(...) env.record("grid_abstraction.init", ...) end,
      led = function(x, y, v) env.record("led", x, y, v) end
    }
    env.press = opts.real_press and dofile(ROOT .. "press.lua") or recording_press(env)
    if opts.on_register_press then
      env.on_register_press = function(name) opts.on_register_press(env, name) end
    end

    local modules = {
      ["mosaic/lib/controls/fader"] = {},
      ["mosaic/lib/controls/sequencer"] = {},
      ["mosaic/lib/controls/button"] = dofile(ROOT .. "controls/button.lua"),
      ["mosaic/lib/press"] = env.press,
      ["mosaic/lib/draw"] = env.draw,
      ["mosaic/lib/grid_abstraction"] = env.grid_abstraction
    }
    for _, name in ipairs(PAGE_GLOBALS) do
      modules["mosaic/lib/pages/" .. name .. "/" .. name] = env.pages[name]
    end
    include = function(path)
      local m = modules[path]
      assert(m ~= nil, "unexpected include " .. tostring(path))
      return m
    end

    env.m_grid = dofile(ROOT .. "m_grid.lua")
    if opts.init ~= false then env.m_grid.init() end
    if not opts.keep_init_log then env.log = {} end
    body(env, env.m_grid)
  end)
end

local function key(env, x, y, z) env.g.key(x, y, z) end

-- Expected log fragments for the recording press on page p.
local function pressed(p, x, y)
  return {fmt("press:handle_pre", p, x, y), "fn.dirty_grid(true)", "fn.dirty_screen(true)",
          fmt("clock.run", "long_press", x, y), "clock.sleep(1)"}
end
local function short(p, x, y)
  return {fmt("press:handle", p, x, y), "fn.dirty_grid(true)", "fn.dirty_screen(true)"}
end
local function dual(p, x, y, x2, y2)
  return {fmt("press:handle_dual", p, x, y, x2, y2), "fn.dirty_grid(true)", "fn.dirty_screen(true)"}
end
local function post(p, x, y)
  return {fmt("press:handle_post", p, x, y), "fn.dirty_grid(true)", "fn.dirty_screen(true)"}
end
local function long(p, x, y)
  return {fmt("press:handle_long", p, x, y), "fn.dirty_grid(true)"}
end
local function cancel(id) return {fmt("clock.cancel", id)} end

local function take_log(env)
  local log = env.log
  env.log = {}
  return log
end

-- LED levels of the menu row as drawn by the registered "menu" draw function.
local function menu_leds(env)
  local before = env.log
  env.log = {}
  env.draws["menu"]()
  local leds = env.log
  env.log = before
  return leds
end

---------------------------------------------------------------------------
-- Load, init and the harness itself
---------------------------------------------------------------------------

function test_grid_input_load_and_init_call_collaborators_in_order()
  with_grid({keep_init_log = true}, function(env, m)
    luaunit.assert_equals(env.log, {
      "grid_abstraction.init()",
      "channel_edit_page.init()", "scale_edit_page.init()", "trigger_edit_page.init()",
      "note_edit_page.init()", "velocity_edit_page.init()", "song_edit_page.init()",
      "trigger_edit_page.register_draws()", "note_edit_page.register_draws()",
      "velocity_edit_page.register_draws()", "channel_edit_page.register_draws()",
      "scale_edit_page.register_draws()", "song_edit_page.register_draws()",
      "draw:register_grid(menu)",
      "channel_edit_page.register_press()", "scale_edit_page.register_press()",
      "trigger_edit_page.register_press()", "note_edit_page.register_press()",
      "velocity_edit_page.register_press()", "song_edit_page.register_press()",
      "press:register(menu)", "press:register(menu)",
      "press:register_long(menu)", "press:register_long(menu)"
    }) -- characterisation
    -- m_grid publishes its collaborators as globals for the page modules.
    luaunit.assert_is(press, env.press)
    luaunit.assert_is(draw, env.draw)
    luaunit.assert_is(grid_abstraction, env.grid_abstraction)
    for _, name in ipairs(PAGE_GLOBALS) do luaunit.assert_is(_G[name], env.pages[name]) end
    -- init wires the page-number -> controller map the menu handler refreshes through.
    luaunit.assert_is(pages.page_to_controller_mappings[TRIG], env.pages.trigger_edit_page)
    luaunit.assert_is(pages.page_to_controller_mappings[SONG], env.pages.song_edit_page)
    -- Per-key timer and long-press tables cover the 16x8 grid.
    for x = 1, 16 do
      for y = 1, 8 do
        luaunit.assert_nil(m.counter[x][y])
        luaunit.assert_equals(m.long_press_active[x][y], {}) -- characterisation (table, not false)
      end
    end
    luaunit.assert_nil(m.counter[17])
    luaunit.assert_equals(m.toggled, {})
    luaunit.assert_true(m.disconnect_dismissed)
    luaunit.assert_is_function(env.g.key)
    luaunit.assert_is_function(env.g.remove)
    luaunit.assert_equals(m.get_pressed_keys(), {})
  end)
end

function test_grid_input_init_sets_menu_leds_for_initial_state()
  with_grid({page = NOTE, setup = function(env)
    env.playing = true
    env.params.record = 2
    env.blink = true
  end}, function(env)
    luaunit.assert_equals(menu_leds(env), {"led(1,8,-4)", "led(2,8,-4)", "led(5,8,10)", "led(3,8,2)", "led(4,8,2)", "led(6,8,2)"})
  end)
end

function test_grid_input_restores_replaced_globals_even_when_the_body_fails()
  local before = {}
  for i, name in ipairs(SAVED_GLOBALS) do before[i] = rawget(_G, name) end
  local stub = m_grid
  local ok, err = pcall(with_grid, {}, function(env)
    luaunit.assert_is(press, env.press)
    error("deliberate")
  end)
  luaunit.assert_false(ok)
  luaunit.assert_str_contains(tostring(err), "deliberate")
  for i, name in ipairs(SAVED_GLOBALS) do luaunit.assert_is(rawget(_G, name), before[i], name) end
  luaunit.assert_is(m_grid, stub)
  luaunit.assert_equals(m_grid.get_pressed_keys(), {})
end

function test_grid_input_initial_channel_sync_depends_on_selected_page()
  -- Not on the scale page: channel 17 is swapped back to the previous channel.
  with_grid({page = TRIG, setup = function(env)
    env.program = {selected_channel = 17, previous_channel = 5}
  end}, function(env)
    luaunit.assert_equals(env.program, {selected_channel = 5, previous_channel = 5})
  end)
  -- On the scale page: the global scale channel 17 is selected.
  with_grid({page = SCALE, setup = function(env)
    env.program = {selected_channel = 9, previous_channel = 2}
  end}, function(env)
    luaunit.assert_equals(env.program, {selected_channel = 17, previous_channel = 9})
  end)
  -- previous_channel 17 is never a valid return target; it becomes 1.
  with_grid({page = TRIG, setup = function(env)
    env.program = {selected_channel = 17, previous_channel = 17}
  end}, function(env)
    luaunit.assert_equals(env.program, {selected_channel = 1, previous_channel = 1})
  end)
  -- No previous channel recorded: fall back to channel 1.
  with_grid({page = TRIG, setup = function(env)
    env.program = {selected_channel = 17}
  end}, function(env)
    luaunit.assert_equals(env.program, {selected_channel = 1})
  end)
end

---------------------------------------------------------------------------
-- Key state machine: single keys
---------------------------------------------------------------------------

function test_grid_input_key_down_records_key_and_starts_one_second_timer()
  with_grid({}, function(env, m)
    local seen
    env.on_press = function(kind) if kind == "handle_pre" then seen = {table.unpack(m.get_pressed_keys()[1])} end end
    key(env, 3, 2, 1)
    luaunit.assert_equals(take_log(env), pressed(TRIG, 3, 2)) -- 738: long press is one second
    luaunit.assert_equals(seen, {3, 2}) -- characterisation: pre handlers already see the key held
    luaunit.assert_equals(m.get_pressed_keys(), {{3, 2}})
    luaunit.assert_equals(m.counter[3][2], 1)
    luaunit.assert_is(env.clock.runs[1].f, m.long_press)
    luaunit.assert_equals(env.clock.runs[1].args, {3, 2})
    luaunit.assert_is(m.get_pressed_keys(), m.get_pressed_keys()) -- characterisation: live table
  end)
end

function test_grid_input_short_press_cancels_timer_then_short_then_post()
  with_grid({}, function(env, m)
    key(env, 3, 2, 1)
    take_log(env)
    key(env, 3, 2, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(1), short(TRIG, 3, 2), post(TRIG, 3, 2)))
    luaunit.assert_equals(m.get_pressed_keys(), {})
    luaunit.assert_true(env.clock.runs[1].cancelled)
    luaunit.assert_equals(m.counter[3][2], 1) -- characterisation: the id is never cleared
  end)
end

function test_grid_input_handlers_receive_the_page_selected_at_each_event()
  with_grid({}, function(env)
    key(env, 3, 2, 1)
    env.selected_page = NOTE
    key(env, 3, 2, 0)
    luaunit.assert_equals(env.log, concat(pressed(TRIG, 3, 2), cancel(1), short(NOTE, 3, 2), post(NOTE, 3, 2)))
    env.log = {}
    key(env, 4, 1, 1)
    env.selected_page = SONG
    fire(env, 2)
    luaunit.assert_equals(env.log, concat(pressed(NOTE, 4, 1), long(SONG, 4, 1)))
  end)
end

function test_grid_input_long_press_fires_after_sleep_and_suppresses_short_press()
  with_grid({}, function(env, m)
    key(env, 3, 2, 1)
    take_log(env)
    luaunit.assert_equals(m.long_press_active[3][2], {}) -- not yet fired
    fire(env, 1)
    luaunit.assert_equals(take_log(env), long(TRIG, 3, 2)) -- characterisation: no dirty_screen
    luaunit.assert_true(m.long_press_active[3][2])
    key(env, 3, 2, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(1), post(TRIG, 3, 2)))
    luaunit.assert_false(m.long_press_active[3][2])
    -- The flag is consumed: the next tap of the same key is a short press again.
    key(env, 3, 2, 1)
    key(env, 3, 2, 0)
    luaunit.assert_equals(take_log(env), concat(pressed(TRIG, 3, 2), cancel(2), short(TRIG, 3, 2), post(TRIG, 3, 2)))
  end)
end

function test_grid_input_release_before_threshold_cancels_long_press()
  with_grid({}, function(env)
    key(env, 3, 2, 1)
    key(env, 3, 2, 0)
    luaunit.assert_true(env.clock.runs[1].cancelled)
    luaunit.assert_false(pcall(fire, env, 1))
  end)
end

function test_grid_input_each_key_has_its_own_timer()
  with_grid({}, function(env, m)
    key(env, 3, 2, 1)
    key(env, 9, 5, 1)
    luaunit.assert_equals(m.counter[3][2], 1)
    luaunit.assert_equals(m.counter[9][5], 2)
    take_log(env)
    fire(env, 2)
    luaunit.assert_equals(take_log(env), long(TRIG, 9, 5))
    luaunit.assert_true(m.long_press_active[9][5])
    luaunit.assert_equals(m.long_press_active[3][2], {})
    fire(env, 1)
    luaunit.assert_equals(take_log(env), long(TRIG, 3, 2))
  end)
end

function test_grid_input_pressed_keys_are_kept_in_press_order()
  with_grid({}, function(env, m)
    key(env, 5, 4, 1)
    key(env, 1, 3, 1)
    key(env, 16, 8, 1)
    luaunit.assert_equals(m.get_pressed_keys(), {{5, 4}, {1, 3}, {16, 8}})
    key(env, 1, 3, 0)
    luaunit.assert_equals(m.get_pressed_keys(), {{5, 4}, {16, 8}})
    key(env, 1, 3, 1)
    luaunit.assert_equals(m.get_pressed_keys(), {{5, 4}, {16, 8}, {1, 3}})
  end)
end

function test_grid_input_z_values_other_than_zero_and_one_are_ignored()
  with_grid({}, function(env, m)
    key(env, 3, 2, 2)
    key(env, 3, 2, -1)
    luaunit.assert_equals(env.log, {})
    luaunit.assert_equals(m.get_pressed_keys(), {})
    luaunit.assert_nil(m.counter[3][2])
  end)
end

function test_grid_input_release_of_never_pressed_key_only_posts()
  with_grid({}, function(env, m)
    key(env, 3, 2, 0)
    luaunit.assert_equals(take_log(env), post(TRIG, 3, 2))
    -- With another key held it is not a two-key gesture either.
    key(env, 7, 1, 1)
    take_log(env)
    key(env, 3, 2, 0)
    luaunit.assert_equals(take_log(env), post(TRIG, 3, 2))
    luaunit.assert_equals(m.get_pressed_keys(), {{7, 1}})
    key(env, 7, 1, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(1), short(TRIG, 7, 1), post(TRIG, 7, 1)))
  end)
end

function test_grid_input_unpaired_release_of_previously_tapped_key_replays_short_press()
  with_grid({}, function(env)
    key(env, 3, 2, 1)
    key(env, 3, 2, 0)
    take_log(env)
    key(env, 3, 2, 0)
    -- characterisation (suspected defect: m_grid.counter[x][y] is never cleared
    -- on release (lib/m_grid.lua:248), so a second z=0 with no z=1 re-cancels the
    -- dead clock and dispatches another short press)
    luaunit.assert_equals(take_log(env), concat(cancel(1), short(TRIG, 3, 2), post(TRIG, 3, 2)))
  end)
end

function test_grid_input_key_outside_16_columns_raises()
  with_grid({}, function(env, m)
    luaunit.assert_false(pcall(key, env, 17, 1, 1)) -- characterisation: counter has columns 1..16
    luaunit.assert_equals(m.get_pressed_keys(), {{17, 1}}) -- characterisation: inserted before the error
  end)
end

---------------------------------------------------------------------------
-- Key state machine: two-key gestures (README 397, 722, 903)
---------------------------------------------------------------------------

function test_grid_input_dual_press_passes_held_key_then_released_key()
  -- README 722: hold the start, press and release the end, then release the start.
  with_grid({}, function(env, m)
    key(env, 3, 4, 1)
    key(env, 9, 4, 1)
    take_log(env)
    key(env, 9, 4, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(2), cancel(1), dual(TRIG, 3, 4, 9, 4), post(TRIG, 9, 4)))
    luaunit.assert_equals(m.get_pressed_keys(), {{3, 4}})
    luaunit.assert_true(env.clock.runs[1].cancelled) -- the held key can no longer long press
    key(env, 3, 4, 0)
    -- Releasing the start key ends the gesture without a short press.
    luaunit.assert_equals(take_log(env), concat(cancel(1), post(TRIG, 3, 4)))
    luaunit.assert_equals(m.get_pressed_keys(), {})
    -- The gesture flag is cleared: the next tap is a short press.
    key(env, 3, 4, 1)
    key(env, 3, 4, 0)
    luaunit.assert_equals(take_log(env), concat(pressed(TRIG, 3, 4), cancel(3), short(TRIG, 3, 4), post(TRIG, 3, 4)))
  end)
end

function test_grid_input_first_pressed_released_first_passes_still_held_key_first()
  -- SEM-016: m_grid always resolves at the first release, the still-held key
  -- first; pressed_after lets song slot copy recover press order (README 903).
  with_grid({}, function(env, m)
    key(env, 2, 1, 1) -- source slot
    key(env, 6, 1, 1) -- destination slot
    take_log(env)
    key(env, 2, 1, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(1), cancel(2), dual(TRIG, 6, 1, 2, 1), post(TRIG, 2, 1)))
    luaunit.assert_true(m.pressed_after(6, 1, 2, 1))
    luaunit.assert_false(m.pressed_after(2, 1, 6, 1))
    key(env, 6, 1, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(2), post(TRIG, 6, 1)))
  end)
end

function test_grid_input_three_keys_pair_each_release_with_first_held_key()
  with_grid({}, function(env)
    key(env, 1, 4, 1)
    key(env, 2, 4, 1)
    key(env, 3, 4, 1)
    take_log(env)
    key(env, 3, 4, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(3), cancel(1), dual(TRIG, 1, 4, 3, 4), post(TRIG, 3, 4)))
    key(env, 2, 4, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(2), cancel(1), dual(TRIG, 1, 4, 2, 4), post(TRIG, 2, 4)))
    key(env, 1, 4, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(1), post(TRIG, 1, 4)))
  end)
  -- Middle key first: the first key then pairs with the last remaining key.
  with_grid({}, function(env)
    key(env, 1, 4, 1)
    key(env, 2, 4, 1)
    key(env, 3, 4, 1)
    take_log(env)
    key(env, 2, 4, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(2), cancel(1), dual(TRIG, 1, 4, 2, 4), post(TRIG, 2, 4)))
    key(env, 1, 4, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(1), cancel(3), dual(TRIG, 3, 4, 1, 4), post(TRIG, 1, 4))) -- characterisation
    key(env, 3, 4, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(3), post(TRIG, 3, 4)))
  end)
end

function test_grid_input_held_key_long_press_does_not_block_a_later_dual()
  -- README 722: a step held a long time stays available for a later end-step press.
  with_grid({}, function(env, m)
    key(env, 3, 4, 1)
    fire(env, 1)
    take_log(env)
    key(env, 9, 4, 1)
    key(env, 9, 4, 0)
    luaunit.assert_equals(take_log(env), concat(pressed(TRIG, 9, 4), cancel(2), cancel(1), dual(TRIG, 3, 4, 9, 4), post(TRIG, 9, 4)))
    key(env, 3, 4, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(1), post(TRIG, 3, 4)))
    luaunit.assert_false(m.long_press_active[3][4])
    -- The gesture flag is reset once no key is held, even though the last
    -- release took the long-press branch: the next tap is a short press.
    key(env, 5, 5, 1)
    key(env, 5, 5, 0)
    luaunit.assert_equals(take_log(env), concat(pressed(TRIG, 5, 5), cancel(3), short(TRIG, 5, 5), post(TRIG, 5, 5)))
  end)
end

function test_grid_input_released_key_long_pressed_is_not_a_dual()
  with_grid({}, function(env, m)
    key(env, 3, 4, 1)
    key(env, 9, 4, 1)
    fire(env, 2)
    take_log(env)
    key(env, 9, 4, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(2), post(TRIG, 9, 4)))
    luaunit.assert_false(m.long_press_active[9][4])
    key(env, 3, 4, 0)
    -- characterisation: the first key then completes as its own short press
    luaunit.assert_equals(take_log(env), concat(cancel(1), short(TRIG, 3, 4), post(TRIG, 3, 4)))
  end)
end

function test_grid_input_gesture_continues_while_first_key_stays_held()
  with_grid({}, function(env)
    key(env, 3, 4, 1)
    key(env, 9, 4, 1)
    key(env, 9, 4, 0)
    take_log(env)
    key(env, 12, 4, 1)
    key(env, 12, 4, 0)
    luaunit.assert_equals(take_log(env), concat(pressed(TRIG, 12, 4), cancel(3), cancel(1), dual(TRIG, 3, 4, 12, 4), post(TRIG, 12, 4)))
    key(env, 3, 4, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(1), post(TRIG, 3, 4)))
  end)
end

function test_grid_input_duplicate_key_down_overwrites_timer_and_leaves_stale_key()
  with_grid({}, function(env, m)
    key(env, 3, 2, 1)
    key(env, 3, 2, 1)
    luaunit.assert_equals(take_log(env), concat(pressed(TRIG, 3, 2), pressed(TRIG, 3, 2)))
    -- characterisation (suspected defect: lib/m_grid.lua:237-241 neither checks
    -- for an already-held key nor cancels its running timer)
    luaunit.assert_equals(m.get_pressed_keys(), {{3, 2}, {3, 2}})
    luaunit.assert_equals(m.counter[3][2], 2)
    luaunit.assert_nil(env.clock.runs[1].cancelled)
    key(env, 3, 2, 0)
    -- characterisation (suspected defect: the stale duplicate is taken as the
    -- held key, so one physical key resolves as a two-key gesture with itself)
    luaunit.assert_equals(take_log(env), concat(cancel(2), cancel(2), dual(TRIG, 3, 2, 3, 2), post(TRIG, 3, 2)))
    luaunit.assert_equals(m.get_pressed_keys(), {{3, 2}})
    -- characterisation (suspected defect: the orphaned first timer still fires
    -- a long press after the key was released)
    fire(env, 1)
    luaunit.assert_equals(take_log(env), long(TRIG, 3, 2))
    key(env, 3, 2, 0)
    luaunit.assert_equals(take_log(env), concat(cancel(2), post(TRIG, 3, 2)))
    luaunit.assert_equals(m.get_pressed_keys(), {})
    key(env, 5, 5, 1)
    key(env, 5, 5, 0)
    luaunit.assert_equals(take_log(env), concat(pressed(TRIG, 5, 5), cancel(3), short(TRIG, 5, 5), post(TRIG, 5, 5)))
  end)
end

---------------------------------------------------------------------------
-- Press order (SEM-016)
---------------------------------------------------------------------------

function test_grid_input_pressed_after_compares_press_order()
  with_grid({}, function(env, m)
    luaunit.assert_false(m.pressed_after(1, 1, 2, 1)) -- neither pressed
    key(env, 1, 1, 1)
    luaunit.assert_false(m.pressed_after(1, 1, 2, 1)) -- second never pressed
    luaunit.assert_false(m.pressed_after(2, 1, 1, 1)) -- first never pressed
    luaunit.assert_false(m.pressed_after(1, 1, 1, 1)) -- same key
    key(env, 2, 1, 1)
    luaunit.assert_true(m.pressed_after(2, 1, 1, 1))
    luaunit.assert_false(m.pressed_after(1, 1, 2, 1))
    -- The key coordinates are distinct: (1,12) and (11,2) do not collide.
    key(env, 1, 12, 1)
    key(env, 11, 2, 1)
    luaunit.assert_true(m.pressed_after(11, 2, 1, 12))
    luaunit.assert_false(m.pressed_after(1, 12, 11, 2))
  end)
end

function test_grid_input_pressed_after_uses_latest_press_and_survives_release()
  with_grid({}, function(env, m)
    key(env, 1, 1, 1)
    key(env, 2, 1, 1)
    key(env, 1, 1, 0)
    key(env, 1, 1, 1) -- re-pressed: now later than (2,1)
    luaunit.assert_true(m.pressed_after(1, 1, 2, 1))
    luaunit.assert_false(m.pressed_after(2, 1, 1, 1))
    key(env, 1, 1, 0)
    key(env, 2, 1, 0)
    -- characterisation: order is never cleared on release, so it still
    -- answers for keys that are no longer held
    luaunit.assert_true(m.pressed_after(1, 1, 2, 1))
  end)
end

---------------------------------------------------------------------------
-- Disconnect and reconnect
---------------------------------------------------------------------------

-- Human decision 2026-09-11 (suspected-defects S29; bugs.json grid-disconnect-held-keys): a
-- disconnected grid sends no key-ups, so disconnect forgets the held keys and cancels their
-- long-press timers. Fixed defensively: no behaviour reproduction exists, by decision (an
-- emulator probe showed no user-visible effect), so these units are the regression.
function test_grid_input_remove_clears_held_keys_and_cancels_their_timers()
  with_grid({}, function(env, m)
    local live = m.get_pressed_keys()
    key(env, 3, 2, 1)
    key(env, 5, 2, 1)
    take_log(env)
    env.g.remove()
    luaunit.assert_equals(take_log(env), concat(cancel(1), cancel(2), {"print(Grid disconnected)"}))
    luaunit.assert_equals(m.get_pressed_keys(), {})
    luaunit.assert_is(m.get_pressed_keys(), live) -- still the live table
    luaunit.assert_true(env.clock.runs[1].cancelled)
    luaunit.assert_true(env.clock.runs[2].cancelled)
    -- A later single tap is a short press, not a two-key gesture with a stale key.
    key(env, 7, 2, 1)
    key(env, 7, 2, 0)
    luaunit.assert_equals(take_log(env), concat(pressed(TRIG, 7, 2), cancel(3), short(TRIG, 7, 2), post(TRIG, 7, 2)))
  end)
end

function test_grid_input_remove_forgets_a_fired_long_press()
  with_grid({}, function(env, m)
    key(env, 3, 2, 1)
    fire(env, 1)
    take_log(env)
    env.g.remove()
    luaunit.assert_equals(take_log(env), concat(cancel(1), {"print(Grid disconnected)"}))
    luaunit.assert_false(m.long_press_active[3][2])
    -- The next tap of that key after reconnecting is a short press, not swallowed.
    key(env, 3, 2, 1)
    key(env, 3, 2, 0)
    luaunit.assert_equals(take_log(env), concat(pressed(TRIG, 3, 2), cancel(2), short(TRIG, 3, 2), post(TRIG, 3, 2)))
  end)
end

function test_grid_input_remove_ends_a_two_key_gesture_in_progress()
  with_grid({}, function(env, m)
    key(env, 5, 2, 1)
    key(env, 6, 2, 1)
    key(env, 6, 2, 0) -- two-key gesture; (5, 2) is still held
    take_log(env)
    env.g.remove()
    luaunit.assert_equals(take_log(env), concat(cancel(1), {"print(Grid disconnected)"}))
    -- The next single tap is a short press, not the tail of the old gesture.
    key(env, 7, 2, 1)
    key(env, 7, 2, 0)
    luaunit.assert_equals(take_log(env), concat(pressed(TRIG, 7, 2), cancel(3), short(TRIG, 7, 2), post(TRIG, 7, 2)))
  end)
end

function test_grid_input_reconnect_after_interrupted_dual_starts_a_clean_tap()
  -- Characterisation of grid.add: reconnecting to the same port reinstates the
  -- input path. The first tap must be a short press, never the missing release
  -- from the interrupted two-key gesture.
  with_grid({real_press = true, on_register_press = function(env, name)
    if name == "trigger_edit_page" then
      press:register("trigger_edit_page", function(...) env.record("trig.short", ...) end)
      press:register_dual("trigger_edit_page", function(...) env.record("trig.dual", ...) end)
    end
  end}, function(env, m)
    key(env, 5, 2, 1)
    key(env, 6, 2, 1)
    env.g.remove()
    take_log(env)
    grid.add({port = 1})
    key(env, 7, 2, 1)
    key(env, 7, 2, 0)
    local log = take_log(env)
    luaunit.assert_equals(log, {
      "grid.connect(1)", "fn.dirty_grid(true)",
      "fn.dirty_grid(true)", "fn.dirty_screen(true)", "clock.run(long_press,7,2)", "clock.sleep(1)",
      "clock.cancel(3)", "trig.short(7,2)", "save_confirm.cancel()", "autosave_reset()",
      "fn.dirty_grid(true)", "fn.dirty_screen(true)", "fn.dirty_grid(true)", "fn.dirty_screen(true)"
    })
    luaunit.assert_equals(m.get_pressed_keys(), {})
  end)
end

function test_grid_input_grid_add_connects_marks_connected_and_dirty()
  with_grid({}, function(env, m)
    key(env, 3, 2, 1)
    take_log(env)
    luaunit.assert_nil(grid_connected)
    grid.add({port = 2})
    luaunit.assert_equals(take_log(env), {"grid.connect(2)", "fn.dirty_grid(true)"})
    luaunit.assert_is(g, env.vports[2])
    luaunit.assert_true(grid_connected)
    luaunit.assert_equals(m.get_pressed_keys(), {{3, 2}}) -- characterisation
  end)
end

---------------------------------------------------------------------------
-- Redraw and refresh
---------------------------------------------------------------------------

function test_grid_input_grid_redraw_only_when_connected_and_dirty()
  with_grid({}, function(env, m)
    m.grid_redraw()
    luaunit.assert_equals(take_log(env), {}) -- not connected: dirty flag not even read
    grid_connected = false
    env.dirty_grid = true
    m.grid_redraw()
    luaunit.assert_equals(take_log(env), {})
    grid_connected = true
    env.dirty_grid = false
    m.grid_redraw()
    luaunit.assert_equals(take_log(env), {"fn.dirty_grid()"})
    env.dirty_grid = true
    env.selected_page = SONG
    m.grid_redraw()
    luaunit.assert_equals(take_log(env), {"fn.dirty_grid()", "g:all(0)", "draw:handle_grid(7)", "g:refresh()", "fn.dirty_grid(false)"})
    luaunit.assert_false(env.dirty_grid)
  end)
end

function test_grid_input_refresh_refreshes_pages_and_menu_state()
  with_grid({}, function(env, m)
    env.selected_page = SONG
    m.refresh()
    luaunit.assert_equals(take_log(env), {
      "channel_edit_page.refresh()", "song_edit_page.refresh()", "trigger_edit_page.refresh()",
      "note_edit_page.refresh()", "velocity_edit_page.refresh()"
    }) -- characterisation: the scale page is not refreshed
    luaunit.assert_equals(menu_leds(env), {"led(1,8,2)", "led(2,8,2)", "led(5,8,2)", "led(3,8,2)", "led(4,8,2)", "led(6,8,15)"})
  end)
end

function test_grid_input_menu_leds_follow_selected_page()
  local expected = {
    [CHANNEL]  = {5, 2, 15, 2, 2},
    [SCALE]    = {5, 2, 2, 15, 2},
    [TRIG]     = {5, 5, 2, 2, 2},
    [NOTE]     = {5, 10, 2, 2, 2},
    [VELOCITY] = {5, 15, 2, 2, 2},
    [SONG]     = {5, 2, 2, 2, 15}
  }
  with_grid({}, function(env, m)
    for page = CHANNEL, SONG do
      env.selected_page = page
      m.set_menu_button_state()
      local e = expected[page]
      luaunit.assert_equals(menu_leds(env), {
        "led(1,8,2)", "led(2,8,2)", fmt("led", e[1], 8, e[2]), fmt("led", 3, 8, e[3]),
        fmt("led", 4, 8, e[4]), fmt("led", 6, 8, e[5])
      }, "page " .. page)
    end
  end)
end

function test_grid_input_menu_play_and_record_blink_with_state()
  with_grid({}, function(env, m)
    env.blink = true
    env.playing = true
    m.set_menu_button_state()
    luaunit.assert_equals(menu_leds(env)[1], "led(1,8,-4)") -- characterisation: 2 - 6
    luaunit.assert_equals(menu_leds(env)[2], "led(2,8,2)")
    env.playing = false
    env.params.record = 2
    m.set_menu_button_state()
    luaunit.assert_equals(menu_leds(env)[1], "led(1,8,2)")
    luaunit.assert_equals(menu_leds(env)[2], "led(2,8,-4)")
    env.blink = false -- blink phase off: full level
    luaunit.assert_equals(menu_leds(env)[2], "led(2,8,2)")
  end)
end

---------------------------------------------------------------------------
-- Menu row handlers registered by m_grid.init
---------------------------------------------------------------------------

local function nav(env) return env.press.registered.register[1].f end
local function transport(env) return env.press.registered.register[2].f end
local function long_stop(env) return env.press.registered.register_long[1].f end
local function long_panic(env) return env.press.registered.register_long[2].f end

function test_grid_input_menu_handlers_are_registered_for_menu()
  with_grid({}, function(env)
    local r = env.press.registered
    luaunit.assert_equals(#r.register, 2)
    luaunit.assert_equals(#r.register_long, 2)
    luaunit.assert_equals({r.register[1].page, r.register[2].page, r.register_long[1].page, r.register_long[2].page},
      {"menu", "menu", "menu", "menu"})
    luaunit.assert_equals(#r.register_dual + #r.register_pre + #r.register_post, 0)
  end)
end

function test_grid_input_menu_nav_selects_page_and_refreshes()
  local cases = {
    -- from page, x, to page, refreshed controller, tooltip
    {TRIG, 3, CHANNEL, "channel_edit_page", "Channel Editor"},
    {TRIG, 4, SCALE, "scale_edit_page", "Scale Editor"},
    {TRIG, 6, SONG, "song_edit_page", "Song Editor"},
    {TRIG, 5, NOTE, "note_edit_page", "Pattern Note Editor"},
    {NOTE, 5, VELOCITY, "velocity_edit_page", "Pattern Velocity Editor"},
    {VELOCITY, 5, TRIG, "trigger_edit_page", "Pattern Trig Editor"},
    {CHANNEL, 5, TRIG, "trigger_edit_page", "Pattern Trig Editor"},
    {SCALE, 5, TRIG, "trigger_edit_page", "Pattern Trig Editor"},
    {SONG, 5, TRIG, "trigger_edit_page", "Pattern Trig Editor"}
  }
  for _, c in ipairs(cases) do
    with_grid({page = c[1]}, function(env)
      nav(env)(c[2], 8)
      luaunit.assert_equals(take_log(env), {
        fmt("program.set_selected_page", c[3]), c[4] .. ".refresh()", fmt("tooltip:show", c[5]),
        "fn.dirty_screen(true)", "fn.dirty_grid(true)"
      }, "from " .. c[1] .. " x " .. c[2])
      luaunit.assert_equals(env.selected_page, c[3])
    end)
  end
end

function test_grid_input_menu_nav_to_selected_page_only_refreshes()
  with_grid({page = CHANNEL}, function(env)
    nav(env)(3, 8)
    luaunit.assert_equals(take_log(env), {"channel_edit_page.refresh()", "tooltip:show(Channel Editor)", "fn.dirty_screen(true)", "fn.dirty_grid(true)"})
    luaunit.assert_equals(env.selected_page, CHANNEL)
    -- The menu row LEDs were recomputed for the selected page.
    luaunit.assert_equals(menu_leds(env)[4], "led(3,8,15)")
  end)
end

function test_grid_input_menu_nav_updates_menu_leds()
  with_grid({page = TRIG}, function(env)
    nav(env)(6, 8)
    luaunit.assert_equals(menu_leds(env), {"led(1,8,2)", "led(2,8,2)", "led(5,8,2)", "led(3,8,2)", "led(4,8,2)", "led(6,8,15)"})
  end)
end

function test_grid_input_menu_nav_ignores_keys_outside_page_buttons()
  with_grid({page = TRIG}, function(env)
    nav(env)(2, 8)
    nav(env)(7, 8)
    nav(env)(3, 7)
    nav(env)(1, 8)
    luaunit.assert_equals(env.log, {})
    luaunit.assert_equals(env.selected_page, TRIG)
  end)
end

function test_grid_input_menu_nav_syncs_channel_17_for_scale_page()
  with_grid({page = TRIG, setup = function(env) env.program = {selected_channel = 5, previous_channel = 1} end}, function(env)
    nav(env)(4, 8)
    luaunit.assert_equals(env.program, {selected_channel = 17, previous_channel = 5})
    nav(env)(4, 8) -- already on channel 17: previous is kept
    luaunit.assert_equals(env.program, {selected_channel = 17, previous_channel = 5})
    nav(env)(3, 8)
    luaunit.assert_equals(env.program, {selected_channel = 5, previous_channel = 5})
    env.program.selected_channel = 8
    nav(env)(6, 8) -- leaving to another non-scale page keeps the channel
    luaunit.assert_equals(env.program, {selected_channel = 8, previous_channel = 5})
  end)
end

function test_grid_input_menu_play_starts_when_stopped()
  with_grid({}, function(env)
    env.blink = true
    transport(env)(1, 8)
    luaunit.assert_equals(take_log(env), {"m_clock:start()", "tooltip:show(Starting playback)", "channel_edit_page.refresh_faders()"})
    luaunit.assert_equals(menu_leds(env)[1], "led(1,8,-4)") -- menu state recomputed after start
  end)
end

function test_grid_input_menu_play_stops_unless_stop_safety_holds_it()
  -- README 1066: with stop safety on, play/stop only stops on long press or with K1 held.
  local cases = {
    {1, false, true}, {1, true, true}, {2, false, false}, {2, true, true}
  }
  for _, c in ipairs(cases) do
    with_grid({}, function(env)
      env.params.stop_safety = c[1]
      is_key1_down = c[2]
      env.playing = true
      env.blink = true
      transport(env)(1, 8)
      if c[3] then
        luaunit.assert_equals(take_log(env), {"clock.transport:stop()", "tooltip:show(Stopping playback)",
          "recorder.clear_all_trig_lock_dirty()", "channel_edit_page.refresh_faders()"})
        luaunit.assert_equals(menu_leds(env)[1], "led(1,8,2)")
      else
        luaunit.assert_equals(take_log(env), {"channel_edit_page.refresh_faders()"})
        luaunit.assert_equals(menu_leds(env)[1], "led(1,8,-4)")
      end
    end)
  end
end

function test_grid_input_menu_record_toggles()
  with_grid({}, function(env)
    env.blink = true
    transport(env)(2, 8)
    luaunit.assert_equals(take_log(env), {"params:set(record,2)", "tooltip:show(Recording started)"})
    luaunit.assert_equals(menu_leds(env)[2], "led(2,8,-4)")
    transport(env)(2, 8)
    luaunit.assert_equals(take_log(env), {"params:set(record,1)", "tooltip:show(Recording stopped)", "recorder.clear_all_trig_lock_dirty()"})
    luaunit.assert_equals(menu_leds(env)[2], "led(2,8,2)")
  end)
end

function test_grid_input_menu_transport_ignores_other_keys()
  with_grid({}, function(env)
    transport(env)(1, 7)
    transport(env)(2, 7)
    transport(env)(3, 8)
    luaunit.assert_equals(env.log, {})
  end)
end

function test_grid_input_menu_long_play_stops_only_with_stop_safety()
  with_grid({}, function(env)
    env.playing = true
    env.blink = true
    long_stop(env)(1, 8)
    luaunit.assert_equals(take_log(env), {})
    env.params.stop_safety = 2
    long_stop(env)(1, 7)
    long_stop(env)(2, 8)
    luaunit.assert_equals(take_log(env), {})
    long_stop(env)(1, 8)
    luaunit.assert_equals(take_log(env), {"clock.transport:stop()", "recorder.clear_all_trig_lock_dirty()", "tooltip:show(Stopping playback)"})
    luaunit.assert_equals(menu_leds(env)[1], "led(1,8,2)")
  end)
end

function test_grid_input_menu_long_press_on_unselected_page_button_panics()
  -- README 316.
  local cases = {
    {TRIG, 3, true}, {TRIG, 4, true}, {TRIG, 5, false}, {TRIG, 6, true},
    {NOTE, 5, false}, {VELOCITY, 5, false}, {CHANNEL, 3, false}, {CHANNEL, 5, true},
    {SCALE, 4, false}, {SONG, 6, false}, {SONG, 3, true},
    {TRIG, 2, false}, {TRIG, 7, false}, {TRIG, 1, false}
  }
  for _, c in ipairs(cases) do
    with_grid({page = c[1]}, function(env)
      long_panic(env)(c[2], 8)
      luaunit.assert_equals(take_log(env), c[3] and {"tooltip:show(Midi Panic)", "m_clock.panic()"} or {},
        "page " .. c[1] .. " x " .. c[2])
    end)
  end
  with_grid({page = TRIG}, function(env)
    long_panic(env)(3, 7)
    luaunit.assert_equals(env.log, {})
  end)
end

---------------------------------------------------------------------------
-- Real m_grid + real press.lua end to end
---------------------------------------------------------------------------

local function register_trig_handlers(env, name)
  if name == "trigger_edit_page" then
    local function rec(label) return function(...) env.record(label, ...) end end
    press:register_pre("trigger_edit_page", rec("trig.pre"))
    press:register("trigger_edit_page", rec("trig.short1"))
    press:register_dual("trigger_edit_page", rec("trig.dual"))
    press:register_long("trigger_edit_page", rec("trig.long"))
    press:register_post("trigger_edit_page", rec("trig.post"))
    press:register("trigger_edit_page", rec("trig.short2"))
  elseif name == "note_edit_page" then
    local function rec(label) return function(...) env.record(label, ...) end end
    press:register("note_edit_page", rec("note.short"))
    press:register_pre("note_edit_page", rec("note.pre"))
  end
end

function test_grid_input_real_press_dispatches_tap_to_page_handlers_in_order()
  with_grid({real_press = true, on_register_press = register_trig_handlers}, function(env)
    luaunit.assert_is(press, env.press)
    key(env, 3, 2, 1)
    luaunit.assert_equals(take_log(env), {"trig.pre(3,2)", "fn.dirty_grid(true)", "fn.dirty_screen(true)",
      "clock.run(long_press,3,2)", "clock.sleep(1)"})
    key(env, 3, 2, 0)
    luaunit.assert_equals(take_log(env), {"clock.cancel(1)", "trig.short1(3,2)", "trig.short2(3,2)",
      "save_confirm.cancel()", "autosave_reset()", "fn.dirty_grid(true)", "fn.dirty_screen(true)",
      "trig.post(3,2)", "fn.dirty_grid(true)", "fn.dirty_screen(true)"})
  end)
end

function test_grid_input_real_press_dispatches_long_and_dual()
  with_grid({real_press = true, on_register_press = register_trig_handlers}, function(env)
    key(env, 3, 2, 1)
    take_log(env)
    fire(env, 1)
    luaunit.assert_equals(take_log(env), {"trig.long(3,2)", "autosave_reset()", "fn.dirty_grid(true)"})
    key(env, 8, 2, 1)
    take_log(env)
    key(env, 8, 2, 0)
    luaunit.assert_equals(take_log(env), {"clock.cancel(2)", "clock.cancel(1)", "trig.dual(3,2,8,2)", "autosave_reset()",
      "fn.dirty_grid(true)", "fn.dirty_screen(true)", "trig.post(8,2)", "fn.dirty_grid(true)", "fn.dirty_screen(true)"})
    key(env, 3, 2, 0)
    luaunit.assert_equals(take_log(env), {"clock.cancel(1)", "trig.post(3,2)", "fn.dirty_grid(true)", "fn.dirty_screen(true)"})
  end)
end


function test_grid_input_real_press_uses_only_the_selected_page_handlers()
  with_grid({real_press = true, page = NOTE, on_register_press = register_trig_handlers}, function(env)
    key(env, 3, 2, 1)
    key(env, 3, 2, 0)
    luaunit.assert_equals(take_log(env), {"note.pre(3,2)", "fn.dirty_grid(true)", "fn.dirty_screen(true)",
      "clock.run(long_press,3,2)", "clock.sleep(1)", "clock.cancel(1)", "note.short(3,2)",
      "save_confirm.cancel()", "autosave_reset()", "fn.dirty_grid(true)", "fn.dirty_screen(true)",
      "fn.dirty_grid(true)", "fn.dirty_screen(true)"})
    -- No long, dual or post handlers on this page: nothing dispatched, no autosave.
    key(env, 3, 2, 1)
    fire(env, 2)
    key(env, 3, 2, 0)
    key(env, 5, 2, 1)
    key(env, 6, 2, 1)
    key(env, 6, 2, 0)
    key(env, 5, 2, 0)
    luaunit.assert_equals(take_log(env), {
      "note.pre(3,2)", "fn.dirty_grid(true)", "fn.dirty_screen(true)", "clock.run(long_press,3,2)", "clock.sleep(1)",
      "fn.dirty_grid(true)",
      "clock.cancel(2)", "fn.dirty_grid(true)", "fn.dirty_screen(true)",
      "note.pre(5,2)", "fn.dirty_grid(true)", "fn.dirty_screen(true)", "clock.run(long_press,5,2)", "clock.sleep(1)",
      "note.pre(6,2)", "fn.dirty_grid(true)", "fn.dirty_screen(true)", "clock.run(long_press,6,2)", "clock.sleep(1)",
      "clock.cancel(4)", "clock.cancel(3)", "fn.dirty_grid(true)", "fn.dirty_screen(true)",
      "fn.dirty_grid(true)", "fn.dirty_screen(true)",
      "clock.cancel(3)", "fn.dirty_grid(true)", "fn.dirty_screen(true)"
    })
  end)
end

function test_grid_input_real_press_panic_hold_does_not_change_page()
  -- README 316: holding a non-selected page button panics; releasing it does not change pages.
  with_grid({real_press = true, page = CHANNEL}, function(env)
    key(env, 4, 8, 1)
    take_log(env)
    fire(env, 1)
    luaunit.assert_equals(take_log(env), {"tooltip:show(Midi Panic)", "m_clock.panic()", "fn.dirty_grid(true)"})
    key(env, 4, 8, 0)
    luaunit.assert_equals(take_log(env), {"clock.cancel(1)", "fn.dirty_grid(true)", "fn.dirty_screen(true)"})
    luaunit.assert_equals(env.selected_page, CHANNEL)
  end)
end

function test_grid_input_real_press_menu_tap_navigates_and_posts_to_new_page()
  local function register(env, name)
    local function rec(label) return function(...) env.record(label, ...) end end
    press:register(name, rec(name .. ".short"))
    press:register_post(name, rec(name .. ".post"))
  end
  with_grid({real_press = true, page = CHANNEL, on_register_press = register}, function(env)
    key(env, 4, 8, 1)
    take_log(env)
    key(env, 4, 8, 0)
    -- characterisation: the short press dispatches to the page selected when the
    -- key was released (channel), the post press to the page the menu selected.
    luaunit.assert_equals(take_log(env), {"clock.cancel(1)", "program.set_selected_page(3)", "scale_edit_page.refresh()",
      "tooltip:show(Scale Editor)", "fn.dirty_screen(true)", "fn.dirty_grid(true)",
      "channel_edit_page.short(4,8)", "save_confirm.cancel()", "autosave_reset()",
      "fn.dirty_grid(true)", "fn.dirty_screen(true)",
      "scale_edit_page.post(4,8)", "fn.dirty_grid(true)", "fn.dirty_screen(true)"})
    luaunit.assert_equals(env.selected_page, SCALE)
  end)
end

---------------------------------------------------------------------------
-- press.lua on its own
---------------------------------------------------------------------------

local function with_press(body)
  with_saved_globals(function()
    local env = {log = {}}
    function env.record(...) env.log[#env.log + 1] = fmt(...) end
    save_confirm = {cancel = function(...) env.record("save_confirm.cancel", ...) end}
    autosave_reset = function(...) env.record("autosave_reset", ...) end
    function env.rec(label) return function(...) env.record(label, ...) end end
    body(env, dofile(ROOT .. "press.lua"))
  end)
end

function test_grid_input_press_module_starts_with_empty_handler_tables()
  with_press(function(env, p)
    luaunit.assert_equals(p.handlers, {})
    luaunit.assert_equals(p.dual_handlers, {})
    luaunit.assert_equals(p.long_handlers, {})
    luaunit.assert_equals(p.pre_handlers, {})
    luaunit.assert_equals(p.post_handlers, {})
  end)
end

function test_grid_input_press_register_kinds_use_separate_lists_per_page()
  with_press(function(env, p)
    local a, b, c, d, e, f = env.rec("a"), env.rec("b"), env.rec("c"), env.rec("d"), env.rec("e"), env.rec("f")
    p:register("trigger_edit_page", a)
    p:register("trigger_edit_page", b)
    p:register("note_edit_page", c)
    p:register_dual("trigger_edit_page", d)
    p:register_long("trigger_edit_page", e)
    p:register_pre("song_edit_page", f)
    p:register_post("song_edit_page", a)
    luaunit.assert_equals(#p.handlers.trigger_edit_page, 2)
    luaunit.assert_is(p.handlers.trigger_edit_page[1], a)
    luaunit.assert_is(p.handlers.trigger_edit_page[2], b)
    luaunit.assert_is(p.handlers.note_edit_page[1], c)
    luaunit.assert_equals(#p.dual_handlers.trigger_edit_page, 1)
    luaunit.assert_is(p.dual_handlers.trigger_edit_page[1], d)
    luaunit.assert_is(p.long_handlers.trigger_edit_page[1], e)
    luaunit.assert_is(p.pre_handlers.song_edit_page[1], f)
    luaunit.assert_is(p.post_handlers.song_edit_page[1], a)
    luaunit.assert_nil(p.dual_handlers.note_edit_page)
    luaunit.assert_nil(p.long_handlers.song_edit_page)
    luaunit.assert_nil(p.pre_handlers.trigger_edit_page)
    luaunit.assert_nil(p.post_handlers.trigger_edit_page)
    luaunit.assert_equals(env.log, {}) -- registering calls nothing
  end)
end

function test_grid_input_press_handle_runs_menu_then_page_handlers_then_saves()
  with_press(function(env, p)
    p:register("menu", env.rec("menu1"))
    p:register("trigger_edit_page", env.rec("trig1"))
    p:register("menu", env.rec("menu2"))
    p:register("trigger_edit_page", env.rec("trig2"))
    p:register("note_edit_page", env.rec("note"))
    p:register_pre("trigger_edit_page", env.rec("pre"))
    p:register_post("trigger_edit_page", env.rec("post"))
    p:register_long("trigger_edit_page", env.rec("long"))
    p:register_dual("trigger_edit_page", env.rec("dual"))
    p:handle(TRIG, 3, 2)
    luaunit.assert_equals(env.log, {"menu1(3,2)", "menu2(3,2)", "trig1(3,2)", "trig2(3,2)", "save_confirm.cancel()", "autosave_reset()"})
  end)
end

function test_grid_input_press_handle_without_page_handlers_runs_menu_only()
  with_press(function(env, p)
    p:register("menu", env.rec("menu"))
    p:register("note_edit_page", env.rec("note"))
    p:handle(TRIG, 3, 2)
    luaunit.assert_equals(env.log, {"menu(3,2)"}) -- no save_confirm.cancel, no autosave
    env.log = {}
    p:handle(1, 5, 6) -- page 1 (Memory) has no page id
    p:handle(99, 5, 6)
    luaunit.assert_equals(env.log, {"menu(5,6)", "menu(5,6)"})
    env.log = {}
    p:handle(NOTE, 4, 4)
    luaunit.assert_equals(env.log, {"menu(4,4)", "note(4,4)", "save_confirm.cancel()", "autosave_reset()"})
  end)
end

function test_grid_input_press_handlers_are_keyed_by_page_id_not_number()
  with_press(function(env, p)
    p:register("menu", env.rec("menu"))
    p:register(TRIG, env.rec("by_number"))
    p:register_pre(TRIG, env.rec("pre_by_number"))
    p:handle(TRIG, 1, 1)
    p:handle_pre(TRIG, 1, 1)
    luaunit.assert_equals(env.log, {"menu(1,1)"}) -- characterisation
  end)
end

function test_grid_input_press_handle_and_handle_long_require_menu_handlers()
  with_press(function(env, p)
    p:register("trigger_edit_page", env.rec("trig"))
    p:register_long("trigger_edit_page", env.rec("long"))
    -- characterisation: m_grid.init always registers menu handlers first
    luaunit.assert_false(pcall(p.handle, p, TRIG, 1, 1))
    luaunit.assert_false(pcall(p.handle_long, p, TRIG, 1, 1))
    luaunit.assert_equals(env.log, {})
  end)
end

function test_grid_input_press_handle_long_runs_menu_then_page_then_autosave()
  with_press(function(env, p)
    p:register_long("menu", env.rec("menu_long"))
    p:register_long("velocity_edit_page", env.rec("vel_long1"))
    p:register_long("velocity_edit_page", env.rec("vel_long2"))
    p:register("velocity_edit_page", env.rec("vel_short"))
    p:handle_long(VELOCITY, 7, 3)
    luaunit.assert_equals(env.log, {"menu_long(7,3)", "vel_long1(7,3)", "vel_long2(7,3)", "autosave_reset()"})
    env.log = {}
    p:handle_long(SONG, 7, 3)
    luaunit.assert_equals(env.log, {"menu_long(7,3)"})
  end)
end

function test_grid_input_press_handle_dual_runs_page_handlers_only()
  with_press(function(env, p)
    p:register_dual("menu", env.rec("menu_dual"))
    p:register_dual("song_edit_page", env.rec("song_dual1"))
    p:register_dual("song_edit_page", env.rec("song_dual2"))
    p:register("menu", env.rec("menu"))
    p:handle_dual(SONG, 1, 2, 3, 4)
    luaunit.assert_equals(env.log, {"song_dual1(1,2,3,4)", "song_dual2(1,2,3,4)", "autosave_reset()"})
    env.log = {}
    p:handle_dual(TRIG, 1, 2, 3, 4)
    luaunit.assert_equals(env.log, {}) -- no page handlers: no autosave; menu dual never runs
  end)
end

function test_grid_input_press_handle_pre_and_post_run_page_handlers_only()
  with_press(function(env, p)
    p:register_pre("menu", env.rec("menu_pre"))
    p:register_post("menu", env.rec("menu_post"))
    p:register_pre("channel_edit_page", env.rec("pre1"))
    p:register_pre("channel_edit_page", env.rec("pre2"))
    p:register_post("channel_edit_page", env.rec("post1"))
    p:register_post("channel_edit_page", env.rec("post2"))
    p:register("channel_edit_page", env.rec("short"))
    p:handle_pre(CHANNEL, 9, 1)
    p:handle_post(CHANNEL, 9, 2)
    luaunit.assert_equals(env.log, {"pre1(9,1)", "pre2(9,1)", "post1(9,2)", "post2(9,2)"}) -- no autosave
    env.log = {}
    p:handle_pre(SCALE, 9, 1)
    p:handle_post(SCALE, 9, 2)
    luaunit.assert_equals(env.log, {})
  end)
end

function test_grid_input_press_handlers_registered_during_dispatch()
  with_press(function(env, p)
    p:register("menu", env.rec("menu"))
    p:register("scale_edit_page", function(x, y)
      env.record("first", x, y)
      p:register("scale_edit_page", env.rec("late"))
    end)
    p:handle(SCALE, 2, 2)
    -- characterisation: ipairs sees the handler appended during the loop
    luaunit.assert_equals(env.log, {"menu(2,2)", "first(2,2)", "late(2,2)", "save_confirm.cancel()", "autosave_reset()"})
  end)
end
