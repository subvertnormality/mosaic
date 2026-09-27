-- MM-12 nominal Space (planned occupancy). Contract:
-- docs/musical-merge-extensions-plan.md §6 (gate semantics, scheduling policy,
-- residual MM-12-AUDIBLE) on the common time, prediction, freshness and query
-- support of §1 and the candidate pipeline of §3. README "Merge Shape" still
-- defers Space to the MM-11 UI/docs card, so every assertion is a
-- characterisation of that approved plan, outside the current manual; "explicit
-- channel/step masks still win" is README "Merge Shape" behaviour. Nothing here
-- asserts audible silence: the reserved intervals are nominal planned
-- occupancy, and MM-12-AUDIBLE remains open (§6.3).

local merge_config = include("mosaic/lib/musical_merge/config")
local merge_state = include("mosaic/lib/musical_merge/state")
local merge_timeline = include("mosaic/lib/musical_merge/timeline")
local foundation_planner = include("mosaic/lib/musical_merge/foundation")
local space = include("mosaic/lib/musical_merge/space")
local space_gate = include("mosaic/lib/musical_merge/space_gate")
local transaction = include("mosaic/lib/optional_config_transaction")
local pattern_module = include("mosaic/lib/pattern")
local strum_descriptor = include("mosaic/lib/musical_resolution/strum_descriptor")
local chord_order = include("mosaic/lib/musical_resolution/chord_order")
local chord_timing = include("mosaic/lib/clock/chord_timing")
local divisions = include("mosaic/lib/clock/divisions")
local harness = include("mosaic/lib/tests/helpers/merge_playback_harness")

local FOLLOWER, LEADER, OTHER = 1, 2, 3
local D1 = {name = "/1", value = 1, type = "clock_division"}
local D1_5 = {name = "/1.5", value = 1.5, type = "clock_division"}
local X2 = {name = "x2", value = 2, type = "clock_multiplication"}
local X3 = {name = "x3", value = 3, type = "clock_multiplication"}
local X4 = {name = "x4", value = 4, type = "clock_multiplication"}

local pulses, stop_transport = harness.pulses, harness.stop_transport

local function foundation(anchor, extra)
  local value = merge_config.new()
  value.mode, value.anchor = "foundation", anchor
  for key, item in pairs(extra or {}) do value[key] = item end
  return value
end

