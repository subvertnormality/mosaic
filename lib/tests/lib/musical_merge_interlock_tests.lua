-- MM-09 Interlock (onset). Contract: docs/musical-merge-extensions-plan.md §1
-- (common time, counters, prediction, freshness, query support, budget) and
-- §3 (candidate pipeline). README "Merge Shape" still defers Interlock to the
-- MM-11 UI/docs card, so every assertion is a characterisation of that
-- approved plan, outside the current manual. "Explicit channel/step masks
-- still win" is README "Merge Shape" behaviour.

local merge_config = include("mosaic/lib/musical_merge/config")
local merge_state = include("mosaic/lib/musical_merge/state")
local merge_timeline = include("mosaic/lib/musical_merge/timeline")
local foundation_planner = include("mosaic/lib/musical_merge/foundation")
local transaction = include("mosaic/lib/optional_config_transaction")
local pattern_module = include("mosaic/lib/pattern")

local FOLLOWER, LEADER = 1, 2
local X2 = {name = "x2", value = 2, type = "clock_multiplication"}
local D1 = {name = "/1", value = 1, type = "clock_division"}
local D1_5 = {name = "/1.5", value = 1.5, type = "clock_division"}

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

-- Follower channel 1: anchor pattern 3, candidate pattern 4 (every step).
-- Leader channel 2: anchor pattern 1 (plus pattern 5 for a changed anchor).
local function setup(options)
  options = options or {}
  program.init(); globals.reset(); params.reset(); memory.init()
  merge_state.reset(); merge_timeline.stop()
  program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  song.global_pattern_length = options.global_length or 64
  for number = 1, 16 do program.get().devices[number].midi_channel = number end
  local follower, leader = song.channels[FOLLOWER], song.channels[LEADER]
  follower.clock_mods = options.follower_mod or X2
  leader.clock_mods = options.leader_mod or D1
  set_range(follower, 1, options.follower_last or 8)
  set_range(leader, 1, options.leader_last or 4)
  trigs(song.patterns[1], options.leader_anchors or {1, 3})
  trigs(song.patterns[5], options.leader_changed_anchors or {2})
  trigs(song.patterns[3], options.follower_anchors or {3})
  local all = {}
  for step = 1, 64 do all[#all + 1] = step end
  trigs(song.patterns[4], options.candidates or all)
  follower.selected_patterns = {[3] = true, [4] = true}
  leader.selected_patterns = {[1] = true, [5] = true}
  if options.leader_config ~= false then
    leader.musical_merge = options.leader_config or foundation(1)
  end
  if options.follower_config ~= false then
    follower.musical_merge = options.follower_config or
      foundation(3, {interlock = {leader = LEADER, window = options.window or 0}})
  end
  for number = 1, 16 do pattern_module.update_working_pattern(number, song) end
  return song, follower, leader
end

local function build(song, number)
  local channel = song.channels[number]
  return pattern_module.get_and_merge_patterns(number, channel.trig_merge_mode, channel.note_merge_mode,
    channel.velocity_merge_mode, channel.length_merge_mode, song)
end

local function reason_steps(result, reason)
  local steps = {}
  for step = 1, 64 do
    local list = result.foundation.reason_lists and result.foundation.reason_lists[step]
    for _, value in ipairs(list or {}) do if value == reason then steps[#steps + 1] = step end end
  end
  return steps
end

local function blocked_steps(result)
  local steps = {}
  for step in pairs(result.foundation.interlock.blocked) do steps[#steps + 1] = step end
  table.sort(steps)
  return steps
end

local function additions(result)
  local steps = {}
  for step = 1, 64 do if result.foundation.roles[step] == "addition" then steps[#steps + 1] = step end end
  return steps
end

local function without_interlock(song)
  local follower = song.channels[FOLLOWER]
  local saved = follower.musical_merge
  local plain = merge_config.canonicalize(saved)
  plain.interlock = {leader = nil, window = 0}
  follower.musical_merge = plain
  merge_state.reset()
  local result = build(song, FOLLOWER)
  follower.musical_merge = saved
  merge_state.reset()
  return result
end

local harness = include("mosaic/lib/tests/helpers/merge_playback_harness")
local pulses, stop_transport = harness.pulses, harness.stop_transport

-- §3 window 0: exactly coincident nominal onsets. Follower x2 (1/32), leader
-- /1 (1/16) anchors at steps 1 and 3 = 0 and 4/32: follower positions 1 and 5.
function test_interlock_window_zero_removes_only_coincident_candidates()
  local song = setup()
  local result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.interlock.status, "ok")
  luaunit.assert_equals(blocked_steps(result), {1, 5})
  luaunit.assert_equals(reason_steps(result, "INTERLOCK CH02"), {1, 5})
  luaunit.assert_equals(result.foundation.reasons[1], "INTERLOCK CH02")
  luaunit.assert_equals(result.trig_values[1], 0)
  luaunit.assert_equals(result.trig_values[5], 0)
  luaunit.assert_equals(result.foundation.roles[3], "anchor")
  luaunit.assert_equals(result.foundation.eligible_count, 5)
  luaunit.assert_equals(additions(result), {2, 4, 6, 7, 8})
end

-- §1.4 exact endpoints: |a − o| <= window·d_f is blocked, one follower step
-- further is not; the next leader cycle's anchor (8/32) reaches back into
-- the follower cycle's last position (7/32).
function test_interlock_window_endpoints_are_inclusive_and_carry_in_next_leader_cycle()
  local song = setup({window = 1})
  local result = build(song, FOLLOWER)
  luaunit.assert_equals(blocked_steps(result), {1, 2, 4, 5, 6, 8})
  luaunit.assert_nil(result.foundation.interlock.blocked[7])
end

-- Anchors of either channel are never changed; anchors are never filtered.
function test_interlock_never_filters_or_changes_anchors()
  local song = setup({follower_anchors = {1, 5}})
  local result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.roles[1], "anchor")
  luaunit.assert_equals(result.foundation.roles[5], "anchor")
  luaunit.assert_equals(result.trig_values[1], 1)
  luaunit.assert_equals(result.trig_values[5], 1)
  luaunit.assert_nil(result.foundation.reason_lists[1])
  local leader = build(song, LEADER)
  merge_state.reset()
  song.channels[FOLLOWER].musical_merge = nil
  luaunit.assert_equals(build(song, LEADER), leader)
end

-- §1.4 origin clipping: no leader cycle before 0. Leader /1 1..4 anchor at
-- step 4 (3/16); follower /1 1..8, window 1: an anchor at −1/16 would block
-- follower position 1 if the support were not clipped.
function test_interlock_support_is_clipped_at_the_origin()
  local song = setup({follower_mod = D1, leader_anchors = {4}, window = 1})
  local result = build(song, FOLLOWER)
  luaunit.assert_nil(result.foundation.interlock.blocked[1])
  luaunit.assert_equals(blocked_steps(result), {3, 4, 5, 7, 8})
end

-- Different clock modifiers and unequal ranges in exact common time:
-- follower /1.5 (3/32) 1..5, leader x2 (1/32) 1..3 anchors at step 2.
-- Leader anchors at 1/32 + 3i/32; follower onsets at 3n/32 never coincide.
-- With window 1 (3/32) every follower onset is within reach.
function test_interlock_unequal_modifiers_and_ranges_use_exact_nominal_time()
  local song = setup({follower_mod = D1_5, follower_last = 5, leader_mod = X2, leader_last = 3,
    leader_anchors = {2}})
  local result = build(song, FOLLOWER)
  luaunit.assert_equals(blocked_steps(result), {})
  song = setup({follower_mod = D1_5, follower_last = 5, leader_mod = X2, leader_last = 3,
    leader_anchors = {2}, window = 1})
  result = build(song, FOLLOWER)
  -- Blocked is evaluated for every playable position; the anchor (3) is
  -- never filtered.
  luaunit.assert_equals(blocked_steps(result), {1, 2, 3, 4, 5})
  luaunit.assert_equals(result.foundation.roles[3], "anchor")
  -- A leader anchor at step 1 coincides with every follower onset (3n/32).
  song = setup({follower_mod = D1_5, follower_last = 5, leader_mod = X2, leader_last = 3,
    leader_anchors = {1}})
  result = build(song, FOLLOWER)
  luaunit.assert_equals(blocked_steps(result), {1, 2, 3, 4, 5})
end

-- §1.1 modifier pairs with non-terminating decimals: x5.3 (5/424) against /1
-- and /1 against /5.3 (53/160), in exact integer arithmetic (no near-miss
-- is taken for a coincidence). Hand-computed over 33920 and 80 units.
function test_interlock_x5_3_and_div_5_3_pairs_are_exact()
  local x53 = {name = "x5.3", value = 5.3, type = "clock_multiplication"}
  local d53 = {name = "/5.3", value = 5.3, type = "clock_division"}
  -- Follower x5.3 onsets 400(n−1), leader /1 1..4 anchors at 8480i; window
  -- 400: |400(n−1) − 8480i| <= 400.
  local song = setup({follower_mod = x53, follower_last = 64, leader_mod = D1, leader_last = 4,
    leader_anchors = {1}, window = 1})
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {1, 2, 22, 23, 43, 44, 64})
  song = setup({follower_mod = x53, follower_last = 64, leader_mod = D1, leader_last = 4, leader_anchors = {1}})
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {1})
  -- Follower /1 onsets 5(n−1)/80, leader /5.3 1..2 anchors at 53i/80.
  song = setup({follower_mod = D1, follower_last = 64, leader_mod = d53, leader_last = 2, leader_anchors = {1}})
  luaunit.assert_equals(blocked_steps(build(song, FOLLOWER)), {1, 54})
