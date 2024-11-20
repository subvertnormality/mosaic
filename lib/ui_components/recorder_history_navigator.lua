local recorder_history_navigator = {}
recorder_history_navigator.__index = recorder_history_navigator



function recorder_history_navigator:new(x, y, name)
  local self = setmetatable({}, recorder_history_navigator)
  self.x = x
  self.y = y
  self.name = name
  self.value = 0
  self.event_state = nil
  self.selected = false
  return self
end

function recorder_history_navigator:draw()
  if self.selected then
    screen.level(15)
  else
    screen.level(1)
  end
  screen.move(self.x, self.y)
  screen.move(self.x, self.y + 8)
  screen.font_size(10)
  screen.text(recorder.get_state().current_event_index)
  if self.event_state.events then
    for i, event in ipairs(self.event_state.events) do
      if event.type == "note_mask" then
        local note = event.data and event.data.event_data and event.data.event_data.note
        local length = event.data and event.data.event_data and event.data.event_data.length
        local velocity = event.data and event.data.event_data and event.data.event_data.velocity or 120
        local chord_degrees = event.data and event.data.event_data and event.data.event_data.chord_degrees
        screen.level(math.floor(velocity / 10) + 3)
        screen.move(self.x + 70 - (i * 5), self.y + 40 - ((note or 50) / 3))
        if note and note > -1 then
          screen.font_size(5)
          screen.font_face(60)
          screen.text("\u{286}")
          screen.font_face(1)
        elseif chord_degrees and fn.table_count(chord_degrees) > 0 then
          screen.text("'")
        elseif length then
          screen.text("l")
        end
      end
    end
  end
end

function recorder_history_navigator:select()
  self.selected = true
  fn.dirty_screen(true)
end

function recorder_history_navigator:deselect()
  self.selected = false
  fn.dirty_screen(true)
end

function recorder_history_navigator:is_selected()
  return self.selected
end

function recorder_history_navigator:get_value()
  return self.value
end

function recorder_history_navigator:set_value(v)
  self.value = v
  fn.dirty_screen(true)
end

function recorder_history_navigator:set_event_state(event_state)
  self.event_state = event_state
end

return recorder_history_navigator
