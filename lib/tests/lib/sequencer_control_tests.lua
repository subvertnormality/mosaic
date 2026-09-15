-- Unit tests for lib/controls/sequencer.lua (the 16x4 step sequencer grid control).
-- range_gesture_tests.lua already covers the in-row channel dual_press matrix and
-- the in-row pattern note-length wrap for distinct keys; this file covers the rest.
-- Assertions not backed by README.md are marked "-- characterisation".

local sequencer_control = include("mosaic/lib/controls/sequencer")

local function coords(step) return ((step - 1) % 16) + 1, math.floor((step - 1) / 16) + 4 end

local function setup()
  program.init()
  globals.reset()
  params.reset()
end

local function with_overrides(overrides, body)
  local saved = {}
  for i, o in ipairs(overrides) do
    saved[i] = o[1][o[2]]
    o[1][o[2]] = o[3]
  end
  local ok, err = pcall(body)
  for i = #overrides, 1, -1 do
    overrides[i][1][overrides[i][2]] = saved[i]
  end
  if not ok then error(err, 0) end
end

-- construction and hit testing --------------------------------------------------

function test_seqctl_new_normalises_mode_and_starts_with_empty_unsaved_grid()
  local channel = sequencer_control:new(4, "channel")
  luaunit.assert_equals(channel.mode, "channel")
  luaunit.assert_equals(channel.y, 4)
  luaunit.assert_equals(channel.unsaved_grid, {})
  luaunit.assert_equals(sequencer_control:new(4, "pattern").mode, "pattern")
  -- characterisation: anything other than "channel" becomes "pattern".
  luaunit.assert_equals(sequencer_control:new(4, nil).mode, "pattern")
  luaunit.assert_equals(sequencer_control:new(4, "scale").mode, "pattern")
  local other = sequencer_control:new(4, "channel")
  luaunit.assert_not_is(other.unsaved_grid, channel.unsaved_grid)
end

function test_seqctl_is_this_covers_exactly_four_rows_from_y()
  local control = sequencer_control:new(4, "pattern")
  luaunit.assert_false(control:is_this(1, 3))
  luaunit.assert_true(control:is_this(1, 4))
  luaunit.assert_true(control:is_this(16, 7))
  luaunit.assert_false(control:is_this(1, 8))
  local lower = sequencer_control:new(2, "pattern")
  luaunit.assert_false(lower:is_this(1, 1))
  luaunit.assert_true(lower:is_this(1, 2))
  luaunit.assert_true(lower:is_this(1, 5))
  luaunit.assert_false(lower:is_this(1, 6))
end

function test_seqctl_show_and_hide_unsaved_grid()
  local control = sequencer_control:new(4, "pattern")
  local grid = {[3] = true}
  control:show_unsaved_grid(grid)
  luaunit.assert_is(control.unsaved_grid, grid)
  control:hide_unsaved_grid()
  luaunit.assert_equals(control.unsaved_grid, {})
  luaunit.assert_not_is(control.unsaved_grid, grid)
  luaunit.assert_equals(grid, {[3] = true})
end

-- press -----------------------------------------------------------------------

function test_seqctl_pattern_press_toggles_trig_and_activates_song_pattern()
  setup()
  local control = sequencer_control:new(4, "pattern")
  local pattern = program.get_selected_pattern()
  local song_pattern = program.get_selected_song_pattern()
  song_pattern.active = false
  -- README.md:397: "simply tap in steps using the sequencer".
  control:press(1, 4)
  luaunit.assert_equals(pattern.trig_values[1], 1)
  luaunit.assert_true(song_pattern.active)
  control:press(16, 7)
  luaunit.assert_equals(pattern.trig_values[64], 1)
  control:press(1, 4)
  luaunit.assert_equals(pattern.trig_values[1], 0)
  -- characterisation: untoggling does not deactivate the song pattern.
  luaunit.assert_true(song_pattern.active)
  for step = 2, 63 do luaunit.assert_equals(pattern.trig_values[step], 0) end
end

