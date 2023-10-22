local GridViewer = {}
GridViewer.__index = GridViewer

local screen_view_sequencer = Sequencer:new(4, "channel")

function GridViewer:new(x, y)
  local self = setmetatable({}, GridViewer)
  self.x = x - 1
  self.y = y - 2
  self.selected_channel = 1

  return self
end

function GridViewer:draw()
  screen_view_sequencer:draw(program.get_channel(self.selected_channel), grid_abstraction.seq)

  local state = grid_abstraction.get_screen_state()

  for x = 1, 16 do
    for y = 1, 8 do
      screen.move(self.x + (x * 7), self.y + (y * 7))
      screen.level(state[x][y])
      screen.font_size(35)
      screen.text(".")
    end
  end
  screen.move(self.x + 7, self.y + 12)
  screen.level(10)
  screen.font_size(8)
  screen.text("Channel " .. self.selected_channel .. " grid viewer")
end

function GridViewer:next_channel()
  self.selected_channel = self.selected_channel + 1
  if self.selected_channel > 16 then
    self.selected_channel = 16
  end
end

function GridViewer:prev_channel()
  self.selected_channel = self.selected_channel - 1
  if self.selected_channel < 1 then
    self.selected_channel = 1
  end
end

return GridViewer
