local er = require("er")
local drum_ops = include("mosaic/lib/helpers/drum_ops")


local trigger_edit_page = {}
local shift = 0
local rhythm_doctor = nil
local rhythm_doctor_lane = nil
local rhythm_doctor_paint_preview = nil

local trigger_edit_page_pattern_select_fader = fader:new(1, 1, 16, 16)
local trigger_edit_page_sequencer = sequencer:new(4, "pattern")
local trigger_edit_page_pattern1_fader = fader:new(1, 2, 10, 100)
local trigger_edit_page_pattern2_fader = fader:new(1, 3, 10, 100)
local trigger_edit_page_algorithm_fader = fader:new(12, 2, 5, 5)
local trigger_edit_page_bankmask_fader = fader:new(12, 3, 5, 5)
local trigger_edit_page_paint_button = button:new(16, 8, {{"Inactive", 3}, {"Save", 15}})
local trigger_edit_page_cancel_button = button:new(14, 8, {{"Inactive", 3}, {"Cancel", 15}})
local trigger_edit_page_left_button = button:new(10, 8, {{"Inactive", 3}, {"Shift Left", 15}})
local trigger_edit_page_centre_button = button:new(11, 8, {{"Inactive", 3}, {"Reset Shift", 8}})
local trigger_edit_page_right_button = button:new(12, 8, {{"Inactive", 3}, {"Shift Right", 15}})

local load_timer = nil
local throttle_time = 0.1

function trigger_edit_page.init()
  trigger_edit_page.refresh_trigger_edit_page_ui()
end

local cancel_rhythm_doctor_paint
local preview_rhythm_doctor_paint
local rhythm_doctor_target

-- Whether an armed preview is still aimed at the destination that is selected.
function trigger_edit_page.paint_target_moved(armed, current)
  if type(armed) ~= "table" or type(current) ~= "table" then return false end
  return armed.song_slot ~= current.song_slot or armed.pattern_id ~= current.pattern_id
end

local function discard_stale_rhythm_doctor_paint()
  local preview = rhythm_doctor_paint_preview
  if not preview or type(preview.target) ~= "table" then return false end
  if not trigger_edit_page.paint_target_moved(preview.target, rhythm_doctor_target()) then return false end
  cancel_rhythm_doctor_paint()
  return true
end

function trigger_edit_page.register_draws()
  draw:register_grid(
    "trigger_edit_page",
    function()
      -- The song slot can change from another page, so the armed preview is
      -- rechecked here rather than only where the pattern fader is pressed.
      discard_stale_rhythm_doctor_paint()
      return trigger_edit_page_pattern_select_fader:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_sequencer:draw(program.get_selected_channel(), grid_abstraction.led)
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      if trigger_edit_page_algorithm_fader:get_value() ~= 5 then return trigger_edit_page_pattern1_fader:draw() end
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      if trigger_edit_page_algorithm_fader:get_value() ~= 5 then return trigger_edit_page_pattern2_fader:draw() end
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_algorithm_fader:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      if trigger_edit_page_algorithm_fader:get_value() ~= 5 then return trigger_edit_page_bankmask_fader:draw() end
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_paint_button:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_cancel_button:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_left_button:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_centre_button:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_right_button:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      if trigger_edit_page_algorithm_fader:get_value() ~= 5 then return end
      local model = rhythm_doctor and rhythm_doctor.screen_model and rhythm_doctor:screen_model() or nil
      grid_abstraction.led(1, 2, model and model.worker_ready and 15 or 4)
      -- The adapter owns where a lane sits, because the page assuming a single
      -- row ran a ten lane analysis under the algorithm fader at column 12.
      local cells = rhythm_doctor and rhythm_doctor.lane_cells and rhythm_doctor:lane_cells() or {}
      -- The effective lane, not the raw local: nothing is selected until the
      -- player picks, and the first lane of the live set is current until then.
      local current = trigger_edit_page.get_rhythm_doctor_lane()
      for _, cell in ipairs(cells) do
        grid_abstraction.led(cell.x, cell.y, cell.lane == current and 15 or 4)
      end
      grid_abstraction.led(2, 2, 0) -- reserved: never an old fader side effect
    end
  )
end

