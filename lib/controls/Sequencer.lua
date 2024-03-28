Sequencer = {}
Sequencer.__index = Sequencer

local fn = include("mosaic/lib/functions")

function Sequencer:new(y, mode)
  local self = setmetatable({}, self)
  self.y = y
  self.unsaved_grid = {}

  self.bclock = {}

  self.bclock.state = false
  self.bclock.bright_mod = 0
  self.bclock.clock =
    clock.run(
    function()
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
    end
  )

  self.mode = "pattern"

  if mode == "channel" then
    self.mode = "channel"
  end

  return self
end

function Sequencer:draw(channel, draw_func)
  local trigs = channel.working_pattern.trig_values
  local lengths = channel.working_pattern.lengths

  local selected_pattern = program.get_selected_pattern()

  if (self.mode == "pattern") then
    trigs = selected_pattern.trig_values
    lengths = selected_pattern.lengths
  end

  local length = -1
  local grid_count = -1

  local start_x = channel.start_trig[1]
  local start_y = channel.start_trig[2]
  local start_step = fn.calc_grid_count(start_x, start_y)

  local end_x = channel.end_trig[1]
  local end_y = channel.end_trig[2]
  local end_step = fn.calc_grid_count(end_x, end_y)
  local global_pattern_length = program.get_selected_sequencer_pattern().global_pattern_length

  if global_pattern_length < end_step then
    
    if (start_step == 1) then
      end_step = global_pattern_length
    else
      end_step = global_pattern_length + (end_step - (start_step - 1))
    end
  end

  local current_step = program.get().current_step

  current_step = program.get_current_step_for_channel(channel.number)

  for y = self.y, self.y + 3 do
    for x = 1, 16 do
      local grid_count = fn.calc_grid_count(x, y)
      local in_step_length = start_step <= grid_count and end_step >= grid_count

      if (self.mode == "channel") then
        if (in_step_length) then
          if program.step_has_trig_lock(channel, grid_count) then
            draw_func(
              x,
              y,
              2 - ((self.bclock.bright_mod == 3 and 1) or (self.bclock.bright_mod == 0 and 0) or self.bclock.bright_mod)
            )
          else
            draw_func(x, y, 2)
          end
        end
      else
        draw_func(x, y, 2)
      end
    end
  end

  for y = self.y, self.y + 3 do
    for x = 1, 16 do
      local grid_count = fn.calc_grid_count(x, y)

      local in_step_length = start_step <= grid_count and end_step >= grid_count

      if (self.unsaved_grid[grid_count]) then
        draw_func(x, y, 15 - self.bclock.bright_mod)
      end

      if (trigs[grid_count] > 0) then
        if (self.mode == "channel") then
          if (in_step_length) then
            if program.step_has_trig_lock(channel, grid_count) then
              draw_func(x, y, 15 - self.bclock.bright_mod)
            else
              draw_func(x, y, 15)
            end
          end
        else
          draw_func(x, y, 15)
        end

        if (self.unsaved_grid[grid_count]) then
          draw_func(x, y, 0 + self.bclock.bright_mod)
        end

        length = lengths[grid_count]

        if (length > 1 and in_step_length) then
          for lx = grid_count + 1, grid_count + length - 1 do
            if lx > 64 then
              lx = lx - 64
            end

            if (trigs[lx] < 1 and lx < 65) then
              local length_grid_count = fn.calc_grid_count((lx - 1) % 16 + 1, 4 + ((lx - 1) // 16))
              if start_step <= length_grid_count and end_step >= length_grid_count then
                if program.step_has_trig_lock(channel, lx) then
                  draw_func((lx - 1) % 16 + 1, 4 + ((lx - 1) // 16), 5 - ((self.bclock.bright_mod == 3 and 1) or (self.bclock.bright_mod == 0 and 0) or self.bclock.bright_mod))
                else
                  draw_func((lx - 1) % 16 + 1, 4 + ((lx - 1) // 16), 5)
                end
              end
            else
              break
            end
          end
        end
      end
      if (self.mode == "channel") then
        if program.get_step_trig_masks(channel.number) and program.get_step_trig_masks(channel.number)[grid_count] == false then
          local b = 2 - self.bclock.bright_mod
          if b < 0 then b = 0 end
          draw_func(x, y, b)
        end
      end

      if current_step == grid_count and clock_controller.is_playing() then
        if (self.mode == "channel") then
          if fn.calc_grid_count(x, y) >= start_step then
            if program.step_has_trig_lock(channel, grid_count) then
              draw_func(x, y, 10 - self.bclock.bright_mod)
            else
              draw_func(x, y, 10)
            end
          end
        end
      end
    end
  end
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function Sequencer:press(x, y)
  if (y >= self.y and y <= self.y + 3) then
    if (self.mode == "pattern") then
      program.get_selected_pattern().trig_values[fn.calc_grid_count(x, y)] =
        1 - program.get_selected_pattern().trig_values[fn.calc_grid_count(x, y)]
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
          program.get_selected_pattern().lengths[fn.calc_grid_count(x, y)] =
            (fn.calc_grid_count(x2, y2) + 1) - fn.calc_grid_count(x, y)
        else
          program.get_selected_pattern().lengths[fn.calc_grid_count(x, y)] =
            (64 - fn.calc_grid_count(x, y)) + ((fn.calc_grid_count(x2, y2)) + 1)
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