end

-- §1.4 large ratios and the fallback: more than 64 leader cycles in the
-- support bypasses Interlock with PLAN LIMIT; the Foundation result is the
-- one without Interlock.
function test_interlock_large_ratio_falls_back_with_plan_limit()
  local song = setup({follower_mod = {name = "/128", value = 128, type = "clock_division"},
    follower_last = 64, leader_mod = {name = "x16", value = 16, type = "clock_multiplication"},
    leader_last = 64})
  local result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.interlock.status, "PLAN LIMIT")
  luaunit.assert_equals(result.foundation.interlock.blocked, {})
  -- Support [0, 63·8] against leader cycles of 1/4: 2017 cycles counted.
  luaunit.assert_equals(result.foundation.interlock.cycles, 2017)
  luaunit.assert_equals(result.foundation.interlock.anchors, 0)
  luaunit.assert_equals(result.foundation.interlock.plan_builds, 0)
  local plain = without_interlock(song)
  luaunit.assert_equals(result.trig_values, plain.trig_values)
  luaunit.assert_equals(result.foundation.eligible_count, plain.foundation.eligible_count)
end

-- §1.4 single budget: 64 leader cycles; there is no plan budget any more. A
-- per-phrase leader (a new phrase position every cycle) is supported exactly
-- like a fixed one: its anchors do not depend on the phrase (§1.2.3).
function test_interlock_per_phrase_leader_has_no_plan_budget()
  local x4 = {name = "x4", value = 4, type = "clock_multiplication"}
  for _, variation in ipairs({"per_phrase", "fixed"}) do
    local song = setup({follower_mod = D1, follower_last = 16, leader_mod = x4, leader_last = 4,
      leader_anchors = {1}, leader_config = foundation(1, {variation = variation, cycles = 8, shape = "build",
        percentages = {13, 25, 38, 50, 63, 75, 88, 100}})})
    local admission = build(song, FOLLOWER).foundation.interlock
    luaunit.assert_equals(admission.status, "ok", variation)
    -- Leader cycle length 4/64 = 1/16: an anchor at every follower onset;
    -- support [0, 15/16] meets leader cycles 0..15.
    luaunit.assert_equals(#blocked_steps(build(song, FOLLOWER)), 16, variation)
    luaunit.assert_equals(admission.cycles, 16, variation)
    luaunit.assert_equals(admission.anchors, 16, variation)
    luaunit.assert_equals(admission.plan_builds, 0, variation)
  end
end

-- §1.5: a leader cycle whose configuration is Off, or Foundation with a
-- missing anchor, contributes no anchors, with LEADER OFF / LEADER MISSING.
function test_interlock_leader_off_and_missing_contribute_no_anchors()
  local song = setup({leader_config = false})
  local result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.interlock.status, "LEADER OFF")
  luaunit.assert_equals(result.foundation.interlock.blocked, {})
  luaunit.assert_equals(result.trig_values, without_interlock(song).trig_values)
  song = setup({leader_config = foundation(7)})
  result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.interlock.status, "LEADER MISSING")
  luaunit.assert_equals(result.trig_values, without_interlock(song).trig_values)
  local fragments = merge_config.new(); fragments.mode = "fragments"
  song = setup({leader_config = fragments})
  luaunit.assert_equals(build(song, FOLLOWER).foundation.interlock.status, "LEADER OFF")
