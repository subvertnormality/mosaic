local pattern = {}

local quantiser = include("mosaic/lib/quantiser")
local foundation = include("mosaic/lib/musical_merge/foundation")
local merge_state = include("mosaic/lib/musical_merge/state")
local merge_config = include("mosaic/lib/musical_merge/config")

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
  local foundation_result
  if merge_settings and merge_settings.schema_version == 1 and merge_settings.mode == "foundation" then
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
    local cycle_percentage = merge_settings.percentages and merge_settings.percentages[cycle] or 100
    local effective_amount = foundation.round_half_up((merge_settings.amount or 100) * cycle_percentage / 100)
    local effective_start=fn.calc_grid_count(pattern_channel.start_trig[1],pattern_channel.start_trig[2])
    local effective_end=fn.calc_grid_count(pattern_channel.end_trig[1],pattern_channel.end_trig[2])
    effective_end=math.min(effective_end,effective_start+(selected_song_pattern.global_pattern_length or 64)-1)
    foundation_result = foundation.plan({
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
      song_slot = selected_song_pattern.number or program.get().selected_song_pattern or 1,
      channel = channel,
      binding = table.concat(binding_parts, ",") .. "|" .. tostring(note_merge_mode) .. "|" ..
        tostring(velocity_merge_mode) .. "|" .. tostring(length_merge_mode),
      phrase = merge_runtime.ranking_phrase or 0,
      ranking_version = merge_settings.ranking_version
    })
    foundation_result.cycle = cycle
    foundation_result.cycles = merge_settings.cycles or 1
    foundation_result.phrase = merge_runtime.phrase or 0
    foundation_result.config = merge_settings
    foundation_result.anchor_notes = patterns[merge_settings.anchor] and
      patterns[merge_settings.anchor].note_values or nil
    merged_pattern.foundation = foundation_result
  end

  for s = 1, 64 do
    if foundation_result and foundation_result.status == "ok" then
      merged_pattern.trig_values[s] = foundation_result.trigs[s]
      if foundation_result.velocities[s] ~= nil then
        merged_pattern.velocity_values[s] = foundation_result.velocities[s]
      end
    end

    if step_trig_masks[s] then
      merged_pattern.trig_values[s] = step_trig_masks[s]
    elseif channel_data.trig_mask and channel_data.trig_mask ~= -1 then
      merged_pattern.trig_values[s] = channel_data.trig_mask
    end

    if step_note_masks[s] then
      merged_pattern.note_mask_values[s] = step_note_masks[s]
    elseif channel_data.note_mask and channel_data.note_mask ~= -1 then
      merged_pattern.note_mask_values[s] = channel_data.note_mask
    end

    if step_velocity_masks[s] then
      merged_pattern.velocity_values[s] = step_velocity_masks[s]
    elseif channel_data.velocity_mask and channel_data.velocity_mask ~= -1 then
      merged_pattern.velocity_values[s] = channel_data.velocity_mask
    end

    if step_length_masks[s] then
      merged_pattern.lengths[s] = step_length_masks[s]
    elseif channel_data.length_mask and channel_data.lengths_mask ~= -1 then
      merged_pattern.lengths[s] = program.get_length_mask(channel_data)
    end
  end

  return merged_pattern
end

local working_pattern_updates = setmetatable({}, {__mode = "k"})

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
        for c = 1, 16 do
          if state.dirty[c] then
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
      until next(state.dirty) == nil
      state.effective_lengths_cache = nil
    end, throttle_time)
    working_pattern_updates[target] = state
  end
  -- At most the song's 16 source length arrays live for this request.
  -- Any request invalidates them, including a no-op or mask-only request.
  state.effective_lengths_cache = {}
  local requested = false
  for c = 1, 16 do
    if not affected_channels or affected_channels[c] then
      state.dirty[c] = true
      state.revision[c] = (state.revision[c] or 0) + 1
      requested = true
    end
  end
  if requested then state.update() end
end

function pattern.update_source_working_patterns(song_pattern, source_number)
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

function pattern.update_working_pattern(c, song_pattern)
  -- Legacy synchronous callers may have changed source arrays directly.
  -- Do not let a pending sweep retain pre-edit lengths after this ingress.
  local state = working_pattern_updates[song_pattern]
  if state then state.effective_lengths_cache = {} end
  local channel_pattern = song_pattern.channels[c]
  channel_pattern.working_pattern = build_working_pattern(c, song_pattern, channel_pattern)
end

return pattern
