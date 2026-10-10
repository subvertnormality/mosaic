-- Transport-wide counters and cycle logs (docs/musical-merge-extensions-plan.md
-- §1.2.1 and §1.2.2).
--
-- For every channel 1..16, whether or not any merge feature is enabled, the
-- transport owns the channel's elapsed-cycle counter k, a captured timing, a
-- sticky resync flag and a log of the segments that governed its recent
-- cycles. A wrap costs one integer increment, a few scalar comparisons and one
-- bounded ring write; nothing here changes any musical output.
--
-- include() is dofile in the test harness, so the state lives in a registry on
-- _G that every execution of this module shares.
local merge_state = include("mosaic/lib/musical_merge/state")

local timeline = {}

-- Segments covering the last RETENTION cycles of a channel are retained.
local RETENTION = 64
timeline.RETENTION = RETENTION

local registry = rawget(_G, "__mosaic_merge_timeline")
if not registry then
  registry = {running = false, serial = 0, song = nil, channels = {}}
  rawset(_G, "__mosaic_merge_timeline", registry)
end

local function new_channel()
  return {
    k = 0, resync = false, onsets = nil,
    mod_type = nil, mod_value = nil, first = nil, last = nil, global_length = nil, count = nil,
    log_index = {}, log_config = {}, log_cycle = {}, log_phrase = {}
  }
end

local function bounds(channel, global_length)
  local first = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
  local last = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])
  if last - first + 1 > global_length then last = first + global_length - 1 end
  return first, last
end
timeline.bounds = bounds

local function capture(record, channel, global_length)
  local mods = channel.clock_mods or {}
  record.mod_type, record.mod_value = mods.type, mods.value
  record.global_length = global_length
  record.first, record.last = bounds(channel, global_length)
  record.count = record.last - record.first + 1
end

-- Whether channel `channel` (song data) still has the timing captured at the
-- origin: clock mod, start/end and the global pattern length.
local function same_timing(record, channel, global_length)
  local mods = channel.clock_mods or {}
  if mods.type ~= record.mod_type or mods.value ~= record.mod_value or
    global_length ~= record.global_length then return false end
  local first, last = bounds(channel, global_length)
  return first == record.first and last == record.last
end

-- Copy (never derive) what merge_state holds for the channel into the ring
-- slot of cycle `k`. Channels without merge state record Off.
local function append(record, song, number, k)
  local state = merge_state.peek(song, number)
  local slot = k % RETENTION + 1
  record.log_index[slot] = k
  if state then
    record.log_config[slot] = state.active or false
    record.log_cycle[slot], record.log_phrase[slot] = state.cycle, state.phrase
  else
    local channel = song.channels[number]
    record.log_config[slot] = channel and channel.musical_merge or false
    record.log_cycle[slot], record.log_phrase[slot] = 1, 0
  end
end

local function sprocket_onsets(number)
  local clock = m_clock and m_clock["channel_" .. number .. "_clock"]
  return type(clock) == "table" and (clock.onset_count or 0) or 0
end

local function begin_origin(song, k)
  registry.serial = registry.serial + 1
  registry.song = song
  registry.running = true
  -- Master onsets since the origin are counted by the existing accumulator.
  registry.accumulator_base = program.get().global_step_accumulator or 0
  local global_length = song.global_pattern_length or 64
  for number = 1, 16 do
    local record = new_channel()
    record.k = k
    capture(record, song.channels[number], global_length)
    registry.channels[number] = record
  end
end

-- Start: origin serial += 1, every k = 0, timing captured, resync cleared, and
-- each log restarts with the entry for cycle 0. The first onset after Start is
-- not a wrap, so the onset count it starts from is recorded here.
function timeline.start(song)
  begin_origin(song, 0)
  for number = 1, 16 do
    local record = registry.channels[number]
    append(record, song, number, 0)
    -- The first onset (count + 1) starts cycle 0.
    record.onsets = sprocket_onsets(number) + 1
  end
end

-- Realign: a new common origin, every k = -1 (the forced wrap at the next
-- onset makes it 0 without counting an elapsed cycle), timing recaptured,
-- resync cleared, logs restarted empty. The forced wrap logs cycle 0.
function timeline.realign(song)
  begin_origin(song, -1)
end

-- Stop, project load, New: everything is discarded.
function timeline.stop()
  registry.running = false
  registry.song = nil
  registry.channels = {}
end

function timeline.running()
  return registry.running
end

function timeline.serial()
  return registry.serial
end

function timeline.song()
  return registry.song
end

-- Master onsets since the origin (0 before the first one after Start).
function timeline.elapsed_master()
  if not registry.running then return 0 end
  return (program.get().global_step_accumulator or 0) - (registry.accumulator_base or 0)
end

-- Channel wrap. Runs for every channel 1..16 in the clock's wrap branch, after
-- merge_state.on_cycle_boundary. `onsets` is the channel sprocket's onset count
-- at this onset. Returns true when this wrap newly set resync.
function timeline.on_wrap(song, number, channel, global_length, onsets)
  local record = registry.running and registry.channels[number]
  if not record then return false end
  local k = record.k + 1
  record.k = k
  local was = record.resync
  if not was then
    -- A cycle that did not last exactly its captured playable count, a timing
    -- that differs from the captured one or a replaced song slot table cannot
    -- be described by the cycle-indexed schedule.
    if song ~= registry.song or not same_timing(record, channel, global_length) or
      (k > 0 and record.onsets ~= nil and onsets - record.onsets ~= record.count) then
      record.resync = true
    end
  end
  record.onsets = onsets
  append(record, song, number, k)
  return record.resync and not was
end

-- Sticky until the next origin. Returns true when newly set.
function timeline.set_resync(number)
  local record = registry.running and registry.channels[number]
  if not record or record.resync then return false end
  record.resync = true
  return true
end

function timeline.resync_all()
  local changed = {}
  for number = 1, 16 do if timeline.set_resync(number) then changed[number] = true end end
  return changed
end

-- nil while stopped.
function timeline.channel(number)
  return registry.running and registry.channels[number] or nil
end

function timeline.k(number)
  local record = timeline.channel(number)
  return record and record.k or nil
end

function timeline.resync(number)
  local record = timeline.channel(number)
  return record ~= nil and record.resync
end

-- Whether the channel's live timing still equals the timing captured at the
-- origin; a difference sets the sticky resync.
function timeline.check_timing(song, number)
  local record = timeline.channel(number)
  if not record then return true end
  if record.resync then return false end
  if song ~= registry.song or
    not same_timing(record, song.channels[number], song.global_pattern_length or 64) then
    record.resync = true
    return false
  end
  return true
end

-- The logged segment of cycle i: config (false for Off), cycle, phrase; nil
-- when the cycle has not been logged or is older than the retention.
function timeline.segment(number, i)
  local record = timeline.channel(number)
  if not record or i < 0 then return nil end
  local slot = i % RETENTION + 1
  if record.log_index[slot] ~= i then return nil end
  return record.log_config[slot], record.log_cycle[slot], record.log_phrase[slot]
end

return timeline
