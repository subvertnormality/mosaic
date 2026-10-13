-- Transport-wide counters, cycle logs and prediction (MM-09). Contract:
-- docs/musical-merge-extensions-plan.md §1.2.1 (state machine), §1.2.2 (cycle
-- log), §1.2.3 (prediction) and §1.3 (Off cost). README "Merge Shape" still
-- defers Interlock to MM-11, so every assertion is a characterisation of that
-- approved plan, outside the current manual.

local merge_config = include("mosaic/lib/musical_merge/config")
local merge_state = include("mosaic/lib/musical_merge/state")
local merge_timeline = include("mosaic/lib/musical_merge/timeline")
local transaction = include("mosaic/lib/optional_config_transaction")
local pattern_module = include("mosaic/lib/pattern")

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

-- Channel 1: Foundation, 2-cycle phrase, 3 steps. Channel 2: no merge, 5
-- steps at /1.5. Channel 3: Foundation per phrase, 4 steps at x2. The rest
-- keep their defaults (16 steps, no merge).
local function setup(global_length)
  program.init(); globals.reset(); params.reset(); memory.init()
  merge_state.reset(); merge_timeline.stop()
  program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  song.global_pattern_length = global_length or 64
  for number = 1, 16 do program.get().devices[number].midi_channel = number end
  for _, step in ipairs({1, 3, 5, 9}) do song.patterns[1].trig_values[step] = 1 end
  for _, step in ipairs({2, 4, 6, 7}) do song.patterns[2].trig_values[step] = 1 end
  local channels = song.channels
  channels[1].selected_patterns = {[1] = true, [2] = true}; set_range(channels[1], 1, 3)
  channels[1].musical_merge = foundation(1, {cycles = 2, shape = "custom", percentages = {50, 100}})
  channels[2].selected_patterns = {[2] = true}; set_range(channels[2], 2, 6)
  channels[2].clock_mods = {name = "/1.5", value = 1.5, type = "clock_division"}
  channels[3].selected_patterns = {[1] = true, [2] = true}; set_range(channels[3], 1, 4)
  channels[3].clock_mods = {name = "x2", value = 2, type = "clock_multiplication"}
  channels[3].musical_merge = foundation(1, {cycles = 1, variation = "per_phrase"})
  pattern_module.update_working_patterns(song)
  return song
end

local function pulses(count)
  for _ = 1, count do m_clock.get_clock_lattice():pulse() end
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

-- The logged segment of the channel's current cycle equals merge_state (the
-- log copies it; it never derives it). Channels without merge state log Off.
local function assert_log_matches_state(song, label)
  for number = 1, 16 do
    local k = merge_timeline.k(number)
    if k >= 0 then
      local config, cycle, phrase = merge_timeline.segment(number, k)
      local record = merge_state.peek(song, number)
      if record then
        luaunit.assert_is(config, record.active or false, label .. " ch" .. number)
        luaunit.assert_equals({cycle, phrase}, {record.cycle, record.phrase}, label .. " ch" .. number)
      else
        luaunit.assert_equals(config, song.channels[number].musical_merge or false, label .. " ch" .. number)
        luaunit.assert_equals({cycle, phrase}, {1, 0}, label .. " ch" .. number)
      end
    end
  end
end

-- Start: serial += 1, every k = 0, timing captured, resync cleared, one log
-- entry for cycle 0; the first onset after Start is not a wrap.
function test_timeline_start_sets_the_origin_and_logs_cycle_zero()
  local song = setup()
  local serial = merge_timeline.serial()
  luaunit.assert_false(merge_timeline.running())
  m_clock.init(); m_clock:start()
  luaunit.assert_true(merge_timeline.running())
  luaunit.assert_equals(merge_timeline.serial(), serial + 1)
  for number = 1, 16 do
    luaunit.assert_equals(merge_timeline.k(number), 0, number)
    luaunit.assert_false(merge_timeline.resync(number), number)
    luaunit.assert_nil(merge_timeline.segment(number, 1))
  end
  assert_log_matches_state(song, "start")
  -- The Start onset has sounded; it advanced nothing.
  pulses(5)
  for number = 1, 16 do luaunit.assert_equals(merge_timeline.k(number), 0, number) end
  stop_transport()
end

