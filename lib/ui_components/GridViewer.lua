-- grid_abstract.get_state() 



local GridViewer = {}
GridViewer.__index = GridViewer

local screen_view_sequencer = Sequencer:new(4, "channel")

function GridViewer:new(x, y)
  local self = setmetatable({}, GridViewer)
  self.x = x - 8
  self.y = y - 10

  return self
end

function GridViewer:draw()

  local selected_sequencer_pattern = program.get().selected_sequencer_pattern
  local trigs = program.get_selected_channel().working_pattern.trig_values
  local lengths = program.get_selected_channel().working_pattern.lengths

  screen_view_sequencer:draw(trigs, lengths, grid_abstraction.seq)


  local state = grid_abstraction.get_screen_state() 
  for x = 1, 16 do
    for y = 1, 8 do
      screen.move(self.x + (x*7), self.y + (y*7))
      screen.level(state[x][y])
      screen.font_size(38)
      screen.text(".")
      
    end
  end

end


return GridViewer