end

-- §1.2.3 Leader anchors for cycle i: read directly from the currently stored
-- anchor pattern under the governing configuration, equal to the positions
-- foundation.plan marks `anchor` for the same configuration and stored data,
-- for every configuration shape the Interlock suite uses (and a few more):
-- offset and one-step ranges, phrase shapes, per-phrase variation, gap,
-- partial Amount, Accent zero, masks, missing/unassigned anchor, Off,
-- Fragments and a v1 Foundation configuration.
function test_interlock_direct_leader_anchors_equal_foundation_plan_anchors()
  local v1 = {schema_version = 1, mode = "foundation", anchor = 1, amount = 30, accent = 55, gap = 1, seed = 5,
    ranking_version = 1, cycles = 2, shape = "custom", percentages = {20, 90}, variation = "per_phrase",
    keep_anchor_pitch = false, target = {kind = "legacy"}}
  local fragments = merge_config.new(); fragments.mode = "fragments"
  local shapes = {
    {label = "default", config = foundation(1)},
    {label = "changed anchor", config = foundation(5)},
    {label = "phrase", config = foundation(1, {cycles = 2, shape = "custom", percentages = {40, 100},
      variation = "per_phrase", amount = 60})},
    {label = "gap amount accent", config = foundation(1, {gap = 3, amount = 17, accent = 0, seed = 77})},
    {label = "offset range", config = foundation(1), first = 5, last = 20},
    {label = "one step", config = foundation(1), first = 1, last = 1},
    {label = "masks", config = foundation(1), masks = true},
    {label = "unassigned anchor", config = foundation(7)},
    {label = "off", config = merge_config.new()},
    {label = "fragments", config = fragments},
    {label = "v1", config = v1}
  }
  local query = include("mosaic/lib/musical_merge/leader_query")
  for _, shape in ipairs(shapes) do
    local song, follower, leader = setup({leader_config = shape.config, leader_anchors = {1, 3, 6, 9, 17, 20}})
    set_range(leader, shape.first or 1, shape.last or 4)
    if shape.masks then
      leader.step_trig_masks[1] = 0; leader.step_trig_masks[2] = 1; leader.trig_mask = 1
    end
    merge_state.reset()
    local plan = build(song, LEADER).foundation
    local frame = query.frame({song = song, channel = FOLLOWER, first = 1, last = 8}, LEADER)
    local direct = query.anchors(frame, shape.config)
    if plan == nil then
      luaunit.assert_false(direct, shape.label)
    elseif plan.status ~= "ok" then
      luaunit.assert_nil(direct, shape.label)
    else
      local expected = {}
      for index = 1, frame.l_count do
        if plan.roles[frame.l_first + index - 1] == "anchor" then expected[#expected + 1] = index end
      end
      luaunit.assert_equals(direct, expected, shape.label)
    end
    -- The admission reads the same set and builds nothing.
    local admission = build(song, FOLLOWER).foundation.interlock
    luaunit.assert_equals(admission.plan_builds, 0, shape.label)
  end
end

-- §1.2.3 acceptance: an admission performs zero leader-plan builds. The
-- follower build is the only get_and_merge_patterns call, over a support of
-- many leader cycles with per-phrase variation and a predicted queued change.
function test_interlock_admission_performs_zero_leader_plan_builds()
  local x4 = {name = "x4", value = 4, type = "clock_multiplication"}
  local song = setup({follower_mod = D1, follower_last = 64, leader_mod = x4, leader_last = 4, leader_anchors = {1},
    window = 0, leader_config = foundation(1, {cycles = 4, shape = "build", percentages = {25, 50, 75, 100},
      variation = "per_phrase"})})
  merge_state.request(song, LEADER, foundation(5, {variation = "per_phrase"}), false)
  local original = pattern_module.get_and_merge_patterns
  local calls = {}
  pattern_module.get_and_merge_patterns = function(channel, ...)
    calls[#calls + 1] = channel
    return original(channel, ...)
  end
  local ok, result = pcall(build, song, FOLLOWER)
  pattern_module.get_and_merge_patterns = original
  if not ok then error(result, 0) end
  luaunit.assert_equals(calls, {FOLLOWER})
  local admission = result.foundation.interlock
  luaunit.assert_equals(admission.status, "ok")
  luaunit.assert_equals(admission.plan_builds, 0)
  luaunit.assert_equals(admission.cycles, 64)
end

-- §3 candidate pipeline: gap, then Interlock, every applicable reason kept
-- in order; the survivors are ranked with the existing FNV order, Amount
-- counts survivors, masks are applied last.
function test_interlock_combined_gap_and_interlock_reasons_with_partial_amount_and_masks()
  local song, follower = setup({window = 0, follower_config =
    foundation(3, {gap = 1, amount = 50, seed = 99, interlock = {leader = LEADER, window = 0}})})
  follower.step_trig_masks[5] = 1 -- a mask overrides an Interlock rejection
  local result = build(song, FOLLOWER)
  local plan = result.foundation
  -- Anchor 3; gap 1 blocks 2 and 4; Interlock blocks 1 and 5.
  luaunit.assert_equals(plan.reason_lists[2], {"gap"})
  luaunit.assert_equals(plan.reason_lists[4], {"gap"})
  luaunit.assert_equals(plan.reason_lists[1], {"INTERLOCK CH02"})
  luaunit.assert_equals(plan.reason_lists[5], {"INTERLOCK CH02"})
  luaunit.assert_equals(plan.eligible_count, 3) -- 6, 7, 8
  luaunit.assert_equals(plan.admitted_count, 2) -- round_half_up(50 · 3 / 100)
  -- Independent ranking of the survivors (FNV-1a of the v1 rank identity).
  local ranked = {}
  for _, step in ipairs({6, 7, 8}) do
    ranked[#ranked + 1] = {step = step, rank = foundation_planner.fnv1a(table.concat(
      {1, 99, 1, FOLLOWER, "3,4|average|average|average", 0, step}, "|"))}
  end
  table.sort(ranked, function(a, b) if a.rank ~= b.rank then return a.rank < b.rank end return a.step < b.step end)
  local expected = {ranked[1].step, ranked[2].step}
  table.sort(expected)
  luaunit.assert_equals(additions(result), expected)
  luaunit.assert_equals(plan.reason_lists[ranked[3].step], {"amount"})
  luaunit.assert_equals(result.trig_values[5], 1)
  luaunit.assert_equals(result.trig_values[1], 0)
  -- Overlapping reasons: gap and Interlock on the same candidate.
  song, follower = setup({window = 1, follower_config =
    foundation(3, {gap = 1, accent = 0, interlock = {leader = LEADER, window = 1}})})
  result = build(song, FOLLOWER)
  plan = result.foundation
  luaunit.assert_equals(plan.reason_lists[2], {"gap", "INTERLOCK CH02"})
  luaunit.assert_equals(plan.reason_lists[4], {"gap", "INTERLOCK CH02"})
  luaunit.assert_equals(plan.reasons[4], "gap")
  luaunit.assert_equals(plan.reason_lists[1], {"INTERLOCK CH02"})
  -- Accent zero keeps its zero-admission behaviour on the survivor (7).
  luaunit.assert_equals(plan.eligible_count, 1)
  luaunit.assert_equals(plan.admitted_count, 0)
  luaunit.assert_equals(plan.reason_lists[7], {"accent"})
  luaunit.assert_equals(additions(result), {})
