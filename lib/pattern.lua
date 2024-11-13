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

local function sync_pattern_values(merged_pattern, pattern, s)
  merged_pattern.lengths[s] = pattern.lengths[s]
  merged_pattern.velocity_values[s] = pattern.velocity_values[s]
  merged_pattern.note_values[s] = pattern.note_values[s]
  return merged_pattern
end

local function extract_pattern_number(merge_mode)
  local prefix = "pattern_number_"
  if merge_mode:sub(1, #prefix) == prefix then
    return tonumber(merge_mode:sub(#prefix + 1))
  end
  return nil
end

function pattern.get_and_merge_patterns(channel, trig_merge_mode, note_merge_mode, velocity_merge_mode, length_merge_mode)
  local selected_sequencer_pattern = program.get_selected_sequencer_pattern()
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

  local pattern_channel = selected_sequencer_pattern.channels[channel]
  local patterns = selected_sequencer_pattern.patterns

  for i = 1, 64 do
    notes[i] = {}
    lengths[i] = {}
    velocities[i] = {}
  end

  local function do_moded_merge(pattern_number, is_pattern_trig_one, s, mode, values, merged_values, pushed_values)
    if mode == "pattern_number_" .. pattern_number then
      merged_values[s] = values[s]
    elseif mode == "up" or mode == "down" or mode == "average" then
      if is_pattern_trig_one then
        insert(pushed_values[s], values[s])
      end
    end
  end

  local patterns_to_process = pattern_channel.selected_patterns

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

    for s = 1, 64 do
      local is_pattern_trig_one = pattern.trig_values[s] == 1
      if pattern_enabled then
        if trig_merge_mode == "skip" then
          if is_pattern_trig_one and merged_pattern.trig_values[s] < 1 and skip_bits[s] < 1 then
            merged_pattern = sync_pattern_values(merged_pattern, pattern, s)
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

      local is_positive_step_trig_mask = program.get_step_trig_masks(channel) and program.get_step_trig_masks(channel)[s] == 1
      local should_process_note_merge_mode = is_pattern_trig_one or is_positive_step_trig_mask or (note_merge_mode and extract_pattern_number(note_merge_mode))
      local should_process_velocity_merge_mode = is_pattern_trig_one or is_positive_step_trig_mask or (velocity_merge_mode and extract_pattern_number(velocity_merge_mode))
      local should_process_length_merge_mode = is_pattern_trig_one or is_positive_step_trig_mask or (length_merge_mode and extract_pattern_number(length_merge_mode))

      if should_process_note_merge_mode then
        do_moded_merge(pattern_number, true, s, note_merge_mode, pattern.note_values, merged_pattern.note_values, notes)
      end
      if should_process_velocity_merge_mode then
        do_moded_merge(pattern_number, true, s, velocity_merge_mode, pattern.velocity_values, merged_pattern.velocity_values, velocities)
      end
      if should_process_length_merge_mode then
        do_moded_merge(pattern_number, true, s, length_merge_mode, pattern.lengths, merged_pattern.lengths, lengths)
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

  local step_trig_masks = program.get_step_trig_masks(channel)
  local step_note_masks = program.get_step_note_masks(channel)
  local step_velocity_masks = program.get_step_velocity_masks(channel)
  local step_length_masks = program.get_step_length_masks(channel)
  local channel_data = program.get_channel(channel)

  for s = 1, 64 do
    do_mode_calculation(note_merge_mode, s, notes, merged_pattern.note_values)
    do_mode_calculation(velocity_merge_mode, s, velocities, merged_pattern.velocity_values)
    do_mode_calculation(length_merge_mode, s, lengths, merged_pattern.lengths)

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

pattern.update_working_patterns = scheduler.debounce(function()
  for c = 1, 16 do
    pattern.update_working_pattern(c)
    coroutine.yield()
  end
end, throttle_time)

function pattern.update_working_pattern(c)
  local selected_sequencer_pattern = program.get_selected_sequencer_pattern()
  local channel_pattern = selected_sequencer_pattern.channels[c]
  channel_pattern.working_pattern = pattern.get_and_merge_patterns(
    c,
    channel_pattern.trig_merge_mode,
    channel_pattern.note_merge_mode,
    channel_pattern.velocity_merge_mode,
    channel_pattern.length_merge_mode
  )

  if c == 1 then 
    -- fn.print_table(channel_pattern.working_pattern)
  end
end

return pattern