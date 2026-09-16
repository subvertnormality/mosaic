-- Characterisation of the redraw step guard: a redraw must not start when less
-- than the guard is left before the next step, and the guard has to cover how
-- long a redraw actually takes rather than a fixed estimate.
local redraw_guard = include("mosaic/lib/clock/redraw_guard")

local function fixture(remaining_sequence, cost_sequence)
  local state = {clock = 0, index = 0, draws = 0}
  local guard = redraw_guard.new(
    function()
      state.index = state.index + 1
      return remaining_sequence[state.index]
    end,
    function() return state.clock end)
  state.step = function()
    local cost = cost_sequence[state.index + 1] or 0
    local before = state.clock
    local ran = guard.run(function()
      state.draws = state.draws + 1
      state.clock = before + cost
    end)
    return ran
  end
  state.guard = guard
  return state
end

function test_redraw_guard_skips_a_redraw_inside_the_guard()
  local f = fixture({0.2, 0.01, 0.2}, {0, 0, 0})
  luaunit.assert_true(f.step())
  luaunit.assert_false(f.step())
  luaunit.assert_true(f.step())
  luaunit.assert_equals(f.draws, 2)
end

function test_redraw_guard_draws_when_the_transport_reports_nothing()
  local f = fixture({nil, nil}, {0, 0})
  luaunit.assert_true(f.step())
  luaunit.assert_true(f.step())
  luaunit.assert_equals(f.draws, 2)
end

function test_redraw_guard_starts_at_the_floor()
  local f = fixture({}, {})
  luaunit.assert_equals(f.guard.guard_seconds(), redraw_guard.FLOOR)
end

function test_redraw_guard_widens_to_cover_a_slow_redraw()
  local f = fixture({0.2, 0.2}, {0.04, 0})
  f.step()
  luaunit.assert_almost_equals(f.guard.guard_seconds(), 0.04, 1e-12)
  -- A redraw that would now fall inside the widened guard is skipped.
  local g = fixture({0.2, 0.03}, {0.04, 0})
  luaunit.assert_true(g.step())
  luaunit.assert_false(g.step())
end

function test_redraw_guard_never_exceeds_the_ceiling()
  local f = fixture({0.5, 0.5}, {10, 0})
  f.step()
  luaunit.assert_equals(f.guard.guard_seconds(), redraw_guard.CEILING)
end

function test_redraw_guard_decays_back_to_the_floor()
  local remaining, costs = {0.5, 0.5}, {0.05}
  for i = 2, 200 do remaining[i] = 0.5; costs[i] = 0 end
  local f = fixture(remaining, costs)
  f.step()
  luaunit.assert_almost_equals(f.guard.guard_seconds(), 0.05, 1e-12)
  for _ = 1, 100 do f.step() end
  luaunit.assert_equals(f.guard.guard_seconds(), redraw_guard.FLOOR)
end