-- Every channel wrap increments k, for every channel whether or not merge is
-- enabled, and logs what merge_state holds after on_cycle_boundary.
function test_timeline_wraps_count_every_channel_and_log_merge_state()
  local song = setup()
  m_clock.init(); m_clock:start()
  local wraps = {}
  local previous = {}
  for number = 1, 16 do wraps[number] = 0; previous[number] = program.get_current_step_for_channel(number) end
  for _ = 1, 24 * 40 do
    pulses(1)
    for number = 1, 16 do
      local current = program.get_current_step_for_channel(number)
      local first = fn.calc_grid_count(song.channels[number].start_trig[1], song.channels[number].start_trig[2])
      if current == first and previous[number] ~= current then wraps[number] = wraps[number] + 1 end
      previous[number] = current
    end
    assert_log_matches_state(song, "wrap")
  end
  for number = 1, 16 do luaunit.assert_equals(merge_timeline.k(number), wraps[number], number) end
  luaunit.assert_true(wraps[1] >= 12 and wraps[2] >= 5 and wraps[3] >= 20)
  luaunit.assert_false(merge_timeline.resync(1))
  stop_transport()
end

-- Realign: a new origin; every k = -1 until the forced wrap makes it 0 without
-- counting an elapsed cycle; the phrase is not reset for the same slot.
function test_timeline_realign_restarts_the_origin_and_keeps_the_same_slot_phrase()
  local song = setup(8)
  params:set("song_mode", 2); params:set("reset_on_end_of_pattern_repeat", 2)
  song.active = true
  m_clock.init(); m_clock:start()
  pulses(24 * 8 - 1)
  local serial = merge_timeline.serial()
  local phrase_before = merge_state.peek(song, 1).phrase
  local cycle_before = merge_state.peek(song, 1).cycle
  luaunit.assert_equals(merge_timeline.k(1), 2) -- 3-step loop: wraps at 3 and 6
  pulses(1) -- the pattern boundary at 8/16
  luaunit.assert_equals(merge_timeline.serial(), serial + 1)
  for number = 1, 16 do
    luaunit.assert_equals(merge_timeline.k(number), 0, number)
    luaunit.assert_false(merge_timeline.resync(number), number)
    luaunit.assert_nil(merge_timeline.segment(number, 1))
  end
  -- Same slot: the forced wrap advanced the phrase position as today.
  local record = merge_state.peek(song, 1)
  luaunit.assert_equals({record.cycle, record.phrase},
    cycle_before == 2 and {1, phrase_before + 1} or {2, phrase_before})
  assert_log_matches_state(song, "realign")
  -- The realign alone sets k = -1; the forced wrap makes it 0.
  merge_timeline.realign(song)
  luaunit.assert_equals(merge_timeline.k(5), -1)
  merge_timeline.on_wrap(song, 5, song.channels[5], 8, 1)
  luaunit.assert_equals(merge_timeline.k(5), 0)
  luaunit.assert_false(merge_timeline.resync(5))
  stop_transport()
end

-- Timing change while playing: clock mod, range or global length.
function test_timeline_timing_changes_set_a_sticky_resync_until_the_next_origin()
  local song = setup()
  m_clock.init(); m_clock:start(); pulses(24 * 3)
  local original = m_clock.calculate_divisor(song.channels[2].clock_mods)
  m_clock.set_channel_division(2, m_clock.calculate_divisor({value = 3, type = "clock_division"}))
  luaunit.assert_true(merge_timeline.resync(2))
  m_clock.set_channel_division(2, original)
  pulses(24 * 20)
  luaunit.assert_true(merge_timeline.resync(2))
  assert_log_matches_state(song, "after timing change")
  luaunit.assert_false(merge_timeline.resync(4))
  -- A range edit is found at the next wrap.
  set_range(song.channels[4], 1, 12)
  pulses(24 * 16)
  luaunit.assert_true(merge_timeline.resync(4))
  luaunit.assert_false(merge_timeline.resync(5))
  -- A global length change differs for every channel.
  song.global_pattern_length = 32
  luaunit.assert_false(merge_timeline.check_timing(song, 5))
  luaunit.assert_true(merge_timeline.resync(5))
  stop_transport()
  -- Stop discards everything; Start is a new origin.
  luaunit.assert_false(merge_timeline.running())
  luaunit.assert_nil(merge_timeline.k(2))
  m_clock.init(); m_clock:start()
  for number = 1, 16 do luaunit.assert_false(merge_timeline.resync(number), number) end
  stop_transport()
end

