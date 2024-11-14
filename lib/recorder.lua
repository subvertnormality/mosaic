local recorder = {}

local state = {
  event_history = {},
  current_event_index = 0,
  original_states = {}
}

function recorder.init()
  state = {
    event_history = {},
    current_event_index = 0,
    original_states = {}
  }
end

local function capture_step_state(channel, step)
  local captured = {
    channel_number = channel.number,
    step = step,
    trig_mask = channel.step_trig_masks[step],
    note_mask = channel.step_note_masks[step],
    velocity_mask = channel.step_velocity_masks[step],
    length_mask = channel.step_length_masks[step],
    -- Capture working pattern state
    working_pattern = {
      trig_value = channel.working_pattern.trig_values[step],
      note_value = channel.working_pattern.note_values[step],
      velocity_value = channel.working_pattern.velocity_values[step],
      length = channel.working_pattern.lengths[step]
    }
  }
  
  if channel.step_chord_masks and channel.step_chord_masks[step] then
    captured.chord_mask = fn.deep_copy(channel.step_chord_masks[step])
  end
  
  return captured
end

local function restore_step_state(channel, saved_state)
  channel.step_trig_masks[saved_state.step] = saved_state.trig_mask
  channel.step_note_masks[saved_state.step] = saved_state.note_mask
  channel.step_velocity_masks[saved_state.step] = saved_state.velocity_mask
  channel.step_length_masks[saved_state.step] = saved_state.length_mask
  
  if saved_state.chord_mask then
    if not channel.step_chord_masks then
      channel.step_chord_masks = {}
    end
    channel.step_chord_masks[saved_state.step] = fn.deep_copy(saved_state.chord_mask)
  else
    if channel.step_chord_masks then
      channel.step_chord_masks[saved_state.step] = nil
    end
  end
  
  -- Restore working pattern state
  channel.working_pattern.trig_values[saved_state.step] = saved_state.working_pattern.trig_value
  channel.working_pattern.note_values[saved_state.step] = saved_state.working_pattern.note_value
  channel.working_pattern.velocity_values[saved_state.step] = saved_state.working_pattern.velocity_value
  channel.working_pattern.lengths[saved_state.step] = saved_state.working_pattern.length
end


function recorder.add_step(channel, step, note, velocity, chord_degrees, song_pattern)
  -- Use current selected pattern if none specified
  song_pattern = song_pattern or program.get().selected_sequencer_pattern
  
  -- Generate unique key for this step
  local step_key = string.format("%d_%d_%d", song_pattern, channel.number, step)
  
  -- Capture original state if this is the first modification to this step
  if not state.original_states[step_key] then
    state.original_states[step_key] = capture_step_state(channel, step)
  end
  
  -- Clear any redo history
  while #state.event_history > state.current_event_index do
    table.remove(state.event_history)
  end
  
  -- Create new event
  local event = {
    type = chord_degrees and #chord_degrees > 0,
    data = {
      channel_number = channel.number,
      song_pattern = song_pattern,
      step = step,
      note = note,
      velocity = velocity,
      chord_degrees = chord_degrees,  -- Remove deep_copy
      original_state = state.original_states[step_key]
    }
  }
  
  -- Apply the change to masks
  channel.step_trig_masks[step] = 1
  channel.step_note_masks[step] = note
  channel.step_velocity_masks[step] = velocity
  channel.step_length_masks[step] = 1
  
  if chord_degrees and #chord_degrees > 0 then
    if not channel.step_chord_masks then
      channel.step_chord_masks = {}
    end
    channel.step_chord_masks[step] = chord_degrees  -- Remove deep_copy
  else
    if channel.step_chord_masks then
      channel.step_chord_masks[step] = nil
    end
  end
  
  -- Update working pattern
  program.update_working_pattern_for_step(channel, step, note, velocity, 1)
  
  -- Add to history
  table.insert(state.event_history, event)
  state.current_event_index = state.current_event_index + 1
end

function recorder.undo()
  if state.current_event_index > 0 then
    local event = state.event_history[state.current_event_index]
    local channel = program.get_channel(event.data.song_pattern, event.data.channel_number)
    local step = event.data.step
    
    -- Find the most recent previous event for this step/pattern/channel
    local prev_event = nil
    for i = state.current_event_index - 1, 1, -1 do
      local e = state.event_history[i]
      if e.data.channel_number == event.data.channel_number and
         e.data.song_pattern == event.data.song_pattern and
         e.data.step == step then
        prev_event = e
        break
      end
    end
    
    if prev_event then
      -- Restore the previous event's state directly (remove capture_step_state call)
      channel.step_trig_masks[step] = 1
      channel.step_note_masks[step] = prev_event.data.note
      channel.step_velocity_masks[step] = prev_event.data.velocity
      channel.step_length_masks[step] = 1
      
      if prev_event.data.chord_degrees and #prev_event.data.chord_degrees > 0 then
        if not channel.step_chord_masks then
          channel.step_chord_masks = {}
        end
        channel.step_chord_masks[step] = fn.deep_copy(prev_event.data.chord_degrees)
      else
        if channel.step_chord_masks then
          channel.step_chord_masks[step] = nil
        end
      end
      
      -- Update working pattern to match previous event
      program.update_working_pattern_for_step(channel, step, prev_event.data.note, prev_event.data.velocity, 1)
    else
      -- No previous event, restore original state
      restore_step_state(channel, event.data.original_state)
    end
    
    state.current_event_index = state.current_event_index - 1
  end
end

function recorder.redo()
  if state.current_event_index < #state.event_history then
    state.current_event_index = state.current_event_index + 1
    local event = state.event_history[state.current_event_index]
    local channel = program.get_channel(event.data.song_pattern, event.data.channel_number)
    local step = event.data.step
    
    -- Apply the event's changes
    channel.step_trig_masks[step] = 1
    channel.step_note_masks[step] = event.data.note
    channel.step_velocity_masks[step] = event.data.velocity
    channel.step_length_masks[step] = 1
    
    if event.data.chord_degrees and #event.data.chord_degrees > 0 then
      if not channel.step_chord_masks then
        channel.step_chord_masks = {}
      end
      channel.step_chord_masks[step] = event.data.chord_degrees  -- Remove deep_copy
    else
      if channel.step_chord_masks then
        channel.step_chord_masks[step] = nil
      end
    end
    
    -- Update working pattern to match restored state
    program.update_working_pattern_for_step(
      channel,
      step,
      event.data.note,
      event.data.velocity,
      1
    )
  end
end

function recorder.get_state()
  return state
end

return recorder