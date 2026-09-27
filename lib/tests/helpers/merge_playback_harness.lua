-- Scheduler-level playback harness of the MM-09 Interlock tests. Nominal
-- onset times are counted in lattice pulses per step
-- (d · 384), exact for the clock mods used there.
local merge_timeline = include("mosaic/lib/musical_merge/timeline")

local harness = {}

function harness.pulses(count)
  for _ = 1, count do m_clock.get_clock_lattice():pulse() end
end

function harness.stop_transport()
  local saved_nb, saved_handler, saved_stop = rawget(_G, "nb"), rawget(_G, "norns_param_state_handler"), m_midi.stop
  rawset(_G, "nb", {stop_all = function() end})
  rawset(_G, "norns_param_state_handler", include("mosaic/lib/devices/norns_param_state_handler"))
  m_midi.stop = function() end
  local ok, err = pcall(function() m_clock:stop() end)
  rawset(_G, "nb", saved_nb); rawset(_G, "norns_param_state_handler", saved_handler); m_midi.stop = saved_stop
  if not ok then error(err, 0) end
end

function harness.pulses_per_step(mod)
  return math.floor(384 / m_clock.calculate_divisor(mod) / 4 + 0.5)
end

function harness.reverse_channel_order()
  local order = m_clock.get_clock_lattice().sprocket_pulse_order[2]
  local reversed = {}
  for index = #order, 1, -1 do reversed[#reversed + 1] = order[index] end
  m_clock.get_clock_lattice().sprocket_pulse_order[2] = reversed
end

-- Plays `total` pulses and records, per onset of the follower and leader:
-- nominal time, step, the working pattern's role/reasons/length and whether
-- MIDI sounded, plus the follower's admission (options.admission, default
-- "interlock") for every follower cycle. options.follower / options.leader
-- name the two channels.
function harness.play(song, total, options)
  options = options or {}
  local follower, leader = options.follower, options.leader
  local field = options.admission or "interlock"
  m_clock.init()
  local mods = {[follower] = song.channels[follower].clock_mods, [leader] = song.channels[leader].clock_mods}
  local log = {[follower] = {}, [leader] = {}}
  local cycles = {}
  local counts = {[follower] = 0, [leader] = 0}
  local notes_before = #midi_note_on_events
  -- Fresh sprockets count onsets from 0; Start sounds the first onset.
  local function observe()
    local sounded = {}
    for index = notes_before + 1, #midi_note_on_events do sounded[midi_note_on_events[index][3]] = true end
    for _, number in ipairs({follower, leader}) do
      local count = m_clock["channel_" .. number .. "_clock"].onset_count or 0
      if count > counts[number] then
        counts[number] = count
        local current = program.get_current_step_for_channel(number)
        local working = song.channels[number].working_pattern
        log[number][#log[number] + 1] = {
          time = (count - 1) * harness.pulses_per_step(mods[number]), step = current,
          role = working.foundation and working.foundation.roles[current],
          reasons = working.foundation and working.foundation.reason_lists and working.foundation.reason_lists[current],
          trig = working.trig_values[current], length = working.lengths[current],
          sounded = sounded[number] == true,
          k = merge_timeline.k(number)
        }
        if number == follower then
          local k = merge_timeline.k(follower)
          local admission = working.foundation and working.foundation[field]
          if admission and not cycles[k] then
            local blocked = {}
            for step in pairs(admission.blocked) do blocked[#blocked + 1] = step end
            table.sort(blocked)
            cycles[k] = {status = admission.status, blocked = table.concat(blocked, ",")}
          end
        end
      end
    end
  end
  m_clock:start()
  if options.reversed then harness.reverse_channel_order() end
  for _, number in ipairs({follower, leader}) do
    if options.swing then m_clock.set_channel_swing(number, options.swing) end
    if options.shuffle then
      m_clock.set_swing_shuffle_type(number, 2); m_clock.set_channel_shuffle_feel(number, 1)
      m_clock.set_channel_shuffle_basis(number, 1); m_clock.set_channel_shuffle_amount(number, 60)
    end
  end
  observe()
  for pulse = 1, total do
    if options.at_pulse then options.at_pulse(pulse) end
    notes_before = #midi_note_on_events
    harness.pulses(1)
    observe()
  end
  harness.stop_transport()
  return log, cycles
end

-- Grid (working pattern) and MIDI agree at every onset.
function harness.assert_grid_and_midi_agree(log, label)
  for number, onsets in pairs(log) do
    for index, onset in ipairs(onsets) do
      luaunit.assert_equals(onset.sounded, onset.trig == 1, label .. " ch" .. number .. " onset " .. index)
    end
  end
end

return harness
