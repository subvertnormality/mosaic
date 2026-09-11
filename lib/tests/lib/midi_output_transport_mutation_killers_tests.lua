-- Mutation killers for lib/clock/midi_output_transport.lua, driven directly through a fake
-- native MIDI output boundary (clock.midi.subscribe_output) and a recording lattice.
-- characterisation: README does not describe MIDI clock output alignment; these pin the
-- module's own contract (one lattice pulse per ppqn/24 output tick, counted from the source
-- origin, with the receiver's pulse count preserved across a source epoch change).
local transport = include("mosaic/lib/clock/midi_output_transport")

-- Install fake native clock hooks, run body, and restore them even on failure.
local function with_boundary(body)
  local old_midi, old_run, old_cancel = clock.midi, clock.run, clock.cancel
  local env = {subscriptions = {}, cancelled_outputs = {}, runs = 0, cancelled_runs = {}}
  clock.midi = {
    subscribe_output = function(callbacks)
      env.subscriptions[#env.subscriptions + 1] = callbacks
      return "sub" .. #env.subscriptions
    end,
    cancel_output = function(handle) env.cancelled_outputs[#env.cancelled_outputs + 1] = handle end
  }
  -- Intermediate pulses are scheduler work; these cases drive output ticks only.
  clock.run = function() env.runs = env.runs + 1; return "run" .. env.runs end
  clock.cancel = function(handle) env.cancelled_runs[#env.cancelled_runs + 1] = handle end
  local ok, err = pcall(body, env)
  clock.midi, clock.run, clock.cancel = old_midi, old_run, old_cancel
  if not ok then error(err, 0) end
end

local function recording_lattice()
  local l = {ppqn = 96, pulses = 0, starts = 0, auto = true}
  function l:pulse() self.pulses = self.pulses + 1 end
  function l:start() self.starts = self.starts + 1 end
  return l
end

function test_mout_available_requires_a_subscribe_output_function()
  local old_midi = clock.midi
  local ok, err = pcall(function()
    clock.midi = nil
    luaunit.assert_nil(transport.available())
    clock.midi = {}
    luaunit.assert_equals(transport.available(), false)
    clock.midi = {subscribe_output = "not a function"}
    luaunit.assert_equals(transport.available(), false)
    clock.midi = {subscribe_output = function() end}
    luaunit.assert_equals(transport.available(), true)
  end)
  clock.midi = old_midi
  if not ok then error(err, 0) end
end

-- Without a source origin the first output tick is pulse zero: exactly one lattice pulse,
-- whatever the absolute deadline. Later ticks follow the deadline (4 pulses per F8 at
-- 96 ppqn), including a skipped tick inside one epoch.
function test_mout_first_tick_is_pulse_zero_and_later_ticks_follow_the_deadline()
  with_boundary(function(env)
    local lattice = recording_lattice()
    local starts = 0
    local cancel = transport.start(lattice, function() starts = starts + 1 end, nil, nil)
    luaunit.assert_false(lattice.auto)
    luaunit.assert_equals(#env.subscriptions, 1)
    local cb = env.subscriptions[1]
    cb.before()
    luaunit.assert_equals(starts, 1)
    luaunit.assert_equals(lattice.pulses, 0, "Nothing is pulsed before the first F8 is sent")
    cb.after(0.5, 7)
    luaunit.assert_equals(lattice.starts, 1)
    luaunit.assert_equals(lattice.pulses, 1)
    cb.before()
    cb.after(0.5 + 1 / 24, 7)
    luaunit.assert_equals(lattice.pulses, 5)
    -- One F8 later than expected (a skipped tick): catch up from the deadline.
    cb.before()
    cb.after(0.5 + 3 / 24, 7)
    luaunit.assert_equals(lattice.pulses, 13)
    luaunit.assert_equals(starts, 1, "Start is sent once, before the first F8")
    luaunit.assert_equals(lattice.starts, 1, "The lattice is started once")
    cancel()
    luaunit.assert_equals(env.cancelled_outputs, {"sub1"})
  end)
end

-- A native source epoch change keeps the receiver's pulse count: the next tick is exactly
-- ppqn/24 pulses later regardless of the new deadline, and later ticks count from there.
function test_mout_epoch_change_preserves_the_receiver_pulse_count()
  with_boundary(function(env)
    local lattice = recording_lattice()
    transport.start(lattice, function() end, nil, nil)
    local cb = env.subscriptions[1]
    cb.after(2.0, 1)
    cb.after(2.0 + 1 / 24, 1)
    luaunit.assert_equals(lattice.pulses, 5)
    local runs_before = env.runs
    cb.after(10.0, 2)
    luaunit.assert_equals(lattice.pulses, 9)
    luaunit.assert_equals(env.runs, runs_before + 1, "An epoch change restarts intermediate pulses")
    cb.after(10.0 + 1 / 24, 2)
    luaunit.assert_equals(lattice.pulses, 13)
    luaunit.assert_equals(env.runs, runs_before + 1, "A same-epoch tick does not restart them")
    luaunit.assert_equals(lattice.starts, 1)
  end)
end

-- A supplied source origin (incoming MIDI Start = beat zero) makes a late first tick catch
-- up every pulse since that origin.
function test_mout_source_origin_catches_up_pulses_since_beat_zero()
  with_boundary(function(env)
    local lattice = recording_lattice()
    transport.start(lattice, function() end, nil, 0)
    env.subscriptions[1].after(0.5, 3)
    luaunit.assert_equals(lattice.pulses, 49)
  end)
  with_boundary(function(env)
    local lattice = recording_lattice()
    transport.start(lattice, function() end, nil, 1.25)
    env.subscriptions[1].after(1.5, 3)
    luaunit.assert_equals(lattice.pulses, 25)
  end)
end
