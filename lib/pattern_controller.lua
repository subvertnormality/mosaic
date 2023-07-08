local pattern_controller = {}

function pattern_controller:merge_patterns(merged_pattern, pattern, merge_mode)
  local selected_sequencer_pattern = program.selected_sequencer_pattern
  for s = 1, 64 do

    if merge_mode == "skip" then
      if pattern[s] == 1 and merged_pattern[s] < 1 then
        merged_pattern[s] = 1
      elseif pattern[s] == 1 and merged_pattern[s] == 1 then
        merged_pattern[s] = 0
      end
    else
      if pattern[s] == 1 then
        merged_pattern[s] = 1
      end
    end
  end

  return merged_pattern
  
end

function pattern_controller:get_and_merge_patterns(channel, merge_mode)

  local selected_sequencer_pattern = program.selected_sequencer_pattern
  local merged_pattern = initialise_64_table(0)

  for pattern in pairs(program.sequencer_patterns[selected_sequencer_pattern].channels[channel].selected_patterns) do
    merged_pattern = pattern_controller:merge_patterns(merged_pattern, program.sequencer_patterns[selected_sequencer_pattern].patterns[pattern].trig_values, merge_mode)
  end

  return merged_pattern
end

function pattern_controller:merge_lengths(merged_lengths, lengths, merge_mode)

  for s = 1, 64 do

    if merge_mode == "skip" then
      if lengths[s] >= 1 and merged_lengths[s] < 2 then
        merged_lengths[s] = 1
      end
    else
      if lengths[s] >= 1 then
        merged_lengths[s] = lengths[s]
      end
    end
  end

  return merged_lengths
  
end

function pattern_controller:get_and_merge_lengths(channel, merge_mode)

  local selected_sequencer_pattern = program.selected_sequencer_pattern
  local merged_lengths = initialise_64_table(-1)

  -- TODO: implement merge strategies

  for pattern in pairs(program.sequencer_patterns[selected_sequencer_pattern].channels[channel].selected_patterns) do
    merged_lengths = pattern_controller:merge_lengths(merged_lengths, program.sequencer_patterns[selected_sequencer_pattern].patterns[pattern].lengths)
  end

  
  return merged_lengths
end

function pattern_controller:update_working_patterns()
  local selected_sequencer_pattern = program.selected_sequencer_pattern

  for c = 1, 16 do
    local merge_mode = program.sequencer_patterns[selected_sequencer_pattern].channels[c].merge_mode
    local trigs = pattern_controller:get_and_merge_patterns(c, merge_mode)
    local lengths = pattern_controller:get_and_merge_lengths(c, merge_mode)
    program.sequencer_patterns[selected_sequencer_pattern].channels[c].working_pattern.trig_values = trigs
    program.sequencer_patterns[selected_sequencer_pattern].channels[c].working_pattern.lengths = lengths
  end

end

return pattern_controller