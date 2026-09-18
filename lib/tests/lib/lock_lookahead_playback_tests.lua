-- Lock lookahead driven through the real clock. README "Lock lead time": a
-- step's MIDI parameter values leave a lead before the step, inside an earlier
-- clock pulse, and nothing else moves. Each case pulses the lattice by hand and
-- reads the pulse every CC left on, so what is asserted is what the receiver
-- hears and when: a value that already left is not sent again by its step, and
-- anything that changes what the receiver holds before that step is corrected
-- at the step.
step = step
local m_clock = include("mosaic/lib/clock/m_clock")

include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/norns_mock")
include("mosaic/lib/tests/helpers/mocks/channel_sequence_page_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_mock")

local function setup()
  program.init()
  globals.reset()
  params.reset()
end

local function lattice() return m_clock.get_clock_lattice() end

local function pulses(n)
  for _ = 1, n do lattice():pulse() end
end

local function with_globals(replacements, body)
  local saved = {}
  for name, value in pairs(replacements) do saved[name] = {value = _G[name]}; _G[name] = value end
  local ok, err = pcall(body)
  for name, entry in pairs(saved) do _G[name] = entry.value end
  if not ok then error(err, 0) end
end

local function with_fields(target, replacements, body)
  local saved = {}
  for name, value in pairs(replacements) do saved[name] = {value = target[name]}; target[name] = value end
  local ok, err = pcall(body)
  for name, entry in pairs(saved) do target[name] = entry.value end
  if not ok then error(err, 0) end
end

local function with_clock(body)
  with_globals({
    testing = true,
    m_clock = m_clock,
    nb = {stop_all = function() end},
    norns_param_state_handler = include("mosaic/lib/devices/norns_param_state_handler"),
  }, function()
    with_fields(m_midi, {start = function() end, stop = function() end}, body)
  end)
end

local function play_notes(c, notes)
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  for s, note in pairs(notes) do
    test_pattern.note_values[s] = note
    test_pattern.lengths[s] = 0.25
    test_pattern.trig_values[s] = 1
    test_pattern.velocity_values[s] = 100
  end
  program.get_song_pattern(1).patterns[c] = test_pattern
  fn.add_to_set(program.get_song_pattern(1).channels[c].selected_patterns, c)
  pattern.update_working_patterns()
end

local function cc_slot(c, slot, cc)
  local channel = program.get_channel(1, c)
  channel.trig_lock_params[slot] = {type = "midi", id = "cc" .. cc, param_id = "lookahead_param_" .. c .. "_" .. slot,
                                    cc_msb = cc, cc_min_value = 0, cc_max_value = 127, off_value = -1}
  -- The assigned value is Off, so only locked steps send anything.
  params:set(channel.trig_lock_params[slot].param_id, -1)
  return channel
end

-- Lead 25 ms at the mock's 120 bpm: 25 * 120 * 96 / 60000 = 4.8, so five pulses.
local LEAD_PULSES = 5

local function install_lookahead()
  m_midi.set_lead_time(25)
  m_clock.set_lock_contract("pulse-advance")
end