end

-- §3 nested sets: with immutable inputs and nonzero Accent, increasing Amount
-- never removes an admitted addition.
function test_interlock_admitted_additions_are_nested_in_amount()
  local previous
  for amount = 0, 100, 5 do
    local song = setup({window = 0, follower_last = 16, follower_config =
      foundation(3, {amount = amount, seed = 4321, interlock = {leader = LEADER, window = 0}})})
    local current = {}
    for _, step in ipairs(additions(build(song, FOLLOWER))) do current[step] = true end
    if previous then
      for step in pairs(previous) do luaunit.assert_true(current[step], "amount " .. amount .. " step " .. step) end
    end
    previous = current
  end
end

-- §1.3 while stopped j = 0 and k_l = 0: the stopped preview equals what the
-- first cycle after Start plays (first cycle filtered, no waiting cycle).
function test_interlock_first_cycle_after_start_is_filtered_like_the_stopped_preview()
  local song, follower = setup()
  local preview = follower.working_pattern
  luaunit.assert_equals(blocked_steps(preview), {1, 5})
  m_clock.init(); m_clock:start()
  pulses(1)
  luaunit.assert_equals(merge_timeline.k(FOLLOWER), 0)
  luaunit.assert_equals(build(song, FOLLOWER).trig_values, preview.trig_values)
  stop_transport()
end

-- Off stays exact: Foundation without a leader is the plan without filters.
function test_interlock_off_leaves_the_foundation_result_unchanged()
  local song = setup({follower_config = foundation(3)})
  local result = build(song, FOLLOWER)
  luaunit.assert_nil(result.foundation.interlock)
  luaunit.assert_nil(result.foundation.reason_lists)
end

-- ---------------------------------------------------------------------------
-- Scheduler level. Nominal onset times are counted in lattice pulses per step
-- (d · 384), exact for the clock mods used here.

local function play(song, total, options)
  options = options or {}
  options.follower, options.leader = FOLLOWER, LEADER
  return harness.play(song, total, options)
end

local assert_grid_and_midi_agree = harness.assert_grid_and_midi_agree