local function set_range(channel, first, last)
  channel.start_trig = {(first - 1) % 16 + 1, 4 + (first - 1) // 16}
  channel.end_trig = {(last - 1) % 16 + 1, 4 + (last - 1) // 16}
end

local function trigs(pattern_values, steps)
  for step = 1, 64 do pattern_values.trig_values[step] = 0 end
  for _, step in ipairs(steps) do pattern_values.trig_values[step] = 1 end
end

-- Stock parameter slots of a channel (lib/helpers/functions.lua) and their Off
-- values (lib/devices/device_map.lua stock_params).
local STOCK = {trig_probability = 6, chord_strum = 8, chord_arp = 9, chord_spread = 10,
  chord_acceleration = 11, chord_velocity_modifier = 12, chord_strum_pattern = 13, mute_root_note = 14}
local STOCK_OFF = {trig_probability = -1, chord_strum = 0, chord_arp = 0, chord_spread = 0,
  chord_acceleration = 0, chord_velocity_modifier = 0, chord_strum_pattern = 0, mute_root_note = 0}

local function set_stock(number, kind, value)
  params:add("midi_device_params_channel_" .. number .. "_" .. STOCK[kind], {val = value, default = STOCK_OFF[kind]})
end

local function division_index(value)
  for index, entry in ipairs(divisions.note_divisions) do if entry.value == value then return index end end
  error("no note division " .. tostring(value))
end

-- Follower channel 1: anchor pattern 3 (no trigs unless given), candidate
-- pattern 4 (every step), Space leader channel 2 (legacy merge unless a
-- leader configuration is given: a leader in legacy merge still sounds).
-- Leader channel 2 plays pattern 1.
local function setup(options)
  options = options or {}
  program.init(); globals.reset(); params.reset(); memory.init()
  merge_state.reset(); merge_timeline.stop()
  program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  song.global_pattern_length = options.global_length or 64
  for number = 1, 16 do program.get().devices[number].midi_channel = number end
  local follower, leader = song.channels[FOLLOWER], song.channels[LEADER]
  follower.clock_mods = options.follower_mod or D1
  leader.clock_mods = options.leader_mod or D1
  set_range(follower, 1, options.follower_last or 8)
  set_range(leader, 1, options.leader_last or 16)
  trigs(song.patterns[1], options.leader_trigs or {1})
  for step, value in pairs(options.leader_lengths or {}) do song.patterns[1].lengths[step] = value end
  trigs(song.patterns[3], options.follower_anchors or {})
  local all = {}
  for step = 1, 64 do all[#all + 1] = step end
  trigs(song.patterns[4], options.candidates or all)
  follower.selected_patterns = {[3] = true, [4] = true}
  leader.selected_patterns = options.leader_patterns or {[1] = true}
  if options.leader_config then leader.musical_merge = options.leader_config end
  if options.before_build then options.before_build(song) end
  if options.follower_config ~= false then
    follower.musical_merge = options.follower_config or
      foundation(3, {space = {leader = LEADER, release = options.release or 0}})
  end
  for number = 1, 16 do pattern_module.update_working_pattern(number, song) end
  return song, follower, leader
end

local function build(song, number)
  local channel = song.channels[number]
  return pattern_module.get_and_merge_patterns(number, channel.trig_merge_mode, channel.note_merge_mode,
    channel.velocity_merge_mode, channel.length_merge_mode, song)
end

local function blocked_steps(result)
  local steps = {}
  for step in pairs(result.foundation.space.blocked) do steps[#steps + 1] = step end
  table.sort(steps)
  return steps
end

local function reason_steps(result, reason)
  local steps = {}
  for step = 1, 64 do
    local list = result.foundation.reason_lists and result.foundation.reason_lists[step]
    for _, value in ipairs(list or {}) do if value == reason then steps[#steps + 1] = step end end
  end
  return steps
end

local function additions(result)
  local steps = {}
  for step = 1, 64 do if result.foundation.roles[step] == "addition" then steps[#steps + 1] = step end end
  return steps
end

-- The same follower build with no Interlock or Space leader.
local function without_filters(song)
  local follower = song.channels[FOLLOWER]
  local saved = follower.musical_merge
  local plain = merge_config.canonicalize(saved)
  plain.interlock = {leader = nil, window = 0}
  plain.space = {leader = nil, release = 0}
  follower.musical_merge = plain
  local record = merge_state.peek(song, FOLLOWER)
  local active = record and record.active
  if record then record.active = plain end
  local result = build(song, FOLLOWER)
  follower.musical_merge = saved
  if record then record.active = active end
  return result
end

local function lock(channel, step, slot, value)
  channel.step_trig_lock_banks[step] = channel.step_trig_lock_banks[step] or {}
  channel.step_trig_lock_banks[step][slot] = value
end

-- The descriptor the playback path schedules with (step.lua binds exactly this
-- pair), on the playback inputs as floats.
local descriptor_root_now, descriptor_chord, descriptor_root_later =
  strum_descriptor.new(chord_order.index, chord_timing.delay)

-- The largest scheduled delay among the voices a step schedules (nil when it
-- schedules none), from the actual descriptor outputs.
local function descriptor_tail(masks, pattern, mute, division, spread, acceleration, arp)
  local has = false
  for i = 1, 4 do if masks[i] and masks[i] ~= 0 then has = true end end
  if arp then return (has or not mute) and 0 or nil end
  local voices, tail = false, 0
  if descriptor_root_now(pattern, mute) then voices = true end
  if has then
    for i = 1, 4 do
      local number, delay = descriptor_chord(i, masks, pattern, division, spread, acceleration)
      if number then voices = true; if delay > tail then tail = delay end end
    end
  end
  local later = descriptor_root_later(pattern, mute, division, spread, acceleration)
  if later then voices = true; if later > tail then tail = later end end
  return voices and tail or nil
end

-- ---------------------------------------------------------------------------
-- §6.1 exact rationals of stored floats.

function test_space_gate_rational_of_recovers_exact_fractions()
  luaunit.assert_equals(space_gate.rational_of(3), {3, 1})
  luaunit.assert_equals(space_gate.rational_of(14.5), {29, 2})
  luaunit.assert_equals(space_gate.rational_of(10 / 3), {10, 3})
  luaunit.assert_equals(space_gate.rational_of(1 / 24), {1, 24})
  luaunit.assert_equals(space_gate.rational_of(-0.75), {-3, 4})
  -- An up merge of {1, 10, 10} computed in floats: average + (max − min).
  luaunit.assert_equals(space_gate.rational_of((1 + 10 + 11) / 3 + 10), {52, 3})
  luaunit.assert_equals(space_gate.rational_of((1 + 2 + 2) / 3 + 1), {8, 3})
  luaunit.assert_nil(space_gate.rational_of(0 / 0))
  luaunit.assert_nil(space_gate.rational_of(math.huge))
  luaunit.assert_nil(space_gate.rational_of(-math.huge))
  luaunit.assert_nil(space_gate.rational_of(nil))
  luaunit.assert_nil(space_gate.rational_of("3"))
end

-- ---------------------------------------------------------------------------
-- §6.1 articulation snapshot: descriptor-equivalent tails.

-- Every strum pattern (Off, forward, reverse, both alternations), sparse chord
-- slots, root-only strums, muted roots, strum divisions, spreads and negative
-- acceleration (including gaps that turn nonpositive): the snapshot's tail is
-- the largest delay the actual descriptor schedules, and a step that schedules
-- no voice has no gate.
function test_space_gate_tails_equal_the_strum_descriptor_outputs()
  local song = setup()
  local leader = song.channels[LEADER]
  local masks_list = {{0, 0, 0, 0}, {5, 0, 0, 0}, {0, 0, 7, 0}, {3, 0, 0, 9}, {1, 2, 3, 4}, {0, -2, 0, 0}}
  local checked, omitted, invalid = 0, 0, 0
  for _, masks in ipairs(masks_list) do
    leader.chord_one_mask, leader.chord_two_mask = masks[1], masks[2]
    leader.chord_three_mask, leader.chord_four_mask = masks[3], masks[4]
    for pattern = 0, 4 do
      for mute = 0, 1 do
        for _, strum in ipairs({0, 1, 5, 14}) do
          for _, spread in ipairs({0, 3, 8}) do
            for _, acceleration in ipairs({-5, -2, -1, 0, 1, 3}) do
              set_stock(LEADER, "chord_strum_pattern", pattern)
              set_stock(LEADER, "mute_root_note", mute)
              set_stock(LEADER, "chord_strum", strum)
              set_stock(LEADER, "chord_spread", spread)
              set_stock(LEADER, "chord_acceleration", acceleration)
              local record = space_gate.snapshot(leader, 1, 1)
              luaunit.assert_equals(record.status, "ok")
              local division = strum ~= 0 and divisions.note_divisions[strum].value or nil
              local spread_value = spread ~= 0 and divisions.note_division_values[spread] or 0
              local expected = descriptor_tail(masks, pattern ~= 0 and pattern or nil, mute == 1,
                division, spread_value, acceleration)
              local label = table.concat({table.concat(masks, ","), pattern, mute, strum, spread, acceleration}, " ")
              local actual = space_gate.tail(record, 1)
              if expected == nil then
                luaunit.assert_nil(actual, label)
                omitted = omitted + 1
              else
                luaunit.assert_not_nil(actual, label)
                luaunit.assert_true(math.abs(actual - expected) <= 1e-9, label .. " " .. actual .. " " .. expected)
              end
              if division and descriptor_chord(2, {1, 1, 1, 1}, 1, division, spread_value, acceleration) == nil then
                invalid = invalid + 1
              end
              checked = checked + 1
            end
          end
        end
      end
    end
  end
  luaunit.assert_equals(checked, 6 * 5 * 2 * 4 * 3 * 6)
  luaunit.assert_true(omitted > 0)
  luaunit.assert_true(invalid > 0)
end

-- Hand-computed cases in exact rationals: a forward strum over sparse slots
-- 1 and 3 at 1/4 schedules chord 3 at 3/4; a reverse root-only strum delays
-- the root by ordinal 4 (4 · 1/4 = 1) with no chord voice; a muted root with no
-- chord slot schedules nothing; the arp adds nothing to the gate.
function test_space_gate_hand_computed_tails_and_voiceless_steps()
  local song = setup()
  local leader = song.channels[LEADER]
  leader.chord_one_mask, leader.chord_three_mask = 3, 5
  set_stock(LEADER, "chord_strum", division_index(1 / 4))
  set_stock(LEADER, "chord_strum_pattern", 1)
  local record = space_gate.snapshot(leader, 1, 1)
  luaunit.assert_equals(record.tails[1], {3, 4})
  leader.chord_one_mask, leader.chord_three_mask = 0, 0
  set_stock(LEADER, "chord_strum_pattern", 2)
  record = space_gate.snapshot(leader, 1, 1)
  luaunit.assert_equals(record.tails[1], {1, 1})
  set_stock(LEADER, "mute_root_note", 1)
  record = space_gate.snapshot(leader, 1, 1)
  luaunit.assert_nil(record.tails[1])
  luaunit.assert_nil(space_gate.tail(record, 1))
  -- Arp: bounded by the gate length already. With a muted root and no chord
  -- slot the arp sequence is empty, so nothing sounds.
  set_stock(LEADER, "chord_arp", division_index(1 / 4))
  record = space_gate.snapshot(leader, 1, 1)
  luaunit.assert_nil(record.tails[1])
  leader.chord_one_mask = 4
  record = space_gate.snapshot(leader, 1, 1)
  luaunit.assert_equals(record.tails[1], {0, 1})
end

-- Per-step locks and parameter-slot values resolve with stock precedence
-- exactly as playback: a slot assignment reads its step lock, else the slot's
-- value; a lock at the slot's Off value suppresses the kind.
function test_space_gate_snapshot_resolves_per_step_locks_and_slot_values()
  local song = setup()
  local leader = song.channels[LEADER]
  leader.chord_two_mask = 7
  leader.trig_lock_params[1] = {id = "chord_strum", param_id = "space_slot_strum", off_value = 0, type = "stock"}
  params:add("space_slot_strum", {val = division_index(1 / 2), default = 0})
  lock(leader, 3, 1, division_index(1))
  lock(leader, 4, 1, 0)
  -- Step-chord masks override the channel's slots on one step.
  leader.step_chord_masks[5] = {0, 0, 0, 9}
  local record = space_gate.snapshot(leader, 1, 5)
  luaunit.assert_equals(record.status, "ok")
  luaunit.assert_equals(record.tails[1], {1, 1}) -- chord 2, ordinal 2 · 1/2
  luaunit.assert_equals(record.tails[3], {2, 1}) -- ordinal 2 · 1
  luaunit.assert_equals(record.tails[4], {0, 1}) -- Off lock: no strum
  luaunit.assert_equals(record.tails[5], {2, 1}) -- chord 4, ordinal 4 · 1/2
  luaunit.assert_equals(record.s_max, {2, 1})
end

-- A record is immutable: changing the captured inputs after construction
-- changes only a later record (§1.3 publication).
function test_space_gate_record_is_immutable_after_capture()
  local song = setup()
  local leader = song.channels[LEADER]
  leader.chord_one_mask = 2
  set_stock(LEADER, "chord_strum", division_index(1 / 4))
  local first = space_gate.snapshot(leader, 1, 2)
  set_stock(LEADER, "chord_strum", division_index(1))
  leader.chord_one_mask = 0
  leader.chord_four_mask = 3
  luaunit.assert_equals(first.tails[1], {1, 4})
  local second = space_gate.snapshot(leader, 1, 2)
  luaunit.assert_equals(second.tails[1], {4, 1})
  luaunit.assert_equals(first.tails[1], {1, 4})
end

-- Record construction and the follower build that uses it execute no
-- parameter lock, send no message, schedule nothing and consume no RNG.
function test_space_gate_construction_has_no_rng_lock_or_message_side_effects()
  local song = setup({leader_trigs = {1, 5}, leader_lengths = {[1] = 3}})
  local leader = song.channels[LEADER]
  leader.chord_one_mask, leader.chord_three_mask = 3, 5
  leader.trig_lock_params[1] = {id = "chord_strum", param_id = "space_slot_strum", off_value = 0, type = "stock"}
  params:add("space_slot_strum", {val = division_index(1 / 4), default = 0})
  lock(leader, 5, 1, division_index(1 / 2))
  set_stock(LEADER, "trig_probability", 50)
  local calls = {}
  local function counting(name, original)
    return function(...) calls[#calls + 1] = name; return original(...) end
  end
  local saved = {random = rawget(_G, "random"), math_random = math.random, set = params.set,
    delay_action = m_clock.delay_action, note_on = m_midi.note_on, cc = m_midi.cc, nrpn = m_midi.nrpn,
    process_params = step and step.process_params}
  rawset(_G, "random", counting("random", saved.random or math.random))
  math.random = counting("math.random", saved.math_random)
  params.set = counting("params:set", saved.set)
  m_clock.delay_action = counting("delay_action", saved.delay_action)
  m_midi.note_on = counting("note_on", saved.note_on)
  m_midi.cc = counting("cc", saved.cc or function() end)
  m_midi.nrpn = counting("nrpn", saved.nrpn or function() end)
  if step then step.process_params = counting("process_params", saved.process_params) end
  local ok, err = pcall(function()
    local before = #midi_note_on_events
    local record = space_gate.snapshot(leader, 1, 16)
    luaunit.assert_equals(record.status, "ok")
    local result = build(song, FOLLOWER)
    luaunit.assert_equals(result.foundation.space.status, "ok")
    luaunit.assert_equals(#midi_note_on_events, before)
  end)
  rawset(_G, "random", saved.random); math.random = saved.math_random; params.set = saved.set
  m_clock.delay_action = saved.delay_action; m_midi.note_on = saved.note_on
  m_midi.cc = saved.cc; m_midi.nrpn = saved.nrpn
  if step then step.process_params = saved.process_params end
  if not ok then error(err, 0) end
  luaunit.assert_equals(calls, {})
end

-- An input whose tail cannot be computed without executing playback makes the
-- whole record unavailable (never assumed zero), and the follower visibly
-- bypasses Space for the cycle with GATE INPUT UNAVAILABLE. Interlock, a
-- separate filter, is unaffected.
function test_space_gate_input_unavailable_bypasses_space_visibly()
  local cases = {
    -- A spread index outside the division table: playback cannot time it.
    function(leader)
      leader.chord_one_mask = 3
      set_stock(LEADER, "chord_strum", division_index(1 / 4))
      leader.trig_lock_params[2] = {id = "chord_spread", param_id = "space_slot_spread", off_value = 0, type = "stock"}
      params:add("space_slot_spread", {val = 0, default = 0})
      lock(leader, 1, 2, 99)
    end,
    -- A non-finite acceleration lock.
    function(leader)
      leader.chord_one_mask = 3
      set_stock(LEADER, "chord_strum", division_index(1 / 4))
      leader.trig_lock_params[2] = {id = "chord_acceleration", param_id = "space_slot_accel", off_value = 0,
        type = "stock"}
      params:add("space_slot_accel", {val = 0, default = 0})
      lock(leader, 1, 2, math.huge)
    end,
    -- A control whose value depends on live modulation (its getter is not
    -- norns core), which playback reads anew on every step.
    function(leader)
      leader.chord_one_mask = 3
      local id = "midi_device_params_channel_" .. LEADER .. "_" .. STOCK.chord_strum
      params:add(id, {val = 5, default = 0})
      rawset(params.params, id, {t = 3, raw = 0.1, controlspec = {map = function() return 5 end},
        get = function() return 5 end, map_value = function() return 5 end, default = 0})
    end
  }
  local modulated = "midi_device_params_channel_" .. LEADER .. "_" .. STOCK.chord_strum
  for index, prepare in ipairs(cases) do
    local song = setup({leader_lengths = {[1] = 3}, before_build = function(song)
      prepare(song.channels[LEADER])
      song.channels[OTHER].clock_mods = D1
      set_range(song.channels[OTHER], 1, 8)
      trigs(song.patterns[6], {2})
      song.channels[OTHER].selected_patterns = {[6] = true}
      song.channels[OTHER].musical_merge = foundation(6)
    end, follower_config = foundation(3, {space = {leader = LEADER, release = 0},
      interlock = {leader = OTHER, window = 0}})})
    local record = space_gate.snapshot(song.channels[LEADER], 1, 16)
    luaunit.assert_equals(record.status, space.GATE_INPUT_UNAVAILABLE, index)
    luaunit.assert_equals(record.step, 1, index)
    local result = build(song, FOLLOWER)
    luaunit.assert_equals(result.foundation.space.status, "GATE INPUT UNAVAILABLE", index)
    luaunit.assert_equals(result.foundation.space.blocked, {}, index)
    luaunit.assert_equals(reason_steps(result, "SPACE CH02"), {}, index)
    luaunit.assert_equals(result.foundation.interlock.status, "ok", index)
    luaunit.assert_equals(reason_steps(result, "INTERLOCK CH03"), {2}, index)
    local plain = without_filters(song)
    rawset(params.params, modulated, nil)
    local expected = {}
    for step = 1, 64 do expected[step] = plain.trig_values[step] end
    expected[2] = 0
    luaunit.assert_equals(result.trig_values, expected, index)
  end
end

-- ---------------------------------------------------------------------------
-- §6.1 gate intervals.

-- Length is the final post-mask working-pattern length; gates are half-open.
function test_space_gates_use_final_masked_lengths_and_half_open_ends()
  local song = setup({leader_lengths = {[1] = 3}})
  local result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.space.status, "ok")
  -- [0, 3/16): follower onsets 0, 1/16, 2/16; 3/16 is the excluded end.
  luaunit.assert_equals(blocked_steps(result), {1, 2, 3})
  luaunit.assert_equals(reason_steps(result, "SPACE CH02"), {1, 2, 3})
  luaunit.assert_equals(result.foundation.reasons[1], "SPACE CH02")
  luaunit.assert_equals(additions(result), {4, 5, 6, 7, 8})
  -- A step length mask on the leader replaces the value.
  song.channels[LEADER].step_length_masks[1] = 5
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {1, 2, 3, 4, 5})
  -- A channel length mask replaces every value.
  song.channels[LEADER].step_length_masks[1] = nil
  song.channels[LEADER].length_mask = 2
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {1, 2})
  -- Half-open at a finer follower grid: x2 onsets 5/32 inside, 6/32 the end.
  song = setup({leader_lengths = {[1] = 3}, follower_mod = X2})
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {1, 2, 3, 4, 5, 6})
end

-- The release margin extends every gate by release · d_f.
function test_space_release_margin_extends_by_follower_steps()
  local expected = {[0] = 6, [1] = 7, [2] = 8, [4] = 10}
  for release, last in pairs(expected) do
    local song = setup({leader_lengths = {[1] = 3}, follower_mod = X2, follower_last = 12, release = release})
    local steps = {}
    for step = 1, last do steps[#steps + 1] = step end
    luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), steps, "release " .. release)
  end
end

-- Zero or negative effective lengths contribute no gate; fractional lengths
-- are exact rationals (1/3 of a /1 step against x3 onsets 1/48 apart).
function test_space_zero_negative_and_fractional_lengths()
  local song = setup({leader_trigs = {1, 5}, leader_lengths = {[1] = 0, [5] = -2}})
  local result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.space.status, "ok")
  luaunit.assert_equals(blocked_steps(result), {})
  song = setup({leader_lengths = {[1] = 1 / 3}, follower_mod = X3})
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {1})
  song = setup({leader_lengths = {[1] = 0.5}, follower_mod = X2})
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {1})
end