-- "cc<number>=<value>@<pulse>" for every CC that left, in order.
local function cc_log()
  local out = {}
  for _, event in ipairs(midi_event_log) do
    if event.kind == "cc" then out[#out + 1] = "cc" .. tostring(event.a) .. "=" .. tostring(event.b) .. "@" .. event.pulse end
  end
  return out
end

local function start_clock()
  m_clock:stop()
  m_clock:start()
end

-- Steps are 24 pulses apart with step 1 on pulse 1, so step 2 sounds on pulse 25
-- and step 3 on pulse 49 (characterisation of the mock clock).
local STEP_2, STEP_3 = 25, 49

-- README "Lock lead time": the value leaves a lead before its step and its step
-- does not send it again.
function test_lookahead_playback_sends_a_lock_early_and_its_step_does_not_repeat_it()
  with_clock(function()
    setup()
    install_lookahead()
    play_notes(1, {[1] = 60, [2] = 62})
    program.add_step_param_trig_lock_to_channel(cc_slot(1, 1, 1), 2, 1, 64)
    start_clock()
    pulses(STEP_2 + 2)
    luaunit.assert_equals(cc_log(), {"cc1=64@" .. (STEP_2 - LEAD_PULSES)})
  end)
end

-- A live control (lib/devices/param_manager.lua sends it straight to m_midi.cc)
-- turned after the early send leaves the receiver holding its value, not the
-- lock. The step has to put the lock back, so the note sounds as documented.
function test_lookahead_playback_step_restores_a_lock_a_live_control_overwrote()
  with_clock(function()
    setup()
    install_lookahead()
    play_notes(1, {[1] = 60, [2] = 62})
    program.add_step_param_trig_lock_to_channel(cc_slot(1, 1, 1), 2, 1, 64)
    start_clock()
    pulses(STEP_2 - 3)
    -- The pulse just run left the transport on the one after it.
    m_midi.cc(1, nil, 20, 1, 1)
    pulses(3)
    luaunit.assert_equals(cc_log(), {"cc1=64@" .. (STEP_2 - LEAD_PULSES), "cc1=20@" .. (STEP_2 - 2), "cc1=64@" .. STEP_2})
  end)
end

-- README "Resend unchanged locks": with the repeat off, a value is skipped only
-- because the receiver is already holding it. Once something else has written
-- the address, it no longer is, so the correction must still go.
function test_lookahead_playback_correction_is_not_swallowed_by_the_resend_cache()
  with_clock(function()
    setup()
    params:set("repeat_unchanged_locks", 1)
    install_lookahead()
    play_notes(1, {[1] = 60, [2] = 62})
    program.add_step_param_trig_lock_to_channel(cc_slot(1, 1, 1), 2, 1, 64)
    start_clock()
    pulses(STEP_2 - 3)
    -- The pulse just run left the transport on the one after it.
    m_midi.cc(1, nil, 20, 1, 1)
    pulses(3)
    luaunit.assert_equals(cc_log(), {"cc1=64@" .. (STEP_2 - LEAD_PULSES), "cc1=20@" .. (STEP_2 - 2), "cc1=64@" .. STEP_2})
  end)
end

-- What already left is kept across a pattern boundary so the step does not send
-- it twice. That record is of an address, not a slot: the incoming pattern's
-- slot 1 addresses a different control, and the equal value there has never
-- been sent.
function test_lookahead_playback_equal_value_at_another_address_is_still_sent()
  with_clock(function()
    setup()
    install_lookahead()
    play_notes(1, {[1] = 60, [2] = 62})
    local channel = cc_slot(1, 1, 1)
    program.add_step_param_trig_lock_to_channel(channel, 2, 1, 64)
    start_clock()
    pulses(STEP_2 - 3)
    -- The boundary discards what is pending and keeps what was sent; the
    -- incoming pattern's slot 1 is CC 2 with the same lock value.
    m_clock.discard_lookahead()
    channel.trig_lock_params[1].cc_msb = 2
    channel.trig_lock_params[1].id = "cc2"
    pulses(3)
    luaunit.assert_equals(cc_log(), {"cc1=64@" .. (STEP_2 - LEAD_PULSES), "cc2=64@" .. STEP_2})
  end)
end

-- README "Lock lead time": the lead is a time. A pending deadline counts pulses,
-- so a tempo change discards it and the next value is resolved with the pulse
-- count the new tempo needs: 25 ms at 240 bpm is 9.6, so ten pulses.
function test_lookahead_playback_recomputes_the_lead_in_pulses_after_a_tempo_change()
  with_clock(function()
    setup()
    install_lookahead()
    play_notes(1, {[1] = 60, [2] = 62, [3] = 64})
    local channel = cc_slot(1, 1, 1)
    program.add_step_param_trig_lock_to_channel(channel, 2, 1, 64)
    program.add_step_param_trig_lock_to_channel(channel, 3, 1, 70)
    start_clock()
    pulses(10)
    params:set("clock_tempo", 240)
    pulses(STEP_3 - 10 + 1)
    luaunit.assert_equals(cc_log(), {"cc1=64@" .. STEP_2, "cc1=70@" .. (STEP_3 - 10)})
  end)
end

-- Two tracks writing one physical address keep lead-0 timing (m_clock.lua
-- shared_addresses). When the second track is assigned onto the address while
-- the first track's value is already pending, that value must not leave early
-- either: the assignment is what makes the address shared.
function test_lookahead_playback_assigning_another_track_onto_an_address_cancels_its_pending_value()
  with_clock(function()
    setup()
    install_lookahead()
    play_notes(1, {[1] = 60, [2] = 62})
    program.add_step_param_trig_lock_to_channel(cc_slot(1, 1, 1), 2, 1, 64)
    cc_slot(2, 1, 2)
    start_clock()
    pulses(10)
    program.get_channel(1, 2).trig_lock_params[1].cc_msb = 1
    m_clock.forget_shared_addresses()
    pulses(STEP_2 - 10)
    luaunit.assert_equals(cc_log(), {"cc1=64@" .. STEP_2})
  end)
end

-- README "Song Sequencer": copying a song sequence over the one that is playing
-- replaces every channel's locks and assignments at once. A value resolved from
-- the old sequence must not leave, and the step sends the new sequence's lock.
function test_lookahead_playback_copying_a_song_sequence_over_the_playing_one_discards_its_values()
  with_clock(function()
    setup()
    install_lookahead()
    play_notes(1, {[1] = 60, [2] = 62})
    program.add_step_param_trig_lock_to_channel(cc_slot(1, 1, 1), 2, 1, 64)
    -- Sequence 2 is the same project with a different lock on step 2.
    program.set_song_pattern(1, 2)
    program.add_step_param_trig_lock_to_channel(program.get_channel(2, 1), 2, 1, 90)
    start_clock()
    pulses(10)
    program.set_song_pattern(2, 1)
    pulses(STEP_2 - 10)
    luaunit.assert_equals(cc_log(), {"cc1=90@" .. STEP_2})
  end)
end

-- A note is only appended to the pulse's output batch by m_midi; it reaches the
-- wire at the next flush. Finishing a step resolves the next step's values, and
-- under lookahead that reads and allocates. The notes of a group must be on the
-- wire before that work, not behind it (README "Lock lead time": nothing is
-- delayed to create the lead).
function test_lookahead_playback_notes_are_flushed_before_the_step_finishes()
  local Lattice = include("mosaic/lib/clock/m_lattice")
  local flushes, events = 0, {}
  local lattice = Lattice:new{auto = false, ppqn = 96}
  lattice.output = {
    begin = function() end,
    flush = function() flushes = flushes + 1 end,
    serve = function() end,
  }
  -- The lookahead's own pulse hook, whose presence is what makes the preview run
  -- when a step finishes.
  lattice.advance = function() end
  local sprocket = lattice:new_sprocket{
    action = function() end, division = 1 / 4, order = 2, enabled = true, realign = true,
  }
  sprocket.action = function() sprocket.note_pending = 1 end
  sprocket.note_action = function(self)
    self.note_pending = nil
    events[#events + 1] = "note:" .. flushes
  end
  sprocket.after_note_action = function()
    events[#events + 1] = "finish:" .. flushes
  end
  lattice:start()
  lattice:pulse()
  luaunit.assert_equals(#events, 2)
  luaunit.assert_equals(events[1]:match("^note:(%d+)$") ~= nil, true)
  local at_note = tonumber(events[1]:match("^note:(%d+)$"))
  local at_finish = tonumber(events[2]:match("^finish:(%d+)$"))
  luaunit.assert_true(at_finish > at_note, "the note batch must be flushed before the step finishes")
end
