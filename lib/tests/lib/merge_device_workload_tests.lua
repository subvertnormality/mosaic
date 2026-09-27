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
  "eligible", "admitted", "candidates", "removed", "other", "leader_trig", "build_us", "heap_kb", "heap_delta_bytes"}

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

-- The device runner edits by grid taps: runner.synthetic_grid evaluates
-- _norns.grid.key(id, x, y, 1) and, 0.04 s later, _norns.grid.key(id, x, y, 0)
-- (hardware_performance.run_merge_window -> Ui.tap_step -> hardware_tap).
-- Here the same two calls reach the real m_grid key handler, press module and
-- Trigger editor, through the stock norns routing (_norns.grid.key -> the
-- connected vport's key). Pages Mosaic does not reach in these taps are
-- inert stand-ins; the long-press timer (clock.sleep(1)) does not elapse
-- during a 0.04 s tap. Every global the grid modules set is restored.
local function with_real_grid(body)
  local saved_globals = {}
  for name, value in pairs(_G) do saved_globals[name] = value end
  local saved_norns_grid, saved_run, saved_cancel = _norns.grid, clock.run, clock.cancel
  local real_include = include
  local function inert_page()
    return {init = function() end, register_press = function() end, register_draws = function() end}
  end
  local inert = {
    ["mosaic/lib/pages/channel_edit_page/channel_edit_page"] = inert_page(),
    ["mosaic/lib/pages/song_edit_page/song_edit_page"] = inert_page(),
    ["mosaic/lib/pages/scale_edit_page/scale_edit_page"] = inert_page(),
    ["mosaic/lib/pages/note_edit_page/note_edit_page"] = inert_page(),
    ["mosaic/lib/pages/velocity_edit_page/velocity_edit_page"] = inert_page(),
  }
  local vport = {all = function() end, refresh = function() end, led = function() end}
  local ok, err = pcall(function()
    include = function(path) return inert[path] or real_include(path) end
    grid = {connect = function() return vport end}
    g = vport
    tooltip = {show = function() end}
    save_confirm = {cancel = function() end}
    autosave_reset = function() end
    local m_grid_under_test = include("mosaic/lib/m_grid")
    m_grid_under_test.init()
    include = real_include
    luaunit.assert_is_function(vport.key)
    -- Stock norns lua/core/grid.lua: the key callback of the device's vport.
    _norns.grid = {key = function(id, x, y, z) if vport.key then vport.key(x, y, z) end end}
    local timers = 0
    clock.run = function() timers = timers + 1; return timers end
    clock.cancel = function() end
    body(function(x, y, z) return _norns.grid.key(1, x, y, z) end)
  end)
  _norns.grid, clock.run, clock.cancel = saved_norns_grid, saved_run, saved_cancel
  for name in pairs(_G) do if saved_globals[name] == nil then rawset(_G, name, nil) end end
  for name, value in pairs(saved_globals) do rawset(_G, name, value) end
  if not ok then error(err, 0) end
end

local STEP_ONE = {1, 4}       -- control_cell('step', 1)
local PATTERN_SELECT_Y = 1    -- control_cell('pattern_select', n) = (n, 1)

function test_merge_device_workload_records_grid_tap_edits_with_their_effect()
  local W = workload()
  local followers = followers_2_to_16()
  local rows, taps = nil, {}
  local song = dense_project()
  with_real_grid(function(key)
    W.configure("WORST", "enabled")
    program.set_selected_page(pages.pages.trigger_edit_page)
    -- As the runner: the Trigger editor on the leader's anchor pattern, by a tap.
    key(W.LEADER_PATTERN, PATTERN_SELECT_Y, 1); key(W.LEADER_PATTERN, PATTERN_SELECT_Y, 0)
    luaunit.assert_equals(program.get().selected_pattern, W.LEADER_PATTERN)
    luaunit.assert_equals(W.install(W.LEADER_PATTERN), "__MERGE_REC_INSTALLED__2")
    local ok, failure = pcall(function()
      m_clock:start()
      -- Step-1 taps inside follower cycles 0, 0 and 1; each held two pulses
      -- (0.04 s at 130 bpm is about two 24 ppqn pulses).
      local downs = {24 * 20 + 5, 24 * 40 + 5, 24 * 84 + 5}
      for pulse = 1, 24 * 64 * 2 + 12 do
        for _, at in ipairs(downs) do
          if pulse == at then
            taps[#taps + 1] = {before = song.patterns[W.LEADER_PATTERN].trig_values[1]}
            key(STEP_ONE[1], STEP_ONE[2], 1)
          elseif pulse == at + 2 then
            key(STEP_ONE[1], STEP_ONE[2], 0)
            taps[#taps].after = song.patterns[W.LEADER_PATTERN].trig_values[1]
          end
        end
        m_clock.get_clock_lattice():pulse()
      end
      stop_transport()
    end)
    rows = W.rows()
    W.remove()
    if not ok then error(failure, 0) end
  end)
  -- The taps are real edits: each toggles the leader's anchor trig.
  luaunit.assert_equals(#taps, 3)
  luaunit.assert_equals({taps[1].before, taps[1].after, taps[2].after, taps[3].after}, {1, 0, 1, 0})
  -- The recorder sees every edge on the step cell, and the leader trig it
  -- reports changes on the edge that applied the edit.
  local edges, edits, state = {}, {}, nil
  for index, row in ipairs(rows) do
    if row[1] == 1 then
      state = row[15]
    elseif (row[1] == 2 or row[1] == 3) and row[4] == STEP_ONE[1] and row[5] == STEP_ONE[2] then
      edges[#edges + 1] = row[1]
      -- The device oracle's rule (merge_workloads.admission_oracle): an edit
      -- is a step-cell key row whose leader trig differs from the state before.
      if state ~= nil and row[6] ~= state then
        local k = {}
        for c = 2, 16 do k[c] = row[5 + c] end
        edits[#edits + 1] = {index = index, state = row[6], k = k}
      end
      state = row[6]
    end
  end
  luaunit.assert_equals(#edits, 3)
  luaunit.assert_equals(edges, {2, 3, 2, 3, 2, 3})
  luaunit.assert_equals({edits[1].state, edits[2].state, edits[3].state}, {0, 1, 0})
  -- Propagation from the recorded edit: every follower's next build shows the
  -- new state, inside the follower's current cycle.
  for _, edit in ipairs(edits) do
    for channel in pairs(followers) do
      local first
      for index = edit.index + 1, #rows do
        if rows[index][1] == 1 and rows[index][4] == channel then first = rows[index]; break end
      end
      luaunit.assert_not_nil(first, "ch" .. channel .. " rebuilt after the edit")
      luaunit.assert_equals({first[15], first[5]}, {edit.state, edit.k[channel]}, "ch" .. channel)
    end
  end
end

-- The device row pattern of PERF-MERGE-HW-WORST at c2ad05a9: every wrap pulse
-- builds the 15 followers and the leader, and each global pattern end (song
-- mode on, the norns default) also sweeps all 16 channels
-- (song_transition: update_working_patterns, one channel per scheduler tick
-- after the pulse; the host scheduler mock runs the sweep at once). The sweep also heals working patterns patched in place
-- (memory event handlers), so it stays; it must be cheap: every follower
-- build after the stopped configuration, from the first wrap after Start on,
-- is served by the content-validated memo (legacy merge and plan).
function test_merge_device_workload_wrap_and_song_end_sweep_builds_hit_the_memo()
  local W = workload()
  dense_project()
  params:set("song_mode", 2)
  W.configure("WORST", "enabled")
  local builds = {}
  local lattice
  local ok, err = pcall(function()
    local memo = pattern.wrap_memo_stats
    local merge = pattern.get_and_merge_patterns
    pattern.get_and_merge_patterns = function(c, ...)
      local legacy, plan = memo.legacy_hits, memo.plan_hits
      local result = merge(c, ...)
      builds[#builds + 1] = {pulse = lattice and lattice.transport or -1, channel = c,
        -- A wrap build carries the pulse token (get_and_merge_patterns' 9th argument).
        in_pulse = type(select(8, ...)) == "table",
        legacy_hit = memo.legacy_hits > legacy, plan_hit = memo.plan_hits > plan}
      return result
    end
    m_clock:start()
    lattice = m_clock.get_clock_lattice()
    for _ = 1, 24 * 64 * 2 + 12 do
      if scheduler and scheduler.update then scheduler.update() end   -- between pulses
      lattice:pulse()
    end
    pattern.get_and_merge_patterns = merge
    stop_transport()
  end)
  params:set("song_mode", nil)
  if not ok then error(err, 0) end
  local wraps, sweeps = {}, {}
  for _, row in ipairs(builds) do
    if row.channel >= 2 then
      local into = row.in_pulse and wraps or sweeps
      into[row.pulse] = into[row.pulse] or {}
      into[row.pulse][#into[row.pulse] + 1] = row
      luaunit.assert_true(row.legacy_hit and row.plan_hit,
        string.format("ch%d at pulse %d (%s) served by the memo", row.channel, row.pulse, row.in_pulse and "wrap" or "sweep"))
    end
  end
  -- Two wraps after Start, each with its 15 follower builds and one sweep.
  local wrap_pulses, sweep_pulses = {}, {}
  for pulse, rows in pairs(wraps) do wrap_pulses[#wrap_pulses + 1] = pulse; luaunit.assert_equals(#rows, 15, "wrap " .. pulse) end
  for pulse, rows in pairs(sweeps) do sweep_pulses[#sweep_pulses + 1] = pulse; luaunit.assert_equals(#rows, 15, "sweep " .. pulse) end
  table.sort(wrap_pulses); table.sort(sweep_pulses)
  luaunit.assert_equals(wrap_pulses, {24 * 64 + 1, 24 * 64 * 2 + 1})
  luaunit.assert_equals(sweep_pulses, {24 * 64 + 1, 24 * 64 * 2 + 1})
end

-- Plan §1.4 Start latency compares the enabled window with the same workload
-- with Merge Shape Off; the Off window's followers use a legacy trig merge
-- mode chosen so the first step plays the same notes (channels and pitches).
local function first_step(W, variant, mode, trig_override)
  dense_project()
  W.configure(variant, mode)
  if trig_override then
    for c = 1, 16 do program.get_song_pattern(1).channels[c].trig_merge_mode = trig_override end
    pattern.update_working_patterns(program.get_song_pattern(1))
  end
  local before = #midi_note_on_events
  local notes = {}
  local ok, err = pcall(function()
    m_clock:start()   -- plays the first step (the lattice's immediate first pulse)
    for index = before + 1, #midi_note_on_events do
      local event = midi_note_on_events[index]
      notes[#notes + 1] = event[3] .. ":" .. event[1]
    end
    stop_transport()
  end)
  if not ok then error(err, 0) end
  table.sort(notes)
  return notes
end

function test_merge_device_workload_off_window_plays_the_enabled_first_step()
  local W = workload()
  for _, variant in ipairs({"STEADY", "WORST", "DENSE"}) do
    local enabled = first_step(W, variant, "enabled")
    luaunit.assert_true(#enabled > 0, variant)
    luaunit.assert_equals(first_step(W, variant, "off"), enabled, variant)
  end
  -- The previous Off baseline (legacy "skip" everywhere) played a different
  -- first step: WORST's patterns 7 and 8 coincide on step 1 and cancel.
  luaunit.assert_not_equals(first_step(W, "WORST", "off", "skip"), first_step(W, "WORST", "enabled"))
end

function test_merge_device_workload_build_rows_carry_build_time_and_heap()
  local W = workload()
  local rows = builds(play(W, "STEADY", 24 * 16 + 12), 2)
  luaunit.assert_true(#rows > 0)
  for _, row in ipairs(rows) do
    luaunit.assert_true(row.build_us >= 0)
    luaunit.assert_true(row.heap_kb > 0)
    luaunit.assert_equals(math.type(row.heap_delta_bytes), "integer")
  end
end
