local grid_viewer = {}
grid_viewer.__index = grid_viewer

local fn = include("mosaic/lib/functions")

local screen_view_sequencer = sequencer:new(4, "channel")

function grid_viewer:new(x, y)
  local self = setmetatable({}, grid_viewer)
  self.x = x
  self.y = y
  self.selected_channel = 1

  return self
end

function grid_viewer:draw()
  screen_view_sequencer:draw(program.get_channel(self.selected_channel), grid_abstraction.seq)

  local state = grid_abstraction.get_screen_state()

  for x = 1, 16 do
    for y = 1, 8 do
      screen.move(self.x - 3 + (x * 7), self.y - 5 + (y * 7))
      screen.level(state[x][y])
      screen.font_size(35)
      screen.text(".")
    end
  end
  screen.move(self.x, self.y + 6)
  screen.level(10)
  screen.font_size(8)
  screen.text("Channel " .. self.selected_channel .. " grid viewer")
end

function grid_viewer:next_channel()
  self.selected_channel = self.selected_channel + 1
  if self.selected_channel > 16 then
    self.selected_channel = 16
  end
  
end

function grid_viewer:prev_channel()
  self.selected_channel = self.selected_channel - 1
  if self.selected_channel < 1 then
    self.selected_channel = 1
  end
  
end

return grid_viewer