function test_seqctl_pattern_press_targets_the_selected_pattern_only()
  setup()
  program.get().selected_pattern = 3
  local control = sequencer_control:new(4, "pattern")
  control:press(2, 5)
  local song_pattern = program.get_selected_song_pattern()
  luaunit.assert_equals(song_pattern.patterns[3].trig_values[18], 1)
  luaunit.assert_equals(song_pattern.patterns[1].trig_values[18], 0)
  luaunit.assert_equals(song_pattern.patterns[2].trig_values[18], 0)
end

function test_seqctl_press_outside_rows_or_in_channel_mode_changes_nothing()
  setup()
  local pattern = program.get_selected_pattern()
  local song_pattern = program.get_selected_song_pattern()
  song_pattern.active = false
  local control = sequencer_control:new(4, "pattern")
  control:press(1, 3)
  control:press(1, 8)
  luaunit.assert_false(song_pattern.active)
  for step = 1, 64 do luaunit.assert_equals(pattern.trig_values[step], 0) end
  -- characterisation: in channel mode a plain press is a no-op for this control.
  local channel_control = sequencer_control:new(4, "channel")
  luaunit.assert_nil(channel_control:press(5, 4))
  luaunit.assert_equals(pattern.trig_values[5], 0)
  luaunit.assert_false(song_pattern.active)
end

-- long_press ------------------------------------------------------------------

function test_seqctl_pattern_long_press_resets_length_of_a_trig_only()
  setup()
  local control = sequencer_control:new(4, "pattern")
  local pattern = program.get_selected_pattern()
  pattern.trig_values[20] = 1; pattern.lengths[20] = 9
  pattern.trig_values[21] = 0; pattern.lengths[21] = 7
  local x, y = coords(20)
  control:long_press(x, y)
  luaunit.assert_equals(pattern.lengths[20], 1) -- characterisation
  control:long_press(coords(21))
  luaunit.assert_equals(pattern.lengths[21], 7)
  luaunit.assert_equals(pattern.trig_values[20], 1)
  luaunit.assert_equals(pattern.trig_values[21], 0)
end

function test_seqctl_long_press_outside_rows_or_in_channel_mode_changes_nothing()
  setup()
  local pattern = program.get_selected_pattern()
  local channel = program.get_selected_channel()
  pattern.trig_values[1] = 1; pattern.lengths[1] = 5
  local control = sequencer_control:new(4, "pattern")
  control:long_press(1, 3)
  control:long_press(1, 8)
  luaunit.assert_equals(pattern.lengths[1], 5)
  -- README.md:722: holding a step for a long time does nothing by itself.
  local channel_control = sequencer_control:new(4, "channel")
  luaunit.assert_nil(channel_control:long_press(1, 4))
  luaunit.assert_equals(pattern.lengths[1], 5)
  luaunit.assert_equals(channel.start_trig, {1, 4})
  luaunit.assert_equals(channel.end_trig, {16, 7})
end

-- dual_press ------------------------------------------------------------------

function test_seqctl_channel_dual_press_rejects_keys_outside_rows_on_either_side()
  setup()
  local control = sequencer_control:new(4, "channel")
  local channel = program.get_selected_channel()
  channel.start_trig = {2, 4}; channel.end_trig = {8, 4}
  -- first key above/below the sequencer rows, second key valid
  luaunit.assert_nil(control:dual_press(1, 3, 5, 5))
  luaunit.assert_nil(control:dual_press(1, 8, 5, 5))
  -- second key below the sequencer rows (above is covered by range_gesture_tests)
  luaunit.assert_nil(control:dual_press(1, 4, 5, 8))
  luaunit.assert_equals(channel.start_trig, {2, 4})
  luaunit.assert_equals(channel.end_trig, {8, 4})
end