local function get_bank_name(id)
  if (trigger_edit_page_algorithm_fader:get_value() == 4) then
    return "Prime " .. id
  end

  if (id == 1) then
    return "Random bank"
  elseif (id == 2) then
    return "Bass drum bank"
  elseif (id == 3) then
    return "Snare drum bank"
  elseif (id == 4) then
    return "Closed hi-hat bank"
  elseif (id == 5) then
    return "Open hi-hat bank"
  end
end

local function get_algorithm_name(id)
  if (id == 1) then
    return "Drum algorithm"
  elseif (id == 2) then
    return "Tresillo algorithm"
  elseif (id == 3) then
    return "Euclidean algorithm"
  elseif (id == 4) then
    return "Numeric repetitor"
  elseif (id == 5) then
    return "Rhythm Doctor"
  end
end

local function shift_table(tbl, n)
  local len = #tbl
  n = n % len
  if n == 0 then return tbl end
  local res = {}
  for i = 1, len do
    res[i] = tbl[(i - n - 1) % len + 1]
  end
  return res
end

-- Builds the complete paint pattern; `yield` is coroutine.yield in the preview job and a
-- no-op when Paint needs the pattern at once (bugs.json paint-before-preview-settles).
local function build_paint_pattern(yield)
  -- Get all values up front
  local algorithm = trigger_edit_page_algorithm_fader:get_value()
  local pattern1 = trigger_edit_page_pattern1_fader:get_value()
  local pattern2 = trigger_edit_page_pattern2_fader:get_value() 
  local bank = trigger_edit_page_bankmask_fader:get_value()
  local len = 64
  local paint_pattern = {}
  
  yield() -- Yield after getting values
  
  -- Handle Euclidean rhythm case
  if (algorithm == 3) then
    local erpattern = er.gen(pattern1, pattern2, 0)
    local er_len = #erpattern
    
    -- Process in batches of 4
    for i = 1, len, 4 do
      for j = 0, 3 do
        local index = i + j
        if index <= len then
          paint_pattern[index] = erpattern[(index - 1) % er_len + 1]
        end
      end
      yield() -- Yield after each batch of 4
    end
  
  -- Handle other algorithms
  else
    -- Process in batches of 4
    for step = 1, len, 4 do
      for j = 0, 3 do
        local current_step = step + j
        if current_step <= len then
          if (algorithm == 1) then
            paint_pattern[current_step] = drum_ops.drum(bank, pattern1, current_step)
          elseif (algorithm == 2) then
            paint_pattern[current_step] = drum_ops.tresillo(bank, pattern1, pattern2, params:string("tresillo_amount"), current_step)
          elseif (algorithm == 4) then
            paint_pattern[current_step] = drum_ops.nr(pattern1, bank, pattern2, current_step)
          end
        end
      end
      yield() -- Yield after each batch of 4
    end
  end
 
  yield() -- Yield before shift operation
  
  if shift ~= 0 then
    paint_pattern = shift_table(paint_pattern, shift)
  end

  return paint_pattern
end

local load_paint_pattern = scheduler.debounce(function()
  if (trigger_edit_page_paint_button:get_state() ~= 2) then
    return
  end

  local pattern = build_paint_pattern(coroutine.yield)

  -- Painted or cancelled while this job was building: do not show the preview again.
  if (trigger_edit_page_paint_button:get_state() ~= 2) then
    return
  end

  trigger_edit_page_sequencer:show_unsaved_grid(pattern)
 end, throttle_time)

-- What choosing an algorithm does, from the grid fader or from the norns
-- screen (trigger_edit_page.select_algorithm): the Doctor takes or releases
-- the page, the faders follow, and the paint preview is rebuilt.
local function algorithm_selected(previous, selected)
  if previous ~= 5 and selected == 5 and rhythm_doctor and rhythm_doctor.enter then rhythm_doctor:enter() end
  if previous == 5 and selected ~= 5 and rhythm_doctor and rhythm_doctor.leave then rhythm_doctor:leave() end
  trigger_edit_page.refresh_trigger_edit_page_ui()
  tooltip:show(get_algorithm_name(selected) .. " selected")
  load_paint_pattern()
end

-- Selects algorithm 1..5 exactly as a press on its grid fader key does; the
-- grid shows the new selection on its next redraw.
function trigger_edit_page.select_algorithm(n)
  if type(n) ~= "number" or n < 1 or n > 5 then return false end
  local previous = trigger_edit_page_algorithm_fader:get_value()
  trigger_edit_page_algorithm_fader:set_value(n)
  algorithm_selected(previous, n)
  fn.dirty_grid(true)
  return true
