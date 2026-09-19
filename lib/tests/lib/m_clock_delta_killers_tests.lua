-- Mutation killers for lib/clock/m_clock.lua (campaign mutation-bc0570c, wave 4 delta).
-- Each case drives the real lattice pulse by pulse and pins what a user observes: pending
-- note releases at Stop, parameter-slide values and times, and when recorded notes are
-- committed. Unless a README line is cited, an assertion is characterisation of current
-- behaviour. Every global or module field replaced here is restored even on failure.
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

local slide_onset_fixture = include("mosaic/lib/tests/helpers/slide_onset_fixture")

local function setup()
  program.init()
  globals.reset()
  params.reset()
end

local function lattice() return m_clock.get_clock_lattice() end

local function pulses(n)
  for _ = 1, n do lattice():pulse() end
end

-- Run body with the given globals replaced; restore them even on failure.
local function with_globals(replacements, body)
  local saved = {}
  for name, value in pairs(replacements) do saved[name] = {value = _G[name]}; _G[name] = value end
  local ok, err = pcall(body)
  for name, entry in pairs(saved) do _G[name] = entry.value end
  if not ok then error(err, 0) end
end

-- Run body with fields of a table replaced; restore them even on failure.
local function with_fields(target, replacements, body)
  local saved = {}
  for name, value in pairs(replacements) do saved[name] = {value = target[name]}; target[name] = value end
  local ok, err = pcall(body)
  for name, entry in pairs(saved) do target[name] = entry.value end
  if not ok then error(err, 0) end
end

-- Hardware sinks and module binding for one case: the production global m_clock is this
-- file's module, nb and m_midi transport calls go nowhere, and every lattice pulse is
-- supplied explicitly (testing).
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

local function start_clock()
  m_clock:stop()
  m_clock:start()
end

-- Channel c's shuffle settings, applied through the setters the song-slot boundary uses
-- (step.process_song_song_patterns -> channel_edit_page_ui.align_*).
local function shuffle(c, feel, basis, amount)
  m_clock.set_swing_shuffle_type(c, 2)
  m_clock.set_channel_shuffle_feel(c, feel)
  m_clock.set_channel_shuffle_basis(c, basis)
  m_clock.set_channel_shuffle_amount(c, amount)
end

