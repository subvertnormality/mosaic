local pattern = {}

local quantiser = include("mosaic/lib/quantiser")
local m_clock = include("mosaic/lib/clock/m_clock")
local divisions = include("mosaic/lib/clock/divisions")

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

function pattern.get_and_merge_patterns(channel, trig_merge_mode, note_merge_mode, velocity_merge_mode, length_merge_mode, song_pattern)
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
    local source_lengths = effective_lengths(pattern)
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

function pattern.update_working_patterns(song_pattern)
  local target = song_pattern or program.get_selected_song_pattern()
  local update = working_pattern_updates[target]
  if not update then
    update = scheduler.debounce(function(selected_song_pattern)
      for c = 1, 16 do
        pattern.update_working_pattern(c, selected_song_pattern)
        coroutine.yield()
      end
    end, throttle_time)
    working_pattern_updates[target] = update
  end
  update(target)
end

function pattern.update_working_pattern(c, song_pattern)

  local channel_pattern = song_pattern.channels[c]
  channel_pattern.working_pattern = pattern.get_and_merge_patterns(
    c,
    channel_pattern.trig_merge_mode,
    channel_pattern.note_merge_mode,
    channel_pattern.velocity_merge_mode,
    channel_pattern.length_merge_mode,
    song_pattern
  )
end

return pattern