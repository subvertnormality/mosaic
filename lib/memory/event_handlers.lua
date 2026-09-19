local memory_event_handlers = {}

function memory_event_handlers.new(program, fn)
-- Cache table functions
local table_move = table.move

-- Validation functions
local function validate_step(step)
  return type(step) == "number" and step > 0 and step == math.floor(step)
end

local function validate_note(note)
  return note == nil or (type(note) == "number" and note >= 0 and note <= 127)
end

-- CLEAR (-1) is X on the Masks page: a trig or velocity step lock turned back to X is cleared,
-- exactly as if it had never been set (human decision S24, bugs.json mask-off-stored-as-minus-one).
local CLEAR = -1

local function validate_velocity(velocity) 
  return velocity == nil or velocity == CLEAR or (type(velocity) == "number" and velocity >= 0 and velocity <= 127)
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
    
    capture_state = function(channel, data)
      local step = data.step
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
    
    restore_state = function(channel, data, saved_state)

      local step = data.step
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

      -- Update provided values only; CLEAR removes a trig or velocity lock
      local trig, velocity = data.trig, data.velocity
      if trig == CLEAR then trig = nil; channel.step_trig_masks[step] = nil end
      if velocity == CLEAR then velocity = nil; channel.step_velocity_masks[step] = nil end
      if trig ~= nil then channel.step_trig_masks[step] = trig end
      if data.note ~= nil then channel.step_note_masks[step] = data.note end
      if velocity ~= nil then channel.step_velocity_masks[step] = velocity end
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
      local working_trig = trig or channel.step_trig_masks[step] or 0
      local working_note = data.note or channel.step_note_masks[step] or 0
      local working_velocity = velocity or channel.step_velocity_masks[step] or 100
      local working_length = data.length or channel.step_length_masks[step] or 1

      program.update_working_pattern_for_step(channel, step, working_trig, working_note, working_velocity, working_length)
    end

  },
  trig_lock = {
    validate = function(data)
      if not validate_step(data.step) then return false end
      if data.parameter == nil then return false end
      return true
    end,
    
    capture_state = function(channel, data)
      local step = data.step
      local parameter = data.parameter
      return {
        value = program.get_step_param_trig_lock(channel, step, parameter),
        parameter = parameter,
        step = step
      }
    end,
    
    restore_state = function(channel, data, saved_state)
      local step = data.step
      if not saved_state then return end
      
      if saved_state.value then
        program.add_step_param_trig_lock_to_channel(channel, step, saved_state.parameter, saved_state.value)
      else
        program.clear_trig_lock_for_step_for_channel(channel, step, saved_state.parameter)
      end
    end,
    
    apply_event = function(channel, step, data, apply_type)
      if data.value then
        program.add_step_param_trig_lock_to_channel(channel, step, data.parameter, data.value)
      else
        program.clear_trig_lock_for_step_for_channel(channel, step, data.parameter)
      end
    end
  }
}

  return event_handlers
end

return memory_event_handlers
