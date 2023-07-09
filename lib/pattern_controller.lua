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

  for pattern_number, _ in pairs(program.sequencer_patterns[selected_sequencer_pattern].channels[channel].selected_patterns) do
    local pattern = program.sequencer_patterns[selected_sequencer_pattern].patterns[pattern_number]

    for s = 1, 64 do

      if pattern.note_values[s] == -1 then
        pattern.note_values[s] = 0
      end

      if merged_pattern.note_values[s] == -1 then
        merged_pattern.note_values[s] = 0
      end

      if pattern.lengths[s] == -1 then
        pattern.lengths[s] = 0
      end

      if merged_pattern.lengths[s] == -1 then
        merged_pattern.lengths[s] = 0
      end

      if pattern.velocity_values[s] == -1 then
        pattern.velocity_values[s] = 0
      end

      if merged_pattern.velocity_values[s] == -1 then
        merged_pattern.velocity_values[s] = 0
      end

      if merge_mode == "skip" then
        if pattern.trig_values[s] == 1 and merged_pattern.trig_values[s] < 1 and skip_bits[s] < 1 then
          merged_pattern = pattern_controller:sync_pattern_values(merged_pattern, pattern, s)
        elseif pattern.trig_values[s] == 1 and merged_pattern.trig_values[s] == 1 then
          merged_pattern.trig_values[s] = 0
          skip_bits[s] = 1
        end
      elseif merge_mode == "pattern_number_"..pattern_number then
        if pattern.trig_values[s] == 1 then
          merged_pattern = pattern_controller:sync_pattern_values(merged_pattern, pattern, s)
        end
      elseif merge_mode == "add" or merge_mode == "subtract" or merge_mode == "average" then
        if merge_mode == "add" then

          if pattern.trig_values[s] == 1 then
            merged_pattern.trig_values[s] = 1
            merged_pattern.note_values[s] = merged_pattern.note_values[s] + pattern.note_values[s]
          end
        elseif merge_mode == "average" then
          average_note_accumulator[s] = average_note_accumulator[s] + pattern.note_values[s]
        elseif merge_mode == "subtract" then
  
          if pattern.trig_values[s] == 1 then
            merged_pattern.trig_values[s] = 1
            merged_pattern.note_values[s] = merged_pattern.note_values[s] - pattern.note_values[s]
          end
        end

        if pattern.trig_values[s] == 1 then
          average_length_accumulator[s] = average_length_accumulator[s] + pattern.lengths[s]
          average_velocity_accumulator[s] =  average_velocity_accumulator[s] + pattern.velocity_values[s]
          average_count[s] = average_count[s] + 1
        end

      elseif not string.match(merge_mode, "pattern_number_") then
        if pattern.trig_values[s] == 1 then
          merged_pattern.trig_values[s] = 1
        end
      end
    end
  end

  for s = 1, 64 do
    if merge_mode == "add" or merge_mode == "subtract" or merge_mode == "average" then
      merged_pattern.lengths[s] = math.ceil(average_length_accumulator[s] / average_count[s])
      merged_pattern.velocity_values[s] = math.ceil(average_velocity_accumulator[s] / average_count[s])
      if merge_mode == "average" then
        merged_pattern.note_values[s] = math.ceil(average_note_accumulator[s] / average_count[s])
      end
    end
  end

  return merged_pattern
end



function pattern_controller:update_working_patterns()
  local selected_sequencer_pattern = program.selected_sequencer_pattern

  for c = 1, 16 do
    local merge_mode = program.sequencer_patterns[selected_sequencer_pattern].channels[c].merge_mode
    local working_pattern = pattern_controller:get_and_merge_patterns(c, merge_mode)
    program.sequencer_patterns[selected_sequencer_pattern].channels[c].working_pattern = working_pattern

  end

end

return pattern_controller