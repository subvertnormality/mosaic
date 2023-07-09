local pattern_controller = {}

-- Merge strategies

-- - Col 12: Numbered merge mode, 
-- - Col 13: Skip merge mode,
-- - Col 14: Add merge mode, 
-- - Col 15: Sub merge mode, 
-- - Col 16: Round robin merge mode.

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

  for _, pattern_number in pairs(program.sequencer_patterns[selected_sequencer_pattern].channels[channel].selected_patterns) do
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
      elseif merge_mode == "add" then

        if pattern.trig_values[s] == 1 then
          merged_pattern.trig_values[s] = 1
          merged_pattern.note_values[s] = merged_pattern.note_values[s] + pattern.note_values[s]
          merged_pattern.lengths[s] = merged_pattern.lengths[s] + pattern.lengths[s]
          merged_pattern.velocity_values[s] = merged_pattern.velocity_values[s] + pattern.velocity_values[s]
        end
      elseif merge_mode == "sub" then

        if pattern.trig_values[s] == 1 then
          merged_pattern.trig_values[s] = 1
          merged_pattern.note_values[s] = merged_pattern.note_values[s] - pattern.note_values[s]
          merged_pattern.lengths[s] = merged_pattern.lengths[s] - pattern.lengths[s]
          merged_pattern.velocity_values[s] = merged_pattern.velocity_values[s] - pattern.velocity_values[s]

          if merged_pattern.note_values[s] < 0 then
            merged_pattern.note_values[s] = 0
          end
          if merged_pattern.lengths[s] < 1 then
            merged_pattern.lengths[s] = 1
          end
          if merged_pattern.velocity_values[s] < 0 then
            merged_pattern.velocity_values[s] = 0
          end

        end
      elseif not string.match(merge_mode, "pattern_number_") then
        if pattern.trig_values[s] == 1 then
          merged_pattern.trig_values[s] = 1
        end
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