local pattern_controller = {}

function pattern_controller:sync_pattern_values(merged_pattern, pattern, s)
  merged_pattern.trig_values[s] = 1
  merged_pattern.lengths[s] = pattern.lengths[s]
  merged_pattern.velocity_values[s] = pattern.velocity_values[s]
  merged_pattern.note_values[s] = pattern.note_values[s]
  return merged_pattern
end

function pattern_controller:get_and_merge_patterns(channel, merge_mode)

  local selected_sequencer_pattern = program.selected_sequencer_pattern
  local merged_pattern = fn.initialise_default_pattern()
  local skip_bits = fn.initialise_64_table(0)
  local average_length_accumulator = fn.initialise_64_table(0)
  local average_velocity_accumulator = fn.initialise_64_table(0)
  local average_note_accumulator = fn.initialise_64_table(0)
  local average_count = fn.initialise_64_table(0)

  local pattern_channel = program.sequencer_patterns[selected_sequencer_pattern].channels[channel]
  local patterns = program.sequencer_patterns[selected_sequencer_pattern].patterns

  for pattern_number, _ in pairs(pattern_channel.selected_patterns) do
    local pattern = patterns[pattern_number]

    local sorted_note_values = {} -- Moved the sorted_note_values table inside this loop

    for s = 1, 64 do
      table.insert(sorted_note_values, pattern.note_values[s]) -- Insert note values into the table
    end

    table.sort(sorted_note_values, function(a, b) return a > b end) -- Sort the note values in descending order

    for s = 1, 64 do

      local pattern_note_value = sorted_note_values[s] == -1 and 0 or sorted_note_values[s] -- Use sorted note values here
      local merged_pattern_note_value = merged_pattern.note_values[s] == -1 and 0 or merged_pattern.note_values[s]
      local pattern_length = pattern.lengths[s] == -1 and 0 or pattern.lengths[s]
      local merged_pattern_length = merged_pattern.lengths[s] == -1 and 0 or merged_pattern.lengths[s]
      local pattern_velocity_value = pattern.velocity_values[s] == -1 and 0 or pattern.velocity_values[s]
      local merged_pattern_velocity_value = merged_pattern.velocity_values[s] == -1 and 0 or merged_pattern.velocity_values[s]

      local is_pattern_trig_one = pattern.trig_values[s] == 1

      if merge_mode == "skip" then
        if is_pattern_trig_one and merged_pattern.trig_values[s] < 1 and skip_bits[s] < 1 then
          merged_pattern = pattern_controller:sync_pattern_values(merged_pattern, pattern, s)
        elseif is_pattern_trig_one and merged_pattern.trig_values[s] == 1 then
          merged_pattern.trig_values[s] = 0
          skip_bits[s] = 1
        end
      elseif merge_mode == "pattern_number_"..pattern_number then
        if is_pattern_trig_one then
          merged_pattern = pattern_controller:sync_pattern_values(merged_pattern, pattern, s)
        end
      elseif merge_mode == "add" or merge_mode == "subtract" or merge_mode == "average" then
  
        if merge_mode == "add" then
          if is_pattern_trig_one then
            merged_pattern.trig_values[s] = 1
            merged_pattern.note_values[s] = merged_pattern_note_value + pattern_note_value
          end
        elseif merge_mode == "average" then
          average_note_accumulator[s] = average_note_accumulator[s] + pattern_note_value
        elseif merge_mode == "subtract" then
          if is_pattern_trig_one then
            merged_pattern.trig_values[s] = 1
            if (merged_pattern_note_value == 0) then
              merged_pattern.note_values[s] = pattern_note_value
            else
              merged_pattern.note_values[s] = merged_pattern_note_value - pattern_note_value
            end
          end
        end

        if is_pattern_trig_one then
          average_length_accumulator[s] = average_length_accumulator[s] + pattern_length
          average_velocity_accumulator[s] = average_velocity_accumulator[s] + pattern_velocity_value
          average_count[s] = average_count[s] + 1
        end

      elseif not string.match(merge_mode, "pattern_number_") then
        if is_pattern_trig_one then
          merged_pattern.trig_values[s] = 1
        end
      end
    end
  end

  for s = 1, 64 do
    if merge_mode == "add" or merge_mode == "subtract" or merge_mode == "average" then
      merged_pattern.lengths[s] = math.ceil(average_length_accumulator[s] / (average_count[s] or 1))
      merged_pattern.velocity_values[s] = math.ceil(average_velocity_accumulator[s] / (average_count[s] or 1))
      if merge_mode == "average" then
        merged_pattern.note_values[s] = math.ceil(average_note_accumulator[s] / (average_count[s] or 1))
      end
    end
  end

  return merged_pattern
end



function pattern_controller:update_working_patterns()
  local selected_sequencer_pattern = program.selected_sequencer_pattern
  local sequencer_patterns = program.sequencer_patterns[selected_sequencer_pattern].channels

  for c = 1, 16 do
    local merge_mode = sequencer_patterns[c].merge_mode
    local working_pattern = pattern_controller:get_and_merge_patterns(c, merge_mode)
    sequencer_patterns[c].working_pattern = working_pattern
  end

end

return pattern_controller