-- Supported results equal what the leader then plays: no admitted addition is
-- within the window of an anchor the leader played, and every Interlock
-- rejection has such an anchor (within the played span).
local function assert_matches_leader_playback(log, window_pulses, label)
  local anchors = {}
  local last_leader = 0
  for _, onset in ipairs(log[LEADER]) do
    last_leader = onset.time
    if onset.role == "anchor" then anchors[#anchors + 1] = onset.time end
  end
  local checked = 0
  for _, onset in ipairs(log[FOLLOWER]) do
    if onset.time + window_pulses <= last_leader then
      local near = false
      for _, anchor in ipairs(anchors) do
        if math.abs(anchor - onset.time) <= window_pulses then near = true; break end
      end
      local interlocked = false
      for _, reason in ipairs(onset.reasons or {}) do if reason == "INTERLOCK CH02" then interlocked = true end end
      if onset.role == "addition" then luaunit.assert_false(near, label .. " addition at " .. onset.time) end
      if interlocked then luaunit.assert_true(near, label .. " rejection at " .. onset.time) end
      if near and onset.role ~= "anchor" and (onset.reasons ~= nil) then
        luaunit.assert_true(interlocked, label .. " candidate near an anchor at " .. onset.time)
      end
      checked = checked + 1
    end
  end
  luaunit.assert_true(checked > 20, label .. " checked " .. checked)
end

-- §1.2 supported domain: order-, swing- and shuffle-independent, equal to the
-- leader's playback, across a predicted queued leader activation (a new anchor
-- and seed: an epoch restart) and changing phrases.
function test_interlock_schedule_is_independent_of_callback_order_swing_and_shuffle()
  local runs = {}
  local variants = {
    {label = "leader first"}, {label = "follower first", reversed = true},
    {label = "swing", swing = 30}, {label = "reversed swing", reversed = true, swing = -25},
    {label = "shuffle", shuffle = true}, {label = "reversed shuffle", reversed = true, shuffle = true}
  }
  for _, variant in ipairs(variants) do
    local song = setup({follower_mod = D1, follower_last = 7, leader_mod = D1_5, leader_last = 5,
      leader_anchors = {1, 4}, leader_changed_anchors = {2, 5}, window = 1,
      leader_config = foundation(1, {cycles = 2, shape = "custom", percentages = {50, 100}, variation = "per_phrase"})})
    variant.at_pulse = function(pulse)
      if pulse == 24 * 20 then
        -- A queued leader apply: rebuilds its followers so their predictions
        -- follow the new queue.
        local snapshot = transaction.snapshot(song)
        snapshot.channels[LEADER].musical_merge = foundation(5, {cycles = 2, shape = "custom",
          percentages = {50, 100}, variation = "per_phrase", seed = 11})
        luaunit.assert_true(transaction.apply(song, snapshot, true, "channel"))
      end
    end
    local log, cycles = play(song, 24 * 60, variant)
    assert_grid_and_midi_agree(log, variant.label)
    assert_matches_leader_playback(log, 24, variant.label)
    for k, cycle in pairs(cycles) do luaunit.assert_equals(cycle.status, "ok", variant.label .. " cycle " .. k) end
    runs[#runs + 1] = {label = variant.label, cycles = cycles}
  end
  for index = 2, #runs do
    luaunit.assert_equals(runs[index].cycles, runs[1].cycles, runs[index].label)
  end
end

-- §1.2.3 a leader with no saved configuration never advances a phrase; a
-- first enable mid-play (leader, then follower) starts exactly where the code
-- would, and the follower's first filtered cycle equals the leader's playback.
function test_interlock_first_enable_mid_play_matches_leader_playback()
  for _, reversed in ipairs({false, true}) do
    local song = setup({follower_mod = D1, follower_last = 6, leader_mod = X2, leader_last = 5,
      leader_anchors = {2, 5}, leader_config = false, follower_config = false})
    local label = reversed and "reversed" or "ordered"
    local log, cycles = play(song, 24 * 50, {reversed = reversed, at_pulse = function(pulse)
      if pulse == 24 * 5 + 7 then
        local snapshot = transaction.snapshot(song)
        snapshot.channels[LEADER].musical_merge = foundation(1)
        luaunit.assert_true(transaction.apply(song, snapshot, true, "channel"))
      elseif pulse == 24 * 11 + 3 then
        local snapshot = transaction.snapshot(song)
        snapshot.channels[FOLLOWER].musical_merge = foundation(3, {interlock = {leader = LEADER, window = 0}})
        luaunit.assert_true(transaction.apply(song, snapshot, true, "channel"))
      end
    end})
    assert_grid_and_midi_agree(log, label)
    local filtered = 0
    for _, cycle in pairs(cycles) do if cycle.status == "ok" then filtered = filtered + 1 end end
    luaunit.assert_true(filtered >= 5, label)
    -- Only the part after both enables is compared.
    local trimmed = {[LEADER] = log[LEADER], [FOLLOWER] = {}}
    for _, onset in ipairs(log[FOLLOWER]) do if onset.role then trimmed[FOLLOWER][#trimmed[FOLLOWER] + 1] = onset end end
    assert_matches_leader_playback(trimmed, 0, label)
  end
end

local function apply_timing(options)
  if options.reversed then
    local order = m_clock.get_clock_lattice().sprocket_pulse_order[2]
    local reversed = {}
    for index = #order, 1, -1 do reversed[#reversed + 1] = order[index] end
    m_clock.get_clock_lattice().sprocket_pulse_order[2] = reversed
  end
  for _, number in ipairs({FOLLOWER, LEADER}) do
    if options.swing then m_clock.set_channel_swing(number, options.swing) end
    if options.shuffle then
      m_clock.set_swing_shuffle_type(number, 2); m_clock.set_channel_shuffle_feel(number, 2)
      m_clock.set_channel_shuffle_basis(number, 1); m_clock.set_channel_shuffle_amount(number, 80)
    end
  end
end

-- §1.2.3 pending global activations exclude the pair from queue time; the
-- sticky resync continues the bypass until the next origin; withdrawal before
-- activation returns to the supported domain at the follower's next rebuild.
-- Swing and shuffle in both directions and reversed callback order move
-- leader onsets to either side of the activation; the bypass holds anyway.
function test_interlock_pending_global_activation_bypasses_until_next_origin()
  local variants = {{}, {swing = 40}, {swing = -40, reversed = true}, {shuffle = true},
    {shuffle = true, reversed = true}}
  for index, variant in ipairs(variants) do
    local label = "variant " .. index
    local song, follower = setup({follower_mod = D1, follower_last = 6, leader_mod = D1_5, leader_last = 5,
      global_length = 16})
    m_clock.init(); m_clock:start(); apply_timing(variant)
    pulses(24 * 3)
    luaunit.assert_equals(follower.working_pattern.foundation.interlock.status, "ok", label)
    local snapshot = transaction.snapshot(song)
    snapshot.channels[LEADER].musical_merge = foundation(5)
    luaunit.assert_true(transaction.apply(song, snapshot, true, "pattern"))
    -- Queue time: the follower is rebuilt with the bypass immediately.
    luaunit.assert_equals(follower.working_pattern.foundation.interlock.status, "RESYNC", label)
    luaunit.assert_equals(follower.working_pattern.foundation.interlock.blocked, {}, label)
    local landed = false
    for _ = 1, 24 * 30 do
      pulses(1)
      luaunit.assert_equals(follower.working_pattern.foundation.interlock.status, "RESYNC", label)
      if not merge_state.peek(song, LEADER).global_queued then landed = true end
    end
    luaunit.assert_true(landed, label)
    luaunit.assert_true(merge_timeline.resync(LEADER), label)
    stop_transport()
    -- The next origin (Start) returns to the supported domain.
    m_clock.init(); m_clock:start(); apply_timing(variant); pulses(24 * 7)
    luaunit.assert_false(merge_timeline.resync(LEADER), label)
    luaunit.assert_equals(follower.working_pattern.foundation.interlock.status, "ok", label)
    stop_transport()

    -- Withdrawal (undo before the boundary).
    song, follower = setup({follower_mod = D1, follower_last = 6, leader_mod = D1_5, leader_last = 5,
      global_length = 16})
    m_clock.init(); m_clock:start(); apply_timing(variant); pulses(24 * 2)
    local before = transaction.snapshot(song)
    snapshot = transaction.snapshot(song)
    snapshot.channels[LEADER].musical_merge = foundation(5)
    luaunit.assert_true(transaction.apply(song, snapshot, true, "pattern"))
    luaunit.assert_equals(follower.working_pattern.foundation.interlock.status, "RESYNC", label)
    luaunit.assert_true(transaction.apply(song, before, true, "pattern"))
    luaunit.assert_nil(merge_state.peek(song, LEADER).global_queued, label)
    luaunit.assert_equals(follower.working_pattern.foundation.interlock.status, "ok", label)
    for _ = 1, 24 * 20 do
      pulses(1)
      luaunit.assert_equals(follower.working_pattern.foundation.interlock.status, "ok", label)
    end
    luaunit.assert_false(merge_timeline.resync(LEADER), label)
    stop_transport()
  end
end

-- §1.2.3 a follower's own pending global activation also excludes it.
function test_interlock_follower_global_queue_bypasses_from_queue_time()
  local song, follower = setup({follower_mod = D1, leader_mod = D1, global_length = 16})
  m_clock.init(); m_clock:start(); pulses(24)
  local snapshot = transaction.snapshot(song)
  snapshot.channels[FOLLOWER].musical_merge = foundation(3, {amount = 40, interlock = {leader = LEADER, window = 0}})
  luaunit.assert_true(transaction.apply(song, snapshot, true, "pattern"))
  luaunit.assert_equals(follower.working_pattern.foundation.interlock.status, "RESYNC")
  stop_transport()
end

-- §1.2.1 resync bypass after a division change, a range change and a
-- non-realigning slot change, visible as RESYNC, never filtering.
function test_interlock_resync_after_division_range_and_slot_changes()
  local song, follower = setup({follower_mod = D1, leader_mod = D1, global_length = 16})
  m_clock.init(); m_clock:start(); pulses(24 * 2)
  luaunit.assert_equals(follower.working_pattern.foundation.interlock.status, "ok")
  m_clock.set_channel_division(LEADER, m_clock.calculate_divisor({value = 2, type = "clock_division"}))
  luaunit.assert_equals(follower.working_pattern.foundation.interlock.status, "RESYNC")
  luaunit.assert_equals(follower.working_pattern.trig_values, without_interlock(song).trig_values)
  stop_transport()

  song, follower = setup({follower_mod = D1, leader_mod = D1, global_length = 16})
  m_clock.init(); m_clock:start(); pulses(24 * 2)
  set_range(song.channels[LEADER], 1, 3)
  pattern_module.update_working_pattern(LEADER, song)
  luaunit.assert_equals(follower.working_pattern.foundation.interlock.status, "RESYNC")
  luaunit.assert_true(merge_timeline.resync(LEADER))
  stop_transport()

  song, follower = setup({follower_mod = D1, leader_mod = D1, global_length = 8})
  params:set("song_mode", 2); params:set("reset_on_song_pattern_transition", 1)
  params:set("reset_on_end_of_pattern_repeat", 1)
  song.active = true
  program.set_song_pattern(1, 2)
  local second = program.get_song_pattern(2); second.active = true
  m_clock.init(); m_clock:start()
  pulses(24 * 8 + 1)
  luaunit.assert_equals(program.get().selected_song_pattern, 2)
  for number = 1, 16 do luaunit.assert_true(merge_timeline.resync(number), number) end
  pulses(24 * 8)
  luaunit.assert_equals(second.channels[FOLLOWER].working_pattern.foundation.interlock.status, "RESYNC")
  stop_transport()
end

-- §1.4 an Interlock-only anchor in the preceding leader cycle within the
-- window is found (follower cycle 1 starts at 8/16; the leader's cycle-1
-- anchor at 7/16 is within one follower step).
function test_interlock_preceding_cycle_anchor_within_window_is_found()
  local song, follower = setup({follower_mod = D1, follower_last = 8, leader_mod = D1, leader_last = 4,
    leader_anchors = {4}, window = 1, follower_anchors = {3}})
  m_clock.init(); m_clock:start()
  pulses(24 * 8 + 1)
  luaunit.assert_equals(merge_timeline.k(FOLLOWER), 1)
  local admission = follower.working_pattern.foundation.interlock
  luaunit.assert_equals(admission.status, "ok")
  -- Follower cycle 1 onsets 8..15/16; leader anchors at 7, 11, 15 (and 19).
  luaunit.assert_true(admission.blocked[1])
  luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 3, 4, 5, 7, 8})
  stop_transport()