-- Probability and mute never change the record: potentially skipped notes
-- keep their nominal occupancy.
function test_space_probability_and_mute_do_not_change_the_reservation()
  local song = setup({leader_lengths = {[1] = 3}})
  set_stock(LEADER, "trig_probability", 0)
  song.channels[LEADER].mute = true
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {1, 2, 3})
end

-- Strum tails extend the gate: sparse slots 1 and 3 forward at 1/4 end at
-- 3/4 + length 1 = 7/4 steps (x4 onsets: 7/64 is the excluded end); a
-- reverse root-only strum ends at 1 + 1; a muted root-only reverse strum
-- schedules nothing and has no gate.
function test_space_strum_tails_extend_the_gate()
  local song = setup({follower_mod = X4, follower_last = 12, before_build = function(song)
    song.channels[LEADER].chord_one_mask, song.channels[LEADER].chord_three_mask = 3, 5
    set_stock(LEADER, "chord_strum", division_index(1 / 4))
    set_stock(LEADER, "chord_strum_pattern", 1)
  end})
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {1, 2, 3, 4, 5, 6, 7})
  song.channels[LEADER].chord_one_mask, song.channels[LEADER].chord_three_mask = 0, 0
  set_stock(LEADER, "chord_strum_pattern", 2)
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {1, 2, 3, 4, 5, 6, 7, 8})
  set_stock(LEADER, "mute_root_note", 1)
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {})
end

