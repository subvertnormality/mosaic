local memory_history_navigator = {}
memory_history_navigator.__index = memory_history_navigator



function memory_history_navigator:new(x, y, name)
  local self = setmetatable({}, memory_history_navigator)
  self.x = x
  self.y = y
  self.name = name
  self.current_index = 0
  self.max_index = 0
  self.event_state = nil
  self.selected = false
  return self
end

function memory_history_navigator:draw()
  if self.selected then
    screen.level(15)
  else
    screen.level(1)
  end
  screen.move(self.x, self.y + 5)
  screen.font_size(10)
  screen.text(self.current_index)
  screen.move(self.x, self.y + 17)
  screen.font_size(8)
  screen.text("of")
  screen.move(self.x, self.y + 31)
  screen.font_size(10)
  screen.text(self.max_index)
  
  if self.event_state.events then
    -- Initialize an array to store fixed y positions
    local fixed_y_positions = {}
    local last_valid_y_pos = 60  -- Default value if no valid note is found
    
    -- First pass: determine fixed y positions for all events
    for i = #self.event_state.events, 1, -1 do  -- Scan backwards
      local event = self.event_state.events[i]
      if event.type == "note_mask" then
        local note = event.data and event.data.event_data and event.data.event_data.note
        if note and note > -1 then
          fixed_y_positions[i] = note
          last_valid_y_pos = note
        else
          fixed_y_positions[i] = last_valid_y_pos
        end
      end
    end
    
    -- Second pass: draw using fixed positions
    for i, event in ipairs(self.event_state.events) do
      if i > 15 then
        break
      end
      local y_pos = fixed_y_positions[i] or last_valid_y_pos  -- Fallback to last_valid_y_pos if nil
      screen.font_size(5)
      screen.font_face(60)

      if event.type == "note_mask" then
        local note = event.data and event.data.event_data and event.data.event_data.note
        local length = event.data and event.data.event_data and event.data.event_data.length
        local velocity = event.data and event.data.event_data and event.data.event_data.velocity or 120
        local chord_degrees = event.data and event.data.event_data and event.data.event_data.chord_degrees
        
        if y_pos then  -- Safety check
          screen.level(math.floor(velocity / 10) + 3)
          screen.move(self.x + 120 - (i * 5), self.y + 40 - (y_pos / 3))
          if note and note > -1 then
            screen.text("\u{286}")
          elseif chord_degrees and fn.table_count(chord_degrees) > 0 then
            screen.text("'")
          elseif length then
            screen.text(".")
          end
        end
      elseif event.type == "trig_lock" then
        local y_pos = fixed_y_positions[i] or last_valid_y_pos  -- Fallback to last_valid_y_pos if nil
        if y_pos then
          screen.level(15)
          screen.move(self.x + 120 - (i * 5), self.y + 40 - (y_pos / 3))
          screen.text("T")
        end
      end
      screen.font_face(1)
      screen.font_size(8)
    end
  end
end

function memory_history_navigator:select()
  self.selected = true
  fn.dirty_screen(true)
end

function memory_history_navigator:deselect()
  self.selected = false
  fn.dirty_screen(true)
end

function memory_history_navigator:is_selected()
  return self.selected
end

function memory_history_navigator:get_current_index()
  return self.current_index
end

function memory_history_navigator:set_current_index(v)
  self.current_index = v or 0
  fn.dirty_screen(true)
end

function memory_history_navigator:get_max_index()
  return self.max_index
end

function memory_history_navigator:set_max_index(v)
  self.max_index = v or 0
  fn.dirty_screen(true)
end

function memory_history_navigator:set_event_state(event_state)
  self.event_state = event_state
end

return memory_history_navigator