end

local function save_paint_pattern(p)
  local selected_song_pattern = program.get_selected_song_pattern()
  local selected_pattern = program.get().selected_pattern
  local trigs = selected_song_pattern.patterns[selected_pattern].trig_values
  local lengths = selected_song_pattern.patterns[selected_pattern].lengths

  for x = 1, 64 do
    if (trigs[x] < 1) and p[x] then
      trigs[x] = 1
      lengths[x] = 1
    elseif trigs[x] and p[x] then
      trigs[x] = 0
      lengths[x] = 0
    end
  end
  selected_song_pattern.patterns[selected_pattern].trig_values = trigs
  selected_song_pattern.patterns[selected_pattern].lengths = lengths
  pattern.update_source_working_patterns(selected_song_pattern, selected_pattern)
  selected_song_pattern.active = true
end

function rhythm_doctor_target()
  local data = program.get()
  return { song_slot = data.selected_song_pattern, pattern_id = data.selected_pattern }
end

local function rhythm_doctor_preview_grid(preview)
  local grid = {}
  for step = 1, 64 do grid[step] = preview.shifted_cells and preview.shifted_cells[step] ~= nil end
  return grid
end

-- The left/centre/right buttons browse the recording while algorithm 5 is
-- selected, and they browse it the way they shift a paint pattern everywhere
-- else: a press is worth one step, so the gesture means the same thing in
-- every mode. Holding left or right covers a whole four-bar phrase, and
-- centre returns to the detected phrase start the way it resets the shift.
-- For every other algorithm they keep shifting the paint pattern, which is
-- why these run only inside the algorithm-5 branches of the press handlers.

-- A preview describes the window it was taken from, so a move retires it. But
-- the reason to move while painting is to look at the next part of the
-- recording, so the preview is taken again where the window landed. Without
-- this the grid simply went dark, and stayed dark until some unrelated press
-- happened to rebuild it.
local function refresh_rhythm_doctor_paint()
  if trigger_edit_page_paint_button:get_state() ~= 2 then return end
  local preview, problem = preview_rhythm_doctor_paint()
  if not preview then tooltip:show((problem and problem.code) or "PAINT UNAVAILABLE") end
end

-- Report what happened, not what was asked for. Every move is clamped to the
-- recording, so a press at either end succeeds without moving anything;
-- naming the requested action there would tell the player they had advanced a
-- phrase while the window stood still.
local function rhythm_doctor_window_feedback(value, action, stalled)
  if not (value and (value.ok or value.code == "WINDOW_MOVED")) then
    tooltip:show((value and value.code) or "WINDOW UNAVAILABLE")
    return false
  end
  if value.moved == false then
    tooltip:show(stalled)
  else
    tooltip:show(value.window_label and (action .. " " .. value.window_label) or action)
  end
  refresh_rhythm_doctor_paint()
  return true
end

function rhythm_doctor_jump_to_phrase_start()
  if not rhythm_doctor or type(rhythm_doctor.jump_to_phrase_start) ~= "function" then
    tooltip:show("WINDOW UNAVAILABLE")
    return false
  end
  cancel_rhythm_doctor_paint()
  local value = rhythm_doctor:jump_to_phrase_start()
  rhythm_doctor_window_feedback(value, "Phrase start", "At phrase start")
  return value ~= nil
end

local function rhythm_doctor_browse(method, delta, action)
  if not rhythm_doctor or type(rhythm_doctor[method]) ~= "function" then
    tooltip:show("WINDOW UNAVAILABLE")
    return false
  end
  cancel_rhythm_doctor_paint()
  local value = rhythm_doctor[method](rhythm_doctor, delta)
  rhythm_doctor_window_feedback(value, action,
    delta < 0 and "Start of recording" or "End of recording")
  return value ~= nil
end

function rhythm_doctor_nudge_window(delta)
  return rhythm_doctor_browse("nudge_window", delta, delta < 0 and "Step left" or "Step right")
end

function rhythm_doctor_page_window(delta)
  return rhythm_doctor_browse("page_window", delta, delta < 0 and "Previous phrase" or "Next phrase")
end

