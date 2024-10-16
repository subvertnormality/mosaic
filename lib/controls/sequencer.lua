sequencer = {}
sequencer.__index = sequencer


local setmetatable = setmetatable
local clock_run = clock.run
local clock_sleep = clock.sleep
local math_min = math.min

function sequencer:new(y, mode)
  local self = setmetatable({}, self)
  self.y = y
  self.unsaved_grid = {}
  self.mode = mode == "channel" and "channel" or "pattern"

  return self
end

function sequencer:draw(channel, draw_func)

  local bright_mod = 0

  if program.get_blink_state() then
    bright_mod = 0
  else
    bright_mod = 3
  end

  local mode = self.mode
  local bright_mod_15 = 15 - bright_mod
  local bright_mod_2 = 2 - ((bright_mod == 3 and 1) or (bright_mod == 0 and 0) or bright_mod)
  local unsaved_grid = self.unsaved_grid

  local trigs = channel.working_pattern.trig_values
  local lengths = channel.working_pattern.lengths

  local selected_pattern = program.get_selected_pattern()
  local program_get_selected_sequencer_pattern = program.get_selected_sequencer_pattern
  local program_get_current_step_for_channel = program.get_current_step_for_channel
  local program_step_has_trig_lock = program.step_has_trig_lock
  local clock_controller_is_playing = clock_controller.is_playing
  local fn_calc_grid_count = fn.calc_grid_count
  local math_floor = math.floor

  if mode == "pattern" then
    trigs = selected_pattern.trig_values
    lengths = selected_pattern.lengths
  end

  local length = -1
  local grid_count = -1

  local start_x = channel.start_trig[1]
  local start_y = channel.start_trig[2]
  local start_step = fn_calc_grid_count(start_x, start_y)

  local end_x = channel.end_trig[1]
  local end_y = channel.end_trig[2]
  local end_step = fn_calc_grid_count(end_x, end_y)
  local global_pattern_length = program_get_selected_sequencer_pattern().global_pattern_length

  if global_pattern_length < end_step then
    if start_step == 1 then
      end_step = global_pattern_length
    else
      end_step = start_step + math_min(end_step - start_step, global_pattern_length - 1)
    end
  end

  local current_step = program_get_current_step_for_channel(channel.number)

  for y = self.y, self.y + 3 do
    for x = 1, 16 do
      local grid_count = fn_calc_grid_count(x, y)
      local in_step_length = start_step <= grid_count and end_step >= grid_count

      if mode == "channel" then
        if in_step_length then
          if program_step_has_trig_lock(channel, grid_count) then
            draw_func(x, y, bright_mod_2)
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
      local grid_count = fn_calc_grid_count(x, y)
      local in_step_length = start_step <= grid_count and end_step >= grid_count

      if unsaved_grid[grid_count] then
        draw_func(x, y, bright_mod_15)
      end

      if trigs[grid_count] > 0 then
        if mode == "channel" then
          if in_step_length then
            if program_step_has_trig_lock(channel, grid_count) then
              draw_func(x, y, bright_mod_15)
            else
              draw_func(x, y, 15)
            end
          end
        else
          draw_func(x, y, 15)
        end

        if unsaved_grid[grid_count] then
          draw_func(x, y, bright_mod)
        end

        length = lengths[grid_count]

        if length > 1 then
          for lx = grid_count + 1, grid_count + length - 1 do
            if lx > 64 then
              lx = lx - 64
            end

            if trigs[lx] < 1 and lx < 65 then
              local lx_x = ((lx - 1) % 16) + 1
              local lx_y = self.y + math_floor((lx - 1) / 16)
              local length_grid_count = fn_calc_grid_count(lx_x, lx_y)
              if not (mode == "channel" and not (end_step >= length_grid_count and in_step_length)) and (start_step <= length_grid_count) then
                if program_step_has_trig_lock(channel, lx) then
                  draw_func(lx_x, lx_y, 5 - ((bright_mod == 3 and 1) or (bright_mod == 0 and 0) or bright_mod))
                else
                  draw_func(lx_x, lx_y, 5)
                end
              end
            else
              break
            end
          end
        end
      end

      if current_step == grid_count and clock_controller_is_playing() then
        if mode == "channel" then
          if grid_count >= start_step then
            if program_step_has_trig_lock(channel, grid_count) then
              draw_func(x, y, 10 - bright_mod)
            else
              draw_func(x, y, 10)
            end
          end
        end
      end
    end
  end
end

function sequencer:press(x, y)
  if y >= self.y and y <= self.y + 3 then
    if self.mode == "pattern" then
      local grid_count = fn.calc_grid_count(x, y)
      local selected_pattern = program.get_selected_pattern()
      selected_pattern.trig_values[grid_count] = 1 - selected_pattern.trig_values[grid_count]
      program.get_selected_sequencer_pattern().active = true
    end
  end
end

function sequencer:dual_press(x, y, x2, y2)
  if y >= self.y and y <= self.y + 3 and y2 >= self.y and y2 <= self.y + 3 then
    if self.mode == "channel" then
      program.get_selected_channel().start_trig = {x, y}
      program.get_selected_channel().end_trig = {x2, y2}
    elseif self.mode == "pattern" then
      local grid_count = fn.calc_grid_count(x, y)
      if program.get_selected_pattern().trig_values[grid_count] == 1 then
        local length = fn.calc_grid_count(x2, y2) - grid_count
        if length > 0 then
          program.get_selected_pattern().lengths[grid_count] = length + 1
        else
          program.get_selected_pattern().lengths[grid_count] = (64 - grid_count) + fn.calc_grid_count(x2, y2) + 1
        end
      end
    end
  end
end

function sequencer:long_press(x, y)
  if y >= self.y and y <= self.y + 3 then
    if self.mode == "pattern" then
      local grid_count = fn.calc_grid_count(x, y)
      if program.get_selected_pattern().trig_values[grid_count] == 1 then
        program.get_selected_pattern().lengths[grid_count] = 1
      end
    end
  end
end

function sequencer:is_this(x, y)
  return y >= self.y and y <= self.y + 3
end

function sequencer:show_unsaved_grid(g)
  self.unsaved_grid = g
end

function sequencer:hide_unsaved_grid()
  self.unsaved_grid = {}
end

return sequencer