function test_seqctl_channel_dual_press_stores_fresh_endpoint_tables_on_selected_channel()
  setup()
  program.get().selected_channel = 3
  local control = sequencer_control:new(4, "channel")
  local other = program.get_selected_song_pattern().channels[1]
  local before_start, before_end = other.start_trig, other.end_trig
  -- README.md:722: the end must be after the start.
  luaunit.assert_true(control:dual_press(4, 5, 2, 6))
  local channel = program.get_selected_channel()
  luaunit.assert_equals(channel.start_trig, {4, 5})
  luaunit.assert_equals(channel.end_trig, {2, 6})
  luaunit.assert_is(other.start_trig, before_start)
  luaunit.assert_is(other.end_trig, before_end)
  luaunit.assert_equals(other.start_trig, {1, 4})
  -- equal endpoints: README.md:722 "Selecting a one-step channel range ... is unsupported".
  luaunit.assert_false(control:dual_press(3, 6, 3, 6))
  luaunit.assert_equals(channel.start_trig, {4, 5})
  luaunit.assert_equals(channel.end_trig, {2, 6})
end

function test_seqctl_pattern_dual_press_ignores_steps_without_a_trig()
  setup()
  local control = sequencer_control:new(4, "pattern")
  local pattern = program.get_selected_pattern()
  pattern.trig_values[5] = 0; pattern.lengths[5] = 1
  luaunit.assert_nil(control:dual_press(5, 4, 9, 4))
  luaunit.assert_equals(pattern.lengths[5], 1)
  pattern.trig_values[5] = 1
  -- README.md:397: hold a trig, then choose its ending step.
  luaunit.assert_nil(control:dual_press(5, 4, 9, 4))
  luaunit.assert_equals(pattern.lengths[5], 5)
  for step = 1, 64 do
    if step ~= 5 then luaunit.assert_equals(pattern.lengths[step], 1) end
  end
end

function test_seqctl_pattern_dual_press_rejects_keys_outside_rows()
  setup()
  local control = sequencer_control:new(4, "pattern")
  local pattern = program.get_selected_pattern()
  pattern.trig_values[1] = 1; pattern.lengths[1] = 2
  control:dual_press(1, 4, 1, 3)
  control:dual_press(1, 4, 1, 8)
  control:dual_press(1, 3, 1, 4)
  control:dual_press(1, 8, 1, 4)
  luaunit.assert_equals(pattern.lengths[1], 2)
end

function test_seqctl_pattern_dual_press_wraps_and_targets_selected_pattern()
  setup()
  program.get().selected_pattern = 2
  local control = sequencer_control:new(4, "pattern")
  local song_pattern = program.get_selected_song_pattern()
  local selected = song_pattern.patterns[2]
  selected.trig_values[60] = 1
  song_pattern.patterns[1].trig_values[60] = 1
  -- end before start wraps across step 64: 60..64 then 1..3 = 8 steps.
  control:dual_press(12, 7, 3, 4)
  luaunit.assert_equals(selected.lengths[60], 8)
  luaunit.assert_equals(song_pattern.patterns[1].lengths[60], 1)
  -- end at 64 exactly: 5 steps, and end at 1: wraps to 6 steps.
  control:dual_press(12, 7, 16, 7)
  luaunit.assert_equals(selected.lengths[60], 5)
  control:dual_press(12, 7, 1, 4)
  luaunit.assert_equals(selected.lengths[60], 6)
end

function test_seqctl_pattern_dual_press_same_key_yields_sixty_five()
  setup()
  local control = sequencer_control:new(4, "pattern")
  local pattern = program.get_selected_pattern()
  pattern.trig_values[10] = 1
  -- characterisation: a zero difference takes the wrap branch, giving 64 + 1.
  -- Not reachable with two distinct physical keys.
  control:dual_press(10, 4, 10, 4)
  luaunit.assert_equals(pattern.lengths[10], 65)
end

-- draw ------------------------------------------------------------------------