function preview_rhythm_doctor_paint()
  if not rhythm_doctor or type(rhythm_doctor.paint_preview) ~= "function" then return nil, { code = "PAINT_UNAVAILABLE" } end
  local preview, problem = rhythm_doctor:paint_preview(rhythm_doctor_target())
  if not preview then return nil, problem end
  rhythm_doctor_paint_preview = preview
  trigger_edit_page_sequencer:show_unsaved_grid(rhythm_doctor_preview_grid(preview))
  return preview
end

-- A preview commits to the destination it was built for, not the one that is
-- selected now, so an armed preview must not outlive the selection. Changing
-- pattern or song slot leaves it pointing at the old target while the screen
-- shows the new one, and Paint would then write where the player is no longer
-- looking.
function cancel_rhythm_doctor_paint()
  rhythm_doctor_paint_preview = nil
  trigger_edit_page_sequencer:hide_unsaved_grid()
  if rhythm_doctor and type(rhythm_doctor.invalidate_paint_preview) == "function" then rhythm_doctor:invalidate_paint_preview() end
end

function trigger_edit_page.register_press()
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_pattern_select_fader:is_this(x, y) then
        trigger_edit_page_pattern_select_fader:press(x, y)
        program.get().selected_pattern = trigger_edit_page_pattern_select_fader:get_value()
        discard_stale_rhythm_doctor_paint()
        tooltip:show("Pattern " .. program.get().selected_pattern .. " selected")
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_sequencer:is_this(x, y) then
        local song = program.get_selected_song_pattern()
        local source = program.get().selected_pattern
        trigger_edit_page_sequencer:press(x, y, song, source)
        pattern.update_source_working_patterns(song, source)
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_pattern1_fader:is_this(x, y) then
        if trigger_edit_page_algorithm_fader:get_value() == 5 then return end
        trigger_edit_page_pattern1_fader:press(x, y)
        load_paint_pattern()
        if (trigger_edit_page_algorithm_fader:get_value() == 3) then
          tooltip:show("Fill - " .. trigger_edit_page_pattern1_fader:get_value() .. " selected")
        else
          tooltip:show("Pattern 1 - " .. trigger_edit_page_pattern1_fader:get_value() .. " selected")
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_pattern2_fader:is_this(x, y) then
        if trigger_edit_page_algorithm_fader:get_value() == 5 then return end
        trigger_edit_page_pattern2_fader:press(x, y)
        load_paint_pattern()
        if (trigger_edit_page_algorithm_fader:get_value() == 3) then
          tooltip:show("Length - " .. trigger_edit_page_pattern2_fader:get_value() .. " selected")
        else
          tooltip:show("Pattern 2 - " .. trigger_edit_page_pattern2_fader:get_value() .. " selected")
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      local previous = trigger_edit_page_algorithm_fader:get_value()
      trigger_edit_page_algorithm_fader:press(x, y)
      if trigger_edit_page_algorithm_fader:is_this(x, y) then
        algorithm_selected(previous, trigger_edit_page_algorithm_fader:get_value())
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      local algorithm = trigger_edit_page_algorithm_fader:get_value()
      if trigger_edit_page_bankmask_fader:is_this(x, y) and algorithm ~= 3 and algorithm ~= 5 then
        trigger_edit_page_bankmask_fader:press(x, y)
        load_paint_pattern()
        tooltip:show(get_bank_name(trigger_edit_page_bankmask_fader:get_value()) .. " selected")
      end
    end
  )
  press:register_pre(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_algorithm_fader:get_value() == 5 and x == 1 and y == 2 then
        if rhythm_doctor and rhythm_doctor.record_pressed then rhythm_doctor:record_pressed() end
        return true
      end
      return false
    end
  )
  press:register_post(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_algorithm_fader:get_value() == 5 and x == 1 and y == 2 and rhythm_doctor and rhythm_doctor.record_released then
        rhythm_doctor:record_released()
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      -- Cells are bound to the live lane set through the adapter, which owns
      -- the layout: a cell past the last lane, and every cell belonging to the
      -- algorithm or bank-mask fader, must stay inert rather than dispatch a
      -- lane into the adapter.
      if trigger_edit_page_algorithm_fader:get_value() ~= 5 then return end
      local selected = rhythm_doctor and rhythm_doctor.lane_at and rhythm_doctor:lane_at(x, y) or nil
      if selected then
        local accepted = not rhythm_doctor or not rhythm_doctor.select_lane or rhythm_doctor:select_lane(selected)
        if not accepted or accepted.code == "LANE_SELECTED" then
          rhythm_doctor_lane = selected
          tooltip:show(rhythm_doctor_lane .. " selected")
          if trigger_edit_page_paint_button:get_state() == 2 then
            local preview, problem = preview_rhythm_doctor_paint()
            if not preview then tooltip:show((problem and problem.code) or "PAINT UNAVAILABLE") end
          end
        elseif accepted.code == "STOP_SEQUENCER" then tooltip:show("STOP SEQUENCER") end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      trigger_edit_page_paint_button:press(x, y)

      if trigger_edit_page_paint_button:is_this(x, y) then
        if trigger_edit_page_algorithm_fader:get_value() == 5 then
          if trigger_edit_page_paint_button:get_state() == 2 then
            local preview, problem = preview_rhythm_doctor_paint()
            if not preview then
              trigger_edit_page_paint_button:set_state(1)
              tooltip:show((problem and problem.code) or "PAINT UNAVAILABLE")
              return
            end
            trigger_edit_page_cancel_button:set_state(2)
            trigger_edit_page_left_button:set_state(2)
            trigger_edit_page_centre_button:set_state(2)
            trigger_edit_page_right_button:set_state(2)
            trigger_edit_page_paint_button:blink()
            tooltip:show("Painting Rhythm Doctor")
            return
          end
          local preview = rhythm_doctor_paint_preview
          local saved, problem
          if rhythm_doctor and type(rhythm_doctor.paint_commit) == "function" then
            saved, problem = rhythm_doctor:paint_commit(preview, preview and preview.requires_replace_confirmation == true)
          else
            problem = { code = "PAINT_UNAVAILABLE" }
          end
          if not saved then
            trigger_edit_page_paint_button:set_state(2)
            tooltip:show((problem and problem.code) or "PAINT FAILED")
            return
          end
          rhythm_doctor_paint_preview = nil
          trigger_edit_page_left_button:set_state(1)
          trigger_edit_page_centre_button:set_state(1)
          trigger_edit_page_right_button:set_state(1)
          trigger_edit_page_cancel_button:set_state(1)
          trigger_edit_page_sequencer:hide_unsaved_grid()
          trigger_edit_page_paint_button:no_blink()
          tooltip:show("Pattern painted")
          return
        end
        if (trigger_edit_page_paint_button:get_state() == 2) then
          trigger_edit_page_cancel_button:set_state(2)
          trigger_edit_page_left_button:set_state(2)
          trigger_edit_page_centre_button:set_state(2)
          trigger_edit_page_right_button:set_state(2)
          load_paint_pattern()
          trigger_edit_page_paint_button:blink()
          tooltip:show("Painting pattern")
        else
          trigger_edit_page_left_button:set_state(1)
          trigger_edit_page_centre_button:set_state(1)
          trigger_edit_page_right_button:set_state(1)
          trigger_edit_page_cancel_button:set_state(1)
          trigger_edit_page_sequencer:hide_unsaved_grid()
          save_paint_pattern(build_paint_pattern(function() end))
          trigger_edit_page_paint_button:no_blink()
          tooltip:show("Pattern painted")
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      trigger_edit_page_cancel_button:press(x, y)

      if trigger_edit_page_cancel_button:is_this(x, y) then
        if (trigger_edit_page_paint_button:get_state() == 2) then
          if trigger_edit_page_algorithm_fader:get_value() == 5 then cancel_rhythm_doctor_paint() else trigger_edit_page_sequencer:hide_unsaved_grid() end
          trigger_edit_page_paint_button:set_state(1)
          trigger_edit_page_paint_button:no_blink()
          trigger_edit_page_cancel_button:no_blink()
          trigger_edit_page_left_button:set_state(1)
          trigger_edit_page_centre_button:set_state(1)
          trigger_edit_page_right_button:set_state(1)
          tooltip:show("Painting cancelled")
        else
          trigger_edit_page_cancel_button:set_state(1)
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_left_button:is_this(x, y) then
        -- Rhythm Doctor browses the recording with these, so they act
        -- whenever algorithm 5 is selected. The paint-preview state gate
        -- below belongs to shifting a previewed pattern: leaving it in
        -- place made phrase navigation reachable only while previewing,
        -- which is precisely when the player is no longer browsing.
        if trigger_edit_page_algorithm_fader:get_value() == 5 then
          rhythm_doctor_nudge_window(-1)
          return
        end
        if (trigger_edit_page_left_button:get_state() == 2) then
          shift = shift - 1

          load_paint_pattern()
          trigger_edit_page_left_button:set_state(2)
          tooltip:show("Shifting left")
        else
          trigger_edit_page_left_button:set_state(1)
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_centre_button:is_this(x, y) then
        -- Rhythm Doctor browses the recording with these, so they act
        -- whenever algorithm 5 is selected. The paint-preview state gate
        -- below belongs to shifting a previewed pattern: leaving it in
        -- place made phrase navigation reachable only while previewing,
        -- which is precisely when the player is no longer browsing.
        if trigger_edit_page_algorithm_fader:get_value() == 5 then
          rhythm_doctor_jump_to_phrase_start()
          return
        end
        if (trigger_edit_page_centre_button:get_state() == 2) then
          shift = 0
          load_paint_pattern()
          trigger_edit_page_centre_button:set_state(2)
          tooltip:show("Shift reset")
        else
          trigger_edit_page_centre_button:set_state(1)
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_right_button:is_this(x, y) then
        -- Rhythm Doctor browses the recording with these, so they act
        -- whenever algorithm 5 is selected. The paint-preview state gate
        -- below belongs to shifting a previewed pattern: leaving it in
        -- place made phrase navigation reachable only while previewing,
        -- which is precisely when the player is no longer browsing.
        if trigger_edit_page_algorithm_fader:get_value() == 5 then
          rhythm_doctor_nudge_window(1)
          return
        end
        if (trigger_edit_page_right_button:get_state() == 2) then
          shift = shift + 1

          trigger_edit_page_right_button:set_state(2)
          load_paint_pattern()
          tooltip:show("Shifting right")
        else
          trigger_edit_page_right_button:set_state(1)
        end
      end
    end
  )
  press:register_dual(
    "trigger_edit_page",
    function(x, y, x2, y2)
      local song = program.get_selected_song_pattern()
      local source = program.get().selected_pattern
      trigger_edit_page_sequencer:dual_press(x, y, x2, y2, song, source)
      if trigger_edit_page_sequencer:is_this(x2, y2) then
        pattern.update_source_working_patterns(song, source)
        tooltip:show("Note length set")
      end
    end
  )
  -- Held, the browse buttons cover a whole phrase. Registered separately from
  -- the short press because the grid suppresses the short press once a hold
  -- has fired, so the two gestures cannot both act on one key.
  press:register_long(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_algorithm_fader:get_value() ~= 5 then return end
      if trigger_edit_page_left_button:is_this(x, y) then rhythm_doctor_page_window(-1)
      elseif trigger_edit_page_right_button:is_this(x, y) then rhythm_doctor_page_window(1) end
    end
  )
  press:register_long(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_sequencer:is_this(x, y) then
        local song = program.get_selected_song_pattern()
        local source = program.get().selected_pattern
        trigger_edit_page_sequencer:long_press(x, y, song, source)
        pattern.update_source_working_patterns(song, source)
        tooltip:show("Note length reset")
      end
    end
  )
