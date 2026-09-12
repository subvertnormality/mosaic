-- Song selection, boundary dispatch and pending command ownership.
-- Dependencies already bound by step stay bound; UI/runtime globals retain their
-- existing lookup timing. Public step facades remain available to callers.
local song_transition = {}

function song_transition.new(program, m_clock, step)
local transition = {}
local ipairs = ipairs
local table = table
local switch_to_next_song_pattern_func = function() end
local switch_to_next_song_pattern_blink_cancel_func = function() end
local next_song_pattern_queue = nil
local pattern_change_queue = {}

function transition.calculate_next_selected_song_pattern()
  local program_data = program.get()
  local selected_song_pattern_number = program_data.selected_song_pattern
  local current_song_pattern = program.get_selected_song_pattern()
  local song_patterns = program_data.song_patterns

  -- If there's a queued pattern number, use that
  if next_song_pattern_queue then
    return next_song_pattern_queue
  end

  -- If song mode is not active, stay on the current pattern
  if params:get("song_mode") ~= 2 then
    return selected_song_pattern_number
  end

  -- Get current repeat count and total repeats needed
  local repeat_count = program.get_repeat_count() or 1
  local total_repeats = current_song_pattern.repeats or 1
  
  -- Check if we're already at the end of the current pattern
  -- If we are, then we should find the next pattern regardless of repeat count
  local at_end_of_pattern = step.at_end_of_current_song_pattern(current_song_pattern)
  
  -- If we haven't completed all repeats AND not at end of pattern, stay on the current pattern
  if repeat_count < total_repeats and not at_end_of_pattern then
    return selected_song_pattern_number
  end

  -- Find the next active song pattern
  local next_pattern_number = selected_song_pattern_number + 1

  -- If a valid next pattern exists, use it
  if next_pattern_number < 97 and 
     song_patterns[next_pattern_number] and 
     song_patterns[next_pattern_number].active then
    return next_pattern_number
  end

  -- If no valid next pattern, wrap around to the first active pattern
  local first_active_pattern = selected_song_pattern_number
  while first_active_pattern > 1 and 
        song_patterns[first_active_pattern - 1] and 
        song_patterns[first_active_pattern - 1].active do
    first_active_pattern = first_active_pattern - 1
  end

  return first_active_pattern
end

function transition.process_elektron_program_change(next_song_pattern)
  for i = 1, 16 do
    local channel = program.get_channel(program.get().selected_song_pattern, i)
    local device = device_map.get_device(program.get().devices[i].device_map)
    
    if device.id == "digitone" or 
      device.id == "digitakt" or 
      device.id == "digitakt_2" or 
      device.id == "syntakt" or 
      device.id == "analog_rytm" or 
      device.id == "analog_four" or 
      device.id == "oktatrack" or
      device.id == "analog_heat_1" or    
      device.id == "analog_heat_2" or
      device.id == "model_samples" or
      device.id == "analog_cycles" 
    then

      -- Each Elektron channel's own output device receives the change.
      local midi_device = program.get().devices[i].midi_device

      m_midi:program_change(next_song_pattern - 1, params:get("elektron_program_change_channel"), midi_device)

    end
  end
  
end

function transition.queue_next_song_pattern(s)
  next_song_pattern_queue = s
end

function transition.queue_for_pattern_change(func)
  table.insert(pattern_change_queue, func)
end

function transition.at_end_of_current_song_pattern(song_pattern)
  -- Calculate the total length of the pattern including all repeats
  local total_length = song_pattern.global_pattern_length * song_pattern.repeats
  local global_step = program.get().global_step_accumulator
  
  local is_end = global_step > 0 and global_step % total_length == 0
  
  -- We're at the end of the pattern if:
  -- 1. We've progressed past the initialization (global_step > 0)
  -- 2. We've completed exactly all repeats (global_step is divisible by the total length)
  return is_end
end

