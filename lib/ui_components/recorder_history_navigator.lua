local recorder_history_navigator = {}
recorder_history_navigator.__index = recorder_history_navigator



function recorder_history_navigator:new(x, y, name)
  local self = setmetatable({}, recorder_history_navigator)
  self.x = x
  self.y = y
  self.name = name
  self.value = 0
  -- self.max = max
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
  -- recorder.get_state().event_history.buffer[4].type
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

function recorder_history_navigator:increment()
  self.value = self.value + 1
  if self.value > self.max then
    self.value = self.max
  end
  fn.dirty_screen(true)
end

function recorder_history_navigator:decrement()
  self.value = self.value - 1
  if self.value < self.min then
    self.value = self.min
  end
  fn.dirty_screen(true)
end

function recorder_history_navigator:get_value()
  return self.value
end

function recorder_history_navigator:set_name()
  self.name = name
  fn.dirty_screen(true)
end

function recorder_history_navigator:set_value(v)
  self.value = v
  fn.dirty_screen(true)
end

function recorder_history_navigator:set_max(v)
  self.max = v
  fn.dirty_screen(true)
end

return recorder_history_navigator
