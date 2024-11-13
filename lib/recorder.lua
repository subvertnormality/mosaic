local recorder = {}

local EVENT_TYPES = {
  NOTE_ADDED = "note_added",
  CHORD_ADDED = "chord_added"
}

local state = {
  event_history = {},
  current_event_index = 0,
  original_states = {} -- Will store original state of modified steps
}

local function capture_step_state(channel, step)
  return {
    channel_number = channel.number,
    step = step,
    trig_mask = channel.step_trig_masks[step],
    note_mask = channel.step_note_masks[step],
    velocity_mask = channel.step_velocity_masks[step],
    length_mask = channel.step_length_masks[step],
    chord_mask = channel.step_chord_masks and channel.step_chord_masks[step]
  }
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
    channel.step_chord_masks[saved_state.step] = saved_state.chord_mask
  else
    if channel.step_chord_masks then
      channel.step_chord_masks[saved_state.step] = nil
    end
  end
end

function recorder.init()
  state = {
    event_history = {},
    current_event_index = 0,
    original_states = {}
  }
end

function recorder.add_note(channel, step, note, velocity, song_pattern)
  -- Use current selected pattern if none specified
  song_pattern = song_pattern or program.get().selected_sequencer_pattern
  
  -- Create key that includes song pattern
  local step_key = string.format("%d_%d_%d", song_pattern, channel.number, step)
  
  if not state.original_states[step_key] then
    state.original_states[step_key] = capture_step_state(channel, step)
  end
  
  while #state.event_history > state.current_event_index do
    table.remove(state.event_history)
  end
  
  local event = {
    type = EVENT_TYPES.NOTE_ADDED,
    data = {
      channel_number = channel.number,
      song_pattern = song_pattern,
      step = step,
      note = note,
      velocity = velocity,
      original_state = state.original_states[step_key]
    }
  }
  
  -- Apply change directly
  channel.step_trig_masks[step] = 1
  channel.step_note_masks[step] = note
  channel.step_velocity_masks[step] = velocity
  channel.step_length_masks[step] = 1
  channel.step_chord_masks[step] = nil
  
  table.insert(state.event_history, event)
  state.current_event_index = state.current_event_index + 1
end

function recorder.add_chord(channel, step, notes, velocities, chord_degrees, song_pattern)
  -- Use current selected pattern if none specified
  song_pattern = song_pattern or program.get().selected_sequencer_pattern
  
  -- Capture original state if this is the first modification to this step
  local step_key = string.format("%d_%d_%d", song_pattern, channel.number, step)
  if not state.original_states[step_key] then
    state.original_states[step_key] = capture_step_state(channel, step)
  end
  
  while #state.event_history > state.current_event_index do
    table.remove(state.event_history)
  end
  
  local event = {
    type = EVENT_TYPES.CHORD_ADDED,
    data = {
      channel_number = channel.number,
      song_pattern = song_pattern,
      step = step,
      notes = notes,
      velocities = velocities,
      chord_degrees = chord_degrees,
      original_state = state.original_states[step_key]
    }
  }
  
  -- Apply change directly
  channel.step_trig_masks[step] = 1
  channel.step_note_masks[step] = notes[1]
  channel.step_velocity_masks[step] = velocities[1]
  channel.step_length_masks[step] = 1
  if chord_degrees and #chord_degrees > 0 then
    if not channel.step_chord_masks then
      channel.step_chord_masks = {}
    end
    channel.step_chord_masks[step] = chord_degrees
  else
    if channel.step_chord_masks then
      channel.step_chord_masks[step] = nil
    end
  end
  
  table.insert(state.event_history, event)
  state.current_event_index = state.current_event_index + 1
end

function recorder.undo()
  if state.current_event_index > 0 then
    local event = state.event_history[state.current_event_index]
    -- Use the song pattern from the event data
    local channel = program.get_channel(event.data.song_pattern, event.data.channel_number)
    local step = event.data.step
    
    -- Find the most recent previous event for this step, if any
    local prev_event = nil
    for i = state.current_event_index - 1, 1, -1 do
      if state.event_history[i].data.channel_number == event.data.channel_number and 
         state.event_history[i].data.song_pattern == event.data.song_pattern and  -- Add pattern check
         state.event_history[i].data.step == step then
        prev_event = state.event_history[i]
        break
      end
    end
    
    if prev_event then
      -- Apply the previous event
      if prev_event.type == EVENT_TYPES.NOTE_ADDED then
        channel.step_trig_masks[step] = 1
        channel.step_note_masks[step] = prev_event.data.note
        channel.step_velocity_masks[step] = prev_event.data.velocity
        channel.step_length_masks[step] = 1
        if channel.step_chord_masks then
          channel.step_chord_masks[step] = nil
        end
      elseif prev_event.type == EVENT_TYPES.CHORD_ADDED then
        channel.step_trig_masks[step] = 1
        channel.step_note_masks[step] = prev_event.data.notes[1]
        channel.step_velocity_masks[step] = prev_event.data.velocities[1]
        channel.step_length_masks[step] = 1
        if prev_event.data.chord_degrees and #prev_event.data.chord_degrees > 0 then
          if not channel.step_chord_masks then
            channel.step_chord_masks = {}
          end
          channel.step_chord_masks[step] = prev_event.data.chord_degrees
        end
      end
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
    -- Use the song pattern from the event data
    local channel = program.get_channel(event.data.song_pattern, event.data.channel_number)
    
    if event.type == EVENT_TYPES.NOTE_ADDED then
      channel.step_trig_masks[event.data.step] = 1
      channel.step_note_masks[event.data.step] = event.data.note
      channel.step_velocity_masks[event.data.step] = event.data.velocity
      channel.step_length_masks[event.data.step] = 1
      if channel.step_chord_masks then
        channel.step_chord_masks[event.data.step] = nil
      end
    elseif event.type == EVENT_TYPES.CHORD_ADDED then
      channel.step_trig_masks[event.data.step] = 1
      channel.step_note_masks[event.data.step] = event.data.notes[1]
      channel.step_velocity_masks[event.data.step] = event.data.velocities[1]
      channel.step_length_masks[event.data.step] = 1
      if event.data.chord_degrees and #event.data.chord_degrees > 0 then
        if not channel.step_chord_masks then
          channel.step_chord_masks = {}
        end
        channel.step_chord_masks[event.data.step] = event.data.chord_degrees
      end
    end
  end
end

function recorder.get_state()
  return state
end

return recorder