-- The tail binds to what playback schedules: the chord voices' note-ons leave
-- at the descriptor delays (1/4 and 3/4 of a /1 step: 6 and 18 pulses).
function test_space_strum_tail_matches_the_scheduled_chord_voices()
  local song = setup({follower_config = false, before_build = function(song)
    song.channels[LEADER].chord_one_mask, song.channels[LEADER].chord_three_mask = 3, 5
    set_stock(LEADER, "chord_strum", division_index(1 / 4))
    set_stock(LEADER, "chord_strum_pattern", 1)
  end})
  local record = space_gate.snapshot(song.channels[LEADER], 1, 16)
  luaunit.assert_equals(record.tails[1], {3, 4})
  m_clock.init(); m_clock:start()
  pulses(24)
  stop_transport()
  local offsets = {}
  local onset
  for _, event in ipairs(midi_event_log) do
    if event.kind == "note_on" and event.c == LEADER then
      onset = onset or event.pulse
      offsets[#offsets + 1] = event.pulse - onset
    end
  end
  luaunit.assert_equals(offsets, {0, 6, 18})
  luaunit.assert_equals(offsets[#offsets] / 24, 3 / 4)
end

-- ---------------------------------------------------------------------------
-- §3 candidate pipeline with both leaders.

-- gap, then Interlock, then Space: every applicable reason in that order;
-- survivors are ranked with the existing FNV order, Amount counts survivors,
-- masks are applied last.
function test_space_combined_gap_interlock_and_space_reasons_with_partial_amount()
  local song, follower = setup({follower_anchors = {3}, leader_trigs = {1, 4},
    before_build = function(song)
      -- Interlock leader channel 2: Foundation anchors at 0 and 3/16.
      song.channels[LEADER].musical_merge = foundation(1)
      set_range(song.channels[LEADER], 1, 8)
      -- Space leader channel 3: a gate [3/16, 6/16).
      local other = song.channels[OTHER]
      other.clock_mods = D1
      set_range(other, 1, 16)
      trigs(song.patterns[6], {4})
      song.patterns[6].lengths[4] = 3
      other.selected_patterns = {[6] = true}
    end,
    follower_config = foundation(3, {gap = 1, amount = 50, seed = 99,
      interlock = {leader = LEADER, window = 0}, space = {leader = OTHER, release = 0}})})
  follower.step_trig_masks[5] = 1 -- a mask overrides a Space rejection
  local result = build(song, FOLLOWER)
  local plan = result.foundation
  luaunit.assert_equals(plan.interlock.status, "ok")
  luaunit.assert_equals(plan.space.status, "ok")
  luaunit.assert_equals(plan.reason_lists[1], {"INTERLOCK CH02"})
  luaunit.assert_equals(plan.reason_lists[2], {"gap"})
  luaunit.assert_equals(plan.reason_lists[4], {"gap", "INTERLOCK CH02", "SPACE CH03"})
  luaunit.assert_equals(plan.reasons[4], "gap")
  luaunit.assert_equals(plan.reason_lists[5], {"SPACE CH03"})
  luaunit.assert_equals(plan.reason_lists[6], {"SPACE CH03"})
  luaunit.assert_equals(plan.eligible_count, 2) -- 7, 8
  luaunit.assert_equals(plan.admitted_count, 1) -- round_half_up(50 · 2 / 100)
  local ranked = {}
  for _, step in ipairs({7, 8}) do
    ranked[#ranked + 1] = {step = step, rank = foundation_planner.fnv1a(table.concat(
      {1, 99, 1, FOLLOWER, "3,4|average|average|average", 0, step}, "|"))}
  end
  table.sort(ranked, function(a, b) if a.rank ~= b.rank then return a.rank < b.rank end return a.step < b.step end)
  luaunit.assert_equals(additions(result), {ranked[1].step})
  luaunit.assert_equals(plan.reason_lists[ranked[2].step], {"amount"})
  luaunit.assert_equals(result.trig_values[5], 1)
  luaunit.assert_equals(result.trig_values[6], 0)
end

-- Off stays exact: Foundation without a Space leader is the plan without the
-- filter.
function test_space_off_leaves_the_foundation_result_unchanged()
  local song = setup({follower_config = foundation(3)})
  local result = build(song, FOLLOWER)
  luaunit.assert_nil(result.foundation.space)
  luaunit.assert_nil(result.foundation.reason_lists)
end

-- ---------------------------------------------------------------------------
-- §1.4 support and budget.

-- L_max = max(2A − min(a, 1), M) over all 16 patterns' stored lengths and the
-- channel/step length masks, plus the default working length 1 and, with a
-- fractional stored length, the 1/2 the rounded average can add.
function test_space_length_bound_covers_every_length_path()
  local song = setup()
  local leader = song.channels[LEADER]
  luaunit.assert_equals(space_gate.length_bound(song, leader), {1, 1})
  song.patterns[9].lengths[40] = 10
  luaunit.assert_equals(space_gate.length_bound(song, leader), {19, 1})
  song.patterns[2].lengths[3] = 0
  luaunit.assert_equals(space_gate.length_bound(song, leader), {20, 1})
  leader.step_length_masks[7] = 25
  luaunit.assert_equals(space_gate.length_bound(song, leader), {25, 1})
  leader.length_mask = 30
  luaunit.assert_equals(space_gate.length_bound(song, leader), {30, 1})
  -- Every stored length below one step: the default working length 1 remains.
  song = setup()
  for number = 1, 16 do for step = 1, 64 do song.patterns[number].lengths[step] = 0.5 end end
  luaunit.assert_equals(space_gate.length_bound(song, song.channels[LEADER]), {1, 1})
  -- {1.4, 1.4} merges down to 1.4 − (round(1.4) − 1.4) = 1.8 and {1.5, 1} up
  -- to round(1.25) + 0.5 = 1.5; a stored 1.5 bounds every path by
  -- 2·1.5 − 1 + 1/2 = 5/2.
  song = setup()
  song.patterns[2].lengths[9] = 1.5
  luaunit.assert_equals(space_gate.length_bound(song, song.channels[LEADER]), {5, 2})
end

-- Every merge path of stored lengths stays within the bound: exhaustive over
-- stored sets of three values and every multiset of two or three operands
-- drawn from their effective lengths (a stored value, or a whole distance
-- >= 1 when a following trig clips a value above it). Without the 1/2, fractional values break it:
-- {1, 1.9, 1.9} rounds its average 1.6 up to 2 and merges up to 2.9 > 2·1.9 − 1.
function test_space_length_bound_holds_for_every_merge_mode_over_small_operand_sets()
  local values = {-1, 0, 0.25, 0.5, 1, 1.4, 1.5, 1.9, 2, 3, 7.5, 10}
  local average = fn.average_table_values
  local checked, needs_half = 0, 0
  for i = 1, #values do
    for j = i, #values do
      for k = j, #values do
        local stored = {values[i], values[j], values[k], 1}
        local largest, smallest = math.max(table.unpack(stored)), math.min(table.unpack(stored))
        local integral = true
        for _, value in ipairs(stored) do if value % 1 ~= 0 then integral = false end end
        local plan = math.max(2 * largest - math.min(smallest, 1), 1)
        local bound = plan + (integral and 0 or 0.5)
        local operands = {}
        for _, value in ipairs(stored) do
          operands[#operands + 1] = value
          for distance = 1, 3 do if value > distance then operands[#operands + 1] = distance end end
        end
        for x = 1, #operands do
          for y = x, #operands do
            for z = y, #operands + 1 do
              local chosen = {operands[x], operands[y], operands[z]}
              table.sort(chosen)
              local avg = average(chosen)
              for _, merged in ipairs({avg, avg + (chosen[#chosen] - chosen[1]),
                chosen[1] - (avg - chosen[1])}) do
                luaunit.assert_true(merged <= bound, table.concat(chosen, ",") .. " " .. merged .. " > " .. bound)
                if merged > plan then needs_half = needs_half + 1 end
                checked = checked + 1
              end
            end
          end
        end
      end
    end
  end
  luaunit.assert_true(checked > 10000)
  luaunit.assert_true(needs_half > 0)
end

-- A preceding-cycle up-merged gate longer than every stored length (the
-- {1, 10} case): operands 1 (clipped by the next trig) and 10 merge up to
-- round(5.5) + 9 = 15 steps (<= L_max = 2·10 − 1). Leader cycles are 16
-- steps; follower cycle 7 (onsets 28..31/16) lies at the end of leader cycle
-- 1, whose gate [16, 31) still covers 28, 29 and 30.
function test_space_up_merged_gate_longer_than_every_stored_length_is_carried_in()
  local song, follower, leader = setup({follower_last = 4, leader_trigs = {1, 2},
    leader_lengths = {[1] = 10}, leader_patterns = {[1] = true, [5] = true},
    before_build = function(song)
      trigs(song.patterns[5], {1})
      song.patterns[5].lengths[1] = 10
      song.channels[LEADER].trig_merge_mode = "all"
      song.channels[LEADER].length_merge_mode = "up"
    end})
  -- fn.average_table_values rounds the average half up: round(5.5) + 9 = 15.
  luaunit.assert_equals(leader.working_pattern.lengths[1], 15)
  luaunit.assert_equals(space_gate.length_bound(song, leader), {19, 1})
  m_clock.init(); m_clock:start()
  pulses(24 * 28 + 1)
  luaunit.assert_equals(merge_timeline.k(FOLLOWER), 7)
  local admission = follower.working_pattern.foundation.space
  luaunit.assert_equals(admission.status, "ok")
  luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 2, 3})
  stop_transport()
end

-- Origin clipping and carry-in: a leader gate [4i + 3, 4i + 6) of cycle −1
-- would cover follower onsets 0 and 1 of cycle 0, but there are no leader
-- cycles before the origin; follower cycle 1 receives the carried-in gate of
-- the preceding leader cycle.
function test_space_support_is_clipped_at_the_origin_and_carries_in()
  local song, follower = setup({leader_last = 4, leader_trigs = {4}, leader_lengths = {[4] = 3}})
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {4, 5, 6, 8})
  m_clock.init(); m_clock:start()
  pulses(24 * 8 + 1)
  luaunit.assert_equals(merge_timeline.k(FOLLOWER), 1)
  luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 2, 4, 5, 6, 8})
  stop_transport()