function transition.process_song_song_patterns()
  local selected_song_pattern_number = program.get().selected_song_pattern
  local selected_song_pattern = program.get().song_patterns[selected_song_pattern_number]
  local global_step_accumulator = program.get().global_step_accumulator

  -- Check if we've completed one full global pattern length cycle
  if global_step_accumulator > 0 and 
     global_step_accumulator % selected_song_pattern.global_pattern_length == 0 then
    
    switch_to_next_song_pattern_func()
    switch_to_next_song_pattern_blink_cancel_func()
    switch_to_next_song_pattern_func = function() end
    -- With song mode off the queued switch above is the whole manual change;
    -- a retained queue would redirect the first transition after re-enabling.
    if params:get("song_mode") ~= 2 then
      next_song_pattern_queue = nil
    end
    
    -- Execute any queued pattern change functions
    for i, func in ipairs(pattern_change_queue) do
      func()
    end
    
    -- Align shuffle values for all channels
    for channel_number = 1, 16 do
      channel_edit_page_ui.align_global_and_local_swing_shuffle_type_values(channel_number)
      channel_edit_page_ui.align_global_and_local_swing_values(channel_number)
      channel_edit_page_ui.align_global_and_local_shuffle_feel_values(channel_number)
      channel_edit_page_ui.align_global_and_local_shuffle_basis_values(channel_number)
      channel_edit_page_ui.align_global_and_local_shuffle_amount_values(channel_number)
    end
    
    pattern_change_queue = {}

    -- Update repeat count
    local current_repeat = program.get_repeat_count() or 1
    local max_repeats = selected_song_pattern.repeats or 1
    
    -- Check if we've reached the end of all repeats
    if step.at_end_of_current_song_pattern(selected_song_pattern) then
      -- We've completed all repeats, going to next pattern
      program.set_repeat_count(1)
      
      -- Only change patterns if in song mode
      if params:get("song_mode") == 2 then
        -- Calculate the next pattern to use
        local next_song_pattern = step.calculate_next_selected_song_pattern()
        next_song_pattern_queue = nil

        -- Switch to the next pattern
        program.set_selected_song_pattern(next_song_pattern)
        if selected_song_pattern_number ~= next_song_pattern then
          -- Slides never cross song patterns; a same-pattern repeat may wrap.
          m_clock.cancel_all_spread_actions()
        end
        
        -- Handle pattern reset based on settings
        local reset_channels = selected_song_pattern_number ~= next_song_pattern and
          params:get("reset_on_song_pattern_transition") == 2 or
          params:get("reset_on_end_of_pattern_repeat") == 2
        if reset_channels then
          step.reset_pattern()
        end
        
        pattern.update_working_patterns()

        -- Update all channel settings if we've changed song patterns
        if selected_song_pattern_number ~= next_song_pattern then
          for channel_number = 1, 17 do
            local channel = program.get_channel(program.get().selected_song_pattern, channel_number)
            m_clock.set_channel_division(channel_number, m_clock.calculate_divisor(channel.clock_mods))
            if channel_number ~= 17 then
              channel_edit_page_ui.align_global_and_local_shuffle_feel_values(channel_number)
              channel_edit_page_ui.align_global_and_local_swing_values(channel_number)
              channel_edit_page_ui.align_global_and_local_swing_shuffle_type_values(channel_number)
              channel_edit_page_ui.align_global_and_local_shuffle_basis_values(channel_number)
              channel_edit_page_ui.align_global_and_local_shuffle_amount_values(channel_number)
            end
          end
        
          channel_edit_page_ui.refresh_clock_mods()
          channel_edit_page_ui.refresh_swing()
          channel_edit_page_ui.refresh_swing_shuffle_type()
          channel_edit_page_ui.refresh_shuffle_feel()
          channel_edit_page_ui.refresh_shuffle_basis()
          channel_edit_page_ui.refresh_shuffle_amount()
          song_edit_page.refresh()
          channel_edit_page.refresh()
        end
        
        -- Retain channel phase for evolving polyrhythms when resets are off.
        if reset_channels then
          m_clock.realign_sprockets()
        end
      end
    else
      -- Not at the end of all repeats yet, increment repeat count if needed
      if current_repeat < max_repeats then
        program.set_repeat_count(current_repeat + 1)
      end
    end
  end
end

function transition.queue_switch_to_next_song_pattern_func(func)
  switch_to_next_song_pattern_func = func
end

function transition.queue_switch_to_next_song_pattern_blink_cancel_func(func)
  switch_to_next_song_pattern_blink_cancel_func = func
end

function transition.execute_blink_cancel_func()
  switch_to_next_song_pattern_blink_cancel_func()
  switch_to_next_song_pattern_blink_cancel_func = function()
  end
end

function transition.clear_pending()
  next_song_pattern_queue = nil
  switch_to_next_song_pattern_func = function() end
  pattern_change_queue = {}
end

return transition
end

return song_transition
