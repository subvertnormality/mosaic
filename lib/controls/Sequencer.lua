Sequencer = {}
Sequencer.__index = Sequencer

function Sequencer:new(y)
  local self = setmetatable({}, self)
  self.y = y
  
  return self
end


function Sequencer:draw()
  
  local length = -1
  local grid_count = -1
  
  local selected_sequencer_pattern = program.selected_sequencer_pattern
  local selected_pattern = program.selected_pattern
  
  local trigs = program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].trig_values
  local lengths = program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].lengths

  for y = self.y, self.y + 3 do
    for x = 1, 16 do
      g:led(x, y, 2)
    end
  end

  for y = self.y, self.y + 3 do
    for x = 1, 16 do    
      grid_count = calc_grid_count(x, y)
    
      if (trigs[grid_count] > 0) then
        g:led(x, y, 15)
        length = lengths[grid_count]
        
        if (length > 1) then
          for lx = grid_count + 1, grid_count + length - 1 do
            if (trigs[lx] < 1 and lx < 65) then
              g:led((lx % 16), 4 + (lx // 16), 5)
            else
              break
            end
          end
        end
      end
    end
  end

  fn.dirty_grid(true)
end


function Sequencer:press(x, y)
  if (y >= self.y and y <= self.y + 3) then
    program.sequencer_patterns[1].patterns[program.selected_pattern].trig_values[calc_grid_count(x, y)] = 1 - program.sequencer_patterns[1].patterns[program.selected_pattern].trig_values[calc_grid_count(x, y)] 
  end
    
end


return Sequencer