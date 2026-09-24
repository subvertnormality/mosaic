-- Characterisation outside the manual: the start-up splash animation. It must
-- be deterministic, never consume musical randomness, and end on input.

local ui_splash = include("mosaic/lib/ui_splash")

local function tiles_at(t)
  local count = 0
  for row = 0, 7 do
    for column = 0, 15 do
      if ui_splash.tile(column, row, t) then count = count + 1 end
    end
  end
  return count
end

local function with_recording_screen(body)
  local saved, saved_random = screen, math.random
  local calls = {}
  screen = setmetatable({text_extents = function(text) return #text * 12, 16 end}, {__index = function(_, name)
    return function(...) calls[#calls + 1] = {name, ...} end
  end})
  math.random = function() error("splash consumed math.random") end
  local ok, err = pcall(body, calls)
  screen, math.random = saved, saved_random
  if not ok then error(err, 0) end
  return calls
end

function test_ui_splash_tiles_lay_row_by_row_left_to_right()
  luaunit.assert_equals(tiles_at(0), 0)
  luaunit.assert_true(tiles_at(0.03) >= 1)
  -- Within a row, a tile to the right never appears before one to its left.
  for row = 0, 7 do
    for column = 1, 15 do
      for t = 0, 1, 1 / 60 do
        if ui_splash.tile(column, row, t) then luaunit.assert_not_nil(ui_splash.tile(column - 1, row, t)) end
      end
    end
  end
  -- A later row never starts before the row above has begun.
  luaunit.assert_nil(ui_splash.tile(0, 1, 0.05))
  luaunit.assert_not_nil(ui_splash.tile(0, 1, 0.07))
  luaunit.assert_equals(tiles_at(0.95), 128)
end

function test_ui_splash_tiles_lift_to_leave_the_word_which_then_fades()
  luaunit.assert_equals(ui_splash.letter_level(1, 0.9), 0)
  luaunit.assert_equals(tiles_at(1.7), 0)
  for index = 1, 6 do luaunit.assert_equals(ui_splash.letter_level(index, 1.8), 15) end
  -- Letters fade one after another, left to right.
  luaunit.assert_true(ui_splash.letter_level(1, 2.2) < ui_splash.letter_level(6, 2.2))
  for index = 1, 6 do luaunit.assert_equals(ui_splash.letter_level(index, ui_splash.DURATION), 0) end
end

function test_ui_splash_runs_for_its_duration_then_ends()
  ui_splash.start()
  local frames = 0
  while ui_splash.advance() do frames = frames + 1 end
  luaunit.assert_false(ui_splash.active())
  luaunit.assert_equals(frames + 1, math.ceil(ui_splash.DURATION * ui_splash.FPS))
end

function test_ui_splash_input_ends_it_immediately()
  ui_splash.start()
  ui_splash.advance()
  ui_splash.skip()
  luaunit.assert_false(ui_splash.active())
  luaunit.assert_false(ui_splash.advance())
end

function test_ui_splash_draws_without_randomness_and_hands_over_to_the_ui()
  local ui_drawn = 0
  local draw_ui = function() ui_drawn = ui_drawn + 1 end
  for t = 0, ui_splash.DURATION, 1 / 30 do
    with_recording_screen(function() ui_splash.draw(t, draw_ui) end)
  end
  luaunit.assert_true(ui_drawn > 0)
  -- Before the fade, the application screen is not drawn underneath.
  ui_drawn = 0
  with_recording_screen(function() ui_splash.draw(1.2, draw_ui) end)
  luaunit.assert_equals(ui_drawn, 0)
  -- The same time always draws the same frame.
  local a = with_recording_screen(function() ui_splash.draw(0.5) end)
  local b = with_recording_screen(function() ui_splash.draw(0.5) end)
  luaunit.assert_equals(a, b)
end