end

function trigger_edit_page.refresh_trigger_edit_page_ui()
  local algorithm = trigger_edit_page_algorithm_fader:get_value()

  if (algorithm == 1) then
    trigger_edit_page_pattern1_fader:enabled()
    trigger_edit_page_bankmask_fader:enabled()
    trigger_edit_page_bankmask_fader:set_size(5)
    trigger_edit_page_bankmask_fader:set_length(5)
    trigger_edit_page_pattern1_fader:set_size(128)
    trigger_edit_page_pattern2_fader:set_size(128)
    trigger_edit_page_pattern2_fader:disabled()
  elseif (algorithm == 2) then
    trigger_edit_page_pattern1_fader:enabled()
    trigger_edit_page_bankmask_fader:enabled()
    trigger_edit_page_bankmask_fader:set_size(5)
    trigger_edit_page_bankmask_fader:set_length(5)
    trigger_edit_page_pattern1_fader:set_size(128)
    trigger_edit_page_pattern2_fader:set_size(128)
    trigger_edit_page_pattern2_fader:enabled()
  elseif (algorithm == 3) then
    trigger_edit_page_pattern1_fader:enabled()
    trigger_edit_page_bankmask_fader:disabled()
    trigger_edit_page_bankmask_fader:set_size(5)
    trigger_edit_page_bankmask_fader:set_length(5)
    trigger_edit_page_pattern2_fader:enabled()
    trigger_edit_page_pattern1_fader:set_size(32)
    trigger_edit_page_pattern2_fader:set_size(32)
  elseif (algorithm == 4) then
    trigger_edit_page_pattern1_fader:enabled()
    trigger_edit_page_bankmask_fader:enabled()
    trigger_edit_page_bankmask_fader:set_size(4)
    trigger_edit_page_bankmask_fader:set_length(4)
    trigger_edit_page_pattern1_fader:set_size(32)
    trigger_edit_page_pattern2_fader:set_size(16)
    trigger_edit_page_pattern2_fader:enabled()
  elseif (algorithm == 5) then
    trigger_edit_page_bankmask_fader:disabled()
    trigger_edit_page_pattern1_fader:disabled()
    trigger_edit_page_pattern2_fader:disabled()
  end

  trigger_edit_page_pattern_select_fader:set_value(program.get().selected_pattern)

  fn.dirty_grid(true)