end

-- §1.2.3 a pattern boundary that realigns ends the origin: leader onsets at
-- or after it are excluded from the query.
function test_interlock_realigning_boundary_ends_the_query_origin()
  local song = setup({follower_mod = D1, follower_last = 6, leader_mod = D1, leader_last = 4,
    leader_anchors = {1}, window = 0, global_length = 8})
  params:set("song_mode", 2); params:set("reset_on_end_of_pattern_repeat", 2)
  song.active = true
  m_clock.init(); m_clock:start()
  pulses(24 * 6 + 1)
  -- Follower cycle 1 covers 6..11/16; the realign at 8/16 excludes the
  -- leader's anchor at 8/16 (step 3 of the follower's cycle).
  luaunit.assert_equals(merge_timeline.k(FOLLOWER), 1)
  local admission = song.channels[FOLLOWER].working_pattern.foundation.interlock
  luaunit.assert_nil(admission.blocked[3])
  params:set("song_mode", 1)
  pattern_module.update_working_pattern(FOLLOWER, song)
  luaunit.assert_true(song.channels[FOLLOWER].working_pattern.foundation.interlock.blocked[3])
  stop_transport()
end

-- ---------------------------------------------------------------------------
-- §1.3 freshness.

local function recording_lookahead()
  local calls = {}
  local previous = m_clock.lookahead_scheduler
  m_clock.lookahead_scheduler = {invalidate = function(_, channel, step, slot)
    calls[#calls + 1] = {channel, step, slot}
  end}
  return calls, function() m_clock.lookahead_scheduler = previous end
end

local function invalidated(calls, channel)
  for _, call in ipairs(calls) do if call[1] == channel and call[2] == nil then return true end end
  return false
end

-- A follower edit mid-cycle recomputes the admission from the same inputs.
function test_interlock_follower_edit_mid_cycle_recomputes_same_cycle()
  local song, follower = setup({follower_mod = D1, leader_mod = D1})
  m_clock.init(); m_clock:start(); pulses(24 * 3)
  local before = follower.working_pattern.foundation.interlock
  song.patterns[4].trig_values[6] = 0
  pattern_module.update_working_pattern(FOLLOWER, song)
  local after = follower.working_pattern.foundation.interlock
  luaunit.assert_equals(after.blocked, before.blocked)
  luaunit.assert_equals(follower.working_pattern.trig_values[6], 0)
  stop_transport()
end

-- A leader source edit mid-cycle (unequal cycle lengths) reaches the follower
-- with its lookahead invalidation.
function test_interlock_leader_source_edit_mid_cycle_rebuilds_follower()
  local song, follower = setup({follower_mod = D1, follower_last = 7, leader_mod = D1, leader_last = 5,
    leader_anchors = {1}})
  m_clock.init(); m_clock:start(); pulses(24 * 3 + 5)
  luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 6})
  local calls, restore = recording_lookahead()
  song.patterns[1].trig_values[2] = 1
  pattern_module.update_source_working_patterns(song, 1)
  restore()
  luaunit.assert_true(invalidated(calls, FOLLOWER))
  luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 2, 6, 7})
  stop_transport()
  local log = play(song, 24 * 30)
  assert_grid_and_midi_agree(log, "after edit")
  assert_matches_leader_playback(log, 0, "after edit")