end

-- Budget: at most 64 leader cycles (checked before any plan) and 8 distinct
-- leader plans; PLAN LIMIT bypasses both filters for the follower's cycle and
-- is never evidence of silence. Follower /1.5 (3/32) against a one-step x2
-- leader (1/32): the last follower onset of 22 positions is 63/32, which is
-- exactly 64 leader cycles; 23 positions need 67.
function test_space_budget_edges_and_plan_limit_bypass_both_filters()
  local song = setup({follower_mod = D1_5, follower_last = 22, leader_mod = X2, leader_last = 1})
  local result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.space.status, "ok")
  luaunit.assert_equals(result.foundation.space.cycles, 64)
  luaunit.assert_equals(#blocked_steps(result), 22)
  local function with_interlock(song)
    local other = song.channels[OTHER]
    other.clock_mods = D1
    set_range(other, 1, 8)
    trigs(song.patterns[6], {2})
    other.selected_patterns = {[6] = true}
    other.musical_merge = foundation(6)
  end
  song = setup({follower_mod = D1_5, follower_last = 23, leader_mod = X2, leader_last = 1,
    before_build = with_interlock, follower_config = foundation(3, {space = {leader = LEADER, release = 0},
      interlock = {leader = OTHER, window = 1}})})
  result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.space.status, "PLAN LIMIT")
  luaunit.assert_equals(result.foundation.space.blocked, {})
  -- The Interlock admission alone is supported, but PLAN LIMIT bypasses both.
  luaunit.assert_equals(result.foundation.interlock.status, "PLAN LIMIT")
  luaunit.assert_equals(result.foundation.interlock.blocked, {})
  luaunit.assert_nil(result.foundation.reason_lists[2])
  luaunit.assert_equals(result.trig_values, without_filters(song).trig_values)
  -- More than 8 distinct leader plans: a per-phrase leader draws a new plan
  -- identity every cycle; fixed variation shares one.
  song = setup({follower_last = 16, leader_mod = X4, leader_last = 4,
    leader_config = foundation(1, {variation = "per_phrase"})})
  luaunit.assert_equals(build(song, FOLLOWER).foundation.space.status, "PLAN LIMIT")
  song = setup({follower_last = 16, leader_mod = X4, leader_last = 4, leader_config = foundation(1)})
  result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.space.status, "ok")
  luaunit.assert_equals(result.foundation.space.cycles, 16)