end

function trigger_edit_page.get_algorithm() return trigger_edit_page_algorithm_fader:get_value() end

-- The generator inputs the grid faders set for the algorithm in use (rows 2
-- and 3), for the Trig Algorithm screen (P06).
function trigger_edit_page.generator_inputs()
  return {
    algorithm = trigger_edit_page_algorithm_fader:get_value(),
    pattern1 = trigger_edit_page_pattern1_fader:get_value(),
    pattern2 = trigger_edit_page_pattern2_fader:get_value(),
    bank = trigger_edit_page_bankmask_fader:get_value(),
  }
end

-- The paint preview as the Paint Preview screen (P07) shows it: whether one is
-- showing on the grid, the algorithm it comes from, the shift applied, and
-- how many steps it triggers. Reads only; never builds a pattern.
function trigger_edit_page.paint_state()
  local grid = trigger_edit_page_sequencer.unsaved_grid or {}
  local trigs = 0
  for step = 1, 64 do if grid[step] then trigs = trigs + 1 end end
  return {
    painting = trigger_edit_page_paint_button:get_state() == 2,
    algorithm = trigger_edit_page_algorithm_fader:get_value(),
    algorithm_name = get_algorithm_name(trigger_edit_page_algorithm_fader:get_value()),
    shift = shift,
    trigs = trigs,
  }
