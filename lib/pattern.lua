local pattern = {}
local source_revisions = include("mosaic/lib/source_pattern_revision").new()

local quantiser = include("mosaic/lib/quantiser")
local foundation = include("mosaic/lib/musical_merge/foundation")
local merge_state = include("mosaic/lib/musical_merge/state")
local merge_config = include("mosaic/lib/musical_merge/config")
local fragments = include("mosaic/lib/musical_merge/fragments")
local merge_structure = include("mosaic/lib/musical_merge/structure")
local interlock = include("mosaic/lib/musical_merge/interlock")
local merge_dependency = include("mosaic/lib/musical_merge/dependency")

local program = program

local notes = program.initialise_64_table({})
local lengths = program.initialise_64_table({})
local velocities = program.initialise_64_table({})

-- Helper variables
local update_timer_id = nil
local throttle_time = 0.001
local currently_processing = false

local unpack = table.unpack
local insert = table.insert
local sort = table.sort
local pairs = pairs

-- Pre-allocate tables
local default_trig_values = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}
local default_lengths = {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}
local default_note_values = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}
local default_note_mask_values = {-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1}
local default_velocity_values = {100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100}

local function effective_lengths(source)
  local result = {unpack(source.lengths)}
  local next_trig
  for s = 1, 64 do
    if source.trig_values[s] == 1 then
      next_trig = s + 64
      break
    end
  end
  if not next_trig then return result end

  -- Walking backwards gives every trig its nearest following trig, including
  -- wraparound, without scanning each sustained note separately.
  for s = 64, 1, -1 do
    if source.trig_values[s] == 1 then
      local length = result[s]
      if length > 1 then
        local distance = next_trig - s
        -- The original search excludes a full-cycle self-interruption and
        -- cuts only strictly inside the requested (possibly fractional) gate.
        if distance <= 63 and distance < length then result[s] = distance end
      end
      next_trig = s
    end
  end
  return result
end

local function sync_pattern_values(merged_pattern, pattern, s, source_lengths)
  merged_pattern.lengths[s] = source_lengths[s]
  merged_pattern.velocity_values[s] = pattern.velocity_values[s]
  merged_pattern.note_values[s] = pattern.note_values[s]
  merged_pattern.note_mask_values[s] = pattern.note_mask_values[s]
  return merged_pattern
end

