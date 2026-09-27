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

function pattern.get_and_merge_patterns(channel, trig_merge_mode, note_merge_mode, velocity_merge_mode, length_merge_mode, song_pattern, effective_lengths_cache)
  local selected_song_pattern = song_pattern or program.get_selected_song_pattern()
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

  local step_trig_masks = pattern_channel.step_trig_masks or {}
  local step_note_masks = pattern_channel.step_note_masks or {}
  local step_velocity_masks = pattern_channel.step_velocity_masks or {}
  local step_length_masks = pattern_channel.step_length_masks or {}
  local channel_data = pattern_channel

  for s = 1, 64 do
    do_mode_calculation(note_merge_mode, s, notes, merged_pattern.note_values)
    do_mode_calculation(velocity_merge_mode, s, velocities, merged_pattern.velocity_values)
    do_mode_calculation(length_merge_mode, s, lengths, merged_pattern.lengths)

    if note_priority then merged_pattern.note_values[s] = patterns[note_priority].note_values[s] end
    if velocity_priority then merged_pattern.velocity_values[s] = patterns[velocity_priority].velocity_values[s] end
    if length_priority then merged_pattern.lengths[s] = priority_lengths[s] end
  end

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
        interlock_result = interlock.admission({
          song = selected_song_pattern, channel = channel, config = merge_settings,
          first = effective_start, last = effective_end
        })
        filters = {}
        if interlock_result.status == interlock.SUPPORTED then
          filters[1] = {reason = interlock_result.reason, blocked = interlock_result.blocked}
        end
      end
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

  -- Loop invariants hoisted; nothing below writes the channel or the plan.
  local foundation_trigs = foundation_result and foundation_result.status == "ok" and foundation_result.trigs
  local foundation_velocities = foundation_trigs and foundation_result.velocities
  local trig_values, note_mask_values = merged_pattern.trig_values, merged_pattern.note_mask_values
  local velocity_values, merged_lengths = merged_pattern.velocity_values, merged_pattern.lengths
  local trig_mask, note_mask = channel_data.trig_mask, channel_data.note_mask
  local velocity_mask = channel_data.velocity_mask
  if not (trig_mask and trig_mask ~= -1) then trig_mask = nil end
  if not (note_mask and note_mask ~= -1) then note_mask = nil end
  if not (velocity_mask and velocity_mask ~= -1) then velocity_mask = nil end
  -- (sic) lengths_mask: the existing condition, kept exactly.
  local length_mask_applies = channel_data.length_mask and channel_data.lengths_mask ~= -1
  for s = 1, 64 do
    if foundation_trigs then
      trig_values[s] = foundation_trigs[s]
      local velocity = foundation_velocities[s]
      if velocity ~= nil then velocity_values[s] = velocity end
    end

    local mask = step_trig_masks[s]
    if mask then
      trig_values[s] = mask
    elseif trig_mask then
      trig_values[s] = trig_mask
    end

    mask = step_note_masks[s]
    if mask then
      note_mask_values[s] = mask
    elseif note_mask then
      note_mask_values[s] = note_mask
    end

    mask = step_velocity_masks[s]
    if mask then
      velocity_values[s] = mask
    elseif velocity_mask then
      velocity_values[s] = velocity_mask
    end

    mask = step_length_masks[s]
    if mask then
      merged_lengths[s] = mask
    elseif length_mask_applies then
      merged_lengths[s] = program.get_length_mask(channel_data)
    end
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

local function build_working_pattern(c, song_pattern, channel_pattern, effective_lengths_cache)
  return pattern.get_and_merge_patterns(
    c,
    channel_pattern.trig_merge_mode,
    channel_pattern.note_merge_mode,
    channel_pattern.velocity_merge_mode,
    channel_pattern.length_merge_mode,
    song_pattern,
    effective_lengths_cache
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
              local result = build_working_pattern(c, target, channel, state.effective_lengths_cache)
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

local function rebuild(c, song_pattern)
  local channel_pattern = song_pattern.channels[c]
  channel_pattern.working_pattern = build_working_pattern(c, song_pattern, channel_pattern)
end

-- Rebuild, synchronously, every follower of a channel in `leaders` (every
-- follower in the slot when nil), invalidating each follower's lookahead.
function pattern.rebuild_followers(song_pattern, leaders)
  if not song_pattern then return end
  for c in pairs(pattern.followers_of(song_pattern, leaders)) do
    invalidate_lookahead(c)
    rebuild(c, song_pattern)
  end
end

-- at_wrap: the clock's own rebuild at the channel's loop wrap. That plans the
-- channel's new cycle, which its followers' admissions already predicted
-- (plan §1.2.3), so it is not an edit and does not propagate.
function pattern.update_working_pattern(c, song_pattern, at_wrap)
  -- Legacy synchronous callers may have changed source arrays directly.
  -- Do not let a pending sweep retain pre-edit lengths after this ingress.
  local state = working_pattern_updates[song_pattern]
  if state then state.effective_lengths_cache = {} end
  rebuild(c, song_pattern)
  -- Plan §1.3: leader edits reach followers.
  if not at_wrap then pattern.rebuild_followers(song_pattern, {[c] = true}) end
end

return pattern