end

-- A plan length outside the proven L_max table bypasses with PLAN LIMIT
-- rather than publishing an underestimated support: a leader plan whose
-- length at a trig exceeds every stored-length path.
function test_space_length_outside_the_proven_bound_is_plan_limit()
  local song, follower = setup({leader_lengths = {[1] = 3}})
  local ctx = {song = song, channel = FOLLOWER, config = follower.musical_merge, first = 1, last = 8,
    leader_plan = function()
      local merged = build(song, LEADER)
      merged.lengths[1] = 100
      return merged
    end}
  local result = space.admission(ctx)
  luaunit.assert_equals(result.status, "PLAN LIMIT")
  luaunit.assert_equals(result.blocked, {})
  ctx.leader_plan = function() return build(song, LEADER) end
  ctx.plan_memo = nil
  luaunit.assert_equals(space.admission(ctx).status, "ok")
end

-- ---------------------------------------------------------------------------
-- Scheduler level: long gates and strum tails carried over several cycles with
-- changing phrases and configurations, order-, swing- and shuffle-independent.

local LEADER_TAIL = 1 / 4 -- chord slot 1 forward at 1/4

-- Supported results equal what the leader then plays: no admitted addition
-- starts inside a nominal reserved interval of a gate the leader played, and
-- every Space rejection has such an interval. Nominal pulses: /1 is 24, /1.5
-- is 36 per step.
local function assert_outside_leader_gates(log, release_pulses, leader_pulses, label)
  local gates = {}
  local last_leader = 0
  for _, onset in ipairs(log[LEADER]) do
    last_leader = onset.time
    if onset.trig == 1 and onset.length > 0 then
      gates[#gates + 1] = {onset.time, onset.time + (onset.length + LEADER_TAIL) * leader_pulses + release_pulses}
    end
  end
  local checked, rejected = 0, 0
  for _, onset in ipairs(log[FOLLOWER]) do
    if onset.time <= last_leader then
      local inside = false
      for _, gate in ipairs(gates) do
        if gate[1] <= onset.time and onset.time < gate[2] then inside = true; break end
      end
      local spaced = false
      for _, reason in ipairs(onset.reasons or {}) do if reason == "SPACE CH02" then spaced = true end end
      if onset.role == "addition" then luaunit.assert_false(inside, label .. " addition at " .. onset.time) end
      if spaced then rejected = rejected + 1; luaunit.assert_true(inside, label .. " rejection at " .. onset.time) end
      if inside and onset.role ~= "anchor" and onset.reasons ~= nil then
        luaunit.assert_true(spaced, label .. " candidate inside a gate at " .. onset.time)
      end
      checked = checked + 1
    end
  end
  luaunit.assert_true(checked > 20, label .. " checked " .. checked)
  luaunit.assert_true(rejected > 5, label .. " rejected " .. rejected)
end

function test_space_long_gates_and_tails_over_changing_phrases_are_order_swing_and_shuffle_independent()
  local runs = {}
  local variants = {
    {label = "leader first"}, {label = "follower first", reversed = true},
    {label = "swing", swing = 30}, {label = "reversed swing", reversed = true, swing = -25},
    {label = "shuffle", shuffle = true}, {label = "reversed shuffle", reversed = true, shuffle = true}
  }
  for _, variant in ipairs(variants) do
    local song = setup({follower_last = 7, follower_anchors = {3}, release = 1, leader_mod = D1_5, leader_last = 5,
      leader_trigs = {1, 4}, leader_lengths = {[1] = 4, [4] = 4}, leader_patterns = {[1] = true, [5] = true},
      leader_config = foundation(1, {cycles = 2, shape = "custom", percentages = {50, 100},
        variation = "per_phrase", amount = 60}),
      before_build = function(song)
        trigs(song.patterns[5], {2, 3, 5})
        for _, step in ipairs({2, 3, 5}) do song.patterns[5].lengths[step] = 2 end
        song.channels[LEADER].chord_one_mask = 3
        set_stock(LEADER, "chord_strum", division_index(1 / 4))
        set_stock(LEADER, "chord_strum_pattern", 1)
      end})
    variant.follower, variant.leader, variant.admission = FOLLOWER, LEADER, "space"
    variant.at_pulse = function(pulse)
      if pulse == 24 * 20 then
        -- A queued leader apply: a new anchor and seed (an epoch restart).
        local snapshot = transaction.snapshot(song)
        snapshot.channels[LEADER].musical_merge = foundation(5, {cycles = 2, shape = "custom",
          percentages = {50, 100}, variation = "per_phrase", seed = 11, amount = 60})
        luaunit.assert_true(transaction.apply(song, snapshot, true, "channel"))
      end
    end
    local log, cycles = harness.play(song, 24 * 60, variant)
    harness.assert_grid_and_midi_agree(log, variant.label)
    assert_outside_leader_gates(log, 24, 36, variant.label)
    local leader_lengths = {}
    for _, onset in ipairs(log[LEADER]) do if onset.trig == 1 then leader_lengths[onset.length] = true end end
    luaunit.assert_true(leader_lengths[4] and leader_lengths[2], variant.label)
    for k, cycle in pairs(cycles) do luaunit.assert_equals(cycle.status, "ok", variant.label .. " cycle " .. k) end
    runs[#runs + 1] = {label = variant.label, cycles = cycles}
  end
  for index = 2, #runs do
    luaunit.assert_equals(runs[index].cycles, runs[1].cycles, runs[index].label)
  end
end

-- §1.2.3 Space gates carried in across a pending global activation: from
-- queue time the follower bypasses both filters with RESYNC, and withdrawing
-- the queue returns it to the supported domain at its next rebuild.
function test_space_pending_global_activation_bypasses_and_withdrawal_recovers()
  local song, follower = setup({leader_lengths = {[1] = 12}, leader_last = 8, follower_last = 6,
    global_length = 16})
  m_clock.init(); m_clock:start(); pulses(24 * 9)
  luaunit.assert_equals(follower.working_pattern.foundation.space.status, "ok")
  -- Follower cycle 1 (6..11/16) receives the gate [8, 20) and the carried-in
  -- gate [0, 12) of the preceding leader cycle: 6..11 all covered.
  luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 2, 3, 4, 5, 6})
  local before = transaction.snapshot(song)
  local snapshot = transaction.snapshot(song)
  snapshot.channels[LEADER].musical_merge = foundation(1)
  luaunit.assert_true(transaction.apply(song, snapshot, true, "pattern"))
  luaunit.assert_equals(follower.working_pattern.foundation.space.status, "RESYNC")
  luaunit.assert_equals(follower.working_pattern.foundation.space.blocked, {})
  luaunit.assert_true(transaction.apply(song, before, true, "pattern"))
  luaunit.assert_equals(follower.working_pattern.foundation.space.status, "ok")
  luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 2, 3, 4, 5, 6})
  stop_transport()
