-- Mutation killers for lib/clock/m_clock.lua. Each case drives the real lattice pulse by
-- pulse and pins what a caller or the user observes: MIDI/transport calls, program
-- changes, recorded pattern data, slide values, grid/screen refresh requests and the
-- ring buffer's admission of slides. Unless a README line is cited, a case is
-- characterisation of current behaviour.
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

-- Hardware sinks and module binding for one case: nb and m_midi transport calls are
-- recorded instead of sent, the production global m_clock is this file's module (its
-- functions address channel clocks through that global), and every lattice pulse is
-- supplied explicitly (testing). Everything is restored even on failure.
local function with_clock(body)
  local log = {starts = 0, stops = {}}
  with_globals({
    testing = true,
    m_clock = m_clock,
    nb = {stop_all = function() end},
    norns_param_state_handler = include("mosaic/lib/devices/norns_param_state_handler"),
  }, function()
    with_fields(m_midi, {
      start = function() log.starts = log.starts + 1 end,
      stop = function(send_transport) log.stops[#log.stops + 1] = tostring(send_transport) end
    }, function() body(log) end)
  end)
end

-- A module instance with fresh module state (playing, one-time warning, transport owner).
-- Including it rebinds the global m_clock/clock_lattice; both are restored afterwards.
local function with_fresh_clock(body)
  local saved_module, saved_lattice = _G.m_clock, _G.clock_lattice
  local ok, err = pcall(function()
    local fresh = include("mosaic/lib/clock/m_clock")
    body(fresh)
  end)
  _G.m_clock, _G.clock_lattice = saved_module, saved_lattice
  if not ok then error(err, 0) end
end

-- Stop, then Start (inside with_clock).
local function start_clock(from_external_transport)
  m_clock:stop()
  m_clock:start(from_external_transport)
end

-------------------------------------------------------------------------------------------
-- Elektron program changes (README 1084-1086: pattern changes are mirrored to Elektron
-- devices). The call to step.process_elektron_program_change is recorded with the pulse.
-------------------------------------------------------------------------------------------

local function record_program_changes(body)
  local sent = {}
  with_fields(step, {
    process_elektron_program_change = function(song_pattern)
      sent[#sent + 1] = {pulse = m_clock.get_clock_lattice().transport, pattern = song_pattern}
    end
  }, function() body(sent) end)
  return sent
end


-- Pulses at which program changes are sent: at Start (pulse 1, before the first pulse) and
-- during count pulses of playback, for the given global (song slot) length.
local function program_change_pulses(global_length, enabled, count)
  local observed = {}
  with_clock(function()
    setup()
    program.get_selected_song_pattern().global_pattern_length = global_length
    params:set("elektron_program_changes", enabled and 2 or 1)
    record_program_changes(function(sent)
      start_clock()
      pulses(count)
      for _, entry in ipairs(sent) do
        luaunit.assert_equals(entry.pattern, 1, "Song mode off: the next slot is the current one")
        observed[#observed + 1] = entry.pulse
      end
    end)
  end)
  return observed
end

-- characterisation (SEM-013, arbitrated 2026-09-11, recorded at m_clock.lua:346-350): Start
-- announces the selected slot; lengths >= 3 announce the next slot two steps ahead of the
-- slot boundary (on the step where the master reaches length - 1); lengths 1 and 2 announce
-- it on the slot's final step. 24 pulses per step.
function test_mclk_program_changes_follow_the_song_slot_length()
  local nine_steps = 24 * 9
  luaunit.assert_equals(program_change_pulses(1, true, nine_steps), {1, 1, 25, 49, 73, 97, 121, 145, 169, 193})
  luaunit.assert_equals(program_change_pulses(2, true, nine_steps), {1, 25, 73, 121, 169})
  luaunit.assert_equals(program_change_pulses(3, true, nine_steps), {1, 25, 97, 169})
  luaunit.assert_equals(program_change_pulses(4, true, nine_steps), {1, 49, 145})
  -- README 1086: the setting defaults off; off sends nothing, at Start or during playback.
  luaunit.assert_equals(program_change_pulses(2, false, nine_steps), {})
  luaunit.assert_equals(program_change_pulses(4, false, nine_steps), {})
end

-------------------------------------------------------------------------------------------
-- Stop releases pending notes. README 310: "an ordinary Stop still releases notes and
-- sends Stop". Note releases are must_execute actions (step.lua play_note) and arp voice
-- releases are execute_at_note_end actions (step.lua play_arp_note).
-------------------------------------------------------------------------------------------

function test_mclk_stop_runs_pending_note_releases_once()
  with_clock(function(log)
    setup()
    start_clock()
    local ran = {}
    m_clock.delay_action(1, 4, "must_execute", function() ran[#ran + 1] = "note off" end)
    m_clock.delay_action(1, 4, "execute_at_note_end", function() ran[#ran + 1] = "arp note off" end)
    m_clock.delay_action(1, 4, "destroy_at_note_end", function() ran[#ran + 1] = "discarded" end)
    pulses(24)
    luaunit.assert_equals(ran, {})
    log.stops = {}
    m_clock:stop()
    luaunit.assert_equals(ran, {"note off", "arp note off"})
    luaunit.assert_equals(log.stops, {"nil"}, "Ordinary Stop does not suppress transport Stop")
    m_clock:stop()
    luaunit.assert_equals(ran, {"note off", "arp note off"}, "A release runs once")
  end)
end

-- A release that already fired must not take another pending release's place: the
-- remaining one still runs at Stop.
function test_mclk_a_fired_release_leaves_the_other_pending_for_stop()
  with_clock(function()
    setup()
    start_clock()
    local ran = {}
    m_clock.delay_action(1, 1, "must_execute", function() ran[#ran + 1] = "short" end)
    m_clock.delay_action(1, 8, "must_execute", function() ran[#ran + 1] = "long" end)
    pulses(30)
    luaunit.assert_equals(ran, {"short"})
    m_clock:stop()
    luaunit.assert_equals(ran, {"short", "long"})
  end)
end

-- Fired and restarted actions leave no pending ids behind (observed through the exported
-- pending count), so a long session does not accumulate them.
function test_mclk_fired_and_restarted_actions_leave_no_pending_ids()
  with_clock(function()
    setup()
    start_clock()
    m_clock.delay_action(1, 1, "destroy_at_note_end", function() end)
    m_clock.delay_action(1, 3, "destroy_at_note_end", function() end)
    luaunit.assert_equals(m_clock.get_destroy_at_note_end_ids_length(1), 2)
    pulses(30)
    luaunit.assert_equals(m_clock.get_destroy_at_note_end_ids_length(1), 1)
    pulses(48)
    luaunit.assert_equals(m_clock.get_destroy_at_note_end_ids_length(1), 0)
    m_clock.delay_action(1, 8, "destroy_at_note_end", function() end)
    luaunit.assert_equals(m_clock.get_destroy_at_note_end_ids_length(1), 1)
    start_clock()
    luaunit.assert_equals(m_clock.get_destroy_at_note_end_ids_length(1), 0)
  end)
end

-------------------------------------------------------------------------------------------
-- Transport: Start, Stop and the MIDI clock output boundary.
-------------------------------------------------------------------------------------------

-- Pattern helper: channel c plays notes {step = note offset} with the given length.
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

-- Pulse n times, tagging each emitted MIDI note with the transport it was sent on.
local function note_log(n)
  local out = {}
  for _ = 1, n do
    local t = lattice().transport
    lattice():pulse()
    while #midi_note_on_events > 0 do
      out[#out + 1] = "on@" .. t .. ":" .. table.remove(midi_note_on_events, 1)[1]
    end
    while #midi_note_off_events > 0 do
      out[#out + 1] = "off@" .. t .. ":" .. table.remove(midi_note_off_events, 1)[1]
    end
  end
  return table.concat(out, " ")
end

-- README 310/312: external MIDI Start resets to step 1 even while playing, and restart
-- cleanup does not send a MIDI Stop back to connected devices.
function test_mclk_external_start_while_playing_restarts_at_step_one_without_midi_stop()
  with_clock(function(log)
    setup()
    play_notes(1, {[1] = 0, [2] = 2, [3] = 4}, 0.5)
    start_clock()
    luaunit.assert_equals(note_log(30), "on@1:60 off@13:60 on@25:64")
    log.stops = {}
    m_clock:start(true)
    luaunit.assert_equals(log.stops, {"false"})
    luaunit.assert_true(m_clock.is_playing())
    luaunit.assert_equals(note_log(1), "on@1:60")
  end)
end

-- The one-time boundary warning, the playing flag and the native boundary owner are
-- module state; a fresh module is built for these cases.
function test_mclk_a_new_module_is_stopped_until_start()
  with_clock(function()
    setup()
    with_fresh_clock(function(fresh)
      luaunit.assert_false(fresh.is_playing())
      fresh.init()
      luaunit.assert_false(fresh.is_playing())
      fresh:start()
      luaunit.assert_true(fresh.is_playing())
      fresh:stop()
      luaunit.assert_false(fresh.is_playing())
    end)
  end)
end

-- A fake native MIDI output boundary (clock.midi.subscribe_output); restored afterwards.
local function with_fake_boundary(body)
  local subscriptions = {}
  with_fields(clock, {
    midi = {
      subscribe_output = function(callbacks) subscriptions[#subscriptions + 1] = callbacks; return #subscriptions end,
      cancel_output = function() end
    },
    run = function() return 1 end,
    cancel = function() end,
  }, function() body(subscriptions) end)
end

-- Local Play while already playing changes nothing: no second MIDI Start, no new lattice,
-- and no second output subscription while the first F8 is still pending.
function test_mclk_local_play_while_playing_does_not_restart()
  with_clock(function(log)
    setup()
    with_fresh_clock(function(fresh)
      fresh.init()
      fresh:start()
      local running = fresh.get_clock_lattice()
      luaunit.assert_equals(log.starts, 1)
      fresh:start()
      luaunit.assert_equals(log.starts, 1)
      luaunit.assert_equals(fresh.get_clock_lattice(), running)
      fresh:stop()
    end)
    with_fake_boundary(function(subscriptions)
      params:set("clock_midi_out_1", 1)
      with_fresh_clock(function(fresh)
        fresh.init()
        fresh:start()
        luaunit.assert_equals(#subscriptions, 1)
        fresh:start()
        luaunit.assert_equals(#subscriptions, 1)
        fresh:stop()
      end)
    end)
  end)
end

-- Pinned norns has no native output boundary (clock.midi has no subscribe_output). Asking
-- for clock output then warns once per session and falls back to a local start. Norns has
-- 16 MIDI ports and its paramset raises on an unknown id (core/paramset.lua:485-492), so
-- only clock_midi_out_1..16 may be read.
function test_mclk_unavailable_clock_output_warns_once_and_starts_locally()
  with_clock(function(log)
    local printed = {}
    local original_get = params.get
    local function norns_get(self, id)
      local port = type(id) == "string" and id:match("^clock_midi_out_(%d+)$")
      if port and (tonumber(port) < 1 or tonumber(port) > 16) then error("invalid paramset index: " .. id) end
      return original_get(self, id)
    end
    local function capture(...)
      local parts = {}
      for i = 1, select("#", ...) do parts[#parts + 1] = tostring(select(i, ...)) end
      printed[#printed + 1] = table.concat(parts, " ")
    end
    local function warnings()
      local n = 0
      for _, line in ipairs(printed) do if line:find("boundary unavailable", 1, true) then n = n + 1 end end
      return n
    end
    with_fields(clock, {midi = {}}, function()
      with_fields(params, {get = norns_get}, function()
        with_globals({print = capture}, function()
          setup()
          with_fresh_clock(function(fresh)
            fresh.init()
            fresh:start()
            luaunit.assert_equals(warnings(), 0, "No port sends clock: nothing to warn about")
            luaunit.assert_true(fresh.get_clock_lattice().enabled)
            fresh:stop()
            params:set("clock_midi_out_16", 1)
            fresh:start()
            luaunit.assert_equals(warnings(), 1)
            luaunit.assert_true(fresh.get_clock_lattice().enabled, "Falls back to a local start")
            fresh:stop()
            fresh:start()
            luaunit.assert_equals(warnings(), 1, "The warning is given once")
            fresh:stop()
          end)
        end)
      end)
    end)
    luaunit.assert_equals(log.starts, 3)
  end)
end

-- With a native boundary, Start is sent through it only when a port sends clock.
function test_mclk_clock_output_boundary_is_used_only_when_a_port_sends_clock()
  with_clock(function(log)
    setup()
    with_fake_boundary(function(subscriptions)
      with_fresh_clock(function(fresh)
        fresh.init()
        fresh:start()
        luaunit.assert_equals(#subscriptions, 0)
        luaunit.assert_equals(log.starts, 1)
        luaunit.assert_true(fresh.get_clock_lattice().enabled)
        fresh:stop()
        params:set("clock_midi_out_2", 1)
        fresh:start()
        luaunit.assert_equals(#subscriptions, 1)
        luaunit.assert_equals(log.starts, 1, "Start waits for the first F8")
        luaunit.assert_false(fresh.get_clock_lattice().enabled)
        subscriptions[1].before()
        luaunit.assert_equals(log.starts, 2)
        fresh:stop()
      end)
    end)
  end)
end

-- README 310: "A later external Start marks the next Clock as beat zero". With clock
-- output, the first forwarded tick after an external Start therefore catches up every
-- pulse since beat zero; a local Play starts at the tick's own phase (one pulse).
function test_mclk_external_start_forwards_beat_zero_to_the_clock_output()
  local function transport_after_first_tick(from_external_transport)
    local transport
    with_clock(function()
      setup()
      params:set("clock_midi_out_1", 1)
      with_fake_boundary(function(subscriptions)
        with_fresh_clock(function(fresh)
          fresh.init()
          fresh:start(from_external_transport)
          subscriptions[1].before()
          subscriptions[1].after(0.5, 1)
          transport = fresh.get_clock_lattice().transport
          fresh:stop()
        end)
      end)
    end)
    return transport
  end
  luaunit.assert_equals(transport_after_first_tick(true), 50)
  luaunit.assert_equals(transport_after_first_tick(nil), 2)
end

-- Without clock output the lattice runs from the norns clock coroutine. After an external
-- Start with the MIDI clock source it counts every pulse since beat zero (README 310); a
-- local Play, or an internal clock source, pulses once at the current phase. The coroutine
-- is resumed explicitly with a fixed beat position (no wall clock).
function test_mclk_native_pulses_count_from_beat_zero_only_after_external_start()
  local function transport_after_first_resume(from_external_transport, clock_source)
    local transport
    with_clock(function()
      setup()
      params:set("clock_source", clock_source)
      local scheduled
      with_globals({testing = false}, function()
        with_fields(clock, {
          run = function(body, arg) scheduled = {body = body, arg = arg}; return 7 end,
          sync = function(...) return coroutine.yield(...) end,
          get_beats = function() return 0.5 end,
          cancel = function() end,
        }, function()
          with_fresh_clock(function(fresh)
            fresh.init()
            fresh:start(from_external_transport)
            local thread = coroutine.create(scheduled.body)
            local ok, err = coroutine.resume(thread, scheduled.arg)
            luaunit.assert_true(ok, tostring(err))
            transport = fresh.get_clock_lattice().transport
            fresh:stop()
          end)
        end)
      end)
    end)
    return transport
  end
  luaunit.assert_equals(transport_after_first_resume(true, 2), 50)
  luaunit.assert_equals(transport_after_first_resume(true, 1), 2)
  luaunit.assert_equals(transport_after_first_resume(nil, 2), 2)
end

-------------------------------------------------------------------------------------------
-- Screen and grid refresh requests (fn.dirty_screen / fn.dirty_grid).
-------------------------------------------------------------------------------------------

function test_mclk_each_global_step_requests_a_screen_redraw()
  with_clock(function()
    setup()
    start_clock()
    fn.dirty_screen(false)
    pulses(1)
    luaunit.assert_true(fn.dirty_screen())
    fn.dirty_screen(false)
    pulses(24)
    luaunit.assert_true(fn.dirty_screen())
  end)
end

-- The grid shows the playhead of the selected channel on the channel and scale editors:
-- only that channel's steps request a grid redraw, and only on those pages.
function test_mclk_selected_channel_steps_request_grid_redraws_on_edit_pages()
  with_clock(function()
    setup()
    program.get_channel(1, 1).clock_mods = m_clock.get_clock_divisions()[15] -- /2: 48 pulses
    program.get().selected_channel = 1
    program.get().selected_page = pages.pages.channel_edit_page
    start_clock()
    fn.dirty_grid(false)
    pulses(1)
    luaunit.assert_true(fn.dirty_grid(), "Channel 1 step on the channel editor")
    fn.dirty_grid(false)
    pulses(47)
    luaunit.assert_false(fn.dirty_grid(), "Other channels' steps do not redraw")
    pulses(1)
    luaunit.assert_true(fn.dirty_grid())
    program.get().selected_page = pages.pages.song_edit_page
    fn.dirty_grid(false)
    pulses(48)
    luaunit.assert_false(fn.dirty_grid(), "Not on the song editor")
    program.get().selected_channel = 17
    program.get().selected_page = pages.pages.scale_edit_page
    fn.dirty_grid(false)
    pulses(24)
    luaunit.assert_true(fn.dirty_grid(), "Scale track steps on the scale editor")
  end)
end

-- Recording fixture: the real recorder, and memory refresh requests counted.
local function with_recording(body)
  with_globals({recorder = include("mosaic/lib/recorder")}, function()
    local refreshes = 0
    with_fields(channel_edit_page_ui, {refresh_memory = function() refreshes = refreshes + 1 end}, function()
      body(function() return refreshes end)
    end)
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

-- Pulse n times; report "step@pulse" when a stored mask (note 60 + step) reaches channel 1.
local function commit_log(n, steps)
  local channel = program.get_channel(1, 1)
  local out = {}
  for _ = 1, n do
    local t = lattice().transport
    lattice():pulse()
    for _, s in ipairs(steps) do
      if channel.step_note_masks[s] == 60 + s then
        out[#out + 1] = s .. "@" .. t
        channel.step_note_masks[s] = nil
      end
    end
  end
  return table.concat(out, " ")
end

local slide_onset_fixture = include("mosaic/lib/tests/helpers/slide_onset_fixture")

-------------------------------------------------------------------------------------------
-- Recording (README 239-241).
-------------------------------------------------------------------------------------------

-- Channel 1 armed and selected, with MIDI trig parameter 1 assigned to a recording param
-- whose action is recorded (it sends the value to the device in production).
local function armed_channel_with_param(trigless)
  program.get().selected_channel = 1
  params:set("record", 2)
  params:set("trigless_locks", trigless and 2 or 1)
  local channel = program.get_channel(1, 1)
  channel.trig_lock_params[1] = {type = "midi", param_id = "mclk_recorded_param", cc_msb = 7, off_value = -1}
  local sent = {}
  params:add("mclk_recorded_param", {action = function(value)
    sent[#sent + 1] = program.get_current_step_for_channel(1) .. "=" .. value
  end})
  return channel, sent
end

-- README 241: "Active MIDI values are sent again before each eligible step's note, even
-- when the value has not changed" and recording writes the edited parameter on eligible
-- steps. Eligible steps are trig steps, or every step with trigless locks on (step.lua
-- process_recording_params / recorder.record_trig_event).
function test_mclk_recording_resends_and_records_values_on_eligible_steps()
  with_clock(function()
    with_recording(function()
      for _, trigless in ipairs({false, true}) do
        setup()
        play_notes(1, {[1] = 0}, 0.25)
        local channel, sent = armed_channel_with_param(trigless)
        start_clock()
        recorder.set_trig_lock_dirty(1, 1, 64)
        pulses(24 * 3)
        local recorded = {}
        for s = 1, 4 do recorded[s] = program.get_step_param_trig_lock(channel, s, 1) or false end
        if trigless then
          luaunit.assert_equals(sent, {"1=64", "2=64", "3=64"})
          luaunit.assert_equals(recorded, {64, 64, 64, false})
        else
          luaunit.assert_equals(sent, {"1=64"})
          luaunit.assert_equals(recorded, {64, false, false, false})
        end
      end
    end)
  end)
end


-- README 239-241: while recording, edited MIDI parameters are written to every eligible
-- step. This composed clock-path matrix covers the complete ten-slot recorder bank at
-- once. Values edited between steps replace the next step independently; another channel
-- cannot leak into the armed channel; and the pattern wrap retires all dirty values before
-- the new first step so stale automation is not recorded again. The precise slot order and
-- dirty-state lifetime are characterisation, not manual text.
function test_mclk_all_ten_recording_slots_update_isolate_and_retire_at_wrap()
  with_clock(function()
    with_recording(function()
      setup()
      program.get().selected_channel = 1
      params:set("record", 2)
      params:set("trigless_locks", 2)
      local channel = program.get_channel(1, 1)
      channel.end_trig = {2, 4}
      local sent = {}
      for slot = 1, 10 do
        local id = "mclk_recorded_matrix_" .. slot
        channel.trig_lock_params[slot] = {
          type = "midi", param_id = id, cc_msb = slot - 1, off_value = -1
        }
        params:add(id, {action = function(value)
          sent[#sent + 1] = {step = program.get_current_step_for_channel(1), slot = slot, value = value}
        end})
        recorder.set_trig_lock_dirty(1, slot, slot)
        recorder.set_trig_lock_dirty(2, slot, 100 + slot)
      end

      start_clock()
      pulses(1) -- channel 1, step 1
      for slot = 1, 10 do recorder.set_trig_lock_dirty(1, slot, 50 + slot) end
      pulses(24) -- channel 1, step 2
      pulses(24) -- wrap to step 1; clears the armed channel's dirty bank first

      luaunit.assert_equals(#sent, 20)
      for slot = 1, 10 do
        luaunit.assert_equals(sent[slot], {step = 1, slot = slot, value = slot})
        luaunit.assert_equals(sent[10 + slot], {step = 2, slot = slot, value = 50 + slot})
        luaunit.assert_equals(program.get_step_param_trig_lock(channel, 1, slot), slot)
        luaunit.assert_equals(program.get_step_param_trig_lock(channel, 2, slot), 50 + slot)
        luaunit.assert_false(recorder.trig_lock_is_dirty(1, slot), "armed dirty slot " .. slot)
        luaunit.assert_equals(recorder.trig_lock_is_dirty(2, slot), 100 + slot,
          "unselected channel dirty slot " .. slot)
        luaunit.assert_nil(program.get_step_param_trig_lock(program.get_channel(1, 2), 1, slot),
          "wrong-channel write in slot " .. slot)
      end
    end)
  end)
end

-- A note recorded during a step is committed when that step ends, i.e. on the next step's
-- onset, and the memory view is refreshed at every step end of the armed channel. Channel 1
-- plays steps 1-5 (end_trig {5, 4}); the final step is committed when the channel wraps.
function test_mclk_recorded_notes_commit_when_their_step_ends()
  with_clock(function()
    with_recording(function(refreshes)
      setup()
      program.get().selected_channel = 1
      params:set("record", 2)
      program.get_channel(1, 1).end_trig = {5, 4}
      start_clock()
      stored_mask(1, 61); stored_mask(2, 62); stored_mask(5, 65)
      luaunit.assert_equals(commit_log(24, {1, 2, 5}), "")
      luaunit.assert_equals(commit_log(106, {1, 2, 5}), "1@25 2@49 5@121")
      luaunit.assert_equals(refreshes(), 5)
    end)
  end)
end

-- characterisation (suspected defect, m_clock.lua:456-462): the end-of-step commit derives
-- the step that just ended as "current step - 1", falling back to the raw end step on a
-- wrap. It ignores the channel's start step and the global-length cap, so on a wrap it
-- commits the wrong step and the real last step's note stays pending (until key release).
function test_mclk_wrap_commit_ignores_channel_start_and_global_cap()
  with_clock(function()
    with_recording(function()
      -- Steps 1-5 capped to 1-3 by global length 3: the wrap commits step 5, not step 3.
      setup()
      program.get().selected_channel = 1
      params:set("record", 2)
      program.get_channel(1, 1).end_trig = {5, 4}
      program.get_selected_song_pattern().global_pattern_length = 3
      start_clock()
      stored_mask(3, 63); stored_mask(5, 65)
      luaunit.assert_equals(commit_log(200, {3, 5}), "5@73")
      luaunit.assert_not_nil(recorder.mask_events[1][3], "Step 3's note is still pending")
      -- Steps 2-5: the wrap commits step 1, so step 5's note stays pending.
      setup()
      program.get().selected_channel = 1
      params:set("record", 2)
      program.get_channel(1, 1).start_trig = {2, 4}
      program.get_channel(1, 1).end_trig = {5, 4}
      start_clock()
      stored_mask(3, 63); stored_mask(5, 65)
      luaunit.assert_equals(commit_log(200, {3, 5}), "3@49")
      luaunit.assert_not_nil(recorder.mask_events[1][5], "Step 5's note is still pending")
    end)
  end)
end

-- Under shuffle the end-of-step processor follows the channel's own step lengths: each
-- step's note commits on the next step's onset. Settings arrive through the UI setters.
function test_mclk_recorded_notes_commit_on_shuffled_step_boundaries()
  with_clock(function()
    with_recording(function()
      setup()
      play_notes(1, {[1] = 0, [2] = 0, [3] = 0, [4] = 0, [5] = 0, [6] = 0, [7] = 0, [8] = 0}, 0.25)
      program.get().selected_channel = 1
      params:set("record", 2)
      start_clock()
      m_clock.set_swing_shuffle_type(1, 2)
      m_clock.set_channel_shuffle_feel(1, 1)
      m_clock.set_channel_shuffle_basis(1, 3)
      m_clock.set_channel_shuffle_amount(1, 100)
      for s = 1, 8 do stored_mask(s, 60 + s) end
      local channel = program.get_channel(1, 1)
      local onsets, commits = {}, {}
      for _ = 1, 200 do
        local t = lattice().transport
        lattice():pulse()
        while #midi_note_on_events > 0 do table.remove(midi_note_on_events, 1); onsets[#onsets + 1] = t end
        for s = 1, 8 do
          if channel.step_note_masks[s] == 60 + s then commits[#commits + 1] = t; channel.step_note_masks[s] = nil end
        end
      end
      luaunit.assert_equals(onsets, {1, 39, 59, 78, 97, 135, 155, 174})
      luaunit.assert_equals(commits, {39, 59, 78, 97, 135, 155, 174, 193})
    end)
  end)
end

-------------------------------------------------------------------------------------------
-- Parameter slides (README 962-971, 1080-1082).
-------------------------------------------------------------------------------------------

-- Replaced and finished slides are reclaimed from the front of the slide ring; when a long
-- slide blocks the front, the ring is compacted. Every live slide, including the one whose
-- request triggered compaction, keeps running with its own values, and requests after
-- compaction reuse retired slots without disturbing live slides.
function test_mclk_slide_ring_compaction_keeps_every_live_slide()
  with_clock(function()
    setup()
    start_clock()
    local values = {}
    local function recording(key)
      values[key] = {}
      return function(value) table.insert(values[key], value) end
    end
    local function filler(channel)
      return {channel_number = channel, trig_lock = 1, start_step = 1, end_step = 5, distance = 4,
        start_value = 0, end_value = 1, func = function() end}
    end
    local function replace(count, channel, last_func)
      for i = 1, count do
        local args = filler(channel)
        if i == count and last_func then args.func = last_func end
        m_clock.execute_action_across_steps_by_pulses(args)
      end
    end
    -- Onset 1: 100 replacements on channel 2 (slots 1-100); only the last stays live and the
    -- 99 retired slots in front of it are reclaimed.
    slide_onset_fixture.queue(m_clock, filler(2), function() replace(99, 2) end)
    pulses(24)
    -- Onset 2: four long slides (slots 101-104), then replacements that fill every slot;
    -- the last request arrives with the ring full and triggers compaction.
    for channel = 3, 6 do
      slide_onset_fixture.queue(m_clock, {channel_number = channel, trig_lock = 1, start_step = 1,
        end_step = 9, distance = 8, start_value = 0, end_value = 10 * channel, func = recording(channel)})
    end
    slide_onset_fixture.queue(m_clock, filler(2), function() replace(1018, 2, recording("trigger")) end)
    pulses(24)
    -- Onset 3: 120 more requests reuse the retired slots, including those the long slides
    -- occupied before compaction.
    slide_onset_fixture.queue(m_clock, filler(2), function() replace(119, 2, recording("after")) end)
    pulses(24 * 9)
    for channel = 3, 6 do
      -- Eight steps from pulse 25 (192 pulses), sampled every 8 pulses: 25 samples.
      luaunit.assert_equals(#values[channel], 25, "Samples of the slide on channel " .. channel)
      luaunit.assert_equals(values[channel][#values[channel]], 10 * channel)
    end
    luaunit.assert_equals(#values.trigger, 3, "The compaction request ran until it was replaced")
    luaunit.assert_equals(values.after[#values.after], 1)
    luaunit.assert_false(m_clock.channel_is_sliding({number = 3}, 1))
  end)
end

-- Slide timing follows the channel clock: a division or shuffle change mid-slide retimes
-- the rest of the slide from the current value to the same destination step.
local function slide_samples(change_at, change, shuffle)
  local log = {}
  setup()
  start_clock()
  if shuffle then
    m_clock.set_swing_shuffle_type(1, 2)
    m_clock.set_channel_shuffle_feel(1, 1)
    m_clock.set_channel_shuffle_basis(1, 1)
    m_clock.set_channel_shuffle_amount(1, 100)
  end
  slide_onset_fixture.queue(m_clock, {channel_number = 1, trig_lock = 1, start_step = 1, end_step = 5,
    start_value = 0, end_value = 96,
    func = function(value) log[#log + 1] = lattice().transport .. "=" .. string.format("%.2f", value) end})
  for _ = 1, 200 do
    if lattice().transport == change_at then change() end
    lattice():pulse()
  end
  return table.concat(log, " ")
end

function test_mclk_slides_retime_when_the_channel_clock_changes()
  with_clock(function()
    local head = "1=0.00 9=8.00 17=16.00 25=24.00 33=32.00 41=40.00 "
    luaunit.assert_equals(slide_samples(41, function() m_clock.set_channel_division(1, 2) end),
      head .. "49=44.00 57=48.00 65=52.00 73=56.00 81=60.00 89=64.00 97=68.00 105=72.00 " ..
      "113=76.00 121=80.00 129=84.00 137=88.00 145=92.00 153=96.00")
    luaunit.assert_equals(slide_samples(41, function() m_clock.set_channel_shuffle_basis(1, 3) end, true),
      head .. "49=48.78 57=57.57 65=66.35 73=75.14 81=83.92 89=92.71 97=96.00")
    luaunit.assert_equals(slide_samples(41, function() m_clock.set_channel_shuffle_amount(1, 50) end, true),
      head .. "49=47.59 57=55.19 65=62.78 73=70.37 81=77.97 89=85.56 97=93.15 105=96.00")
  end)
end

-- README 1082: with Param Slides Wrap a slide may run past the end of the channel; a slide
-- to the very next step still takes exactly one step (24 pulses).
function test_mclk_wrapping_slide_to_the_next_step_takes_one_step()
  with_clock(function()
    setup()
    start_clock()
    local check = slide_onset_fixture.observe(m_clock, {channel_number = 1, trig_lock = 1,
      start_step = 1, end_step = 2, should_wrap = true, start_value = 0, end_value = 24,
      func = function() end}, 24)
    pulses(60)
    check()
  end)
end

-- characterisation (suspected defect, m_clock.lua:59-67): fractional quantisation derives
-- its decimal places from floor(log10(quant)), so a quant with more decimals than that
-- (0.25) is rounded to one decimal (0.3) before use. Production slides pass quant 1 or nil;
-- only direct callers of the exported function reach this path.
function test_mclk_quantize_value_fractional_steps()
  luaunit.assert_equals(m_clock.quantize_value(0.74, 0.5), 0.5)
  luaunit.assert_equals(m_clock.quantize_value(0.76, 0.5), 1.0)
  luaunit.assert_equals(m_clock.quantize_value(1.2, 0.5), 1.0)
  luaunit.assert_almost_equals(m_clock.quantize_value(1, 0.25), 0.9, 1e-12)
end

-------------------------------------------------------------------------------------------
-- Arpeggios (README 813) and realignment.
-------------------------------------------------------------------------------------------

-- Channel 1 step 1 plays a root with two chord notes as an arp of the given division index.
local function arp_on_step_one(length, arp_division_index)
  play_notes(1, {[1] = 0}, length)
  program.get().selected_channel = 1
  local channel = program.get_selected_channel()
  channel.trig_lock_params[5].id = "chord_arp"
  channel.step_chord_masks[1] = {1, 2}
  program.add_step_param_trig_lock(1, 5, arp_division_index)
end

-- Voices release one arp division after their onset; when the note length ends first, the
-- sounding voice is released then (index 10 = 2/3 step = 16 pulses; 9 = 5/8 = 15 pulses).
function test_mclk_arp_voices_release_at_their_gap_or_at_the_note_end()
  with_clock(function()
    setup()
    arp_on_step_one(1, 10)
    start_clock()
    luaunit.assert_equals(note_log(40), "on@1:60 on@17:62 off@17:60 off@25:62")
    setup()
    arp_on_step_one(0.5, 10)
    start_clock()
    luaunit.assert_equals(note_log(40), "on@1:60 off@13:60")
    setup()
    arp_on_step_one(8, 9)
    start_clock()
    luaunit.assert_equals(note_log(130), "on@1:60 on@16:62 off@16:60 on@31:64 off@31:62 off@46:64 " ..
      "on@76:60 on@91:62 off@91:60 on@106:64 off@106:62 off@121:64")
  end)
end

-- A song transition with reset realigns the channel clocks (step.lua:1030-1033), which
-- happens on a global step. A divided channel restarts on that step, its end-of-step
-- processor with it; an arp already running keeps its own interval.
function test_mclk_realign_restarts_divided_channels_but_not_running_arps()
  with_clock(function()
    with_recording(function()
      setup()
      program.get_channel(1, 1).clock_mods = m_clock.get_clock_divisions()[17] -- /3: 72 pulses
      play_notes(1, {[1] = 0, [2] = 0, [3] = 0, [4] = 0}, 0.25)
      start_clock()
      luaunit.assert_equals(note_log(96), "on@1:60 off@19:60 on@73:60 off@91:60")
      m_clock.realign_sprockets()
      luaunit.assert_equals(note_log(100), "on@97:60 off@115:60 on@169:60 off@187:60")
      setup()
      program.get_channel(1, 1).clock_mods = m_clock.get_clock_divisions()[17]
      program.get().selected_channel = 1
      params:set("record", 2)
      start_clock()
      stored_mask(2, 62); stored_mask(3, 63)
      luaunit.assert_equals(commit_log(96, {2, 3}), "")
      m_clock.realign_sprockets()
      luaunit.assert_equals(commit_log(160, {2, 3}), "2@97 3@169")
    end)
    setup()
    arp_on_step_one(8, 9)
    start_clock()
    luaunit.assert_equals(note_log(96), "on@1:60 on@16:62 off@16:60 on@31:64 off@31:62 off@46:64 " ..
      "on@76:60 on@91:62 off@91:60")
    m_clock.realign_sprockets()
    luaunit.assert_equals(note_log(60), "on@106:64 off@106:62 off@121:64 on@151:60")
  end)
end

-- The scale track (channel 17) is never swung, even when a global swing applies to the
-- note channels.
function test_mclk_scale_track_is_not_swung_by_global_swing()
  with_clock(function()
    setup()
    params:set("global_swing_shuffle_type", 1)
    params:set("global_swing", 30)
    play_notes(1, {[1] = 0, [2] = 0, [3] = 0, [4] = 0, [5] = 0}, 0.25)
    local scale_steps, notes = {}, nil
    with_fields(step, {process_global_step_scale_trig_lock = function()
      scale_steps[#scale_steps + 1] = lattice().transport
    end}, function()
      start_clock()
      notes = note_log(100)
    end)
    luaunit.assert_equals(notes, "on@1:60 off@9:60 on@32:60 off@37:60 on@49:60 off@57:60 on@80:60 off@85:60 on@97:60")
    luaunit.assert_equals(scale_steps, {1, 25, 49, 73, 97})
  end)
end
-- README 813: with negative acceleration later arp gaps shrink below the voice length
-- (2/3 step), so voices overlap. When the note length ends (2.5 steps = pulse 61) every
-- voice still sounding is released at once.
function test_mclk_arp_note_end_releases_every_overlapping_voice()
  with_clock(function()
    setup()
    play_notes(1, {[1] = 0}, 2.5)
    program.get().selected_channel = 1
    local channel = program.get_selected_channel()
    channel.trig_lock_params[5].id = "chord_arp"
    channel.trig_lock_params[6].id = "chord_spread"
    channel.trig_lock_params[7].id = "chord_acceleration"
    channel.trig_lock_params[7].cc_min_value = -5
    channel.step_chord_masks[1] = {1, 2, 3, 4}
    program.add_step_param_trig_lock(1, 5, 10) -- arp 2/3
    program.add_step_param_trig_lock(1, 6, 5)  -- spread 1/4
    program.add_step_param_trig_lock(1, 7, -1) -- acceleration -1
    start_clock()
    luaunit.assert_equals(note_log(100), "on@1:60 off@17:60 on@23:62 on@39:64 off@39:62 on@49:65 " ..
      "on@53:67 off@55:64 off@61:67 off@61:65")
  end)
end
