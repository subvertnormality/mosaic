local grid_viewer = {}
grid_viewer.__index = grid_viewer

local screen_view_sequencer = sequencer:new(4, "channel")

function grid_viewer:new(x, y)
  local self = setmetatable({}, grid_viewer)
  self.x = x
  self.y = y
  self.selected_channel = 1

  return self
end

function grid_viewer:draw()
  -- The channel sequencer only writes cells inside its active range.
  -- Clear the shared viewer cache so shorter/different ranges cannot retain dots.
  -- These four rows are always inside the grid, so clear the cache columns
  -- directly rather than making sixty-four bounds-checked calls per redraw.
  local state = grid_abstraction.get_screen_state()
  for x = 1, 16 do
    local column = state[x]
    for y = 4, 7 do
      column[y] = 0
    end
  end

  screen_view_sequencer:draw(program.get_channel(program.get().selected_song_pattern, self.selected_channel), grid_abstraction.seq)

  -- Every cell is drawn at the same size, and changing the font size is one of
  -- the more expensive native screen calls. Set it once for the whole grid.
  screen.font_size(35)
  -- The screen keeps the level it was last given, so neighbouring cells of the
  -- same brightness need only one of these calls.
  local origin_x, origin_y = self.x - 3, self.y - 5
  local current_level
  for x = 1, 16 do
    local column = state[x]
    local cell_x = origin_x + (x * 7)
    for y = 1, 8 do
      local level = column[y]
      screen.move(cell_x, origin_y + (y * 7))
      if level ~= current_level then
        screen.level(level)
        current_level = level
      end
      screen.text(".")
    end
  end
  screen.move(self.x, self.y + 6)
  screen.level(10)
  screen.font_size(8)
  screen.text("Channel " .. self.selected_channel .. " grid viewer")
end

-- The 64 step levels (grid rows 4..7) the viewer draws for its channel, from
-- the same sequencer drawing path as draw(). Read-only for the live screen.
function grid_viewer:levels()
  local state = grid_abstraction.get_screen_state()
  for x = 1, 16 do
    local column = state[x]
    for y = 4, 7 do
      column[y] = 0
    end
  end
  screen_view_sequencer:draw(program.get_channel(program.get().selected_song_pattern, self.selected_channel), grid_abstraction.seq)
  local levels = {}
  for y = 4, 7 do
    for x = 1, 16 do
      levels[#levels + 1] = state[x][y] or 0
    end
  end
  return levels
end

function grid_viewer:next_channel()
  self.selected_channel = self.selected_channel + 1
  if self.selected_channel > 16 then
    self.selected_channel = 16
  end
  fn.dirty_screen(true)
end

function grid_viewer:prev_channel()
  self.selected_channel = self.selected_channel - 1
  if self.selected_channel < 1 then
    self.selected_channel = 1
  end
  fn.dirty_screen(true)
end

return grid_viewer
