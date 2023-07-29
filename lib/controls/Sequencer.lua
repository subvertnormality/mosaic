Sequencer = {}
Sequencer.__index = Sequencer

local fn = include("sinfcommand/lib/functions")

function Sequencer:new(y, mode)
  local self = setmetatable({}, self)
  self.y = y
  self.unsaved_grid = {}

  self.bclock = {}

  self.bclock.state = false
  self.bclock.bright_mod = 0
  self.bclock.clock = clock.run(function()
    while true do
      if self.bclock.state then
        self.bclock.bright_mod = 0
        self.bclock.state = false
      else
        self.bclock.bright_mod = 3
        self.bclock.state = true
      end

      fn.dirty_grid(true)
      clock.sleep(0.3)
    end
  end)

  self.mode = "pattern"

  if mode == "channel" then
    self.mode = "channel"
  end

  return self
end


function Sequencer:draw(trigs, lengths)
  
  local length = -1
  local grid_count = -1
  
  local selected_sequencer_pattern = program.get().selected_sequencer_pattern
  local selected_pattern = program.get().selected_pattern

  local channel = program.get_selected_channel()

  local start_x = channel.start_trig[1]
  local start_y = channel.start_trig[2]
  local start_step = fn.calc_grid_count(start_x, start_y)

  local end_x = channel.end_trig[1]
  local end_y = channel.end_trig[2]
  local end_step = fn.calc_grid_count(end_x, end_y)

  for y = self.y, self.y + 3 do
    for x = 1, 16 do
      local grid_count = fn.calc_grid_count(x, y)
      local in_step_length = start_step <= grid_count and end_step >= grid_count

      if (self.mode == "channel") then

        if (in_step_length) then
          if program.step_has_trig_lock(grid_count) then
            g:led(x, y, 2 - ((self.bclock.bright_mod == 3 and 1) or (self.bclock.bright_mod == 0 and 0) or self.bclock.bright_mod))
          else
            g:led(x, y, 2)
          end
        end
      else
        g:led(x, y, 2)
      end
      
    end
  end

  local px = 0
  local py = self.y + 3

  for y = self.y, self.y + 3 do
    for x = 1, 16 do    
      local grid_count = fn.calc_grid_count(x, y)

      local in_step_length = start_step <= fn.calc_grid_count(x, y) and end_step >= fn.calc_grid_count(x, y)

      if (self.unsaved_grid[grid_count]) then
        g:led(x, y, 15 - self.bclock.bright_mod)
      end

      if (trigs[grid_count] > 0) then
        if (self.mode == "channel") then
          if (in_step_length) then
              if fn.calc_grid_count(x, y) == end_step and channel.current_step == start_step then 
                if program.step_has_trig_lock(grid_count) then
                  g:led(end_x, end_y, 10 - self.bclock.bright_mod)
                else
                  g:led(end_x, end_y, 10)
                end
              else
                if program.step_has_trig_lock(grid_count) then
                  g:led(x, y, 15 - self.bclock.bright_mod)
                else
                  g:led(x, y, 15) 
                end
              end
          end
        else
          g:led(x, y, 15) 
        end

        if (self.unsaved_grid[grid_count]) then
          g:led(x, y, 0 + self.bclock.bright_mod)
        end

        length = lengths[grid_count]
        
        if (length > 1 and in_step_length) then
          for lx = grid_count + 1, grid_count + length - 1 do
            if (trigs[lx] < 1 and lx < 65) then
              g:led((lx % 16), 4 + ((lx - 1) // 16 ), 5)
            else
              break
            end
          end
        end

      end

      if channel.current_step == grid_count and (clock_controller.is_playing() and program.get().current_step ~= 1) then
        if (self.mode == "channel") then
          if fn.calc_grid_count(px, py) >= start_step then 
            if (fn.calc_grid_count(px, py) > end_step) then
              if (program.step_has_trig_lock(grid_count)) then
                g:led(end_x, end_y, 10 - self.bclock.bright_mod)
              else
                g:led(end_x, end_y, 10)
              end
            else
              if program.step_has_trig_lock(grid_count) then
                g:led(px, py, 10 - self.bclock.bright_mod)
              else
                g:led(px, py, 10)
              end
            end
          end
        end
      end

      px = x
      py = y

    end
    fn.dirty_grid(true)
  end

  
end


function Sequencer:press(x, y)
  if (y >= self.y and y <= self.y + 3) then

    if (self.mode == "pattern") then
      program.get_selected_pattern().trig_values[fn.calc_grid_count(x, y)] = 1 - program.get_selected_pattern().trig_values[fn.calc_grid_count(x, y)]
      program.get_selected_sequencer_pattern().active = true
    end
    
  end
    
end

function Sequencer:dual_press(x, y, x2, y2)
  if (y >= self.y and y <= self.y + 3 and y2 >= self.y and y2 <= self.y + 3) then
    
    if (self.mode == "channel") then
      program.get_selected_channel().start_trig = {x, y}
      program.get_selected_channel().end_trig = {x2, y2}
    
    elseif (self.mode == "pattern") then
      if (program.get_selected_pattern().trig_values[fn.calc_grid_count(x, y)] == 1) then
        if (fn.calc_grid_count(x2, y2) - fn.calc_grid_count(x, y) > 0) then
          program.get_selected_pattern().lengths[fn.calc_grid_count(x, y)] = (fn.calc_grid_count(x2, y2) + 1) - fn.calc_grid_count(x, y)
        end
      end
    end
    
  end
    
end

function Sequencer:long_press(x, y)
  if (y >= self.y and y <= self.y + 3) then
    if (self.mode == "pattern") then
      if (program.get_selected_pattern().trig_values[fn.calc_grid_count(x, y)] == 1) then
        program.get_selected_pattern().lengths[fn.calc_grid_count(x, y)] = 1
      end
    end
    
  end
    
end

function Sequencer:is_this(x, y)
  if (y >= self.y and y <= self.y + 3) then
    return true
  end

  return false

end


function Sequencer:show_unsaved_grid(g)
  self.unsaved_grid = g
end

function Sequencer:hide_unsaved_grid(g)
  self.unsaved_grid = {}
end

return Sequencer