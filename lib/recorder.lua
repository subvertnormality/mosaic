local recorder = {}

-- Pre-allocate common tables
local empty_table = {}
local default_working_pattern = {
  trig_value = 0,
  note_value = 0,
  velocity_value = 100,
  length = 1
}

-- Cache table functions
local table_move = table.move

-- Index structures to optimize traversal
local function create_step_index()
  return {
    step_to_events = {}, -- Maps steps to event indices
    event_to_step = {},  -- Maps event indices to steps
    last_event = {}      -- Maps steps to their last event index
  }
end

local function update_step_index(index, step, event_idx)
  if not index.step_to_events[step] then
    index.step_to_events[step] = {}
  end
  table.insert(index.step_to_events[step], event_idx)
  index.event_to_step[event_idx] = step
  index.last_event[step] = event_idx
end

local function find_previous_event(index, step, current_idx)
  local step_events = index.step_to_events[step]
  if not step_events then return nil end
  
  for i = #step_events, 1, -1 do
    if step_events[i] < current_idx then
      return step_events[i]
    end
  end
  return nil
end

local function capture_step_state(channel, step)
  local working_pattern = channel.working_pattern
  local captured = {
    channel_number = channel.number,
    step = step,
    trig_mask = channel.step_trig_masks[step],
    note_mask = channel.step_note_masks[step],
    velocity_mask = channel.step_velocity_masks[step], 
    length_mask = channel.step_length_masks[step],
    working_pattern = {
      trig_value = working_pattern.trig_values[step] or 0,
      note_value = working_pattern.note_mask_values[step] or 0,
      velocity_value = working_pattern.velocity_values[step] or 100,
      length = working_pattern.lengths[step] or 1
    }
  }

  if channel.step_chord_masks and channel.step_chord_masks[step] then
    local chord = channel.step_chord_masks[step]
    captured.chord_mask = table_move(chord, 1, #chord, 1, {})
  end

  return captured
end

local function restore_step_state(channel, saved_state)
  if not saved_state then return end
  
  local step = saved_state.step
  local working_pattern = channel.working_pattern
  
  -- Batch assignment of masks
  channel.step_trig_masks[step] = saved_state.trig_mask
  channel.step_note_masks[step] = saved_state.note_mask  
  channel.step_velocity_masks[step] = saved_state.velocity_mask
  channel.step_length_masks[step] = saved_state.length_mask

  -- Handle chord state
  if saved_state.chord_mask then
    if not channel.step_chord_masks then channel.step_chord_masks = {} end
    channel.step_chord_masks[step] = table_move(saved_state.chord_mask, 1, #saved_state.chord_mask, 1, {})
  else
    if channel.step_chord_masks then
      channel.step_chord_masks[step] = nil
    end
  end

  -- Batch restore working pattern
  local saved_wp = saved_state.working_pattern
  working_pattern.trig_values[step] = saved_wp.trig_value
  working_pattern.note_mask_values[step] = saved_wp.note_value
  working_pattern.velocity_values[step] = saved_wp.velocity_value
  working_pattern.lengths[step] = saved_wp.length
end

local function validate_step(step)
  return type(step) == "number" and step > 0 and step == math.floor(step)
end

local function validate_note(note)
  return note == nil or (type(note) == "number" and note >= 0 and note <= 127)
end

local function validate_velocity(velocity) 
  return velocity == nil or (type(velocity) == "number" and velocity >= 0 and velocity <= 127)
end

local function validate_length(length)
  return length == nil or (type(length) == "number" and length >= 0)
end

local function validate_chord_degrees(degrees)
  if degrees == nil then return true end
  if type(degrees) ~= "table" then return false end
  
  local seen = {}
  for _, degree in ipairs(degrees) do
    if type(degree) ~= "number" or degree < 1 or degree > 7 or seen[degree] then
      return false
    end
    seen[degree] = true
  end
  return true
end

-- Main state table with optimized indexing
local state = {
  pattern_channels = {},
  event_history = {},
  current_event_index = 0,
  global_index = create_step_index()
}

function recorder.init()
  state.pattern_channels = {}
  state.event_history = {}
  state.current_event_index = 0
  state.global_index = create_step_index()
end

function recorder.add_step(channel, step, note, velocity, length, chord_degrees, song_pattern)
  -- Fast validation
  if not (channel and validate_step(step) and validate_note(note) and 
          validate_velocity(velocity) and validate_length(length) and 
          validate_chord_degrees(chord_degrees)) then
    return
  end

  song_pattern = song_pattern or program.get().selected_sequencer_pattern
  
  local pc_key = song_pattern .. "_" .. channel.number
  local pc_state = state.pattern_channels[pc_key]
  
  if not pc_state then
    pc_state = {
      event_history = {},
      current_index = 0,
      step_indices = create_step_index(),
      original_states = {}
    }
    state.pattern_channels[pc_key] = pc_state
  end

  local step_key = tostring(step)
  if not pc_state.original_states[step_key] then
    pc_state.original_states[step_key] = capture_step_state(channel, step)
  end

  -- Truncate future events
  if #state.event_history > state.current_event_index then
    for i = state.current_event_index + 1, #state.event_history do
      state.event_history[i] = nil
    end
  end
  
  if #pc_state.event_history > pc_state.current_index then
    for i = pc_state.current_index + 1, #pc_state.event_history do
      pc_state.event_history[i] = nil  
    end
  end

  -- Create event with minimal copying
  local event = {
    data = {
      channel_number = channel.number,
      song_pattern = song_pattern,
      step = step,
      note = note,
      velocity = velocity,
      length = length,
      chord_degrees = chord_degrees and #chord_degrees > 0 
        and table_move(chord_degrees, 1, #chord_degrees, 1, {}) 
        or chord_degrees,  -- preserve nil vs {} distinction
      original_state = pc_state.original_states[step_key]
    }
  }

  pc_state.current_index = pc_state.current_index + 1
  pc_state.event_history[pc_state.current_index] = event
  state.event_history[state.current_event_index + 1] = event
  state.current_event_index = state.current_event_index + 1

  -- Update indices
  update_step_index(pc_state.step_indices, step, pc_state.current_index)
  update_step_index(state.global_index, step, state.current_event_index)

  -- Only update channel state for non-nil values
  channel.step_trig_masks[step] = 1
  if note ~= nil then channel.step_note_masks[step] = note end
  if velocity ~= nil then channel.step_velocity_masks[step] = velocity end
  if length ~= nil then channel.step_length_masks[step] = length end

  -- Update chord state only if explicitly provided
  if chord_degrees ~= nil then
    if chord_degrees and #chord_degrees > 0 then
      if not channel.step_chord_masks then channel.step_chord_masks = {} end
      channel.step_chord_masks[step] = table_move(chord_degrees, 1, #chord_degrees, 1, {})
    else
      if channel.step_chord_masks then
        channel.step_chord_masks[step] = nil
      end
    end
  end

  -- Use existing values for nil parameters in working pattern update
  local working_note = note or channel.step_note_masks[step] or 0
  local working_velocity = velocity or channel.step_velocity_masks[step] or 100
  local working_length = length or channel.step_length_masks[step] or 1
  program.update_working_pattern_for_step(channel, step, working_note, working_velocity, working_length)
end

function recorder.undo(sequencer_pattern, channel_number)
  if sequencer_pattern and channel_number then
    local pc_key = sequencer_pattern .. "_" .. channel_number
    local pc_state = state.pattern_channels[pc_key]
    
    if pc_state and pc_state.current_index > 0 then
      local event = pc_state.event_history[pc_state.current_index]
      local channel = program.get_channel(sequencer_pattern, channel_number)
      local step = event.data.step

      local prev_index = find_previous_event(pc_state.step_indices, step, pc_state.current_index)

      if prev_index then
        local prev_event = pc_state.event_history[prev_index]
        channel.step_trig_masks[step] = 1
        channel.step_note_masks[step] = prev_event.data.note or channel.step_note_masks[step]
        channel.step_velocity_masks[step] = prev_event.data.velocity or channel.step_velocity_masks[step]
        channel.step_length_masks[step] = prev_event.data.length or channel.step_length_masks[step]

        if prev_event.data.chord_degrees then
          if not channel.step_chord_masks then channel.step_chord_masks = {} end
          if not channel.step_chord_masks[step] then channel.step_chord_masks[step] = {} end

          channel.step_chord_masks[step][1] = prev_event.data.chord_degrees[1] or channel.step_chord_masks[step][1] 
          channel.step_chord_masks[step][2] = prev_event.data.chord_degrees[2] or channel.step_chord_masks[step][2]
          channel.step_chord_masks[step][3] = prev_event.data.chord_degrees[3] or channel.step_chord_masks[step][3]
          channel.step_chord_masks[step][4] = prev_event.data.chord_degrees[4] or channel.step_chord_masks[step][4]

        elseif channel.step_chord_masks then
          channel.step_chord_masks[step] = nil
        end

        program.update_working_pattern_for_step(
          channel, 
          step,
          prev_event.data.note or channel.step_note_masks[step],
          prev_event.data.velocity or channel.step_velocity_masks[step],
          prev_event.data.length or channel.step_length_masks[step]
        )
      else
        restore_step_state(channel, event.data.original_state)
      end

      pc_state.current_index = pc_state.current_index - 1
      if state.event_history[state.current_event_index] == event then
        state.current_event_index = state.current_event_index - 1
      end
    end
    return
  end

  if state.current_event_index > 0 then
    local event = state.event_history[state.current_event_index]
    state.current_event_index = state.current_event_index - 1
    recorder.undo(event.data.song_pattern, event.data.channel_number)
  end
end

function recorder.redo(sequencer_pattern, channel_number)
  if sequencer_pattern and channel_number then
    local pc_key = sequencer_pattern .. "_" .. channel_number
    local pc_state = state.pattern_channels[pc_key]
    
    if pc_state and pc_state.current_index < #pc_state.event_history then
      pc_state.current_index = pc_state.current_index + 1
      local event = pc_state.event_history[pc_state.current_index]
      local channel = program.get_channel(sequencer_pattern, channel_number)
      local step = event.data.step

      channel.step_trig_masks[step] = 1
      channel.step_note_masks[step] = event.data.note or channel.step_note_masks[step]
      channel.step_velocity_masks[step] = event.data.velocity or channel.step_velocity_masks[step]
      channel.step_length_masks[step] = event.data.length or channel.step_length_masks[step]

      if event.data.chord_degrees then
        if not channel.step_chord_masks then channel.step_chord_masks = {} end
        if not channel.step_chord_masks[step] then channel.step_chord_masks[step] = {} end
        channel.step_chord_masks[step][1] = event.data.chord_degrees[1] or channel.step_chord_masks[step][1]
        channel.step_chord_masks[step][2] = event.data.chord_degrees[2] or channel.step_chord_masks[step][2]
        channel.step_chord_masks[step][3] = event.data.chord_degrees[3] or channel.step_chord_masks[step][3]
        channel.step_chord_masks[step][4] = event.data.chord_degrees[4] or channel.step_chord_masks[step][4]
      end

      program.update_working_pattern_for_step(
        channel,
        step,
        event.data.note or channel.step_note_masks[step],
        event.data.velocity or channel.step_velocity_masks[step],
        event.data.length or channel.step_length_masks[step]
      )

      if state.event_history[state.current_event_index + 1] == event then
        state.current_event_index = state.current_event_index + 1
      end
    end
    return
  end

  if state.current_event_index < #state.event_history then
    state.current_event_index = state.current_event_index + 1
    local event = state.event_history[state.current_event_index]
    recorder.redo(event.data.song_pattern, event.data.channel_number)
  end
end

function recorder.get_event_count(sequencer_pattern, channel_number)
  local pc_key = sequencer_pattern .. "_" .. channel_number
  local pc_state = state.pattern_channels[pc_key]
  
  if not pc_state then
    return 0
  end
  
  return pc_state.current_index
end

function recorder.get_state()
  return state
end

return recorder