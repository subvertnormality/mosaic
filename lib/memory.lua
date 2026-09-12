local memory = {}
memory.max_history_size = 5000

local history_ring = include("mosaic/lib/history_ring")
local event_handlers = include("mosaic/lib/memory/event_handlers").new(program, fn)

-- Main state structure

local state

function memory.bind_project(project_memory)
  project_memory.channels = project_memory.channels or {}
  project_memory.current_indices = project_memory.current_indices or {}
  project_memory.original_states = project_memory.original_states or {}
  project_memory.pattern_states = project_memory.pattern_states or {}
  state = project_memory
end

memory.bind_project(program.get().memory)

function memory.init()
  local mem = program.get().memory
  mem.channels = {}
  mem.current_indices = {}
  mem.original_states = {}
  mem.pattern_states = {}
  
  -- Clear any existing state when initializing
  memory.bind_project(mem)
end

if not state.channels and not state.current_indices and not state.original_states then
  memory.init()
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

function memory.record_event_for_target(song_pattern, channel_number, event_type, data)

  if not channel_number or not event_type or not event_handlers[event_type] then
    return
  end
  
  local handler = event_handlers[event_type]
  if not handler.validate(data) then
    return
  end

  if not state.channels[channel_number] then
    state.channels[channel_number] = history_ring.new(memory.max_history_size)
    state.current_indices[channel_number] = 0
    state.original_states[channel_number] = {}
  end

  local channel = program.get_channel(song_pattern, channel_number)
  
  local state_key
  if event_type == "trig_lock" then
    state_key = string.format("%d:%d:%s", song_pattern, data.step, data.parameter)
  else
    state_key = string.format("%d:%d", song_pattern, data.step)
  end
  
  if not state.original_states[channel_number][state_key] then
    state.original_states[channel_number][state_key] = handler.capture_state(channel, data)
  end

  -- Prefer the logical post-state of the preceding retained event for this key. This
  -- repairs externally corrupted current tables in the same way as historical replay,
  -- while still retaining the exact floor after older events roll out of the ring.
  local prior_state = handler.capture_state(channel, data)
  for i = state.current_indices[channel_number], 1, -1 do
    local previous = state.channels[channel_number]:get(i)
    if previous and previous.type == event_type and previous.data.step_key == state_key then
      if previous.data.result_state ~= nil then prior_state = fn.deep_copy(previous.data.result_state) end
      break
    end
  end
  
  local event = {
    type = event_type,
    data = {
      step = data.step,
      step_key = state_key,
      event_data = data,
      song_pattern = song_pattern,
      original_state = state.original_states[channel_number][state_key],
      -- The state immediately before this retained event is the undo floor if older
      -- history rolls out of the bounded ring. It also makes ordinary undo exact and
      -- constant-time. `original_state` remains for loading older serialized histories.
      prior_state = prior_state
    }
  }
  
  state.channels[channel_number]:truncate(state.current_indices[channel_number])
  local new_size = state.channels[channel_number]:push(event)
  state.current_indices[channel_number] = new_size
  
  handler.apply_event(channel, data.step, data, "record")
  event.data.result_state = handler.capture_state(channel, data)
end

function memory.record_event(channel_number, event_type, data)
  if not channel_number or not event_type or not event_handlers[event_type] then
    return
  end
  if not event_handlers[event_type].validate(data) then
    return
  end

  local song_pattern = data.song_pattern or program.get().selected_song_pattern
  return memory.record_event_for_target(song_pattern, channel_number, event_type, data)
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
    
    -- New histories carry the exact state before each event. Legacy serialized histories
    -- fall back to replaying from their saved original state.
    if event.data.prior_state ~= nil then
      handler.restore_state(channel, event.data, event.data.prior_state)
    else
      handler.restore_state(channel, event.data, event.data.original_state)
      for i = 1, current_index - 1 do
        local candidate = channel_events:get(i)
        if candidate and candidate.type == event.type and candidate.data.step_key == event.data.step_key then
          handler.apply_event(channel, candidate.data.step, candidate.data.event_data, "redo")
        end
      end
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
  local restored_states = {}

  -- Restore the state immediately before each key's oldest retained event. For legacy
  -- histories every event has the same first-ever original state, so the fallback keeps
  -- their prior behavior.
  for i = 1, current_index do
    local event = channel_events:get(i)
    if event then
      local event_key
      if event.type == "trig_lock" then
        event_key = string.format("%d:%d:%s", event.data.song_pattern, event.data.step, event.data.event_data.parameter)
      else
        event_key = event.data.step_key
      end
      if not restored_states[event_key] then
        local channel = program.get_channel(event.data.song_pattern, channel_number)
        local handler = event_handlers[event.type]
        handler.restore_state(channel, event.data, event.data.prior_state or event.data.original_state)
        restored_states[event_key] = true
      end
    end
  end
  
  state.current_indices[channel_number] = 0
