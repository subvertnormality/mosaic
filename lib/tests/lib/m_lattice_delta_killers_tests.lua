-- Behavioural pins for lib/clock/m_lattice.lua written against the wave-4 delta
-- survivors of the Lua mutation campaign (mutation-bc0570c): the timing a
-- sounding note keeps across a channel reset, onset projection on fast, swung
-- and wrapping channel clocks, and occurrence projection from every callback
-- position. Every assertion goes through the Lattice/Sprocket API: a lattice is
-- driven pulse by pulse and each event records the lattice transport at which
-- it happened. No wall clock.
--
-- Resets are made the way m_clock.lua makes them: an order-1 1/16 "master"
-- sprocket calls realign_eligable_sprockets (step.lua process_song_song_patterns
-- -> m_clock.realign_sprockets) before the order-2 channel clocks run on that
-- pulse. Note releases are before_onset delayed actions and strums are plain
-- delayed actions, as in step.lua play_note_internal and the chord strum.
--
-- Labels:
--   README.md:<line>  -- the manual states the behaviour asserted; the pulse
--                        arithmetic is spelled out beside the assertion.
--   characterisation  -- value recorded from the current implementation; the
--                        manual does not state it.

local Lattice = include("mosaic/lib/clock/m_lattice")

local function new_lattice(args)
  args = args or {}
  if args.auto == nil then args.auto = false end
  local lattice = Lattice:new(args)
  lattice:start()
  return lattice
end

local function run(lattice, pulses)
  for _ = 1, pulses do lattice:pulse() end
end

local function copy(t)
  local out = {}
  for k, v in pairs(t) do out[k] = v end
  return out
end

-- Channel division as m_clock.lua builds it from a clock mod (divisions.lua):
-- "xN" multiplies the 1/16 master rate, "/N" divides it.
local function times(n) return 1 / (16 * n) end
local function over(n) return n / 16 end

