local memory = {}
memory.max_history_size = 50000

-- Cache table functions
local table_move = table.move

-- Validation functions
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
    if degree ~= nil then
      if type(degree) ~= "number" or degree < -14 or degree > 14 or seen[degree] then
        return false
      end
      seen[degree] = true
    end
  end
  return true
end

-- Event handlers
local event_handlers = {
  note_mask = {
    validate = function(data)
      if not validate_step(data.step) then return false end
      if not validate_note(data.note) then return false end
      if not validate_velocity(data.velocity) then return false end
      if not validate_length(data.length) then return false end
      if not validate_chord_degrees(data.chord_degrees) then return false end
      return true
    end,
    
    capture_state = function(channel, step)
      local working_pattern = channel.working_pattern
      local captured = {
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
    end,
    
    restore_state = function(channel, step, saved_state)
      if not saved_state then return end
      
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
    end,
    
    apply_event = function(channel, step, data, apply_type)

      -- Update provided values only
      if data.trig ~= nil then channel.step_trig_masks[step] = data.trig end
      if data.note ~= nil then channel.step_note_masks[step] = data.note end
      if data.velocity ~= nil then channel.step_velocity_masks[step] = data.velocity end
      if data.length ~= nil then channel.step_length_masks[step] = data.length end

      -- Handle chord degrees with partial updates
      if data.chord_degrees ~= nil then

        if fn.table_count(data.chord_degrees) > 0 then
          -- Initialize chord masks table if needed
          if not channel.step_chord_masks then 
            channel.step_chord_masks = {}
          end
          
          -- Initialize or preserve existing chord mask for this step
          if not channel.step_chord_masks[step] then
            channel.step_chord_masks[step] = {nil, nil, nil, nil}
          end
          
          -- Update only non-nil values while preserving others
          -- for i, degree in pairs(data.chord_degrees) do
          for i = 1, 4 do
            if data.chord_degrees[i] ~= nil then
              channel.step_chord_masks[step][i] = data.chord_degrees[i]
            elseif apply_type == "undo" and not data.chord_degrees[i] then
              channel.step_chord_masks[step][i] = nil
            end
          end
          
          -- Check if all values are nil
          local all_nil = true
          for _, v in pairs(channel.step_chord_masks[step]) do
            if v ~= nil then 
              all_nil = false
              break
            end
          end
          
          -- Clear chord if all values are nil
          if all_nil then
            channel.step_chord_masks[step] = nil
          end
        else
          -- Empty array means clear the chord
          channel.step_chord_masks[step] = nil
        end
      elseif channel.step_chord_masks and apply_type == "undo" then
        channel.step_chord_masks[step] = nil
      end
      
      -- Update working pattern with current values
      local working_trig = data.trig or channel.step_trig_masks[step] or 0
      local working_note = data.note or channel.step_note_masks[step] or 0
      local working_velocity = data.velocity or channel.step_velocity_masks[step] or 100
      local working_length = data.length or channel.step_length_masks[step] or 1

      program.update_working_pattern_for_step(channel, step, working_trig, working_note, working_velocity, working_length)
    end

  }
}

local function create_ring_buffer(max_size)
  local buffer = {
    buffer = {},
    start = 1,
    size = 0,
    max_size = max_size,
    total_size = 0,
    
    get_size = function(self)
      return self.size
    end,
    
    push = function(self, event)
      local index
      if self.size < self.max_size then
        self.size = self.size + 1
        index = self.size
      else
        index = self.start
        self.start = (self.start % self.max_size) + 1
      end
      
      self.buffer[index] = event
      self.total_size = self.total_size + 1
      return self.size
    end,
    
    get = function(self, position)
      if not position or position < 1 or position > self.size then
        return nil
      end
      
      local actual_pos = ((self.start + position - 2) % self.max_size) + 1
      if actual_pos <= 0 then 
        actual_pos = actual_pos + self.max_size 
      end
      
      return self.buffer[actual_pos]
    end,
    
    truncate = function(self, position)
      if position < self.size then
        self.size = position
        self.total_size = position  -- Update total size to match current size
      end
    end
  }
  return buffer
end

-- Main state structure
local state = {
  channels = {},
  current_indices = {},
  original_states = {}
}

function memory.init()
  state.channels = {}
  state.current_indices = {}
  state.original_states = {}
  state.pattern_states = {} 
end

local function get_channel_state(channel_number, pattern_number)
  if not state.pattern_states[pattern_number] then
    state.pattern_states[pattern_number] = {}
  end
  if not state.pattern_states[pattern_number][channel_number] then
    state.pattern_states[pattern_number][channel_number] = {
      step_masks = {},
      working_pattern = {}
    }
  end
  return state.pattern_states[pattern_number][channel_number]
end

local function get_channel_and_state(song_pattern, channel_number)
  if not state.pattern_states[song_pattern] then
    state.pattern_states[song_pattern] = {}
  end
  if not state.pattern_states[song_pattern][channel_number] then
    state.pattern_states[song_pattern][channel_number] = {
      working_pattern = {
        trig_values = {},
        note_mask_values = {},
        velocity_values = {},
        lengths = {}
      }
    }
  end
  
  local channel = program.get_channel(song_pattern, channel_number)
  local pattern_state = state.pattern_states[song_pattern][channel_number]
  
  return channel, pattern_state
end

function memory.record_event(channel_number, event_type, data)
  if not channel_number or not event_type or not event_handlers[event_type] then
    return
  end
  
  local handler = event_handlers[event_type]
  if not handler.validate(data) then
    return
  end
  
  -- Initialize channel state
  if not state.channels[channel_number] then
    state.channels[channel_number] = create_ring_buffer(memory.max_history_size)
    state.current_indices[channel_number] = 0
    state.original_states[channel_number] = {}
  end
  
  local song_pattern = data.song_pattern or program.get().selected_song_pattern
  local channel = program.get_channel(song_pattern, channel_number)
  
  -- Create unique step key that includes pattern
  local step_key = string.format("%d:%d", song_pattern, data.step)
  
  -- Capture original state if not already captured
  if not state.original_states[channel_number][step_key] then
    state.original_states[channel_number][step_key] = handler.capture_state(channel, data.step)
  end
  
  -- Create event
  local event = {
    type = event_type,
    data = {
      step = data.step,
      step_key = step_key,
      event_data = data,
      song_pattern = song_pattern,
      original_state = state.original_states[channel_number][step_key]
    }
  }
  
  -- Truncate and add event
  state.channels[channel_number]:truncate(state.current_indices[channel_number])
  local new_size = state.channels[channel_number]:push(event)
  state.current_indices[channel_number] = new_size
  
  -- Apply event
  handler.apply_event(channel, data.step, data, "record")
end

function memory.undo(channel_number)
  if not channel_number or not state.channels[channel_number] then return end
  
  local channel_events = state.channels[channel_number]
  local current_index = state.current_indices[channel_number]
  
  if current_index > 0 then
    local event = channel_events:get(current_index)
    if not event then return end
    
    local channel = program.get_channel(event.data.song_pattern, channel_number)
    local handler = event_handlers[event.type]
    
    -- Find previous event for same step & pattern
    local prev_event = nil
    for i = current_index - 1, 1, -1 do
      local candidate = channel_events:get(i)
      if candidate and 
         candidate.data.song_pattern == event.data.song_pattern and 
         candidate.data.step == event.data.step then
        prev_event = candidate
        break
      end
    end
    
    if prev_event then
      handler.apply_event(channel, event.data.step, prev_event.data.event_data, "undo")
    else
      handler.restore_state(channel, event.data.step, event.data.original_state)
    end
    
    state.current_indices[channel_number] = current_index - 1
  end
end

function memory.redo(channel_number)
  if not channel_number or not state.channels[channel_number] then return end
  
  if state.current_indices[channel_number] < state.channels[channel_number].total_size then
    state.current_indices[channel_number] = state.current_indices[channel_number] + 1
    local event = state.channels[channel_number]:get(state.current_indices[channel_number])
    
    local channel = program.get_channel(event.data.song_pattern, channel_number)
    local handler = event_handlers[event.type]
    
    handler.apply_event(channel, event.data.step, event.data.event_data, "redo")
  end
end

function memory.undo_all(channel_number)
  if not channel_number or not state.channels[channel_number] then return end
  
  local channel_events = state.channels[channel_number]
  local current_index = state.current_indices[channel_number]
  
  -- Track already restored states for each pattern to avoid duplicate restores
  local restored_states = {}
  
  -- Go through events in reverse order to get the latest state for each step
  for i = current_index, 1, -1 do
    local event = channel_events:get(i)
    if event then
      local step_key = string.format("%d:%d", event.data.song_pattern, event.data.step)
      if not restored_states[step_key] then
        local channel = program.get_channel(event.data.song_pattern, channel_number)
        local original_state = event.data.original_state
        
        if original_state then
          event_handlers.note_mask.restore_state(channel, event.data.step, original_state)
        else
          -- If no original state, clear the step
          event_handlers.note_mask.restore_state(channel, event.data.step, {
            trig_mask = nil,
            note_mask = nil,
            velocity_mask = nil,
            length_mask = nil,
            working_pattern = {
              trig_value = 0,
              note_value = 0,
              velocity_value = 100,
              length = 1
            }
          })
        end
        
        restored_states[step_key] = true
      end
    end
  end
  
  state.current_indices[channel_number] = 0
end

function memory.redo_all(channel_number)
  if not channel_number or not state.channels[channel_number] then return end
  
  local channel_events = state.channels[channel_number]
  if not channel_events.total_size or channel_events.total_size == 0 then return end
  
  -- Find latest event for each step per pattern
  local latest_events = {}
  
  for i = state.current_indices[channel_number] + 1, channel_events.total_size do
    local event = channel_events:get(i)
    if event then
      local step_key = string.format("%d:%d", event.data.song_pattern, event.data.step)
      latest_events[step_key] = event
    end
  end
  
  -- Apply latest events
  for _, event in pairs(latest_events) do
    local channel = program.get_channel(event.data.song_pattern, channel_number)
    event_handlers.note_mask.apply_event(channel, event.data.step, event.data.event_data, "redo")
  end
  
  state.current_indices[channel_number] = channel_events.total_size
end

function memory.reset()
  -- Clear histories but keep structure
  for channel_number, channel_events in pairs(state.channels) do
    state.channels[channel_number] = create_ring_buffer(memory.max_history_size)
    state.current_indices[channel_number] = 0
    state.original_states[channel_number] = {}
  end
end

function memory.clear(channel_number)
  if not channel_number or not state.channels[channel_number] then return end
  
  state.channels[channel_number] = create_ring_buffer(memory.max_history_size)
  state.current_indices[channel_number] = 0
  state.original_states[channel_number] = {}
end

function memory.get_event_count(channel_number)
  if not channel_number or not state.channels[channel_number] then return 0 end
  return state.current_indices[channel_number] or 0
end

function memory.get_total_event_count(channel_number)
  if not channel_number or not state.channels[channel_number] then return 0 end
  local channel_events = state.channels[channel_number]
  return channel_events and channel_events.total_size or 0
end

function memory.get_recent_events(channel_number, count)
  count = count or 5
  local events = {}
  
  if channel_number and state.channels[channel_number] then
    local channel_events = state.channels[channel_number]
    local current_idx = state.current_indices[channel_number]
    
    for i = current_idx, math.max(1, current_idx - count + 1), -1 do
      local event = channel_events:get(i)
      if event then
        table.insert(events, event)
      end
    end
  end
  
  return events
end

function memory.get_state(channel_number)
  if not channel_number then
    return {
      channels = state.channels,
      current_indices = state.current_indices,
      original_states = state.original_states
    }
  end
  
  return {
    event_history = state.channels[channel_number] or create_ring_buffer(memory.max_history_size),
    current_event_index = state.current_indices[channel_number] or 0,
    pattern_channels = {} -- Kept for backwards compatibility
  }
end

return memory