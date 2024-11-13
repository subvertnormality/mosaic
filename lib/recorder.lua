local recorder = {}

local EVENT_TYPES = {
  NOTE_ADDED = "note_added",
  CHORD_ADDED = "chord_added"
}

-- State
local state = {
  event_history = {},
  current_event_index = 0
}

function recorder.init()
  state = {
    event_history = {},
    current_event_index = 0
  }
end

function recorder.add_chord(song_pattern, channel, step, notes, velocities, chord_degrees)
  while #state.event_history > state.current_event_index do
    table.remove(state.event_history)
  end
  
  local event = {
    type = EVENT_TYPES.CHORD_ADDED,
    data = {
      song_pattern = song_pattern,
      channel = channel,
      step = step,
      notes = notes,
      velocities = velocities,
      chord_degrees = chord_degrees
    }
  }
  
  -- Apply change directly
  record.set_step_trig_mask(song_pattern, channel, step, 1)
  record.set_step_note_mask(song_pattern, channel, step, notes[1])
  record.set_step_velocity_mask(song_pattern, channel, step, velocities[1])
  record.set_step_length_mask(song_pattern, channel, step, 1)
  -- Only set chord mask if there are chord degrees
  if chord_degrees and #chord_degrees > 0 then
    record.set_step_chord_mask(song_pattern, channel, step, chord_degrees)
  else
    record.set_step_chord_mask(song_pattern, channel, step, nil)
  end
  
  table.insert(state.event_history, event)
  state.current_event_index = state.current_event_index + 1
end

function recorder.add_note(song_pattern, channel, step, note, velocity)
  while #state.event_history > state.current_event_index do
    table.remove(state.event_history)
  end
  
  local event = {
    type = EVENT_TYPES.NOTE_ADDED,
    data = {
      song_pattern = song_pattern,
      channel = channel,
      step = step,
      note = note,
      velocity = velocity
    }
  }
  
  -- Apply change directly
  record.set_step_trig_mask(song_pattern, channel, step, 1)
  record.set_step_note_mask(song_pattern, channel, step, note)
  record.set_step_velocity_mask(song_pattern, channel, step, velocity)
  record.set_step_length_mask(song_pattern, channel, step, 1)
  -- Explicitly clear any chord mask when adding a single note
  record.set_step_chord_mask(song_pattern, channel, step, nil)
  
  table.insert(state.event_history, event)
  state.current_event_index = state.current_event_index + 1
end

function recorder.undo()
  if state.current_event_index > 0 then
    -- Get the event we're undoing
    local event = state.event_history[state.current_event_index]
    local data = event.data
    
    -- Clear just this step
    record.set_step_trig_mask(data.song_pattern, data.channel, data.step, nil)
    record.set_step_note_mask(data.song_pattern, data.channel, data.step, nil)
    record.set_step_velocity_mask(data.song_pattern, data.channel, data.step, nil)
    record.set_step_length_mask(data.song_pattern, data.channel, data.step, nil)
    if event.type == EVENT_TYPES.CHORD_ADDED then
      record.set_step_chord_mask(data.song_pattern, data.channel, data.step, nil)
    end
    
    -- If there's a previous event for this step, reapply it
    if state.current_event_index > 1 then
      for i = state.current_event_index - 1, 1, -1 do
        local prev_event = state.event_history[i]
        if prev_event.data.song_pattern == data.song_pattern and 
           prev_event.data.channel == data.channel and 
           prev_event.data.step == data.step then
          recorder.apply_event(prev_event)
          break
        end
      end
    end
    
    state.current_event_index = state.current_event_index - 1
  end
end

function recorder.redo()
  if state.current_event_index < #state.event_history then
    state.current_event_index = state.current_event_index + 1
    recorder.apply_event(state.event_history[state.current_event_index])
  end
end

function recorder.apply_event(event)
  if event.type == EVENT_TYPES.NOTE_ADDED then
    local data = event.data
    record.set_step_trig_mask(data.song_pattern, data.channel, data.step, 1)
    record.set_step_note_mask(data.song_pattern, data.channel, data.step, data.note)
    record.set_step_velocity_mask(data.song_pattern, data.channel, data.step, data.velocity)
    record.set_step_length_mask(data.song_pattern, data.channel, data.step, 1)
  elseif event.type == EVENT_TYPES.CHORD_ADDED then
    local data = event.data
    record.set_step_trig_mask(data.song_pattern, data.channel, data.step, 1)
    record.set_step_note_mask(data.song_pattern, data.channel, data.step, data.notes[1])
    record.set_step_velocity_mask(data.song_pattern, data.channel, data.step, data.velocities[1])
    record.set_step_length_mask(data.song_pattern, data.channel, data.step, 1)
    record.set_step_chord_mask(data.song_pattern, data.channel, data.step, data.chord_degrees)
  end
end

function recorder.get_state()
  return state
end

return recorder