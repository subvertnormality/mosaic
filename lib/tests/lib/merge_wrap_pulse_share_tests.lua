-- The wrap rebuilds of one lattice pulse share work (docs/musical-merge-
-- extensions-plan.md §1.3 performance): the Interlock admission of followers
-- with the same leader-side inputs, and the validation of source snapshots
-- they have in common. Sharing is scoped by the pulse token m_clock's wrap
-- branch passes down (a fresh table per Lattice:pulse_all). These tests play
-- representative wraps with every shortcut recomputed and compared
-- (pattern.wrap_share_check), compare the output with sharing off, and pin
-- that writes between pulses and an error inside a pulse never reach a later
-- pulse's shortcuts. They also guard the rule that Foundation plan
-- sub-tables are immutable once built (the wrap memo shares them).

local merge_state = include("mosaic/lib/musical_merge/state")
local merge_timeline = include("mosaic/lib/musical_merge/timeline")
local merge_config = include("mosaic/lib/musical_merge/config")
local transaction = include("mosaic/lib/optional_config_transaction")

local function workload()
  _MOSAIC_MERGE_WORKLOAD = nil
  return dofile("../../tests/behaviour/merge_device_workload.lua")
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

local function stats()
  local value = {}
  for key, count in pairs(pattern.wrap_memo_stats) do value[key] = count end
  return value
end

local function delta(before, after, key) return after[key] - before[key] end

local function note_log()
  local result = {}
  for index, event in ipairs(midi_event_log or {}) do
    result[index] = table.concat({event.kind, tostring(event.a), tostring(event.b), tostring(event.c), event.pulse}, ",")
  end
  return result
end

local function working_patterns(song)
  local result = {}
  for c = 1, 16 do result[c] = song.channels[c].working_pattern end
  return result
end

local function deep_equal(left, right)
  if type(left) ~= "table" or type(right) ~= "table" then
    return left == right and math.type(left) == math.type(right)
  end
  for key, value in pairs(left) do if not deep_equal(value, right[key]) then return false end end
  for key in pairs(right) do if left[key] == nil then return false end end
  return true
end

-- Plays `pulses` pulses of a configured project; `between(pulse, song)`
-- runs before each pulse (input-handler time, outside any pulse).
local function play(configure, pulses, between, options)
  options = options or {}
  local saved_share, saved_check = pattern.wrap_share, pattern.wrap_share_check
  pattern.wrap_share = options.share ~= false
  pattern.wrap_share_check = options.check == true
  midi_event_log = {}
  local song = dense_project()
  configure(song)
  local ok, err = pcall(function()
    m_clock:start()
    for pulse = 1, pulses do
      if between then between(pulse, song) end
      m_clock.get_clock_lattice():pulse()
    end
    stop_transport()
  end)
  pattern.wrap_share, pattern.wrap_share_check = saved_share, saved_check
  if not ok then error(err, 0) end
  return note_log(), working_patterns(song)
end

-- The leader's anchor toggled, as the Trigger editor tap does.
local function toggle_leader_anchor(W, song, step)
  local value = song.patterns[W.LEADER_PATTERN]
  value.trig_values[step] = value.trig_values[step] == 1 and 0 or 1
  pattern.update_source_working_patterns(song, W.LEADER_PATTERN)
end

-- Representative scenarios: the device workloads (every follower of one
-- leader wrapping on one pulse), with leader edits mid-cycle.
local SCENARIOS = {
  -- variant, pulses, edit pulses, shared admissions at least (14 per wrap
  -- of the 15 followers after the first)
  {"WORST", 24 * 64 * 3 + 12, {24 * 20 + 5, 24 * 84 + 5, 24 * 130 + 3}, 28},
  {"DENSE", 96 * 64 * 2 + 12, {96 * 16 + 7, 96 * 66 + 7}, 14},
  {"STEADY", 24 * 16 * 4 + 12, {24 * 20 + 5}, 0},
}