-- Runs control:draw with every collaborator stubbed. Returns the ordered LED calls,
-- the trig-lock queries and the current-step queries.
local function run_draw(opts)
  local control = sequencer_control:new(4, opts.mode)
  if opts.unsaved then control:show_unsaved_grid(opts.unsaved) end

  local function pattern_from(trigs)
    local trig_values, lengths = {}, {}
    for s = 1, 64 do trig_values[s] = 0; lengths[s] = 1 end
    for s, len in pairs(trigs or {}) do trig_values[s] = 1; lengths[s] = len end
    return {trig_values = trig_values, lengths = lengths}
  end

  local sx, sy = coords(opts.start or 1)
  local ex, ey = coords(opts["end"] or 64)
  local channel = {
    number = 5,
    start_trig = {sx, sy},
    end_trig = {ex, ey},
    working_pattern = pattern_from(opts.channel_trigs),
  }
  local selected_pattern = pattern_from(opts.pattern_trigs)
  local locks = opts.locks or {}

  local led, lock_queries, step_queries = {}, {}, {}
  local ui = channel_edit_page_ui or {}
  local clock_module = m_clock or {}
  with_overrides({
    {_G, "channel_edit_page_ui", ui},
    {_G, "m_clock", clock_module},
    {program, "get_blink_state", function() return opts.blink end},
    {program, "get_selected_pattern", function() return selected_pattern end},
    {program, "get_selected_song_pattern", function() return {global_pattern_length = opts.global_length or 64} end},
    {program, "get_current_step_for_channel", function(n) table.insert(step_queries, n); return opts.current_step end},
    {ui, "should_show_step_has_trig_lock", function(c, step)
      luaunit.assert_is(c, channel)
      table.insert(lock_queries, step)
      return locks[step] == true
    end},
    {clock_module, "is_playing", function() return opts.playing == true end},
  }, function()
    control:draw(channel, function(x, y, level) table.insert(led, {x, y, level}) end)
  end)
  return led, lock_queries, step_queries
end

local function background(from, to, level, overrides)
  local calls = {}
  for s = from, to do
    local x, y = coords(s)
    table.insert(calls, {x, y, (overrides and overrides[s]) or level})
  end
  return calls
end

local function concat(a, b)
  local out = {}
  for _, v in ipairs(a) do table.insert(out, v) end
  for _, v in ipairs(b) do table.insert(out, v) end
  return out
end

local function distinct_sorted(list)
  local seen, out = {}, {}
  for _, v in ipairs(list) do if not seen[v] then seen[v] = true; table.insert(out, v) end end
  table.sort(out)
  return out
end

function test_seqctl_draw_pattern_mode_empty_grid_is_dim_row_major()
  local led, locks, steps = run_draw({mode = "pattern", blink = true, playing = true, current_step = 3})
  -- characterisation: 64 dim cells, row by row; pattern mode draws no playhead.
  luaunit.assert_equals(led, background(1, 64, 2))
  luaunit.assert_equals(locks, {})
  luaunit.assert_equals(distinct_sorted(steps), {5})
end

function test_seqctl_draw_pattern_mode_trig_is_bright_and_length_glows()
  -- README.md:397: bright steps are trigs; steps with a subtle glow show the length.
  local led = run_draw({mode = "pattern", blink = true, pattern_trigs = {[1] = 3}, channel_trigs = {[40] = 1}})
  luaunit.assert_equals(led, concat(background(1, 64, 2), {{1, 4, 15}, {2, 4, 5}, {3, 4, 5}}))
end

function test_seqctl_draw_pattern_length_ends_at_the_next_trig()
  -- README.md:397: one trig's duration ends upon meeting another.
  local led = run_draw({mode = "pattern", blink = true, pattern_trigs = {[1] = 5, [3] = 1}})
  luaunit.assert_equals(led, concat(background(1, 64, 2), {{1, 4, 15}, {2, 4, 5}, {3, 4, 15}}))
end

function test_seqctl_draw_pattern_length_wraps_past_step_64()
  local led = run_draw({mode = "pattern", blink = true, pattern_trigs = {[63] = 4}})
  -- characterisation
  luaunit.assert_equals(led, concat(background(1, 64, 2), {{15, 7, 15}, {16, 7, 5}, {1, 4, 5}, {2, 4, 5}}))
end

function test_seqctl_draw_pattern_length_longer_than_grid_stops_at_own_trig()
  local led = run_draw({mode = "pattern", blink = true, pattern_trigs = {[1] = 70}})
  -- characterisation
  luaunit.assert_equals(led, concat(concat(background(1, 64, 2), {{1, 4, 15}}), background(2, 64, 5)))