-- A cycle that did not last its captured playable count (a start edit that
-- jumped the cursor and was restored before the wrap) resyncs.
function test_timeline_cycle_of_the_wrong_length_resyncs_at_its_wrap()
  local song = setup()
  m_clock.init(); m_clock:start(); pulses(24)
  set_range(song.channels[6], 9, 16)
  pulses(24 * 2)
  set_range(song.channels[6], 1, 16)
  pulses(24 * 16)
  luaunit.assert_true(merge_timeline.resync(6))
  stop_transport()
end

-- A song-slot transition without realign resyncs every channel; a global
-- (pattern-boundary) activation resyncs its channel.
function test_timeline_slot_change_and_global_activation_resync()
  local song = setup(8)
  params:set("song_mode", 2); params:set("reset_on_song_pattern_transition", 1)
  params:set("reset_on_end_of_pattern_repeat", 1)
  song.active = true
  program.set_song_pattern(1, 2); program.get_song_pattern(2).active = true
  m_clock.init(); m_clock:start()
  pulses(24 * 8)
  luaunit.assert_equals(program.get().selected_song_pattern, 2)
  for number = 1, 16 do luaunit.assert_true(merge_timeline.resync(number), number) end
  -- Every channel wraps again before the next boundary (which switches back).
  pulses(24 * 8 - 6)
  luaunit.assert_equals(program.get().selected_song_pattern, 2)
  assert_log_matches_state(program.get_selected_song_pattern(), "after slot change")
  stop_transport()

  song = setup(8)
  m_clock.init(); m_clock:start(); pulses(24)
  local snapshot = transaction.snapshot(song)
  snapshot.channels[3].musical_merge = foundation(2)
  luaunit.assert_true(transaction.apply(song, snapshot, true, "pattern"))
  luaunit.assert_false(merge_timeline.resync(3))
  pulses(24 * 8)
  luaunit.assert_nil(merge_state.peek(song, 3).global_queued)
  luaunit.assert_true(merge_timeline.resync(3))
  luaunit.assert_false(merge_timeline.resync(1))
  assert_log_matches_state(song, "after global activation")
  stop_transport()
end

-- §1.2.3: the prediction of every pending cycle equals the segment the
-- channel then logs, with the channel's callback before and after the
-- querying channel's, across a queued activation, an epoch restart, a
-- channel with no saved configuration and a first enable mid-play.
function test_timeline_prediction_equals_what_the_channel_then_logs()
  for _, reversed in ipairs({false, true}) do
    local song = setup(64)
    song.channels[5].musical_merge = nil
    m_clock.init(); m_clock:start()
    if reversed then
      local order = m_clock.get_clock_lattice().sprocket_pulse_order[2]
      local flipped = {}
      for index = #order, 1, -1 do flipped[#flipped + 1] = order[index] end
      m_clock.get_clock_lattice().sprocket_pulse_order[2] = flipped
    end
    local predictions = {}
    local compared = 0
    for pulse = 1, 24 * 60 do
      if pulse == 24 * 10 + 5 then
        local snapshot = transaction.snapshot(song)
        snapshot.channels[1].musical_merge = foundation(2, {cycles = 4, shape = "build",
          percentages = merge_config.curve("build", 4), seed = 3})
        snapshot.channels[5].musical_merge = foundation(1, {cycles = 2, shape = "custom", percentages = {10, 20}})
        luaunit.assert_true(transaction.apply(song, snapshot, true, "channel"))
        -- An apply is a user edit between prediction and activation (§1.2.3):
        -- it rebuilds followers; earlier predictions are superseded.
        predictions = {}
      elseif pulse == 24 * 30 + 11 then
        local snapshot = transaction.snapshot(song)
        snapshot.channels[3].musical_merge = foundation(1, {cycles = 2, shape = "custom", percentages = {1, 2},
          variation = "per_phrase", seed = 7})
        luaunit.assert_true(transaction.apply(song, snapshot, true, "channel"))
        predictions = {}
      end
      pulses(1)
      for _, number in ipairs({1, 2, 3, 5}) do
        local k = merge_timeline.k(number)
        -- Compare what was predicted for cycle k with what was logged.
        for _, predicted in ipairs(predictions[number .. ":" .. k] or {}) do
          local config, cycle, phrase = merge_timeline.segment(number, k)
          luaunit.assert_is(config, predicted.config or false, "ch" .. number .. " cycle " .. k)
          luaunit.assert_equals({cycle, phrase}, {predicted.cycle, predicted.phrase}, "ch" .. number .. " cycle " .. k)
          compared = compared + 1
        end
        predictions[number .. ":" .. k] = nil
        for ahead = 1, 3 do
          local key = number .. ":" .. (k + ahead)
          predictions[key] = predictions[key] or {}
          table.insert(predictions[key], merge_state.predict(song, number, song.channels[number].musical_merge, ahead))
        end
      end
    end
    luaunit.assert_true(compared > 200, compared)
    stop_transport()
  end
