-- Characterisation outside the manual: the start-up splash animation. It must
-- be deterministic, never consume musical randomness, and end on input.

local ui_splash = include("mosaic/lib/ui_splash")

local logo = ui_splash.logo

local function blocks_at(t)
  local count = 0
  for index = 1, #logo.blocks do
    if ui_splash.block(index, t) then count = count + 1 end
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

function test_ui_splash_draws_the_logo_blocks_in_its_own_shades()
  -- Nine rows of dots and pills, 15 columns, in the logo's five shades.
  luaunit.assert_equals(logo.rows, 9)
  luaunit.assert_equals(logo.columns, 15)
  local shades, pills = {}, 0
  for _, b in ipairs(logo.blocks) do
    shades[b.level] = true
    if b.last > b.first then pills = pills + 1 end
  end
  luaunit.assert_equals(shades, {[2] = true, [4] = true, [6] = true, [9] = true, [15] = true})
  luaunit.assert_true(pills >= 20, "pill bars as well as dots")
  luaunit.assert_equals(#logo.letters, 6) -- m o s a i c
end

function test_ui_splash_blocks_lay_row_by_row_left_to_right()
  luaunit.assert_equals(blocks_at(0), 0)
  luaunit.assert_true(blocks_at(0.03) >= 1)
  for a, first in ipairs(logo.blocks) do
    for b, second in ipairs(logo.blocks) do
      -- Within a row, a block to the right never appears before one to its left;
      -- a lower row trails the row above, so it never overtakes the block above it.
      local later = second.first > first.first and second.row >= first.row
        or (second.row > first.row and second.first >= first.first)
      if later then
        for t = 0, 1.1, 1 / 60 do
          if ui_splash.block(b, t) then luaunit.assert_not_nil(ui_splash.block(a, t), a .. " before " .. b) end
        end
      end
    end
  end
  luaunit.assert_equals(blocks_at(1.1), #logo.blocks)
end

function test_ui_splash_blocks_lift_to_leave_the_word_which_then_fades()
  luaunit.assert_equals(ui_splash.letter_level(1, 1.1), 0)
  luaunit.assert_equals(blocks_at(1.9), 0)
  for index = 1, 6 do luaunit.assert_equals(ui_splash.letter_level(index, 1.95), 15) end
  -- Letters fade one after another, left to right.
  luaunit.assert_true(ui_splash.letter_level(1, 2.5) < ui_splash.letter_level(6, 2.5))
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
  with_recording_screen(function() ui_splash.draw(1.5, draw_ui) end)
  luaunit.assert_equals(ui_drawn, 0)
  -- The same time always draws the same frame.
  local a = with_recording_screen(function() ui_splash.draw(0.5) end)
  local b = with_recording_screen(function() ui_splash.draw(0.5) end)
  luaunit.assert_equals(a, b)
end