end

-- A manual sweep driver: debounce restarts the sweep; `step` resumes it once.
local function manual_scheduler()
  local driver = {current = nil}
  driver.debounce = function(func)
    return function(...)
      local args = {...}
      driver.current = coroutine.create(function() func(table.unpack(args)) end)
    end
  end
  driver.step = function()
    if driver.current and coroutine.status(driver.current) ~= "dead" then
      assert(coroutine.resume(driver.current))
    end
  end
  driver.finish = function()
    while driver.current and coroutine.status(driver.current) ~= "dead" do driver.step() end
  end
  return driver
end

-- Sweep interleavings: leaders first; until the follower's own rebuild runs it
-- keeps its previous admission; an edit landing between the leader's and the
-- follower's rebuild, a synchronous update while a sweep is pending and a
-- stale completion all leave the admission of the last build from live data.
function test_interlock_yielding_sweep_interleavings_keep_the_last_build()
  local saved_scheduler = scheduler
  local driver = manual_scheduler()
  scheduler = driver
  local ok, err = pcall(function()
    local song, follower = setup({follower_mod = D1, follower_last = 8, leader_mod = D1, leader_last = 4,
      leader_anchors = {1}})
    luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 5})
    local old_follower = follower.working_pattern
    -- Leader source edit: a sweep over leader then follower.
    local calls, restore = recording_lookahead()
    song.patterns[1].trig_values[2] = 1
    pattern_module.update_source_working_patterns(song, 1)
    restore()
    luaunit.assert_true(invalidated(calls, FOLLOWER))
    driver.step() -- leader (channel 2) first
    luaunit.assert_equals(song.channels[LEADER].working_pattern.foundation.roles[2], "anchor")
    luaunit.assert_is(follower.working_pattern, old_follower)
    -- An edit lands between the leader's and the follower's rebuild.
    song.patterns[1].trig_values[3] = 1
    pattern_module.update_source_working_patterns(song, 1)
    luaunit.assert_is(follower.working_pattern, old_follower)
    driver.finish()
    luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 2, 3, 5, 6, 7})
    -- A synchronous update while a sweep is pending.
    song.patterns[1].trig_values[2] = 0
    pattern_module.update_source_working_patterns(song, 1)
    pattern_module.update_working_pattern(LEADER, song)
    luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 3, 5, 7})
    driver.finish()
    luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 3, 5, 7})
    -- Stale completion: a sweep started before a newer edit completes after it.
    song.patterns[1].trig_values[3] = 0
    pattern_module.update_source_working_patterns(song, 1)
    local stale = driver.current
    driver.step()
    song.patterns[1].trig_values[4] = 1
    pattern_module.update_working_pattern(LEADER, song)
    luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 4, 5, 8})
    driver.current = stale
    driver.finish()
    luaunit.assert_equals(blocked_steps(follower.working_pattern), {1, 4, 5, 8})
    luaunit.assert_equals(follower.working_pattern, build(song, FOLLOWER))
  end)
  scheduler = saved_scheduler
  if not ok then error(err, 0) end
end

-- ---------------------------------------------------------------------------
-- §1.4 last-onset support endpoint and the single 64-cycle budget.

