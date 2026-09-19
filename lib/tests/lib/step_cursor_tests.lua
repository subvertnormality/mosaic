-- Characterisation of the next step selection currently embedded in m_clock.
-- The pure helper may not touch recorder/playback state.
local cursor = include("mosaic/lib/clock/step_cursor")

local function next_step(current, first_run, start_trig, end_trig, global_length)
  return {cursor.next(current, first_run, start_trig, end_trig, global_length)}
end

function test_step_cursor_first_run_preserves_the_existing_current_step_then_clamps_to_start()
  -- Characterisation of m_clock: first run does not increment the stored
  -- current step, which may have been restored from the project.
  luaunit.assert_equals(next_step(9, true, 3, 12, 16), {9, false})
  luaunit.assert_equals(next_step(1, true, 3, 12, 16), {3, false})
end

function test_step_cursor_advances_until_the_capped_end_then_wraps_to_start()
  luaunit.assert_equals(next_step(3, false, 3, 12, 16), {4, false})
  luaunit.assert_equals(next_step(12, false, 3, 12, 16), {3, true})
end

function test_step_cursor_caps_the_range_at_global_length_before_wrapping()
  -- Global length caps the channel's range relative to its selected start.
  luaunit.assert_equals(next_step(7, false, 3, 12, 8), {8, false})
  luaunit.assert_equals(next_step(9, false, 3, 12, 8), {10, false})
  luaunit.assert_equals(next_step(10, false, 3, 12, 8), {3, true})
end

function test_step_cursor_wraps_when_the_current_step_is_outside_the_capped_range()
  luaunit.assert_equals(next_step(99, false, 3, 12, 8), {3, true})
end
