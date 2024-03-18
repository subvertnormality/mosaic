local pattern_controller = {}

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

  local notes = program.initialise_64_table({})
  local lengths = program.initialise_64_table({})
  local velocities = program.initialise_64_table({})

  for i = 1, 64 do
    notes[i] = {}
    lengths[i] = {}
    velocities[i] = {}
  end

  function do_moded_merge(pattern_number, is_pattern_trig_one, s, mode, values, merged_values, pushed_values)

    if mode and string.match(mode, "pattern_number_") then
      if mode == "pattern_number_" .. pattern_number then
        merged_values[s] = values[s]
      end
    elseif mode == "up" or mode == "down" or mode == "average" then
      if is_pattern_trig_one then
        table.insert(pushed_values[s], values[s])
      end
    end

  end

  for pattern_number, pattern_enabled in pairs(pattern_channel.selected_patterns) do
    if (pattern_enabled) then
      local pattern = patterns[pattern_number]
      for s = 1, 64 do
        local is_pattern_trig_one = pattern.trig_values[s] == 1

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

        do_moded_merge(pattern_number, is_pattern_trig_one, s, note_merge_mode, patterns[pattern_number].note_values, merged_pattern.note_values, notes)
        do_moded_merge(pattern_number, is_pattern_trig_one, s, velocity_merge_mode, patterns[pattern_number].velocity_values, merged_pattern.velocity_values, velocities)
        do_moded_merge(pattern_number, is_pattern_trig_one, s, length_merge_mode, patterns[pattern_number].lengths, merged_pattern.lengths, lengths)

      end
    end

  end

  for s = 1, 64 do
    table.sort(notes[s])
    table.sort(lengths[s])
    table.sort(velocities[s])

    function do_mode_calculation(mode, values, merged_values)
      if mode == "up" or mode == "down" or mode == "average" then
        if values[s][1] == nil then 
          merged_values[s] = 0
        elseif fn.table_has_one_item(values[s]) then
          merged_values[s] = values[s][1]
        elseif mode == "up" then
          merged_values[s] = (fn.average_table_values(values[s]) - values[s][1]) + values[s][#values[s]]
        elseif mode == "down" then
          merged_values[s] = values[s][1] - ((fn.average_table_values(values[s]) - values[s][1]))
        elseif mode == "average" then
          merged_values[s] = fn.average_table_values(values[s])
        end
      end
    end

    do_mode_calculation(note_merge_mode, notes, merged_pattern.note_values)
    do_mode_calculation(velocity_merge_mode, velocities, merged_pattern.velocity_values)
    do_mode_calculation(length_merge_mode, lengths, merged_pattern.lengths)

  end

  return merged_pattern

end


function pattern_controller.update_working_patterns()
  local selected_sequencer_pattern = program.get().selected_sequencer_pattern
  local sequencer_patterns = program.get_selected_sequencer_pattern().channels

  for c = 1, 16 do
    local merge_mode = sequencer_patterns[c].merge_mode
    local working_pattern = pattern_controller.get_and_merge_patterns(c, merge_mode)
    sequencer_patterns[c].working_pattern = working_pattern
  end
end

return pattern_controller
