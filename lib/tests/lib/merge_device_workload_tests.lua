-- Host evidence for the Interlock device-timing campaign
-- (docs/musical-merge-extensions-plan.md §1.4 "Device acceptance";
-- characterisation of the approved plan, README "Merge Shape" defers the
-- Interlock claims to it). The device campaign (tests/behaviour/
-- hardware_performance.py, PERF-MERGE-HW-*) sends
-- tests/behaviour/merge_device_workload.lua to the norns; this runs the very
-- same chunk against the production modules in the host harness and proves the
-- per-admission semantics the device assertions expect: supported status,
-- leader-cycle and anchor counts at the budget, zero leader-plan builds, every
-- candidate removed with INTERLOCK CH01 or none, followers wrapping together,
-- and edit propagation to every follower within its current cycle. It does not
-- measure timing; the device qualification remains outstanding.

local merge_state = include("mosaic/lib/musical_merge/state")
local merge_timeline = include("mosaic/lib/musical_merge/timeline")

local function workload()
  _MOSAIC_MERGE_WORKLOAD = nil
  local value = dofile("../../tests/behaviour/merge_device_workload.lua")
  luaunit.assert_is(_MOSAIC_MERGE_WORKLOAD, value)
  return value
end

local function stop_transport()
  local saved_nb, saved_handler, saved_stop = rawget(_G, "nb"), rawget(_G, "norns_param_state_handler"), m_midi.stop
  rawset(_G, "nb", {stop_all = function() end})
  rawset(_G, "norns_param_state_handler", include("mosaic/lib/devices/norns_param_state_handler"))
  m_midi.stop = function() end
  local ok, err = pcall(function() m_clock:stop() end)
  rawset(_G, "nb", saved_nb); rawset(_G, "norns_param_state_handler", saved_handler); m_midi.stop = saved_stop
  if not ok then error(err, 0) end
end

-- The PERF-002 dense project: pattern 1 trigs steps 1..16 on every channel.
local function dense_project()
  program.init(); globals.reset(); params.reset(); memory.init(); merge_state.reset(); merge_timeline.stop()
  program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  for step = 1, 16 do song.patterns[1].trig_values[step] = 1 end
  for number = 1, 16 do
    program.get().devices[number].midi_channel = number
    song.channels[number].selected_patterns = {[1] = true}
    song.channels[number].start_trig = {1, 4}; song.channels[number].end_trig = {16, 4}
  end
  m_clock.init()
  return song
end

local FIELDS = {"kind", "time", "pulse", "channel", "k", "status", "cycles", "anchors", "plan_builds",
  "eligible", "admitted", "candidates", "removed", "other", "leader_trig"}

