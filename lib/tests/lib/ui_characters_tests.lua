-- Characterisation outside the manual (README "UI Motion" covers the option):
-- the screen's characters and value dial are deterministic art.

local characters = include("mosaic/lib/ui_characters")

local function record(body)
  local calls, saved, saved_random = {}, screen, math.random
  screen = setmetatable({}, {__index = function(_, name)
    return function(...) calls[#calls + 1] = table.concat({name, ...}, ",") end
  end})
  math.random = function() error("art used math.random") end
  local ok, err = pcall(body)
  screen, math.random = saved, saved_random
  if not ok then error(err, 0) end
  return table.concat(calls, ";")
end

function test_ui_characters_rest_pose_is_the_same_without_a_beat()
  for _, kind in ipairs({"doctor", "garden", "choir", "register", "metronome"}) do
    local a = record(function() characters.draw_art(kind, 0, true, nil) end)
    local b = record(function() characters.draw_art(kind, 0, true, {}) end)
    luaunit.assert_equals(a, b, kind)
    luaunit.assert_true(#a > 0, kind)
  end
end

function test_ui_characters_doctor_dances_four_eighth_note_poses()
  local frames = {}
  for step = 0, 3 do
    frames[step] = record(function() characters.draw_art("doctor", 0, true, {beat = step / 2 + 0.1}) end)
  end
  for a = 0, 3 do
    for b = a + 1, 3 do luaunit.assert_not_equals(frames[a], frames[b]) end
  end
  -- The dance repeats every two beats.
  luaunit.assert_equals(record(function() characters.draw_art("doctor", 0, true, {beat = 2.1}) end), frames[0])
end

function test_ui_characters_garden_and_choir_move_only_with_a_beat()
  for _, kind in ipairs({"garden", "choir"}) do
    local rest = record(function() characters.draw_art(kind, 0, true, nil) end)
    local moving = {}
    for step = 0, 5 do
      moving[#moving + 1] = record(function() characters.draw_art(kind, 0, true, {beat = step * 0.5 + 0.05}) end)
    end
    local differs = false
    for _, frame in ipairs(moving) do if frame ~= rest then differs = true end end
    luaunit.assert_true(differs, kind)
  end
end

function test_ui_characters_metronome_swings_both_ways()
  local left = record(function() characters.draw_art("metronome", 0, true, {beat = 0.5}) end)
  local right = record(function() characters.draw_art("metronome", 0, true, {beat = 1.5}) end)
  local rest = record(function() characters.draw_art("metronome", 0, true, nil) end)
  luaunit.assert_not_equals(left, right)
  luaunit.assert_not_equals(left, rest)
end

function test_ui_characters_dial_clamps_and_moves_its_needle()
  local low = record(function() characters.draw_dial(-5) end)
  luaunit.assert_equals(low, record(function() characters.draw_dial(0) end))
  luaunit.assert_equals(record(function() characters.draw_dial(7) end), record(function() characters.draw_dial(1) end))
  luaunit.assert_not_equals(low, record(function() characters.draw_dial(0.5) end))
end