-- A channel clock that is reset by the master at the given master onsets.
-- notes[k] lists what the channel schedules at its k-th onset:
--   {len = L}               a note release L channel steps later
--   {strum = S, len = L}    a strum S steps later that plays a note of length L
-- Returns the event log: "on<t>", "R<t>" (reset), "off<t>", "strum<t>", "soff<t>".
local function reset_log(channel_args, resets, notes, pulses)
  local lattice = new_lattice()
  local log = {}
  local count = 0
  lattice:new_sprocket({order = 1, division = 1 / 16, action = function(t)
    count = count + 1
    for _, at in ipairs(resets) do
      if at == count then
        log[#log + 1] = "R" .. t
        lattice:realign_eligable_sprockets()
      end
    end
  end})
  local channel
  local onset = 0
  local args = copy(channel_args)
  args.order = 2
  args.realign = true
  args.action = function(t)
    onset = onset + 1
    log[#log + 1] = "on" .. t
    for _, note in ipairs(notes[onset] or {}) do
      if note.strum then
        channel:set_delayed_action(note.strum, function()
          log[#log + 1] = "strum" .. lattice.transport
          channel:set_delayed_action(note.len, function() log[#log + 1] = "soff" .. lattice.transport end, true)
        end)
      else
        channel:set_delayed_action(note.len, function() log[#log + 1] = "off" .. lattice.transport end, true)
      end
    end
  end
  channel = lattice:new_sprocket(args)
  run(lattice, pulses)
  return log
end

---------------------------------------------------------------------------
-- Sounding notes across a reset
---------------------------------------------------------------------------

function test_w4l_reset_keeps_the_remaining_duration_of_sounding_notes()
  -- README.md:805 "Pattern resets likewise preserve the remaining duration of
  -- sounding notes." README.md:1074 a song-sequence reset restarts every
  -- channel. A 1/8 channel (/2) steps every 48 pulses; its note starts on
  -- pulse 1 and the reset lands mid-step on pulse 25, where the channel
  -- restarts (on25). Each release stays 48 * length pulses after pulse 1.
  local eighth = {division = over(2)}
  -- README.md:805: one step -> pulse 49.
  luaunit.assert_equals(reset_log(eighth, {2}, {{{len = 1}}}, 130),
    {"on1", "R25", "on25", "off49", "on73", "on121"})
  -- README.md:805: three quarters of a step -> pulse 37.
  luaunit.assert_equals(reset_log(eighth, {2}, {{{len = 0.75}}}, 130),
    {"on1", "R25", "on25", "off37", "on73", "on121"})
  -- README.md:805: one and a half steps -> pulse 73, where the restarted channel
  -- has its next onset. characterisation: the due release is sent before
  -- that onset, as a release due on an onset pulse is without a reset.
  luaunit.assert_equals(reset_log(eighth, {2}, {{{len = 1.5}}}, 130),
    {"on1", "R25", "on25", "off73", "on73", "on121"})
  -- README.md:805: a second reset (pulse 73) while the note still sounds does not
  -- move its release either: two and a half steps -> pulse 121.
  luaunit.assert_equals(reset_log(eighth, {2, 4}, {{{len = 2.5}}}, 130),
    {"on1", "R25", "on25", "R73", "on73", "off121", "on121"})
end

function test_w4l_reset_keeps_a_swung_note_on_its_original_steps()
  -- README.md:805 as above, on a swung 1/16 channel (swing 10: steps of 26.4
  -- and 21.6 pulses, README.md:685 range -50..50). A 3.5-step note from
  -- pulse 1 spans 26.4 + 21.6 + 26.4 + 10.8 = 85.2 pulses of its original
  -- swung steps, whatever the restarted channel does after the reset at 25.
  -- characterisation: the pulse-rounded release is pulse 87.
  local log = reset_log({division = 1 / 16, swing = 10}, {2}, {{{len = 3.5}}}, 100)
  luaunit.assert_equals(log, {"on1", "R25", "on25", "on49", "on71", "off87", "on97"})
end

function test_w4l_note_started_on_the_reset_pulse_uses_the_restarted_steps()
  -- characterisation: a strum delayed one step from the swung first onset
  -- (1/8, swing 50: first step 72 pulses) falls due on pulse 73, the pulse of
  -- the reset. It plays after the restarted onset, and its half-step note is
  -- timed on the restarted channel (step 1 again, 72 pulses): release 36
  -- pulses later, not half of the pre-reset 24-pulse second step.
  local log = reset_log({division = over(2), swing = 50}, {4}, {{{strum = 1, len = 0.5}}}, 150)
  luaunit.assert_equals(log, {"on1", "R73", "on73", "strum73", "soff109", "on145"})
end

---------------------------------------------------------------------------
-- Onset projection (param slide durations)
---------------------------------------------------------------------------

function test_w4l_onset_projection_matches_actual_onsets_on_fast_swung_and_wrapping_clocks()
  -- README.md:964/971: a param slide transitions to the next lock;
  -- m_clock sizes it with project_onset_pulses, so a projection taken at an
  -- onset must equal the pulses until that later onset actually fires.
  -- Covers the per-step path: x16 (1.5-pulse steps, some below 2 pulses once
  -- swung), fractional x5.3 and /2.6 clocks, swing both ways (README.md:685),
  -- and global lengths 3 and 4 (README.md:917) so projections cross the
  -- pattern wrap where swing pairing restarts.
  local checked = 0
  for _, division in ipairs({times(16), times(5.3), over(2.6)}) do
    for _, swing in ipairs({-50, 0, 25}) do
      for _, pattern_length in ipairs({3, 4, 64}) do
        local lattice = new_lattice({pattern_length = pattern_length})
        local log, projections = {}, {}
        local sprocket
        sprocket = lattice:new_sprocket({division = division, swing = swing, action = function(t)
          log[#log + 1] = t
          if #log <= 3 then
            projections[#log] = {}
            for distance = 1, 8 do projections[#log][distance] = sprocket:project_onset_pulses(distance) end
          end
        end})
        local guard = 0
        while #log < 11 and guard < 10000 do lattice:pulse(); guard = guard + 1 end
        for from = 1, 3 do
          for distance = 1, 8 do
            luaunit.assert_equals(projections[from][distance], log[from + distance] - log[from],
              string.format("division %s swing %d length %d onset %d distance %d",
                tostring(division), swing, pattern_length, from, distance))
            checked = checked + 1
          end
        end
      end
    end
  end
  luaunit.assert_equals(checked, 27 * 3 * 8)
end

---------------------------------------------------------------------------
-- Occurrence projection (param slides retimed by a settings change or reset)
---------------------------------------------------------------------------

-- Projects occurrences done+1 .. done+span of an order-2 channel from a 1/16
-- observer sprocket of the given order, at the observer's `at`-th onset
-- (optionally resetting first, as m_clock.realign_sprockets does). Returns the
-- projections and the pulses until each occurrence actually fired.
local function occurrence_case(channel_args, observer_order, at, span, reset)
  local lattice = new_lattice()
  local log, projected, actual = {}, {}, {}
  local base, first
  local channel
  local count = 0
  lattice:new_sprocket({order = observer_order, division = 1 / 16, action = function()
    count = count + 1
    if count == at then
      if reset then lattice:realign_eligable_sprockets() end
      base = lattice.transport
      first = (channel.onset_count or 0) + 1
      for k = first, first + span - 1 do projected[#projected + 1] = channel:project_onset_occurrence(k) end
    end
  end})
  local args = copy(channel_args)
  args.order = 2
  args.action = function(t) log[#log + 1] = t end
  channel = lattice:new_sprocket(args)
  local guard = 0
  while (base == nil or #log < first + span - 1) and guard < 100000 do lattice:pulse(); guard = guard + 1 end
  for k = first, first + span - 1 do actual[#actual + 1] = log[k] - base end
  return projected, actual
end

function test_w4l_occurrence_projection_matches_actual_onsets_up_to_64_ahead()
  -- README.md:964/971 as above. m_clock retimes a slide from an
  -- order-1 callback (a settings change at a song-pattern boundary) and after
  -- a reset; both reach up to 64 occurrences ahead (a full 64-step channel).
  local cases = {
    {"swing 25", {division = 1 / 16, swing = 25}, false},
    {"x5.3 smooth shuffle", {division = times(5.3), swing_or_shuffle = 2, shuffle_feel = 2,
      shuffle_basis = 1, shuffle_amount = 100}, false},
    {"swing 25 after reset", {division = over(2), swing = 25, realign = true}, true},
  }
  for _, case in ipairs(cases) do
    local projected, actual = occurrence_case(case[2], 1, 3, 64, case[3])
    luaunit.assert_equals(#projected, 64, case[1])
    luaunit.assert_equals(projected, actual, case[1])
  end
end

function test_w4l_occurrence_projection_after_a_mid_step_reset_on_a_fractional_clock()
  -- characterisation (suspected defect: m_lattice.lua:704 leaves the restarted
  -- step's current_ppqn at the unrounded division * ppqn * 4 while
  -- shuffle_updated stays set, so project_onset_occurrence (line 642) projects
  -- a fractional pulse count): a /2.6 channel steps every 62.4 pulses. After a
  -- reset mid-step on pulse 25, the next onset actually fires 62 pulses later
  -- but is projected 62.4 pulses later, and every later occurrence keeps the
  -- extra 0.4 pulse.
  local projected, actual = occurrence_case({division = over(2.6), realign = true}, 1, 2, 4, true)
  luaunit.assert_equals(actual, {0, 62, 125, 187})
  luaunit.assert_equals(#projected, 4)
  luaunit.assert_equals(projected[1], 0)
  for k = 2, 4 do luaunit.assert_almost_equals(projected[k], actual[k] + 0.4, 1e-9, "occurrence " .. k) end
end

function test_w4l_occurrence_projection_from_later_callbacks_and_the_channel_action()
  -- README.md:964/971 as above: wherever the projection is called in a pulse
  -- it must match the onsets that actually fire; a later-order callback sees
  -- this channel already processed. characterisation: the pulse counts; at
  -- 1/16 swing 25 (steps of 30 and 18 pulses) onsets fire on 1, 31, 49, 79 ...
  -- so from the order-3 callback on pulse 49 the next onsets are 30, 48, 78 ...
  -- pulses away.
  local projected, actual = occurrence_case({division = 1 / 16, swing = 25}, 3, 3, 8, false)
  luaunit.assert_equals(projected, actual)
  luaunit.assert_equals(projected, {30, 48, 78, 96, 126, 144, 174, 192})
  -- README.md:964/971 as above, for a reset from a later-order callback after
  -- this channel's onset on that pulse. characterisation: the channel restarts
  -- on the next pulse (1 pulse away); the restarted first step runs straight
  -- (24 pulses, the known m_lattice.lua:703-704 behaviour), then swing resumes
  -- (18, 30).
  projected, actual = occurrence_case({division = 1 / 16, swing = 25, realign = true}, 3, 3, 4, true)
  luaunit.assert_equals(projected, actual)
  luaunit.assert_equals(projected, {1, 25, 43, 73})
  -- characterisation: inside the channel's own action at onset 2 (pulse 31)
  -- the onset in progress is already counted; the next ones are 18, 48, 66
  -- and 96 pulses away, where they actually fire.
  local lattice = new_lattice()
  local log, own = {}, {}
  local channel
  channel = lattice:new_sprocket({division = 1 / 16, swing = 25, action = function(t)
    log[#log + 1] = t
    if #log == 2 then
      for k = 3, 6 do own[#own + 1] = channel:project_onset_occurrence(k) end
    end
  end})
  run(lattice, 130)
  luaunit.assert_equals(log, {1, 31, 49, 79, 97, 127})
  luaunit.assert_equals(own, {18, 48, 66, 96})
end

function test_w4l_occurrence_projection_rejects_unsupported_requests()
  -- characterisation: the lattice refuses occurrences outside 1..64 ahead or
  -- not whole, and clocks it cannot project (delayed, variable, pending delay).
  local lattice = new_lattice()
  local sprocket = lattice:new_sprocket({division = 1 / 16})
  local function outcome(target, occurrence)
    local ok, result = pcall(target.project_onset_occurrence, target, occurrence)
    if ok then return result end
    return tostring(result):match("Invalid future onset occurrence") or
      tostring(result):match("Unsupported variable or delayed projection") or tostring(result)
  end
  local invalid = "Invalid future onset occurrence"
  luaunit.assert_equals({outcome(sprocket, 0), outcome(sprocket, -1), outcome(sprocket, 65), outcome(sprocket, 1.5)},
    {invalid, invalid, invalid, invalid})
  -- characterisation: 64 ahead is accepted: 63 whole 24-pulse steps after the
  -- next pulse.
  luaunit.assert_equals({outcome(sprocket, 1), outcome(sprocket, 64)}, {0, 63 * 24})
  local unsupported = "Unsupported variable or delayed projection"
  local delayed = lattice:new_sprocket({division = 1 / 16, delay = 0.5})
  local variable = lattice:new_sprocket({division = 1 / 16, division_for_cycle = function() return 1 / 16 end})
  local pending = lattice:new_sprocket({division = 1 / 16})
  pending:set_delay(0.25)
  luaunit.assert_equals({outcome(delayed, 1), outcome(variable, 1), outcome(pending, 1)},
    {unsupported, unsupported, unsupported})
end

---------------------------------------------------------------------------
-- set_delay
---------------------------------------------------------------------------

local function delay_changes(steps)
  local lattice = new_lattice()
  local log = {}
  local sprocket = lattice:new_sprocket({division = 1 / 16, action = function(t) log[#log + 1] = t end})
  for _, step in ipairs(steps) do
    run(lattice, step[1])
    if step[2] ~= nil then sprocket:set_delay(step[2]) end
  end
  return log
end

function test_w4l_set_delay_clamps_and_applies_at_the_next_step_boundary()
  -- The manual does not describe set_delay (no m_clock caller); m_lattice.lua:462
  -- documents the delay as a fraction (0-1) of the step.
  -- The 1/16 sprocket has onsets 1, 25, 49 ...; each change is made on pulse 30
  -- and applies from the step boundary after pulse 48.
  -- characterisation: half a step -> the next onset moves 12 pulses later.
  luaunit.assert_equals(delay_changes({{30, 0.5}, {100}}), {1, 25, 61, 85, 109})
  -- characterisation: a negative delay clamps to none and leaves the grid
  -- unchanged.
  luaunit.assert_equals(delay_changes({{30, -1}, {100}}), {1, 25, 49, 73, 97, 121})
  -- characterisation (suspected defect: m_lattice.lua:583 applies the change
  -- with the opposite sign, phase - cp * (delay - delay_new)): a quarter step
  -- moves onsets 18 pulses (three quarters) later, onto 19 + 24k, where a
  -- sprocket created with delay 0.25 fires on 7 + 24k.
  luaunit.assert_equals(delay_changes({{30, 0.25}, {100}}), {1, 25, 67, 91, 115})
  local created = new_lattice()
  local created_log = {}
  created:new_sprocket({division = 1 / 16, delay = 0.25, action = function(t) created_log[#created_log + 1] = t end})
  run(created, 100)
  luaunit.assert_equals(created_log, {7, 31, 55, 79})
  -- characterisation (same suspected defect): 2 clamps to a whole step, which
  -- lands one pulse after the grid (50, 74); a later change to half a step
  -- starts from that clamped whole step.
  luaunit.assert_equals(delay_changes({{30, 2}, {60, 0.5}, {100}}), {1, 25, 50, 74, 110, 134, 158, 182})
end