local function builds(rows, channel)
  local result = {}
  for _, row in ipairs(rows) do
    if row[1] == 1 and (channel == nil or row[4] == channel) then
      local named = {}
      for index, name in ipairs(FIELDS) do named[name] = row[index] end
      result[#result + 1] = named
    end
  end
  return result
end

-- Runs `pulses` pulses with the recorder installed; `at_pulse(n)` may edit.
local function play(W, variant, pulses, at_pulse)
  local song = dense_project()
  local readback = W.configure(variant, "enabled")
  luaunit.assert_not_nil(readback:match("^__MERGE_CONFIG__" .. variant .. "|enabled|"), readback)
  luaunit.assert_equals(W.install(W.LEADER_PATTERN):match("__MERGE_REC_INSTALLED__"), "__MERGE_REC_INSTALLED__")
  local ok, err = pcall(function()
    m_clock:start()
    for pulse = 1, pulses do
      if at_pulse then at_pulse(pulse, song) end
      m_clock.get_clock_lattice():pulse()
    end
    stop_transport()
  end)
  local rows = W.rows()
  W.remove()
  if not ok then error(err, 0) end
  return rows, song
end

-- The grid trig tap in the Trigger editor (trigger_edit_page.lua) toggles the
-- stored trig and requests the source rebuild.
local function toggle_leader_trig(W, song)
  local value = song.patterns[W.LEADER_PATTERN]
  value.trig_values[1] = value.trig_values[1] == 1 and 0 or 1
  pattern.update_source_working_patterns(song, W.LEADER_PATTERN)
  return value.trig_values[1]
end

local function assert_wraps_together(rows, followers)
  local first_pulse = {}
  for _, row in ipairs(builds(rows)) do
    if followers[row.channel] and row.k >= 1 then
      first_pulse[row.k] = first_pulse[row.k] or {}
      local seen = first_pulse[row.k]
      if seen[row.channel] == nil then seen[row.channel] = row.pulse end
    end
  end
  local wraps = 0
  for k, seen in pairs(first_pulse) do
    local pulse
    for channel in pairs(followers) do
      luaunit.assert_not_nil(seen[channel], "follower " .. channel .. " built cycle " .. k)
      pulse = pulse or seen[channel]
      luaunit.assert_equals(seen[channel], pulse, "cycle " .. k .. " wrap pulse ch" .. channel)
    end
    wraps = wraps + 1
  end
  luaunit.assert_true(wraps >= 1, "at least one follower wrap observed")
end

local function followers_2_to_16()
  local result = {}
  for number = 2, 16 do result[number] = true end
  return result
end

function test_merge_device_workload_steady_admissions_follow_the_plan()
  local W = workload()
  local rows = builds(play(W, "STEADY", 24 * 16 * 3 + 12), 2)
  luaunit.assert_true(#rows >= 3, #rows)
  local seen_k = {}
  for _, row in ipairs(rows) do
    -- Cycle 0 (and the build at Start, before the origin: k < 0) clips the
    -- support at the origin: leader cycles 0 and 1. Later cycles meet 3.
    local cycles = row.k <= 0 and 2 or 3
    luaunit.assert_equals({row.status, row.cycles, row.anchors, row.plan_builds},
      {1, cycles, 4 * cycles, 0}, "k=" .. row.k)
    -- Window 1 around leader anchors 1, 5, 9, 13 (and the next cycle's 1)
    -- removes 10 of the 14 candidates; Amount 100 admits the other 4.
    luaunit.assert_equals({row.candidates, row.removed, row.other, row.eligible, row.admitted},
      {14, 10, 0, 4, 4}, "k=" .. row.k)
    -- The recorder must see the leader's real anchor (step 1 of its anchor
    -- pattern): the device oracle picks its expectation from this.
    luaunit.assert_equals(row.leader_trig, 1, "k=" .. row.k)
    seen_k[row.k] = true
  end
  luaunit.assert_true(seen_k[1] and seen_k[2] and seen_k[3], "three wraps observed")
end

function test_merge_device_workload_worst_admission_is_exactly_at_the_budget()
  local W = workload()
  local recorded = play(W, "WORST", 24 * 64 + 24 * 64 + 12)
  local followers = followers_2_to_16()
  local count = 0
  for _, row in ipairs(builds(recorded)) do
    if followers[row.channel] then
      luaunit.assert_equals({row.status, row.cycles, row.anchors, row.plan_builds},
        {1, 64, 64, 0}, "ch" .. row.channel .. " k=" .. row.k)
      luaunit.assert_equals({row.candidates, row.removed, row.other, row.eligible, row.admitted},
        {31, 31, 0, 0, 0}, "ch" .. row.channel .. " k=" .. row.k)
      count = count + 1
    elseif row.channel == 1 then
      luaunit.assert_equals(row.status, 0, "the leader has no Interlock record")
    end
  end
  luaunit.assert_true(count >= 30, count)
  assert_wraps_together(recorded, followers)
end

-- EDIT: the leader's single anchor trig toggled off and on mid-cycle. Every
-- follower's first admission after each edit shows the new state and is a
-- rebuild inside its current cycle (propagation), not its next wrap.
local function assert_edit_propagation(recorded, edits, followers, on, off)
  local rows = builds(recorded)
  for _, edit in ipairs(edits) do
    for channel in pairs(followers) do
      local first
      for index = edit.after + 1, #rows do
        if rows[index].channel == channel then first = rows[index]; break end
      end
      luaunit.assert_not_nil(first, "ch" .. channel .. " rebuilt after the edit at pulse " .. edit.pulse)
      luaunit.assert_equals(first.k, edit.k[channel], "ch" .. channel .. " rebuilt within its cycle")
      luaunit.assert_equals(first.leader_trig, edit.state)
    end
  end
  for _, row in ipairs(rows) do
    if followers[row.channel] then
      local expected = row.leader_trig == 1 and on or off
      luaunit.assert_equals({row.status, row.cycles, row.anchors, row.plan_builds, row.candidates, row.removed,
        row.other, row.eligible, row.admitted}, expected, "ch" .. row.channel .. " k=" .. row.k ..
        " trig=" .. row.leader_trig)
    end
  end
end

local function edit_recorder(W, followers, edits, pulses)
  return function(pulse, song)
    for _, at in ipairs(pulses) do
      if pulse == at then
        local k = {}
        for channel in pairs(followers) do k[channel] = merge_timeline.k(channel) end
        edits[#edits + 1] = {pulse = pulse, after = #builds(W.rows()), k = k, state = toggle_leader_trig(W, song)}
      end
    end
  end
end

function test_merge_device_workload_edit_toggles_reach_every_follower_in_its_cycle()
  local W = workload()
  local followers, edits = followers_2_to_16(), {}
  local recorded = play(W, "WORST", 24 * 64 * 2 + 12,
    edit_recorder(W, followers, edits, {24 * 20 + 5, 24 * 40 + 5, 24 * 84 + 5}))
  luaunit.assert_equals(#edits, 3)
  luaunit.assert_equals({edits[1].state, edits[2].state, edits[3].state}, {0, 1, 0})
  assert_edit_propagation(recorded, edits, followers, {1, 64, 64, 0, 31, 31, 0, 0, 0}, {1, 64, 0, 0, 31, 0, 0, 31, 31})
  assert_wraps_together(recorded, followers)
end

function test_merge_device_workload_dense_admission_has_the_maximum_anchors()
  local W = workload()
  local followers, edits = followers_2_to_16(), {}
  -- One /4 follower cycle is 64 beats; cross one wrap, and toggle the leader's
  -- step-1 anchor off and on again inside the first and second cycles.
  local recorded = play(W, "DENSE", 96 * 64 + 96 * 8,
    edit_recorder(W, followers, edits, {96 * 16 + 7, 96 * 32 + 7, 96 * 66 + 7}))
  luaunit.assert_equals({edits[1].state, edits[2].state, edits[3].state}, {0, 1, 0})
  assert_edit_propagation(recorded, edits, followers, {1, 64, 4096, 0, 64, 64, 0, 0, 0}, {1, 64, 4032, 0, 64, 0, 0, 64, 64})
  assert_wraps_together(recorded, followers)
end

function test_merge_device_workload_off_mode_has_no_merge_configuration()
  local W = workload()
  for _, variant in ipairs({"STEADY", "WORST", "DENSE"}) do
    local song = dense_project()
    local readback = W.configure(variant, "off")
    for number = 1, 16 do luaunit.assert_nil(song.channels[number].musical_merge, variant .. " ch" .. number) end
    luaunit.assert_nil(readback:find("foundation", 1, true), readback)
    luaunit.assert_equals(song.channels[1].clock_mods.name, variant == "DENSE" and "x16" or "/1")
  end
end