function test_merge_pulse_share_recomputes_equal_and_output_matches_sharing_off()
  local W = workload()
  for _, scenario in ipairs(SCENARIOS) do
    local variant, pulses, edits, minimum = scenario[1], scenario[2], scenario[3], scenario[4]
    local function configure() W.configure(variant, "enabled") end
    local function between(pulse, song)
      for _, at in ipairs(edits) do if pulse == at then toggle_leader_anchor(W, song, 1) end end
    end
    local before = stats()
    local shared_notes, shared_patterns = play(configure, pulses, between, {check = true})
    local after = stats()
    local unshared_notes, unshared_patterns = play(configure, pulses, between, {share = false})
    luaunit.assert_equals(shared_notes, unshared_notes, variant)
    if not deep_equal(shared_patterns, unshared_patterns) then
      local function diff(a, b, path)
        if type(a) ~= "table" or type(b) ~= "table" then
          if a ~= b or math.type(a) ~= math.type(b) then return path .. ": " .. tostring(a) .. " vs " .. tostring(b) end
          return nil
        end
        for k, v in pairs(a) do local d = diff(v, b[k], path .. "." .. tostring(k)); if d then return d end end
        for k in pairs(b) do if a[k] == nil then return path .. "." .. tostring(k) .. " missing" end end
      end
      luaunit.fail(variant .. " " .. tostring(diff(shared_patterns, unshared_patterns, "")))
    end
    luaunit.assert_true(#shared_notes > 0, variant)
    luaunit.assert_true(delta(before, after, "shared_admissions") >= minimum, variant)
    luaunit.assert_true(delta(before, after, "shared_validations") >= minimum, variant)
    luaunit.assert_equals(delta(before, after, "share_checks"),
      delta(before, after, "shared_admissions") + delta(before, after, "shared_validations"), variant)
  end
end

-- Mixed followers (different windows, anchors, sources, no leader), a queued
-- leader configuration (never shared) and in-place edits between pulses:
-- seeded, every shortcut recomputed and compared, output equal to sharing off.
function test_merge_pulse_share_random_followers_and_edits_match_sharing_off()
  local W = workload()
  local handlers = include("mosaic/lib/memory/event_handlers").new(program, fn)
  for seed = 1, 3 do
    local function configure(song)
      math.randomseed(seed)
      W.configure("WORST", "enabled")
      local snapshot = transaction.snapshot(song)
      for c = 2, 16 do
        local value = snapshot.channels[c].musical_merge
        local draw = math.random(6)
        if draw == 1 then value.interlock = {leader = nil, window = 0}
        elseif draw == 2 then value.interlock.window = math.random(1, 2)
        elseif draw == 3 then value.anchor = 8 end
      end
      assert(transaction.apply(song, snapshot, false, "channel"))
      for c = 2, 16 do
        if math.random(5) == 1 then song.channels[c].selected_patterns = {[8] = true, [7] = true, [3] = true} end
      end
      pattern.update_working_patterns(song)
    end
    local function between(pulse, song)
      if pulse % 97 ~= 0 then return end
      local draw = math.random(5)
      if draw == 1 then toggle_leader_anchor(W, song, 1)
      elseif draw == 2 then
        local value = song.patterns[8]
        local s = math.random(1, 64)
        value.trig_values[s] = value.trig_values[s] == 1 and 0 or 1   -- in place, no rebuild request
      elseif draw == 3 then
        local c = math.random(2, 16)
        local s = math.random(1, 64)
        handlers.note_mask.apply_event(song.channels[c], s, {step = s, trig = math.random(0, 1)}, "apply")
      elseif draw == 4 then
        local queued = merge_config.new()
        queued.mode, queued.anchor = "foundation", W.LEADER_PATTERN
        queued.amount = math.random(50, 100)
        merge_state.request(song, 1, queued, true)
      else
        song.patterns[7].velocity_values[1] = math.random(1, 127)
      end
    end
    local function run(options)
      math.randomseed(seed * 7919)
      return play(configure, 24 * 64 * 3 + 12, between, options)
    end
    local before = stats()
    local shared_notes, shared_patterns = run({check = true})
    local after = stats()
    local unshared_notes, unshared_patterns = run({share = false})
    luaunit.assert_equals(shared_notes, unshared_notes, "seed " .. seed)
    luaunit.assert_true(deep_equal(shared_patterns, unshared_patterns), "seed " .. seed)
    luaunit.assert_true(delta(before, after, "share_checks") > 0, "seed " .. seed)
  end
end

-- The pulse just before a follower wrap, on WORST.
local WRAP = 24 * 64

function test_merge_pulse_share_input_writes_between_pulses_are_seen_at_the_next_wrap()
  local W = workload()
  local song = dense_project()
  W.configure("WORST", "enabled")
  local lattice = m_clock.get_clock_lattice()
  local ok, err = pcall(function()
    m_clock:start()
    for _ = 1, WRAP * 2 do lattice:pulse() end
    -- Steady wrap: one pulse, 15 followers, sharing in use.
    local before = stats()
    for _ = 1, WRAP do lattice:pulse() end
    local after = stats()
    luaunit.assert_equals(delta(before, after, "shared_admissions"), 14)
    luaunit.assert_true(delta(before, after, "shared_validations") >= 14)
    -- Between pulses, as an input handler would: a source value the
    -- followers read, in place, without a rebuild request. Every follower
    -- must validate it again (legacy miss) at the next wrap.
    song.patterns[8].velocity_values[1] = 17
    before = stats()
    for _ = 1, WRAP do lattice:pulse() end
    after = stats()
    luaunit.assert_equals(delta(before, after, "legacy_misses") >= 15, true)
    for c = 2, 16 do luaunit.assert_equals(song.channels[c].working_pattern.velocity_values[1] ~= nil, true) end
    -- The leader's anchor written in place (no rebuild request): the next
    -- wrap's admission is recomputed under the new pulse and every follower
    -- sees no anchor (WORST's leader has one anchor, at step 1).
    song.patterns[W.LEADER_PATTERN].trig_values[1] = 0
    for _ = 1, WRAP do lattice:pulse() end
    for c = 2, 16 do
      luaunit.assert_equals(song.channels[c].working_pattern.foundation.interlock.anchors, 0, "ch" .. c)
    end
    -- A sweep between pulses (debounced update_working_patterns) builds
    -- without a pulse token: no sharing.
    before = stats()
    pattern.update_working_patterns(song)
    after = stats()
    luaunit.assert_equals({delta(before, after, "shared_admissions"), delta(before, after, "shared_validations")}, {0, 0})
    stop_transport()
  end)
  if not ok then pcall(stop_transport); error(err, 0) end
end

function test_merge_pulse_share_an_error_inside_a_pulse_does_not_leak_sharing()
  local W = workload()
  local song = dense_project()
  W.configure("WORST", "enabled")
  local lattice = m_clock.get_clock_lattice()
  local tokens, fail = {}, false
  local original = pattern.update_working_pattern
  pattern.update_working_pattern = function(c, song_pattern, at_wrap, pulse)
    if at_wrap then tokens[#tokens + 1] = pulse or false end
    original(c, song_pattern, at_wrap, pulse)
    if fail and c == 9 then error("injected failure inside a pulse") end
  end
  local ok, err = pcall(function()
    m_clock:start()
    for _ = 1, WRAP * 2 - 1 do lattice:pulse() end
    fail = true
    local count = #tokens
    local raised = not pcall(function() lattice:pulse() end)
    fail = false
    luaunit.assert_true(raised, "the wrap pulse raised")
    local failed_token = tokens[count + 1]
    luaunit.assert_true(type(failed_token) == "table")
    -- An at-wrap build outside any pulse (no token) shares nothing.
    local before = stats()
    pattern.update_working_pattern(2, song, true)
    local after = stats()
    luaunit.assert_equals({delta(before, after, "shared_admissions"), delta(before, after, "shared_validations")}, {0, 0})
    -- Later pulses run under fresh tokens: nothing of the failed pulse is reused.
    pattern.wrap_share_check = true
    local later = #tokens
    for _ = 1, WRAP do lattice:pulse() end
    pattern.wrap_share_check = false
    luaunit.assert_true(#tokens > later)
    for index = later + 1, #tokens do
      luaunit.assert_true(tokens[index] ~= failed_token and type(tokens[index]) == "table")
    end
    luaunit.assert_nil(lattice.pulse_token)
    stop_transport()
  end)
  pattern.update_working_pattern = original
  pattern.wrap_share_check = false
  if not ok then pcall(stop_transport); error(err, 0) end
end

-- Plan sub-tables are immutable after foundation.plan (the wrap memo shares
-- them between builds). Every plan built while `body` runs gets read-only
-- sub-tables that record any write; reads behave as before.
local function read_only(value, writes, path, cache)
  if type(value) ~= "table" then return value end
  if cache[value] then return cache[value] end
  local proxy = {}
  cache[value] = proxy
  setmetatable(proxy, {
    __index = function(_, key) return read_only(value[key], writes, path .. "." .. tostring(key), cache) end,
    __newindex = function(_, key) writes[#writes + 1] = path .. "." .. tostring(key) end,
    __len = function() return #value end,
    __pairs = function()
      return function(_, key)
        local next_key, item = next(value, key)
        return next_key, read_only(item, writes, path .. "." .. tostring(next_key), cache)
      end, proxy, nil
    end,
  })
  return proxy
end

local function with_read_only_plans(body)
  local builder = pattern.get_and_merge_patterns
  local foundation
  for index = 1, 300 do
    local name, value = debug.getupvalue(builder, index)
    if name == nil then break end
    if name == "foundation" then foundation = value; break end
  end
  assert(foundation, "pattern.lua's foundation module")
  local plan = foundation.plan
  local writes, cache = {}, setmetatable({}, {__mode = "k"})
  foundation.plan = function(args)
    local result = plan(args)
    for key, value in pairs(result) do
      if type(value) == "table" then result[key] = read_only(value, writes, key, cache) end
    end
    return result
  end
  local ok, err = pcall(body)
  foundation.plan = plan
  if not ok then error(err, 0) end
  return writes
end

function test_merge_plan_sub_tables_are_never_written_by_playback()
  local W = workload()
  local function configure() W.configure("WORST", "enabled") end
  local function between(pulse, song) if pulse == 24 * 20 + 5 then toggle_leader_anchor(W, song, 1) end end
  local plain = play(configure, 24 * 64 * 2 + 12, between)
  local guarded
  local writes = with_read_only_plans(function() guarded = play(configure, 24 * 64 * 2 + 12, between) end)
  luaunit.assert_equals(writes, {})
  luaunit.assert_equals(guarded, plain)
end

-- Structure markers (merge_structure.markers over the plan roles), kept
-- anchor pitch and the Harmony Pattern path of step.lua (plan roles read per
-- position), played through step.handle.
function test_merge_plan_sub_tables_are_never_written_by_structure_and_harmony_paths()
  local harmony_config = include("mosaic/lib/harmony/config")
  local harmony_inspection = include("mosaic/lib/harmony/inspection")
  local function run()
    local song = dense_project()
    for number, trigs in pairs({[1] = {1, 5, 9}, [2] = {3, 5, 7, 13}}) do
      local value = program.initialise_default_pattern()
      for _, position in ipairs(trigs) do value.trig_values[position] = 1; value.note_values[position] = position % 7 end
      song.patterns[number] = value
    end
    local group = harmony_config.four_part_smooth(1, {9, 10, 11, 12})
    group.enabled = true
    song.voicing = {schema_version = 1, groups = {[1] = group}}
    local channel = song.channels[1]
    channel.selected_patterns = {[1] = true, [2] = true}
    channel.end_trig = {16, 4}
    local merge = merge_config.new()
    merge.mode, merge.anchor, merge.keep_anchor_pitch = "foundation", 1, true
    merge.structure = {markers = "anchors", group_id = 1}
    channel.musical_merge = merge
    channel.voicing = harmony_config.new_channel("pattern")
    channel.voicing.roles.v1 = {min = 48, max = 59, centre = 53, preferred_leap = 127, strict_leap = false, enabled = true}
    pattern.update_working_pattern(1, song)
    midi_event_log = {}
    for _, position in ipairs({1, 3, 5, 7, 9, 13}) do step.handle(1, position) end
    local planned = {}
    for position = 1, 16 do
      local snapshot = harmony_inspection.snapshot(song, 1, position)
      planned[position] = snapshot and snapshot.planned and snapshot.planned.status or false
    end
    return {note_log(), planned, channel.working_pattern.foundation.markers}
  end
  local plain = run()
  local guarded
  local writes = with_read_only_plans(function() guarded = run() end)
  luaunit.assert_equals(writes, {})
  luaunit.assert_true(deep_equal(guarded[1], plain[1]))
  luaunit.assert_true(deep_equal(guarded[2], plain[2]))
  luaunit.assert_true(deep_equal(guarded[3], plain[3]))
  luaunit.assert_true(next(plain[3]) ~= nil, "markers present")
end

-- The Merge Shape Result and Reason screens (and merge_display) read every
-- plan field of every step.
function test_merge_plan_sub_tables_are_never_written_by_the_result_and_reason_screens()
  local feature_editor = include("mosaic/lib/pages/channel_edit_page/channel_feature_editor")
  local function fields_of(value)
    local result = {}
    for index, field in ipairs(value:get_fields()) do
      result[index] = field.label .. "=" .. tostring(feature_editor.field_value(field))
    end
    return result
  end
  local function open(value, label)
    for index, field in ipairs(value:get_fields()) do
      if field.label == label then value.selected = index; value:key(3); return end
    end
    error("missing " .. label)
  end
  local function step_field(value)
    for _, field in ipairs(value:get_fields()) do if field.label == "Step" then return field end end
  end
  local function run()
    program.init(); globals.reset(); params.reset(); m_clock.init(); merge_state.reset()
    program.set_selected_song_pattern(1)
    local song = program.get_song_pattern(1)
    for number, trigs in pairs({[1] = {1, 5, 9, 13}, [2] = {2, 3, 5, 6, 7, 11, 14}}) do
      for _, position in ipairs(trigs) do song.patterns[number].trig_values[position] = 1 end
    end
    local channel = song.channels[1]
    channel.selected_patterns = {[1] = true, [2] = true}
    song.channels[2].selected_patterns = {[1] = true}
    local config = merge_config.new()
    config.mode, config.anchor, config.gap, config.amount = "foundation", 1, 1, 50
    config.interlock = {leader = 2, window = 1}
    channel.musical_merge = config
    local leader = merge_config.new()
    leader.mode, leader.anchor = "foundation", 1
    song.channels[2].musical_merge = leader
    pattern.update_working_pattern(2, song)
    pattern.update_working_pattern(1, song)
    program.get().selected_channel = 1
    local value = feature_editor.new("merge")
    value:enter()
    open(value, "Result")
    local seen = {}
    for position = 1, 16 do
      step_field(value).set(position)
      seen[#seen + 1] = fields_of(value)
      open(value, "Reason")
      seen[#seen + 1] = fields_of(value)
      value:encoder_one()
      open(value, "Result")
    end
    return seen
  end
  local plain = run()
  local guarded
  local writes = with_read_only_plans(function() guarded = run() end)
  luaunit.assert_equals(writes, {})
  luaunit.assert_equals(guarded, plain)
end