-- A slide on channel c from step 1 to end_step, queued at the channel's next onset through
-- the real channel action. Every sample is logged as "transport=value".
local function slide(c, start_value, end_value, end_step, log)
  slide_onset_fixture.queue(m_clock, {channel_number = c, trig_lock = 1, start_step = 1, end_step = end_step,
    start_value = start_value, end_value = end_value,
    func = function(value) log[#log + 1] = lattice().transport .. "=" .. string.format("%.2f", value) end})
end

-- Pulse n times; before the pulse whose transport is a key of changes, call that change.
-- Called between pulses, a setter sees the same clock state as when the master clock calls
-- it at the start of that pulse on a song-slot boundary (order 1, before any channel).
local function run(n, changes)
  for _ = 1, n do
    local change = changes and changes[lattice().transport]
    if change then change() end
    lattice():pulse()
  end
end

-------------------------------------------------------------------------------------------
-- Stop (README 310: "an ordinary Stop still releases notes and sends Stop").
-------------------------------------------------------------------------------------------

-- Every pending release runs at Stop, however many are pending: note releases
-- (must_execute, step.lua play_note) and arp voice releases (execute_at_note_end).
-- Their order (newest first) is characterisation.
function test_w4k_stop_runs_every_pending_release()
  with_clock(function()
    setup()
    start_clock()
    local ran = {}
    for _, name in ipairs({"note a", "note b", "note c"}) do
      m_clock.delay_action(1, 4, "must_execute", function() ran[#ran + 1] = name end)
    end
    for _, name in ipairs({"arp a", "arp b"}) do
      m_clock.delay_action(1, 4, "execute_at_note_end", function() ran[#ran + 1] = name end)
    end
    pulses(24)
    luaunit.assert_equals(ran, {})
    m_clock:stop()
    luaunit.assert_equals(ran, {"note c", "note b", "note a", "arp b", "arp a"})
  end)
end

-------------------------------------------------------------------------------------------
-- Parameter slides retimed by clock changes (README 964: locks "smoothly transition
-- between each other"; README 685: each channel has an independent swing/shuffle setting).
-------------------------------------------------------------------------------------------

-- README 685: a shuffle change on channel 1 retimes channel 1's running slide and leaves
-- channel 2's slide on channel 2's own, unchanged clock.
function test_w4k_a_shuffle_change_retimes_only_its_own_channels_slides()
  with_clock(function()
    setup()
    start_clock()
    shuffle(1, 1, 1, 100)
    local one, two = {}, {}
    slide(1, 0, 96, 5, one)
    slide(2, 0, 96, 5, two)
    run(200, {[41] = function() m_clock.set_channel_shuffle_basis(1, 3) end})
    local head = "1=0.00 9=8.00 17=16.00 25=24.00 33=32.00 41=40.00 "
    -- characterisation: channel 1 continues from its value at the change to the moved step 5.
    luaunit.assert_equals(table.concat(one, " "),
      head .. "49=48.78 57=57.57 65=66.35 73=75.14 81=83.92 89=92.71 97=96.00")
    luaunit.assert_equals(table.concat(two, " "),
      head .. "49=48.00 57=56.00 65=64.00 73=72.00 81=80.00 89=88.00 97=96.00")
  end)
end

-- characterisation: a slide whose destination step has already begun, but whose final value
-- is still waiting for the next 8-pulse sample, is not retimed by a clock change; it ends
-- on its destination value at that sample, and the change raises no error. A slide is left
-- in this state whenever its destination step does not hand it over (step.process_params
-- returns early for a muted channel). Channel 1 onsets fall at 1 and 39; samples at 1+8k.
function test_w4k_a_clock_change_after_the_destination_step_lets_the_slide_finish()
  with_clock(function()
    setup()
    start_clock()
    shuffle(1, 1, 3, 100)
    local log = {}
    slide(1, 0, 96, 2, log)
    local onsets
    run(60, {[40] = function()
      onsets = m_clock.channel_1_clock.onset_count
      m_clock.set_channel_shuffle_amount(1, 50)
    end})
    luaunit.assert_equals(onsets, 2, "The destination onset (pulse 39) has already run")
    luaunit.assert_equals(table.concat(log, " "), "1=0.00 9=20.21 17=40.42 25=60.63 33=80.84 41=96.00")
  end)
end

-- characterisation: two clock changes in one moment (as when the song-slot boundary applies
-- several queued changes) each continue from the value the previous one rebased to. At
-- pulse 24 the first change (a shuffle basis stored while the channel swings, so its clock
-- is unchanged) rebases the slide to 92 with one pulse left; the second (switching to
-- shuffle) moves step 2 to pulse 26, so pulse 25 samples halfway from 92 to 96.
function test_w4k_a_second_change_in_the_same_moment_continues_from_the_rebased_value()
  with_clock(function()
    setup()
    start_clock()
    m_clock.set_channel_shuffle_amount(1, 100)
    local log = {}
    slide(1, 0, 96, 2, log)
    run(64, {[24] = function()
      m_clock.set_channel_shuffle_basis(1, 3)
      m_clock.set_swing_shuffle_type(1, 2)
    end})
    luaunit.assert_equals(table.concat(log, " "), "1=0.00 9=32.00 17=64.00 25=94.00 33=96.00")
  end)
end

-- README 964: a retimed slide continues smoothly from its current value. A falling slide
-- from 96 to 0 is at 56 when the division halves at pulse 41; the rest runs from 56 to 0
-- over the slower steps (characterisation of the exact samples).
function test_w4k_a_retimed_falling_slide_continues_from_its_current_value()
  with_clock(function()
    setup()
    start_clock()
    local log = {}
    slide(1, 96, 0, 5, log)
    run(200, {[41] = function() m_clock.set_channel_division(1, 2) end})
    luaunit.assert_equals(table.concat(log, " "),
      "1=96.00 9=88.00 17=80.00 25=72.00 33=64.00 41=56.00 49=52.00 57=48.00 65=44.00 73=40.00 " ..
      "81=36.00 89=32.00 97=28.00 105=24.00 113=20.00 121=16.00 129=12.00 137=8.00 145=4.00 153=0.00")
  end)
end

-- characterisation: switching the swing/shuffle type and changing the shuffle feel both
-- retime a running slide to the moved destination step (only basis, amount and division
-- changes were covered before).
function test_w4k_swing_type_and_shuffle_feel_changes_retime_running_slides()
  with_clock(function()
    local function samples(prepare, change)
      local log = {}
      setup()
      start_clock()
      prepare()
      slide(1, 0, 96, 5, log)
      run(250, {[41] = change})
      return table.concat(log, " ")
    end
    local head = "1=0.00 9=8.00 17=16.00 25=24.00 33=32.00 41=40.00 "
    -- Shuffle settings stored while the channel swings; the type switch activates them.
    luaunit.assert_equals(samples(function()
      m_clock.set_channel_shuffle_feel(1, 1)
      m_clock.set_channel_shuffle_basis(1, 3)
      m_clock.set_channel_shuffle_amount(1, 100)
    end, function() m_clock.set_swing_shuffle_type(1, 2) end),
      head .. "49=49.74 57=59.48 65=69.22 73=78.96 81=88.70 89=96.00")
    luaunit.assert_equals(samples(function() shuffle(1, 1, 3, 100) end,
      function() m_clock.set_channel_shuffle_feel(1, 2) end),
      head .. "49=46.79 57=53.58 65=60.36 73=67.15 81=73.94 89=80.73 97=87.52 105=94.30 113=96.00")
  end)
end

-------------------------------------------------------------------------------------------
-- Shuffle feel and recording (README 239: a recorded note belongs to the step active when
-- it is processed; it is committed when that step ends).
-------------------------------------------------------------------------------------------

local function play_notes(c, notes, length)
  program.set_selected_song_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  for s, note in pairs(notes) do
    test_pattern.note_values[s] = note
    test_pattern.lengths[s] = length or 1
    test_pattern.trig_values[s] = 1
    test_pattern.velocity_values[s] = 100
  end
  program.get_song_pattern(1).patterns[c] = test_pattern
  fn.add_to_set(program.get_song_pattern(1).channels[c].selected_patterns, c)
  pattern.update_working_patterns()
end

local function with_recording(body)
  with_globals({recorder = include("mosaic/lib/recorder")}, function()
    with_fields(channel_edit_page_ui, {refresh_memory = function() end}, body)
  end)
end

-- A note mask stored by MIDI input while recording (recorder.handle_note_midi_message).
local function stored_mask(step_number, note)
  recorder.add_note_mask_event_portion(1, step_number, {
    song_pattern = 1,
    data = {song_pattern = 1, trig = 1, note = note, velocity = 100, length = 1,
      chord_degrees = {nil, nil, nil, nil}, step = step_number}
  })
end

-- Pulses at which channel 1's notes start, and at which each step's recorded note is
-- committed, under shuffle basis 3 at full amount with the given feel.
local function onsets_and_commits(feel)
  local onsets, commits = {}, {}
  with_recording(function()
    setup()
    play_notes(1, {[1] = 0, [2] = 0, [3] = 0, [4] = 0, [5] = 0, [6] = 0, [7] = 0, [8] = 0}, 0.25)
    program.get().selected_channel = 1
    params:set("record", 2)
    start_clock()
    shuffle(1, feel, 3, 100)
    for s = 1, 8 do stored_mask(s, 60 + s) end
    local channel = program.get_channel(1, 1)
    for _ = 1, 200 do
      local t = lattice().transport
      lattice():pulse()
      while #midi_note_on_events > 0 do table.remove(midi_note_on_events, 1); onsets[#onsets + 1] = t end
      for s = 1, 8 do
        if channel.step_note_masks[s] == 60 + s then commits[#commits + 1] = t; channel.step_note_masks[s] = nil end
      end
    end
  end)
  return onsets, commits
end

-- Feels other than the first reach both the channel's step clock and its end-of-step
-- processor: steps follow the feel's own timing (characterisation of the pulses) and each
-- step's note is committed exactly when the next step starts.
function test_w4k_shuffle_feel_reaches_the_step_clock_and_the_step_end()
  with_clock(function()
    local expected = {
      [2] = {1, 30, 49, 68, 97, 126, 145, 164},
      [3] = {1, 20, 39, 59, 97, 116, 135, 155},
    }
    for feel, pulses_of_steps in pairs(expected) do
      local onsets, commits = onsets_and_commits(feel)
      luaunit.assert_equals(onsets, pulses_of_steps, "Step onsets with feel " .. feel)
      local next_onsets = {}
      for i = 2, #onsets do next_onsets[#next_onsets + 1] = onsets[i] end
      next_onsets[#next_onsets + 1] = 193
      luaunit.assert_equals(commits, next_onsets, "Commits with feel " .. feel)
    end
  end)
end