end

function test_seqctl_draw_pattern_unsaved_steps_flash_and_blink_dim_over_trigs()
  -- README.md:424: primed steps flash bright; those painted over an active step blink dimly.
  local unsaved = {[5] = true, [6] = true}
  local off = run_draw({mode = "pattern", blink = false, unsaved = unsaved, pattern_trigs = {[5] = 1}})
  luaunit.assert_equals(off, concat(background(1, 64, 2), {{5, 4, 12}, {5, 4, 15}, {5, 4, 3}, {6, 4, 12}}))
  local on = run_draw({mode = "pattern", blink = true, unsaved = unsaved, pattern_trigs = {[5] = 1}})
  luaunit.assert_equals(on, concat(background(1, 64, 2), {{5, 4, 15}, {5, 4, 15}, {5, 4, 0}, {6, 4, 15}}))
end

function test_seqctl_draw_pattern_tails_follow_the_channel_range_start_and_locks()
  -- characterisation (suspected defect: in pattern mode, sequencer.lua:131-132 still
  -- apply the drawn channel's start step and trig locks to length tails, although
  -- heads ignore them; the trigger edit page passes the selected channel).
  local led, locks = run_draw({
    mode = "pattern", blink = false, start = 10, ["end"] = 64,
    pattern_trigs = {[5] = 3, [20] = 3}, locks = {[21] = true},
  })
  luaunit.assert_equals(led, concat(background(1, 64, 2), {{5, 4, 15}, {4, 5, 15}, {5, 5, 4}, {6, 5, 5}}))
  luaunit.assert_equals(distinct_sorted(locks), {21, 22})
end

function test_seqctl_draw_channel_mode_lights_only_the_channel_range()
  -- README.md:722: the active range is indicated by brighter buttons.
  local led, locks, steps = run_draw({mode = "channel", blink = true, start = 5, ["end"] = 12})
  luaunit.assert_equals(led, background(5, 12, 2))
  luaunit.assert_equals(distinct_sorted(locks), {5, 6, 7, 8, 9, 10, 11, 12})
  luaunit.assert_equals(distinct_sorted(steps), {5})
end

function test_seqctl_draw_channel_mode_locked_range_steps_blink()
  local off = run_draw({mode = "channel", blink = false, start = 5, ["end"] = 12, locks = {[6] = true}})
  -- characterisation
  luaunit.assert_equals(off, background(5, 12, 2, {[6] = 1}))
  local on = run_draw({mode = "channel", blink = true, start = 5, ["end"] = 12, locks = {[6] = true}})
  luaunit.assert_equals(on, background(5, 12, 2))
end

function test_seqctl_draw_channel_mode_uses_working_pattern_trigs_within_range()
  local led, locks = run_draw({
    mode = "channel", blink = false, start = 5, ["end"] = 12, locks = {[6] = true},
    channel_trigs = {[3] = 4, [6] = 1, [8] = 3, [11] = 4},
    pattern_trigs = {[7] = 1},
  })
  -- characterisation: out-of-range trig 3 and its tail are hidden; locked trig 6
  -- blinks (12); trig 11's tail stops at the channel end (12).
  luaunit.assert_equals(led, concat(background(5, 12, 2, {[6] = 1}), {
    {6, 4, 12},
    {8, 4, 15}, {9, 4, 5}, {10, 4, 5},
    {11, 4, 15}, {12, 4, 5},
  }))
  luaunit.assert_equals(distinct_sorted(locks), {5, 6, 7, 8, 9, 10, 11, 12})
end

function test_seqctl_draw_channel_mode_locked_tail_blinks()
  local off = run_draw({mode = "channel", blink = false, start = 5, ["end"] = 12, channel_trigs = {[5] = 3}, locks = {[6] = true}})
  -- characterisation
  luaunit.assert_equals(off, concat(background(5, 12, 2, {[6] = 1}), {{5, 4, 15}, {6, 4, 4}, {7, 4, 5}}))
  local on = run_draw({mode = "channel", blink = true, start = 5, ["end"] = 12, channel_trigs = {[5] = 3}, locks = {[6] = true}})
  luaunit.assert_equals(on, concat(background(5, 12, 2), {{5, 4, 15}, {6, 4, 5}, {7, 4, 5}}))