end

-- §1.3 Off cost: the counters and logs are bookkeeping only; Off/default
-- playback (no leader anywhere) is identical to the base revision a38d2e54,
-- including a first enable, the last disable and a re-enable mid-play, and
-- realigning pattern boundaries. The digest below was produced by running
-- this exact scenario (setup excluded from the timeline) on a38d2e54.
local OFF_BASELINE = {count = 318, digest = 2386480326}

local function off_scenario()
  program.init(); globals.reset(); params.reset(); memory.init(); merge_state.reset()
  program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  song.global_pattern_length = 16
  song.active = true
  params:set("song_mode", 2); params:set("reset_on_end_of_pattern_repeat", 2)
  for number = 1, 16 do program.get().devices[number].midi_channel = number end
  for _, step in ipairs({1, 3, 5, 9, 12}) do song.patterns[1].trig_values[step] = 1 end
  for _, step in ipairs({2, 4, 6, 7, 11, 14}) do song.patterns[2].trig_values[step] = 1 end
  local channels = song.channels
  for number = 1, 4 do channels[number].selected_patterns = {[1] = true, [2] = true} end
  channels[1].end_trig = {3, 4}
  channels[2].start_trig = {2, 4}; channels[2].end_trig = {6, 4}
  channels[2].clock_mods = {name = "/1.5", value = 1.5, type = "clock_division"}
  channels[3].end_trig = {5, 4}
  channels[3].clock_mods = {name = "x2", value = 2, type = "clock_multiplication"}
  channels[3].musical_merge = foundation(1, {cycles = 2, shape = "custom", percentages = {40, 100},
    variation = "per_phrase", seed = 9})
  channels[4].end_trig = {7, 4}
  pattern_module.update_working_patterns(song)
  m_clock.init(); m_clock:start()
  local function apply(number, value)
    local snapshot = transaction.snapshot(song)
    snapshot.channels[number].musical_merge = value
    luaunit.assert_true(transaction.apply(song, snapshot, true, "channel"))
  end
  for pulse = 1, 24 * 70 do
    if pulse == 24 * 5 + 3 then apply(1, foundation(1, {amount = 60})) end
    if pulse == 24 * 21 + 7 then apply(1, nil); apply(3, nil) end
    if pulse == 24 * 37 + 1 then apply(1, foundation(1, {amount = 30, seed = 5, cycles = 2,
      shape = "custom", percentages = {100, 50}})) end
    pulses(1)
  end
  stop_transport()
  local events = {}
  for index, event in ipairs(midi_note_on_events) do
    events[index] = table.concat({event[1], event[2], event[3]}, ",")
  end
  local text = table.concat(events, ";")
  local hash = 2166136261
  for index = 1, #text do hash = ((hash ~ string.byte(text, index)) * 16777619) & 0xffffffff end
  return {count = #events, digest = hash}
end

function test_timeline_off_playback_is_identical_to_the_base_revision()
  local result = off_scenario()
  luaunit.assert_true(result.count > 100)
  luaunit.assert_equals(result, OFF_BASELINE)
end

-- The per-wrap bookkeeping is O(1): no allocation grows with the number of
-- cycles played (the log is a fixed ring).
function test_timeline_log_is_a_bounded_ring()
  setup()
  m_clock.init(); m_clock:start()
  pulses(24 * 140)
  local record = merge_timeline.channel(3)
  local size = 0
  for _ in pairs(record.log_index) do size = size + 1 end
  luaunit.assert_equals(size, merge_timeline.RETENTION)
  -- Retention: segments covering the last 64 cycles only.
  local k = merge_timeline.k(3)
  luaunit.assert_true(k >= 64)
  luaunit.assert_not_nil(merge_timeline.segment(3, k - 63))
  luaunit.assert_nil(merge_timeline.segment(3, k - 64))
  stop_transport()
end
