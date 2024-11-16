local recorder = {}

local MAX_HISTORY_SIZE = 50000

-- Cache table functions
local table_move = table.move

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

local event_handlers = {
  note_mask = {
    validate = function(data)
      if not (type(data.step) == "number" and data.step > 0 and data.step == math.floor(data.step)) then
        return false
      end
      
      -- Validate note if provided
      if data.note ~= nil and not (type(data.note) == "number" and data.note >= 0 and data.note <= 127) then
        return false
      end
      
      -- Validate velocity if provided
      if data.velocity ~= nil and not (type(data.velocity) == "number" and data.velocity >= 0 and data.velocity <= 127) then
        return false
      end
      
      -- Validate length if provided
      if data.length ~= nil and not (type(data.length) == "number" and data.length > 0) then
        return false
      end
      
      -- Validate chord degrees if provided
      if data.chord_degrees ~= nil then
        if type(data.chord_degrees) ~= "table" then return false end
        local seen = {}
        for _, degree in ipairs(data.chord_degrees) do
          if type(degree) ~= "number" or degree < 1 or degree > 7 or seen[degree] then
            return false
          end
          seen[degree] = true
        end
      end

      return true
    end,
    
    capture_state = function(channel, step)
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
    end,
    
    restore_state = function(channel, step, saved_state)
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
    end,
    
    apply_event = function(channel, step, data, apply_type)
      -- Always set trig mask
      channel.step_trig_masks[step] = 1
      
      -- Update provided values only
      if data.note ~= nil then channel.step_note_masks[step] = data.note end
      if data.velocity ~= nil then channel.step_velocity_masks[step] = data.velocity end
      if data.length ~= nil then channel.step_length_masks[step] = data.length end

      -- Handle chord degrees explicitly
      if data.chord_degrees ~= nil then
        if #data.chord_degrees > 0 then
          if not channel.step_chord_masks then channel.step_chord_masks = {} end
          channel.step_chord_masks[step] = table_move(data.chord_degrees, 1, #data.chord_degrees, 1, {})
        else
          if channel.step_chord_masks then
            channel.step_chord_masks[step] = nil
          end
        end
      elseif channel.step_chord_masks and apply_type == "undo" then
        channel.step_chord_masks[step] = nil
      end
      
      -- Update working pattern with current values
      local working_note = data.note or channel.step_note_masks[step] or 0
      local working_velocity = data.velocity or channel.step_velocity_masks[step] or 100
      local working_length = data.length or channel.step_length_masks[step] or 1
      program.update_working_pattern_for_step(channel, step, working_note, working_velocity, working_length)
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
    
    push = function(self, event)
      local index
      local did_wrap = false
      
      if self.size < self.max_size then
        self.size = self.size + 1
        index = self.size
      else
        did_wrap = true
        index = self.start
        self.start = (self.start % self.max_size) + 1
      end
    
      self.buffer[index] = event
      self.total_size = self.total_size + 1
      return self.size, did_wrap
    end,
    
    get = function(self, position)
      if position and position > 0 and position <= self.size then
        local actual_pos = ((self.start + position - 2) % self.max_size) + 1
        return self.buffer[actual_pos]
      end
      return nil
    end,
    
    get_size = function(self)
      return self.size
    end,
    
    truncate = function(self, position)
      if position < self.size then
        self.size = position
        self.total_size = position
      end
    end
  }
  return buffer
end

local function update_step_index(index, step, event_idx, is_wrap)
  if is_wrap then
    local step_events = index.step_to_events[step]
    if step_events and #step_events > 0 then
      table.remove(step_events, 1)
    end
  end
  
  if not index.step_to_events[step] then
    index.step_to_events[step] = {}
  end
  
  table.insert(index.step_to_events[step], event_idx)
  index.event_to_step[event_idx] = step
  index.last_event[step] = event_idx
end

-- Index structures to optimize traversal
local function create_step_index()
  return {
    step_to_events = {}, -- Maps steps to event indices
    event_to_step = {},  -- Maps event indices to steps
    last_event = {}      -- Maps steps to their last event index
  }
end

local function reset_step_indices(pc_state)
  pc_state.step_indices = create_step_index()
  for i = 1, pc_state.event_history.size do
    local event = pc_state.event_history:get(i)
    update_step_index(pc_state.step_indices, event.data.step, i)
  end
end

-- Pre-allocate common tables
local empty_table = {}
local default_working_pattern = {
  trig_value = 0,
  note_value = 0,
  velocity_value = 100,
  length = 1
}

local pattern_key_cache = {}
local pattern_key_format = "%d_%d"

local function get_pattern_key(song_pattern, channel_number)
  local cache_key = song_pattern * 1000 + channel_number
  local key = pattern_key_cache[cache_key]
  if not key then
    key = string.format(pattern_key_format, song_pattern, channel_number)
    pattern_key_cache[cache_key] = key
  end
  return key
end

local function find_previous_event(index, step, current_idx)
  local step_events = index.step_to_events[step]
  if not step_events then return nil end
  
  -- Binary search for the insertion point of current_idx
  local left, right = 1, #step_events
  while left <= right do
    local mid = math.floor((left + right) / 2)
    if step_events[mid] < current_idx then
      if mid == #step_events or step_events[mid + 1] >= current_idx then
        return step_events[mid]
      end
      left = mid + 1
    else
      right = mid - 1
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

local function update_chord_mask(dest_chord, src_chord)
  if not src_chord then 
    return nil
  end
  if not dest_chord then
    dest_chord = {}
  end
  
  -- Use table.move for bulk array copy
  return table_move(src_chord, 1, #src_chord, 1, dest_chord)
end

-- Main state table with optimized indexing
local state = {
  pattern_channels = {},
  event_history = create_ring_buffer(MAX_HISTORY_SIZE),
  current_event_index = 0,
  global_index = create_step_index()
}

function recorder.init()
  state.pattern_channels = {}
  state.event_history = create_ring_buffer(MAX_HISTORY_SIZE)
  state.current_event_index = 0
  state.global_index = create_step_index()
end

function recorder.record_event(channel, event_type, data)
  if not (channel and event_type and event_handlers[event_type]) then
    return
  end
  
  local handler = event_handlers[event_type]
  if not handler.validate(data) then
    return
  end
  
  local song_pattern = data.song_pattern or program.get().selected_sequencer_pattern
  local pc_key = get_pattern_key(song_pattern, channel.number)
  local pc_state = state.pattern_channels[pc_key]
  
  if not pc_state then
    pc_state = {
      event_history = create_ring_buffer(MAX_HISTORY_SIZE),
      current_index = 0,
      step_indices = create_step_index(),
      original_states = {}
    }
    state.pattern_channels[pc_key] = pc_state
  end

  local step_key = tostring(data.step)
  if not pc_state.original_states[step_key] then
    pc_state.original_states[step_key] = handler.capture_state(channel, data.step)
  end

  -- Truncate future events
  state.event_history:truncate(state.current_event_index)
  pc_state.event_history:truncate(pc_state.current_index)

  -- Create and add event
  local event = {
    type = event_type,
    data = {
      channel_number = channel.number,
      song_pattern = song_pattern,
      step = data.step,
      event_data = data,
      original_state = pc_state.original_states[step_key]
    }
  }

  local new_size, did_wrap = state.event_history:push(event)
  state.current_event_index = new_size
  update_step_index(state.global_index, data.step, state.current_event_index, did_wrap)

  local pc_new_size, pc_did_wrap = pc_state.event_history:push(event)
  pc_state.current_index = pc_new_size
  update_step_index(pc_state.step_indices, data.step, pc_state.current_index, pc_did_wrap)

  -- Apply the event
  handler.apply_event(channel, data.step, data, "record")
end

function recorder.undo(sequencer_pattern, channel_number)

  if sequencer_pattern and channel_number then
    local pc_key = get_pattern_key(sequencer_pattern, channel_number)
    local pc_state = state.pattern_channels[pc_key]

    if pc_state and pc_state.current_index > 0 then
      local event = pc_state.event_history:get(pc_state.current_index)
      local channel = program.get_channel(sequencer_pattern, channel_number)
      local handler = event_handlers[event.type]
      
      if handler then
        local prev_index = find_previous_event(pc_state.step_indices, event.data.step, pc_state.current_index)
        
        if prev_index then
          local prev_event = pc_state.event_history:get(prev_index)
          handler.apply_event(channel, event.data.step, prev_event.data.event_data, "undo")
        else
          handler.restore_state(channel, event.data.step, event.data.original_state)
        end
        
        pc_state.current_index = pc_state.current_index - 1
        if state.event_history:get(state.current_event_index) == event then
          state.current_event_index = state.current_event_index - 1
        end
      end
    end
    return
  end

  if state.current_event_index > 0 then
    local event = state.event_history:get(state.current_event_index)
    state.current_event_index = state.current_event_index - 1
    recorder.undo(event.data.song_pattern, event.data.channel_number)
  end
end

function recorder.redo(sequencer_pattern, channel_number)
  if sequencer_pattern and channel_number then
    local pc_key = get_pattern_key(sequencer_pattern, channel_number)
    local pc_state = state.pattern_channels[pc_key]
    
    if pc_state and pc_state.current_index < pc_state.event_history.total_size then
      pc_state.current_index = pc_state.current_index + 1
      local event = pc_state.event_history:get(pc_state.current_index)
      
      if event then
        local channel = program.get_channel(sequencer_pattern, channel_number)
        local handler = event_handlers[event.type]
        
        if handler then
          handler.apply_event(channel, event.data.step, event.data.event_data, "redo")
          
          if state.event_history:get(state.current_event_index + 1) == event then
            state.current_event_index = state.current_event_index + 1
          end
        end
      end
    end
    return
  end

  if state.current_event_index < state.event_history.total_size then
    state.current_event_index = state.current_event_index + 1
    local event = state.event_history:get(state.current_event_index)
    if event then
      recorder.redo(event.data.song_pattern, event.data.channel_number)
    end
  end
end

function recorder.undo_all(sequencer_pattern, channel_number)
  if sequencer_pattern and channel_number then
    local pc_key = get_pattern_key(sequencer_pattern, channel_number)
    local pc_state = state.pattern_channels[pc_key]
    
    if pc_state then
      local channel = program.get_channel(sequencer_pattern, channel_number)
      
      -- Get handler from first event (they should all be same type)
      local event = pc_state.event_history:get(1)
      if event then
        local handler = event_handlers[event.type]
        -- Restore to original state for each modified step
        for step_key, original_state in pairs(pc_state.original_states) do
          handler.restore_state(channel, step_key, original_state)
        end
      end
      
      -- Reset current index
      pc_state.current_index = 0
      
      -- Update global index if needed
      if state.current_event_index > 0 then
        state.current_event_index = 0
      end
    end
    return
  end

  -- If no pattern/channel specified, undo all patterns
  state.current_event_index = 0
  for pc_key, pc_state in pairs(state.pattern_channels) do
    local pattern, channel = pc_key:match("(%d+)_(%d+)")
    recorder.undo_all(tonumber(pattern), tonumber(channel))
  end
end

function recorder.redo_all(sequencer_pattern, channel_number)
  if sequencer_pattern and channel_number then
    local pc_key = get_pattern_key(sequencer_pattern, channel_number)
    local pc_state = state.pattern_channels[pc_key]
    
    if pc_state and pc_state.event_history.total_size > 0 then
      local channel = program.get_channel(sequencer_pattern, channel_number)
      local handler = event_handlers["note_mask"]
      
      -- Find latest event for each step from current_index to total_size
      local step_latest_events = {}
      for i = pc_state.current_index + 1, pc_state.event_history.total_size do
        local event = pc_state.event_history:get(i)
        step_latest_events[event.data.step] = event
      end
      
      -- Apply latest events
      for _, event in pairs(step_latest_events) do
        handler.apply_event(channel, event.data.step, event.data.event_data, "redo")
      end
      
      -- Update indices
      pc_state.current_index = pc_state.event_history.total_size
      
      -- Update global index if needed
      local final_event = pc_state.event_history:get(pc_state.event_history.total_size)
      if final_event and state.event_history:get(state.current_event_index + 1) == final_event then
        state.current_event_index = state.event_history.total_size
      end
    end
    return
  end

  -- If no pattern/channel specified, redo all patterns
  for pc_key, pc_state in pairs(state.pattern_channels) do
    local pattern, channel = pc_key:match("(%d+)_(%d+)")
    recorder.redo_all(tonumber(pattern), tonumber(channel))
  end
end

function recorder.reset()
  -- Clear event histories and indices
  state.event_history = create_ring_buffer(MAX_HISTORY_SIZE)
  state.current_event_index = 0
  state.global_index = create_step_index()
  
  -- Clear pattern channel histories but maintain pattern/channel structure
  for pattern_key, pc_state in pairs(state.pattern_channels) do
    pc_state.event_history = create_ring_buffer(MAX_HISTORY_SIZE)
    pc_state.current_index = 0
    pc_state.step_indices = create_step_index()
    
    -- Current state becomes the new original state
    pc_state.original_states = {}
  end
end

function recorder.get_event_count(song_pattern, channel_number)
  local pc_key = get_pattern_key(song_pattern, channel_number)
  local pc_state = state.pattern_channels[pc_key]
  
  if pc_state then
    return pc_state.current_index
  end
  return 0
end

function recorder.get_state()
  return {
    pattern_channels = state.pattern_channels,
    current_event_index = state.current_event_index,
    global_index = state.global_index,
    event_history = state.event_history 
  }
end

return recorder