end

function test_seqctl_draw_channel_mode_tail_wraps_only_into_range()
  local full = run_draw({mode = "channel", blink = true, start = 1, ["end"] = 64, channel_trigs = {[63] = 4}})
  -- characterisation
  luaunit.assert_equals(full, concat(background(1, 64, 2), {{15, 7, 15}, {16, 7, 5}, {1, 4, 5}, {2, 4, 5}}))
  local late = run_draw({mode = "channel", blink = true, start = 60, ["end"] = 64, channel_trigs = {[63] = 4}})
  luaunit.assert_equals(late, concat(background(60, 64, 2), {{15, 7, 15}, {16, 7, 5}}))
end

function test_seqctl_draw_channel_mode_playhead()
  local base = {mode = "channel", start = 5, ["end"] = 12, current_step = 7}
  local function with(extra)
    local o = {}
    for k, v in pairs(base) do o[k] = v end
    for k, v in pairs(extra) do o[k] = v end
    return o
  end
  -- characterisation for all playhead levels.
  luaunit.assert_equals(run_draw(with({blink = true, playing = true})), concat(background(5, 12, 2), {{7, 4, 10}}))
  luaunit.assert_equals(run_draw(with({blink = true, playing = false})), background(5, 12, 2))
  luaunit.assert_equals(run_draw(with({blink = false, playing = true, locks = {[7] = true}})),
    concat(background(5, 12, 2, {[7] = 1}), {{7, 4, 7}}))
  luaunit.assert_equals(run_draw(with({blink = true, playing = true, locks = {[7] = true}})),
    concat(background(5, 12, 2), {{7, 4, 10}}))
  luaunit.assert_equals(run_draw(with({blink = true, playing = true, current_step = 4})), background(5, 12, 2))
  luaunit.assert_equals(run_draw(with({blink = true, playing = true, current_step = 5})), concat(background(5, 12, 2), {{5, 4, 10}}))
  -- only the lower bound is checked: a playhead past the end is still drawn.
  luaunit.assert_equals(run_draw(with({blink = true, playing = true, current_step = 14})), concat(background(5, 12, 2), {{14, 4, 10}}))
end

function test_seqctl_draw_channel_mode_unsaved_is_drawn_outside_range()
  local led = run_draw({mode = "channel", blink = false, start = 5, ["end"] = 12, unsaved = {[3] = true, [8] = true}, channel_trigs = {[8] = 1}})
  -- characterisation
  luaunit.assert_equals(led, concat(background(5, 12, 2), {{3, 4, 12}, {8, 4, 12}, {8, 4, 15}, {8, 4, 3}}))
end

function test_seqctl_draw_channel_range_is_capped_by_global_length_from_start()
  -- README.md:917: the cap counts steps from the channel start; steps 2-4 with
  -- global length 2 play steps 2 and 3.
  luaunit.assert_equals(run_draw({mode = "channel", blink = true, start = 2, ["end"] = 4, global_length = 2}), background(2, 3, 2))
  luaunit.assert_equals(run_draw({mode = "channel", blink = true, start = 1, ["end"] = 16, global_length = 8}), background(1, 8, 2))
  luaunit.assert_equals(run_draw({mode = "channel", blink = true, start = 5, ["end"] = 12, global_length = 4}), background(5, 8, 2))
  luaunit.assert_equals(run_draw({mode = "channel", blink = true, start = 5, ["end"] = 12, global_length = 11}), background(5, 12, 2))
  luaunit.assert_equals(run_draw({mode = "channel", blink = true, start = 5, ["end"] = 12, global_length = 12}), background(5, 12, 2))
  luaunit.assert_equals(run_draw({mode = "channel", blink = true, start = 1, ["end"] = 12, global_length = 11}), background(1, 11, 2))
end
