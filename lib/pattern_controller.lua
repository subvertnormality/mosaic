local pattern_controller = {}
local fn = include("mosaic/lib/functions")


local notes = program.initialise_64_table({})
local lengths = program.initialise_64_table({})
local velocities = program.initialise_64_table({})

function pattern_controller.sync_pattern_values(merged_pattern, pattern, s)
  merged_pattern.lengths[s] = pattern.lengths[s]
  merged_pattern.velocity_values[s] = pattern.velocity_values[s]
  merged_pattern.note_values[s] = pattern.note_values[s]
  return merged_pattern
end

function pattern_controller.get_and_merge_patterns(channel, trig_merge_mode, note_merge_mode, velocity_merge_mode, length_merge_mode)

  local selected_sequencer_pattern = program.get().selected_sequencer_pattern
  local merged_pattern = program.initialise_default_pattern()
  local skip_bits = program.initialise_64_table(0)
  local only_bits = program.initialise_64_table(0)

  local pattern_channel = program.get_selected_sequencer_pattern().channels[channel]
  local patterns = program.get_selected_sequencer_pattern().patterns

  for i = 1, 64 do
    notes[i] = {}
    lengths[i] = {}
    velocities[i] = {}
  end

  function do_moded_merge(pattern_number, is_pattern_trig_one, s, mode, values, merged_values, pushed_values)

    if mode == "pattern_number_" .. pattern_number then
      merged_values[s] = values[s]
    elseif mode == "up" or mode == "down" or mode == "average" then
      if is_pattern_trig_one then
        table.insert(pushed_values[s], values[s])
      end
    end

  end

  local patterns_to_process = fn.deep_copy(pattern_channel.selected_patterns)

  local function process_merge_mode(merge_mode)
      if merge_mode and string.match(merge_mode, "pattern_number_") then
          local pattern_number = tonumber(string.match(merge_mode, "pattern_number_(%d+)"))
          if patterns_to_process[pattern_number] == nil then
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
        if (pattern_enabled) then
          if trig_merge_mode == "skip" then
            if is_pattern_trig_one and merged_pattern.trig_values[s] < 1 and skip_bits[s] < 1 then
              merged_pattern = pattern_controller.sync_pattern_values(merged_pattern, pattern, s)
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
          elseif trig_merge_mode == "all" then
            if is_pattern_trig_one then
              
              merged_pattern.trig_values[s] = 1
            end
          end 
        end
        
        -- Determine whether to process each merge mode based on `is_pattern_trig_one` or the specific "pattern_number_" condition.
        local should_process_note_merge_mode = is_pattern_trig_one or (note_merge_mode and string.match(note_merge_mode, "pattern_number_"))
        local should_process_velocity_merge_mode = is_pattern_trig_one or (velocity_merge_mode and string.match(velocity_merge_mode, "pattern_number_"))
        local should_process_length_merge_mode = is_pattern_trig_one or (length_merge_mode and string.match(length_merge_mode, "pattern_number_"))

        -- Process each merge mode only if its corresponding condition is met.
        if should_process_note_merge_mode then
            do_moded_merge(pattern_number, is_pattern_trig_one, s, note_merge_mode, patterns[pattern_number].note_values, merged_pattern.note_values, notes)
        end
        if should_process_velocity_merge_mode then
            do_moded_merge(pattern_number, is_pattern_trig_one, s, velocity_merge_mode, patterns[pattern_number].velocity_values, merged_pattern.velocity_values, velocities)
        end
        if should_process_length_merge_mode then
            do_moded_merge(pattern_number, is_pattern_trig_one, s, length_merge_mode, patterns[pattern_number].lengths, merged_pattern.lengths, lengths)
        end

      end



  end

  local function do_mode_calculation(mode, s, values, merged_values, fn)
    if mode == "up" or mode == "down" or mode == "average" then
      if not values[s] or #values[s] == 0 then
        merged_values[s] = 0
      elseif #values[s] == 1 then
        merged_values[s] = values[s][1]
      else
        local min_value = values[s][1]
        local max_value = values[s][#values[s]]
        local average = fn.average_table_values(values[s])
        if mode == "up" then
          merged_values[s] = average + (max_value - min_value)
        elseif mode == "down" then
          merged_values[s] = min_value - (average - min_value)
        elseif mode == "average" then
          merged_values[s] = average
        end
      end
    end
  end

  for s = 1, 64 do
      if note_merge_mode == "up" or note_merge_mode == "down" then table.sort(notes[s]) end
      if velocity_merge_mode == "up" or velocity_merge_mode == "down" then table.sort(velocities[s]) end
      if length_merge_mode == "up" or length_merge_mode == "down" then table.sort(lengths[s]) end
  
      do_mode_calculation(note_merge_mode, s, notes, merged_pattern.note_values, fn)
      do_mode_calculation(velocity_merge_mode, s, velocities, merged_pattern.velocity_values, fn)
      do_mode_calculation(length_merge_mode, s, lengths, merged_pattern.lengths, fn)

      -- Override trig with the channel's set trig mask
      local step_trig_masks = program.get_step_trig_masks(channel)
      if step_trig_masks[s] ~= -1 then
        merged_pattern.trig_values[s] = step_trig_masks[s]
      end

  end


  return merged_pattern

end


function pattern_controller.update_working_patterns()
  local selected_sequencer_pattern = program.get().selected_sequencer_pattern
  local sequencer_patterns = program.get_selected_sequencer_pattern().channels

  for c = 1, 16 do
    local trig_merge_mode = sequencer_patterns[c].trig_merge_mode
    local note_merge_mode = sequencer_patterns[c].note_merge_mode
    local velocity_merge_mode = sequencer_patterns[c].velocity_merge_mode
    local length_merge_mode = sequencer_patterns[c].length_merge_mode
    local working_pattern = pattern_controller.get_and_merge_patterns(c, trig_merge_mode, note_merge_mode, velocity_merge_mode, length_merge_mode)
    sequencer_patterns[c].working_pattern = working_pattern
  end
end

return pattern_controller
