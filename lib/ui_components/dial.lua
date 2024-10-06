local dial = {}
dial.__index = dial

local fn = include("mosaic/lib/functions")

function dial:new(x, y, name, id, top_label, bottom_label)
  local self = setmetatable({}, dial)
  self.x = x
  self.y = y
  self.name = name
  self.value = -1
  self.top_label = top_label
  self.bottom_label = bottom_label
  self.selected = false
  self.min_value = nil
  self.max_value = nil
  self.off_value = -1
  self.ui_labels = nil
  self.display_value = false
  self.display_value_clock = nil

  return self
end


function dial:draw()
  -- Set screen level based on selection
  screen.level(self.selected and 15 or 1)
  
  -- Draw the top label
  screen.move(self.x, self.y)
  screen.text(fn.title_case(self.top_label))

  -- Position for drawing the bar
  local bar_x = self.x
  local bar_y = self.y + 7  -- Position below the top label

  -- Ensure `self.value` is within `min_value` and `max_value`
  if self.min_value and self.value then
    self.value = math.max(self.min_value, math.min(self.value, self.max_value))
  end

  -- Handle special cases for displaying value
  if self.value == self.off_value or not self.value then
    screen.move(self.x, bar_y)
    screen.text("X")
  elseif self.ui_labels and self.min_value then
    screen.move(self.x, bar_y)
    screen.text(self.ui_labels[self.value - (self.min_value - 1)])
  else
    -- Define bar dimensions and segments
    local bar_width = 20  -- Total width of the bar
    local bar_height = 4
    local num_segments = 20
    local segment_width = bar_width / num_segments
    local center_x = bar_x + (bar_width / 2)

    -- Determine if the range includes negative values
    local is_negative_range = self.min_value < self.off_value

    if is_negative_range then
      -- Negative and positive values
      local total_negative_range = self.off_value - self.min_value
      local total_positive_range = self.max_value - self.off_value
      local half_num_segments = num_segments / 2

      if self.value >= self.off_value then
        -- Positive values: fill from center to right
        local value_fraction = (self.value - self.off_value) / total_positive_range
        local filled_segments = math.floor(value_fraction * half_num_segments)
        local partial_fill = (value_fraction * half_num_segments) - filled_segments

        -- Draw filled segments
        for i = 1, filled_segments do
          local segment_x = center_x + (i - 1) * segment_width
          screen.rect(segment_x, bar_y - bar_height, segment_width, bar_height)
          screen.fill()
        end

        -- Draw partial segment
        if partial_fill > 0 and filled_segments < half_num_segments then
          local segment_x = center_x + filled_segments * segment_width
          local fill_width = segment_width * partial_fill
          screen.rect(segment_x, bar_y - bar_height, fill_width, bar_height)
          screen.fill()
        end
      else
        -- Negative values: fill from center to left
        local value_fraction = (self.off_value - self.value) / total_negative_range
        local filled_segments = math.floor(value_fraction * half_num_segments)
        local partial_fill = (value_fraction * half_num_segments) - filled_segments

        -- Draw filled segments
        for i = 1, filled_segments do
          local segment_x = center_x - i * segment_width
          screen.rect(segment_x, bar_y - bar_height, segment_width, bar_height)
          screen.fill()
        end

        -- Draw partial segment
        if partial_fill > 0 and filled_segments < half_num_segments then
          local segment_x = center_x - (filled_segments + 1) * segment_width
          local fill_width = segment_width * partial_fill
          screen.rect(segment_x + (segment_width - fill_width), bar_y - bar_height, fill_width, bar_height)
          screen.fill()
        end
      end
    else
      -- Positive-only values: fill from left edge to right
      local total_range = self.max_value - self.min_value
      local value_fraction = (self.value - self.min_value) / total_range
      local filled_segments = math.floor(value_fraction * num_segments)
      local partial_fill = (value_fraction * num_segments) - filled_segments

      -- Draw filled segments
      for i = 1, filled_segments do
        local segment_x = bar_x + (i - 1) * segment_width
        screen.rect(segment_x, bar_y - bar_height, segment_width, bar_height)
        screen.fill()
      end

      -- Draw partial segment
      if partial_fill > 0 and filled_segments < num_segments then
        local segment_x = bar_x + filled_segments * segment_width
        local fill_width = segment_width * partial_fill
        screen.rect(segment_x, bar_y - bar_height, fill_width, bar_height)
        screen.fill()
      end
    end
  end

  -- Draw the bottom label or value
  screen.move(self.x, self.y + 14)
  if self.display_value == false or self.value == self.off_value then
    screen.text(fn.title_case(self.bottom_label))
  else
    screen.text(self.value and fn.clean_number(self.value) or "X")
  end
end


function dial:select()
  self.selected = true
end

function dial:deselect()
  self.selected = false
end

function dial:is_selected()
  return self.selected
end

function dial:increment()
  self.value = self.value + 1
end

function dial:decrement()
  self.value = self.value - 1
end

function dial:set_value(value)
  if value == nil or (self.min_value and value < self.min_value) or (self.max_value and value > self.max_value) then
    value = self.off_value
  end
  self.value = value
end

function dial:set_top_label(label)
  self.top_label = label
end

function dial:set_bottom_label(label)
  self.bottom_label = label
end

function dial:set_name()
  self.name = name
  
end

function dial:get_name()
  return self.name
end

function dial:get_id()
  return self.id
end

function dial:set_off_value(off_value)
  self.off_value = off_value
end

function dial:set_ui_labels(ui_labels)
  self.ui_labels = ui_labels
end

function dial:set_min_value(min_value)
  self.min_value = min_value
end

function dial:set_max_value(max_value)
  self.max_value = max_value
end

function dial:temp_display_value()
  self.display_value = true

  if self.display_value_clock then
    clock.cancel(self.display_value_clock)
  end

  self.display_value_clock = clock.run(function()
    clock.sleep(2)
    self.display_value = false
    clock.cancel(self.display_value_clock)
    self.display_value_clock = nil
  end)
end

return dial
