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
  local program_get_selected_song_pattern = program.get_selected_song_pattern
  local program_get_current_step_for_channel = program.get_current_step_for_channel
  local should_show_step_has_trig_lock = channel_edit_page_ui.should_show_step_has_trig_lock
  -- Heads, tails and the playhead ask about the same steps; the indicator
  -- cannot change during one draw, so query each step once.
  local step_lock_shown = {}
  local function program_step_has_trig_lock(step_channel, step)
    local shown = step_lock_shown[step]
    if shown == nil then
      shown = should_show_step_has_trig_lock(step_channel, step) and true or false
      step_lock_shown[step] = shown
    end
    return shown
  end

  local m_clock_is_playing = m_clock.is_playing
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
  local global_pattern_length = program_get_selected_song_pattern().global_pattern_length

  if global_pattern_length < end_step then
    if start_step == 1 then
      end_step = global_pattern_length
    else
      end_step = start_step + math_min(end_step - start_step, global_pattern_length - 1)
    end
  end

  local current_step = program_get_current_step_for_channel(channel.number)

  -- A row's grid counts are consecutive, so the row's first count is all the
  -- position each cell needs; the helper is still used off the row grid below.
  for y = self.y, self.y + 3 do
    local row_base = fn_calc_grid_count(0, y)
    for x = 1, 16 do
      local grid_count = row_base + x
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
    local row_base = fn_calc_grid_count(0, y)
    for x = 1, 16 do
      local grid_count = row_base + x
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

      if current_step == grid_count and m_clock_is_playing() then
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

function sequencer:press(x, y, song_pattern, pattern_number)
  if y >= self.y and y <= self.y + 3 then
    if self.mode == "pattern" then
      local grid_count = fn.calc_grid_count(x, y)
      local selected_pattern = song_pattern and song_pattern.patterns[pattern_number] or program.get_selected_pattern()
      selected_pattern.trig_values[grid_count] = 1 - selected_pattern.trig_values[grid_count]
      local target_song = song_pattern or program.get_selected_song_pattern()
      target_song.active = true
    end
  end
end

function sequencer:dual_press(x, y, x2, y2, song_pattern, pattern_number)
  if y >= self.y and y <= self.y + 3 and y2 >= self.y and y2 <= self.y + 3 then
    if self.mode == "channel" then
      -- Channel ranges are ascending and need distinct endpoints. Reject the
      -- gesture before changing either endpoint; pattern lengths may wrap.
      if fn.calc_grid_count(x2, y2) <= fn.calc_grid_count(x, y) then
        return false
      end
      local channel = program.get_selected_channel()
      channel.start_trig = {x, y}
      channel.end_trig = {x2, y2}
      -- The next step is chosen from the range at its onset, so a value already
      -- resolved for the step the old range would have played next must not
      -- leave: the new range may never play that step. What has left stays
      -- sent; its record names a step, so it cannot speak for another.
      local scheduler = m_clock and m_clock.get_lock_lookahead and m_clock.get_lock_lookahead()
      -- A step edited out of the range never arrives to correct a value that
      -- already left for it, so withdraw those sends and put back what they
      -- displaced. Without this the receiver keeps an excluded step's value,
      -- which is a difference from lead 0 that the player never asked for.
      if scheduler then scheduler:revert_channel(channel.number, step.restore_lock_value) end
      return true
    elseif self.mode == "pattern" then
      local grid_count = fn.calc_grid_count(x, y)
      local selected_pattern = song_pattern and song_pattern.patterns[pattern_number] or program.get_selected_pattern()
      if selected_pattern.trig_values[grid_count] == 1 then
        local length = fn.calc_grid_count(x2, y2) - grid_count
        if length > 0 then
          selected_pattern.lengths[grid_count] = length + 1
        else
          selected_pattern.lengths[grid_count] = (64 - grid_count) + fn.calc_grid_count(x2, y2) + 1
        end
      end
    end
  end
end

function sequencer:long_press(x, y, song_pattern, pattern_number)
  if y >= self.y and y <= self.y + 3 then
    if self.mode == "pattern" then
      local grid_count = fn.calc_grid_count(x, y)
      local selected_pattern = song_pattern and song_pattern.patterns[pattern_number] or program.get_selected_pattern()
      if selected_pattern.trig_values[grid_count] == 1 then
        selected_pattern.lengths[grid_count] = 1
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