local function odd_steps()
  local steps = {}
  for step = 1, 63, 2 do steps[#steps + 1] = step end
  return steps
end

local function reason_count(result, reason)
  return #reason_steps(result, reason)
end

-- PERF-MERGE-HW-WORST shape: a 64-step /1 follower against a one-step /1
-- leader with an anchor there. The support [0, 63/16] (the last onset, not
-- the cycle end) meets exactly 64 leader cycles: supported, 64 anchors, zero
-- builds, and every one of the 31 candidate additions is removed.
function test_interlock_last_onset_support_worst_shape_is_exactly_the_budget()
  local song = setup({follower_mod = D1, follower_last = 64, leader_mod = D1, leader_last = 1,
    leader_anchors = {1}, follower_anchors = {1}, candidates = odd_steps(), window = 0})
  local result = build(song, FOLLOWER)
  local admission = result.foundation.interlock
  luaunit.assert_equals(admission.status, "ok")
  luaunit.assert_equals(admission.cycles, 64)
  luaunit.assert_equals(admission.anchors, 64)
  luaunit.assert_equals(admission.plan_builds, 0)
  luaunit.assert_equals(reason_count(result, "INTERLOCK CH02"), 31)
  luaunit.assert_equals(result.foundation.eligible_count, 0)
  luaunit.assert_equals(additions(result), {})
  -- One more follower step of window reaches leader cycle 64: PLAN LIMIT,
  -- with Interlock bypassed and the result of Interlock off.
  song = setup({follower_mod = D1, follower_last = 64, leader_mod = D1, leader_last = 1,
    leader_anchors = {1}, follower_anchors = {1}, candidates = odd_steps(), window = 1})
  result = build(song, FOLLOWER)
  admission = result.foundation.interlock
  luaunit.assert_equals(admission.status, "PLAN LIMIT")
  luaunit.assert_equals(admission.cycles, 65)
  luaunit.assert_equals(admission.plan_builds, 0)
  luaunit.assert_equals(reason_count(result, "INTERLOCK CH02"), 0)
  luaunit.assert_equals(result.foundation.eligible_count, 31)
  luaunit.assert_equals(result.foundation.admitted_count, 31)
end

-- The same endpoint while playing, in follower cycle j = 1: support
-- [64/16, 127/16] meets leader cycles 64..127.
function test_interlock_last_onset_support_worst_shape_in_a_later_cycle()
  local song, follower = setup({follower_mod = D1, follower_last = 64, leader_mod = D1, leader_last = 1,
    leader_anchors = {1}, follower_anchors = {1}, candidates = odd_steps(), window = 0})
  m_clock.init(); m_clock:start()
  pulses(24 * 64 + 1)
  luaunit.assert_equals(merge_timeline.k(FOLLOWER), 1)
  local admission = follower.working_pattern.foundation.interlock
  luaunit.assert_equals(admission.status, "ok")
  luaunit.assert_equals(admission.cycles, 64)
  luaunit.assert_equals(admission.anchors, 64)
  luaunit.assert_equals(reason_count(follower.working_pattern, "INTERLOCK CH02"), 31)
  stop_transport()
end

-- ---------------------------------------------------------------------------
-- §1.2 unsupported-admission fallback: RESYNC and PLAN LIMIT bypass Interlock
-- only; gap, eligibility, ranking, phrase-adjusted Amount, Accent and masks
-- run exactly as with Interlock off.

local function assert_same_as_interlock_off(result, plain, label)
  local plan, off = result.foundation, plain.foundation
  for step = 1, 64 do
    luaunit.assert_equals(plan.reasons[step], off.reasons[step], label .. " reason " .. step)
    luaunit.assert_equals(plan.roles[step], off.roles[step], label .. " role " .. step)
    for _, reason in ipairs(plan.reason_lists[step] or {}) do
      luaunit.assert_false(reason:find("^INTERLOCK") ~= nil, label .. " interlock reason " .. step)
    end
  end
  luaunit.assert_equals(plan.eligible_count, off.eligible_count, label)
  luaunit.assert_equals(plan.admitted_count, off.admitted_count, label)
  luaunit.assert_equals(additions(result), additions(plain), label)
  luaunit.assert_equals(result.trig_values, plain.trig_values, label)
  luaunit.assert_equals(result.velocity_values, plain.velocity_values, label)
end

local function fallback_config()
  return foundation(3, {gap = 2, amount = 40, seed = 321, interlock = {leader = LEADER, window = 0}})
end

function test_interlock_plan_limit_fallback_matches_interlock_off_with_gap_and_amount()
  local song, follower = setup({follower_mod = {name = "/128", value = 128, type = "clock_division"},
    follower_last = 32, follower_anchors = {3, 20}, leader_mod = {name = "x16", value = 16,
    type = "clock_multiplication"}, leader_last = 64, leader_anchors = {1, 3, 5, 7, 9},
    follower_config = fallback_config()})
  follower.step_trig_masks[21] = 1
  local result = build(song, FOLLOWER)
  luaunit.assert_equals(result.foundation.interlock.status, "PLAN LIMIT")
  local plain = without_interlock(song)
  luaunit.assert_true(#reason_steps(result, "gap") > 0)
  luaunit.assert_true(result.foundation.admitted_count > 0)
  luaunit.assert_true(result.foundation.admitted_count < result.foundation.eligible_count)
  assert_same_as_interlock_off(result, plain, "plan limit")
  -- The same configuration within the budget does filter.
  song = setup({follower_mod = D1, follower_last = 32, follower_anchors = {3, 20}, leader_mod = D1,
    leader_last = 4, leader_anchors = {2}, follower_config = fallback_config()})
  luaunit.assert_true(reason_count(build(song, FOLLOWER), "INTERLOCK CH02") > 0)
end

function test_interlock_resync_fallback_matches_interlock_off_with_gap_and_amount()
  local song, follower = setup({follower_mod = D1, follower_last = 32, follower_anchors = {3, 20},
    leader_mod = D1, leader_last = 4, leader_anchors = {2}, global_length = 64,
    follower_config = fallback_config()})
  m_clock.init(); m_clock:start(); pulses(24 * 2)
  luaunit.assert_true(reason_count(follower.working_pattern, "INTERLOCK CH02") > 0)
  m_clock.set_channel_division(LEADER, m_clock.calculate_divisor({value = 2, type = "clock_division"}))
  local result = follower.working_pattern
  luaunit.assert_equals(result.foundation.interlock.status, "RESYNC")
  luaunit.assert_equals(result.foundation.interlock.plan_builds, 0)
  luaunit.assert_true(#reason_steps(result, "gap") > 0)
  luaunit.assert_true(result.foundation.admitted_count < result.foundation.eligible_count)
  local plain = without_interlock(song)
  assert_same_as_interlock_off(result, plain, "resync")
  stop_transport()
end

-- ---------------------------------------------------------------------------
-- PERF-MERGE-HW-DENSE shape at host level: an x16 64-step leader with an
-- anchor on every step; a /4 64-step follower whose assigned anchor pattern
-- is empty and whose second source has every step (64 candidates). d_f / d_l
-- = 64, so each follower step lasts one leader cycle: 64 cycles, 4,096
-- anchors, every candidate on a leader step-1 anchor.
function test_interlock_dense_shape_counts_and_leader_step_one_toggle()
  local all = {}
  for step = 1, 64 do all[#all + 1] = step end
  local options = {follower_mod = {name = "/4", value = 4, type = "clock_division"}, follower_last = 64,
    follower_anchors = {}, leader_mod = {name = "x16", value = 16, type = "clock_multiplication"},
    leader_last = 64, leader_anchors = all, window = 0}
  local song = setup(options)
  local result = build(song, FOLLOWER)
  local admission = result.foundation.interlock
  luaunit.assert_equals(admission.status, "ok")
  luaunit.assert_equals(admission.cycles, 64)
  luaunit.assert_equals(admission.anchors, 4096)
  luaunit.assert_equals(admission.plan_builds, 0)
  luaunit.assert_equals(reason_count(result, "INTERLOCK CH02"), 64)
  luaunit.assert_equals(result.foundation.eligible_count, 0)
  luaunit.assert_equals(result.foundation.admitted_count, 0)
  -- Leader step-1 anchor trig off: no follower onset meets an anchor.
  song.patterns[1].trig_values[1] = 0
  pattern_module.update_source_working_patterns(song, 1)
  result = song.channels[FOLLOWER].working_pattern
  admission = result.foundation.interlock
  luaunit.assert_equals(admission.status, "ok")
  luaunit.assert_equals(admission.cycles, 64)
  luaunit.assert_equals(admission.anchors, 4032)
  luaunit.assert_equals(admission.plan_builds, 0)
  luaunit.assert_equals(reason_count(result, "INTERLOCK CH02"), 0)
  luaunit.assert_equals(result.foundation.eligible_count, 64)
  luaunit.assert_equals(result.foundation.admitted_count, 64)
  luaunit.assert_equals(#additions(result), 64)
end