end
function trigger_edit_page.get_rhythm_doctor_lane()
  -- Before anything is selected, the first lane of the live set is current --
  -- which after a ten lane analysis is not BD.
  if rhythm_doctor_lane then return rhythm_doctor_lane end
  local lanes = rhythm_doctor and rhythm_doctor.lanes and rhythm_doctor:lanes() or {}
  return lanes[1]
end
function trigger_edit_page.get_rhythm_doctor_model()
  return rhythm_doctor and rhythm_doctor.screen_model and rhythm_doctor:screen_model() or nil
end
function trigger_edit_page.set_rhythm_doctor(value) rhythm_doctor = value end
-- Read-only accessors for lib/ui_adapters/doctor.lua (UI02). They expose the
-- existing instance and state; they change nothing.
function trigger_edit_page.get_rhythm_doctor() return rhythm_doctor end
-- doctor_routes input `preview`: the Paint button armed while algorithm 5 is selected.
function trigger_edit_page.rhythm_doctor_preview_armed()
  return trigger_edit_page_algorithm_fader:get_value() == 5 and trigger_edit_page_paint_button:get_state() == 2
end
-- The destination an armed preview is built for (the selected song slot and pattern).
function trigger_edit_page.rhythm_doctor_paint_destination() return rhythm_doctor_target() end
function trigger_edit_page.handle_rhythm_doctor_key(n, z)
  if not rhythm_doctor or not rhythm_doctor.key then return nil end
  return rhythm_doctor:key(n, z)
end
function trigger_edit_page.handle_rhythm_doctor_encoder(n, d)
  if not rhythm_doctor or not rhythm_doctor.enc then return nil end
  return rhythm_doctor:enc(n, d)
end
function trigger_edit_page.disconnect_rhythm_doctor()
  if rhythm_doctor and rhythm_doctor.disconnect then rhythm_doctor:disconnect() end
end

function trigger_edit_page.refresh()
  trigger_edit_page.refresh_trigger_edit_page_ui()
end

return trigger_edit_page