local function extract_pattern_number(merge_mode)
  local prefix = "pattern_number_"
  if merge_mode:sub(1, #prefix) == prefix then
    return tonumber(merge_mode:sub(#prefix + 1))
  end
  return nil
end

-- The legacy (pre-Foundation, pre-mask) merge of a channel's sources.
-- `trace`, when given, receives the visit order of the sources.
local function legacy_merge(channel, trig_merge_mode, note_merge_mode, velocity_merge_mode, length_merge_mode, selected_song_pattern, effective_lengths_cache, trace)
  local merged_pattern = {
    trig_values = {unpack(default_trig_values)},
    lengths = {unpack(default_lengths)},
    note_values = {unpack(default_note_values)},
    note_mask_values = {unpack(default_note_mask_values)},
    velocity_values = {unpack(default_velocity_values)},
    merged_notes = {}
  }
  local skip_bits = {unpack(default_trig_values)}
  local only_bits = {unpack(default_trig_values)}

  local pattern_channel = selected_song_pattern.channels[channel]
  local patterns = selected_song_pattern.patterns
  local note_priority = note_merge_mode and extract_pattern_number(note_merge_mode)
  local velocity_priority = velocity_merge_mode and extract_pattern_number(velocity_merge_mode)
  local length_priority = length_merge_mode and extract_pattern_number(length_merge_mode)
  local priority_lengths
  local merge_step_trig_masks = program.get_step_trig_masks(channel)

  for i = 1, 64 do
    notes[i] = {}
    lengths[i] = {}
    velocities[i] = {}
  end

  local function do_moded_merge(pattern_number, is_pattern_trig_one, s, mode, priority, values, merged_values, pushed_values)
    if priority == pattern_number then
      merged_values[s] = values[s]
    elseif mode == "up" or mode == "down" or mode == "average" then
      if is_pattern_trig_one then
        insert(pushed_values[s], values[s])
      end
    end
  end

  -- Priority sources participate in merging without becoming channel assignments.
  local patterns_to_process = {}
  for number, enabled in pairs(pattern_channel.selected_patterns) do
    patterns_to_process[number] = enabled
  end

  local function process_merge_mode(merge_mode)
    if merge_mode then
      local pattern_number = extract_pattern_number(merge_mode)
      if pattern_number and patterns_to_process[pattern_number] == nil then
        patterns_to_process[pattern_number] = false
      end
    end
  end

  process_merge_mode(note_merge_mode)
  process_merge_mode(velocity_merge_mode)
  process_merge_mode(length_merge_mode)

  for pattern_number, pattern_enabled in pairs(patterns_to_process) do
    local pattern = patterns[pattern_number]
    if trace then trace[#trace + 1] = pattern_number; trace[#trace + 1] = pattern_enabled; trace[#trace + 1] = pattern end
    local source_lengths = effective_lengths_cache and effective_lengths_cache[pattern_number]
    if not source_lengths then
      source_lengths = effective_lengths(pattern)
      if effective_lengths_cache then effective_lengths_cache[pattern_number] = source_lengths end
    end
    if pattern_number == length_priority then priority_lengths = source_lengths end

    for s = 1, 64 do
      local is_pattern_trig_one = pattern.trig_values[s] == 1
      if pattern_enabled then
        if trig_merge_mode == "skip" then
          if is_pattern_trig_one and merged_pattern.trig_values[s] < 1 and skip_bits[s] < 1 then
            merged_pattern = sync_pattern_values(merged_pattern, pattern, s, source_lengths)
            merged_pattern.trig_values[s] = 1
          elseif is_pattern_trig_one and merged_pattern.trig_values[s] == 1 then
            merged_pattern.trig_values[s] = 0
            skip_bits[s] = 1
          end
        elseif trig_merge_mode == "only" then
          if is_pattern_trig_one and merged_pattern.trig_values[s] < 1 and only_bits[s] == 0 then
            only_bits[s] = 1
            merged_pattern.trig_values[s] = 0
          elseif is_pattern_trig_one and only_bits[s] == 1 then
            merged_pattern.trig_values[s] = 1
          end
        elseif trig_merge_mode == "all" and is_pattern_trig_one then
          merged_pattern.trig_values[s] = 1
        end
      end

      local is_positive_step_trig_mask = merge_step_trig_masks and merge_step_trig_masks[s] == 1
      local should_process_note_merge_mode = is_pattern_trig_one or is_positive_step_trig_mask or note_priority
      local should_process_velocity_merge_mode = is_pattern_trig_one or is_positive_step_trig_mask or velocity_priority
      local should_process_length_merge_mode = is_pattern_trig_one or is_positive_step_trig_mask or length_priority

      if should_process_note_merge_mode then
        do_moded_merge(pattern_number, pattern_enabled, s, note_merge_mode, note_priority, pattern.note_values, merged_pattern.note_values, notes)
      end
      if should_process_velocity_merge_mode then
        do_moded_merge(pattern_number, pattern_enabled, s, velocity_merge_mode, velocity_priority, pattern.velocity_values, merged_pattern.velocity_values, velocities)
      end
      if should_process_length_merge_mode then
        do_moded_merge(pattern_number, pattern_enabled, s, length_merge_mode, length_priority, source_lengths, merged_pattern.lengths, lengths)
      end
    end
  end

  local function do_mode_calculation(mode, s, values, merged_values)
    if mode == "up" or mode == "down" or mode == "average" then
      if not values[s] or #values[s] == 0 then
        merged_values[s] = 0
      elseif #values[s] == 1 then
        merged_values[s] = values[s][1]
      else
        sort(values[s])
        local min_value = values[s][1]
        local max_value = values[s][#values[s]]
        local average = fn.average_table_values(values[s])
        if mode == "up" then
          merged_values[s] = average + (max_value - min_value)
        elseif mode == "down" then
          merged_values[s] = min_value - (average - min_value)
        else
          merged_values[s] = average
        end
        merged_pattern.merged_notes[s] = true
      end
    end
  end

  -- Trig collection may copy another pattern's values. Apply explicit priorities
  -- after that collection so table iteration order cannot overwrite the choice.

  for s = 1, 64 do
    do_mode_calculation(note_merge_mode, s, notes, merged_pattern.note_values)
    do_mode_calculation(velocity_merge_mode, s, velocities, merged_pattern.velocity_values)
    do_mode_calculation(length_merge_mode, s, lengths, merged_pattern.lengths)

    if note_priority then merged_pattern.note_values[s] = patterns[note_priority].note_values[s] end
    if velocity_priority then merged_pattern.velocity_values[s] = patterns[velocity_priority].velocity_values[s] end
    if length_priority then merged_pattern.lengths[s] = priority_lengths[s] end
  end
  return merged_pattern, merge_step_trig_masks
end

-- Memo of legacy_merge for every working-pattern build of this module (the
-- clock's wrap rebuild, edits, follower rebuilds, sweeps; seeded by each)
-- (docs/musical-merge-extensions-plan.md §1.3 performance). Source arrays
-- and step masks are written in place without any rebuild request
-- (program.update_working_pattern_for_step, the memory event handlers), so
-- an entry is never trusted because nothing asked for a rebuild: it is
-- validated on every use against a copy of each input value legacy_merge,
-- and foundation.plan after it, can read:
--   * the merge modes, and the source visit order as legacy_merge builds it
--     (number, enabled value and source table identity, in pairs order);
--   * each source's trig class at every step: == 1 (what legacy_merge
--     reads), == true (what foundation.plan also accepts), or neither;
--   * the positive step trig masks (== 1, the only test legacy_merge makes);
--   * note, velocity, length and note-mask values at every step they can be
--     read: the source's trig steps (1 or true) and positive-mask steps, or
--     all 64 when a pattern-priority mode reads whole arrays; compared by
--     value and by number subtype (math.type).
-- A hit returns a fresh copy of the pristine merged pattern stored at the
-- miss; nothing the caller does to the result reaches the entry.
--
-- Within one lattice pulse (the `pulse` token m_clock's wrap branch passes
-- down; a fresh table per Lattice:pulse_all), a source snapshot that equals
-- another entry's is shared (interned), and a snapshot validated once in the
-- pulse is not validated again. Sound because a pulse runs to completion in
-- one coroutine without yielding, and no code that runs inside a pulse
-- writes source arrays: only input handlers and editors do (grid pages,
-- Rhythm Doctor, memory undo/redo, project load), and they never run
-- inside a pulse. Step masks are per channel and always validated.
local legacy_memo = setmetatable({}, {__mode = "k"})
local math_type = math.type
local VALUE_FIELDS = {"note_values", "velocity_values", "lengths", "note_mask_values"}
local MERGED_FIELDS = {"trig_values", "lengths", "note_values", "note_mask_values", "velocity_values"}

-- Hit and miss counts of the wrap memo, for tests and profiling.
pattern.wrap_memo_stats = {legacy_hits = 0, legacy_misses = 0, plan_hits = 0, plan_misses = 0,
  shared_validations = 0, shared_admissions = 0, share_checks = 0}

-- Tests only: when true, every in-pulse shortcut (a skipped source
-- validation, a shared admission) is also recomputed and compared, raising
-- on any difference.
pattern.wrap_share_check = false
-- Tests only: false turns the in-pulse sharing off (the differential baseline).
pattern.wrap_share = true

-- The trig class of a source value: 1 (== 1), 2 (== true) or 0.
local function trig_class(value)
  if value == 1 then return 1 end
  if value == true then return 2 end
  return 0
end

local function positive_masks(masks)
  local result = {}
  for s = 1, 64 do result[s] = masks ~= nil and masks[s] == 1 end
  return result
end

local function snapshot_values(source, positive, every)
  local trigs = source.trig_values
  if type(trigs) ~= "table" then return nil end
  local classes, steps = {}, {}
  for s = 1, 64 do
    local class = trig_class(trigs[s])
    classes[s] = class
    if every or class ~= 0 or positive[s] then steps[#steps + 1] = s end
  end
  local saved = {source = source, classes = classes, steps = steps}
  for _, field in ipairs(VALUE_FIELDS) do
    local values = source[field]
    if type(values) ~= "table" then return nil end
    local copy = {}
    for index = 1, #steps do copy[index] = values[steps[index]] end
    saved[field] = copy
  end
  return saved
end

local function same_snapshot(a, b)
  local steps, other_steps = a.steps, b.steps
  if #steps ~= #other_steps then return false end
  for s = 1, 64 do if a.classes[s] ~= b.classes[s] then return false end end
  for i = 1, #steps do if steps[i] ~= other_steps[i] then return false end end
  for _, field in ipairs(VALUE_FIELDS) do
    local x, y = a[field], b[field]
    for i = 1, #steps do
      local u, v = x[i], y[i]
      if u ~= v or math_type(u) ~= math_type(v) then return false end
    end
  end
  return true
end

-- Snapshots by source table; equal snapshots are one object, so the
-- followers of one leader that merge the same sources validate it once per
-- pulse.
local interned = setmetatable({}, {__mode = "k"})

local function snapshot_source(source, positive, every)
  local saved = snapshot_values(source, positive, every)
  if not saved then return nil end
  local list = interned[source]
  if not list then list = setmetatable({}, {__mode = "v"}); interned[source] = list end
  for _, other in pairs(list) do
    if same_snapshot(other, saved) then return other end
  end
  list[#list + 1] = saved
  return saved
end

-- Whether a source still holds a snapshot's values.
local function source_matches(saved)
  local trigs, classes = saved.source.trig_values, saved.classes
  if type(trigs) ~= "table" then return false end
  for s = 1, 64 do
    local value = trigs[s]
    local class = value == 1 and 1 or value == true and 2 or 0
    if class ~= classes[s] then return false end
  end
  -- Classes are equal, so the read steps are the saved ones.
  local steps = saved.steps
  for _, field in ipairs(VALUE_FIELDS) do
    local values, copy = saved.source[field], saved[field]
    if type(values) ~= "table" then return false end
    for i = 1, #steps do
      local u, v = values[steps[i]], copy[i]
      if u ~= v or math_type(u) ~= math_type(v) then return false end
    end
  end
  return true
end

local function memo_valid(entry, channel, modes, pattern_channel, patterns, pulse)
  for index = 1, 4 do if entry.modes[index] ~= modes[index] then return false end end
  -- The visit order of the sources, built exactly as legacy_merge builds it.
  local order = {}
  for number, enabled in pairs(pattern_channel.selected_patterns) do order[number] = enabled end
  for index = 2, 4 do
    local mode = modes[index]
    local number = mode and extract_pattern_number(mode)
    if number and order[number] == nil then order[number] = false end
  end
  local trace, position = entry.trace, 0
  for number, enabled in pairs(order) do
    if trace[position + 1] ~= number or trace[position + 2] ~= enabled or trace[position + 3] ~= patterns[number] then
      return false
    end
    position = position + 3
  end
  if position ~= #trace then return false end
  local masks = program.get_step_trig_masks(channel)
  local positive = entry.positive
  for s = 1, 64 do
    if (masks ~= nil and masks[s] == 1) ~= positive[s] then return false end
  end
  local sources = entry.sources
  local stats = pattern.wrap_memo_stats
  for index = 1, #sources do
    local saved = sources[index]
    if pulse and saved.valid_pulse == pulse then
      stats.shared_validations = stats.shared_validations + 1
      if pattern.wrap_share_check then
        stats.share_checks = stats.share_checks + 1
        if not source_matches(saved) then error("wrap memo: a source changed inside a pulse", 2) end
      end
    else
      if not source_matches(saved) then return false end
      if pulse then saved.valid_pulse = pulse end
    end
  end
  return true
end

-- Steps 1..64 are copied explicitly: a nil value (a hole) must not shorten
-- the copy as unpack's length would.
local function copy_merged(merged)
  local result = {}
  for _, field in ipairs(MERGED_FIELDS) do
    local values, copy = merged[field], {}
    for s = 1, 64 do copy[s] = values[s] end
    result[field] = copy
  end
  local notes_merged = {}
  for key, value in pairs(merged.merged_notes) do notes_merged[key] = value end
  result.merged_notes = notes_merged
  return result
end

-- legacy_merge, served from the memo when every input equals the entry's.
-- Returns the merged pattern and whether it came from the memo.
local function memo_legacy_merge(channel, modes, selected_song_pattern, pulse)
  local pattern_channel = selected_song_pattern.channels[channel]
  local patterns = selected_song_pattern.patterns
  local by_channel = legacy_memo[selected_song_pattern]
  local entry = by_channel and by_channel[channel]
  local stats = pattern.wrap_memo_stats
  if entry and entry.channel_table == pattern_channel and entry.patterns == patterns and
    memo_valid(entry, channel, modes, pattern_channel, patterns, pulse) then
    stats.legacy_hits = stats.legacy_hits + 1
    return copy_merged(entry.merged), true
  end
  stats.legacy_misses = stats.legacy_misses + 1
  local trace = {}
  local merged, masks = legacy_merge(channel, modes[1], modes[2], modes[3], modes[4], selected_song_pattern, nil, trace)
  local positive = positive_masks(masks)
  -- A priority mode reads its source's whole arrays.
  local every = false
  for index = 2, 4 do if modes[index] and extract_pattern_number(modes[index]) then every = true end end
  local sources = {}
  for index = 3, #trace, 3 do
    local saved = snapshot_source(trace[index], positive, every)
    if not saved then sources = nil; break end
    sources[#sources + 1] = saved
  end
  if not by_channel then by_channel = {}; legacy_memo[selected_song_pattern] = by_channel end
  by_channel[channel] = sources and {
    modes = {modes[1], modes[2], modes[3], modes[4]}, trace = trace, sources = sources,
    positive = positive, channel_table = pattern_channel, patterns = patterns,
    merged = copy_merged(merged)
  } or nil
  return merged, false
end

-- Memo of foundation.plan for the same wrap rebuild. Its inputs besides the
-- key below and the filters are the sources' trigs and velocities and the
-- merged velocities, which a legacy-memo hit has just validated, so a plan
-- entry is used only on such a hit (it belongs to that legacy entry, and a
-- legacy miss replaces the entry and drops it) and only when all 12 key
-- fields are equal by value and number subtype and the Interlock filters are
-- the same ordered list with exactly the same blocked sets.
local function legacy_entry(song_pattern, channel)
  local by_channel = legacy_memo[song_pattern]
  return by_channel and by_channel[channel]
end

local function same_plan_key(left, right)
  for index = 1, 12 do
    local u, v = left[index], right[index]
    if u ~= v or math_type(u) ~= math_type(v) then return false end
  end
  return true
end

-- Filters as foundation.plan reads them: nil, or an ordered list of
-- {reason, blocked set}.
local function copy_filters(filters)
  if not filters then return nil end
  local result = {}
  for index, filter in ipairs(filters) do
    local blocked = {}
    for step, value in pairs(filter.blocked) do blocked[step] = value end
    result[index] = {reason = filter.reason, blocked = blocked}
  end
  return result
end

local function same_filters(saved, filters)
  if saved == nil or filters == nil then return saved == nil and filters == nil end
  if #saved ~= #filters then return false end
  for index, filter in ipairs(filters) do
    local other = saved[index]
    if other.reason ~= filter.reason then return false end
    for step, value in pairs(filter.blocked) do
      if other.blocked[step] ~= value then return false end
    end
    for step in pairs(other.blocked) do
      if filter.blocked[step] == nil then return false end
    end
  end
  return true
end

-- The plan a hit returns: a fresh top-level table (the build adds its own
-- interlock, cycle, phrase, config, anchor_notes and markers there) whose
-- sub-tables (trigs, roles, reasons, velocities, sources, reason_lists and
-- their per-step lists) are shared with the stored plan and with earlier
-- builds' plans. Rule: plan sub-tables are immutable once foundation.plan
-- has built them. Nothing in Mosaic writes them (step.handle,
-- harmony pitch resolution, the Merge Shape Result/Reason screens,
-- merge_structure.markers and merge_display only read them);
-- merge_wrap_pulse_share_tests.lua runs those paths with the sub-tables made
-- read-only. A writer added later must copy first.
local function copy_plan(plan)
  local result = {}
  for key, value in pairs(plan) do result[key] = value end
  return result
end

-- The Interlock admission shared by the wrap rebuilds of one lattice pulse
-- (the `pulse` token). Every admission input that code running inside a
-- pulse can write is in the key: the merge_state records of follower and
-- leader, the timeline counters, resync flags and origin serial, the song
-- slot and table, and the origin end (song transitions run inside pulses).
-- Leader data only input handlers and editors write (anchor pattern trigs,
-- ranges, clock mods, assignments, the saved configuration) cannot change
-- within a pulse. Never shared: a global queue on either channel or a
-- queued leader configuration (the prediction then reads the song-wide
-- dependency edges). The follower's timing check, with its sticky resync
-- side effect, runs on every build.
local timeline = include("mosaic/lib/musical_merge/timeline")
local shared_admission = {}
local ADMISSION_KEY_SIZE = 21

local function same_admission_key(left, right)
  for index = 1, ADMISSION_KEY_SIZE do
    local u, v = left[index], right[index]
    if u ~= v or math_type(u) ~= math_type(v) then return false end
  end
  return true
end

local function admission_key(song, follower, config, first, last)
  local leader, window = interlock.settings(config)
  if not leader then return nil end
  local follower_record, leader_record = merge_state.peek(song, follower), merge_state.peek(song, leader)
  if (follower_record and follower_record.global_queued) or leader_record and
    (leader_record.global_queued or leader_record.queued ~= nil) then
    return nil
  end
  local running = timeline.running()
  local j, k_l, leader_resync = 0, 0, false
  if running then
    if not timeline.check_timing(song, follower) then return nil end
    local follower_log, leader_log = timeline.channel(follower), timeline.channel(leader)
    j, k_l = follower_log and follower_log.k, leader_log and leader_log.k
    leader_resync = leader_log and leader_log.resync or false
  end
  local mods = song.channels[follower].clock_mods
  local transition = step and step.origin_end_boundary
  local ending = transition and transition(timeline.elapsed_master()) or false
  return {song, leader, window, first, last, running, j, k_l, leader_resync, timeline.serial(),
    leader_record ~= nil, leader_record and leader_record.active or false,
    leader_record and leader_record.cycle or false, leader_record and leader_record.phrase or false,
    type(mods) == "table" and mods.type or false, type(mods) == "table" and mods.value or false,
    ending, program.get().selected_song_pattern, song.global_pattern_length or false,
    config.schema_version, config.mode}
end

local function deep_equal(left, right)
  if type(left) ~= "table" or type(right) ~= "table" then
    return left == right and math_type(left) == math_type(right)
  end
  for key, value in pairs(left) do if not deep_equal(value, right[key]) then return false end end
  for key in pairs(right) do if left[key] == nil then return false end end
  return true
end

local function admission(song, channel, config, first, last, pulse)
  local key = pulse and admission_key(song, channel, config, first, last)
  if key and shared_admission.pulse == pulse and same_admission_key(shared_admission.key, key) then
    local stats = pattern.wrap_memo_stats
    stats.shared_admissions = stats.shared_admissions + 1
    if pattern.wrap_share_check then
      stats.share_checks = stats.share_checks + 1
      local fresh = interlock.admission({song = song, channel = channel, config = config, first = first, last = last})
      if not deep_equal(fresh, shared_admission.result) then
        error("wrap memo: a shared admission differs from its recomputation (channel " .. channel .. ")", 2)
      end
    end
    return shared_admission.result
  end
  local result = interlock.admission({song = song, channel = channel, config = config, first = first, last = last})
  if key then
    shared_admission.pulse, shared_admission.key, shared_admission.result = pulse, key, result
  elseif shared_admission.pulse ~= pulse then
    shared_admission.pulse, shared_admission.key, shared_admission.result = nil, nil, nil
  end
  return result
end

-- One mask layer over steps 1..64: the step mask where one is set (truthy),
-- else the channel-wide value when one applies. Without a channel-wide value
-- only the steps holding a step mask are written.
local function apply_mask_layer(values, step_masks, channel_value)
  if channel_value ~= nil then
    for s = 1, 64 do
      local mask = step_masks[s]
      if mask then values[s] = mask else values[s] = channel_value end
    end
    return
  end
  for s, mask in pairs(step_masks) do
    if mask and math_type(s) == "integer" and s >= 1 and s <= 64 then values[s] = mask end
  end
end

-- memo: serve and seed the content-validated memo (every build of this
-- module passes it; a memo build ignores effective_lengths_cache and, on a
-- miss, derives the lengths from the sources themselves). pulse: the lattice
-- pulse token of a wrap rebuild inside a pulse (m_clock's wrap branch).
function pattern.get_and_merge_patterns(channel, trig_merge_mode, note_merge_mode, velocity_merge_mode, length_merge_mode, song_pattern, effective_lengths_cache, memo, pulse)
  local selected_song_pattern = song_pattern or program.get_selected_song_pattern()
  local merged_pattern, legacy_hit
  local share = memo and type(pulse) == "table" and pattern.wrap_share and pulse or nil
  if memo then
    merged_pattern, legacy_hit = memo_legacy_merge(channel,
      {trig_merge_mode, note_merge_mode, velocity_merge_mode, length_merge_mode}, selected_song_pattern, share)
  else
    merged_pattern = legacy_merge(channel, trig_merge_mode, note_merge_mode, velocity_merge_mode,
      length_merge_mode, selected_song_pattern, effective_lengths_cache)
  end
  local pattern_channel = selected_song_pattern.channels[channel]
  local patterns = selected_song_pattern.patterns
  local step_trig_masks = pattern_channel.step_trig_masks or {}
  local step_note_masks = pattern_channel.step_note_masks or {}
  local step_velocity_masks = pattern_channel.step_velocity_masks or {}
  local step_length_masks = pattern_channel.step_length_masks or {}
  local channel_data = pattern_channel

  local requested_merge_settings = pattern_channel.musical_merge or merge_config.new()
  local merge_runtime = merge_state.effective(selected_song_pattern, channel, requested_merge_settings)
  local merge_settings = merge_runtime and merge_runtime.config
  local merge_version = merge_settings and merge_settings.schema_version
  local foundation_result, fragments_result
  -- Canonical v2 keeps every v1 Foundation behaviour; Fragments exists only in v2.
  local foundation_mode = (merge_version == 1 or merge_version == 2) and merge_settings.mode == "foundation"
  local fragments_mode = merge_version == 2 and merge_settings.mode == "fragments"
  if foundation_mode or fragments_mode then
    local source_trigs, source_velocities, binding_parts = {}, {}, {}
    for pattern_number, enabled in pairs(pattern_channel.selected_patterns) do
      if enabled then
        source_trigs[pattern_number] = patterns[pattern_number].trig_values
        source_velocities[pattern_number] = patterns[pattern_number].velocity_values
        binding_parts[#binding_parts + 1] = pattern_number
      end
    end
    table.sort(binding_parts)
    local cycle = merge_runtime.cycle or 1
    local effective_start=fn.calc_grid_count(pattern_channel.start_trig[1],pattern_channel.start_trig[2])
    local effective_end=fn.calc_grid_count(pattern_channel.end_trig[1],pattern_channel.end_trig[2])
    effective_end=math.min(effective_end,effective_start+(selected_song_pattern.global_pattern_length or 64)-1)
    local song_slot = selected_song_pattern.number or program.get().selected_song_pattern or 1
    local binding = table.concat(binding_parts, ",") .. "|" .. tostring(note_merge_mode) .. "|" ..
      tostring(velocity_merge_mode) .. "|" .. tostring(length_merge_mode)
    if foundation_mode then
      local cycle_percentage = merge_settings.percentages and merge_settings.percentages[cycle] or 100
      local effective_amount = foundation.round_half_up((merge_settings.amount or 100) * cycle_percentage / 100)
      -- Plan §3: the Interlock admission for this build's cycle. It reads the
      -- leader's stored anchors directly and builds no leader plan (§1.2.3).
      -- Its record is published as foundation.interlock (fields documented
      -- in musical_merge/interlock.lua). Every bypass status (RESYNC, PLAN
      -- LIMIT, LEADER OFF, LEADER MISSING) adds no filter: gap, eligibility,
      -- ranking, Amount, Accent and masks then run exactly as with Interlock
      -- off (§1.2 unsupported-admission fallback).
      local filters, interlock_result
      if interlock.settings(merge_settings) then
        interlock_result = admission(selected_song_pattern, channel, merge_settings, effective_start, effective_end, share)
        filters = {}
        if interlock_result.status == interlock.SUPPORTED then
          filters[1] = {reason = interlock_result.reason, blocked = interlock_result.blocked}
        end
      end
      local plan_key = memo and {effective_start, effective_end, merge_settings.anchor, effective_amount,
        merge_settings.accent, merge_settings.gap, merge_settings.seed, song_slot, channel, binding,
        merge_runtime.ranking_phrase or 0, merge_settings.ranking_version}
      local entry = memo and legacy_entry(selected_song_pattern, channel)
      if legacy_hit and entry and entry.plan and same_plan_key(entry.plan_key, plan_key) and
        same_filters(entry.plan_filters, filters) then
        pattern.wrap_memo_stats.plan_hits = pattern.wrap_memo_stats.plan_hits + 1
        foundation_result = copy_plan(entry.plan)
      else
        foundation_result = foundation.plan({
          filters = filters,
          start_step = effective_start,
          end_step = effective_end,
          anchor = merge_settings.anchor,
          source_trigs = source_trigs,
          source_velocities = source_velocities,
          merged_velocities = merged_pattern.velocity_values,
          amount = effective_amount,
          accent = merge_settings.accent,
          gap = merge_settings.gap,
          seed = merge_settings.seed,
          song_slot = song_slot,
          channel = channel,
          binding = binding,
          phrase = merge_runtime.ranking_phrase or 0,
          ranking_version = merge_settings.ranking_version
        })
        if entry then
          pattern.wrap_memo_stats.plan_misses = pattern.wrap_memo_stats.plan_misses + 1
          entry.plan, entry.plan_key, entry.plan_filters = copy_plan(foundation_result), plan_key, copy_filters(filters)
        end
      end
      foundation_result.interlock = interlock_result
      foundation_result.cycle = cycle
      foundation_result.cycles = merge_settings.cycles or 1
      foundation_result.phrase = merge_runtime.phrase or 0
      foundation_result.config = merge_settings
      foundation_result.anchor_notes = patterns[merge_settings.anchor] and
        patterns[merge_settings.anchor].note_values or nil
      -- Plan §4 Markers: explicit structural positions of this plan, read by
      -- step.handle and the Harmony Pattern loop through one shared policy.
      local structure_settings = merge_structure.active(merge_settings)
      if structure_settings and foundation_result.status == "ok" then
        foundation_result.markers = merge_structure.markers(structure_settings.markers,
          merge_structure.positions(effective_start, effective_end), foundation_result.roles)
      end
      merged_pattern.foundation = foundation_result
    else
      -- Plan §2: a separate mode, never the Foundation planner. Shape
      -- percentages, Amount, Accent and Gap do not apply.
      local fragment_settings = merge_settings.fragments or {}
      fragments_result = fragments.plan({
        start_step = effective_start,
        end_step = effective_end,
        size = fragment_settings.size or 8,
        candidates = binding_parts,
        patterns = patterns,
        seed = merge_settings.seed,
        song_slot = song_slot,
        channel = channel,
        binding = binding,
        phrase = merge_runtime.ranking_phrase or 0,
        cycle = cycle,
        keep_anchor = fragment_settings.keep_anchor == true,
        anchor = merge_settings.anchor
      })
      fragments_result.cycle = cycle
      fragments_result.cycles = merge_settings.cycles or 1
      fragments_result.phrase = merge_runtime.phrase or 0
      fragments_result.config = merge_settings
      merged_pattern.fragments = fragments_result
      if fragments_result.status == "ok" then
        -- Inside a fragment the legacy note/velocity/length merge modes and
        -- merged-pentatonic do not apply: every value is the source's own.
        merged_pattern.merged_notes = {}
        for s = 1, 64 do merged_pattern.trig_values[s] = fragments_result.trigs[s] end
        for _, s in ipairs(fragments_result.positions) do
          merged_pattern.note_values[s] = fragments_result.notes[s]
          merged_pattern.velocity_values[s] = fragments_result.velocities[s]
          merged_pattern.lengths[s] = fragments_result.lengths[s]
        end
      end
    end
  end

  -- The final layer: the plan's trigs and velocities, then the step masks,
  -- else the channel masks. Each step's writes are independent of every
  -- other step's, so the layers are applied one after another; when no
  -- channel-wide mask applies only the steps that have a step mask are
  -- visited (1..64 integer keys; `false` never applies). Nothing below
  -- writes the channel or the plan.
  local foundation_trigs = foundation_result and foundation_result.status == "ok" and foundation_result.trigs
  local trig_values, note_mask_values = merged_pattern.trig_values, merged_pattern.note_mask_values
  local velocity_values, merged_lengths = merged_pattern.velocity_values, merged_pattern.lengths
  if foundation_trigs then
    for s = 1, 64 do trig_values[s] = foundation_trigs[s] end
    local foundation_velocities = foundation_result.velocities
    for s = 1, 64 do
      local velocity = foundation_velocities[s]
      if velocity ~= nil then velocity_values[s] = velocity end
    end
  end
  local trig_mask, note_mask = channel_data.trig_mask, channel_data.note_mask
  local velocity_mask = channel_data.velocity_mask
  if not (trig_mask and trig_mask ~= -1) then trig_mask = nil end
  if not (note_mask and note_mask ~= -1) then note_mask = nil end
  if not (velocity_mask and velocity_mask ~= -1) then velocity_mask = nil end
  -- (sic) lengths_mask: the existing condition, kept exactly.
  local length_mask_applies = channel_data.length_mask and channel_data.lengths_mask ~= -1
  apply_mask_layer(trig_values, step_trig_masks, trig_mask)
  apply_mask_layer(note_mask_values, step_note_masks, note_mask)
  apply_mask_layer(velocity_values, step_velocity_masks, velocity_mask)
  if length_mask_applies then
    for s = 1, 64 do
      local mask = step_length_masks[s]
      if mask then merged_lengths[s] = mask else merged_lengths[s] = program.get_length_mask(channel_data) end
    end
  else
    apply_mask_layer(merged_lengths, step_length_masks, nil)
  end

  return merged_pattern
end

local working_pattern_updates = setmetatable({}, {__mode = "k"})

-- Plan §1.3 / §1.5: the Interlock leader a configuration names, counted
-- whether or not the feature is active.
local function add_leaders(config, number, leaders, into)
  for _, leader in ipairs(merge_dependency.leaders(config)) do
    if leaders == nil or leaders[leader] then into[number] = true end
  end
end

-- Channels whose saved, active or queued configuration follows a channel in
-- `leaders` (every leader when nil). Empty when no leader is configured in the
-- slot, so Off adds no rebuilds.
function pattern.followers_of(song_pattern, leaders)
  local result = {}
  for c = 1, 16 do
    local channel = song_pattern.channels[c]
    add_leaders(channel and channel.musical_merge, c, leaders, result)
    local record = merge_state.peek(song_pattern, c)
    if record then
      add_leaders(record.active, c, leaders, result)
      add_leaders(record.queued, c, leaders, result)
      add_leaders(record.global_queued, c, leaders, result)
    end
  end
  return result
end

local function invalidate_lookahead(c)
  local scheduler = m_clock and m_clock.lookahead_scheduler
  if scheduler then scheduler:invalidate(c, nil, nil) end
end

local function build_working_pattern(c, song_pattern, channel_pattern, effective_lengths_cache, memo, pulse)
  return pattern.get_and_merge_patterns(
    c,
    channel_pattern.trig_merge_mode,
    channel_pattern.note_merge_mode,
    channel_pattern.velocity_merge_mode,
    channel_pattern.length_merge_mode,
    song_pattern,
    effective_lengths_cache,
    memo,
    pulse
  )
end

-- Revisions describe pending rebuild requests, not persisted source versions.
-- Compound writers retain the all-channel facade; targeted requests are unioned
-- so cancelling a partial sweep cannot discard another channel's pending edit.
function pattern.update_working_patterns(song_pattern, affected_channels)
  local target = song_pattern or program.get_selected_song_pattern()
  local state = working_pattern_updates[target]
  if not state then
    state = {dirty = {}, revision = {}}
    state.update = scheduler.debounce(function()
      repeat
        -- Leaders before their followers (plan §1.3); without followers this
        -- is the original 1..16 order.
        local followers = pattern.followers_of(target)
        for pass = 1, next(followers) and 2 or 1 do
          for c = 1, 16 do
            if state.dirty[c] and (followers[c] == true) == (pass == 2) then
              local revision = state.revision[c]
              local channel = target.channels[c]
              local result = build_working_pattern(c, target, channel, state.effective_lengths_cache, true)
              if working_pattern_updates[target] == state
                and state.revision[c] == revision and target.channels[c] == channel then
                channel.working_pattern = result
                state.dirty[c] = nil
              end
              coroutine.yield()
            end
          end
        end
      until next(state.dirty) == nil
      state.effective_lengths_cache = nil
    end, throttle_time)
    working_pattern_updates[target] = state
  end
  -- At most the song's 16 source length arrays live for this request.
  -- Any request invalidates them, including a no-op or mask-only request.
  state.effective_lengths_cache = {}
  -- Plan §1.3: a rebuilt leader adds its followers to the same rebuild set,
  -- with the lookahead invalidation an edit to the follower itself receives.
  local followers = affected_channels and pattern.followers_of(target, affected_channels) or {}
  local requested = false
  for c = 1, 16 do
    if not affected_channels or affected_channels[c] or followers[c] then
      if followers[c] and not (affected_channels and affected_channels[c]) then invalidate_lookahead(c) end
      state.dirty[c] = true
      state.revision[c] = (state.revision[c] or 0) + 1
      requested = true
    end
  end
  if requested then state.update() end
end

function pattern.get_source_revision(song_pattern, source_number)
  return source_revisions:get(song_pattern, source_number)
end

function pattern.update_source_working_patterns(song_pattern, source_number)
  source_revisions:edited(song_pattern, source_number)
  local affected = {}
  for c = 1, 16 do
    local channel = song_pattern.channels[c]
    affected[c] = channel.selected_patterns[source_number] == true
      or (channel.note_merge_mode and extract_pattern_number(channel.note_merge_mode) == source_number)
      or (channel.velocity_merge_mode and extract_pattern_number(channel.velocity_merge_mode) == source_number)
      or (channel.length_merge_mode and extract_pattern_number(channel.length_merge_mode) == source_number)
  end
  pattern.update_working_patterns(song_pattern, affected)
end

local function rebuild(c, song_pattern, memo, pulse)
  local channel_pattern = song_pattern.channels[c]
  channel_pattern.working_pattern = build_working_pattern(c, song_pattern, channel_pattern, nil, memo, pulse)
end

-- Rebuild, synchronously, every follower of a channel in `leaders` (every
-- follower in the slot when nil), invalidating each follower's lookahead.
function pattern.rebuild_followers(song_pattern, leaders)
  if not song_pattern then return end
  for c in pairs(pattern.followers_of(song_pattern, leaders)) do
    invalidate_lookahead(c)
    rebuild(c, song_pattern, true)
  end
end

-- at_wrap: the clock's own rebuild at the channel's loop wrap. That plans the
-- channel's new cycle, which its followers' admissions already predicted
-- (plan §1.2.3), so it is not an edit and does not propagate. pulse: the
-- lattice pulse token of that wrap (Lattice.pulse_token), which lets the
-- rebuilds of one pulse share work (see the wrap memo).
function pattern.update_working_pattern(c, song_pattern, at_wrap, pulse)
  -- Legacy synchronous callers may have changed source arrays directly.
  -- Do not let a pending sweep retain pre-edit lengths after this ingress.
  local state = working_pattern_updates[song_pattern]
  if state then state.effective_lengths_cache = {} end
  -- The wrap rebuild serves unchanged inputs from the content-validated memo.
  rebuild(c, song_pattern, true, at_wrap == true and pulse or nil)
  -- Plan §1.3: leader edits reach followers.
  if not at_wrap then pattern.rebuild_followers(song_pattern, {[c] = true}) end
end

return pattern
