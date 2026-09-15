-- Behavioural pins for lib/clock/m_lattice.lua, written against the survivors of
-- the Lua mutation campaign (mutation-bc0570c). Every assertion is made through
-- the public Lattice/Sprocket API: a lattice is driven pulse by pulse and the
-- lattice transport passed to each action records WHEN it fired. No wall clock.
--
-- Labels:
--   derived          -- expectation follows from a stated musical/contract rule,
--                       independently of the implementation's tables.
--   characterisation -- golden value recorded from the current implementation;
--                       README.md "Clocks, Swing and Shuffle" (README.md:681-694)
--                       names the swing range (-50..50) and the Cyrene feel/basis
--                       controls but specifies no onset offsets.

local Lattice = include("mosaic/lib/clock/m_lattice")

local PPQN = 96
local STRAIGHT_QUARTER = PPQN -- pulses in one 1/4 division at the default ppqn

local function new_lattice(args)
  args = args or {}
  if args.auto == nil then args.auto = false end
  local lattice = Lattice:new(args)
  lattice:start()
  return lattice
end

local function run(lattice, pulses)
  for _ = 1, pulses do lattice:pulse() end
end

-- Adds a sprocket whose action appends the lattice transport to the returned log.
local function logged_sprocket(lattice, args, log)
  log = log or {}
  args.action = function(t) log[#log + 1] = t end
  return lattice:new_sprocket(args), log
end

-- Onset transports of a fresh sprocket on a fresh lattice.
local function onsets(args, count, lattice_args)
  local lattice = new_lattice(lattice_args)
  local sprocket, log = logged_sprocket(lattice, args)
  local guard = 0
  while #log < count and guard < 100000 do
    lattice:pulse()
    guard = guard + 1
  end
  return log, sprocket, lattice
end

local function intervals(log, first, last)
  local out = {}
  for i = first + 1, last do out[#out + 1] = log[i] - log[i - 1] end
  return out
end

local function repeated(value, count)
  local out = {}
  for i = 1, count do out[i] = value end
  return out
end

local function error_message(f, ...)
  local ok, err = pcall(f, ...)
  luaunit.assert_false(ok, "expected an error")
  return tostring(err)
end

local function with_global(name, value, body)
  local saved = _G[name]
  _G[name] = value
  local ok, err = pcall(body)
  _G[name] = saved
  if not ok then error(err, 0) end
end

---------------------------------------------------------------------------
-- Shuffle feel tables
---------------------------------------------------------------------------

-- characterisation: onset intervals (pulses) of steps 1..8 for a 1/4 sprocket
-- at shuffle amount 100, ppqn 96. Feel order follows the lattice's
-- shuffle_feels list (drunk, smooth, heavy, clave). Step 1 reads the second
-- column of a feel row (playpos = step % 8 + 1).
local SHUFFLE_INTERVALS = {
  [1] = { -- drunk
    {128, 85, 86, 85, 128, 85, 86, 85},
    {109, 110, 55, 110, 109, 110, 55, 110},
    {153, 77, 77, 77, 153, 77, 77, 77},
    {192, 64, 64, 64, 192, 64, 64, 64},
    {192, 96, 48, 48, 192, 96, 48, 48},
    {214, 85, 43, 42, 214, 85, 43, 42},
  },
  [2] = { -- smooth
    {106, 86, 85, 107, 106, 86, 85, 107},
    {109, 83, 82, 110, 109, 83, 82, 110},
    {115, 77, 77, 115, 115, 77, 77, 115},
    {128, 64, 64, 128, 128, 64, 64, 128},
    {120, 72, 72, 120, 120, 72, 72, 120},
    {150, 64, 42, 128, 150, 64, 42, 128},
  },
  [3] = { -- heavy
    {86, 85, 43, 170, 86, 85, 43, 170},
    {55, 109, 55, 165, 55, 109, 55, 165},
    {77, 76, 77, 154, 77, 76, 77, 154},
    {64, 64, 64, 192, 64, 64, 64, 192},
    {48, 96, 48, 192, 48, 96, 48, 192},
    {42, 86, 42, 214, 42, 86, 42, 214},
  },
  [4] = { -- clave
    {128, 85, 86, 128, 85, 85, 86, 85},
    {109, 55, 110, 110, 55, 109, 110, 110},
    {153, 77, 77, 153, 77, 77, 77, 77},
    {128, 64, 96, 128, 64, 96, 96, 96},
    {144, 72, 96, 120, 72, 96, 96, 72},
    {150, 64, 85, 149, 43, 107, 85, 85},
  },
}

local function shuffle_args(feel, basis, amount)
  return {division = 1 / 4, swing_or_shuffle = 2, shuffle_feel = feel,
          shuffle_basis = basis, shuffle_amount = amount}
end

function test_lattice_mk_shuffle_feel_cycle_spans_eight_straight_steps()
  -- derived: a feel only redistributes time inside its 8-step cycle, so each
  -- cycle of 8 onsets spans exactly 8 straight steps and the first onset is on
  -- the first pulse. Holds at full and partial amount.
  for _, amount in ipairs({100, 50}) do
    for feel = 1, 4 do
      for basis = 1, 6 do
        local log = onsets(shuffle_args(feel, basis, amount), 25)
        local label = string.format("feel %d basis %d amount %d", feel, basis, amount)
        luaunit.assert_equals(log[1], 1, label)
        for cycle = 1, 3 do
          luaunit.assert_equals(log[1 + 8 * cycle] - log[1 + 8 * (cycle - 1)], 8 * STRAIGHT_QUARTER, label)
        end
      end
    end
  end
end

function test_lattice_mk_shuffle_amount_zero_is_straight_for_every_feel()
  -- derived: amount 0 means no shuffle at all.
  for feel = 1, 4 do
    for basis = 1, 6 do
      local log = onsets(shuffle_args(feel, basis, 0), 9)
      luaunit.assert_equals(intervals(log, 1, 9), repeated(STRAIGHT_QUARTER, 8),
        string.format("feel %d basis %d", feel, basis))
    end
  end
end

function test_lattice_mk_shuffle_feel_onset_intervals_golden()
  -- characterisation: exact per-step onset intervals for every feel/basis,
  -- repeated identically in the second and third 8-step cycles.
  for feel = 1, 4 do
    for basis = 1, 6 do
      local log = onsets(shuffle_args(feel, basis, 100), 25)
      local label = string.format("feel %d basis %d", feel, basis)
      local expected = SHUFFLE_INTERVALS[feel][basis]
      luaunit.assert_equals(intervals(log, 1, 9), expected, label)
      luaunit.assert_equals(intervals(log, 9, 17), expected, label)
      luaunit.assert_equals(intervals(log, 17, 25), expected, label)
    end
  end
end

---------------------------------------------------------------------------
-- Lattice construction, start/stop, pulse bookkeeping
---------------------------------------------------------------------------

function test_lattice_mk_start_runs_norns_clock_only_when_auto()
  local runs = {}
  local fake_clock = {
    run = function(f, arg) runs[#runs + 1] = {f = f, arg = arg}; return 42 end,
    cancel = function() end,
  }
  with_global("clock", fake_clock, function()
    local auto = Lattice:new()
    auto:start()
    auto:start()
    luaunit.assert_equals(#runs, 1)
    luaunit.assert_equals(runs[1].f, Lattice.auto_pulse)
    luaunit.assert_equals(runs[1].arg, auto)

    local manual = Lattice:new({auto = false})
    manual:start()
    luaunit.assert_equals(#runs, 1)
  end)
end

function test_lattice_mk_default_pattern_length_wraps_steps_after_64()
  -- derived: the lattice's default pattern length is 64 steps. A 1/384
  -- division lasts exactly one pulse, so step n begins on pulse n.
  local lattice = Lattice:new({auto = false})
  lattice:start()
  local sprocket = lattice:new_sprocket({division = 1 / (PPQN * 4)})
  run(lattice, 63)
  luaunit.assert_equals(sprocket:get_step(), 64)
  run(lattice, 1)
  luaunit.assert_equals(sprocket:get_step(), 1)

  local short = new_lattice({pattern_length = 16})
  local short_sprocket = short:new_sprocket({division = 1 / (PPQN * 4)})
  run(short, 15)
  luaunit.assert_equals(short_sprocket:get_step(), 16)
  run(short, 1)
  luaunit.assert_equals(short_sprocket:get_step(), 1)
end

function test_lattice_mk_stopped_lattice_ignores_pulses_until_started()
  local lattice = new_lattice()
  local _, log = logged_sprocket(lattice, {division = 1 / 16})
  run(lattice, 1)
  lattice:stop()
  run(lattice, 100)
  luaunit.assert_equals(log, {1})
  lattice:start()
  run(lattice, 24)
  -- transport did not advance while stopped: the next onset is 24 pulses on.
  luaunit.assert_equals(log, {1, 25})
end

function test_lattice_mk_stopped_sprocket_is_kept_and_resumes()
  local lattice = new_lattice()
  local sprocket, log = logged_sprocket(lattice, {division = 1 / 16})
  run(lattice, 5)
  sprocket:stop()
  run(lattice, 30)
  sprocket:start()
  run(lattice, 40)
  -- derived: the sprocket's phase is frozen while stopped; 5 of its 24 pulses
  -- had elapsed, so its next onset is 19 pulses after it restarts (pulse 36).
  luaunit.assert_equals(log, {1, 55})
end

function test_lattice_mk_destroyed_sprocket_stops_firing()
  local lattice = new_lattice()
  local doomed, doomed_log = logged_sprocket(lattice, {division = 1 / 16})
  local _, kept_log = logged_sprocket(lattice, {division = 1 / 16})
  run(lattice, 1)
  doomed:destroy()
  run(lattice, 48)
  luaunit.assert_equals(doomed_log, {1})
  luaunit.assert_equals(kept_log, {1, 25, 49})
end

function test_lattice_mk_sprocket_order_defaults_to_three_and_clamps_to_one_to_five()
  local lattice = new_lattice()
  local fired = {}
  local function add(name, order)
    lattice:new_sprocket({division = 1 / 16, order = order,
      action = function() fired[#fired + 1] = name end})
  end
  -- creation order deliberately differs from the expected firing order;
  -- equal orders fire in creation order.
  add("two", 2)
  add("four", 4)
  add("five", 5)
  add("default", nil)
  add("nine", 9)
  add("zero", 0)
  run(lattice, 1)
  luaunit.assert_equals(fired, {"zero", "two", "default", "four", "five", "nine"})
end

function test_lattice_mk_many_equal_order_sprockets_fire_in_creation_order()
  -- derived: equal-order sprockets fire in creation order. Mosaic creates its
  -- channel clocks as a large same-order group, so this must hold for more
  -- sprockets than a Lua hash traversal happens to keep in sequence.
  for _, order in ipairs({1, 2, 3, 4, 5}) do
    local lattice = new_lattice()
    local fired, expected = {}, {}
    for i = 1, 16 do
      expected[i] = i
      lattice:new_sprocket({division = 1 / 16, order = order, action = function() fired[#fired + 1] = i end})
    end
    run(lattice, 1)
    luaunit.assert_equals(fired, expected, "order " .. order)
  end
end

function test_lattice_mk_default_division_is_a_quarter_note()
  -- derived: division 1/4 at ppqn 96 is 96 pulses.
  local log = onsets({}, 3)
  luaunit.assert_equals(log, {1, 97, 193})
end

function test_lattice_mk_sub_pulse_division_is_floored_to_one_pulse()
  -- derived: the shortest division is one native pulse (1/(4*ppqn)).
  local one_pulse = 1 / (PPQN * 4)
  luaunit.assert_equals(onsets({division = one_pulse}, 5), {1, 2, 3, 4, 5})
  luaunit.assert_equals(onsets({division = 1e-6}, 5), {1, 2, 3, 4, 5})
  -- With maximum swing the floored division must behave exactly like an
  -- explicit one-pulse division (its swung 1.5-pulse steps).
  local floored = onsets({division = 1e-6, swing = 50}, 10)
  luaunit.assert_equals(floored, onsets({division = one_pulse, swing = 50}, 10))
  luaunit.assert_equals(floored, {1, 3, 4, 5, 6, 8, 9, 10, 11, 13}) -- characterisation
end

function test_lattice_mk_sprocket_enabled_unless_explicitly_disabled()
  local lattice = new_lattice()
  local _, default_log = logged_sprocket(lattice, {division = 1 / 16})
  local _, disabled_log = logged_sprocket(lattice, {division = 1 / 16, enabled = false})
  local _, enabled_log = logged_sprocket(lattice, {division = 1 / 16, enabled = true})
  run(lattice, 25)
  luaunit.assert_equals(default_log, {1, 25})
  luaunit.assert_equals(disabled_log, {})
  luaunit.assert_equals(enabled_log, {1, 25})
end

function test_lattice_mk_delay_is_clamped_to_one_division()
  -- derived: delay 1 postpones the first onset by one whole division.
  luaunit.assert_equals(onsets({division = 1 / 4, delay = 1}, 3), {97, 193, 289})
  luaunit.assert_equals(onsets({division = 1 / 4, delay = 5}, 3), {97, 193, 289})
  luaunit.assert_equals(onsets({division = 1 / 4, delay = 0.5}, 2), {49, 145})
end

function test_lattice_mk_swing_defaults_to_straight_and_clamps_to_fifty()
  -- derived: swing s% lengthens odd steps by s% and shortens even steps by s%.
  local function first_intervals(args)
    args.division = 1 / 4
    return intervals(onsets(args, 5), 1, 5)
  end
  luaunit.assert_equals(first_intervals({}), {96, 96, 96, 96})
  luaunit.assert_equals(first_intervals({swing = 50}), {144, 48, 144, 48})
  luaunit.assert_equals(first_intervals({swing = 80}), {144, 48, 144, 48})
  luaunit.assert_equals(first_intervals({swing = -50}), {48, 144, 48, 144})
  luaunit.assert_equals(first_intervals({swing = -80}), {48, 144, 48, 144})
end

function test_lattice_mk_swing_or_shuffle_out_of_range_clamps_to_shuffle_or_swing()
  local shuffle = intervals(onsets(shuffle_args(1, 4, 100), 5), 1, 5)
  luaunit.assert_equals(shuffle, {192, 64, 64, 64}) -- characterisation (drunk basis 4)
  local above = shuffle_args(1, 4, 100); above.swing_or_shuffle = 5
  luaunit.assert_equals(intervals(onsets(above, 5), 1, 5), shuffle)
  local below = shuffle_args(1, 4, 100); below.swing_or_shuffle = 0; below.swing = 25
  luaunit.assert_equals(intervals(onsets(below, 5), 1, 5), {120, 72, 120, 72})
end

function test_lattice_mk_negative_shuffle_amount_is_no_shuffle()
  for basis = 1, 6 do
    local log = onsets(shuffle_args(1, basis, -20), 9)
    luaunit.assert_equals(intervals(log, 1, 9), repeated(STRAIGHT_QUARTER, 8), "basis " .. basis)
  end
end

function test_lattice_mk_shuffle_amount_above_hundred_is_full_shuffle()
  luaunit.assert_equals(intervals(onsets(shuffle_args(3, 6, 150), 9), 1, 9), SHUFFLE_INTERVALS[3][6])
end

---------------------------------------------------------------------------
-- Delayed actions
---------------------------------------------------------------------------

function test_lattice_mk_fractional_length_with_float_residue_fires_on_its_pulse()
  -- derived: at swing 25 the first 1/4 step is 120 pulses; 3/5 of it is 72
  -- pulses. 3 * (1/5) is 0.6000000000000001, whose product with 120 lands a
  -- hair above 72 -- the residue must not push the release a pulse late.
  local lattice = new_lattice()
  local log = {}
  local sprocket
  sprocket = lattice:new_sprocket({division = 1 / 4, swing = 25, action = function(t)
    log[#log + 1] = "on" .. t
    if t == 1 then
      sprocket:set_delayed_action(3 * (1 / 5), function() log[#log + 1] = "off" .. lattice.transport end)
    end
  end})
  run(lattice, 200)
  luaunit.assert_equals(log, {"on1", "off73", "on121", "on193"})
end

function test_lattice_mk_fraction_rounding_to_a_full_step_fires_after_next_onset()
  -- derived: 0.999 of a 24-pulse step cannot complete inside the step, so the
  -- release lands on the next onset pulse, after that onset's action.
  local lattice = new_lattice()
  local log = {}
  local sprocket
  sprocket = lattice:new_sprocket({division = 1 / 16, action = function(t)
    log[#log + 1] = "on" .. t
    if t == 1 then
      sprocket:set_delayed_action(0.999, function() log[#log + 1] = "off" .. lattice.transport end)
    end
  end})
  run(lattice, 60)
  luaunit.assert_equals(log, {"on1", "on25", "off25", "on49"})
end

function test_lattice_mk_due_releases_run_before_the_onset_in_insertion_order()
  local lattice = new_lattice()
  local log = {}
  local sprocket = lattice:new_sprocket({division = 1 / 16, action = function(t) log[#log + 1] = "on" .. t end})
  run(lattice, 24) -- the next pulse (25) is an onset
  sprocket:set_delayed_action(0, function() log[#log + 1] = "release-a" end, true)
  sprocket:set_delayed_action(0, function() log[#log + 1] = "release-b" end, true)
  sprocket:set_delayed_action(0, function() log[#log + 1] = "after" end)
  run(lattice, 1)
  luaunit.assert_equals(log, {"on1", "release-a", "release-b", "on25", "after"})
end

function test_lattice_mk_cleanup_callback_receives_completed_action_id()
  local lattice = new_lattice()
  local cleaned = {}
  local sprocket = lattice:new_sprocket({division = 1 / 16,
    cleanup_delayed_action = function(id) cleaned[#cleaned + 1] = id end})
  run(lattice, 2)
  local ran = false
  local id = sprocket:set_delayed_action(0, function() ran = true end)
  luaunit.assert_equals(cleaned, {})
  run(lattice, 1)
  luaunit.assert_true(ran)
  luaunit.assert_equals(cleaned, {id})
end

function test_lattice_mk_delayed_action_error_propagates_unchanged()
  local lattice = new_lattice()
  local sprocket = lattice:new_sprocket({division = 1 / 16})
  run(lattice, 2)
  sprocket:set_delayed_action(0, function() error("boom", 0) end)
  local ok, err = pcall(lattice.pulse, lattice)
  luaunit.assert_false(ok)
  luaunit.assert_equals(err, "boom")
end

---------------------------------------------------------------------------
-- Onset counting and projection
---------------------------------------------------------------------------

function test_lattice_mk_onset_count_and_occurrence_projection_match_firing()
  -- derived: a projection of occurrence k is the number of pulses after the
  -- next pulse at which the k-th onset fires (1/16 = 24 pulses).
  local lattice = new_lattice()
  local sprocket, log = logged_sprocket(lattice, {division = 1 / 16})
  luaunit.assert_equals(sprocket:project_onset_occurrence(1), 0)
  luaunit.assert_equals(sprocket:project_onset_occurrence(3), 48)
  run(lattice, 1)
  luaunit.assert_equals(sprocket.onset_count, 1)
  luaunit.assert_equals(sprocket:project_onset_occurrence(2), 23)
  luaunit.assert_equals(sprocket:project_onset_occurrence(4), 71)
  run(lattice, 10)
  luaunit.assert_equals(sprocket:project_onset_occurrence(3), 37)
  local at = lattice.transport
  run(lattice, 38)
  luaunit.assert_equals(sprocket.onset_count, 3)
  luaunit.assert_equals(log[3], at + 37)
end

local function projection_matches_actual(args, label)
  -- derived: projections taken inside the action at onset k equal the transport
  -- offsets at which onsets k+1..k+8 actually fire.
  local lattice = new_lattice()
  local log, projections = {}, {}
  local sprocket
  args.action = function(t)
    log[#log + 1] = t
    if #log == 2 then
      for distance = 1, 8 do projections[distance] = sprocket:project_onset_pulses(distance) end
    end
  end
  sprocket = lattice:new_sprocket(args)
  local guard = 0
  while #log < 10 and guard < 10000 do lattice:pulse(); guard = guard + 1 end
  for distance = 1, 8 do
    luaunit.assert_equals(projections[distance], log[2 + distance] - log[2], label .. " distance " .. distance)
  end
end

function test_lattice_mk_onset_projection_matches_actual_onsets()
  projection_matches_actual({division = 1 / 16}, "straight")
  projection_matches_actual({division = 1 / 4, swing = 25}, "swing")
  projection_matches_actual({division = 1 / 28}, "fractional straight")
  projection_matches_actual(shuffle_args(1, 1, 100), "drunk 1")
  projection_matches_actual(shuffle_args(1, 2, 100), "drunk 2")
  projection_matches_actual(shuffle_args(2, 1, 100), "smooth 1")
  projection_matches_actual(shuffle_args(4, 6, 100), "clave 6")
end

function test_lattice_mk_onset_projection_rejects_invalid_distance()
  local lattice = new_lattice()
  local results = {}
  local sprocket
  sprocket = lattice:new_sprocket({division = 1 / 16, action = function()
    for _, distance in ipairs({0, 65, 1.5, "2"}) do
      local ok, err = pcall(sprocket.project_onset_pulses, sprocket, distance)
      results[#results + 1] = {ok, tostring(err):match("Invalid onset distance") ~= nil}
    end
    results[#results + 1] = {sprocket:project_onset_pulses(64)}
    results[#results + 1] = {sprocket:project_onset_pulses(1)}
  end})
  run(lattice, 1)
  luaunit.assert_equals(results, {{false, true}, {false, true}, {false, true}, {false, true}, {64 * 24}, {24}})
end

function test_lattice_mk_onset_projection_requires_a_resolved_onset()
  local lattice = new_lattice()
  local sprocket = lattice:new_sprocket({division = 1 / 16})
  run(lattice, 1) -- between pulses, one pulse into the step
  luaunit.assert_str_contains(error_message(sprocket.project_onset_pulses, sprocket, 1),
    "Projection requires a resolved channel onset")
end

function test_lattice_mk_onset_projection_rejects_delayed_or_variable_clocks()
  local lattice = new_lattice()
  local messages = {}
  local function capture(sprocket)
    return function()
      local ok, err = pcall(sprocket.project_onset_pulses, sprocket, 1)
      messages[#messages + 1] = (not ok) and tostring(err):match("Unsupported variable or delayed projection") ~= nil
    end
  end
  local delayed = lattice:new_sprocket({division = 1 / 16, delay = 0.5})
  delayed:set_action(capture(delayed))
  local variable = lattice:new_sprocket({division = 1 / 16, division_for_cycle = function() return 1 / 16 end})
  variable:set_action(capture(variable))
  local pending = lattice:new_sprocket({division = 1 / 16})
  pending:set_action(capture(pending))
  pending:set_delay(0.25)
  run(lattice, 20)
  luaunit.assert_equals(messages, {true, true, true})
end

---------------------------------------------------------------------------
-- Setters
---------------------------------------------------------------------------

function test_lattice_mk_set_division_keeps_proportional_progress_rounded()
  local function after_change(pulses_before)
    local lattice = new_lattice()
    local sprocket, log = logged_sprocket(lattice, {division = 1 / 8})
    run(lattice, pulses_before)
    sprocket:set_division(1 / 16)
    run(lattice, 100)
    return log
  end
  -- derived: at a step boundary the change starts a fresh 24-pulse step now.
  luaunit.assert_equals(after_change(0), {1, 25, 49, 73, 97})
  -- derived: 24 of 48 pulses elapsed -> 12 of 24; next onset 12 pulses on.
  luaunit.assert_equals(after_change(24), {1, 37, 61, 85, 109})
  -- derived: 25 of 48 elapsed -> 12.5 of 24, rounded half up to 13 elapsed,
  -- so 11 pulses remain and the next onset is pulse 25 + 11 + 1.
  luaunit.assert_equals(after_change(25), {1, 37, 61, 85, 109})
  -- 26 of 48 -> exactly 13 of 24; 27 of 48 -> 13.5, rounded up to 14.
  luaunit.assert_equals(after_change(26), {1, 38, 62, 86, 110})
  luaunit.assert_equals(after_change(27), {1, 38, 62, 86, 110})
end

function test_lattice_mk_switching_to_shuffle_mid_step_keeps_progress()
  local lattice = new_lattice()
  local sprocket, log = logged_sprocket(lattice, {division = 1 / 4, shuffle_feel = 1,
    shuffle_basis = 4, shuffle_amount = 100})
  run(lattice, 48)
  sprocket:set_swing_or_shuffle(2)
  run(lattice, 600)
  -- derived: halfway through a straight step when the step becomes a 192-pulse
  -- shuffled step, so 96 pulses remain; later steps follow drunk basis 4.
  luaunit.assert_equals(log, {1, 145, 209, 273, 337, 529, 593})
end

function test_lattice_mk_set_swing_or_shuffle_clamps_and_ignores_repeats()
  local function run_with(value)
    local lattice = new_lattice()
    local sprocket, log = logged_sprocket(lattice, {division = 1 / 4, swing = 25,
      swing_or_shuffle = 2, shuffle_feel = 1, shuffle_basis = 4, shuffle_amount = 100})
    sprocket:set_swing_or_shuffle(value)
    run(lattice, 800)
    return intervals(log, 1, 5)
  end
  luaunit.assert_equals(run_with(0), {120, 72, 120, 72})
  luaunit.assert_equals(run_with(1), {120, 72, 120, 72})
  luaunit.assert_equals(run_with(2), {192, 64, 64, 64})
  luaunit.assert_equals(run_with(7), {192, 64, 64, 64})
end

function test_lattice_mk_set_swing_defaults_nil_and_clamps()
  local function run_with(value)
    local lattice = new_lattice()
    local sprocket, log = logged_sprocket(lattice, {division = 1 / 4, swing = 30})
    sprocket:set_swing(value)
    run(lattice, 500)
    return intervals(log, 1, 5)
  end
  luaunit.assert_equals(run_with(nil), {96, 96, 96, 96})
  luaunit.assert_equals(run_with(80), {144, 48, 144, 48})
  luaunit.assert_equals(run_with(-80), {48, 144, 48, 144})
end

function test_lattice_mk_set_shuffle_amount_scales_and_clamps()
  local function run_with(value)
    local lattice = new_lattice()
    local sprocket, log = logged_sprocket(lattice, shuffle_args(3, 6, 0))
    sprocket:set_shuffle_amount(value)
    run(lattice, 900)
    return intervals(log, 1, 9)
  end
  -- characterisation: heavy basis 6 once the amount is raised from 0 before
  -- the first pulse (step 1 rounded once, unlike a sprocket created at 100).
  local full = run_with(100)
  luaunit.assert_equals(full, {43, 85, 43, 213, 43, 85, 43, 213})
  luaunit.assert_equals(run_with(150), full)
  luaunit.assert_equals(run_with(-10), repeated(STRAIGHT_QUARTER, 8))
  luaunit.assert_equals(run_with(0), repeated(STRAIGHT_QUARTER, 8))
  -- derived: 50% sits halfway between straight and the full feel, and the
  -- 8-step cycle still spans 8 straight steps.
  local half = run_with(50)
  local total = 0
  for i = 1, 8 do
    total = total + half[i]
    luaunit.assert_true(math.abs(half[i] - (STRAIGHT_QUARTER + full[i]) / 2) <= 1, "position " .. i)
  end
  luaunit.assert_equals(total, 8 * STRAIGHT_QUARTER)
end

local function shuffle_setter_case(setter, value, start_feel, start_basis)
  local lattice = new_lattice()
  local sprocket, log = logged_sprocket(lattice, shuffle_args(start_feel, start_basis, 100))
  sprocket[setter](sprocket, value)
  run(lattice, 900)
  return intervals(log, 1, 9)
end

function test_lattice_mk_set_shuffle_basis_clamps_to_one_to_six()
  luaunit.assert_equals(shuffle_setter_case("set_shuffle_basis", 0, 1, 4), SHUFFLE_INTERVALS[1][1])
  luaunit.assert_equals(shuffle_setter_case("set_shuffle_basis", 9, 1, 4), SHUFFLE_INTERVALS[1][6])
  luaunit.assert_equals(shuffle_setter_case("set_shuffle_basis", 2, 1, 4), SHUFFLE_INTERVALS[1][2])
end

function test_lattice_mk_set_shuffle_feel_clamps_to_one_to_four()
  luaunit.assert_equals(shuffle_setter_case("set_shuffle_feel", 0, 3, 4), SHUFFLE_INTERVALS[1][4])
  luaunit.assert_equals(shuffle_setter_case("set_shuffle_feel", 9, 1, 4), SHUFFLE_INTERVALS[4][4])
  luaunit.assert_equals(shuffle_setter_case("set_shuffle_feel", 2, 1, 4), SHUFFLE_INTERVALS[2][4])
end

local function mid_step_setter(setter, value)
  -- drunk basis 4: step 1 is 192 pulses. The setter runs 48 pulses in.
  local lattice = new_lattice()
  local sprocket, log = logged_sprocket(lattice, shuffle_args(1, 4, 100))
  run(lattice, 48)
  sprocket[setter](sprocket, value)
  run(lattice, 400)
  return log
end

function test_lattice_mk_shuffle_feel_and_basis_changes_apply_to_the_current_step()
  -- derived: in shuffle mode the running step is re-timed at once, keeping its
  -- proportional progress: 48 of 192 pulses (1/4) elapsed.
  -- basis 5 step 1 = 192 pulses too, so nothing moves; basis 1 (128 pulses):
  -- 1/4 elapsed -> 96 remain -> onset at 48 + 96 + 1 = 145.
  luaunit.assert_equals(mid_step_setter("set_shuffle_basis", 1)[2], 145)
  -- smooth basis 4 step 1 = 128 pulses as well.
  luaunit.assert_equals(mid_step_setter("set_shuffle_feel", 2)[2], 145)
  luaunit.assert_equals(mid_step_setter("set_shuffle_basis", 4)[2], 193)
  luaunit.assert_equals(mid_step_setter("set_shuffle_feel", 1)[2], 193)
end

function test_lattice_mk_inactive_shuffle_preferences_do_not_disturb_swing()
  -- derived: with Swing selected, feel/basis are stored preferences only; the
  -- swung onsets (fractional 26.4/21.6-pulse steps) must match an untouched run.
  local function swung(change)
    local lattice = new_lattice()
    local sprocket, log = logged_sprocket(lattice, {division = 1 / 16, swing = 10})
    for _ = 1, 10 do
      run(lattice, 13)
      if change then change(sprocket) end
    end
    run(lattice, 200)
    return log
  end
  local control = swung(nil)
  local n = 0
  local changed = swung(function(sprocket)
    n = n + 1
    sprocket:set_shuffle_basis((n % 6) + 1)
    sprocket:set_shuffle_feel((n % 4) + 1)
  end)
  luaunit.assert_equals(changed, control)
end

function test_lattice_mk_odd_pattern_length_keeps_its_last_swing_step_straight()
  -- derived: an odd pattern cannot pair its last step, so that step is straight.
  local log = onsets({division = 1 / 4, swing = 25}, 10, {pattern_length = 3})
  luaunit.assert_equals(intervals(log, 1, 10), {120, 72, 96, 120, 72, 96, 120, 72, 96})
end

---------------------------------------------------------------------------
-- Variable divisions
---------------------------------------------------------------------------

function test_lattice_mk_division_for_cycle_selects_each_step_length()
  local lengths = {1 / 16, 1 / 8, 1 / 32}
  local n = 0
  local log = onsets({division = 1 / 4, division_for_cycle = function()
    n = n + 1
    return lengths[((n - 1) % 3) + 1]
  end}, 5)
  -- derived: 24, 48 and 12 pulse steps in turn.
  luaunit.assert_equals(log, {1, 25, 73, 85, 109})
end

function test_lattice_mk_division_for_cycle_floors_to_one_pulse()
  -- derived: a sub-pulse variable division behaves exactly like a variable
  -- division of one native pulse, including its swung 1.5-pulse steps.
  local tiny = onsets({division = 1 / 4, swing = 50, division_for_cycle = function() return 1e-6 end}, 10)
  luaunit.assert_equals(tiny, onsets({division = 1 / 4, swing = 50,
    division_for_cycle = function() return 1 / (PPQN * 4) end}, 10))
  luaunit.assert_equals(tiny, {1, 2, 3, 5, 6, 7, 8, 10, 11, 12}) -- characterisation
  local plain = onsets({division = 1 / 4, division_for_cycle = function() return 1e-6 end}, 5)
  luaunit.assert_equals(plain, {1, 2, 3, 4, 5})
end

function test_lattice_mk_division_for_cycle_rejects_invalid_divisions()
  for _, bad in ipairs({0, -1, math.huge, "x"}) do
    local lattice = new_lattice()
    lattice:new_sprocket({division_for_cycle = function() return bad end})
    luaunit.assert_str_contains(error_message(lattice.pulse, lattice), "Invalid cycle division")
  end
end

---------------------------------------------------------------------------
-- Realignment
---------------------------------------------------------------------------

function test_lattice_mk_realign_restarts_only_opted_in_sprockets()
  local lattice = new_lattice()
  local early_log, late_log, fixed_log, steps = {}, {}, {}, {}
  -- An order-1 opted-in sprocket that runs before the realigning action.
  local early = logged_sprocket(lattice, {division = 1 / 4, order = 1, realign = true}, early_log)
  local master_count = 0
  lattice:new_sprocket({division = 1 / 16, order = 1, action = function()
    master_count = master_count + 1
    if master_count == 3 then lattice:realign_eligable_sprockets() end
  end})
  local late
  late = lattice:new_sprocket({division = 1 / 4, order = 2, realign = true,
    action = function(t) late_log[#late_log + 1] = t; steps[#steps + 1] = late:get_step() end})
  logged_sprocket(lattice, {division = 1 / 4, order = 2}, fixed_log)
  run(lattice, 400)
  -- derived: realignment happens on pulse 49 (third 1/16 onset). The later
  -- sprocket restarts on that same pulse at step 1; the earlier one, already
  -- processed this pulse, restarts on the next pulse; the opted-out sprocket
  -- keeps its original grid.
  luaunit.assert_equals(early_log, {1, 50, 146, 242, 338})
  luaunit.assert_equals(late_log, {1, 49, 145, 241, 337})
  luaunit.assert_equals(steps, {1, 1, 2, 3, 4})
  luaunit.assert_equals(fixed_log, {1, 97, 193, 289, 385})
end

function test_lattice_mk_realign_mid_step_keeps_the_swung_first_step()
  -- derived (bugs.json realign-mid-step-length, S41; formerly pinned as
  -- characterisation of m_lattice.lua:703-704): a channel restarted in the
  -- middle of a step starts again at step 1 with its swung length, as from its
  -- first pulse. Swing 25 on 1/4: 120 then 72 pulses, so after the realign on
  -- pulse 49 the onsets are 49, 169, 241, 361, 433 (not a straight 96 first).
  local lattice = new_lattice()
  local _, log = logged_sprocket(lattice, {division = 1 / 4, swing = 25, realign = true})
  run(lattice, 48)
  lattice:realign_eligable_sprockets()
  run(lattice, 500)
  luaunit.assert_equals(log, {1, 49, 169, 241, 361, 433})
  luaunit.assert_equals(intervals(log, 2, 6), {120, 72, 120, 72})
end

function test_lattice_mk_realign_mid_step_restarts_shuffle_carry()
  -- derived (bugs.json realign-mid-step-length, S41/S53): after a mid-step
  -- realign the rounding carry restarts from the step-1 state, so the
  -- restarted channel repeats the intervals of a fresh sprocket exactly.
  -- characterisation: fractional smooth basis 1 intervals 106, 86, 85, 107 ...
  local lattice = new_lattice()
  local args = shuffle_args(2, 1, 100)
  args.realign = true
  local _, log = logged_sprocket(lattice, args)
  run(lattice, 50)
  lattice:realign_eligable_sprockets()
  run(lattice, 1000)
  local fresh = onsets(shuffle_args(2, 1, 100), 10)
  luaunit.assert_equals(intervals(log, 2, 11), intervals(fresh, 1, 10))
  luaunit.assert_equals(intervals(log, 2, 11), {106, 86, 85, 107, 106, 86, 85, 107, 106})
end

---------------------------------------------------------------------------
-- Suspected defect: initial delay discarded by first-step re-rounding
---------------------------------------------------------------------------

function test_lattice_mk_initial_delay_with_carry_changed_first_step()
  -- characterisation (suspected defect: m_lattice.lua:550-553 with :345/:574).
  -- new_sprocket rounds step 1 once (line 345) and the first begin_cycle rounds
  -- it again (line 574). When the second rounding changes the step length
  -- (smooth basis 1: 107 then 106 pulses), update_shuffle rescales the negative
  -- pre-delay phase and clamps it to 1, so a delay of half a step is dropped
  -- and the first onset lands on pulse 1. Drunk basis 1 (128 exactly both
  -- times) keeps its delay. m_clock's end_of_clock_processor uses delay = 1
  -- with the channel's shuffle settings.
  luaunit.assert_equals(onsets({division = 1 / 4, delay = 0.5, swing_or_shuffle = 2,
    shuffle_feel = 1, shuffle_basis = 1, shuffle_amount = 100}, 2), {65, 193})
  luaunit.assert_equals(onsets({division = 1 / 4, delay = 0.5, swing_or_shuffle = 2,
    shuffle_feel = 2, shuffle_basis = 1, shuffle_amount = 100}, 2), {1, 107})
end