end

-- §1.3 freshness: a leader length edit reaches the follower in the same
-- rebuild set, with the follower's lookahead invalidated.
function test_space_leader_length_edit_rebuilds_the_follower()
  local song, follower = setup({leader_lengths = {[1] = 2}})
  m_clock.init(); m_clock:start(); pulses(24 * 3)
  luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 2})
  local calls = {}
  local previous = m_clock.lookahead_scheduler
  m_clock.lookahead_scheduler = {invalidate = function(_, channel, step, slot)
    calls[#calls + 1] = {channel, step, slot}
  end}
  song.patterns[1].lengths[1] = 5
  pattern_module.update_source_working_patterns(song, 1)
  m_clock.lookahead_scheduler = previous
  local invalidated = false
  for _, call in ipairs(calls) do if call[1] == FOLLOWER and call[2] == nil then invalidated = true end end
  luaunit.assert_true(invalidated)
  luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 2, 3, 4, 5})
  stop_transport()
end

-- §1.3/§1.4 bounded synchronous work: leader plans are memoised within one
-- build, so Interlock and Space on the same leader share each plan; with two
-- different leaders each filter may build up to 8 (16 in all, the worst case
-- a follower's wrap rebuild performs).
function test_space_and_interlock_share_leader_plans_within_one_build()
  local function per_phrase_leader(song, number, pattern_number, mod, last)
    local channel = song.channels[number]
    channel.clock_mods = mod or X4
    set_range(channel, 1, last or 4)
    trigs(song.patterns[pattern_number], {1, 3})
    channel.selected_patterns = {[pattern_number] = true}
    channel.musical_merge = foundation(pattern_number, {variation = "per_phrase"})
  end
  -- Follower /1 1..7: Interlock (window 0) reaches 7/16, eight 1/16 leader
  -- cycles; Space reaches the last onset 6/16, seven of the same plans.
  local song = setup({follower_last = 7, before_build = function(song) per_phrase_leader(song, LEADER, 1) end,
    follower_config = foundation(3, {interlock = {leader = LEADER, window = 0}, space = {leader = LEADER, release = 0}})})
  local result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.interlock.status, "ok")
  luaunit.assert_equals(result.foundation.space.status, "ok")
  luaunit.assert_equals(result.foundation.interlock.cycles, 8)
  luaunit.assert_equals(result.foundation.space.cycles, 7)
  luaunit.assert_equals(result.foundation.leader_plan_builds, 8)
  -- Follower /1 1..8: Space on channel 2 needs eight 1/16 plans; Interlock
  -- on channel 3 (x8, nine steps: 9/128 per cycle) eight more up to 8/16.
  song = setup({before_build = function(song)
      per_phrase_leader(song, LEADER, 1)
      per_phrase_leader(song, OTHER, 6, {name = "x8", value = 8, type = "clock_multiplication"}, 9)
    end,
    follower_config = foundation(3, {interlock = {leader = OTHER, window = 0}, space = {leader = LEADER, release = 0}})})
  result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.interlock.status, "ok")
  luaunit.assert_equals(result.foundation.space.status, "ok")
  luaunit.assert_equals(result.foundation.interlock.cycles, 8)
  luaunit.assert_equals(result.foundation.space.cycles, 8)
  luaunit.assert_equals(result.foundation.leader_plan_builds, 16)
end