end

function memory.redo_all(channel_number)
  if not channel_number or not state.channels[channel_number] then return end
  
  local channel_events = state.channels[channel_number]
  if not channel_events.total_size or channel_events.total_size == 0 then return end
  
  -- Combine events for each step 
  local combined_events = {}
  
  for i = state.current_indices[channel_number] + 1, channel_events.total_size do
    local event = channel_events:get(i)
    if event then
      local event_key
      if event.type == "trig_lock" then
        event_key = string.format("%d:%d:%s", event.data.song_pattern, event.data.step, event.data.event_data.parameter)
      else
        event_key = string.format("%d:%d", event.data.song_pattern, event.data.step)
      end
      
      if not combined_events[event_key] then
        combined_events[event_key] = {
          type = event.type,
          data = {
            step = event.data.step,
            song_pattern = event.data.song_pattern,
            event_data = fn.deep_copy(event.data.event_data)
          }
        }
      else
        -- Merge event data. Chord degrees merge voice by voice, as apply_event does, so a
        -- later chord edit on the step does not drop an earlier one (S57).
        local merged = combined_events[event_key].data.event_data
        for k, v in pairs(event.data.event_data) do
          if k == "chord_degrees" and type(v) == "table" and type(merged.chord_degrees) == "table" then
            for i = 1, 4 do
              if v[i] ~= nil then merged.chord_degrees[i] = v[i] end
            end
          else
            merged[k] = v
          end
        end
      end
    end
  end
  
  -- Apply combined events
  for _, event in pairs(combined_events) do
    local channel = program.get_channel(event.data.song_pattern, channel_number)
    local handler = event_handlers[event.type]
    handler.apply_event(channel, event.data.step, event.data.event_data, "redo")
  end
  
  state.current_indices[channel_number] = channel_events.total_size
end

function memory.reset()
  -- Clear histories but keep structure
  for channel_number, _ in pairs(state.channels) do
    memory.clear(channel_number)
  end
end

function memory.clear(channel_number)
  if not channel_number or not state.channels[channel_number] then return end
  
  state.channels[channel_number] = history_ring.new(memory.max_history_size)
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
    event_history = state.channels[channel_number] or history_ring.new(memory.max_history_size),
    current_event_index = state.current_indices[channel_number] or 0,
    pattern_channels = {} -- Kept for backwards compatibility
  }
end

-- Add these functions to the memory module
function memory.serialize_state()
  local serialized = {
    channels = {},
    current_indices = state.current_indices,
    original_states = state.original_states,
    pattern_states = state.pattern_states
  }
  
  -- Serialize each channel's ring buffer
  for channel_number, channel_buffer in pairs(state.channels) do
    serialized.channels[channel_number] = history_ring.serialize(channel_buffer)
  end
  
  return serialized
end

function memory.deserialize_state(saved_state)
  if not saved_state then return end
  
  -- Restore the simple data
  state.current_indices = saved_state.current_indices or {}
  state.original_states = saved_state.original_states or {}
  state.pattern_states = saved_state.pattern_states or {}
  
  -- Deserialize each channel's ring buffer
  state.channels = {}
  for channel_number, channel_data in pairs(saved_state.channels or {}) do
    state.channels[channel_number] = history_ring.deserialize(channel_data, memory.max_history_size)
  end
end

return memory